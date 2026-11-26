#!/usr/bin/env python3
"""Parse and analyse the finite authored grammar. This is not a general NLP coder."""
from pathlib import Path
from collections import Counter, defaultdict
from fractions import Fraction
import csv
import hashlib
import itertools
import json
import math
import platform
import re
import sys

ROOT = Path(__file__).resolve().parent
INPUT = ROOT/'inputs'
OUT = ROOT/'results'

def read_csv(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))

def write_csv(path, rows, fields=None):
    if fields is None:
        fields = list(rows[0])
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=True, sort_keys=True) if isinstance(value,(dict,list)) else value for key,value in row.items()})

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def span(text, match):
    return {'start':match.start(), 'end':match.end(), 'text':text[match.start():match.end()]}

def jaccard(a,b):
    union = set(a)|set(b)
    return len(set(a)&set(b))/len(union) if union else None

def kappa(a,b,ordinal=False):
    if len(a)!=len(b) or not a:
        raise ValueError('Label streams must be nonempty and paired.')
    n=len(a)
    cats=range(5) if ordinal else sorted(set(a)|set(b))
    distance=(lambda x,y: abs(x-y)/4) if ordinal else (lambda x,y: int(x!=y))
    ca,cb=Counter(a),Counter(b)
    observed=sum(distance(x,y) for x,y in zip(a,b))/n
    expected=sum(ca[x]*cb[y]*distance(x,y) for x in cats for y in cats)/(n*n)
    return None if expected==0 else 1-observed/expected

def distribution(sets):
    counts=Counter(entity for values in sets for entity in set(values))
    total=sum(counts.values())
    if not total:
        return {'counts':{}, 'appearances':0, 'K':0, 'hhi':None, 'entropy':None, 'normalized_entropy':None, 'effective_hhi':None, 'effective_entropy':None}
    shares=[value/total for value in counts.values()]
    hhi=sum(p*p for p in shares)
    entropy=-sum(p*math.log(p) for p in shares)
    support=len(counts)
    return {'counts':dict(sorted(counts.items())), 'appearances':total, 'K':support, 'hhi':hhi,
            'entropy':entropy, 'normalized_entropy':entropy/math.log(support) if support>1 else None,
            'effective_hhi':1/hhi, 'effective_entropy':math.exp(entropy)}

def parse_response(text, entity_list):
    entities={item['product_id']:item for item in entity_list}
    aliases={item[key]:item['product_id'] for item in entity_list for key in ['name','alias']}
    brand_names={item['brand_name']:item['brand_id'] for item in entity_list}
    displayed=[]
    resolved_brands=set()
    unknown=[]
    entity_spans=[]
    for match in re.finditer(r'^- (.+)$',text,re.M):
        name=match.group(1)
        pid=aliases.get(name)
        entity_spans.append({'surface':name,'canonical_id':pid, **span(text,match)})
        if pid is None:
            unknown.append(name)
            matches={bid for brand,bid in brand_names.items() if re.search(r'(?<!\w)'+re.escape(brand)+r'(?!\w)',name)}
            if len(matches)==1:
                resolved_brands.update(matches)
        elif pid not in displayed:
            displayed.append(pid)
            resolved_brands.add(entities[pid]['brand_id'])
    strength=0
    groups=[]
    negative_products=[]
    advice_match=re.search(r'^Advice: (.+)$',text,re.M)
    if advice_match:
        advice=advice_match.group(1)
        regular = [
            (1,r'You could choose (.+?) first, followed by (.+?), if the listed features meet your needs\.'),
            (2,r'I recommend (.+?) first, followed by (.+?)\.'),
            (3,r'I strongly recommend (.+?) first, followed by (.+?)\.'),
            (4,r'Choose (.+?) first, followed by (.+?); (.+?) is clearly the best overall option for these needs\.')]
        found=False
        for level,pattern in regular:
            match=re.fullmatch(pattern,advice)
            if match:
                strength=level
                groups=[[aliases.get(match.group(1))],[aliases.get(match.group(2))]]
                if level==4 and match.group(3)!=match.group(1):
                    raise ValueError('Conflicting categorical choice in fixture.')
                found=True
                break
        tie=re.fullmatch(r'I recommend (.+?) and (.+?) equally; there is no overall first choice\.',advice)
        negative=re.fullmatch(r'I do not recommend (.+?)\.',advice)
        if tie:
            strength=2
            groups=[[aliases.get(tie.group(1)),aliases.get(tie.group(2))]]
            found=True
        if negative:
            found=True
            target=aliases.get(negative.group(1))
            if target is None:
                raise ValueError('Unresolved negative-advice target in controlled fixture.')
            negative_products.append(target)
        if not found:
            raise ValueError(f'Advice outside the declared grammar: {advice}')
        if any(pid not in displayed for group in groups for pid in group):
            raise ValueError('Unresolved or undisplayed recommendation target.')
    choice=re.search(r'^Overall choice: (.+?) is my single overall choice for these needs\.$',text,re.M)
    chosen=aliases.get(choice.group(1)) if choice else None
    if choice and (chosen not in displayed or strength==0):
        raise ValueError('Single-best choice violates the protocol.')
    comparison=re.search(r'^Comparison: (.+)$',text,re.M)
    prioritization=re.search(r'^Prioritization: (.+)$',text,re.M)
    information=re.search(r'^Evidence-linked claim: .+ has a battery life of \d+ hours',text,re.M)
    return {'products':displayed, 'brands':sorted(resolved_brands),
            'families':sorted({entities[pid]['family_id'] for pid in displayed}),
            'unknown_entities':unknown, 'entity_complete':not unknown,
            'information':int(bool(information)), 'comparison':int(bool(comparison)),
            'prioritization':int(bool(prioritization)), 'direct_recommendation':int(strength>0),
            'single_best':int(bool(chosen)), 'single_best_product':chosen,
            'strength':strength, 'recommendation_groups':groups,
            'first_displayed':displayed[0] if displayed else None,
            'first_recommended':groups[0][0] if groups and len(groups[0])==1 else None,
            'top_recommendation_tied':bool(groups and len(groups[0])>1),
            'negative_advice_products':negative_products,
            'trace':{'entity_mentions':entity_spans,
                     'information':span(text,information) if information else None,
                     'comparison':span(text,comparison) if comparison else None,
                     'prioritization':span(text,prioritization) if prioritization else None,
                     'advice':span(text,advice_match) if advice_match else None,
                     'single_best':span(text,choice) if choice else None}}

def assess_bundle(text, source_lookup, entities):
    match=re.search(r'^Evidence-linked claim: (.+?) has a battery life of (\d+) hours and a warranty of (\d+) years \[([^\]]+)\]\.$',text,re.M)
    if match is None:
        raise ValueError('Expected exactly one designated source-linked bundle.')
    if len(re.findall(r'^Evidence-linked claim:',text,re.M))!=1:
        raise ValueError('Fixture frame must have one focal bundle per response.')
    alias={item[key]:item['product_id'] for item in entities for key in ['name','alias']}
    source_id=match.group(4)
    source=source_lookup[source_id]
    requested_pid=alias.get(match.group(1))
    claim_span=span(text,match)
    atoms=[]
    if source['availability']!='available':
        return {'source_id':source_id, 'source_path':'', 'source_sha256':'', 'source_type':'unavailable',
                'support':'inaccessible','permissive_support':'inaccessible',
                'claim_span':claim_span,'excerpt':None,'atoms':[]}
    path=INPUT/source['document_path']
    source_text=path.read_text(encoding='utf-8')
    product_match=re.search(r'^Product: (.+)$',source_text,re.M)
    source_pid=alias.get(product_match.group(1)) if product_match else None
    if source_pid!=requested_pid:
        raise ValueError('Focal claim/source product mismatch in the controlled fixture.')
    source_type=re.search(r'^Publisher type: (.+)$',source_text,re.M).group(1)
    begin=source_text.index('Product: ')
    excerpt={'start':begin,'end':len(source_text),'text':source_text[begin:]}
    for field,claim_value,pattern in [
        ('battery_hours',int(match.group(2)),r'^Battery life: (.+)\.$'),
        ('warranty_years',int(match.group(3)),r'^Warranty: (.+)\.$')]:
        evidence=re.search(pattern,source_text,re.M)
        value_match=re.match(r'(\d+) (hours|years)$',evidence.group(1)) if evidence else None
        actual=int(value_match.group(1)) if value_match else None
        code='N' if actual is None else ('E' if actual==claim_value else 'C')
        atoms.append({'field':field,'claimed_value':claim_value,'source_value':actual,
                      'judgement':code, 'evidence_span':span(source_text,evidence) if evidence else None})
    codes=[a['judgement'] for a in atoms]
    strict=('unsupported' if 'C' in codes else 'full' if all(x=='E' for x in codes)
            else 'partial' if 'E' in codes else 'unsupported')
    permissive='full' if 'E' in codes else 'unsupported'
    return {'source_id':source_id,'source_path':source['document_path'],'source_sha256':digest(path),
            'source_type':source_type,'support':strict,'permissive_support':permissive,
            'claim_span':claim_span,'excerpt':excerpt,'atoms':atoms}

def pair_rows(rows):
    output=[]
    dimensions=[('within_snapshot','replicate'),('wording','wording'),('adjacent_snapshot','snapshot')]
    for contrast,changed in dimensions:
        keys=[key for key in ['query_id','scenario','wording','snapshot','replicate'] if key!=changed]
        groups=defaultdict(list)
        for row in rows:
            groups[tuple(row[key] for key in keys)].append(row)
        for key,group in sorted(groups.items()):
            if len(group)!=2:
                raise ValueError('Expected exactly two members of each constructed pair.')
            a,b=sorted(group,key=lambda x:x[changed])
            eligible=a['first_recommended'] is not None and b['first_recommended'] is not None
            depth=min(len(a['products']),len(b['products']))
            weights=[.9**d for d in range(depth)]
            prefix=sum(weights[d]*len(set(a['products'][:d+1])&set(b['products'][:d+1]))/(d+1) for d in range(depth))/sum(weights) if depth else None
            output.append({'contrast':contrast,'query_id':a['query_id'],'scenario':a['scenario'],
                           'record_a':a['record_id'],'record_b':b['record_id'],
                           'brand_jaccard':jaccard(a['brands'],b['brands']),
                           'product_jaccard':jaccard(a['products'],b['products']),
                           'family_jaccard':jaccard(a['families'],b['families']),
                           'weighted_prefix_overlap':prefix,
                           'first_display_agreement':int(a['first_displayed']==b['first_displayed']),
                           'first_recommendation_eligible':int(eligible),
                           'first_recommendation_agreement':int(a['first_recommended']==b['first_recommended']) if eligible else None})
    return output

def mean(values):
    vals=[x for x in values if x is not None]
    return sum(vals)/len(vals) if vals else None

def main():
    OUT.mkdir(exist_ok=True)
    entities=json.loads((INPUT/'entities.json').read_text(encoding='utf-8'))
    source_lookup={row['source_id']:row for row in read_csv(INPUT/'source_index.csv')}
    rows=[]
    traces=[]
    claims=[]
    atoms=[]
    streams=[]
    for meta in read_csv(INPUT/'record_index.csv'):
        path=INPUT/meta['response_path']
        text=path.read_text(encoding='utf-8')
        coded=parse_response(text,entities)
        evidence=assess_bundle(text,source_lookup,entities)
        trace=coded.pop('trace')
        rows.append({**meta,**coded,'brand_count':len(coded['brands']),
                     'product_count':len(coded['products']),'family_count':len(coded['families']),
                     'support':evidence['support'],'source_type':evidence['source_type']})
        traces.append({'record_id':meta['record_id'],'response_path':meta['response_path'],
                       'response_sha256':digest(path),'coding_origin':'deterministic_controlled_grammar_v1',
                       'human_coder':False, 'response_trace':trace,'evidence_trace':evidence})
        claims.append({'record_id':meta['record_id'],'source_id':evidence['source_id'],
                       'source_path':evidence['source_path'],'source_sha256':evidence['source_sha256'],
                       'claim_start':evidence['claim_span']['start'],'claim_end':evidence['claim_span']['end'],
                       'excerpt_start':evidence['excerpt']['start'] if evidence['excerpt'] else None,
                       'excerpt_end':evidence['excerpt']['end'] if evidence['excerpt'] else None,
                       'source_type':evidence['source_type'], 'support_A':evidence['support'],
                       'support_B':evidence['permissive_support']})
        for atom in evidence['atoms']:
            atoms.append({'record_id':meta['record_id'],'source_id':evidence['source_id'],**atom})
        baseline={0:0,1:0,2:2,3:2,4:4}[coded['strength']]
        streams.append({'record_id':meta['record_id'],'strength_A':coded['strength'],
                        'strength_B':baseline,'direct_A':coded['direct_recommendation'],
                        'direct_B':int(baseline>0),'support_A':evidence['support'],
                        'support_B':evidence['permissive_support'],
                        'origin_A':'declared_protocol_on_controlled_grammar',
                        'origin_B':'declared_deliberately_coarser_procedure'})
    pairs=pair_rows(rows)
    scenario_summary=[]
    for scenario in ['X','Y']:
        group=[row for row in rows if row['scenario']==scenario]
        brand=distribution([row['brands'] for row in group])
        product=distribution([row['products'] for row in group])
        family=distribution([row['families'] for row in group])
        counts=Counter(row['support'] for row in group)
        scenario_summary.append({'scenario':scenario,'n_responses':len(group),
            'mean_brand_count':mean([row['brand_count'] for row in group]),
            'mean_product_count':mean([row['product_count'] for row in group]),
            'mean_family_count':mean([row['family_count'] for row in group]),
            'direct_recommendation_count':sum(row['direct_recommendation'] for row in group),
            'single_best_count':sum(row['single_best'] for row in group),
            'full_support_count':counts['full'],'partial_support_count':counts['partial'],
            'unsupported_count':counts['unsupported'],'inaccessible_count':counts['inaccessible'],
            'support_denominator':len(group),'assessable_support_denominator':len(group)-counts['inaccessible'],
            'brand_distribution':brand,'product_distribution':product,'family_distribution':family})
    overlap=[]
    for scenario,contrast in itertools.product(['X','Y'],['within_snapshot','wording','adjacent_snapshot']):
        group=[row for row in pairs if row['scenario']==scenario and row['contrast']==contrast]
        overlap.append({'scenario':scenario,'contrast':contrast,'n_pairs':len(group),
            'mean_brand_jaccard':mean([row['brand_jaccard'] for row in group]),
            'mean_product_jaccard':mean([row['product_jaccard'] for row in group]),
            'mean_family_jaccard':mean([row['family_jaccard'] for row in group]),
            'mean_weighted_prefix_overlap':mean([row['weighted_prefix_overlap'] for row in group]),
            'first_display_agreement':mean([row['first_display_agreement'] for row in group]),
            'first_recommendation_eligible':sum(row['first_recommendation_eligible'] for row in group),
            'first_recommendation_agreement':mean([row['first_recommendation_agreement'] for row in group])})
    agreements=[]
    for label,ka,kb,ordinal in [('direct_recommendation','direct_A','direct_B',False),('strength','strength_A','strength_B',True),('bundle_support','support_A','support_B',False)]:
        a=[row[ka] for row in streams]
        b=[row[kb] for row in streams]
        agreements.append({'field':label,'n_pairs':len(a),'raw_agreement':sum(x==y for x,y in zip(a,b))/len(a),
                           'kappa':kappa(a,b,ordinal),'coefficient':'linearly_weighted_kappa' if ordinal else 'nominal_kappa',
                           'interpretation':'agreement_between_two_authored_deterministic_procedures_only'})
    verification=manual_checks(rows,overlap,agreements,entities)
    write_csv(OUT/'coded_responses.csv',rows)
    write_csv(OUT/'claim_bundles.csv',claims)
    write_csv(OUT/'claim_atoms.csv',atoms)
    write_csv(OUT/'constructed_label_streams.csv',streams)
    write_csv(OUT/'condition_pairs.csv',pairs)
    write_csv(OUT/'scenario_summary.csv',scenario_summary)
    write_csv(OUT/'overlap_summary.csv',overlap)
    write_csv(OUT/'algorithm_agreement.csv',agreements)
    with (OUT/'annotation_trace.jsonl').open('w',encoding='utf-8') as stream:
        for trace in traces:
            stream.write(json.dumps(trace,sort_keys=True,ensure_ascii=True)+'\n')
    summary={'origin':'new_fully_disclosed_authored_synthetic_demonstration',
             'n_responses':len(rows),'n_base_queries':2,'scenario_summary':scenario_summary,
             'overlap':overlap,'agreement':agreements,
             'strength_counts':dict(sorted(Counter(row['strength'] for row in rows).items())),
             'support_counts':dict(sorted(Counter(row['support'] for row in rows).items())),
             'source_document_count':12,'source_locators':16,'new_platform_observations':0,
             'human_coding_sessions':0,'verification':verification}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (OUT/'verification.json').write_text(json.dumps(verification,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (ROOT/'runtime.json').write_text(json.dumps({'python':platform.python_version(),'implementation':platform.python_implementation(),
        'dependencies':'Python standard library only','randomness':'none','version':'1.0.0'},indent=2)+'\n',encoding='utf-8')
    write_tex(summary)
    files=[ROOT/'fixture_spec.json',ROOT/'build_inputs.py',ROOT/'run_demo.py',ROOT/'run_all.py',ROOT/'verify_reproducibility.py',ROOT/'README.md']
    files += sorted(p for p in INPUT.rglob('*') if p.is_file())
    files += sorted(p for p in OUT.rglob('*') if p.is_file())
    files += [ROOT/'main_results.tex',ROOT/'overview.tex']
    manifest={'hash_algorithm':'SHA-256','version':'1.0.0','files':[
        {'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':digest(path)} for path in files]}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','records':len(rows),'manual_checks':verification['check_count'],
                      'scenarios':scenario_summary,'agreement':agreements},indent=2))

def manual_checks(rows,overlap,agreements,entities):
    """Fixed analytic expectations, independent of the computed summaries."""
    checks=[]
    def require(name,condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    def close(name,actual,expected):
        require(name,math.isclose(actual,float(expected),rel_tol=1e-12,abs_tol=1e-12))
    require('32 finite constructed records',len(rows)==32)
    require('all construction metadata have fictional origin',all(r['origin']=='new_authored_fictional_fixture' for r in rows))
    require('all response entities resolved',all(r['entity_complete'] for r in rows))
    require('80 strict-product appearances',sum(r['product_count'] for r in rows)==80)
    require('68 brand appearances',sum(r['brand_count'] for r in rows)==68)
    require('fixed strength distribution',Counter(r['strength'] for r in rows)==Counter({0:5,1:5,2:7,3:8,4:7}))
    require('fixed support distribution',Counter(r['support'] for r in rows)==Counter({'full':6,'partial':6,'unsupported':10,'inaccessible':10}))
    for scenario,brands,products,hh in [('X',Fraction(7,4),2,Fraction(17,49)),('Y',Fraction(5,2),3,Fraction(17,50))]:
        group=[r for r in rows if r['scenario']==scenario]
        close(scenario+' hand-derived brand mean',mean([r['brand_count'] for r in group]),brands)
        close(scenario+' hand-derived product mean',mean([r['product_count'] for r in group]),products)
        close(scenario+' hand-derived brand HHI',distribution([r['brands'] for r in group])['hhi'],hh)
        close(scenario+' equal product frequencies',distribution([r['products'] for r in group])['hhi'],Fraction(1,4))
    expected={('X','within_snapshot'):(Fraction(7,24),Fraction(1,6)),('X','wording'):(Fraction(7,24),Fraction(1,6)),
              ('X','adjacent_snapshot'):(Fraction(5,12),Fraction(1,3)),('Y','within_snapshot'):(Fraction(2,3),Fraction(1,2)),
              ('Y','wording'):(Fraction(2,3),Fraction(1,2)),('Y','adjacent_snapshot'):(Fraction(2,3),Fraction(1,2))}
    for row in overlap:
        eb,ep=expected[row['scenario'],row['contrast']]
        require(row['scenario']+' '+row['contrast']+' pair count',row['n_pairs']==8)
        close(row['scenario']+' '+row['contrast']+' hand-derived brand overlap',row['mean_brand_jaccard'],eb)
        close(row['scenario']+' '+row['contrast']+' hand-derived product overlap',row['mean_product_jaccard'],ep)
    expected_k={'direct_recommendation':Fraction(11,19),'strength':Fraction(3,4),'bundle_support':Fraction(35,99)}
    for row in agreements:
        close('hand-derived '+row['field']+' kappa',row['kappa'],expected_k[row['field']])
    by_id={r['record_id']:r for r in rows}
    a=by_id['D_QD01_W0_X_S0_R0']; b=by_id['D_QD01_W0_X_S0_R1']
    require('worked example 1 exact product list',a['products']==['P_A1','P_B1'])
    require('worked example 1 no choice advice',a['strength']==0 and a['direct_recommendation']==0)
    require('worked example 1 full bundle',a['support']=='full')
    require('worked example 2 distinct configurations same brand',b['brand_count']==1 and b['product_count']==2 and b['family_count']==1)
    require('worked example 2 tentative selection',b['strength']==1 and b['direct_recommendation']==1 and b['single_best']==0)
    require('worked example 2 display differs from recommendation',b['first_displayed']=='P_A1' and b['first_recommended']=='P_A2')
    require('worked example 2 partial bundle',b['support']=='partial')
    require('joint-empty Jaccard undefined',jaccard([],[]) is None)
    require('one-empty Jaccard zero',jaccard([],['P_A1'])==0)
    require('constant identical labels do not imply kappa one',kappa([1,1],[1,1]) is None)
    negative=parse_response('Options in display order:\n- DemoAlpha One standard\nAdvice: I do not recommend DemoAlpha One standard.\n',entities)
    require('negative recommendation is not positive choice advice',negative['direct_recommendation']==0 and negative['negative_advice_products']==['P_A1'])
    tied=parse_response('Options in display order:\n- DemoAlpha One standard\n- DemoBeta Solo\nAdvice: I recommend DemoAlpha One standard and DemoBeta Solo equally; there is no overall first choice.\n',entities)
    require('top tie retained without invented first recommendation',tied['top_recommendation_tied'] and tied['first_recommended'] is None and tied['single_best']==0)
    repeated=parse_response('Options in display order:\n- DemoAlpha One standard\n- DemoAlpha One (standard)\n',entities)
    require('known aliases count once per response',len(repeated['products'])==1)
    require('name-only lists do not establish information',repeated['information']==0)
    unknown=parse_response('Options in display order:\n- DemoAlpha unspecified model\n',entities)
    require('unknown product is not silently assigned a strict identity',not unknown['entity_complete'] and len(unknown['products'])==0)
    require('known brand retained when strict model unresolved',unknown['brands']==['B_A'])
    return {'status':'PASS','check_count':len(checks),'checks':checks,
            'scope':'construction, parsing and arithmetic checks; no external measurement validation'}

def write_tex(summary):
    profiles=summary['scenario_summary']
    text=[r'\begin{table}[H]',r'\begin{revision}',
          r'\caption{Results of the newly constructed demonstration. X and Y are authored scenarios, not AI systems. Each scenario contains 16 fictional answers.}\label{tab:demo_profile}',
          r'\small',r'\begin{tabularx}{\textwidth}{Xrr}',r'\toprule',r'Indicator & Scenario X & Scenario Y \\',r'\midrule']
    entries=[('Mean distinct brands','mean_brand_count'),('Mean strict products','mean_product_count'),('Mean product families','mean_family_count')]
    for label,key in entries:
        text.append(f'{label} & {profiles[0][key]:.3f} & {profiles[1][key]:.3f} '+r'\\')
    for label,key in [('Direct recommendation','direct_recommendation_count'),('Single overall choice','single_best_count'),('Full support in fictional evidence','full_support_count'),('Partial support','partial_support_count'),('Unsupported','unsupported_count'),('Unavailable fictional evidence','inaccessible_count')]:
        text.append(f'{label} & {profiles[0][key]}/16 & {profiles[1][key]}/16 '+r'\\')
    text += [f"Brand HHI & {profiles[0]['brand_distribution']['hhi']:.3f} & {profiles[1]['brand_distribution']['hhi']:.3f} "+r'\\',
             f"Strict-product HHI & {profiles[0]['product_distribution']['hhi']:.3f} & {profiles[1]['product_distribution']['hhi']:.3f} "+r'\\',
             r'\bottomrule',r'\end{tabularx}',r'\end{revision}',r'\end{table}',
             r'\begin{table}[H]',r'\begin{revision}',
             r'\caption{Agreement between two explicitly constructed coding procedures. Both procedures run on the same authored inputs; the coefficients do not estimate human coder reliability or coding validity.}\label{tab:demo_algorithm_agreement}',
             r'\small',r'\begin{tabularx}{\textwidth}{Xrrr}',r'\toprule',r'Field & Paired units & Raw agreement & $\kappa$ \\',r'\midrule']
    names={'direct_recommendation':'Direct recommendation','strength':'Strength (linear weights)','bundle_support':'Bundle support'}
    for row in summary['agreement']:
        text.append(f"{names[row['field']]} & {row['n_pairs']} & {row['raw_agreement']:.3f} & {row['kappa']:.3f} "+r'\\')
    text += [r'\bottomrule',r'\end{tabularx}',r'\end{revision}',r'\end{table}',
             r'\begin{table}[H]',r'\begin{revision}',
             r'\caption{Set overlap in the constructed demonstration. Every row uses eight declared response pairs. Snapshot positions are authored conditions, not collection dates.}\label{tab:demo_overlap}',
             r'\small',r'\begin{tabularx}{\textwidth}{lXrr}',r'\toprule',r'Scenario & Contrast & Brand Jaccard & Product Jaccard \\',r'\midrule']
    names={'within_snapshot':'Repetition within a snapshot','wording':'Matched wording variants','adjacent_snapshot':'Adjacent constructed snapshots'}
    for row in summary['overlap']:
        text.append(f"{row['scenario']} & {names[row['contrast']]} & {row['mean_brand_jaccard']:.3f} & {row['mean_product_jaccard']:.3f} "+r'\\')
    text += [r'\bottomrule',r'\end{tabularx}',r'\end{revision}',r'\end{table}']
    (ROOT/'main_results.tex').write_text('\n'.join(text)+'\n',encoding='utf-8')
    overview=r'''\section{Reproducible constructed demonstration}
\label{sec:demo_supplement}
This supplement describes a new authored synthetic example. No commercial AI platform was queried, no human coding session was conducted, and no external source page was sampled. It does not relabel or authenticate the earlier archive of 2400 processed records. All names, statements, sources and scenario differences in this example were deliberately constructed for teaching the procedure.

\subsection{Documented construction}
The example contains two authored shopping needs, two wording variants, scenarios X and Y, two ordered snapshot positions, and two replicates. Their complete crossing gives 32 fictional answer documents. All construction decisions are in \texttt{fixture\_spec.json}; \texttt{build\_inputs.py} implements the disclosed recipe. Let $q,w,s,r\in\{0,1\}$ identify query, wording, snapshot and replicate, and let $c=0$ for X and $c=1$ for Y. The display pattern is $(2q+w+2s+r)\bmod 4$, the advice template is $(q+2w+s+r+c)\bmod 5$, and the source case is $(q+w+s+r+c)\bmod 4$. These arithmetic rules create inspectable differences; they model neither a vendor nor a stochastic data-generating process.

The four products are DemoAlpha One standard, DemoAlpha One extended, DemoBeta Solo and DemoGamma Mini. The first two share one brand and one declared family but have separate strict identities. Each has two declared surface forms. Scenario X displays two strict products and scenario Y displays three. The four display patterns are fully enumerated in the specification. Selection advice refers first to the last displayed item and then to the first displayed item. This deliberately separates display order from recommendation order.

\subsection{Raw text and deterministic coding}
The package retains every unmodified generated answer as a text file, every prompt, the record index, the alias dictionary and all available fictional source documents. The parser in \texttt{run\_demo.py} reads the text files; it does not obtain the reported codes from the construction formula. It recognizes only the published templates. An unrecognized advice sentence stops execution. This exact parser is an inspectable implementation for a controlled grammar, not a validated natural-language coding tool for arbitrary answers. Human use of the prospective protocol still requires independent training and assessment.

Procedure A implements the declared rules on this grammar. Procedure B intentionally drops tentative level-1 selection advice and treats level-3 strong advice as ordinary level-2 advice. For evidence, A requires all material atoms to be supported and gives any contradiction priority; B uses a deliberately permissive rule that labels a bundle full whenever at least one atom is supported. Both retain unavailable evidence as inaccessible. The two procedures are fully deterministic and share inputs. Their agreement illustrates the calculation and its dependence on the rule; it is not human inter-rater reliability, independent validation, or evidence of accuracy.

\subsection{Evidence integration and trace}
Each answer contains one designated battery-life-and-warranty bundle, which forms the complete 32-unit claim frame. Twelve complete fictional documents are supplied; four additional source locators are deliberately unavailable. Available documents contain exact values for both elements, an exact battery value with warranty not stated, or a contradictory battery value with an exact warranty. A contradictory element makes the whole bundle unsupported under Procedure A, even when the other element is supported. Available evidence yields two atomic records; inaccessible bundles retain a bundle-level availability code and do not invent assessable atomic labels.

\texttt{annotation\_trace.jsonl} preserves the exact response span, source file, source hash, excerpt boundaries and atomic decision for each coded bundle. Offsets are zero-based, end-exclusive Unicode character positions in the UTF-8 text after decoding. The complete source text is retained alongside each excerpt so that surrounding context can be checked. The excerpt is the contiguous product, battery and warranty block selected by an explicit deterministic rule. These local fictional sources do not establish factual support for real products or live website citations.

\subsection{Worked records}
Record \texttt{D\_QD01\_W0\_X\_S0\_R0} displays DemoAlpha One standard and DemoBeta Solo. It contains no selection-oriented advice. Its breadth is two brands and two strict products, strength is 0, and both atoms of its focal claim are supported in the constructed source. Record \texttt{D\_QD01\_W0\_X\_S0\_R1} displays the standard and extended versions of DemoAlpha One. They contribute one brand, two strict products and one family. The sentence beginning ``You could choose'' names the extended version first and the standard version second, giving direct recommendation = 1 and strength = 1. No single overall choice is asserted. The displayed first product is therefore different from the first recommended product. Only battery life is established by the associated document; the bundle receives partial support. Both full answer documents, associated source texts and coding spans are supplied.

\subsection{Checks and reproduction}
From \texttt{round2\_supplement/demo}, run \texttt{python run\_all.py} using Python 3.10 or later; no third-party packages or network access are needed. The command regenerates the complete fixture, reads the resulting text, computes codes and outputs the tables. \texttt{manifest.json} records SHA-256 hashes for the scripts, specification, inputs, coded outputs and generated LaTeX tables. \texttt{runtime.json} records the tested Python interpreter. Repeating the command in the same runtime regenerates byte-identical deterministic artifacts. The separate reproducibility receipt records the two-run comparison.

Fixed hand-derived checks include 80 strict-product appearances, 68 brand appearances, scenario brand means of $7/4$ and $5/2$, brand HHI values of $17/49$ and $17/50$, and equal strict-product HHI of $1/4$. The paired procedure checks have nominal $\kappa=11/19$ for direct recommendation, linearly weighted $\kappa=3/4$ for strength, and nominal $\kappa=35/99$ for bundle support. Boundary checks retain undefined joint-empty Jaccard and undefined constant-label kappa, keep top-rank ties, distinguish negative from positive advice, merge declared aliases, and flag unresolved entities. These checks verify the authored example and arithmetic; they do not validate the framework against real system outputs or independent human judgement.

No confidence intervals, significance tests or population claims are produced for the finite authored example. Every count and difference follows from the disclosed construction. The interpretation is procedural: breadth, concentration, order, agreement and evidence support measure distinct properties and must keep their own units and denominators.
'''
    (ROOT/'overview.tex').write_text(overview,encoding='utf-8')

if __name__ == '__main__':
    main()

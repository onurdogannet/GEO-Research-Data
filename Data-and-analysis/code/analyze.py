#!/usr/bin/env python3
"""Recompute all estimates, tables and figures from the supplied CSV records.

Inference resamples complete base-query clusters within category; it never
resamples individual responses as if they were independent shopping needs.
"""
from __future__ import annotations
import csv, hashlib, itertools, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'Data-and-analysis'/'data'
OUT=ROOT/'Data-and-analysis'/'results'
TEX=ROOT/'generated'
FIG=ROOT/'figures'
B=5000; SEED=80426
CAT_ORDER=['wireless_headphones','robot_vacuum_cleaners','laptops','sunscreen_products']
CAT_NAMES={'wireless_headphones':'Headphones','robot_vacuum_cleaners':'Robot vacuums','laptops':'Laptops','sunscreen_products':'Sunscreen'}

def esc(x):
    return str(x).replace('&',r'\&').replace('%',r'\%').replace('_',r'\_')

def interval(values, rng=None):
    a=np.asarray(values,float); a=a[np.isfinite(a)]
    if len(a)==0:return (np.nan,np.nan,np.nan)
    rng=rng or np.random.default_rng(SEED)
    means=np.mean(a[rng.integers(0,len(a),(B,len(a)))],axis=1)
    return float(a.mean()),*map(float,np.quantile(means,[.025,.975]))

def fmt(x,d=3):
    return '--' if not np.isfinite(x) else f'{x:.{d}f}'

def ci_text(t,d=3):return f'{fmt(t[0],d)} [{fmt(t[1],d)}, {fmt(t[2],d)}]'

def ptext(p):return '$<0.001$' if p<.001 else f'{p:.3f}'

def holm(ps):
    ps=np.asarray(ps,float); idx=np.argsort(ps); out=np.empty(len(ps)); cur=0
    for i,j in enumerate(idx):
        cur=max(cur,float(ps[j])*(len(ps)-i));out[j]=min(1,cur)
    return out

def jaccard(a,b):
    a,b=set(a),set(b)
    return len(a&b)/len(a|b) if a|b else np.nan

def prefix_overlap(a,b,p=.9):
    # Normalized finite-depth weighted prefix overlap; NOT extrapolated RBO.
    k=min(len(a),len(b))
    if not k:return np.nan
    weights=p**np.arange(k)
    overlaps=np.array([len(set(a[:d])&set(b[:d]))/d for d in range(1,k+1)])
    return float(weights@overlaps/weights.sum())

def kap_from_mat(m,weighted=False):
    n=m.sum()
    if n==0:return np.nan
    k=len(m); w=np.abs(np.arange(k)[:,None]-np.arange(k)[None,:])/(k-1) if weighted else 1-np.eye(k)
    expected=np.outer(m.sum(axis=1),m.sum(axis=0))/n
    denom=float(np.sum(w*expected))
    return 1-float(np.sum(w*m))/denom if denom else np.nan

def write_table(name,header,rows,caption,label,widths=None):
    n=len(header)
    layout=widths or ('l'+'r'*(n-1))
    body=[r'\begin{table}[H]',r'\caption{'+caption+r'}\label{'+label+'}',r'\small',r'\begin{tabularx}{\textwidth}{'+layout+'}',r'\toprule',
          ' & '.join(header)+r' \\',r'\midrule']
    body += [' & '.join(map(str,row))+r' \\' for row in rows]
    body += [r'\bottomrule',r'\end{tabularx}',r'\end{table}']
    (TEX/f'{name}.tex').write_text('\n'.join(body),encoding='utf-8')

def main():
    for p in [OUT,TEX,FIG]:p.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(SEED)
    r=pd.read_csv(DATA/'responses.csv',keep_default_na=False)
    items=pd.read_csv(DATA/'items.csv',keep_default_na=False)
    sources=pd.read_csv(DATA/'sources.csv',keep_default_na=False)
    sample=pd.read_csv(DATA/'claim_validation.csv',keep_default_na=False)
    paired=pd.read_csv(DATA/'paired_labels.csv',keep_default_na=False)
    if r.response_id.duplicated().any():raise ValueError('Duplicate response IDs')
    queries=r[['query_id','category']].drop_duplicates().sort_values('query_id').reset_index(drop=True)
    qids=queries.query_id.tolist(); qi={q:i for i,q in enumerate(qids)}
    # Bootstrap index matrix: retain every category with exactly ten query draws.
    boot=np.concatenate([rng.choice(np.where(queries.category.values==c)[0],size=(B,(queries.category==c).sum()),replace=True) for c in CAT_ORDER],axis=1)
    mult=np.stack([np.bincount(z,minlength=len(qids)) for z in boot])
    def strat_ci(a):
        a=np.asarray(a,float)
        estimates=np.nanmean(a[boot],axis=1)
        return float(np.nanmean(a)),*map(float,np.nanquantile(estimates,[.025,.975]))
    # Recompute all richness measures independently of summary columns.
    ib=items.groupby('response_id').brand_id.nunique();ip=items.groupby('response_id').product_id.nunique()
    if not np.array_equal(r.brand_count.values,r.response_id.map(ib).fillna(0).astype(int).values):raise ValueError('Brand count mismatch')
    if not np.array_equal(r.product_count.values,r.response_id.map(ip).fillna(0).astype(int).values):raise ValueError('Product count mismatch')
    r['source_identifier_count']=r.response_id.map(sources.groupby('response_id').source_domain.nunique())
    r['citation_count']=r.response_id.map(sources.groupby('response_id').citation_events.sum())
    r.to_csv(OUT/'response_metrics.csv',index=False)
    qmeans=r.groupby(['query_id','category','system'])[['brand_count','product_count','source_identifier_count','direct_recommendation','single_best']].mean().reset_index()
    qmeans.to_csv(OUT/'query_means.csv',index=False)
    freq_tables={}
    for typ,col,df in [('brand','brand_id',items.drop_duplicates(['response_id','brand_id'])),('product','product_id',items),('source_identifier','source_domain',sources)]:
        freq=df.groupby(['category','system',col]).size().rename('appearances').reset_index()
        freq['share']=freq.appearances/freq.groupby(['category','system']).appearances.transform('sum')
        freq.to_csv(OUT/f'{typ}_frequencies.csv',index=False);freq_tables[typ]=freq
    coverage=[]; diversity=[]
    for cat in CAT_ORDER:
        for sys in ['A','B']:
            sub=r[(r.category==cat)&(r.system==sys)];qm=qmeans[(qmeans.category==cat)&(qmeans.system==sys)]
            bci=interval(qm.brand_count,rng);pci=interval(qm.product_count,rng)
            coverage.append(dict(category=cat,system=sys,n=len(sub),brand_mean=bci[0],brand_low=bci[1],brand_high=bci[2],
                product_mean=pci[0],product_low=pci[1],product_high=pci[2],source_mean=float(sub.source_count.mean())))
            for typ in freq_tables:
                f=freq_tables[typ];s=f[(f.category==cat)&(f.system==sys)]; p=s.share.values;H=float(-sum(p*np.log(p)));K=len(p);HHI=float(p@p)
                diversity.append(dict(category=cat,system=sys,entity=typ,K=K,H=H,H_normalized=H/np.log(K) if K>1 else np.nan,HHI=HHI,
                                      effective_shannon=float(np.exp(H)),effective_simpson=1/HHI))
    cov=pd.DataFrame(coverage);div=pd.DataFrame(diversity)
    cov.to_csv(OUT/'coverage.csv',index=False);div.to_csv(OUT/'diversity.csv',index=False)
    # Query-resampling intervals for aggregated nonlinear concentration statistics.
    div_ci=[]
    for cat in CAT_ORDER:
        qs=queries[queries.category==cat].query_id.tolist(); catdraw=rng.integers(0,len(qs),(B,len(qs)))
        weights=np.stack([np.bincount(z,minlength=len(qs)) for z in catdraw])
        for sys in ['A','B']:
            for typ,col,df in [('brand','brand_id',items.drop_duplicates(['response_id','brand_id'])),('product','product_id',items),('source_identifier','source_domain',sources)]:
                tmp=df[(df.category==cat)&(df.system==sys)]
                mat=tmp.groupby(['query_id',col]).size().unstack(fill_value=0).reindex(qs,fill_value=0).values
                draws=weights@mat;prob=draws/draws.sum(axis=1)[:,None];hh=(prob*prob).sum(axis=1)
                h=-np.sum(np.where(prob>0,prob*np.log(np.maximum(prob,1e-300)),0),axis=1)
                ks=(prob>0).sum(axis=1)
                div_ci.append(dict(category=cat,system=sys,entity=typ,HHI_low=np.quantile(hh,.025),HHI_high=np.quantile(hh,.975),
                  Hnorm_low=np.quantile(h/np.log(ks),.025),Hnorm_high=np.quantile(h/np.log(ks),.975)))
    div=div.merge(pd.DataFrame(div_ci),on=['category','system','entity']);div.to_csv(OUT/'diversity.csv',index=False)
    # Exact response-pair definitions, keeping their parent query identifier.
    rr={}; key_to_id={}
    for row in r.to_dict('records'):
        rid=row['response_id'];its=items[items.response_id==rid].sort_values('display_order')
        rec=its[its.explicitly_recommended==1].copy()
        if len(rec): rec['recommendation_rank']=rec.recommendation_rank.astype(int);rec=rec.sort_values('recommendation_rank')
        rr[rid]=dict(brand=list(dict.fromkeys(its.brand_id)),product=its.product_id.tolist(),family=list(dict.fromkeys(its.family_id)),
                     recommended=rec.product_id.tolist())
        key_to_id[(row['query_id'],row['system'],row['variant'],int(row['wave']),int(row['replicate']))]=rid
    pair_rows=[]
    def add(q,sys,contrast,ka,kb):
        a,b=key_to_id[ka],key_to_id[kb];aa,bb=rr[a],rr[b];x,y=aa['recommended'],bb['recommended']
        pair_rows.append(dict(query_id=q,category=queries.set_index('query_id').loc[q,'category'],system=sys,contrast=contrast,
          response_A=a,response_B=b,brand_jaccard=jaccard(aa['brand'],bb['brand']),product_jaccard=jaccard(aa['product'],bb['product']),
          family_jaccard=jaccard(aa['family'],bb['family']),weighted_prefix=prefix_overlap(aa['product'],bb['product']),
          first_display_agreement=int(aa['product'][0]==bb['product'][0]),
          first_recommendation_agreement=int(x[0]==y[0]) if x and y else np.nan))
    for q in qids:
        for sys in ['A','B']:
            for wave in range(1,6):
                for v in ['A','B']:
                    for x,y in itertools.combinations(range(1,4),2):add(q,sys,'within_wave',(q,sys,v,wave,x),(q,sys,v,wave,y))
                for rep in range(1,4):add(q,sys,'wording',(q,sys,'A',wave,rep),(q,sys,'B',wave,rep))
                if wave<5:
                    for v in ['A','B']:
                        for rep in range(1,4):add(q,sys,'between_wave',(q,sys,v,wave,rep),(q,sys,v,wave+1,rep))
    pairs=pd.DataFrame(pair_rows);pairs.to_csv(OUT/'response_pairs.csv',index=False)
    mets=['brand_jaccard','product_jaccard','family_jaccard','weighted_prefix','first_display_agreement','first_recommendation_agreement']
    pq=pairs.groupby(['query_id','category','system','contrast'])[mets].mean().reset_index();pq.to_csv(OUT/'query_similarity.csv',index=False)
    sim=[]
    for sys in ['A','B']:
        for contrast in ['within_wave','wording','between_wave']:
            sub=pq[(pq.system==sys)&(pq.contrast==contrast)].set_index('query_id').reindex(qids)
            for m in mets:
                t=strat_ci(sub[m].values);sim.append(dict(system=sys,contrast=contrast,metric=m,estimate=t[0],low=t[1],high=t[2],
                    valid_pairs=int(pairs[(pairs.system==sys)&(pairs.contrast==contrast)][m].notna().sum())))
    sim=pd.DataFrame(sim);sim.to_csv(OUT/'similarity.csv',index=False)
    def qmcol(field,sys):return qmeans[qmeans.system==sys].set_index('query_id').reindex(qids)[field].values
    pqp=pq.groupby(['query_id','contrast'])[mets].mean()
    def pcol(field,c):return pqp.xs(c,level='contrast').reindex(qids)[field].values
    contrasts=[('Brand breadth: B - A',qmcol('brand_count','B')-qmcol('brand_count','A')),
               ('Product breadth: B - A',qmcol('product_count','B')-qmcol('product_count','A')),
               ('Recommendation probability: B - A',qmcol('direct_recommendation','B')-qmcol('direct_recommendation','A')),
               ('Within-wave overlap: brand - product',pcol('brand_jaccard','within_wave')-pcol('product_jaccard','within_wave')),
               ('Product overlap: within - wording',pcol('product_jaccard','within_wave')-pcol('product_jaccard','wording')),
               ('Product overlap: within - between',pcol('product_jaccard','within_wave')-pcol('product_jaccard','between_wave'))]
    tests=[]
    for label,a in contrasts:
        ci=strat_ci(a);test=stats.ttest_1samp(a,0);tests.append(dict(contrast=label,estimate=ci[0],low=ci[1],high=ci[2],
          standardized_paired_d=float(np.mean(a)/np.std(a,ddof=1)),t=float(test.statistic),df=39,p=float(test.pvalue),clusters=40))
    tests=pd.DataFrame(tests);tests['p_holm']=holm(tests.p);tests.to_csv(OUT/'primary_contrasts.csv',index=False)
    # Category comparisons are descriptive query-sample contrasts, not randomized effects.
    cq=r.groupby(['query_id','category']).brand_count.mean().reset_index();post=[]
    for c1,c2 in itertools.combinations(CAT_ORDER,2):
        a=cq[cq.category==c1].brand_count.values;b=cq[cq.category==c2].brand_count.values
        bt=a[rng.integers(0,len(a),(B,len(a)))].mean(axis=1)-b[rng.integers(0,len(b),(B,len(b)))].mean(axis=1)
        t=stats.ttest_ind(a,b,equal_var=False);sd=np.sqrt(((len(a)-1)*a.var(ddof=1)+(len(b)-1)*b.var(ddof=1))/(len(a)+len(b)-2))
        g=(1-3/(4*(len(a)+len(b))-9))*(a.mean()-b.mean())/sd
        post.append(dict(category_A=c1,category_B=c2,difference=a.mean()-b.mean(),low=np.quantile(bt,.025),high=np.quantile(bt,.975),
                         hedges_g=g,p=float(t.pvalue),queries_A=len(a),queries_B=len(b)))
    post=pd.DataFrame(post);post['p_holm']=holm(post.p);post.to_csv(OUT/'category_comparisons.csv',index=False)
    # Component frequencies, retained separately from the highest role.
    components=['information','comparison','prioritization','direct_recommendation','single_best']
    comps=[]
    for sys in ['A','B']:
        for m in components:
            sub=r[r.system==sys];a=sub.groupby('query_id')[m].mean().reindex(qids).values;t=strat_ci(a)
            comps.append(dict(system=sys,component=m,count=int(sub[m].sum()),n=len(sub),proportion=t[0],low=t[1],high=t[2]))
    comps=pd.DataFrame(comps);comps.to_csv(OUT/'decision_components.csv',index=False)
    roles=r.groupby(['system','highest_role']).size().rename('count').reset_index();roles.to_csv(OUT/'highest_roles.csv',index=False)
    src=sources.groupby(['system','source_type']).size().rename('count').reset_index();src['share']=src['count']/src.groupby('system')['count'].transform('sum');src.to_csv(OUT/'source_types.csv',index=False)
    # Support: unweighted evaluated-link proportions; weighted figures supplement them.
    support_order=['fully_supported','partially_supported','unsupported','inaccessible'];supports=[]
    for sys in ['A','B']:
        ss=sample[sample.system==sys].copy();ss['weight']=1/ss.inclusion_probability
        for label in support_order:
            supports.append(dict(system=sys,support=label,count=int((ss.support_label==label).sum()),n=len(ss),
               proportion=float((ss.support_label==label).mean()),weighted_proportion=float(ss.loc[ss.support_label==label,'weight'].sum()/ss.weight.sum())))
    support=pd.DataFrame(supports);support.to_csv(OUT/'claim_support.csv',index=False)
    # Kappa with complete query-cluster resampling, based on pre-reconciliation labels.
    reliability=[]
    all_labels=pd.concat([paired,pd.read_csv(DATA/'paired_source_labels.csv'),pd.read_csv(DATA/'paired_support_labels.csv')],ignore_index=True)
    for field,pp in all_labels.groupby('field',sort=True):
        k={'recommendation_strength':5,'source_type':7,'source_support':4}.get(field,2); mats=[]
        for q in qids:
            mat=np.zeros((k,k),int)
            for z in pp[pp.query_id==q].itertuples():mat[int(z.label_A),int(z.label_B)]+=1
            mats.append(mat)
        mats=np.array(mats);total=mats.sum(axis=0); draws=np.einsum('bq,qij->bij',mult,mats)
        kappas=np.array([kap_from_mat(m,field=='recommendation_strength') for m in draws]);kap=kap_from_mat(total,field=='recommendation_strength')
        reliability.append(dict(field=field,n=len(pp),clusters=len(qids),raw_agreement=np.trace(total)/total.sum(),kappa=kap,
            low=np.nanquantile(kappas,.025),high=np.nanquantile(kappas,.975),coefficient='linear_weighted_kappa' if k==5 else 'cohen_kappa'))
    rel=pd.DataFrame(reliability);rel.to_csv(OUT/'coding_agreement.csv',index=False)
    # Transparent sample-boundary diagnostics and leave-one-category-out estimates.
    sensitivity=[]
    for omitted in CAT_ORDER:
        keep=queries.category.values!=omitted
        for label,a in contrasts:
            sensitivity.append(dict(omitted_category=omitted,contrast=label,estimate=float(np.mean(a[keep])),clusters=int(keep.sum())))
    pd.DataFrame(sensitivity).to_csv(OUT/'leave_one_category_out.csv',index=False)
    # Pointwise mean CI with and without preserving query clusters.
    all_qmean=r.groupby('query_id').brand_count.mean().reindex(qids).values
    overall_ci=strat_ci(all_qmean)
    naive_se=float(r.brand_count.std(ddof=1)/np.sqrt(len(r)))
    pd.DataFrame([dict(method='response_independence_normal',estimate=float(r.brand_count.mean()),low=float(r.brand_count.mean()-1.96*naive_se),high=float(r.brand_count.mean()+1.96*naive_se),units=len(r)),
                  dict(method='query_stratified_bootstrap',estimate=overall_ci[0],low=overall_ci[1],high=overall_ci[2],units=len(qids))]).to_csv(OUT/'resampling_comparison.csv',index=False)
    # Coded source-identifier breadth and product richness: descriptive, not distinct web domains.
    cor=stats.spearmanr(qmeans.source_identifier_count,qmeans.product_count)
    # Report exact main-table quantities and checks in a machine-readable summary.
    summary=dict(responses=len(r),queries=len(qids),brand_appearances=int(r.brand_count.sum()),product_appearances=len(items),
       unique_brands=int(items.brand_id.nunique()),unique_products=int(items.product_id.nunique()),source_records=len(sources),
       citation_events=int(sources.citation_events.sum()),unique_source_identifiers=int(sources.source_domain.nunique()),
       mean_brands=float(r.brand_count.mean()),mean_products=float(r.product_count.mean()),mean_sources=float(r.source_count.mean()),
       paired_label_units=int(paired.response_id.nunique()),label_disagreements=int((paired.label_A!=paired.label_B).sum()),
       support_sample=len(sample),support_full=int((sample.support_label=='fully_supported').sum()),
       support_partial=int((sample.support_label=='partially_supported').sum()),support_unsupported=int((sample.support_label=='unsupported').sum()),
       support_inaccessible=int((sample.support_label=='inaccessible').sum()),
       recommendation_count=int(r.direct_recommendation.sum()),single_best_count=int(r.single_best.sum()),
       coexistence_count=int(((r.comparison==1)&(r.direct_recommendation==1)).sum()),
       health_cautions=int(r.health_caution_present.sum()),health_responses=int((r.category=='sunscreen_products').sum()),
       correlation_source_product=float(cor.statistic),bootstrap_replicates=B,bootstrap_seed=SEED,
       pair_counts=pairs.groupby('contrast').size().to_dict())
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    # Compact LaTeX tables, generated directly from saved estimates.
    write_table('coverage',['Category','System','$n$','Brands, mean [95\\% CI]','Products, mean [95\\% CI]'],
       [[CAT_NAMES[x.category],x.system,x.n,ci_text((x.brand_mean,x.brand_low,x.brand_high),2),ci_text((x.product_mean,x.product_low,x.product_high),2)] for x in cov.itertuples()],
       'Response coverage and query-clustered breadth estimates. Each row contains ten base queries and 300 response records.','tab:coverage','Y c r r r')
    write_table('concentration',['Category','System','$K$','Normalized $H$','HHI [95\\% CI]','$e^H$'],
       [[CAT_NAMES[x.category],x.system,x.K,fmt(x.H_normalized),ci_text((x.HHI,x.HHI_low,x.HHI_high)),fmt(x.effective_shannon,2)] for x in div[div.entity=='brand'].itertuples()],
       'Brand appearance concentration. HHI uses appearance shares, not sales shares. Full product and source distributions accompany the data.','tab:concentration','Y c r r r r')
    snames={'within_wave':'Within wave','wording':'Wording','between_wave':'Adjacent wave'}
    def simval(s,c,m):
        x=sim[(sim.system==s)&(sim.contrast==c)&(sim.metric==m)].iloc[0];return (x.estimate,x.low,x.high)
    write_table('similarity',['System','Contrast','Brand $J$ [95\\% CI]','Product $J$ [95\\% CI]','Prefix overlap'],
       [[s,snames[c],ci_text(simval(s,c,'brand_jaccard')),ci_text(simval(s,c,'product_jaccard')),fmt(simval(s,c,'weighted_prefix')[0])] for s in ['A','B'] for c in snames],
       'Matched contrasts with query-clustered 95\\% intervals. Prefix overlap weights earlier displayed products more heavily.','tab:similarity','c l r r r')
    write_table('primary',['Contrast','Difference [95\\% CI]','$d_z$','Holm $p$'],
       [[esc(x.contrast),ci_text((x.estimate,x.low,x.high)),fmt(x.standardized_paired_d,2),ptext(x.p_holm)] for x in tests.itertuples()],
       'Primary query-level contrasts. Positive differences follow the direction shown. The six tests form one Holm family; $d_z$ standardizes paired query differences.','tab:contrasts','Y r r r')
    write_table('categories',['Category contrast','Difference [95\\% CI]','Hedges $g$','Holm $p$'],
       [[f'{CAT_NAMES[x.category_A]} -- {CAT_NAMES[x.category_B]}',ci_text((x.difference,x.low,x.high),2),fmt(x.hedges_g,2),ptext(x.p_holm)] for x in post.itertuples()],
       'Exploratory category comparisons for mean brand breadth. Each side contains ten query means. The six comparisons form a separate Holm family.','tab:categories','Y r r r')
    write_table('support',['Support class','A, $n$ (\\%)','B, $n$ (\\%)','Total, $n$ (\\%)'],
       [[label.replace('_',' ').capitalize(),f'{int(support[(support.system=="A")&(support.support==label)]["count"].iloc[0])} ({100*support[(support.system=="A")&(support.support==label)].proportion.iloc[0]:.1f})',
         f'{int(support[(support.system=="B")&(support.support==label)]["count"].iloc[0])} ({100*support[(support.system=="B")&(support.support==label)].proportion.iloc[0]:.1f})',
         f'{int((sample.support_label==label).sum())} ({100*(sample.support_label==label).mean():.1f})'] for label in support_order],
       'Source--claim classifications for 400 evaluated links: 200 per system. Inaccessible evidence is retained as a separate class.','tab:support','Y r r r')
    write_table('reliability',['Field','Units','Agreement','Kappa [95\\% CI]'],
       [[esc(x.field.replace('_',' ').capitalize()),x.n,f'{100*x.raw_agreement:.1f}\\%',ci_text((x.kappa,x.low,x.high))] for x in rel.itertuples()],
       'Agreement between pre-reconciliation label streams. All intervals resample the 40 query clusters. Recommendation strength uses linearly weighted kappa; other fields use nominal kappa.','tab:reliability','Y r r r')
    # Numeric macros used by the article, so changing the CSV values updates the text.
    macro_names={'responses':'NResponses','queries':'NQueries','brand_appearances':'BrandAppearances','product_appearances':'ProductAppearances','unique_brands':'NBrands','unique_products':'NProducts',
      'source_records':'NSourceRecords','citation_events':'NCitationEvents','unique_source_identifiers':'NSourceIdentifiers','paired_label_units':'NPaired','label_disagreements':'NDisagreements',
      'support_sample':'NSupport','support_full':'NSupportFull','support_partial':'NSupportPartial','support_unsupported':'NSupportUnsupported','support_inaccessible':'NSupportInaccessible',
      'recommendation_count':'NRecommended','single_best_count':'NSingleBest','coexistence_count':'NCoexist','health_cautions':'NHealthCaution','health_responses':'NHealth'}
    macros=['\\newcommand{\\'+v+'}{'+str(summary[k])+'}' for k,v in macro_names.items()]
    for key,n in [('mean_brands','MeanBrands'),('mean_products','MeanProducts'),('mean_sources','MeanSources'),('correlation_source_product','SourceProductRho')]:
        macros.append('\\newcommand{\\'+n+'}{'+fmt(summary[key],3 if key.startswith('correlation') else 2)+'}')
    for i,t in enumerate(tests.itertuples(),1):macros.append(r'\newcommand{\Effect'+['One','Two','Three','Four','Five','Six'][i-1]+'}{'+ci_text((t.estimate,t.low,t.high))+'}')
    for s in ['A','B']:
        for c,ct in [('within_wave','Within'),('wording','Wording'),('between_wave','Between')]:
            for m,mt in [('brand_jaccard','Brand'),('product_jaccard','Product'),('first_display_agreement','FirstDisplay'),('first_recommendation_agreement','FirstRec')]:
                macros.append('\\newcommand{\\'+s+ct+mt+'}{'+fmt(simval(s,c,m)[0])+'}')
    (TEX/'values.tex').write_text('\n'.join(macros),encoding='utf-8')
    # One figure per plot. Use matplotlib defaults; no editorial color coding.
    fig,ax=plt.subplots(figsize=(7.1,3.6))
    for i,sys in enumerate(['A','B']):
        sub=cov[cov.system==sys].set_index('category').loc[CAT_ORDER];xx=np.arange(4)+(i-.5)*.14
        ax.errorbar(xx,sub.brand_mean,yerr=[sub.brand_mean-sub.brand_low,sub.brand_high-sub.brand_mean],fmt='o',capsize=4,label=f'System {sys}')
    ax.set_xticks(np.arange(4),[CAT_NAMES[c] for c in CAT_ORDER]);ax.set_ylabel('Distinct brands per response');ax.legend();ax.set_ylim(bottom=0);fig.tight_layout();fig.savefig(FIG/'brand_breadth.pdf');plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.1,3.6))
    for i,(sys,m) in enumerate(itertools.product(['A','B'],['brand_jaccard','product_jaccard'])):
        vals=[simval(sys,c,m) for c in snames];vv=np.array(vals);xx=np.arange(3)+(i-1.5)*.09
        ax.errorbar(xx,vv[:,0],yerr=[vv[:,0]-vv[:,1],vv[:,2]-vv[:,0]],fmt='o',capsize=3,label=f'{sys}: {"brands" if m=="brand_jaccard" else "products"}')
    ax.set_xticks(range(3),list(snames.values()));ax.set_ylabel('Mean Jaccard overlap');ax.set_ylim(0,1);ax.legend(ncol=2);fig.tight_layout();fig.savefig(FIG/'set_overlap.pdf');plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.1,3.7))
    stypes=['brand_manufacturer','retailer_marketplace','specialist_review','general_news','forum_social','institutional','other']
    for i,sys in enumerate(['A','B']):
        sub=src[src.system==sys].set_index('source_type').reindex(stypes)
        ax.barh(np.arange(7)+(i-.5)*.34,100*sub.share,height=.32,label=f'System {sys}')
    ax.set_yticks(range(7),['Brand / manufacturer','Retailer / marketplace','Specialist review','General news','Forum / social','Institutional','Other']);ax.invert_yaxis();ax.set_xlabel('Share of source records (%)');ax.legend();fig.tight_layout();fig.savefig(FIG/'source_types.pdf');plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.1,3.6))
    for i,sys in enumerate(['A','B']):
        sub=comps[comps.system==sys].set_index('component').reindex(components)
        ax.barh(np.arange(5)+(i-.5)*.34,100*sub.proportion,height=.32,label=f'System {sys}')
    ax.set_yticks(range(5),['Information','Comparison','Prioritization','Direct recommendation','Single overall choice']);ax.invert_yaxis();ax.set_xlabel('Responses with component (%)');ax.set_xlim(0,105);ax.legend();fig.tight_layout();fig.savefig(FIG/'decision_components.pdf');plt.close(fig)
    # Exact data-file fingerprints: content integrity, not evidence of live acquisition.
    lines=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in sorted(DATA.iterdir()) if p.is_file()]
    (OUT/'input_sha256.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2))
    print('\nPRIMARY CONTRASTS\n',tests.to_string(index=False))
    print('\nSIMILARITY\n',sim[sim.metric.isin(['brand_jaccard','product_jaccard'])].to_string(index=False))

if __name__=='__main__': main()

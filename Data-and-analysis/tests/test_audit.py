"""Offline structural, numerical and text-link tests for the coded research archive."""
from pathlib import Path
import hashlib
import importlib.util
import json
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'Data-and-analysis'/'data'
OUT=ROOT/'Data-and-analysis'/'results'
spec=importlib.util.spec_from_file_location('audit_analysis',ROOT/'Data-and-analysis'/'code'/'analyze.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

def read(name):return pd.read_csv(DATA/name,keep_default_na=False)

def objects(name):
    with (DATA/name).open(encoding='utf-8') as f:return [json.loads(line) for line in f if line.strip()]

class AuditDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=read('responses.csv');cls.q=read('queries.csv');cls.b=read('base_queries.csv')
        cls.i=read('items.csv');cls.s=read('sources.csv');cls.f=read('claim_frame.csv');cls.c=read('claim_validation.csv')
        cls.d=read('entity_dictionary.csv');cls.labels=read('paired_labels.csv')
        cls.text={v['response_id']:v for v in objects('response_texts.jsonl')}
        cls.docs={v['source_record_id']:v for v in objects('source_documents.jsonl')}
        cls.pairs=pd.read_csv(OUT/'response_pairs.csv')
        cls.summary=json.loads((OUT/'summary.json').read_text())

    def test_01_factorial_size(self):
        self.assertEqual(len(self.r),2400);self.assertEqual(len(self.q),80);self.assertEqual(len(self.b),40)
        self.assertTrue((self.r.groupby('query_id').size()==60).all())
        self.assertTrue((self.r.groupby(['query_id','variant','system','wave']).size()==3).all())
        self.assertFalse(self.r.duplicated(['query_id','variant','system','wave','replicate']).any())

    def test_02_balanced_query_families(self):
        self.assertTrue((self.b.groupby(['category','query_family']).size()==2).all())
        self.assertTrue((self.q.groupby('query_id').size()==2).all())
        self.assertTrue((self.r.groupby(['category','system']).size()==300).all())

    def test_03_keys_and_foreign_keys(self):
        for df,key in [(self.r,'response_id'),(self.d,'product_id'),(self.s,'source_record_id'),(self.f,'link_id'),(self.c,'link_id')]:
            self.assertFalse(df[key].duplicated().any(),key)
        self.assertEqual(set(self.text),set(self.r.response_id))
        self.assertEqual(set(self.docs),set(self.s.source_record_id))
        self.assertTrue(set(self.i.response_id)<=set(self.r.response_id))
        self.assertTrue(set(self.s.response_id)<=set(self.r.response_id))
        self.assertTrue(set(self.i.product_id)<=set(self.d.product_id))
        self.assertTrue(set(self.c.link_id)<=set(self.f.link_id))

    def test_04_parent_query_identity(self):
        parent=self.r.set_index('response_id')
        for frame in [self.i,self.s,self.f,self.c,self.labels]:
            self.assertTrue((frame.query_id==frame.response_id.map(parent.query_id)).all())
            self.assertTrue((frame.category==frame.response_id.map(parent.category)).all())

    def test_05_count_identities(self):
        ic=self.i.groupby('response_id').agg(brand=('brand_id','nunique'),product=('product_id','nunique'))
        self.assertTrue((self.r.brand_count==self.r.response_id.map(ic.brand)).all())
        self.assertTrue((self.r.product_count==self.r.response_id.map(ic["product"])).all())
        self.assertEqual(int(self.r.brand_count.sum()),10746)
        self.assertEqual(int(self.r.product_count.sum()),12451)
        self.assertEqual(self.r.product_count.sum(),len(self.i))
        self.assertTrue((self.r.product_count>=self.r.brand_count).all())
        self.assertFalse(self.i.duplicated(['response_id','product_id']).any())

    def test_06_strict_family_resolution(self):
        parent=self.d.set_index('product_id')
        self.assertEqual(self.d.brand_id.nunique(),46);self.assertEqual(len(self.d),184)
        self.assertTrue((self.i.brand_id==self.i.product_id.map(parent.brand_id)).all())
        self.assertTrue((self.i.family_id==self.i.product_id.map(parent.family_id)).all())
        self.assertTrue((self.d.groupby('family_id').size()==2).all())

    def test_07_text_and_prompt_hashes(self):
        for row in self.r.itertuples():
            text=self.text[row.response_id]['text']
            self.assertEqual(hashlib.sha256(text.encode('utf-8')).hexdigest(),row.response_sha256)
        for row in self.q.itertuples():self.assertEqual(hashlib.sha256(row.prompt.encode('utf-8')).hexdigest(),row.prompt_sha256)
        lookup=self.q.set_index(['query_id','variant']).prompt.to_dict()
        for row in self.r.itertuples():self.assertEqual(row.prompt,lookup[(row.query_id,row.variant)])

    def test_08_item_text_and_display_position(self):
        for rid,group in self.i.groupby('response_id',sort=False):
            txt=self.text[rid]['text'];ordered=group.sort_values('display_order')
            self.assertEqual(ordered.display_order.tolist(),list(range(1,len(group)+1)))
            for it in ordered.itertuples():self.assertIn(f'{it.display_order}. {it.surface_name}:',txt)

    def test_09_recommendation_text_and_counts(self):
        rc=self.i.groupby('response_id').explicitly_recommended.sum()
        self.assertTrue((self.r.recommended_product_count==self.r.response_id.map(rc)).all())
        self.assertTrue((self.r.direct_recommendation==(self.r.recommended_product_count>0).astype(int)).all())
        for rid,g in self.i[self.i.explicitly_recommended==1].groupby('response_id'):
            ranks=sorted(int(x) for x in g.recommendation_rank)
            self.assertEqual(ranks,list(range(1,len(g)+1)))
            for it in g.itertuples():self.assertIn(f'Recommendation rank {int(it.recommendation_rank)}:',self.text[rid]['text'])
        for row in self.r.itertuples():
            self.assertEqual(int(row.single_best),int(bool(row.best_product_id)))
            if row.single_best:self.assertIn(row.best_product_id,self.i[(self.i.response_id==row.response_id)&(self.i.explicitly_recommended==1)].product_id.tolist())

    def test_10_decision_component_text(self):
        for row in self.r.itertuples():
            text=self.text[row.response_id]['text']
            self.assertEqual(row.comparison,int('should be compared' in text))
            self.assertEqual(row.prioritization,int('criterion-specific advantage' in text))
            self.assertEqual(row.single_best,int('my single overall choice is' in text))
            self.assertEqual(row.health_caution_present,int('individual medical advice' in text))
            expected=4 if row.single_best else 3 if row.direct_recommendation else 2 if row.prioritization else 1 if row.comparison else 0
            self.assertEqual(expected,row.highest_role)

    def test_11_source_citation_count(self):
        self.assertEqual(len(self.s),11575);self.assertEqual(int(self.s.citation_events.sum()),23111)
        self.assertEqual(self.s.source_domain.nunique(),28)
        counts=self.s.groupby('response_id').size()
        self.assertTrue((self.r.source_count==self.r.response_id.map(counts)).all())
        for src in self.s.itertuples():
            self.assertEqual(self.text[src.response_id]['text'].count('['+src.source_record_id+']'),src.citation_events)

    def test_12_coded_sources_have_no_url_fields(self):
        # Checks coded-archive consistency, NOT whether any original web publisher existed.
        self.assertFalse({'raw_url','canonical_url','normalization_rule'} & set(self.s.columns))
        self.assertEqual(set(self.s.source_domain),{f'SRC_{i:03d}' for i in range(1,29)})
        self.assertEqual(set(self.s.source_record_id),set(self.docs))
        for doc in self.docs.values():
            self.assertEqual(set(doc),{'source_record_id','availability','text'})
        for source in self.s.itertuples():
            self.assertRegex(source.source_domain,r'^SRC_\d{3}$')

    def test_13_claim_links_and_evidence(self):
        for c in self.f.itertuples():
            self.assertIn(c.claim_text,self.text[c.response_id]['text'])
            self.assertEqual(c.evidence_locator,'source_documents.jsonl#'+c.source_record_id)
            self.assertIn(c.source_record_id,self.docs)
        for c in self.c.itertuples():
            d=self.docs[c.source_record_id]
            self.assertEqual(d['availability']=='unavailable',c.support_label=='inaccessible')
            self.assertEqual(d['text']=='',c.support_label=='inaccessible')

    def test_14_stratified_support_sample(self):
        self.assertEqual(len(self.c),400)
        self.assertTrue((self.c.groupby(['category','system','wave']).size()==10).all())
        frame=self.f.groupby(['category','system','wave']).size()
        for row in self.c.itertuples():
            self.assertEqual(frame.loc[(row.category,row.system,row.wave)],row.stratum_size)
            self.assertAlmostEqual(row.inclusion_probability,10/row.stratum_size,places=12)
        self.assertEqual(self.c.support_label.value_counts().to_dict(),{'fully_supported':279,'partially_supported':64,'unsupported':29,'inaccessible':28})

    def test_15_label_units_and_final_decisions(self):
        self.assertEqual(self.labels.response_id.nunique(),600);self.assertEqual(len(self.labels),3000)
        self.assertTrue((self.labels.groupby('response_id').size()==5).all())
        parent=self.r.set_index('response_id')
        for row in self.labels.itertuples():self.assertEqual(row.final_label,parent.loc[row.response_id,row.field])
        distinct=self.labels[['response_id','query_id']].drop_duplicates()
        distinct['wave']=distinct.response_id.map(parent.wave)
        self.assertTrue((distinct.groupby(['query_id','wave']).size()==3).all())
        disagreements=read('label_disagreements.csv')
        self.assertEqual(len(disagreements),int((self.labels.label_A!=self.labels.label_B).sum()))

    def test_16_source_support_final_labels(self):
        source_labels=read('paired_source_labels.csv');support_labels=read('paired_support_labels.csv')
        self.assertEqual(len(source_labels),600);self.assertEqual(len(support_labels),400)
        s=self.s.set_index('source_record_id');c=self.c.set_index('link_id')
        st=['brand_manufacturer','retailer_marketplace','specialist_review','general_news','forum_social','institutional','other']
        sp=['fully_supported','partially_supported','unsupported','inaccessible']
        for row in source_labels.itertuples():self.assertEqual(row.final_label,st.index(s.loc[row.unit_id,'source_type']))
        for row in support_labels.itertuples():self.assertEqual(row.final_label,sp.index(c.loc[row.unit_id,'support_label']))

    def test_17_pair_definitions(self):
        self.assertEqual(self.pairs.contrast.value_counts().to_dict(),{'within_wave':2400,'between_wave':1920,'wording':1200})
        idx=self.r.set_index('response_id')
        for pair in self.pairs.itertuples():
            a=idx.loc[pair.response_A];b=idx.loc[pair.response_B]
            self.assertEqual(a.query_id,b.query_id);self.assertEqual(a.system,b.system)
            if pair.contrast=='within_wave':
                self.assertEqual(a.wave,b.wave);self.assertEqual(a.variant,b.variant);self.assertNotEqual(a.replicate,b.replicate)
            elif pair.contrast=='wording':
                self.assertEqual(a.wave,b.wave);self.assertEqual(a.replicate,b.replicate);self.assertNotEqual(a.variant,b.variant)
            else:
                self.assertEqual(b.wave-a.wave,1);self.assertEqual(a.variant,b.variant);self.assertEqual(a.replicate,b.replicate)

    def test_18_pair_bounds_and_denominators(self):
        for name in ['brand_jaccard','product_jaccard','family_jaccard','weighted_prefix','first_display_agreement','first_recommendation_agreement']:
            vals=self.pairs[name].dropna();self.assertTrue(vals.between(0,1).all())
        idx=self.r.set_index('response_id')
        ok=self.pairs.response_A.map(idx.direct_recommendation).eq(1)&self.pairs.response_B.map(idx.direct_recommendation).eq(1)
        self.assertTrue((self.pairs.first_recommendation_agreement.notna()==ok).all())

    def test_19_primary_effects_and_holm(self):
        results=pd.read_csv(OUT/'primary_contrasts.csv')
        for k,col in enumerate(['brand_count','product_count','direct_recommendation']):
            qm=self.r.groupby(['query_id','system'])[col].mean().unstack()
            diff=qm.B-qm.A
            self.assertAlmostEqual(diff.mean(),results.iloc[k].estimate,places=12)
            self.assertAlmostEqual(diff.mean()/diff.std(ddof=1),results.iloc[k].standardized_paired_d,places=12)
        self.assertTrue((results.clusters==40).all());self.assertTrue((results.df==39).all())
        np.testing.assert_allclose(audit.holm(results.p),results.p_holm,rtol=1e-10)

    def test_20_summary_and_hash_manifest(self):
        self.assertEqual(self.summary['responses'],len(self.r));self.assertEqual(self.summary['source_records'],len(self.s))
        self.assertEqual(self.summary['product_appearances'],len(self.i))
        for line in (OUT/'input_sha256.txt').read_text().splitlines():
            digest,name=line.split('  ',1)
            self.assertEqual(hashlib.sha256((DATA/name).read_bytes()).hexdigest(),digest)

    def test_21_relative_positions_are_not_calendar_timestamps(self):
        self.assertTrue((self.r.relative_day==7*(self.r.wave-1)).all())
        self.assertFalse({'capture_timestamp','acquired_at','recorded_at'} & set(self.r.columns))

class StatisticFunctionTests(unittest.TestCase):
    def test_22_jaccard(self):
        self.assertAlmostEqual(audit.jaccard(['x','y'],['y','z']),1/3)
        self.assertEqual(audit.jaccard(['x','x'],['x']),1)
        self.assertEqual(audit.jaccard([],['x']),0)
        self.assertTrue(np.isnan(audit.jaccard([],[])))
    def test_23_prefix(self):
        self.assertAlmostEqual(audit.prefix_overlap(['x','y'],['x','y']),1)
        self.assertEqual(audit.prefix_overlap(['x'],['y']),0)
        self.assertLess(audit.prefix_overlap(['x','y'],['y','x']),1)
        self.assertTrue(np.isnan(audit.prefix_overlap([],['x'])))
    def test_24_holm(self):np.testing.assert_allclose(audit.holm([.01,.04,.03]),[.03,.06,.06])
    def test_25_kappa(self):
        self.assertAlmostEqual(audit.kap_from_mat(np.array([[10,0],[0,10]])),1)
        self.assertAlmostEqual(audit.kap_from_mat(np.array([[5,5],[5,5]])),0)
        self.assertTrue(np.isnan(audit.kap_from_mat(np.array([[10,0],[0,0]]))))
        self.assertAlmostEqual(audit.kap_from_mat(np.eye(5,dtype=int)*10,weighted=True),1)
    def test_26_interval(self):
        m,lo,hi=audit.interval([3,3,3],np.random.default_rng(1))
        self.assertEqual((m,lo,hi),(3,3,3))
        self.assertTrue(all(np.isnan(x) for x in audit.interval([])))

if __name__=='__main__':unittest.main(verbosity=2)

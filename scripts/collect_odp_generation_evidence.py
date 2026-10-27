"""Verify current selected ODP-count/split components and collect report evidence."""
import argparse, hashlib, json, sys
from pathlib import Path
from dataclasses import replace
import numpy as np
import pandas as pd


def collect(project, report):
    sys.path.insert(0,str(project/'src'))
    from strategic_planner.models import Model, SalesOrderPosition, SimpleMassSplitModel
    from strategic_planner.data.feature_names import read_snapshot_parquet
    from strategic_planner.order_generation.mass_split_data import first_child_split_cases
    from strategic_planner.order_generation.count_classification import split_indices
    hashes={}
    def path(name):
        p=project/name; hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest();return p
    def meta(name):return json.loads(path(name).read_text())
    config=meta('configs/production_cascade_selected.json')
    cascade=Model.load_model(path(config['artifact']))
    count=cascade.components['count'];split=cascade.components['mass_split']
    # Confirm the embedded components match the separately selected artifacts.
    for name,filename in [('count','odv_count_mass_logistic_v2.spmodel'),('mass_split','odv_mass_split_distance_beta_v2.spmodel')]:
        separate=Model.load_model(path('outputs/models/'+filename))
        assert str(separate.to_state())==str(cascade.components[name].to_state())
    frames={n:read_snapshot_parquet(path(f'data/interim/{n}_260915.parquet')) for n in ['odv','odp','consuntivi']}
    cases=first_child_split_cases(frames['odv'],frames['odp'],frames['consuntivi'])
    reference=meta('outputs/analysis/odp_count_classification_20261021/summary.json')
    indices=split_indices(cases,reference['split_keys'])
    eligible={k:cases.iloc[v].query('observed_count in [1,2]').copy() for k,v in indices.items()}
    train,val=eligible['train'],eligible['validation']
    positions=[SalesOrderPosition(float(q)) for q in val.quantita_odv_kg]
    predictions=count.predict_batch(positions)
    truth=val.observed_count.to_numpy(int)
    rows=[]
    for name,pred in [('Sempre un ODP',np.ones(len(val),int)),('Regola dei 93 t',1+(val.quantita_odv_kg.to_numpy()>93000)),('Regressione logistica bilanciata',predictions)]:
        cm=np.array([[int(((truth==i)&(pred==j)).sum()) for j in [1,2]] for i in [1,2]])
        recall=cm.diagonal()/cm.sum(axis=1)
        rows.append(dict(model=name,accuracy=100*float((truth==pred).mean()),balanced_accuracy=100*float(recall.mean()),recall_two=100*recall[1],confusion=cm.tolist()))
    expected=meta('outputs/analysis/selected_refit_zero_duration_v2/summary.json')['count_validation']
    assert rows[-1]['confusion']==expected['confusion_true_rows_pred_columns']
    pd.DataFrame([{k:v for k,v in r.items() if k!='confusion'} for r in rows]).to_csv(report/'tables/data/odp-count-comparison.csv',index=False)
    # Reproduce validation against the current ready quantities, without refitting.
    two=val[val.observed_count.eq(2)].copy()
    original=pd.read_csv(path('outputs/analysis/first_child_beta_split_20261023/validation_predictions.csv'),dtype={'odv':str,'posizione_odv':str})
    original=original[original.model.eq('beta')]
    checked=two.merge(original[['odv','posizione_odv','first_share']],on=['odv','posizione_odv'],suffixes=('','_previous'),validate='one_to_one')
    assert len(checked)==len(two)
    np.testing.assert_allclose(checked.first_share,checked.first_share_previous,rtol=0,atol=1e-12)
    constant=meta('outputs/analysis/first_child_beta_split_20261023/summary.json')['parameters']
    a,b=constant['alpha'],constant['beta']
    state=split.to_state()
    models={'Ripartizione a metà':SimpleMassSplitModel(replace(state,kind='equal',coefficients=(.5,))), 'Beta costante':SimpleMassSplitModel(replace(state,kind='beta',coefficients=(float(np.log(a/b)),),log_precision=float(np.log(a+b)))), 'Beta dipendente dalla quantità':split}
    q=two.quantita_odv_kg.to_numpy(float); y=two.first_share.to_numpy(float)
    split_rows=[]
    for name,model in models.items():
        lo=model.predict_quantile(q,.05);hi=model.predict_quantile(q,.95)
        split_rows.append(dict(model=name,mae_median_pp=100*float(np.abs(y-model.predict_quantile(q,.5)).mean()),mae_mean_pp=100*float(np.abs(y-model.predict_mean_share(q)).mean()),crps_pp=100*float(model.crps(q,y).mean()),coverage90=100*float(((y>=lo)&(y<=hi)).mean()) if model.probabilistic else None))
    pd.DataFrame(split_rows).to_csv(report/'tables/data/odp-split-comparison.csv',index=False)
    grid=np.linspace(float(q.min()),float(q.max()),301)
    pd.DataFrame(dict(quantity_kg=grid,mean=split.predict_mean_share(grid),low=split.predict_quantile(grid,.05),high=split.predict_quantile(grid,.95))).to_csv(report/'figures/data/odp-split-band.csv',index=False)
    two[['odv','posizione_odv','quantita_odv_kg','first_share']].to_csv(report/'figures/data/odp-split-validation.csv',index=False)
    # A real validation request, actually split into two and predicted as two.
    two['predicted_count']=count.predict_batch([SalesOrderPosition(float(q)) for q in two.quantita_odv_kg])
    row=two[two.predicted_count.eq(2)].assign(distance=lambda d:(d.quantita_odv_kg-100000).abs()).sort_values(['distance','odv','posizione_odv']).iloc[0]
    rng=np.random.default_rng(42);quantity=float(row.quantita_odv_kg)
    masses=split.sample((quantity,2),rng)
    position=SalesOrderPosition(quantity,row.to_dict())
    features=cascade.components['direct_mapper'].sample(position,rng)
    features.update(cascade.components['lookups'].sample(position,rng).as_dict())
    assert np.isclose(sum(masses),quantity) and min(masses)>0
    example=dict(odv=row.odv,posizione_odv=row.posizione_odv,requested_kg=quantity,observed_odp=[row.first_odp,row.second_odp],observed_ready_kg=[float(row.first_observed_kg),float(row.second_observed_kg)],generated_kg=masses,generated_features=features,seed=42)
    summary=dict(sources_sha256=hashes,positions=len(cases),counts={int(k):int(v) for k,v in cases.observed_count.value_counts().sort_index().items()},split_positions={k:len(v) for k,v in eligible.items()},split_odv={k:v.odv.nunique() for k,v in eligible.items()},two_odp_training=int(train.observed_count.eq(2).sum()),count_results=rows,split_results=split_rows,mean_share=float(split.predict_mean_share([93000])[0]),example=example,direct_mappings=cascade.components['direct_mapper'].to_state().field_mappings,notes=['Count predictions are argmax of class-balanced, uncalibrated scores.','Split median is used for the tabulated MAE; deterministic cascade uses the mean.','Only validation is evaluated; test remains unused.','Example samples the split then lookups with seed 42, using the observed sales context.'])
    (report/'tables/data/odp-generation-summary.json').write_text(json.dumps(summary,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x))+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['sources_sha256','direct_mappings','notes']},indent=2,default=str))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-dir',type=Path,required=True);p.add_argument('--report-dir',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();collect(a.project_dir.resolve(),a.report_dir.resolve())

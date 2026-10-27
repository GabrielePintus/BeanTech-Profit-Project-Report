"""Collect section 4.3 evidence from saved audits, without fitting or editing source data.

Usage: python scripts/collect_duration_evidence.py --project-dir ../StrategicPlannerBeanTech
"""
from pathlib import Path
import argparse, hashlib, json, zipfile
import numpy as np
import pandas as pd

def collect(project, report):
    sources={}
    def read(relative):
        path=project/relative
        sources[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
        return pd.read_parquet(path)
    def meta(relative):
        path=project/relative
        sources[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
        return json.loads(path.read_text())
    base='data/interim/'
    before=read(base+'duration_components_audit_260915.parquet')
    final=read(base+'consuntivi_260915.parquet')
    corrections=read(base+'statistical_duration_corrections_260915.parquet')
    expected=read(base+'expected_duration_imputations_260915.parquet')
    decisions=read(base+'statistical_duration_decisions_260915.parquet')
    means=read(base+'statistical_duration_means_260915.parquet')
    thresholds=pd.concat([read(base+'statistical_duration_thresholds_260915.parquet'),
                          read(base+'expected_duration_thresholds_260915.parquet')],ignore_index=True)
    thresholds=thresholds[thresholds.method.eq('MAD')].copy()
    assert corrections.applicata.all() and expected.applicata.all()
    paired=corrections[['operazione_id','odp','odv','posizione_odv','macro_fase','durata_totale_min','durata_totale_min_corretta']].rename(columns={'durata_totale_min':'before_minutes','durata_totale_min_corretta':'after_minutes'})
    paired=pd.concat([paired,expected[['operazione_id','odp','odv','posizione_odv','macro_fase','durata_originale_min','durata_corretta_min']].rename(columns={'durata_originale_min':'before_minutes','durata_corretta_min':'after_minutes'})],ignore_index=True)
    assert paired.operazione_id.is_unique
    old=before.set_index('operazione_id'); new=final.set_index('operazione_id')
    np.testing.assert_allclose(paired.before_minutes,old.loc[paired.operazione_id,'durata_totale_min'],rtol=0,atol=1e-8)
    np.testing.assert_allclose(paired.after_minutes,new.loc[paired.operazione_id,'durata_totale_min'],rtol=0,atol=1e-8)
    reference=[]
    for row in thresholds.itertuples():
        frame=before[before.macro_fase.eq(row.phase)]
        positive=frame[frame.durata_totale_min.gt(0)]
        flags=(positive.durata_totale_min.lt(min(row.lower_minutes,row.lower_outer_ci95_minutes)) |
               positive.durata_totale_min.gt(max(row.upper_minutes,row.upper_outer_ci95_minutes)))
        assert len(positive)==row.positive
        assert set(positive.loc[flags,'operazione_id'])==set(paired.loc[paired.macro_fase.eq(row.phase),'operazione_id'])
        values=positive.loc[~flags,'durata_totale_min'].astype(float)
        if row.phase in set(means.macro_fase):
            np.testing.assert_allclose(values.mean(),means.loc[means.macro_fase.eq(row.phase),'media_minuti'].item())
        quantiles=values.quantile([.05,.25,.5,.75,.95])
        reference.append({'phase':row.phase,'n':len(values),'p05':quantiles.loc[.05],'p25':quantiles.loc[.25],'median':quantiles.loc[.5],'p75':quantiles.loc[.75],'p95':quantiles.loc[.95]})
    training='outputs/analysis/duration_correction_training_v3/'
    manifest=meta(training+'manifest.json')
    model_manifest=meta('outputs/models/duration_corrections_v3/manifest.json')
    prior=read(base+'duration_corrections_260915.parquet')
    assert set(prior.modello_sha256.dropna())=={model_manifest['models_sha256']}
    model_path=project/'outputs/models/duration_corrections_v3/models.joblib'
    digest=hashlib.sha256(model_path.read_bytes()).hexdigest()
    assert digest==model_manifest['models_sha256']
    sources[str(model_path.relative_to(project))]=digest
    metrics=read(training+'metriche_controlli.parquet')
    selected=metrics[metrics.selezionato].copy()
    control=read(training+'predizioni_controlli.parquet')
    # The saved held-out metrics are paired with the exact model checksum used by the pipeline.
    for row in selected.itertuples():
        subset=control[control.macro_fase.eq(row.macro_fase)&control.modello.eq(row.modello)]
        assert len(subset)==row.n_test
        np.testing.assert_allclose((subset.durata_totale_min-subset.predizione_min).abs().mean(),row.MAE_min)
        np.testing.assert_allclose(subset.dentro_90.mean(),row.copertura_test_90)
    selected[['macro_fase','modello','n_train','n_cal','n_test','MAE_min','copertura_test_90','raggio_log_90']].to_csv(report/'figures/data/duration-correction-validation.csv',index=False)
    target=set(manifest['odv_groups']['target'])
    applied=prior[prior.azione.isin(['troncamento','imputazione'])]
    overlaps={name:sorted(set(applied.odv)&set(manifest['odv_groups'][name])) for name in ['training','calibration','test']}
    lfc=meta('outputs/analysis/tratt_lfc_outlier_imputation_v1/summary.json')
    path=project/'outputs/analysis/tratt_lfc_outlier_imputation_v1/imputer.spmodel'
    sources[str(path.relative_to(project))]=hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as z: state=json.loads(z.read('state.json'))
    assert state['model_metadata']['attributes']['training_operations']==lfc['training_operations']
    example=expected.iloc[0]
    assert example.odp==lfc['odp']
    np.testing.assert_allclose(example.durata_corretta_min,np.exp(lfc['log_location']+.5*lfc['log_scale']**2))
    total_before=float(paired.before_minutes.sum()); total_after=float(paired.after_minutes.sum())
    result={'sources_sha256':sources,'candidate_occurrences':len(paired),'candidate_odp':paired.odp.nunique(),
            'candidate_positions':len(paired[['odv','posizione_odv']].drop_duplicates()),'candidate_odv':paired.odv.nunique(),
            'before_total_minutes':total_before,'after_total_minutes':total_after,
            'whole_dataset_before_total_minutes':float(before.durata_totale_min.sum()),
            'positive_corrections_only_delta_minutes':total_after-total_before,
            'graphs_with_fewer_branches':int(decisions.rami_ridotti.sum()),
            'graphs_without_previous_implicit_ready':int(decisions.pronto_implicito_rimosso.sum()),
            'means':means.to_dict('records'),
            'correction_model_split_odv':{k:len(v) for k,v in manifest['odv_groups'].items()},
            'applied_correction_odv_in_reference_groups':overlaps,
            'lfc_example':lfc,
            'notes':['Before values come from duration_components_audit, preceding positive-duration corrections.',
                     'Only positive-duration correction effects are measured here; zero-duration imputations are a separate stage.',
                     'Model verification uses the stored v3 metrics and the SHA-256 found in the current duration correction audit.',
                     'One ODV with an applied temporal correction also occurs in the recorded training split.']}
    for name,frame in [('statistical-duration-thresholds',thresholds),('statistical-duration-paired',paired),('statistical-duration-reference',pd.DataFrame(reference))]:
        frame.to_csv(report/f'figures/data/{name}.csv',index=False)
    (report/'tables/data/statistical-duration-summary.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps({k:result[k] for k in ['candidate_occurrences','candidate_odp','candidate_positions','candidate_odv','graphs_with_fewer_branches','graphs_without_previous_implicit_ready','applied_correction_odv_in_reference_groups']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir',type=Path,required=True)
    parser.add_argument('--report-dir',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args(); collect(args.project_dir.resolve(),args.report_dir.resolve())

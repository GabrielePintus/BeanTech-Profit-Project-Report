"""Verify selected VAEAC evidence and generate a reproducible conditional example."""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch


def collect(project, report):
    sys.path.insert(0,str(project/'src'))
    from strategic_planner.models import Model
    hashes={}
    def path(name):
        p=project/name; hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest(); return p
    def meta(name): return json.loads(path(name).read_text())
    selected=meta('configs/odv_feature_distribution_selected.json')
    comparison=meta('outputs/evaluation/vaeac_mass_required_v2/comparison.json')
    split=meta('configs/splits/odv_features_complete_families_v2.json')
    data=pd.read_parquet(path('data/processed/feature_distribution/odv_complete_families_v2.parquet'))
    previous=pd.read_parquet(path('data/processed/feature_distribution/odv_complete_families_v1.parquet'))
    features=comparison['protocol']['physical_features']
    pd.testing.assert_frame_equal(data[['odv','posizione_odv',*features]],previous[['odv','posizione_odv',*features]])
    assert not (set(split['groups']['train'])&set(split['groups']['validation']))
    train=data[data.odv.isin(split['groups']['train'])]
    validation=data[data.odv.isin(split['groups']['validation'])]
    assert len(train)==selected['train_positions'] and len(validation)==selected['validation_positions']
    assert len(train)+len(validation)==len(data)
    best=comparison['models']['previous-arbitrary-model-mass-observed']
    alternative=comparison['models']['mass-required-v2-best']
    model=Model.load_model(project/selected['artifact'])
    assert model.required_feature_names==tuple(selected['required_conditioning_features'])
    assert hashlib.sha256(path(selected['artifact']).read_bytes()).hexdigest()==selected['artifact_sha256']
    # The published comparison uses equivalent weights on identical physical data.
    ckpt=torch.load(path(best['checkpoint']),map_location='cpu',weights_only=False)
    assert set(ckpt['state_dict'])==set(model.network.state_dict())
    for name,tensor in model.network.state_dict().items():
        assert torch.equal(tensor.cpu(),ckpt['state_dict'][name]), name
    score_difference=alternative['joint_nll_per_target']-best['joint_nll_per_target']
    np.testing.assert_allclose(score_difference,-comparison['pairwise'][0]['nll_improvement_nats_per_target'])
    by_feature=pd.DataFrame([dict(feature=k,**v) for k,v in best['by_feature'].items() if v['targets']])
    np.testing.assert_allclose(by_feature.dummy_nll-by_feature.nll,by_feature.skill_nats)
    cats=by_feature[by_feature.kind.eq('categorical')]
    np.testing.assert_allclose(np.average(cats.accuracy,weights=cats.targets),best['categorical_accuracy'],atol=1e-7)
    # Reproduce the exact physical masks and categorical eligibility used in the comparison.
    import yaml
    from types import SimpleNamespace
    from strategic_planner.feature_distribution.neural.data import TabularFeatureDataModule
    from strategic_planner.feature_distribution.neural.evaluation import (
        _physical_availability, _physical_features, make_physical_conditioning_masks,
    )
    assert all(v['data_config']==best['data_config'] for v in comparison['models'].values())
    args=dict(yaml.safe_load(path(best['data_config']).read_text())['data'])
    for name in ['data_path','split_manifest_path']:
        args[name]=str(project/args[name])
    args.update(num_workers=0,pin_memory=False)
    dm=TabularFeatureDataModule(**args);dm.setup('fit')
    categorical,numeric=_physical_features(dm.metadata)
    assert list(categorical+numeric)==features
    categorical_index={name:i for i,name in enumerate(dm.metadata.categorical_features)}
    candidate=SimpleNamespace(datamodule=dm,categorical_index=categorical_index,
        continuous_index={name:i for i,name in enumerate(dm.metadata.continuous_features)},
        indicator_index={name:categorical_index[indicator] for name,indicator in dm.metadata.special_numeric_indicators.items()})
    available=_physical_availability(candidate,'validation',tuple(features))
    protocol=comparison['protocol']
    condition=make_physical_conditioning_masks(available,seed=protocol['seed'],
        observed_fraction=protocol['observed_fraction'],
        required_indices=[features.index(name) for name in protocol['required_observed_features']])
    hidden=available & ~condition
    raw_train=previous.iloc[dm._datasets['train'].row_indices.numpy()]
    raw_validation=previous.iloc[dm._datasets['validation'].row_indices.numpy()]
    assert set(raw_train.odv)==set(train.odv)
    assert set(raw_validation.odv)==set(validation.odv)
    baseline=[]
    for j,name in enumerate(categorical):
        counts=raw_train[name].astype('string').value_counts(dropna=True)
        tied=sorted(str(x) for x in counts.index[counts.eq(counts.max())])
        prediction=tied[0]
        truth=raw_validation[name].astype('string').to_numpy()[hidden[:,j]]
        expected=best['by_feature'][name]
        assert len(truth)==expected['targets']
        probabilities=np.array([(float(counts.get(value,0))+.5)/(counts.sum()+.5*len(counts)) for value in truth])
        np.testing.assert_allclose(-np.log(probabilities).mean(),expected['dummy_nll'],atol=1e-10)
        correct=int((truth==prediction).sum())
        baseline.append(dict(feature=name,predicted_category=prediction,training_mode_count=int(counts.max()),
            tied_modes=len(tied),targets=len(truth),correct=correct,accuracy=correct/len(truth)))
    baseline=pd.DataFrame(baseline)
    baseline_accuracy=float(baseline.correct.sum()/baseline.targets.sum())
    assert baseline.targets.sum()==cats.targets.sum()
    assert hidden.sum()==by_feature.targets.sum()
    baseline.to_csv(report/'tables/data/feature-generation-baseline-accuracy.csv',index=False)
    by_feature.to_csv(report/'figures/data/feature-generation-scores.csv',index=False)
    row=validation.sort_values(['odv','posizione_odv']).iloc[0]
    context={k:row[k] for k in ['quantita_odv_kg','forma','descrizione_marca_acciaio']}
    samples=model.sample_frame(context,rng=np.random.default_rng(42),n_samples=4,batch_size=4)
    for name,value in context.items(): assert samples[name].eq(value).all()
    for name,value in selected['constant_features'].items(): assert samples[name].eq(value).all()
    columns=[*context,'dimensione_1_mm','lunghezza_richiesta','stato_fisico']
    samples[columns].to_csv(report/'tables/data/feature-generation-example.csv',index=False)
    results=[dict(model='Marginali indipendenti',score=best['dummy_nll_per_target'],accuracy=100*baseline_accuracy),dict(model='VAEAC, quantità sempre nota in addestramento',score=alternative['joint_nll_per_target'],accuracy=100*alternative['categorical_accuracy']),dict(model='VAEAC selezionato',score=best['joint_nll_per_target'],accuracy=100*best['categorical_accuracy'])]
    pd.DataFrame(results).to_csv(report/'tables/data/feature-generation-comparison.csv',index=False)
    summary=dict(baseline_accuracy=dict(correct=int(baseline.correct.sum()),targets=int(baseline.targets.sum()),accuracy=baseline_accuracy,rule="Most frequent training category per feature; lexicographic tie break; same hidden known-category targets as VAEAC"),sources_sha256=hashes,selected_weights_equal_evaluated_checkpoint=True,physical_data_equal_evaluation_data=True,train_positions=len(train),train_odv=train.odv.nunique(),validation_positions=len(validation),validation_odv=validation.odv.nunique(),physical_feature_count=len(features),categorical_target_count=int(cats.targets.sum()),hidden_target_count=int(by_feature.targets.sum()),protocol=comparison['protocol'],results=results,score_difference=score_difference,difference_ci95=[-x for x in reversed(comparison['pairwise'][0]['improvement_95_ci'])],gain_over_independent=best['skill_nats_per_target'],gain_ci95=best['skill_nats_95_ci'],example_context=context,example_source_position={k:row[k] for k in ['odv','posizione_odv']},example_sampling=dict(seed=42,batch_size=4,device='cpu',draws=4),notes=['No independent test set. Model selection and evaluation share validation.', 'Joint score is not the mean of the per-feature marginal scores in the plot.', 'Example values are generated, not observed production records.'])
    (report/'tables/data/feature-generation-summary.json').write_text(json.dumps(summary,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x))+'\n')
    print(json.dumps({k:summary[k] for k in ['train_positions','train_odv','validation_positions','validation_odv','hidden_target_count','baseline_accuracy','results','difference_ci95']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir',type=Path,required=True)
    parser.add_argument('--report-dir',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args();collect(args.project_dir.resolve(),args.report_dir.resolve())

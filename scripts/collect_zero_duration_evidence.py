"""Collect and verify section 4.4 evidence without changing the source dataset."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd


def collect(project, report):
    sys.path.insert(0, str(project / 'src'))
    from strategic_planner.data.zero_duration import imputer_features, sample_durations
    from strategic_planner.data.feature_names import rename_features
    hashes = {}
    def read(name):
        path = project / name
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return pd.read_parquet(path)
    def meta(name):
        path = project / name
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return json.loads(path.read_text())
    audit = read('data/interim/zero_duration_imputations_260915.parquet').sort_values('operazione_id')
    final = read('data/interim/consuntivi_260915.parquet')
    master = read('data/interim/odp_260915.parquet')
    sales = read('data/interim/odv_260915.parquet')
    policy = meta('data/rules/zero_duration_imputation.json')
    model_dir = project / policy['model_directory']
    for name, expected in policy['models'].items():
        path = model_dir / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected
        hashes[str(path.relative_to(project))] = actual
    training = meta('outputs/analysis/additional_duration_distributions_v1/metadata.json')
    for name in ['antimix.cbm', 'conf.joblib']:
        assert hashlib.sha256((project/'outputs/analysis/additional_duration_distributions_v1'/name).read_bytes()).hexdigest() == policy['models'][name]
    features = imputer_features(rename_features(final, 'consuntivi'), rename_features(master, 'odp'), rename_features(sales, 'odv'))
    selected = features.set_index('operazione_id').loc[audit.operazione_id].reset_index()
    durations, clock, strong, probability = sample_durations(selected, audit.tempo_disponibile_min.to_numpy(), policy, model_dir)
    np.testing.assert_allclose(durations, audit.durata_imputata_min, rtol=0, atol=1e-8)
    np.testing.assert_array_equal(clock, audit.durata_timestamp_non_vincolanti)
    np.testing.assert_array_equal(strong, audit.durata_forte_condizionamento_temporale)
    np.testing.assert_allclose(probability, audit.probabilita_finestra, rtol=1e-8, atol=1e-12)
    keyed = final.set_index('operazione_id').loc[audit.operazione_id]
    np.testing.assert_allclose(keyed.durata_totale_min, durations, rtol=0, atol=1e-8)
    assert (keyed.data_ora_fine_calcolata.to_numpy() == audit.fine_calcolata_imputata.to_numpy()).all()
    assert audit.durata_originale_min.eq(0).all()
    assert final.loc[final.macro_fase.isin(policy['phases']), 'durata_totale_min'].gt(0).all()
    distributions, counts = [], []
    for phase in policy['phases']:
        a = audit[audit.macro_fase.eq(phase)]
        reference = final[final.macro_fase.eq(phase) & ~final.operazione_id.isin(audit.operazione_id)].durata_totale_min
        assert reference.gt(0).all()
        for group, values in [('positive_reference', reference), ('imputed', a.durata_imputata_min)]:
            q = values.quantile([.05,.25,.5,.75,.95])
            distributions.append(dict(phase=phase, group=group, n=len(values), p05=q.loc[.05], p25=q.loc[.25], median=q.loc[.5], p75=q.loc[.75], p95=q.loc[.95]))
        counts.append(dict(phase=phase, imputed=len(a), time_relaxed=int(a.durata_timestamp_non_vincolanti.sum()), strongly_conditioned=int(a.durata_forte_condizionamento_temporale.sum()), median=float(a.durata_imputata_min.median())))
    example = audit[audit.odp.eq('000010874347') & audit.macro_fase.eq('ANTIMIX')].iloc[0]
    assert np.isclose(example.tempo_disponibile_min,13)
    result = dict(sources_sha256=hashes, occurrences=len(audit), odp=audit.odp.nunique(), odv=audit.odv.nunique(), positions=len(audit[['odv','posizione_odv']].drop_duplicates()), time_relaxed=int(clock.sum()), strongly_conditioned=int(strong.sum()), by_phase=counts, training=training['parameters'], example=example.to_dict(), notes=['Reference boxes contain durations already positive before zero imputation, including earlier temporal corrections.', 'Regenerated all imputations from frozen models, seed, current mass features and saved time windows; all match the audit and final parquet.'])
    (report/'tables/data/zero-duration-summary.json').write_text(json.dumps(result, indent=2, default=str)+'\n')
    pd.DataFrame(distributions).to_csv(report/'figures/data/zero-duration-distributions.csv',index=False)
    pd.DataFrame(counts).to_csv(report/'tables/data/zero-duration-counts.csv',index=False)
    print(json.dumps({k:result[k] for k in ['occurrences','odp','odv','positions','time_relaxed','strongly_conditioned','by_phase']}, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', type=Path, required=True)
    parser.add_argument('--report-dir', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    collect(args.project_dir.resolve(),args.report_dir.resolve())

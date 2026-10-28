"""Verify selected duration predictions on current data; never refit or evaluate test ODV."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import logistic, norm


def collect(project, report, output):
    sys.path.insert(0, str(project / 'src'))
    from strategic_planner.data.feature_names import read_snapshot_parquet
    from strategic_planner.data.zero_duration import imputer_features
    from strategic_planner.models import Model
    from strategic_planner.models.duration import OperationDurationInput

    hashes = {}
    def source(name):
        path = project / name
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    selected = json.loads(source('configs/production_cascade_selected.json').read_text())
    model = Model.load_model(source(selected['sources']['duration']))
    assert hashes[selected['sources']['duration']] == selected['source_sha256'][selected['sources']['duration']]
    cascade = Model.load_model(source(selected['artifact']))
    state = model.to_state()
    meta, arrays = state.to_metadata_and_arrays()
    embedded_meta, embedded_arrays = cascade.components['duration'].to_state().to_metadata_and_arrays()
    assert meta == embedded_meta and arrays.keys() == embedded_arrays.keys()
    for name in arrays:
        np.testing.assert_array_equal(arrays[name], embedded_arrays[name])

    manifest = json.loads(source(selected['evaluation_split']).read_text())
    groups = {k: {str(x[0]) for x in v} for k, v in manifest['split_keys'].items()}
    for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
        assert not groups[a] & groups[b]
    frames = [read_snapshot_parquet(source(f'data/interim/{n}_260915.parquet')) for n in ('consuntivi', 'odp', 'odv')]
    with np.errstate(divide='ignore', invalid='ignore'):
        data = imputer_features(*frames)
    data = data[data.macro_fase.isin(model.modelled_phases) & data.durata_totale_minuti.gt(0)].copy()
    data['observed'] = ~data.durata_zero_imputata.fillna(False) & ~data.durata_imputata_statisticamente.fillna(False)
    train = data[data.odv.isin(groups['train'])]
    validation = data[data.odv.isin(groups['validation']) & data.observed].copy()
    means = train[train.observed].groupby('macro_fase').durata_totale_minuti.mean()

    def evaluate(value):
        mu, scale = model.log_parameters(value)
        location = state.residual_locations.get(value.macro_phase, 0.)
        law = logistic(loc=location, scale=scale) if state.residual_distributions.get(value.macro_phase) == 'logistic' else norm(loc=location, scale=scale)
        lo, hi = np.exp(mu + law.ppf([.025, .975])) if scale else (np.nan, np.nan)
        return dict(predicted_minutes=60 * model.predict(value), lower95_minutes=lo, upper95_minutes=hi)

    rows = []
    for row in validation.to_dict('records'):
        value = OperationDurationInput(row['macro_fase'], row['quantita_kg'], row)
        rows.append(dict(odv=row['odv'], odp=row['odp'], operation_id=row['operazione_id'], phase=row['macro_fase'], actual_minutes=row['durata_totale_minuti'], baseline_minutes=means[row['macro_fase']], **evaluate(value)))
    predictions = pd.DataFrame(rows)
    old = pd.read_csv(source('outputs/analysis/phase_durations_zero_imputed_v4/validation_predictions.csv'), dtype={'odp': str, 'odv': str})
    extension = pd.read_csv(source('outputs/analysis/tratt_lfc_duration_v2/validation_predictions.csv'), dtype={'odp': str, 'odv': str})
    old = pd.concat([old, extension[extension.model.eq('ridge')].assign(phase='TRATT_LFC')]).sort_values(['odp', 'phase', 'actual_minutes']).reset_index(drop=True)
    current = predictions.sort_values(['odp', 'phase', 'actual_minutes']).reset_index(drop=True)
    pd.testing.assert_frame_equal(old[['odv', 'odp', 'phase']], current[['odv', 'odp', 'phase']])
    for name in ['actual_minutes', 'predicted_minutes']:
        np.testing.assert_allclose(current[name], old[name], rtol=1e-10, atol=1e-8)
    for name in ['lower95_minutes', 'upper95_minutes']:
        # Saved TRATT_LFC intervals use rounded 1.96 rather than the exact normal quantile.
        for phase, tolerance in [('TRATT_LFC', 2e-5), ('other', 1e-10)]:
            mask = current.phase.eq('TRATT_LFC') if phase == 'TRATT_LFC' else current.phase.ne('TRATT_LFC')
            np.testing.assert_allclose(current.loc[mask, name], old.loc[mask, name], rtol=tolerance, atol=1e-8, equal_nan=True)
    metrics = []
    for phase in ['TRENOLUNA', 'BANCHI', 'ANTIMIX', 'TAG', 'RADDR', 'CONF', 'CIRCO', 'TRATT_LUNA', 'TRATT_LFC', 'MOL']:
        t = train[train.macro_fase.eq(phase)]; v = predictions[predictions.phase.eq(phase)]
        probabilistic = phase in state.log_scales
        metrics.append(dict(phase=phase, training=len(t), training_observed=int(t.observed.sum()), training_imputed=int((~t.observed).sum()), validation=len(v), mae_minutes=float(abs(v.actual_minutes-v.predicted_minutes).mean()) if len(v) else None, baseline_mae_minutes=float(abs(v.actual_minutes-v.baseline_minutes).mean()) if len(v) else None, coverage95=float(((v.actual_minutes>=v.lower95_minutes)&(v.actual_minutes<=v.upper95_minutes)).mean()) if len(v) and probabilistic else None, fixed_minutes=float(np.exp(state.intercepts[phase])) if not probabilistic else None))

    graph_path = report/'tables/data/graph-generation-summary.json'
    example = json.loads(graph_path.read_text())['example_candidates'][0]
    account = example['prediction']['accounting']; rng = np.random.default_rng(42)
    exrows = []
    for i, node in enumerate(example['prediction']['structure']['nodes']):
        if not model.supports_phase(node['phase']):
            assert node['phase'] == 'PRONTO'
            continue
        mass = account['entering_kg'][i]
        features = {**example['context'], 'scrap_fraction': account['scrap_kg'][i]/mass, 'relative_mass': mass/example['prediction']['initial_mass_kg']}
        value = OperationDurationInput(node['phase'], mass, features)
        exrows.append(dict(phase=node['phase'], mass_kg=mass, **evaluate(value), sampled_minutes=60*model.sample(value, rng)))
    summary = dict(sources_sha256=hashes, training_operations=len(train), training_observed=int(train.observed.sum()), training_imputed=int((~train.observed).sum()), validation_operations=len(validation), validation_orders=int(validation.odp.nunique()), validation_sales_orders=int(validation.odv.nunique()), saved_predictions_reproduced=len(predictions), metrics=metrics, example=dict(odp=example['odp'], odv=example['odv'], position=example['posizione_odv'], graph_evidence_sha256=hashlib.sha256(graph_path.read_bytes()).hexdigest(), seed=42, durations=exrows), notes=['Frozen standalone duration state equals embedded selected cascade state.', 'Predictions and eligible observed targets reproduced against current canonical parquet, not historical data.', 'Baseline uses only non-statistically-imputed positive training targets consistently for all phases; TRATT_LFC baseline therefore differs slightly from its saved report.', 'Observed selection excludes durata_zero_imputata and durata_imputata_statisticamente. Earlier temporal adjustments are not separately filtered.', 'Frozen imputers use different ODV splits; this is a component diagnostic, not an independent evaluation of the complete treatment pipeline.', 'No training, source edits or test predictions.'])
    output.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output/'duration-generation-validation.csv', index=False)
    pd.DataFrame(metrics).to_csv(output/'duration-generation-metrics.csv', index=False)
    pd.DataFrame(exrows).to_csv(output/'duration-generation-example.csv', index=False)
    (output/'duration-generation-summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    print(pd.DataFrame(metrics).to_string(index=False))
    print(json.dumps(summary['example'], indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir', type=Path, required=True)
    parser.add_argument('--report-dir', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    collect(args.project_dir.resolve(), args.report_dir.resolve(), args.output_dir or args.report_dir/'tables/data')

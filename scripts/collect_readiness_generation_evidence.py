"""Verify the selected deadline distribution and its fitting cohort on current data."""
import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import gamma


def collect(project, output):
    sys.path.insert(0, str(project/'src'))
    from strategic_planner.models import Model
    from strategic_planner.data.feature_names import read_snapshot_parquet
    from strategic_planner.models.readiness_cleaning import logical_date_flags, fit_mad_limits, apply_mad_limits

    hashes = {}
    def source(relative):
        path = project/relative
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path
    selected = json.loads(source('configs/production_cascade_selected.json').read_text())
    config = json.loads(source('configs/readiness_margin_selected.json').read_text())
    original = json.loads(source('outputs/analysis/readiness_gamma_v1/summary.json').read_text())
    model = Model.load_model(source(selected['sources']['readiness_margin']))
    assert hashes[selected['sources']['readiness_margin']] == selected['source_sha256'][selected['sources']['readiness_margin']]
    cascade = Model.load_model(source(selected['artifact']))
    assert model.to_state().to_metadata_and_arrays() == cascade.components['readiness_margin'].to_state().to_metadata_and_arrays()
    state = model.to_state()
    assert state.shape == config['shape'] and state.scale_days == config['scale_days']

    sales, orders, ops = [read_snapshot_parquet(source(f'data/interim/{name}_260915.parquet')) for name in ('odv', 'odp', 'consuntivi')]
    for name, digest in original['source_sha256'].items():
        assert hashes[name] == digest, f'Changed fitting snapshot: {name}'
    keys = ['odv', 'posizione_odv']
    assert not sales.duplicated(keys).any()
    assert sales.posizione_odv_completa_dopo_filtro.fillna(False).all()
    counts = orders.groupby(keys).size().rename('actual_children')
    data = sales.merge(counts, on=keys, validate='one_to_one')
    assert data.actual_children.eq(data.numero_odp_posizione_odv_prima_filtro).all()
    starts = ops[ops.macro_fase.eq('TRENOLUNA')].groupby(keys).data_ora_inizio_registrata.min()
    data = data.merge(starts.rename('production_start'), on=keys, validate='one_to_one')
    for field in ['data_approntamento_confermata', 'data_uscita_merci_confermata', 'data_consegna_confermata']:
        raw = data[field]
        data[field] = pd.to_datetime(raw.mask(raw.astype('string').str.startswith('9999-', na=False)), errors='coerce').astype('datetime64[ns]')
    data['margin_days'] = (data.data_approntamento_confermata - data.production_start.dt.normalize()).dt.days
    invalid = int(data.margin_days.isna().sum())
    valid = data[data.margin_days.notna()].copy()
    valid['margin_days'] = valid.margin_days.astype(int)
    valid['stato_fisico'] = valid.stato_fisico.fillna('')
    flags = logical_date_flags(valid)
    valid['logical_excluded'] = flags.any(axis=1)
    logical = valid[~valid.logical_excluded]
    limits = fit_mad_limits(logical)
    flags = apply_mad_limits(logical, limits)
    valid = valid.join(flags)
    valid['final_retained'] = ~valid.logical_excluded & ~valid.mad_outlier.fillna(False).astype(bool)
    audit_path = source('outputs/analysis/readiness_margin_v2/cleaning_audit.csv')
    assert hashes['outputs/analysis/readiness_margin_v2/cleaning_audit.csv'] == original['audit_sha256']
    saved = pd.read_csv(audit_path, dtype={'odv':str, 'posizione_odv':str}).set_index(keys).sort_index()
    current = valid.set_index(keys).sort_index()
    assert list(current.index) == list(saved.index)
    for name in ['margin_days', 'logical_excluded', 'final_retained']:
        np.testing.assert_array_equal(current[name], saved[name])
    retained = valid[valid.final_retained]
    fitted = retained[retained.margin_days.gt(0)].copy()
    assert len(fitted) == original['positive_fitted'] == config['attributes']['training_positions']
    law = gamma(a=state.shape, scale=state.scale_days)
    np.testing.assert_allclose(fitted.margin_days.mean(), law.mean(), rtol=1e-12)
    # Rounded margins have P(D=d)=F(d)-F(d-1), d>=1. No Monte Carlo noise.
    days = np.arange(1, int(np.ceil(law.ppf(1-1e-13)))+1)
    probability = law.cdf(days)-law.cdf(days-1)
    assert probability.sum() > 1-1e-12
    rounded_mean = float(np.dot(days, probability))
    rounded_std = float(np.sqrt(np.dot((days-rounded_mean)**2, probability)))
    hist = []
    for lo in range(1, 80, 3):
        hi = lo+2
        observed = int(fitted.margin_days.between(lo, hi).sum())
        hist.append(dict(lower_day=lo, upper_day=hi, observed_count=observed, observed_pct=100*observed/len(fitted), model_pct=100*float(law.cdf(hi)-law.cdf(lo-1))))
    # Reference date is an illustrative scenario assumption, not an observed date.
    example = model.sample({'start_date': '2026-11-02'}, np.random.default_rng(42))
    assert example['deadline_date'] == (date(2026,11,2)+timedelta(days=example['margin_days'])).isoformat()
    # Reuse the two generated ODP from Example 5.2, keeping a single deadline per position.
    assert ((sales.odv=='0001118360') & (sales.posizione_odv=='000010')).sum() == 1
    summary = dict(sources_sha256=hashes, initial_positions=len(data), invalid_dates=invalid, valid_dates=len(valid), logical_excluded=int(valid.logical_excluded.sum()), mad_excluded=int(flags.mad_outlier.sum()), retained=len(retained), zero_excluded=int(retained.margin_days.eq(0).sum()), negative_excluded=int(retained.margin_days.lt(0).sum()), fitted_positions=len(fitted), shape=state.shape, scale_days=state.scale_days, observed=dict(mean=float(fitted.margin_days.mean()), std=float(fitted.margin_days.std()), median=float(fitted.margin_days.median()), q05=float(fitted.margin_days.quantile(.05)), q95=float(fitted.margin_days.quantile(.95)), min=int(fitted.margin_days.min()), max=int(fitted.margin_days.max())), gamma_continuous=dict(mean=float(law.mean()), std=float(law.std()), q05=float(law.ppf(.05)), median=float(law.ppf(.5)), q95=float(law.ppf(.95))), gamma_rounded=dict(mean=rounded_mean, std=rounded_std, q05=int(np.ceil(law.ppf(.05))), median=int(np.ceil(law.ppf(.5))), q95=int(np.ceil(law.ppf(.95))), probability_over_81_days=float(law.sf(81))), example=dict(odv='0001118360', posizione_odv='000010', reference_date='2026-11-02', seed=42, **example), notes=['Current snapshot hashes equal the Gamma fitting sources.', 'Every margin and filtering decision reproduced from current canonical data.', 'Selected standalone Gamma equals the component in production_cascade_selected; stale integrated_in_cascade=false in component configuration is not used as runtime evidence.', 'The Gamma is fitted on all retained positive margins, not on the graph train split. Descriptive fit only; no held-out Gamma metrics.', 'Histogram model probabilities include upward rounding to whole calendar days. Mean uses exact rounded PMF truncated beyond 1-1e-13 probability.', 'No model promotion, training, source changes or test evaluation.'])
    output.mkdir(parents=True, exist_ok=True)
    fitted[[*keys, 'stato_fisico', 'production_start', 'data_approntamento_confermata', 'margin_days']].to_csv(output/'readiness-generation-cohort.csv', index=False)
    pd.DataFrame(hist).to_csv(output/'readiness-generation-histogram.csv', index=False)
    (output/'readiness-generation-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('sources_sha256','notes')}, indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'tables/data')
    args=parser.parse_args();collect(args.project_dir.resolve(),args.output_dir.resolve())

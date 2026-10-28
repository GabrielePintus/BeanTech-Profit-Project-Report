"""Verify selected graph generation against current masses and flow bounds; no fitting."""
import json,sys
from pathlib import Path
import numpy as np
import pandas as pd

def load(project):
    sys.path[:0]=[str(project/'src'),str(project/'scripts')]
    from strategic_planner.data.feature_names import read_snapshot_parquet
    from strategic_planner.models.classical_graph import NUMERIC,CATEGORICAL
    from strategic_planner.production_generation.closed_set_split import canonical_catalog_graphs
    from strategic_planner.production_generation.graph_comparison import graph_isomorphic,graph_signature
    from evaluate_production_cascade import structure
    from improve_classical_graph_generation import enriched_examples
    config=json.loads((project/'configs/production_cascade_selected.json').read_text())
    manifest=json.loads((project/config['evaluation_split']).read_text())
    cache=json.loads((project/config['graph_truth_cache']).read_text())
    catalog=json.loads((project/manifest['catalog']).read_text())
    graphs=canonical_catalog_graphs(catalog)
    by_signature={}
    for g in graphs.values():by_signature.setdefault(graph_signature(g),[]).append(g)
    ops=read_snapshot_parquet(project/'data/interim/consuntivi_260915.parquet').set_index('operazione_id')
    orders=read_snapshot_parquet(project/'data/interim/odp_260915.parquet').set_index('odp')
    sales=read_snapshot_parquet(project/'data/interim/odv_260915.parquet').set_index(['odv','posizione_odv'])
    order_ids={k:set(g.index) for k,g in orders.groupby(['odv','posizione_odv'])}
    ready=ops[ops.macro_fase.isin(['PRONTO','PRONTO_QS','PRONTO_QWR'])].set_index('odp').quantita_kg
    assert not ready.index.duplicated().any()
    keys={k:set(map(tuple,v)) for k,v in manifest['split_keys'].items()}
    for a,b in [('train','validation'),('train','test'),('validation','test')]:assert not ({k[0] for k in keys[a]}&{k[0] for k in keys[b]})
    links=read_snapshot_parquet(project/'data/interim/intervalli_flusso_materiale_260915.parquet')
    bounds={(r.odp,r.operazione_da_id,r.operazione_a_id):(r.quantita_minima_kg,r.quantita_massima_kg) for r in links.itertuples()}
    completions=read_snapshot_parquet(project/'data/interim/nodi_completamento_flussi_260915.parquet')
    completion_kind={(r.odp,r.nodo_id):r.tipo_nodo for r in completions.itertuples()}
    output={'train':[],'validation':[]}; originals={};seen=set();node_ids=set();checked=0;checked_edges=0
    for family in cache['families']:
        key=(family['sales_id'],family['position']);seen.add(key)
        assert family['requested_mass']==float(sales.loc[key].quantita_odv_kg)
        assert {o['source_id'] for o in family['orders']}==order_ids[key]
        total=sum(float(ready.loc[o['source_id']]) for o in family['orders'])
        for order in family['orders']:
            originals[order['source_id']]=order
            for n in order['nodes']:
                if n['key'] in ops.index:
                    op=ops.loc[n['key']];node_ids.add(n['key'])
                    assert n['phase']==op.macro_fase and order['source_id']==op.odp
                    np.testing.assert_allclose(n.get('observed_mass',n['mass']),float(op.quantita_kg),rtol=0,atol=1e-8)
                    np.testing.assert_allclose(n['scrap'],float(op.quantita_scarto_kg),rtol=0,atol=1e-8)
                    checked+=1
            for edge in order['edges']:
                key_edge=(order['source_id'],edge['source'],edge['target'])
                if key_edge in bounds:
                    lo,hi=bounds[key_edge];assert lo<=edge['mass']<=hi
                else:
                    assert completion_kind.get((order['source_id'],edge['source'])) in {'PRONTO_IMPLICITO','PRONTO_OSSERVATO_DI_RAMO'}
                    assert completion_kind.get((order['source_id'],edge['target']))=='COMPLETAMENTO_ODP'
                checked_edges+=1
            part=next((k for k in output if key in keys[k]),None)
            if part is None:continue
            row=orders.loc[order['source_id']]
            raw={name:float(row[name]) for name in NUMERIC if name!='assigned_mass_kg' and pd.notna(row[name])}
            raw.update({name:str(row[name]) for name in CATEGORICAL if pd.notna(row[name])})
            raw['assigned_mass_kg']=family['requested_mass']*float(ready.loc[order['source_id']])/total
            g=structure(order)
            candidates=by_signature[graph_signature(g)]
            canonical=next(v for v in candidates if graph_isomorphic(v,g))
            output[part].append((raw,canonical,dict(odv=key[0],posizione_odv=key[1],odp=order['source_id'])))
    assert seen==set(sales.index)==set.union(*keys.values())
    assert set(originals)==set(orders.index)
    assert node_ids==set(ops.index)
    print('Verified cached physical quantities for',checked,'observed nodes and',checked_edges,'flow links; durations are outside this analysis.',flush=True)
    return enriched_examples(output,project),originals,dict(observed_nodes_verified=checked,flow_links_verified=checked_edges,orders=len(originals),catalog_size=len(graphs),split_positions={k:len(v) for k,v in keys.items()},split_odv={k:len({x[0] for x in v}) for k,v in keys.items()})


def collect(project,report):
    import hashlib
    from collections import Counter
    from dataclasses import asdict
    parts,originals,verification=load(project)
    from strategic_planner.models import Model
    from strategic_planner.models.classical_graph import actions_graph
    from strategic_planner.production_generation.classical_decoding import action_probabilities
    from strategic_planner.production_generation.graph_comparison import graph_isomorphic
    from train_mass_aware_graph import replay
    source_hashes={}
    def path(name):
        p=project/name;source_hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest();return p
    def meta(name):return json.loads(path(name).read_text())
    selected=meta('configs/production_cascade_selected.json')
    for filename,digest in selected['source_sha256'].items():
        assert hashlib.sha256((project/filename).read_bytes()).hexdigest()==digest
    model=Model.load_model(path(selected['sources']['graph']))
    structure=model.graph
    frozen=meta('outputs/analysis/selected_refit_zero_duration_v2/summary.json')
    saved=pd.read_csv(path('outputs/analysis/selected_refit_zero_duration_v2/predictions_beam1.csv'),dtype={'odp':str,'odv':str,'posizione_odv':str}).set_index('odp')
    for filename in model.to_state().metadata.attributes['source_sha256']:path(filename)
    config=meta('configs/classical_graph_zero_duration_v1.json')
    manifest=meta(config['split_reference']);catalog=meta(config['catalog_reference']);path(selected['graph_truth_cache'])
    import hashlib
    expected_fingerprint=hashlib.sha256(json.dumps(manifest['source_sha256'],sort_keys=True).encode()).hexdigest()
    assert json.loads((project/selected['graph_truth_cache']).read_text())['fingerprint']==expected_fingerprint
    assert model.to_state().metadata.attributes['source_sha256']==manifest['source_sha256']==catalog['source_sha256']
    assert len(parts['train'])==model.to_state().metadata.attributes['training_orders']
    train_counts=Counter()
    for _,g,_ in parts['train']:
        from strategic_planner.models.classical_graph import graph_actions
        train_counts[graph_actions(g)]+=1
    state=structure.to_state()
    assert tuple(train_counts[t] for t in state.templates)==state.counts
    modal=actions_graph(state.templates[int(np.argmax(state.counts))])
    rng=np.random.default_rng(42);draws=10
    records=[];examples=[];phase_truth=Counter();phase_generated=Counter();sample_records=[]
    original_prediction_changes=0
    for j,(raw,truth,identity) in enumerate(parts['validation']):
        # Match inference: the cascade does not provide codice_motivo_ordine.
        available={k:v for k,v in raw.items() if k!='codice_motivo_ordine'}
        prefix=()
        while not prefix or prefix[-1]!='END':
            choices=tuple(sorted(structure.trie[prefix]));p=action_probabilities(structure,available,prefix,choices)
            prefix=(*prefix,choices[int(p.argmax())])
        baseline=actions_graph(prefix)
        _,reference_initial,reference_account,nodes=replay(model,raw,truth,originals[identity['odp']])
        original_pred=model.predict(raw)
        stored=saved.loc[identity['odp']]
        assert original_pred.complete==stored.complete
        assert graph_isomorphic(original_pred.structure,truth)==stored.exact
        np.testing.assert_allclose([original_pred.initial_mass_kg,reference_initial,sum(reference_account.scrap_kg)], [stored.predicted_initial_kg,stored.actual_initial_kg,stored.actual_scrap_kg],rtol=1e-10,atol=1e-7)
        pred=model.predict(available);assert pred.complete
        original_prediction_changes+=not graph_isomorphic(pred.structure,original_pred.structure)
        account=pred.accounting
        record=dict(**identity,assigned_final_kg=available['assigned_mass_kg'],exact_frequency=graph_isomorphic(modal,truth),exact_structure=graph_isomorphic(baseline,truth),exact_selected=graph_isomorphic(pred.structure,truth),predicted_initial_kg=pred.initial_mass_kg,reference_initial_kg=reference_initial,predicted_scrap_kg=sum(account.scrap_kg),reference_scrap_kg=sum(reference_account.scrap_kg),reference_yield=reference_account.final_kg/reference_initial,predicted_yield=account.final_kg/pred.initial_mass_kg,balance_error_kg=abs(pred.initial_mass_kg-account.final_kg-sum(account.scrap_kg)),target_error_kg=abs(account.final_kg-available['assigned_mass_kg']),reference_nodes=len(truth.nodes),predicted_nodes=len(pred.structure.nodes))
        records.append(record)
        phase_truth.update(set(n.phase for n in truth.nodes))
        for draw in range(draws):
            sample=model.sample(available,rng);assert sample.complete
            acct=sample.accounting
            assert min(v for n,v in zip(sample.structure.nodes,acct.entering_kg) if n.role!='marker')>0
            np.testing.assert_allclose(sample.initial_mass_kg,acct.final_kg+sum(acct.scrap_kg),atol=1e-7,rtol=1e-10)
            np.testing.assert_allclose(acct.final_kg,available['assigned_mass_kg'],atol=1e-7,rtol=1e-10)
            phase_generated.update(set(n.phase for n in sample.structure.nodes))
            sample_records.append(dict(**identity,draw=draw,exact=graph_isomorphic(sample.structure,truth),yield_fraction=acct.final_kg/sample.initial_mass_kg,initial_kg=sample.initial_mass_kg,final_kg=acct.final_kg,scrap_kg=sum(acct.scrap_kg)))
            phases=[n.phase for n in sample.structure.nodes]
            if draw==0 and len(phases) in [3,4] and phases[0]=='TRENOLUNA' and phases[-1]=='PRONTO' and all(n.role in ['material','ready_final'] for n in sample.structure.nodes) and len(sample.structure.edges)>len(phases)-1 and not any('+' in p for p in phases):
                examples.append(dict(**identity,draw=draw,context=available,prediction=asdict(sample),reference_initial_kg=reference_initial))
        if (j+1)%150==0:print('Evaluated',j+1,'ODP',flush=True)
    frame=pd.DataFrame(records);sample_frame=pd.DataFrame(sample_records)
    assert len(frame)==frozen['graph_validation']['n']==len(saved)
    frame.to_csv(report/'tables/data/graph-generation-validation.csv',index=False)
    sample_frame.to_csv(report/'figures/data/graph-generation-samples.csv',index=False)
    frequencies=pd.DataFrame([dict(phase=p,observed_orders=phase_truth[p],sampled_orders=phase_generated[p],observed_pct=100*phase_truth[p]/len(frame),sampled_pct=100*phase_generated[p]/len(sample_frame)) for p in sorted(set(phase_truth)|set(phase_generated))])
    frequencies.to_csv(report/'figures/data/graph-generation-phases.csv',index=False)
    metrics=[dict(model=name,exact=int(frame[column].sum()),accuracy=100*float(frame[column].mean())) for name,column in [('Percorso più frequente','exact_frequency'),('Solo struttura','exact_structure'),('Struttura e masse','exact_selected')]]
    pd.DataFrame(metrics).to_csv(report/'tables/data/graph-generation-comparison.csv',index=False)
    summary=dict(verification=verification,sources_sha256=source_hashes,training_orders=len(parts['train']),validation_orders=len(frame),test_orders=verification['orders']-sum(map(len,parts.values())),comparison=metrics,greedy_complete=len(frame),sampled_complete=len(sample_frame),sample_draws_per_order=draws,sample_seed=42,initial_mae_kg=float(np.abs(frame.predicted_initial_kg-frame.reference_initial_kg).mean()),scrap_mae_kg=float(np.abs(frame.predicted_scrap_kg-frame.reference_scrap_kg).mean()),max_balance_error_kg=float(frame.balance_error_kg.max()),max_target_error_kg=float(frame.target_error_kg.max()),sample_exact_rate=100*float(sample_frame.exact.mean()),original_input_structural_changes=original_prediction_changes,reference_report=frozen['graph_validation'],example_candidates=examples[:12],notes=['Current snapshot byte hashes differ from frozen training metadata. Every cached observed phase, quantity and scrap is checked against the current snapshot; selected-model predictions and normalized reference masses reproduce every saved validation record.','codice_motivo_ordine is omitted for reported inference-compatible comparisons; all other upstream attributes are observed, not generated.','The current catalog uses all-data structural labels; numerical parameters and empirical frequencies use training only.','No test predictions, retraining, or source writes.','Reference masses preserve observed scrap/input ratios and normalized outgoing flow ratios, scaled to the assigned commercial final mass.'])
    (report/'tables/data/graph-generation-summary.json').write_text(json.dumps(summary,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x))+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['sources_sha256','example_candidates','notes']},indent=2))
    print('EXAMPLES',[(e['odp'],[n['phase'] for n in e['prediction']['structure']['nodes']],e['context']['assigned_mass_kg']) for e in examples[:12]])

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-dir',type=Path,required=True);p.add_argument('--report-dir',type=Path,default=Path(__file__).resolve().parents[1]);args=p.parse_args();collect(args.project_dir.resolve(),args.report_dir.resolve())

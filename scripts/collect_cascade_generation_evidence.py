"""Read-only evaluation of the selected cascade on graph-validation positions."""
import argparse
from collections import Counter
from datetime import date,timedelta
import hashlib,json,sys
from pathlib import Path
import numpy as np
import pandas as pd


def collect(project, report, output):
    sys.path[:0]=[str(report/'scripts'),str(project/'src'),str(project/'scripts')]
    import torch
    torch.set_num_threads(2)
    from collect_graph_generation_evidence import load
    from strategic_planner.models import Model,SalesOrderPosition
    from strategic_planner.data.feature_names import read_snapshot_parquet
    from strategic_planner.production_generation.graph_comparison import graph_isomorphic
    from train_mass_aware_graph import replay
    parts,originals,verification=load(project)
    hashes={}
    def source(name):
        p=project/name;hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest();return p
    config=json.loads(source('configs/production_cascade_selected.json').read_text())
    for name,digest in config['source_sha256'].items():assert hashlib.sha256(source(name).read_bytes()).hexdigest()==digest
    cascade=Model.load_model(source(config['artifact']))
    for name,path in config['sources'].items():
        standalone=Model.load_model(project/path)
        if name=='direct_mapper':
            from dataclasses import replace
            from strategic_planner.data.feature_names import column_mapping
            from strategic_planner.models.order_generation import DirectFeatureMapper
            legacy=standalone.direct_mapper.to_state()
            sm,om=column_mapping('odv'),column_mapping('odp')
            standalone=DirectFeatureMapper(replace(legacy,field_mappings=tuple((om.get(t,t),sm.get(s,s)) for t,s in legacy.field_mappings),source_transforms={om.get(k,k):v for k,v in legacy.source_transforms.items()},value_maps={om.get(k,k):v for k,v in legacy.value_maps.items()}))
        meta,arrays=standalone.to_state().to_metadata_and_arrays()
        emeta,earrays=cascade.components[name].to_state().to_metadata_and_arrays()
        assert meta==emeta and arrays.keys()==earrays.keys(),name
        for key in arrays:np.testing.assert_array_equal(arrays[key],earrays[key])
    train_summary=json.loads(source(config['count_training_split']).read_text())
    count_training={k[0] for k in train_summary['split_keys']['train']}
    pxsplit=json.loads(source('configs/splits/odv_features_complete_families_v2.json').read_text())
    pxtraining=set(pxsplit['groups']['train'])
    sales=read_snapshot_parquet(source('data/interim/odv_260915.parquet')).set_index(['odv','posizione_odv'])
    ops=read_snapshot_parquet(source('data/interim/consuntivi_260915.parquet'))
    source('data/interim/odp_260915.parquet')
    ops_by_order={k:g for k,g in ops.groupby('odp')}
    grouped={}
    for raw,graph,identity in parts['validation']:
        key=(identity['odv'],identity['posizione_odv'])
        _,initial,account,_=replay(cascade.components['graph'],raw,graph,originals[identity['odp']])
        grouped.setdefault(key,[]).append(dict(odp=identity['odp'],graph=graph,final=raw['assigned_mass_kg'],initial=initial,scrap=sum(account.scrap_kg)))
    phase_counts={m:Counter() for m in ['observed','specified','quantity_only']}
    order_counts={m:0 for m in phase_counts}
    records=[];details=[];failures=[];samples=[]
    rng=np.random.default_rng(42)
    for index,(key,truth) in enumerate(sorted(grouped.items())):
        truth.sort(key=lambda v:int(v['odp']))
        for order in truth:
            phase_counts['observed'].update(set(n.phase for n in order['graph'].nodes));order_counts['observed']+=1
        row=sales.loc[key];quantity=float(row.quantita_odv_kg)
        context={k:(None if pd.isna(v) else v) for k,v in row.items()}
        target_ops=pd.concat([ops_by_order[o['odp']] for o in truth])
        material=target_ops[~target_ops.macro_fase.isin(['HPT','PRONTO','PRONTO_QS','PRONTO_QWR'])]
        observed_duration=bool(len(material) and material.durata_totale_minuti.gt(0).all() and not (material.durata_zero_imputata.fillna(False)|material.durata_imputata_statisticamente.fillna(False)).any() and all(cascade.components['duration'].supports_phase(p) for p in material.macro_fase))
        duration_reference=float(material.durata_totale_minuti.sum()) if observed_duration else np.nan
        for mode in ['specified','quantity_only']:
            try:
                pred=cascade.predict(SalesOrderPosition(quantity,context)) if mode=='specified' else cascade.sample(SalesOrderPosition(quantity),rng,plan_start_date='2026-11-02')
            except Exception as error:
                failures.append(dict(odv=key[0],posizione_odv=key[1],mode=mode,error=repr(error)))
                continue
            assert pred.sales_features['quantita_odv_kg']==quantity
            flows=[o.prediction.flow for o in pred.orders]
            complete=pred.complete and pred.durations_complete
            balance_errors=[];local_errors=[];target_errors=[]
            for order in pred.orders:
                flow=order.prediction.flow
                if not flow.complete:continue
                ac=flow.accounting
                balance_errors.append(abs(flow.initial_mass_kg-sum(ac.scrap_kg)-ac.final_kg))
                target_errors.append(abs(ac.final_kg-order.final_mass_kg))
                for i,node in enumerate(flow.structure.nodes):
                    incoming=sum(m for a,b,m in ac.edges_kg if b==i)
                    outgoing=sum(m for a,b,m in ac.edges_kg if a==i)
                    assert np.isfinite(ac.entering_kg[i]) and 0<=ac.scrap_kg[i]<=ac.entering_kg[i]
                    if node.role=='marker':continue
                    assert ac.entering_kg[i]>0
                    if i:local_errors.append(abs(ac.entering_kg[i]-incoming))
                    if node.role=='material':
                        local_errors.append(abs(ac.entering_kg[i]-ac.scrap_kg[i]-outgoing))
                        d=order.prediction.duration_hours[i]
                        if d is not None:assert np.isfinite(d) and d>0
                phase_counts[mode].update(set(n.phase for n in flow.structure.nodes));order_counts[mode]+=1
                assert all(m>0 and np.isfinite(m) for _,_,m in ac.edges_kg)
            allocation_error=abs(sum(o.final_mass_kg for o in pred.orders)-quantity)
            deadline=pred.readiness
            assert deadline['margin_days']>=1 and deadline['margin_days']==int(np.ceil(deadline['margin_days_continuous']))
            if mode=='quantity_only':assert deadline['deadline_date']==(date(2026,11,2)+timedelta(days=deadline['margin_days'])).isoformat()
            exact=0;relative_allocation=0
            for i in range(max(len(pred.orders),len(truth))):
                actual=truth[i] if i<len(truth) else None
                generated=pred.orders[i] if i<len(pred.orders) else None
                correct=bool(actual and generated and generated.prediction.flow.complete and graph_isomorphic(actual['graph'],generated.prediction.flow.structure))
                exact+=correct
                relative_allocation+=abs((actual['final'] if actual else 0)-(generated.final_mass_kg if generated else 0))/quantity
                if mode=='specified':details.append(dict(odv=key[0],posizione_odv=key[1],ordinal=i+1,actual_odp=actual['odp'] if actual else None,generated=generated is not None,exact=correct))
            initial=sum(f.initial_mass_kg for f in flows) if pred.complete else np.nan
            scrap=sum(sum(f.accounting.scrap_kg) for f in flows) if pred.complete else np.nan
            duration=sum(sum(o.prediction.duration_hours) for o in pred.orders)*60 if pred.durations_complete else np.nan
            records.append(dict(odv=key[0],posizione_odv=key[1],mode=mode,requested_kg=quantity,actual_count=len(truth),generated_count=len(pred.orders),count_training_overlap=key[0] in count_training,px_training_overlap=key[0] in pxtraining,complete=complete,flow_complete=pred.complete,durations_complete=pred.durations_complete,exact_graphs=exact,exact_position=(exact==len(truth)==len(pred.orders)),actual_initial_kg=sum(t['initial'] for t in truth),predicted_initial_kg=initial,actual_scrap_kg=sum(t['scrap'] for t in truth),predicted_scrap_kg=scrap,allocation_relative_l1=relative_allocation,actual_total_operation_minutes=duration_reference,predicted_total_operation_minutes=duration,margin_days=deadline['margin_days'],max_balance_error_kg=max(balance_errors,default=np.nan),max_local_balance_error_kg=max(local_errors,default=np.nan),max_final_error_kg=max(target_errors+[allocation_error])))
            if mode=='quantity_only' and index<3:
                from dataclasses import asdict
                samples.append(dict(odv=key[0],posizione_odv=key[1],prediction=asdict(pred)))
        if (index+1)%100==0:print('Verified cascade',index+1,'/',len(grouped),flush=True)
    frame=pd.DataFrame(records)
    summary_metrics=[]
    for label,part in [('specified',frame[frame['mode'].eq('specified')]),('specified_unseen_count',frame[frame['mode'].eq('specified')&~frame.count_training_overlap]),('quantity_only',frame[frame['mode'].eq('quantity_only')])]:
        supported=part[part.actual_count.isin([1,2])]
        recalls=[float((g.generated_count==k).mean()) for k,g in supported.groupby('actual_count')]
        duration=part.dropna(subset=['actual_total_operation_minutes','predicted_total_operation_minutes'])
        summary_metrics.append(dict(mode=label,positions=len(part),observed_orders=int(part.actual_count.sum()),generated_orders=int(part.generated_count.sum()),unsupported_count_positions=int((part.actual_count>2).sum()),balanced_count_accuracy_supported=float(np.mean(recalls)),exact_positions=int(part.exact_position.sum()),exact_position_pct=100*float(part.exact_position.mean()),exact_graphs=int(part.exact_graphs.sum()),complete_positions=int(part.complete.sum()),initial_mae_kg=float(abs(part.actual_initial_kg-part.predicted_initial_kg).mean()),scrap_mae_kg=float(abs(part.actual_scrap_kg-part.predicted_scrap_kg).mean()),duration_positions=len(duration),total_operation_minutes_mae=float(abs(duration.actual_total_operation_minutes-duration.predicted_total_operation_minutes).mean()),median_total_operation_minutes=float(part.predicted_total_operation_minutes.median()),q95_total_operation_minutes=float(part.predicted_total_operation_minutes.quantile(.95)),mean_margin_days=float(part.margin_days.mean()),max_balance_error_kg=float(part.max_balance_error_kg.max()),max_local_balance_error_kg=float(part.max_local_balance_error_kg.max()),max_final_error_kg=float(part.max_final_error_kg.max())))
    summary=dict(sources_sha256=hashes,verification=verification,protocol=dict(validation_positions=len(grouped),sample_draws_per_position=1,seed=42,count_uses_argmax=True,matching='observed numeric ODP order vs generated ordinal; no best permutation',reference_masses='same normalized balances and assigned observed final shares as section 5.4',duration_target='sum of current observed material-operation minutes; excludes entire positions with statistically-imputed, zero or unsupported material durations',mass_only_input='requested commercial quantity only; all remaining modelled sales features sampled',test_evaluated=False),metrics=summary_metrics,failures=failures,phase_denominators=order_counts,count_training_overlapping_positions=int(frame[frame['mode'].eq('specified')].count_training_overlap.sum()),px_training_overlapping_positions=int(frame[frame['mode'].eq('quantity_only')].px_training_overlap.sum()),notes=['Frozen cache validated against current observed masses and flow bounds. Duration references come from current operations, not cached durations.','Embedded components match selected sources; the direct mapper is extracted from its source package and its field names are canonically converted as in the cascade build.','Not an independent end-to-end test: upstream component splits differ; lookups, structural support and deadline Gamma use broader data.','No model fitting or production-source edits.'])
    summary['aggregate_comparisons']={mode:{'requested_kg':float(g.requested_kg.sum()),'observed_initial_kg':float(g.actual_initial_kg.sum()),'generated_initial_kg':float(g.predicted_initial_kg.sum()),'observed_scrap_kg':float(g.actual_scrap_kg.sum()),'generated_scrap_kg':float(g.predicted_scrap_kg.sum()),'observed_counts':{str(k):int(v) for k,v in g.actual_count.value_counts().items()},'generated_counts':{str(k):int(v) for k,v in g.generated_count.value_counts().items()}} for mode,g in frame.groupby('mode')}
    output.mkdir(parents=True,exist_ok=True)
    frame.to_csv(output/'cascade-generation-positions.csv',index=False)
    pd.DataFrame(details).to_csv(output/'cascade-generation-orders.csv',index=False)
    pd.DataFrame(summary_metrics).to_csv(output/'cascade-generation-metrics.csv',index=False)
    phases=sorted(set.union(*(set(v) for v in phase_counts.values())))
    pd.DataFrame([dict(phase=p,**{m+'_pct':100*phase_counts[m][p]/order_counts[m] for m in phase_counts},**{m+'_count':phase_counts[m][p] for m in phase_counts}) for p in phases]).to_csv(output/'cascade-generation-phases.csv',index=False)
    (output/'cascade-generation-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (output/'cascade-generation-examples.json').write_text(json.dumps(samples,indent=2,default=str)+'\n')
    print(json.dumps(summary_metrics,indent=2));print('Failures',failures);print('Overlap count',summary['count_training_overlapping_positions'],'px',summary['px_training_overlapping_positions'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-dir',type=Path,required=True);p.add_argument('--report-dir',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output-dir',type=Path);a=p.parse_args();collect(a.project_dir.resolve(),a.report_dir.resolve(),a.output_dir or a.report_dir/'tables/data')

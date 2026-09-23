"""Run immutable S037 baseline, simulated stock loss, old-plan audit, V2 replan."""
import argparse
import importlib
import json
import sys
from pathlib import Path
from state_manager import SimulatedState,sha,digest_table
from simulate_event import load_event
from replanner import run,reassess_old_plan
from compare_plans import compare
import jsonschema
from decimal import Decimal

ROOT=Path(__file__).resolve().parent


def write(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,indent=2,allow_nan=False,default=str),encoding='utf8')


def checked(name,payload):
    schema=json.loads((ROOT/'schemas'/f'{name}_schema.json').read_text())
    jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(payload)
    return payload


class Runtime:
    def __init__(self,project,data,v2,extensions,risk_v2=None):
        self.project=Path(project).resolve();self.data=Path(data).resolve()
        self.v2=Path(v2).resolve();self.extensions=Path(extensions).resolve()
        self.risk_v2=Path(risk_v2).resolve() if risk_v2 else None
        self.modules={}
        mapping={name:self.project for name in ('build_supply_chain_graph','propagate_disruption',
                 'financial_blast_radius','generate_mitigation_strategies','optimize_mitigation')}
        mapping.update({name:self.v2 for name in ('extend_dataset_v2','optimize_mitigation_v2')})
        for name,folder in mapping.items():
            target=folder/(name+'.py')
            if not target.is_file():raise FileNotFoundError(target)
            sys.path.insert(0,str(folder))
            module=importlib.import_module(name)
            if Path(module.__file__).resolve()!=target:raise ValueError('Module shadowing detected: '+name)
            self.modules[name]=module
        self.tracked=list(folder/(name+'.py') for name,folder in mapping.items())
        if self.data.is_file():self.tracked.append(self.data)
        else:
            folder=self.data/'data' if (self.data/'data').is_dir() else self.data
            self.tracked.extend(folder/filename for filename in self.modules['build_supply_chain_graph'].FILES.values())
        self.tracked.extend(sorted(self.extensions.glob('*.csv')))
        if self.risk_v2:
            self.tracked.extend(f for f in self.risk_v2.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
        earlier_future=self.project/'Step7_Future_Test'
        if earlier_future.is_dir():
            self.tracked.extend(f for f in earlier_future.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
        self.source_hashes={str(f):sha(f) for f in sorted(set(self.tracked))}
        builder=self.modules['build_supply_chain_graph']
        self.tables=builder.load_tables(self.data)
        if len(self.tables['orders'])!=100000:raise ValueError('Corrected 100000-order dataset required')
        self.graph=builder.build_graph(self.tables)
        self.ext=self.modules['extend_dataset_v2'].load_extension(self.extensions)
        self.modules['extend_dataset_v2'].validate_extension(self.tables,self.ext)
        snapshots=set(map(str,self.tables['inventory'].last_updated_date.unique()))
        if len(snapshots)!=1:raise ValueError('Ambiguous inventory snapshot')
        self.snapshot=snapshots.pop()
        self.original_table_hashes={name:digest_table(table) for name,table in self.tables.items()}
        self.extension_hashes={name:digest_table(table) for name,table in self.ext.items()}

    def check_immutable(self):
        if self.source_hashes!={str(f):sha(f) for f in sorted(set(self.tracked))}:
            raise RuntimeError('Frozen source files changed')
        if self.original_table_hashes!={name:digest_table(table) for name,table in self.tables.items()}:
            raise RuntimeError('Frozen in-memory tables changed')
        if self.extension_hashes!={name:digest_table(table) for name,table in self.ext.items()}:
            raise RuntimeError('Frozen capacity calendars changed')


def check_reference(path,scenario,baseline):
    if path is None:return {'status':'NO_ARCHIVED_STEP8_CASE','meaning':'New deterministic initial plan computed with original Steps 2–6 V2; no Step 8 risk signal used'}
    case=json.loads(Path(path).read_text());reference=case['messages']['optimization']['data']
    if case['status']!='RECOMMENDATION_READY' or case.get('actions_executed') is not False:
        raise ValueError('Archived Step 8 case is not a recommendation-only completed case')
    prior=case['scenario']
    for source,target in [('supplier_id','supplier_id'),('capacity_loss_percent','capacity_loss_percent'),
                          ('duration_days','duration_days'),('assumed_delay_days','assumed_delay_days'),
                          ('daily_penalty_rate','daily_penalty_rate'),
                          ('uncovered_unit_cost_cents','uncovered_unit_cost_cents'),
                          ('route_capacity_mode','route_capacity_mode')]:
        left,right=prior[source],scenario[target]
        same=Decimal(str(left))==Decimal(str(right)) if source in ('capacity_loss_percent','daily_penalty_rate') else left==right
        if not same:raise ValueError('Step 8 case assumptions do not match: '+source)
    for field in ['total_cost_cents','orders_protected','unresolved_order_ids']:
        if reference['audit'][field]!=baseline['optimization']['audit'][field]:
            raise ValueError('Initial plan differs from archived Step 8: '+field)
    return dict(status='VERIFIED_ARCHIVED_STEP8',path=str(Path(path).resolve()),
        original_case_id=case['case_id'],old_risk_model='Historical Step 8 signal, not rescored or retrained; not used to drive new event',
        initial_objective_cents=reference['audit']['total_cost_cents'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for argument in ('project-root','data','v2-root','extensions','scenario','output'):
        p.add_argument('--'+argument,required=True)
    p.add_argument('--risk-v2-root',help='Optional frozen V2 files checked before/after; never retrained')
    p.add_argument('--initial-step8-case',help='Optional archived Step 8 case_state.json; matched to recalculated baseline')
    a=p.parse_args();out=Path(a.output).resolve()
    raw=json.loads(Path(a.scenario).read_text())
    checked('event',raw)
    scenario=raw['scenario']
    if scenario['snapshot']!='2027-01-01':raise ValueError('Current V2 calendars support the 2027-01-01 snapshot only')
    event=load_event(raw,scenario['snapshot'])
    tools=Runtime(a.project_root,a.data,a.v2_root,a.extensions,a.risk_v2_root)
    if tools.snapshot!=scenario['snapshot']:raise ValueError('Scenario/actual snapshot mismatch')
    forbidden=[tools.data,tools.v2,tools.extensions,tools.risk_v2,
               tools.project/'SupplyGrid_Step8',tools.project/'SupplyGrid_Step7',
               tools.project/'Step7_Future_Test',Path(a.scenario).resolve()]
    if out.exists() or any(q and (out==q or q in out.parents) for q in forbidden):
        raise ValueError('Use a fresh output directory outside frozen inputs')
    out.mkdir(parents=True)
    try:
        initial=run(tools,tools.tables,scenario)
        reference=check_reference(a.initial_step8_case,scenario,initial)
        state=SimulatedState(tools.tables,tools.snapshot)
        transition=state.apply_inventory_loss(event)
        checked('state',transition)
        state.verify_isolation()
        revised=run(tools,state.tables,scenario)
        old_review=reassess_old_plan(tools,initial['optimization']['plan'],revised['context'],scenario['uncovered_unit_cost_cents'])
        if old_review['valid']:
            raise AssertionError('For this experiment the initial plan must become invalid under the new event')
        comparison=compare(initial,revised,old_review)
        checked('plan',comparison)
        tools.check_immutable();state.verify_isolation()
        for stage,result in [('initial',initial),('revised',revised)]:
            write(out/f'{stage}_summary.json',dict(impact_potential_order_ids=result['impact']['potential_order_ids'],
                conditional_financial_exposure_usd=result['financial']['breakdown']['total_cost'],
                mitigation_candidate_count=len(result['candidates']['candidates']),
                solver_status=result['optimization']['status'],plan=result['optimization']['plan'],
                audit=result['optimization']['audit'],conditional_objective_usd=result['optimization']['objective_value']))
        write(out/'state_transition.json',transition)
        write(out/'plan_comparison.json',comparison)
        write(out/'run_manifest.json',dict(scenario=scenario,reference=reference,source_hashes=tools.source_hashes,
             frozen_source_verified=True,simulation_only=True,actions_executed=False,
             event_time=event['event_time'],initial_recommendation_time=event['initial_recommendation_time']))
        print(json.dumps({k:comparison[k] for k in ['initial_protected_orders','revised_protected_orders',
          'initial_unresolved_orders','revised_unresolved_orders','initial_conditional_objective_usd',
          'revised_conditional_objective_usd','old_plan_reassessment']},indent=2))
        return comparison
    except Exception as exc:
        write(out/'failed_run.json',dict(type=type(exc).__name__,error=str(exc),frozen_source_check_attempted=True))
        tools.check_immutable()
        raise


if __name__=='__main__':main()

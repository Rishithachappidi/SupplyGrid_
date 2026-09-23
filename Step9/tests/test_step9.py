import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from state_manager import SimulatedState,digest_table
from simulate_event import load_event
from run_simulation import checked,check_reference
from compare_plans import compare

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=json.loads((ROOT/'scenarios/s037_dynamic_scenario.json').read_text())


class Step9Tests(unittest.TestCase):
    def sample(self):
        frame=pd.DataFrame([dict(inventory_id='I001',warehouse_id='W023',product_id='P050',
            quantity_on_hand=1180,reserved_quantity=118,available_quantity=1062,
            safety_stock=100,last_updated_date='2027-01-01')])
        return {'inventory':frame}

    def test_schema_and_event_time(self):
        checked('event',FIXTURE)
        self.assertEqual(load_event(FIXTURE,'2027-01-01')['units_lost'],962)

    def test_event_before_plan_rejected(self):
        altered=copy.deepcopy(FIXTURE)
        altered['event']['event_time']='2027-01-01T08:59:00'
        with self.assertRaises(ValueError):load_event(altered,'2027-01-01')

    def test_cross_day_rejected(self):
        altered=copy.deepcopy(FIXTURE)
        altered['event']['event_time']='2027-01-02T09:05:00'
        with self.assertRaises(ValueError):load_event(altered,'2027-01-01')

    def test_unknown_event_rejected(self):
        altered=copy.deepcopy(FIXTURE)
        altered['event']['event_type']='factory_fire'
        with self.assertRaises(Exception):load_event(altered,'2027-01-01')

    def test_stock_loss_keeps_original_and_accounting(self):
        original=self.sample();before=digest_table(original['inventory'])
        state=SimulatedState(original,'2027-01-01')
        result=state.apply_inventory_loss(FIXTURE['event'])
        state.verify_isolation();checked('state',result)
        self.assertEqual(before,digest_table(original['inventory']))
        self.assertEqual(int(state.tables['inventory'].at[0,'quantity_on_hand']),218)
        self.assertEqual(int(state.tables['inventory'].at[0,'available_quantity']),100)
        self.assertEqual(int(state.tables['inventory'].at[0,'reserved_quantity']),118)

    def test_no_double_application(self):
        state=SimulatedState(self.sample(),'2027-01-01');state.apply_inventory_loss(FIXTURE['event'])
        with self.assertRaises(ValueError):state.apply_inventory_loss(FIXTURE['event'])

    def test_oversize_loss_rejected(self):
        e=copy.deepcopy(FIXTURE['event']);e['units_lost']=1063
        with self.assertRaises(ValueError):SimulatedState(self.sample(),'2027-01-01').apply_inventory_loss(e)

    def test_isolation_guard_detects_mutation(self):
        original=self.sample();state=SimulatedState(original,'2027-01-01')
        state.apply_inventory_loss(FIXTURE['event']);original['inventory'].at[0,'available_quantity']=0
        with self.assertRaises(RuntimeError):state.verify_isolation()

    def test_completed_real_run(self):
        path=ROOT/'results/s037_dynamic_run'
        comparison=json.loads((path/'plan_comparison.json').read_text())
        checked('plan',comparison)
        self.assertEqual(comparison['initial_protected_orders'],36)
        self.assertEqual(comparison['revised_protected_orders'],35)
        self.assertEqual(comparison['initial_unresolved_orders'],80)
        self.assertEqual(comparison['revised_unresolved_orders'],81)
        self.assertFalse(comparison['old_plan_reassessment']['valid'])
        self.assertEqual(comparison['conditional_objective_delta_usd'],'11.50')
        self.assertEqual(comparison['removed_selected_transfers'],1)
        manifest=json.loads((path/'run_manifest.json').read_text())
        self.assertTrue(manifest['frozen_source_verified'])
        self.assertFalse(manifest['actions_executed'])
        self.assertEqual(manifest['reference']['status'],'VERIFIED_ARCHIVED_STEP8')

    def test_reference_mismatched_assumption_fails(self):
        before=json.loads((ROOT/'results/s037_dynamic_run/run_manifest.json').read_text())
        fake=dict(before['scenario']);fake['duration_days']=4
        fixture={'status':'RECOMMENDATION_READY','actions_executed':False,'scenario':before['scenario'],
                 'messages':{'optimization':{'data':{'audit':{}}}}}
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/'case.json';file.write_text(json.dumps(fixture))
            with self.assertRaises(ValueError):check_reference(file,fake,{'optimization':{'audit':{}}})


if __name__=='__main__':unittest.main()

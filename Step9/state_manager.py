"""Isolated same-snapshot simulation state. Frozen inputs remain read-only."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import pandas as pd


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def digest_table(table):
    h=hashlib.sha256()
    h.update(json.dumps(list(table.columns)).encode())
    h.update(pd.util.hash_pandas_object(table,index=True).values.tobytes())
    return h.hexdigest()


class SimulatedState:
    def __init__(self, original, snapshot):
        self.original=original
        self.snapshot=snapshot
        self.tables=dict(original)
        self.events=[]
        self.original_inventory_digest=digest_table(original['inventory'])

    def apply_inventory_loss(self,event):
        if event['event_type']!='warehouse_finished_stock_loss':
            raise ValueError('Unsupported event; no state modification')
        if event['effective_date']!=self.snapshot:
            raise ValueError('Step 6 V2 requires same-day original calendar; no backdated/advanced event allowed')
        if self.events:
            raise ValueError('Use a fresh state for each scenario')
        frame=self.original['inventory'].copy(deep=True)
        mask=(frame.warehouse_id==event['warehouse_id'])&(frame.product_id==event['product_id'])
        if mask.sum()!=1:raise ValueError('Warehouse/product position missing or ambiguous')
        idx=frame.index[mask][0]
        loss=event['units_lost']
        before={k:int(frame.at[idx,k]) for k in ['quantity_on_hand','reserved_quantity','available_quantity','safety_stock']}
        if loss>before['available_quantity'] or loss>before['quantity_on_hand']-before['reserved_quantity']:
            raise ValueError('Cannot lose reserved/unavailable product stock')
        frame.at[idx,'quantity_on_hand']=before['quantity_on_hand']-loss
        frame.at[idx,'available_quantity']=before['available_quantity']-loss
        assert before['reserved_quantity']==int(frame.at[idx,'reserved_quantity'])
        self.tables['inventory']=frame
        after={k:int(frame.at[idx,k]) for k in before}
        change=dict(event=event,inventory_id=str(frame.at[idx,'inventory_id']),before=before,after=after,
                    original_inventory_sha256=self.original_inventory_digest,simulated_inventory_sha256=digest_table(frame),
                    frozen_source_changed=False,real_actions_executed=False)
        self.events.append(change)
        return change

    def verify_isolation(self):
        if digest_table(self.original['inventory'])!=self.original_inventory_digest:
            raise RuntimeError('Frozen inventory changed')
        if self.tables['inventory'] is self.original['inventory']:
            raise RuntimeError('Working state aliases frozen inventory')

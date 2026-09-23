"""Report exact actions and comparable conditional objectives, not causal savings."""
from decimal import Decimal


def selections(result):
    p=result['optimization']['plan']
    finished={(a['order_id'],a['source_location'],a['destination_location'],a['product_id'],a['recoverable_units'],a['action_type']) for a in p['finished_transfers']}
    jobs={(a['order_id'],a['factory_id'],a['product_id'],a['start_date']) for a in p['production_jobs']}
    lots={(a['supplier_id'],a['component_id'],a['factory_id'],a['reservation_date'],a['quantity']) for a in p['procurement_lots']}
    return finished,jobs,lots


def compare(initial,revised,old_plan_review):
    a,b=initial['optimization']['audit'],revised['optimization']['audit']
    sa,sb=selections(initial),selections(revised)
    common={'initial':initial,'revised':revised}
    removed=[len(sa[i]-sb[i]) for i in range(3)]
    added=[len(sb[i]-sa[i]) for i in range(3)]
    impact_before=set(initial['impact']['potential_order_ids'])
    impact_after=set(revised['impact']['potential_order_ids'])
    outcome=dict(initial_solver_status=initial['optimization']['status'],revised_solver_status=revised['optimization']['status'],
        initial_conditional_objective_usd=str(initial['optimization']['objective_value']),
        revised_conditional_objective_usd=str(revised['optimization']['objective_value']),
        conditional_objective_delta_usd=str(Decimal(revised['optimization']['objective_value'])-Decimal(initial['optimization']['objective_value'])),
        initial_protected_orders=a['orders_protected'],revised_protected_orders=b['orders_protected'],
        initial_unresolved_orders=len(a['unresolved_order_ids']),revised_unresolved_orders=len(b['unresolved_order_ids']),
        initial_unresolved_units=a['unresolved_units'],revised_unresolved_units=b['unresolved_units'],
        initial_potential_order_count=len(impact_before),revised_potential_order_count=len(impact_after),
        added_potential_order_ids=sorted(impact_after-impact_before),removed_potential_order_ids=sorted(impact_before-impact_after),
        revised_cost_breakdown_cents=b['cost_breakdown_cents'],
        removed_selected_transfers=removed[0],added_selected_transfers=added[0],
        removed_production_jobs=removed[1],added_production_jobs=added[1],
        removed_procurement_lots=removed[2],added_procurement_lots=added[2],
        selected_finished_transfers_initial=len(sa[0]),selected_finished_transfers_revised=len(sb[0]),
        selected_production_initial=len(sa[1]),selected_production_revised=len(sb[1]),
        old_plan_reassessment=old_plan_review,
        initial_financial_conditional_exposure_usd=str(initial['financial']['breakdown']['total_cost']),
        revised_financial_conditional_exposure_usd=str(revised['financial']['breakdown']['total_cost']),
        scope='Synthetic same-snapshot what-if, not causal loss, realized savings, or executed actions',
        recommendation_only=True,source_modified=False)
    if not any(removed+added) and a['total_cost_cents']==b['total_cost_cents'] and impact_before==impact_after:
        raise AssertionError('State change did not materially alter impact or selected plan')
    return outcome

"""Call the unchanged Steps 2–6 V2 on each isolated supply-chain state."""
from datetime import date
from decimal import Decimal
from state_manager import sha


def run(tools,tables,scenario):
    impact=tools.modules['propagate_disruption'].propagate(
        tools.graph,tables,scenario['supplier_id'],float(scenario['capacity_loss_percent']),
        int(scenario['duration_days']),date.fromisoformat(tools.snapshot))
    financial=tools.modules['financial_blast_radius'].calculate_financial_exposure(
        impact,tables,int(scenario['assumed_delay_days']),'0',str(scenario['daily_penalty_rate']))
    candidates=tools.modules['generate_mitigation_strategies'].generate_options(
        impact,tools.graph,tables,int(scenario['assumed_delay_days']))
    solver=tools.modules['optimize_mitigation_v2']
    ctx=solver.Context(tables,tools.ext,impact,candidates,financial,scenario['route_capacity_mode'])
    result=solver.optimize_v2(ctx,int(scenario['uncovered_unit_cost_cents']),int(scenario['time_limit_seconds']))
    if result['status'] not in ('OPTIMAL','FEASIBLE'):
        raise RuntimeError(f"V2 solver produced no valid plan: {result['status']}")
    independent=solver.audit_plan(ctx,result['plan'],int(scenario['uncovered_unit_cost_cents']))
    if independent!=result['audit'] or independent['total_cost_cents']!=int(Decimal(result['objective_value'])*100):
        raise ArithmeticError('Independent V2 audit differs from solver result')
    return dict(impact=impact,financial=financial,candidates=candidates,optimization=result,context=ctx)


def reassess_old_plan(tools,original_plan,new_context,service_cost_cents):
    try:
        report=tools.modules['optimize_mitigation_v2'].audit_plan(new_context,original_plan,int(service_cost_cents))
    except (ValueError,ArithmeticError,KeyError,TypeError) as error:
        return dict(valid=False,audit_error_type=type(error).__name__,audit_reason=str(error))
    return dict(valid=True,audit=report)

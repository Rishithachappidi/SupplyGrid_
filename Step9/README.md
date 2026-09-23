# SupplyGrid Step 9 — isolated state-change simulation and replanning

This **Step 9-only** folder leaves Steps 1–8, the 14 original tables, three dated V2 extensions, archived Step 7, V2 model and both Step 7 future-test evidence sets untouched. No model retraining, new agent runtime, optimizer modification, external action or shipment occurs. Use the existing corrected **100,000-order** dataset.

## What the experiment does

1. Load the original corrected dataset, graph and unchanged Steps 3–6 V2. Compute an initial S037 plan for **2027-01-01**, capacity loss 80% for 10 days, 10 assumed delay days. Optionally verify its objective, protected orders and unresolved order IDs against the saved Step 8 case. The saved Step 8 risk classification is a historical synthetic signal; Step 9 does **not** rerun, reinterpret or retrain that model.
2. Simulate a stock-count loss **five minutes after the first recommendation and before any action**. The declared event removes 962 finished P050 units from warehouse W023: on-hand 1180 → 218, unreserved available 1062 → 100, reserved 118 unchanged. It is a deliberately severe what-if scenario; this is not an observed stock loss. The original inventory stays unchanged; only one copied DataFrame row changes.
3. Rerun impact, finance, candidate generation and the **unchanged V2 SCIP optimizer** on the revised working state. Independently audit the old plan on the revised context; it must fail. Independently audit the new plan and compare the actual selected actions, objective and order counts.

**Measured in the packaged example:** Initial plan 36 protected / 80 unresolved / USD 12,627.78 conditional objective. Revised plan 35 protected / 81 unresolved / USD 12,639.28; one previously selected finished-stock transfer is removed. The initial plan fails the revised-state audit as a disabled/changed finished-stock action. Both solver plans themselves pass independent V2 audits, and frozen input hashes are unchanged. The USD 11.50 difference is between modeled *conditional optimization objectives*, not a realized financial loss or amount saved. The conditional financial exposure estimate does not change in this scenario; stock loss changes mitigation availability rather than the counted exposed orders.

The V2 calendar begins on January 1 and its existing `Context` requires the initial calendar day. Thus both event and recommendation are **on the same snapshot day**; this does not implement advancing several days, execution/reservation of selected actions, probabilistic future worlds or live digital-twin synchronization. Those are future enhancements requiring a new dated inventory/order/commitment state model. A seven-day-ahead risk forecast from 2028/2029 cannot be treated as a contemporaneous 2027 event. Synthetic loss is explicitly supplied by the scenario, never inferred from the risk probability.

## Extract and run on Windows

Extract `SupplyGrid_Step9_Only.zip` into `C:\Users\rishi\Downloads\Supplygrid`. It creates `SupplyGrid_Step9/` only. Keep your existing root scripts, `dataset` containing the **corrected** 14 CSVs, Step 6 V2 folder, Step 8 folder, and Step 7 V2 folder separately.

```powershell
cd C:\Users\rishi\Downloads\Supplygrid
py -3.12 -m venv .venv_step9
.venv_step9\Scripts\python -m pip install -r SupplyGrid_Step9\requirements.txt
.venv_step9\Scripts\python SupplyGrid_Step9\run_simulation.py --project-root . --data dataset --v2-root SupplyGrid_Step6_V2_Only --extensions SupplyGrid_Step6_V2_Only\data_v2 --risk-v2-root SupplyGrid_Step7_V2 --scenario SupplyGrid_Step9\scenarios\s037_dynamic_scenario.json --initial-step8-case SupplyGrid_Step8\results\s037_demo\case_state.json --output SupplyGrid_Step9\results\my_first_run
```

Point `--v2-root` to the **inner** directory with `optimize_mitigation_v2.py` if your V2 ZIP contains a wrapper folder. If your old Step 8 case file is unavailable, omit `--initial-step8-case`; Step 9 still calculates and audits an initial plan from Steps 2–6, but it cannot claim parity with a saved Step 8 recommendation. The optional `--risk-v2-root` hashes V2 model and future evidence without running the model. Use a **new** `--output` each time; source folders and previous results are not overwritten.

The standalone example reports are in `results/s037_dynamic_run/`: `initial_summary.json`, `state_transition.json`, `revised_summary.json`, `plan_comparison.json`, and `run_manifest.json`. The manifest includes source hashes and the Step 8 comparison when supplied. Run `python -m unittest discover -s SupplyGrid_Step9/tests -v` for focused guards and checks. These are deterministic software agents/solvers reused as tools, not new agents implemented in Step 9.

## Scope of claims

The example demonstrates *same-day hypothetical state correction → old plan invalidation → deterministic reoptimization → auditable changed recommendation*. It does not prove the predicted S037 disruption happened, establish causal financial exposure, measure real operational service improvement or validate the weak Step 7 predictor. The archived Step 8 folder still expects original Step 7; a V2 risk adapter is a separate integration task. Always use human review before any operational use.

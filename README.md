# SupplyGrid

## Autonomous Supply Chain Disruption Mitigation and Optimization Platform

SupplyGrid is a research-oriented platform for studying how supply-chain disruptions can be detected, propagated through a dependency graph, quantified financially, mitigated, optimized, and dynamically replanned.

The project combines graph analysis, machine-learning risk prediction, financial impact estimation, constrained optimization, multi-agent orchestration, and event-driven replanning in one experimental pipeline.

> **Research status:** Steps 1–9 have been implemented and experimentally validated on the project's synthetic supply-chain environment. The experiments are synthetic and do not constitute enterprise or real-world operational validation.

---

## Research Question

> **Can a graph-aware multi-agent optimization system reduce disruption recovery cost and time compared with conventional rule-based and centralized approaches?**

SupplyGrid investigates this question through a staged architecture rather than treating disruption management as a single prediction problem.

---

## Architecture

```text
Supply-Chain Data
        │
        ▼
Dependency Graph
        │
        ▼
Disruption Propagation
        │
        ▼
Financial Impact
        │
        ▼
Mitigation Generation
        │
        ▼
Constrained Optimization
        │
        ▼
Risk + Specialized Agents
        │
        ▼
Decision Orchestration
        │
        ▼
Dynamic Replanning
```

---

## Implementation Stages

| Stage | Capability |
|---|---|
| 1 | Integrated synthetic supply-chain dataset and validation |
| 2 | Typed dependency-graph construction |
| 3 | Disruption propagation and exposure analysis |
| 4 | Conditional financial blast-radius estimation |
| 5 | Mitigation candidate generation |
| 6 | Constrained mathematical optimization, including V2 production/capacity extensions |
| 7 | Leakage-controlled supplier disruption-risk prediction (V2) |
| 8 | Multi-agent analysis and decision orchestration |
| 9 | Event-driven plan reassessment and dynamic replanning |

The public repository contains selected implementation and experiment artifacts from these stages. The complete research archive and full synthetic master dataset are maintained separately.

---

## Example Experiment

A representative synthetic scenario uses supplier **S037** with an **80% capacity loss for 10 days**.

The optimization pipeline produced a conditional objective of **USD 12,627.78**, protecting 36 orders in the frozen Step 8 scenario. A later synthetic event affecting warehouse W023 caused the previous plan to fail its audit, after which the replanner generated a revised plan with 35 protected orders and a conditional objective of **USD 12,639.28**.

These numbers are **scenario-specific synthetic experiment results**, not claims about real-world cost savings.

---

## Step 6 — Optimization

Step 6 implements constrained mitigation optimization using the supply-chain state and generated mitigation candidates.

The V2 extension adds supporting factory inventory and dated capacity information so the model can represent production-oriented recovery decisions in addition to finished-product transfers.

See `Step6_V2/` for the V2 implementation, validation tables, and experiment reports.

---

## Step 7 — Risk Prediction V2

The official predictive implementation is Step 7 V2.

It uses:

- chronological supervised learning;
- a forward 7-day disruption target;
- leakage controls and purged temporal evaluation;
- native XGBoost model serialization;
- preprocessing and probability calibration;
- a stable prediction API;
- reproducibility and integrity checks.

The public package contains the model artifacts and supporting metadata needed to inspect the experimental implementation.

The frozen synthetic future evaluation produced measurable ranking signal above its random-prevalence baseline, but it is explicitly treated as **synthetic validation**, not real enterprise evidence.

See `Step7_V2/`.

---

## Step 8 — Multi-Agent Decision Pipeline

Step 8 separates the analysis into specialized agents for:

- risk prediction;
- graph impact;
- financial impact;
- mitigation;
- optimization.

An orchestrator coordinates the agents and maintains structured case state, schemas, evidence, assumptions, and decision traces.

The system is analysis/recommendation oriented: no real operational action is executed by the experiment.

See `Step8/`.

---

## Step 9 — Dynamic Replanning

Step 9 introduces a new event after an initial mitigation plan has been generated.

The experiment:

1. creates an initial state;
2. generates a plan;
3. introduces a new operational event;
4. reassesses the existing plan;
5. invalidates the affected plan when its assumptions no longer hold;
6. generates a revised plan;
7. records the state transition and plan comparison.

The selected final experiment is preserved under `Step9/results/windows_run_01/`.

---

## Project Limitations

- The operational environment is synthetic.
- The financial calculations use explicit scenario assumptions.
- The predictive model has not been validated on proprietary enterprise supplier data.
- Public data does not provide all supplier, BOM, factory-capacity, inventory, and production-state relationships required for direct real-world replay.
- The experiments demonstrate the architecture and internal behavior of the system; they do not establish universal business performance.

---

## Repository Contents

```text
SupplyGrid/
├── README.md
├── build_supply_chain_graph.py
├── propagate_disruption.py
├── financial_blast_radius.py
├── generate_mitigation_strategies.py
├── optimize_mitigation.py
├── validation_report.json
│
├── Step6_V2/
├── Step7_V2/
├── Step8/
└── Step9/
```

The full synthetic master dataset, historical/provenance material, intermediate experiments, and internal development archive are intentionally excluded from this public repository.

---

## Technologies

- Python
- Pandas
- NumPy
- NetworkX
- scikit-learn
- XGBoost
- OR-Tools / SCIP
- JSON Schema

---

## Reproducibility

The public repository contains selected code, model artifacts, schemas, validation material, and representative experiment outputs. Some end-to-end commands from the private research archive require the complete synthetic dataset and supporting artifacts, which are intentionally not distributed here.

For the complete reproducibility package, use the private research archive.

---

## Future Research

Planned extensions include:

- real-world operational validation;
- broader alternate-supplier and procurement modeling;
- real-time data integration;
- larger-scale benchmarking;
- control-tower visualization;
- integration with live enterprise planning systems.

---

## License

No open-source license is granted by this showcase package unless a separate license file is added by the project owner.

##Author 

RISHITHA C 

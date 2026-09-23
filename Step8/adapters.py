"""Read-only adapters to original SupplyGrid modules. No copied decision engines."""

import importlib
import sys
from pathlib import Path

from common import file_digest


class Tools:
    def __init__(self, project, data, v2, extensions, risk, features=None):
        self.project, self.v2, self.risk = map(
            lambda x: Path(x).resolve(),
            (project, v2, risk),
        )
        self.data = Path(data).resolve()
        self.extensions = Path(extensions).resolve()

        # Step 7 V2 uses the frozen V2 model, while the original
        # Step 7 inference feature file is retained as its input data.
        self.features = (
            Path(features).resolve()
            if features
            else (
                self.risk.parent
                / "SupplyGrid_Step7"
                / "data"
                / "inference_features.csv"
            )
        )

        sources = {
            "build_supply_chain_graph": self.project,
            "propagate_disruption": self.project,
            "financial_blast_radius": self.project,
            "generate_mitigation_strategies": self.project,
            "optimize_mitigation": self.project,
            "extend_dataset_v2": self.v2,
            "optimize_mitigation_v2": self.v2,
            "risk_api": self.risk,
        }

        # Load root modules before V2, so old copies inside a V2 bundle
        # cannot shadow them.
        self.modules = {}

        for name, directory in sources.items():
            target = directory / (name + ".py")

            if not target.is_file():
                raise FileNotFoundError(target)

            sys.path.insert(0, str(directory))

            module = importlib.import_module(name)

            if Path(module.__file__).resolve() != target:
                raise ValueError(
                    f"Module shadowing detected: {name}; run in a fresh process"
                )

            self.modules[name] = module

        self.tracked = list(
            sources[name] / (name + ".py") for name in sources
        )

        if self.data.is_file():
            self.tracked.append(self.data)
        else:
            directory = (
                self.data / "data"
                if (self.data / "data").is_dir()
                else self.data
            )

            self.tracked.extend(
                directory / f
                for f in self.modules[
                    "build_supply_chain_graph"
                ].FILES.values()
            )

        self.tracked.extend(self.extensions.glob("*.csv"))

        # Track the exact frozen Step 7 V2 model artifacts,
        # metadata, API, and inference input.
        self.tracked.extend(
            [
                self.features,
                self.risk / "model" / "xgboost_model.json",
                self.risk / "model" / "preprocessor.joblib",
                self.risk / "model" / "calibrator.joblib",
                self.risk / "model_metadata.json",
                self.risk / "risk_api.py",
            ]
        )

        self.before = self.hashes()

        graph_tool = self.modules["build_supply_chain_graph"]
        self.tables = graph_tool.load_tables(self.data)

        # Detect accidentally supplied truncated dataset before graph construction.
        if len(self.tables["orders"]) != 100000:
            raise ValueError("Expected the corrected 100,000-order dataset")

        self.graph = graph_tool.build_graph(self.tables)

        self.ext = self.modules[
            "extend_dataset_v2"
        ].load_extension(self.extensions)

        self.modules[
            "extend_dataset_v2"
        ].validate_extension(
            self.tables,
            self.ext,
        )

        snapshots = set(
            self.tables["inventory"][
                "last_updated_date"
            ].astype(str)
        )

        if len(snapshots) != 1:
            raise ValueError("Exactly one inventory snapshot required")

        self.snapshot = next(iter(snapshots))
        self.model = None
        self.memory_before = self.memory_hashes()

    def hashes(self):
        return {
            str(p): file_digest(p)
            for p in sorted(set(self.tracked))
        }

    def memory_hashes(self):
        import hashlib
        import pickle
        import pandas as pd

        def frames_hash(frames):
            h = hashlib.sha256()

            for name, frame in sorted(frames.items()):
                h.update(
                    pickle.dumps(
                        (
                            name,
                            list(frame.columns),
                            list(map(str, frame.dtypes)),
                        )
                    )
                )

                h.update(
                    pd.util.hash_pandas_object(
                        frame,
                        index=True,
                    ).to_numpy().tobytes()
                )

            return h.hexdigest()

        # Ignore harmless Pandas/NetworkX query caches, but protect all values,
        # schema, node/edge attributes and actual graph topology.
        topology = (
            self.graph.graph,
            list(self.graph.nodes(data=True)),
            list(self.graph.edges(keys=True, data=True)),
        )

        return {
            "tables": frames_hash(self.tables),
            "extensions": frames_hash(self.ext),
            "graph": hashlib.sha256(
                pickle.dumps(topology)
            ).hexdigest(),
        }

    def assert_unchanged(self):
        if (
            self.before != self.hashes()
            or self.memory_before != self.memory_hashes()
        ):
            raise RuntimeError(
                "Source file or in-memory operational input changed"
            )

    def evidence(self, module):
        # Step 8's existing risk agent is historically named "risk_core".
        # Step 7 V2 replaces that implementation with risk_api.py.
        actual_module = "risk_api" if module == "risk_core" else module

        path = Path(
            self.modules[actual_module].__file__
        ).resolve()

        return {
            "tool": module,
            "path": str(path),
            "sha256": self.before[str(path)],
        }

    def risk_prediction(self, supplier):
        import pandas as pd

        # Step 7 V2 stable prediction interface.
        # Predictor verifies the V2 model artifact checksums and loads
        # the native XGBoost model.
        predictor = self.modules[
            "risk_api"
        ].Predictor(self.risk)

        frame = pd.read_csv(self.features)

        self.modules[
            "risk_api"
        ].validate(frame)

        # Preserve the original Step 8 behavior:
        # use the latest available forecast origin.
        latest = pd.to_datetime(
            frame.date
        ).max()

        frame = frame.loc[
            pd.to_datetime(frame.date) == latest
        ].copy()

        unknown = (
            set(frame.supplier_id)
            - set(
                self.tables["suppliers"].supplier_id
            )
        )

        if unknown:
            raise ValueError(
                "Prediction suppliers absent from operational dataset"
            )

        predictions = predictor.predict(frame)

        selected = predictions.loc[
            predictions.supplier_id == supplier
        ]

        if len(selected) != 1:
            raise ValueError(
                "Supplier absent or ambiguous at latest forecast origin"
            )

        row = selected.iloc[0].to_dict()

        # Step 7 V2 returns risk_date/risk_probability.
        # Step 8's existing schema expects date/disruption_probability.
        # Translate the interface here without modifying the frozen V2 model.
        return {
            "supplier_id": str(row["supplier_id"]),
            "date": str(pd.Timestamp(row["risk_date"]).date()),
            "disruption_probability": float(row["risk_probability"]),
            "risk_rank": int(row["risk_rank"]),
            "risk_level": str(row["risk_level"]),
            "threshold": float(predictor.threshold),
            "horizon_days": 7,
            "confirmed_disruption": False,
            "explanations": [],
        }

    def graph_impact(self, scenario):
        from datetime import date

        return self.modules[
            "propagate_disruption"
        ].propagate(
            self.graph,
            self.tables,
            scenario.supplier_id,
            scenario.capacity_loss_percent,
            scenario.duration_days,
            date.fromisoformat(
                self.snapshot
            ),
        )

    def financial(self, impact, scenario):
        return self.modules[
            "financial_blast_radius"
        ].calculate_financial_exposure(
            impact,
            self.tables,
            scenario.assumed_delay_days,
            "0",
            scenario.daily_penalty_rate,
        )

    def mitigation(self, impact, scenario):
        return self.modules[
            "generate_mitigation_strategies"
        ].generate_options(
            impact,
            self.graph,
            self.tables,
            scenario.assumed_delay_days,
        )

    def optimize(
        self,
        impact,
        finance,
        candidates,
        scenario,
    ):
        v2 = self.modules[
            "optimize_mitigation_v2"
        ]

        ctx = v2.Context(
            self.tables,
            self.ext,
            impact,
            candidates,
            finance,
            scenario.route_capacity_mode,
        )

        result = v2.optimize_v2(
            ctx,
            service_cost_cents=(
                scenario.uncovered_unit_cost_cents
            ),
            time_limit_seconds=(
                scenario.time_limit_seconds
            ),
        )

        if result["status"] not in (
            "OPTIMAL",
            "FEASIBLE",
        ):
            raise RuntimeError(
                f"No usable solver plan: {result['status']}"
            )

        audit = v2.audit_plan(
            ctx,
            result["plan"],
            scenario.uncovered_unit_cost_cents,
        )

        if (
            audit != result["audit"]
            or audit["status"] != "PASSED"
        ):
            raise ValueError(
                "Independent plan audit failed"
            )

        result["actions_executed"] = False
        result["recommendation_only"] = True

        return result

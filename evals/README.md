# WeatherGuard Evaluation Suite

This suite evaluates the real LangGraph entry point, `PolicyEngine`, Open-Meteo client seam, typed EvidencePack, response composer, session checkpointing, and YAML registry. It is designed to discover safety regressions rather than make a screenshot look successful.

## Run

From the repository root:

```powershell
python -m pytest -q
python evals/run_evals.py
```

The runner writes the detailed report to `evals/reports/latest_report.md` and exits nonzero if any case is `FAIL`.

## Evaluation strategy

The suite separates weather-dependent behavior into two classes:

- **Live:** Open-Meteo is called for Tokyo. The suite asserts that returned normalized values reach the EvidencePack and response path. It does not require a particular forecast or policy winner.
- **Deterministic:** WeatherSnapshots are synthesized from thresholds read directly from the loaded YAML registry. These cases cover severe conditions, routine conditions, boundaries, multiple matches, and conflict resolution. They remain valid when weather events disappear.

The live severe-weather case reports `NOT_APPLICABLE` when current weather does not satisfy a severe SOP. That is not converted into PASS or FAIL. The deterministic severe case still verifies severe policy behavior every run.

## Cases

The catalog in `cases.yaml` contains 20 cases covering clear SOP matches, paraphrases, live weather, deterministic severe behavior, no-policy behavior, service failures, adversarial inputs, session memory, conflict resolution, boundaries, grounding, hot reload, and invalid policy files.

Each report entry contains the test ID, category, input, expected behavior, actual behavior, selected SOP, normalized weather evidence, status, and explanation.

## Honest reporting

Only assertions that execute successfully are marked `PASS`. A live service outage or a calm live forecast can produce `NOT_APPLICABLE` where the case explicitly allows it. An implementation defect produces `FAIL`, and the runner exits with status 1.

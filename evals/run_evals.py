from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from evals.evaluator import EvalResult, WeatherGuardEvaluator


def write_report(results: list[EvalResult]) -> Path:
    report_dir = Path(__file__).resolve().parent / "reports"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / "latest_report.md"
    counts = {status: sum(result.status == status for result in results) for status in ["PASS", "FAIL", "NOT_APPLICABLE"]}
    with report_path.open("w", encoding="utf-8") as report:
        report.write("# WeatherGuard Evaluation Report\n\n")
        report.write(f"Run: {datetime.now(timezone.utc).isoformat()}\n\n")
        report.write(f"Summary: PASS={counts['PASS']} FAIL={counts['FAIL']} NOT_APPLICABLE={counts['NOT_APPLICABLE']} TOTAL={len(results)}\n\n")
        report.write("The live severe-weather case is intentionally allowed to be NOT_APPLICABLE when current Open-Meteo data does not satisfy a severe SOP. Deterministic severe tests use thresholds loaded from YAML, so the suite remains valid after weather events change.\n\n")
        for result in results:
            report.write(f"## {result.test_id} — {result.name}\n\n")
            report.write(f"**Category:** `{result.category}`  \n")
            report.write(f"**Input:** {result.input}  \n")
            report.write(f"**Expected:** {result.expected}  \n")
            report.write(f"**Actual:** {result.actual}  \n")
            report.write(f"**Selected SOP:** `{result.selected_sop or 'none'}`  \n")
            report.write(f"**Weather:** {result.weather}  \n")
            report.write(f"**Result:** **{result.status}**  \n")
            report.write(f"**Explanation:** {result.explanation}\n\n")
    return report_path


async def main() -> int:
    evaluator = WeatherGuardEvaluator()
    results = await evaluator.run_all()
    report_path = write_report(results)
    for result in results:
        print(f"[{result.status}] {result.test_id} {result.name}: {result.explanation}")
    counts = {status: sum(result.status == status for result in results) for status in ["PASS", "FAIL", "NOT_APPLICABLE"]}
    print(f"SUMMARY PASS={counts['PASS']} FAIL={counts['FAIL']} NOT_APPLICABLE={counts['NOT_APPLICABLE']} TOTAL={len(results)}")
    print(f"REPORT {report_path}")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

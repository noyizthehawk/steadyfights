# refresh_data.py

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

CAREER_TRAJECTORY = "part_2/improvement_velocity.py"

POST_SCRAPE_STEPS = [
    ("Clean raw data", "data_clean.py"),
    ("Build fighter-level CSV", "part_2/part_2_data_prep.py"),
]


def run_step(label: str, script: str) -> None:
    """Run one pipeline step as its own process, exactly like `python <script>`.

    sys.executable = the SAME interpreter running this file, so the sub-step
    inherits our venv (avoids the "ModuleNotFoundError: passlib" class of bug
    from using the wrong python). check=True turns any non-zero exit into a
    raised CalledProcessError, so the FIRST failure halts the whole refresh
    instead of letting later steps run on stale/half-written data.
    """
    print(f"\n=== {label} ({script}) ===", flush=True)
    subprocess.run([sys.executable, script], cwd=PROJECT_ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh all UFC model data.")
    parser.add_argument(
        "--no-scrape",
        action="store_true",
        help="Skip the slow network scrape; just reprocess existing data.",
    )
    args = parser.parse_args()

    try:
        if args.no_scrape:
            # Reprocess what's already on disk: clean -> data_prep -> opp strength.
            for label, script in POST_SCRAPE_STEPS:
                run_step(label, script)
        else:
            # Full pipeline. Update_fights.py already does scrape -> transform ->
            # clean -> data_prep, so we reuse it rather than re-list those steps.
            run_step("Scrape + clean + build (Update_fights.py)", "Update_fights.py")

        # The missing final step, run in BOTH modes.
        run_step("Career trajectory / opponent strength", CAREER_TRAJECTORY)

    except subprocess.CalledProcessError as e:
        # A step exited non-zero. Say which one and stop with a failure code so
        # callers (and a future /api/admin/refresh endpoint) can detect it.
        print(
            f"\n Refresh FAILED at: {' '.join(str(p) for p in e.cmd)} "
            f"(exit code {e.returncode}). Earlier steps' output is above; "
            f"later steps were NOT run.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\n Data refreshed. Restart the backend so train() picks up the new CSVs.")


if __name__ == "__main__":
    main()

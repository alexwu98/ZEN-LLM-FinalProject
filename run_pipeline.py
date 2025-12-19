import argparse
import subprocess
import sys
import csv
from datetime import datetime
from pathlib import Path

"""
File to run the entire pipeline for immediate results and convenience.
Exports results to CSV for convenience of viewing results, especially over multiple runs.
"""

root = Path(__file__).resolve().parent

scripts = {
    "export": root / "src" / "01_export_patch.py",
    "mutate": root / "src" / "02_mutate_patch.py",
    "llm": root / "src" / "03_llm_repair.py",        # infer repair plan via LLM
    "repair": root / "src" / "03_repair_patch.py",   # apply plan deterministically
    "to_pkl": root / "src" / "04_json_to_pkl.py",
    "break_demo": root / "src" / "05_break_demo.py",
    "compare": root / "src" / "06_compare_original_vs_repaired.py",
}


def run(script: Path, extra_args=None, capture=False):
    extra_args = extra_args or []
    if not script.exists():
        raise FileNotFoundError(f"Missing script: {script}")

    print(f"\n--- Running: {script.relative_to(root)} {' '.join(extra_args)} ---")
    cmd = [sys.executable, str(script)] + extra_args

    if capture:
        return subprocess.run(
            cmd,
            cwd=str(root),
            check=True,
            text=True,
            capture_output=True,
        )

    subprocess.run(cmd, cwd=str(root), check=True)
    return None


def main():
    ap = argparse.ArgumentParser(
        description="Run the ZEN schema-drift + LLM repair pipeline."
    )

    ap.add_argument("--trials", type=int, default=1,
                    help="Number of trials to run (default: 1).")
    ap.add_argument("--skip-export", action="store_true",
                    help="Skip 01_export_patch.py if already done.")
    ap.add_argument("--skip-llm", action="store_true",
                    help="Skip 03_llm_repair.py (LLM plan generation).")
    ap.add_argument("--skip-compare", action="store_true",
                    help="Skip original-vs-repaired comparison step.")
    ap.add_argument("--mutate-mode", default=None,
                    help="Forward --mode to 02_mutate_patch.py.")
    ap.add_argument("--order",
                    choices=["rename_then_wrap", "wrap_then_rename", "random"],
                    default=None,
                    help="Forward --order to 02_mutate_patch.py.")

    args = ap.parse_args()

    # Export once
    if not args.skip_export:
        run(scripts["export"])

    # Prepare results CSV (trimmed columns + running accuracy)
    results_path = root / "data" / "trial_results.csv"
    results_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        #"timestamp",
        "trial_id",
        "mode",
        "functions_keyset",
        "top_level_keys",
        "accuracy",
    ]

    new_file = not results_path.exists()
    csv_f = open(results_path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(csv_f, fieldnames=fieldnames)

    if new_file:
        writer.writeheader()

    trials = args.trials
    success_count = 0

    for t in range(trials):
        print(f"\n===== TRIAL {t + 1} / {trials} =====")

        # Build mutation args
        mutate_args = [
            "--seed", str(t),
            "--trial-id", str(t),
        ]

        if args.mutate_mode:
            mutate_args += ["--mode", args.mutate_mode]
        if args.order:
            mutate_args += ["--order", args.order]

        run(scripts["mutate"], mutate_args)

        if not args.skip_llm:
            run(scripts["llm"])

        run(scripts["repair"])
        run(scripts["to_pkl"])
        if trials == 1:
            run(scripts["break_demo"])  # Tons of terminal bloat. If multiple runs, just skip.

        # Defaults in case compare is skipped
        functions_keyset = "SKIPPED"
        top_level_keys = "SKIPPED"

        if not args.skip_compare:
            res = run(scripts["compare"], capture=True)
            out = res.stdout or ""

            if "PASS: functions keyset EXACT MATCH" in out:
                functions_keyset = "PASS"
            elif "FAIL: functions keyset DIFFER" in out:
                functions_keyset = "FAIL"

            if "PASS: top-level patch keys match" in out:
                top_level_keys = "PASS"
            elif "FAIL: top-level patch keys differ" in out:
                top_level_keys = "FAIL"

        print("\n[FUNCTIONS KEYSET CHECK]")
        print(f"  {functions_keyset}: functions keyset")
        print("\n[TOP-LEVEL PATCH KEYS CHECK]")
        print(f"  {top_level_keys}: top-level patch keys")

        # Running accuracy. Count a success only if both checks pass
        trial_passed = (functions_keyset == "PASS") and (top_level_keys == "PASS")
        if trial_passed:
            success_count += 1
        accuracy = f"{success_count}/{t + 1}"

        writer.writerow({
            #"timestamp": datetime.now().isoformat(timespec="seconds"),
            "trial_id": t,
            "mode": args.mutate_mode or "default",
            "functions_keyset": functions_keyset,
            "top_level_keys": top_level_keys,
            "accuracy": accuracy,
        })
        csv_f.flush()

    csv_f.close()
    print(f"\nWrote trial summary: {results_path}")
    print("Pipeline completed successfully.")


if __name__ == "__main__":
    main()

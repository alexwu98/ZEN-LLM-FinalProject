import json
import os
from schema_drift_config import CANON_KEY, find_functions_key

# File paths
ORIGINAL_PATCH_PATH = os.path.join("data", "patch_reference.json")
MUTATED_PATCH_PATH = os.path.join("data", "patch_mutated.json")
REPAIRED_PATCH_PATH = os.path.join("data", "patch_repaired.json")
MUTATION_LOG_PATH = os.path.join("data", "mutation_log.json")


def load_patch(path: str) -> dict:
    """
    Load a JSON-wrapped patch file and return underlying patch dict.
    
    :param path: Path to JSON file
    :type path: str
    :return: Extracted patch dictionary
    :rtype: dict
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["patch"]


def main():
    original_patch = load_patch(ORIGINAL_PATCH_PATH)
    mutated_patch = load_patch(MUTATED_PATCH_PATH)
    repaired_patch = load_patch(REPAIRED_PATCH_PATH)

    # Select a representative function key 
    try:
        target_fn = next(iter(original_patch[CANON_KEY].keys()))
    except Exception:
        target_fn = None

    print("\n[ORIGINAL]")
    try:
        _ = original_patch[CANON_KEY][target_fn]
        print(f"OK: patch['{CANON_KEY}']['{target_fn}'] exists")
    except Exception as e:
        print(f"FAIL: patch['{CANON_KEY}']['{target_fn}'] -> {type(e).__name__}: {e}")

    print("\n[MUTATED]")

    # Access attempt using canonical key
    try:
        _ = mutated_patch[CANON_KEY][target_fn]
        print(
            f"OK: patch['{CANON_KEY}']['{target_fn}'] exists "
            "(unexpected if schema drift applied)"
        )
    except Exception as e:
        print(
            f"FAIL: patch['{CANON_KEY}']['{target_fn}'] "
            f"-> {type(e).__name__}: {e}"
        )

    # Access attempt using renamed functions key
    functions_container_key = find_functions_key(mutated_patch)
    if functions_container_key and functions_container_key != CANON_KEY:
        try:
            _ = mutated_patch[functions_container_key]
            print(
                f"INFO: functions container appears under renamed key: "
                f"'{functions_container_key}'"
            )
        except Exception as e:
            print(
                f"FAIL: renamed functions key lookup '{functions_container_key}' "
                f"-> {type(e).__name__}: {e}"
            )

    print("\n[REPAIRED]")
    try:
        _ = repaired_patch[CANON_KEY][target_fn]
        print(f"OK: patch['{CANON_KEY}']['{target_fn}'] exists")
    except Exception as e:
        print(
            f"FAIL: patch['{CANON_KEY}']['{target_fn}'] "
            f"-> {type(e).__name__}: {e}"
        )


if __name__ == "__main__":
    main()

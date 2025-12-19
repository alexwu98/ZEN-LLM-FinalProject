import json
import os
import argparse
import random
from datetime import datetime

from schema_drift_config import CANON_KEY, RENAME_VARIANTS, WRAPPER_VARIANTS, EXTRA_STRUCT_KEYS

# File paths for the incoming, outgoing, JSON patches and the outgoing log
IN_JSON = os.path.join("data", "patch_reference.json")
OUT_JSON = os.path.join("data", "patch_mutated.json")
OUT_LOG = os.path.join("data", "mutation_log.json")


def main():
    # Parse the CLI arguments for the drifts to mutate the patch
    parser = argparse.ArgumentParser(
        description="Apply controlled schema drift to ZEN patch dictionary"
    )
    parser.add_argument(
        "--mode",
        choices=["wrapper", "rename", "extra", "both", "all", "random"],
        default="wrapper",
        help=(
            "wrapper: wrap functions dict under a wrapper key\n"
            "rename: rename 'functions' key to a variant\n"
            "extra: add ignorable extra structural dict alongside functions\n"
            "both: rename + wrapper\n"
            "all: rename + wrapper + extra\n"
            "random: randomly choose which drift types to apply"
        ),
    )
    parser.add_argument("--seed", type=int, default=None, help="Seed for reproducible randomness.")
    parser.add_argument("--trial-id", type=int, default=None, help="Optional identifier for logging.")
    parser.add_argument(
        "--order",
        choices=["rename_then_wrap", "wrap_then_rename", "random"],
        default="random",
        help="Order of operations when both rename and wrapper are applied.",
    )

    args = parser.parse_args()

    # Assign Seeds for Later Reproducability
    if args.seed is not None:
        random.seed(args.seed)

    with open(IN_JSON, "r", encoding="utf-8") as f:
        obj = json.load(f)

    # Note: we mutate obj["patch"] in-place so the __meta__ wrapper is preserved.
    patch = obj["patch"]

    # Check if patch contains the canonical key first before doing anything
    if CANON_KEY not in patch:
        raise KeyError(f"Expected top-level key '{CANON_KEY}' not found in patch_reference.json.")

    # Options for possible drifts for mutation
    if args.mode == "random":
        use_rename = random.choice([True, False])
        use_wrap = random.choice([True, False])
        use_extra = random.choice([True, False])

        # Ensure at least one drift happens
        if not (use_rename or use_wrap or use_extra):
            use_wrap = True
    else:
        use_wrap = args.mode in ("wrapper", "both", "all")
        use_rename = args.mode in ("rename", "both", "all")
        use_extra = args.mode in ("extra", "all")

    # Select parameters for each drift option
    if use_rename:
        # Choose a rename target that doesn't already exist as a top-level key.
        candidates = [k for k in RENAME_VARIANTS if k not in patch]
        if not candidates:
            raise RuntimeError("No available rename targets")
        rename_to = random.choice(candidates)
    else:
        rename_to = None

    wrapper_key = random.choice(WRAPPER_VARIANTS) if use_wrap else None
    extra_key = random.choice(EXTRA_STRUCT_KEYS) if use_extra else None

    # Determine operation order only when both rename and wrap are used
    if use_rename and use_wrap:
        if args.order == "random":
            op_order = random.choice(["rename_then_wrap", "wrap_then_rename"])
        else:
            op_order = args.order
    else:
        op_order = "n/a"

    # Add ignorable struct (does not contain any relevant info for recovery)
    def add_extra_struct(container: dict):
        """
        Adds an extra top-level dict that should be ignored by canonical consumers.
        This simulates non-semantic structural drift (extra fields).
        """
        if not extra_key:
            return
        if extra_key in container:
            return

        container[extra_key] = {
            "note": "extra_struct noise field (ignorable)",
            "trial_id": args.trial_id,
            "seed": args.seed,
        }

    def current_functions_key(p: dict) -> str:
        """
        Returns the key name that currently holds the functions container.
        (Either the canonical key or one of the rename variants.)
        """
        if CANON_KEY in p:
            return CANON_KEY
        for k in RENAME_VARIANTS:
            if k in p:
                return k
        raise KeyError("Could not locate functions dict under canonical or known renamed keys.")

    if not isinstance(patch[CANON_KEY], dict):
        raise TypeError(f"Expected patch['{CANON_KEY}'] to be a dict.")

    # Apply the drifts to the patch in chosen order
    if use_rename and use_wrap:
        if op_order == "rename_then_wrap":
            if rename_to and CANON_KEY in patch and rename_to not in patch:
                patch[rename_to] = patch.pop(CANON_KEY)
            functions_key = current_functions_key(patch)
            if not isinstance(patch[functions_key], dict):
                raise TypeError(f"Expected patch['{functions_key}'] to be a dict before wrapping.")
            patch[functions_key] = {wrapper_key: patch[functions_key]}
            add_extra_struct(patch)

        elif op_order == "wrap_then_rename":
            patch[CANON_KEY] = {wrapper_key: patch[CANON_KEY]}
            if rename_to and CANON_KEY in patch and rename_to not in patch:
                patch[rename_to] = patch.pop(CANON_KEY)
            add_extra_struct(patch)

        else:
            raise ValueError(f"Unexpected op_order: {op_order}")

    elif use_rename:
        if rename_to and CANON_KEY in patch and rename_to not in patch:
            patch[rename_to] = patch.pop(CANON_KEY)
        add_extra_struct(patch)

    elif use_wrap:
        functions_key = current_functions_key(patch)
        if not isinstance(patch[functions_key], dict):
            raise TypeError(f"Expected patch['{functions_key}'] to be a dict before wrapping.")
        patch[functions_key] = {wrapper_key: patch[functions_key]}
        add_extra_struct(patch)

    elif use_extra:
        add_extra_struct(patch)

    else:
        raise RuntimeError("No mutation applied.")

    # Write patch and mutation log
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

    mutation_log = {
        "trial_id": args.trial_id,
        "seed": args.seed,
        "mode": args.mode,
        "use_rename": use_rename,
        "rename_to": rename_to,
        "use_wrap": use_wrap,
        "wrapper_key": wrapper_key,
        "use_extra_struct": use_extra,
        "extra_struct_key": extra_key,
        "order": op_order,
    }

    with open(OUT_LOG, "w", encoding="utf-8") as f:
        json.dump(mutation_log, f, indent=2, ensure_ascii=False)

    print("Mutation complete.")
    print(json.dumps(mutation_log, indent=2))


if __name__ == "__main__":
    main()

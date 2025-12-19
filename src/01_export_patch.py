import json
import os
import pickle
from datetime import datetime
from typing import Any

import numpy as np
import torch

# File paths for the pikl files and the final output
INPUT_PKL = os.path.join("data", "patch_original.pkl")
OUTPUT_JSON = os.path.join("data", "patch_reference.json")


def to_jsonable(obj: Any, max_str_len: int = 5000) -> Any:
    """
    Converts a Python object into something that can be serialized as a JSON.
    
    :param obj: Object to convert
    :type obj: Any
    :param max_str_len: Max length for strings before truncation to prevent bloat
    :type max_str_len: int
    :return: JSON-serializable representation of obj
    :rtype: Any
    """
    # Already JSON-serializable
    if obj is None or isinstance(obj, (bool, int, float, str)):
        if isinstance(obj, str) and len(obj) > max_str_len:
            return obj[:max_str_len] + "...(truncated)"
        return obj

    # Store the size and preview
    if isinstance(obj, (bytes, bytearray)):
        return {
            "__type__": "bytes",
            "len": len(obj),
            "preview_hex": bytes(obj[:64]).hex(),
        }

    # Dicts with string keys
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v, max_str_len=max_str_len) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(x, max_str_len=max_str_len) for x in obj]

    # Numpy Arrays
    if isinstance(obj, np.ndarray):
        return {
            "__type__": "ndarray",
            "dtype": str(obj.dtype),
            "shape": list(obj.shape),
        }

    # Torch Tensors
    if isinstance(obj, torch.Tensor):
        return {
            "__type__": "torch.Tensor",
            "dtype": str(obj.dtype),
            "shape": list(obj.shape),
            "device": str(obj.device),
        }

    # Unknown objects of other types
    r = repr(obj)
    if len(r) > 2000:
        r = r[:2000] + "...(truncated)"
    return {"__type__": type(obj).__name__, "repr": r}


def main():
    if not os.path.exists(INPUT_PKL):
        raise FileNotFoundError(f"Missing input pickle: {INPUT_PKL}")

    with open(INPUT_PKL, "rb") as f:
        patch = pickle.load(f)

    # Patch type for debugging
    print("Patch type:", type(patch))

    if hasattr(patch, "keys"):
        keys = list(patch.keys())
        print("Top-level keys:")
        for k in keys:
            print("  -", k)
    else:
        print("Patch has no top-level keys attribute (not a dict-like object)")

    # Build the export object
    export = {
        "__meta__": {
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "input_pickle": INPUT_PKL,
            "patch_type": str(type(patch)),
        },
        "patch": to_jsonable(patch),
    }

    # Write the JSON to the disk
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(
            export,
            f,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )

    print(f"\nExported to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()

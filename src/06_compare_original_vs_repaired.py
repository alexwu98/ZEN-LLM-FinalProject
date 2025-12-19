import json
import os
import hashlib
from typing import Dict, Any, Tuple, List

from schema_drift_config import CANON_KEY, EXTRA_STRUCT_KEYS

ORIG_JSON = os.path.join("data", "patch_reference.json")
REPAIRED_JSON = os.path.join("data", "patch_repaired.json")


def sha256_of_strings(strings: List[str]) -> str:
    """
    Compute a SHA-256 hash over ordered list of strings. SHA-256 needed as a 
    fingerprint of strucutre to compare and ensure the repaired patch is structurally
    identical to the original patch.
    
    :param strings: Strings to has in order.
    :type strings: List[str]
    :return: Hex digest of SHA-256 hash.
    :rtype: str
    """
    hash = hashlib.sha256()
    for s in strings:
        hash.update(s.encode("utf-8"))
        hash.update(b"\n")
    return hash.hexdigest()


def load_patch(path: str) -> Dict[str, Any]:
    """
    Load a JSON-wrapped patch file and return underlying patch dict.
    
    :param path: Path to JSON field
    :type path: str
    :return: Extracted patch dictionary
    :rtype: Dict[str, Any]
    """
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj["patch"]


def summarize_functions(patch: Dict[str, Any]) -> Tuple[int, List[str], str]:
    """
    Summarize functions container by various parameters (count, sorted keys, keyset hash).
    
    :param patch: Patch dictionary to be summarized
    :type patch: Dict[str, Any]
    :return: Number of function keys, sorted list of function keys, SHA-256 hash of sorted keys
    :rtype: Tuple[int, List[str], str]
    """
    fns = patch.get(CANON_KEY, {})
    if not isinstance(fns, dict):
        return (0, [], "NOT_A_DICT")
    keys = sorted(fns.keys())
    return (len(keys), keys, sha256_of_strings(keys))


def sample_field_checks(orig: Dict[str, Any], repaired: Dict[str, Any], fn_name: str) -> List[str]:
    """
    Compare small set of fields for single function record
    
    :param orig: Original canonical patch
    :type orig: Dict[str, Any]
    :param repaired: Repaired patch
    :type repaired: Dict[str, Any]
    :param fn_name: Function key to compare
    :type fn_name: str
    :return: Comparison lines to show if matched or different. 
    :rtype: List[str]
    """
    logs: List[str] = []

    o = orig.get(CANON_KEY, {}).get(fn_name)
    r = repaired.get(CANON_KEY, {}).get(fn_name)

    if not isinstance(o, dict) or not isinstance(r, dict):
        return [f"Sample '{fn_name}': missing or not dict"]

    fields = [
        "func_module",
        "func_qualname",
        "co_argcount",
        "co_kwonlyargcount",
        "co_flags",
    ]

    for k in fields:
        ov = o.get(k)
        rv = r.get(k)
        logs.append(
            f"  {fn_name}.{k}: {'MATCH' if ov == rv else 'DIFF'} "
            f"(orig={ov!r}, repaired={rv!r})"
        )

    o_code = o.get("co_code", {})
    r_code = r.get("co_code", {})
    if isinstance(o_code, dict) and isinstance(r_code, dict):
        for k in ["len", "preview_hex"]:
            ov = o_code.get(k)
            rv = r_code.get(k)
            logs.append(
                f"  {fn_name}.co_code.{k}: {'MATCH' if ov == rv else 'DIFF'}"
            )

    return logs


def main():
    orig = load_patch(ORIG_JSON)
    repaired = load_patch(REPAIRED_JSON)

    o_n, o_keys, o_hash = summarize_functions(orig)
    r_n, r_keys, r_hash = summarize_functions(repaired)

    print("[FUNCTIONS KEYSET CHECK]")
    print(f"  original functions count: {o_n}")
    print(f"  repaired  functions count: {r_n}")
    print(f"  original keys sha256: {o_hash}")
    print(f"  repaired  keys sha256: {r_hash}")

    if o_keys == r_keys:
        print("  PASS: functions keyset EXACT MATCH")
    else:
        print("  FAIL: functions keyset DIFFER")
        o_set = set(o_keys)
        r_set = set(r_keys)
        print(f"    missing in repaired: {sorted(list(o_set - r_set))[:25]}")
        print(f"    extra in repaired:   {sorted(list(r_set - o_set))[:25]}")

    # Top level key check. Ignore the noise keys.
    print("\n[TOP-LEVEL PATCH KEYS CHECK]")
    o_top = sorted([k for k in orig.keys() if k not in EXTRA_STRUCT_KEYS])
    r_top = sorted([k for k in repaired.keys() if k not in EXTRA_STRUCT_KEYS])

    if o_top == r_top:
        print("  PASS: top-level patch keys match (excluding ignorable noise)")
    else:
        print("  FAIL: top-level patch keys differ (excluding ignorable noise)")
        print(f"    missing in repaired: {sorted(list(set(o_top) - set(r_top)))[:25]}")
        print(f"    extra in repaired:   {sorted(list(set(r_top) - set(o_top)))[:25]}")

    """sample_name = (
        "emojis"
        if "emojis" in orig.get(CANON_KEY, {})
        else (o_keys[0] if o_keys else None)
    )"""

    sample_name = o_keys[0] if o_keys else None

    print(f"\n[SAMPLE FUNCTION FIELD CHECK: {sample_name}]")
    if sample_name is None:
        print("  No functions available to sample.")
    else:
        for line in sample_field_checks(orig, repaired, sample_name):
            print(line)


if __name__ == "__main__":
    main()

from typing import Optional
CANON_KEY = "functions"

RENAME_VARIANTS = [
    "function",
    "Functions",
    "funcs",
    "fn_map",
    "function_map",
    "functions_map",
    "functions_dict",
]

WRAPPER_VARIANTS = [
    "wrapper",
    "new_wrapper",
    "new_schema",
    "new_layout",
    "wrapped",
    "temp_wrapper",
]

EXTRA_STRUCT_KEYS = [
    "extra_struct_1",
    "extra_struct_2",
    "temp_block",
    "temp_struct",
]


def find_functions_key(patch: dict) -> Optional[str]:
    """Return the key under which the functions container currently lives."""
    if CANON_KEY in patch:
        return CANON_KEY
    for k in RENAME_VARIANTS:
        if k in patch:
            return k
    return None


def find_wrapper_key(functions_container: dict) -> Optional[str]:
    """Return a wrapper key if the functions container is wrapped."""
    if not isinstance(functions_container, dict):
        return None
    for k in WRAPPER_VARIANTS:
        v = functions_container.get(k)
        if isinstance(v, dict):
            return k
    return None

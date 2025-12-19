import json
import os

from schema_repair_patcher import SchemaRepairPatcher

IN_JSON = os.path.join("data", "patch_mutated.json")
IN_PLAN = os.path.join("data", "repair_plan.json")
OUT_JSON = os.path.join("data", "patch_repaired.json")


def main():
    # Apply deterministic fixes to the mutated patch from the plan given by the LLM
    with open(IN_JSON, "r", encoding="utf-8") as f:
        obj = json.load(f)

    with open(IN_PLAN, "r", encoding="utf-8") as f:
        plan = json.load(f)

    patch = obj["patch"]

    engine = SchemaRepairPatcher()
    logs = engine.apply_plan_to_patch(patch, plan)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

    print(f"Wrote: {OUT_JSON}")
    print("Applied actions:")
    for line in logs:
        print(" ", line)


if __name__ == "__main__":
    main()




'''
def get_at_path(root: Dict[str, Any], path: List[str]) -> Any:
    cur: Any = root
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            raise KeyError(f"Path not found: {path} (missing '{key}')")
        cur = cur[key]
    return cur


def set_at_path(root: Dict[str, Any], path: List[str], value: Any) -> None:
    if not path:
        raise ValueError("set_at_path: empty path not supported for this helper.")
    cur: Any = root
    for key in path[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[path[-1]] = value


def apply_unwrap(root_patch: Dict[str, Any], path: List[str], wrapper_key: str) -> bool:

    parent = get_at_path(root_patch, path)
    if not isinstance(parent, dict):
        return False
    if wrapper_key not in parent:
        return False
    inner = parent[wrapper_key]
    if not isinstance(inner, dict):
        return False

    set_at_path(root_patch, path, inner)
    return True


def apply_actions(patch: Dict[str, Any], actions: List[Dict[str, Any]]) -> List[str]:
    logs: List[str] = []

    for i, action in enumerate(actions):
        op = action.get("op")
        if op == "unwrap":
            path = action.get("path", [])
            wrapper_key = action.get("wrapper_key")
            if not isinstance(path, list) or not wrapper_key:
                logs.append(f"[{i}] unwrap: invalid action schema -> skipped")
                continue

            applied = apply_unwrap(patch, path, wrapper_key)
            logs.append(f"[{i}] unwrap {path} wrapper='{wrapper_key}': {'APPLIED' if applied else 'NOOP'}")

        elif op == "rename_key":
            path = action.get("path", [])
            src = action.get("from")
            dst = action.get("to")

            try:
                target = patch if path == [] else get_at_path(patch, path)
                if isinstance(target, dict) and src in target and dst not in target:
                    target[dst] = target.pop(src)
                    logs.append(f"[{i}] rename_key {path}: '{src}' -> '{dst}': APPLIED")
                else:
                    logs.append(f"[{i}] rename_key {path}: '{src}' -> '{dst}': NOOP")
            except Exception as e:
                logs.append(f"[{i}] rename_key: ERROR {e}")

        else:
            logs.append(f"[{i}] unknown op '{op}': skipped")

    return logs


def main():
    with open(IN_MUTATED, "r", encoding="utf-8") as f:
        obj = json.load(f)

    with open(IN_PLAN, "r", encoding="utf-8") as f:
        plan = json.load(f)

    patch = obj["patch"]
    actions = plan.get("actions", [])

    logs = apply_actions(patch, actions)

    out_obj = {"patch": patch}
    with open(OUT_REPAIRED, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, indent=2, ensure_ascii=False)

    print(f"Wrote: {OUT_REPAIRED}")
    print("Applied actions:")
    for line in logs:
        print("  " + line)
'''

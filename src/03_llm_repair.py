import json
import os

from schema_repair_patcher import SchemaRepairPatcher

IN_JSON = os.path.join("data", "patch_mutated.json")
OUT_PLAN = os.path.join("data", "repair_plan.json")


def main():
    # Infer a schema repair plan from LLM
    with open(IN_JSON, "r", encoding="utf-8") as f:
        obj = json.load(f)

    patch = obj["patch"]

    engine = SchemaRepairPatcher()
    plan = engine.infer_plan_from_patch(patch)

    with open(OUT_PLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(f"Wrote: {OUT_PLAN}")
    print("Inferred actions:")
    for a in plan.get("actions", []):
        print(" ", a)


if __name__ == "__main__":
    main()


'''from google import genai

from schema_drift_config import (
    CANON_KEY,
    RENAME_VARIANTS,
    WRAPPER_VARIANTS,
    EXTRA_STRUCT_KEYS,
    find_functions_key,
    find_wrapper_key,
)

IN_JSON = os.path.join("data", "patch_mutated.json")
OUT_PLAN = os.path.join("data", "repair_plan.json")
MODEL_ID = "models/gemini-2.0-flash"


def extract_excerpt(patch: dict) -> dict:
    excerpt = {
        "top_level_patch_keys_sample": list(patch.keys())[:40],
        "has_canonical_functions": CANON_KEY in patch,
        "possible_renamed_functions_keys_present": [k for k in RENAME_VARIANTS if k in patch],
        "extra_struct_keys_present": [k for k in EXTRA_STRUCT_KEYS if k in patch],
    }

    functions_key = find_functions_key(patch)
    excerpt["functions_container_key"] = functions_key

    functions = patch.get(functions_key) if functions_key else None

    if isinstance(functions, dict):
        excerpt["functions_container_keys_sample"] = list(functions.keys())[:25]

        wk = find_wrapper_key(functions)
        excerpt["wrapper_key_detected"] = wk

        if wk and isinstance(functions.get(wk), dict):
            excerpt["wrapper_inner_keys_sample"] = list(functions[wk].keys())[:25]
    else:
        excerpt["functions_container_type"] = str(type(functions))

    return excerpt


def extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in Gemini output.")
    return text[start : end + 1]


def main():
    with open(IN_JSON, "r", encoding="utf-8") as f:
        obj = json.load(f)

    patch = obj["patch"]
    excerpt = extract_excerpt(patch)

    prompt = f"""
You are diagnosing schema drift in a recovered patch dictionary.

Canonical requirements:
- patch must contain a key named "{CANON_KEY}"
- patch["{CANON_KEY}"] must be a dict mapping function_name -> function_record
- patch["{CANON_KEY}"] must NOT be wrapped under an extra layer (e.g., patch["{CANON_KEY}"]["<wrapper>"])
- Extra top-level keys may exist and should be ignored unless they replace "{CANON_KEY}"

Observed excerpt from mutated patch (schema-only, not full content):
{json.dumps(excerpt, indent=2)}

Return ONLY valid JSON with schema:

{{
  "actions": [
    {{
      "op": "rename_key",
      "path": [],
      "from": "<current_functions_key>",
      "to": "{CANON_KEY}"
    }},
    {{
      "op": "unwrap",
      "path": ["{CANON_KEY}"],
      "wrapper_key": "<wrapper_key>"
    }}
  ]
}}

Rules:
- Include ONLY actions that are necessary based on the excerpt.
- If "{CANON_KEY}" is missing but a renamed key is present, include rename_key.
- If "{CANON_KEY}" is present and appears wrapped, include unwrap using the detected wrapper key.
- Do NOT include actions for extra_struct keys; they are ignorable noise.
- If no repair is needed, return {{ "actions": [] }}.
""".strip()

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
    )

    raw_text = (response.text or "").strip()
    json_text = extract_json_object(raw_text)
    plan = json.loads(json_text)

    with open(OUT_PLAN, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print(f"Wrote repair plan to {OUT_PLAN}")
    print("LLM repair plan:")
    print(json.dumps(plan, indent=2))'''
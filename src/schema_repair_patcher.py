import json
import os
from typing import Any, Dict, List

from google import genai

from schema_drift_config import (
    CANON_KEY,
    EXTRA_STRUCT_KEYS,
    RENAME_VARIANTS,
    find_functions_key,
    find_wrapper_key,
)


class SchemaRepairPatcher:
    """
    Core logic for inferring a repair plan from a mutated patch by handing off to an LLM (Gemini 2.0 in this case). 
    Using that plan, apply it deterministically in order to produce a repaired patch.
    """

    def __init__(self, model_id: str = "models/gemini-2.0-flash", api_key_env: str = "GEMINI_API_KEY"):
        """
        Initializes the SchemaRepairPatcher with LLM configuration.

        :param model_id: Gemini model ID used 
        :type model_id: str
        :param api_key_env: Environment variable name containing the Gemini API key
        :type api_key_env: str
        """
        self.model_id = model_id
        self.api_key_env = api_key_env


    def extract_excerpt(self, patch: dict) -> dict:
        """
        Extracts a small, schema-only excerpt from a recovered patch dictionary. 
        Does not include full content and is condensed due to restrictions with API usage limts
        and input restrictions. 

        :param patch: The full recovered patch dictionary
        :type patch: dict
        :return: A compact JSON-serializable excerpt 
        :rtype: dict
        """
        excerpt: Dict[str, Any] = {
            "top_level_patch_keys_sample": list(patch.keys())[:40],
            "has_canonical_functions": CANON_KEY in patch,
            "possible_renamed_functions_keys_present": [k for k in RENAME_VARIANTS if k in patch],
            "extra_struct_keys_present": [k for k in EXTRA_STRUCT_KEYS if k in patch],
        }

        # Identify where the "functions container" currently lives 
        functions_key = find_functions_key(patch)
        excerpt["functions_container_key"] = functions_key

        functions_container = patch.get(functions_key) if functions_key else None
        excerpt["functions_container_type"] = str(type(functions_container))

        if isinstance(functions_container, dict):
            keys = list(functions_container.keys())
            excerpt["functions_container_keys_sample"] = keys[:25]

            # Wrapper detection from known wrapper variants
            wk = find_wrapper_key(functions_container)
            excerpt["wrapper_key_detected_by_list"] = wk

            # Strong heuristic for determining wrapper schema. 
            # If single-key dict and inner is dict, then assume wrapper schema
            if len(keys) == 1 and isinstance(functions_container.get(keys[0]), dict):
                heuristic_wrapper_key = keys[0]
                excerpt["single_key_wrapper_heuristic"] = {
                    "wrapper_key": heuristic_wrapper_key,
                    "inner_keys_sample": list(functions_container[heuristic_wrapper_key].keys())[:25],
                }

        return excerpt

    def infer_plan_from_patch(self, patch: dict) -> dict:
        """
        Uses an LLM (Gemini) to infer a minimal repair plan for schema drift.

        :param patch: The mutated patch dictionary to diagnose
        :type patch: dict
        :return: A repair plan dict with schema describing deterministic edits
        :rtype: dict
        :raises RuntimeError: If the Gemini API key env var is missing
        :raises ValueError: If the LLM output cannot be parsed as a valid plan
        """
        excerpt = self.extract_excerpt(patch)

        # Prompt to feed the LLM. Developed by asking Gemini what would be a good prompt 
        # when fed the mutated JSON with the options of possible scehma drift. 
        prompt = f"""
You are diagnosing schema drift in a recovered patch dictionary.

Canonical requirements:
- patch must contain a key named "{CANON_KEY}"
- patch["{CANON_KEY}"] must be a dict mapping function_name -> function_record
- patch["{CANON_KEY}"] must NOT be wrapped under an extra layer
- Extra top-level keys may exist and should be ignored unless they replace "{CANON_KEY}"

Observed excerpt from mutated patch (schema-only, not full content):
{json.dumps(excerpt, indent=2)}

Return ONLY valid JSON with schema:

{{
  "actions": [
    {{
      "op": "rename_key",
      "path": [],
      "from": "<use excerpt.functions_container_key>",
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
- Include ONLY actions necessary based on the excerpt.
- If "{CANON_KEY}" is missing but a renamed key is present, include rename_key using that key.
- If the functions container appears wrapped:
  - Prefer wrapper_key from "single_key_wrapper_heuristic.wrapper_key" if present.
  - Otherwise use a wrapper key that appears under the functions container.
- Do NOT include actions for extra_struct keys; they are ignorable noise.
- Do not propose renames to keys other than "{CANON_KEY}".
- Return at most one rename_key action and at most one unwrap action.
- If wrapper_key_detected_by_list is non-null, include an unwrap action using that wrapper_key.
- If no repair is needed, return {{ "actions": [] }}.
""".strip()

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"Missing environment variable: {self.api_key_env}")

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=self.model_id, contents=prompt)

        raw_text = (response.text or "").strip()
        json_text = self._extract_json_object(raw_text)
        plan = json.loads(json_text)

        # Validating plan output to make sure it is viable
        if not isinstance(plan, dict) or "actions" not in plan or not isinstance(plan["actions"], list):
            raise ValueError("LLM returned invalid plan shape (expected dict with 'actions': list).")

        return plan


    def apply_plan_to_patch(self, patch: dict, plan: dict) -> List[str]:
        """
        Applies a repair plan deterministically to a patch.

        :param patch: Patch dictionary to modify (mutated input)
        :type patch: dict
        :param plan: Repair plan dict returned by the LLM 
        :type plan: dict
        :return: Human-readable logs describing which actions were applied / no-op / skipped
        :rtype: List[str]
        :raises ValueError: If plan["actions"] is not a list
        """
        actions = plan.get("actions", [])
        if not isinstance(actions, list):
            raise ValueError("Plan 'actions' must be a list.")

        # Ensure deterministic order. Rename first, then unwrap
        priority = {"rename_key": 0, "unwrap": 1}
        actions = sorted(actions, key=lambda a: priority.get(a.get("op") if isinstance(a, dict) else None, 99))

        logs: List[str] = []

        for i, a in enumerate(actions):
            if not isinstance(a, dict):
                logs.append(f"[{i}] invalid action (not a dict). Skipped")
                continue

            op = a.get("op")

            if op == "rename_key":
                src = a.get("from")
                dst = a.get("to")

                if not src or not dst:
                    logs.append(f"[{i}] rename_key missing from/to. Skipped")
                    continue

                if src in patch and dst not in patch:
                    patch[dst] = patch.pop(src)
                    logs.append(f"[{i}] rename_key '{src}' -> '{dst}'. Applied")
                else:
                    logs.append(f"[{i}] rename_key '{src}' -> '{dst}'. No change")

            elif op == "unwrap":
                path = a.get("path", [])
                wrapper_key = a.get("wrapper_key")

                if path != [CANON_KEY] or not wrapper_key:
                    logs.append(f"[{i}] unwrap invalid (path/wrapper_key). Skipped")
                    continue

                container = patch.get(CANON_KEY)
                if isinstance(container, dict) and wrapper_key in container and isinstance(container[wrapper_key], dict):
                    patch[CANON_KEY] = container[wrapper_key]
                    logs.append(f"[{i}] unwrap ['{CANON_KEY}'] wrapper='{wrapper_key}'. Applied")
                else:
                    logs.append(f"[{i}] unwrap ['{CANON_KEY}'] wrapper='{wrapper_key}'. No change")

            else:
                logs.append(f"[{i}] unknown op '{op}'. Skipped")

        return logs

    def _extract_json_object(self, text: str) -> str:
        """
        Extracts the first JSON object substring from raw model output text.

        :param text: Raw model output that may contain extra prose
        :type text: str
        :return: Substring containing the first JSON object
        :rtype: str
        :raises ValueError: If no JSON object boundaries are found
        """
        # Strip Markdown code fences if present
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            # Remove first and last fence lines
            if len(lines) >= 3:
                stripped = "\n".join(lines[1:-1]).strip()

        # Try to parse entire string
        try:
            json.loads(stripped)
            return stripped
        except Exception:
            pass

        # If it can't parse entire string, extract first {...} block
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in LLM output.")

        candidate = stripped[start : end + 1]

        # Final validation
        try:
            json.loads(candidate)
            return candidate
        except Exception as e:
            raise ValueError(f"Extracted JSON is invalid: {e}")

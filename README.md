# ZEN-LLM Schema Repair (Final Project)

This project demonstrates a minimal, LLM-guided compatibility layer for repairing **schema drift** in recovered **ZEN patch dictionaries**.  
Given a valid ZEN patch, we (1) simulate structural drift, (2) use an LLM to infer a minimal repair plan from a **schema-only excerpt**, and (3) apply repairs deterministically to restore ZEN’s canonical layout.

## Repository Structure

- `src/`
  - `01_export_patch.py` — export canonical patch (`.pkl`) to JSON (`patch_reference.json`)
  - `02_mutate_patch.py` — apply controlled schema drift to generate `patch_mutated.json`
  - `03_llm_repair.py` — call Gemini to infer `repair_plan.json` from schema-only excerpt
  - `03_repair_patch.py` — apply plan deterministically to produce `patch_repaired.json`
  - `04_json_to_pkl.py` — convert mutated/repaired JSON back to `.pkl`
  - `05_break_demo.py` — demonstrate canonical access break + repair success
  - `06_compare_original_vs_repaired.py` — structural equivalence checks (PASS/FAIL)
  - `schema_drift_config.py` — canonical schema + drift variants + helper detection
  - `schema_repair_patcher.py` — core class: excerpt extraction, LLM plan inference, deterministic executor
- `data/`
  - inputs/outputs for pipeline runs (JSON/PKL/logs/CSV)
- `run_pipeline.py`
  - end-to-end runner with `--trials` support + CSV summary

## Environment / Requirements

Tested on:
- Windows 10/11
- Python 3.10+ (recommended)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Full Pipeline

The primary driver for this project is `run_pipeline.py`, which executes the full schema-drift simulation and repair workflow end-to-end. This script orchestrates all stages of the pipeline, including patch export, schema mutation, LLM-guided repair planning, deterministic repair execution, and structural equivalence evaluation.

All multi-trial results are recorded in `data/trial_results.csv`.

Run the 30 trial experiment that was reported in the paper:

```bash
python run_pipeline.py --skip-export --trials 30 --mutate-mode random
```

---

## Basic Usage

Run a single trial of the full pipeline:

```bash
python run_pipeline.py
```
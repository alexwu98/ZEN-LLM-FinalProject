import json
import os
import pickle


def convert(json_path: str, pkl_path: str):
    """
    Convert a JSON-wrapped patch into a pickle file containing only the underlying patch dictionary

    :param json_path: Path to JSON file
    :type json_path: str
    :param pkl_path: Destination path for output pickle
    :type pkl_path: str
    """
    with open(json_path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    patch = obj["patch"]
    with open(pkl_path, "wb") as f:
        pickle.dump(patch, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Wrote: {pkl_path}")


def main():
    convert(os.path.join("data", "patch_mutated.json"), os.path.join("data", "patch_mutated.pkl"))
    convert(os.path.join("data", "patch_repaired.json"), os.path.join("data", "patch_repaired.pkl"))

    # Sanity-load
    for p in ["data/patch_mutated.pkl", "data/patch_repaired.pkl"]:
        with open(p, "rb") as f:
            obj = pickle.load(f)
        print("\nLoaded:", p)
        print("  type:", type(obj))
        print("  has keys:", hasattr(obj, "keys"))
        if hasattr(obj, "keys"):
            print("  top keys (first 10):", list(obj.keys())[:10])
            if "functions" in obj:
                fn = obj["functions"]
                print("  functions type:", type(fn))
                if isinstance(fn, dict):
                    print("  functions keys (first 10):", list(fn.keys())[:10])

if __name__ == "__main__":
    main()

"""Reproduce or verify the shipped model and synthetic dataset."""

from pathlib import Path
import argparse
import csv
import io
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from machine_learning import FEATURE_NAMES, build_model, generate_profiles, models_equivalent  # noqa: E402


def expected_files() -> dict[Path, str]:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["id", "split", *FEATURE_NAMES, "label"])
    for row in generate_profiles():
        writer.writerow([row.identifier, row.split, *row.features, row.label])
    return {
        ROOT / "data/model.json": json.dumps(build_model(), indent=2) + "\n",
        ROOT / "data/synthetic_profiles.csv": output.getvalue(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify without modifying files")
    args = parser.parse_args()
    for path, content in expected_files().items():
        if args.check:
            matches = False
            if path.exists():
                actual = path.read_text(encoding="utf-8")
                try:
                    matches = (
                        models_equivalent(json.loads(actual), json.loads(content))
                        if path.suffix == ".json"
                        else actual == content
                    )
                except json.JSONDecodeError:
                    pass
            if not matches:
                parser.exit(1, f"Model/data differ from reproducible output: {path.name}\n")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print("Model and synthetic dataset verified." if args.check else "Model and synthetic dataset written.")


if __name__ == "__main__":
    main()

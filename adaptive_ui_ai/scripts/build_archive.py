"""Build a reproducible source ZIP from an explicit file allowlist, without README."""

import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ".gitignore",
    "app.py",
    "machine_learning.py",
    "pyproject.toml",
    "LICENSE.txt",
    "SOURCE_CREDITS.txt",
    "MODEL_CARD.txt",
    "DESIGN_NOTES.txt",
    "MAC_AND_GITHUB_STEPS.txt",
    "data/lessons.json",
    "data/model.json",
    "data/synthetic_profiles.csv",
    "web/index.html",
    "web/styles.css",
    "web/app.js",
    "web/model.mjs",
    "web/adaptation.mjs",
    "scripts/train_model.py",
    "scripts/build_archive.py",
    "tests/test_project.py",
    "tests/adaptation.test.mjs",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/AdaptiveStudy_AI_Source.zip")
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.suffix != ".zip" or destination in {(ROOT / name).resolve() for name in FILES}:
        parser.error("Output must be a separate .zip file.")
    for relative in FILES:
        if not (ROOT / relative).is_file():
            parser.exit(1, f"Required file missing: {relative}\n")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(FILES):
            info = zipfile.ZipInfo(f"adaptive_ui_ai/{relative}", date_time=(2026, 10, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (ROOT / relative).read_bytes())
    print(f"Created {destination} with {len(FILES)} project files; no README.")


if __name__ == "__main__":
    main()

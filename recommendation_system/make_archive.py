"""Package an explicit source allowlist; never package credentials or .venv."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent


def build_archive(destination: Path | None = None) -> Path:
    output = destination or ROOT / "dist" / "recommendation_system.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    files = [ROOT / name for name in
             ("app.py", "engine.py", "requirements.txt", ".gitignore", "make_archive.py")]
    # Directory patterns are narrow so screenshots and unknown files are excluded.
    for directory, pattern in (("data", "*.json"), ("web", "*.html"),
                               ("web", "*.css"), ("web", "*.js"), ("tests", "test_*.py")):
        files.extend(sorted((ROOT / directory).glob(pattern)))
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for source in files:
            archive.write(source, Path("recommendation_system") / source.relative_to(ROOT))
    return output


if __name__ == "__main__":
    print(build_archive())

"""Create a clean source archive using an explicit safe file allowlist."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_FILES: tuple[str, ...] = (
    "README.md", ".gitignore", "requirements.txt", "app.py", "engine.py", "make_archive.py",
    "static/index.html", "static/style.css", "static/app.js",
    "tests/test_engine.py", "tests/test_http.py",
)
OPTIONAL_EVIDENCE: tuple[str, ...] = (
    "evidence/assistant_validation.txt", "evidence/windows_validation.txt",
)


def create_archive(output: Path) -> Path:
    """Include known project sources and validation logs, never an entire repo."""
    output = output.resolve()
    if output.suffix.lower() != ".zip":
        raise ValueError("The archive output filename must end in .zip.")
    paths = list(PROJECT_FILES)
    paths.extend(name for name in OPTIONAL_EVIDENCE if (PROJECT_ROOT / name).is_file())
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = ["Source archive SHA-256 manifest", ""]
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_name in paths:
            data = (PROJECT_ROOT / relative_name).read_bytes()
            archive_name = f"traditional_chatbot/{relative_name}"
            archive.writestr(archive_name, data)
            manifest.append(f"{hashlib.sha256(data).hexdigest()}  {archive_name}")
        archive.writestr("traditional_chatbot/ARCHIVE_MANIFEST.txt", "\n".join(manifest) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive only chatbot source files and validation evidence.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "dist" / "traditional_chatbot.zip")
    arguments = parser.parse_args()
    output = create_archive(arguments.output)
    print(f"Created {output}")
    print("Excluded virtual environments, Git history, credentials, unrelated repo files, and existing archives.")
    print("Review any validation evidence for private information before submission.")


if __name__ == "__main__":
    main()

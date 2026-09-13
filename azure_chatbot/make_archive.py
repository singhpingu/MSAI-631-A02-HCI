"""Build a source ZIP from a fixed allowlist; never recursively archive credentials."""

import argparse
import hashlib
from pathlib import Path
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_FILES = (
    ".gitignore", "requirements.txt", "app.py", "engine.py", "hybrid.py",
    "azure_service.py", "smoke_test.py", "make_archive.py",
    "static/index.html", "static/style.css", "static/app.js",
    "tests/test_engine.py", "tests/test_http.py", "tests/test_hybrid.py", "tests/test_azure.py", "tests/test_sdk.py",
)


def create_archive(output: Path) -> Path:
    output = output.resolve()
    if output.suffix.lower() != ".zip":
        raise ValueError("The output filename must end in .zip.")
    files = list(PROJECT_FILES)
    evidence = PROJECT_ROOT / "evidence" / "assistant_validation.txt"
    if evidence.is_file():
        files.append("evidence/assistant_validation.txt")
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = ["Azure chatbot source archive SHA-256 manifest", ""]
    # Read all source files before writing, so a missing required file fails early.
    sources = [(name, (PROJECT_ROOT / name).read_bytes()) for name in files]
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sources:
            archive_name = f"azure_chatbot/{name}"
            archive.writestr(archive_name, data)
            manifest.append(f"{hashlib.sha256(data).hexdigest()}  {archive_name}")
        archive.writestr("azure_chatbot/ARCHIVE_MANIFEST.txt", "\n".join(manifest) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archive only the Azure chatbot's known source files.")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "dist" / "azure_chatbot.zip")
    args = parser.parse_args()
    print(f"Created {create_archive(args.output)}")
    print("Excluded environment files, credentials, virtual environments, Git history, and local logs.")

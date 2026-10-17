"""Explicit source allowlist, shared by handoff and native release packaging."""
from pathlib import Path
import zipfile

ROOT_FILES = (
    ".gitignore", ".gitattributes", ".env.example", "README.md", "README.en.md", "DESKTOP.md",
    "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md",
    "pyproject.toml", "requirements.txt", "requirements-desktop.txt",
    "requirements-desktop-lock.txt", "requirements-macos.txt", "run_desktop.py",
    "SOURCE_MANIFEST.json", "MANIFEST.in", "20261016-141343.png",
)
FOLDERS = ("desktop", "mystery", "scripts", "tests", "examples", "docs", "licenses")
EXTENSIONS = {".py", ".js", ".mjs", ".cjs", ".json", ".html", ".css", ".md", ".yml",
              ".txt", ".svg", ".png", ".jpg", ".ico", ".icns", ".iss", ".spec", ".plist"}


def source_files(root):
    root = Path(root)
    files = [root / name for name in ROOT_FILES]
    for name in ("LICENSE", "COPYRIGHT"):
        if (root / name).is_file():
            files.append(root / name)
    for path in (root / ".github").rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".yml"}:
            files.append(path)
    for folder in FOLDERS:
        for path in (root / folder).rglob("*"):
            relative = path.relative_to(root)
            if (not path.is_file() or path.is_symlink()
                    or any(part.startswith(".") or part in {"__pycache__", "node_modules"}
                           for part in relative.parts)):
                continue
            if path.suffix.lower() in EXTENSIONS or "LICENSE" in path.name or path.name.endswith("-NOTICE"):
                files.append(path)
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Source path escapes project: {path}")
    return sorted(set(files), key=lambda p: p.relative_to(root).as_posix())


def write_source_zip(root, destination):
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source_files(root):
            archive.write(path, path.relative_to(root).as_posix())

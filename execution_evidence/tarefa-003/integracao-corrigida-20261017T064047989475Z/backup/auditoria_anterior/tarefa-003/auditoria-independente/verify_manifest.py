"""Verificador independente do manifesto desta análise, sem alterar arquivos cobertos."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys


def main():
    root = Path(__file__).resolve().parent
    manifest_path = root / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    errors = []
    excluded = {"manifest.json", "manifest-verification.json", "manifest-verification.log"}
    if set(manifest["excluded"]) != excluded:
        errors.append({"code": "unexpected_exclusions"})
    entries = manifest["entries"]
    names = [entry["path"] for entry in entries]
    if len(names) != len(set(names)):
        errors.append({"code": "duplicate_manifest_paths"})
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    expected = set(names)
    for name in sorted(expected - actual):
        errors.append({"code": "missing_file", "path": name})
    for name in sorted(actual - expected - excluded):
        errors.append({"code": "unexpected_file", "path": name})
    for entry in entries:
        path = root / entry["path"]
        if not path.resolve().is_relative_to(root) or path.is_symlink():
            errors.append({"code": "unsafe_path", "path": entry["path"]})
            continue
        if not path.is_file():
            continue
        if path.stat().st_size != entry["size_bytes"]:
            errors.append({"code": "size_mismatch", "path": entry["path"]})
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest != entry["sha256"]:
            errors.append({"code": "hash_mismatch", "path": entry["path"]})
    result = {
        "command": [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        "cwd": str(Path.cwd()),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "checked_files": len(entries),
        "errors": errors,
        "returncode": 1 if errors else 0,
    }
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    (root / "manifest-verification.json").write_text(output, encoding="utf-8")
    print(output, end="")
    return result["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())

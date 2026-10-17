from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
root = Path(__file__).resolve().parent
manifest_path = root / "manifest.json"
blob = manifest_path.read_bytes()
manifest = json.loads(blob)
excluded = {"manifest.json", "manifest-verification.json", "manifest-verification.log"}
errors = []
if set(manifest["excluded"]) != excluded:
    errors.append({"code": "invalid_exclusions"})
entries = manifest["entries"]
expected = {e["path"] for e in entries}
if len(entries) != len(expected):
    errors.append({"code": "duplicate_paths"})
actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
for name in sorted(expected - actual):
    errors.append({"path": name, "code": "missing_file"})
for name in sorted(actual - expected - excluded):
    errors.append({"path": name, "code": "unexpected_file"})
for entry in entries:
    path = root / entry["path"]
    if not path.resolve().is_relative_to(root) or path.is_symlink():
        errors.append({"path": entry["path"], "code": "unsafe_path"})
        continue
    if not path.is_file():
        continue
    if path.stat().st_size != entry["size_bytes"]:
        errors.append({"path": entry["path"], "code": "size_mismatch"})
    with path.open("rb") as source:
        value = hashlib.file_digest(source, "sha256").hexdigest()
    if value != entry["sha256"]:
        errors.append({"path": entry["path"], "code": "hash_mismatch"})
result = {"command": [sys.executable, str(Path(__file__).resolve())],
          "cwd": str(Path.cwd()), "finished_utc": datetime.now(timezone.utc).isoformat(),
          "manifest_sha256": hashlib.sha256(blob).hexdigest(),
          "checked_files": len(entries), "errors": errors,
          "returncode": 1 if errors else 0}
output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
(root / "manifest-verification.json").write_text(output, encoding="utf-8")
print(output, end="")
raise SystemExit(result["returncode"])

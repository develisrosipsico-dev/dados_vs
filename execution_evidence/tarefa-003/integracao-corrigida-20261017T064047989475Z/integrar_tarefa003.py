#!/usr/bin/env python3
"""Integra o pacote verificado da Tarefa 003, preservando as cópias anteriores.

Não processa PDFs nem altera o corpus. Usa somente a biblioteca padrão neste
script; os testes e o CLI usam o interpretador do ambiente do projeto.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

PACKAGE_SHA256 = "4f43d19bf336462f4db257d06f2ef4548f4f6bca6cf482213c9a195ae4034228"
TEST_SHA256 = "a5adc3d498d04ec96dfd28203589a324522aa02f65388fdba173dacfaf0e4010"
PDF_SHA256 = "dabd10538ffdc866c6fa24187ffb1b9f784f647a01d5286a9c6a91cd7015633d"
CORPUS_VERSION = "corpus_9be43285a4ba3bc831b26b9e"
AUDIT_PREFIX = "execution_evidence/tarefa-003/auditoria-independente/"
EXCLUDED = {"manifest.json", "manifest-verification.json", "manifest-verification.log"}


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def snapshot(folder):
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Link simbólico não esperado no corpus: {path}")
        if path.is_file():
            result[path.relative_to(folder).as_posix()] = {
                "size_bytes": path.stat().st_size, "sha256": digest(path)
            }
    return result


def validate_archive(package):
    if not package.is_file():
        raise RuntimeError(f"ZIP não encontrado: {package}")
    if digest(package) != PACKAGE_SHA256:
        raise RuntimeError("O SHA-256 do ZIP difere do pacote auditado; nada foi integrado.")
    with ZipFile(package) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("Entradas duplicadas no ZIP")
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in item.filename
                    or stat.S_ISLNK(item.external_attr >> 16)):
                raise RuntimeError(f"Entrada insegura: {item.filename}")
        manifest = json.loads(archive.read(AUDIT_PREFIX + "manifest.json"))
        if set(manifest["excluded"]) != EXCLUDED:
            raise RuntimeError("Exclusões inesperadas no manifesto")
        expected = {"tests/test_tarefa_003.py"} | {AUDIT_PREFIX + p for p in EXCLUDED}
        for entry in manifest["entries"]:
            name = AUDIT_PREFIX + entry["path"]
            expected.add(name)
            data = archive.read(name)
            if len(data) != entry["size_bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise RuntimeError(f"Integridade inválida no ZIP: {name}")
        if set(names) != expected:
            raise RuntimeError("Inventário inesperado no ZIP")
        data = archive.read("tests/test_tarefa_003.py")
        if (hashlib.sha256(data).hexdigest() != TEST_SHA256
                or data != archive.read(AUDIT_PREFIX + "tests/test_tarefa_003.py")):
            raise RuntimeError("Teste do pacote não corresponde ao arquivo auditado")
    return manifest


def check_restored_audit(folder, manifest):
    """Somente leitura; mantém inclusive os comprovantes originais do pacote."""
    errors = []
    expected = {entry["path"] for entry in manifest["entries"]}
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    for name in sorted(expected - actual):
        errors.append({"path": name, "code": "missing_file"})
    for name in sorted(actual - expected - EXCLUDED):
        errors.append({"path": name, "code": "unexpected_file"})
    for entry in manifest["entries"]:
        path = folder / entry["path"]
        if not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):
            errors.append({"path": entry["path"], "code": "unsafe_path"})
            continue
        if path.stat().st_size != entry["size_bytes"]:
            errors.append({"path": entry["path"], "code": "size_mismatch"})
        if digest(path) != entry["sha256"]:
            errors.append({"path": entry["path"], "code": "hash_mismatch"})
    return {"checked_files": len(expected), "errors": errors}


VERIFIER = r'''from pathlib import Path
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
'''


def finish_manifest(run_dir):
    (run_dir / "verify_integration_manifest.py").write_text(VERIFIER, encoding="utf-8")
    entries = []
    for path in sorted(run_dir.rglob("*")):
        name = path.relative_to(run_dir).as_posix()
        if path.is_file() and name not in EXCLUDED:
            data = path.read_bytes()
            entries.append({"path": name, "size_bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()})
    write_json(run_dir / "manifest.json", {"created_utc": now(), "entries": entries,
                                           "excluded": sorted(EXCLUDED)})
    with (run_dir / "manifest-verification.log").open("w", encoding="utf-8") as output:
        result = subprocess.run([sys.executable, str(run_dir / "verify_integration_manifest.py")],
                                cwd=run_dir, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Manifesto de integração divergiu: {run_dir}")
    return json.loads((run_dir / "manifest-verification.json").read_text(encoding="utf-8"))


def junit_counts(path):
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    return {"collected": len(cases),
            "passed": sum(not any(c.find(tag) is not None for tag in ("failure", "error", "skipped")) for c in cases),
            "failed": sum(c.find("failure") is not None for c in cases),
            "errors": sum(c.find("error") is not None for c in cases),
            "skipped": sum(c.find("skipped") is not None for c in cases)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path("/Users/rodrigodevellis/dados_vs"))
    parser.add_argument("--zip", dest="package", type=Path,
                        default=Path.home() / "Downloads/tarefa003_regularizada.zip")
    parser.add_argument("--python", dest="python", type=Path)
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        raise RuntimeError("Execute este script com o Python 3.11+ do ambiente do projeto.")
    project = args.project.expanduser().resolve()
    package = args.package.expanduser().resolve()
    manifest = validate_archive(package)
    # Não resolver o link bin/python: isso pode perder a identificação do venv.
    python = (args.python or project / ".venv/bin/python").expanduser().absolute()
    if not python.is_file():
        raise RuntimeError(f"Interpretador não encontrado: {python}")
    corpus = project / "corpora/corpora/story-capitulo-1-revisao-documental-v0.2.3"
    metadata = json.loads((corpus / "metadata.json").read_text(encoding="utf-8"))
    if metadata["corpus_version"] != CORPUS_VERSION:
        raise RuntimeError("O corpus local não é a versão autorizada.")
    if digest(project / "story-capitulo-1.pdf") != PDF_SHA256:
        raise RuntimeError("O PDF local difere da fonte autorizada.")

    run_dir = project / "execution_evidence/tarefa-003" / (
        "integracao-corrigida-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_dir.mkdir(parents=True, exist_ok=False)
    backup = run_dir / "backup"
    backup.mkdir()
    shutil.copyfile(Path(__file__).resolve(), run_dir / "integrar_tarefa003.py")
    before = snapshot(corpus)
    write_json(run_dir / "corpus_before.json", before)
    result = {"started_utc": now(), "project": str(project), "zip_sha256": digest(package),
              "operational_status": "blocked", "errors": [], "commands": []}
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONPATH"] = str(project / "src") + os.pathsep + env.get("PYTHONPATH", "")

    def run(label, arguments, expected=(0,)):
        command = [str(python), *map(str, arguments)]
        output = run_dir / (label + ".log")
        started = now()
        print(f"Executando {label}...", flush=True)
        with output.open("w", encoding="utf-8") as log:
            process = subprocess.run(command, cwd=project, env=env,
                                     stdout=log, stderr=subprocess.STDOUT)
        record = {"argv": command, "cwd": str(project), "started_utc": started,
                  "finished_utc": now(), "returncode": process.returncode,
                  "expected_returncodes": list(expected), "output": output.name,
                  "env_overrides": {k: env[k] for k in ("PYTHONPATH", "PYTEST_DISABLE_PLUGIN_AUTOLOAD")},
                  "removed_env_keys": ["PYTEST_ADDOPTS"]}
        result["commands"].append(record)
        with (run_dir / "commands.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
        if process.returncode not in expected:
            print(output.read_text(encoding="utf-8", errors="replace")[-5000:], flush=True)
            raise RuntimeError(f"{label}: retorno {process.returncode}; consulte {output}")
        return output

    try:
        canonical = project / "tests/test_tarefa_003.py"
        duplicate = project / "tests/test_tarefa_003_integrado.py"
        if canonical.exists():
            shutil.copyfile(canonical, backup / "test_tarefa_003_anterior.py")
        if duplicate.exists():
            shutil.move(str(duplicate), backup / "test_tarefa_003_integrado.py")
        audit_folder = project / AUDIT_PREFIX.rstrip("/")
        if audit_folder.exists():
            shutil.move(str(audit_folder), backup / "auditoria_anterior")
        with ZipFile(package) as archive:
            for name in archive.namelist():
                destination = project / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(name))
        if digest(canonical) != TEST_SHA256 or duplicate.exists():
            raise RuntimeError("O teste canônico ou a remoção da duplicata não foi confirmado.")
        audit_check = check_restored_audit(audit_folder, manifest)
        write_json(run_dir / "auditoria_restaurada_verificacao.json", audit_check)
        if audit_check["errors"]:
            raise RuntimeError("A auditoria restaurada não corresponde ao manifesto original.")

        environment_log = run("00-ambiente", ["-c", (
            "import json,sys; from importlib import metadata; "
            "print(json.dumps({'executable':sys.executable,'prefix':sys.prefix,"
            "'base_prefix':sys.base_prefix,'python':sys.version,"
            "'dependencies':{n:metadata.version(n) for n in ('pytest','PyMuPDF')}}))"
        )])
        result["runtime"] = json.loads(environment_log.read_text(encoding="utf-8"))
        run("01-coleta", ["-m", "pytest", "--collect-only", "-q", "--color=no"])
        run("02-direcionados", ["-m", "pytest", "-vv", "--color=no", "--junitxml",
                                run_dir / "direcionados.xml", "tests/test_tarefa_003.py"])
        run("03-suite-completa", ["-m", "pytest", "-vv", "--color=no", "--junitxml",
                                  run_dir / "suite-completa.xml"])
        validation_log = run("04-validate", ["-m", "corpus_documental", "validate", corpus])
        ready_log = run("05-check-ready", ["-m", "corpus_documental", "check-ready", corpus], (2,))
        result["target_tests"] = junit_counts(run_dir / "direcionados.xml")
        result["full_suite"] = junit_counts(run_dir / "suite-completa.xml")
        validation = json.loads(validation_log.read_text(encoding="utf-8"))
        gate = json.loads(ready_log.read_text(encoding="utf-8"))
        result["documentary_status"] = validation["status"]
        result["chunking_gate"] = gate
        if (validation["status"] != "review_required" or gate["allowed"] is not False
                or gate["pending_review_count"] != 12 or gate["blocking_error_count"] != 0
                or validation["metrics"]["paragraphs"] != 72):
            raise RuntimeError("Estado documental ou gate divergiu da base autorizada.")
        target = result["target_tests"]
        full = result["full_suite"]
        if target != {"collected": 11, "passed": 11, "failed": 0, "errors": 0, "skipped": 0}:
            raise RuntimeError("Resultado direcionado divergiu da referência; valores reais preservados no resumo.")
        if full["collected"] != 101 or full["failed"] or full["errors"]:
            raise RuntimeError("Suíte divergiu dos 101 casos de referência; consulte a coleta e o XML reais.")
        result["operational_status"] = "executed_and_persisted"
        result["all_tests_passed_without_skips"] = full["skipped"] == 0
        result["human_approval_granted"] = False
        result["task_004_started"] = False
    except Exception as error:
        result["operational_status"] = "failed"
        result["errors"].append(str(error))
    finally:
        after = snapshot(corpus)
        write_json(run_dir / "corpus_after.json", after)
        result["corpus_unchanged"] = before == after
        if before != after:
            result["operational_status"] = "failed"
            result["errors"].append("Hashes do corpus divergiram entre início e fim.")
        result["finished_utc"] = now()
        write_json(run_dir / "resultado.json", result)

    proof = finish_manifest(run_dir)
    print("\nRESULTADO OBSERVADO:", flush=True)
    print(json.dumps({k: v for k, v in result.items() if k != "commands"}, ensure_ascii=False, indent=2))
    print(f"Manifesto local: {proof['checked_files']} arquivos, {len(proof['errors'])} divergências.")
    print(f"Evidências: {run_dir}")
    print("O script terminou nesta integração da Tarefa 003.")
    return 0 if result["operational_status"] == "executed_and_persisted" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"BLOQUEADO: {error}", file=sys.stderr)
        raise SystemExit(2)

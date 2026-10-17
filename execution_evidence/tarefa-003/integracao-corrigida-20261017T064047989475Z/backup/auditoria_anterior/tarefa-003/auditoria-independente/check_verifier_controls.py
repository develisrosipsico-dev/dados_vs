from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
root=Path(__file__).resolve().parent
results=[]
with tempfile.TemporaryDirectory() as location:
    folder=Path(location)
    shutil.copyfile(root/"verify_manifest.py",folder/"verify_manifest.py")
    sample=folder/"sample.txt"
    sample.write_bytes(b"original\n")
    entries=[]
    for p in (sample,folder/"verify_manifest.py"):
        blob=p.read_bytes()
        entries.append({"path":p.name,"size_bytes":len(blob),"sha256":hashlib.sha256(blob).hexdigest()})
    manifest={"entries":entries,"excluded":["manifest.json","manifest-verification.json","manifest-verification.log"]}
    (folder/"manifest.json").write_text(json.dumps(manifest))
    def check(name,expected,required=None):
        process=subprocess.run([sys.executable,str(folder/"verify_manifest.py")],cwd=folder,capture_output=True,text=True)
        result=json.loads(process.stdout)
        codes={e["code"] for e in result["errors"]}
        assert process.returncode==expected,(name,process.returncode,result)
        if required:assert required<=codes,(name,codes)
        results.append({"case":name,"returncode":process.returncode,"errors":result["errors"]})
    check("valid",0)
    sample.write_bytes(b"alterado\n")
    check("wrong_hash",1,{"hash_mismatch"})
    sample.write_bytes(b"larger_modified_file\n")
    check("wrong_size",1,{"hash_mismatch","size_mismatch"})
    sample.write_bytes(b"original\n")
    extra=folder/"unexpected.txt"
    extra.write_bytes(b"extra")
    check("unexpected_file",1,{"unexpected_file"})
    extra.unlink();sample.unlink()
    check("missing_file",1,{"missing_file"})
print(json.dumps({"scope":"Controles temporários do verificador; corpus e evidências reais intactos.","all_controls_passed":True,"cases":results},ensure_ascii=False,indent=2))

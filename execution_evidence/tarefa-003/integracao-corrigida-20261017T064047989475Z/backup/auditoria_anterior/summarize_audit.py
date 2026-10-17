from pathlib import Path
from datetime import datetime, timezone
from importlib import metadata as installed
import hashlib
import json
import platform
import sys
import xml.etree.ElementTree as ET
import pymupdf
from corpus_documental.storage import load_corpus
from corpus_documental.provenance import validate_map

project=Path.cwd()
root=Path(sys.argv[1])
base=project/"corpora/corpora/story-capitulo-1-revisao-documental-v0.2.3"
data=load_corpus(base)
meta=data["metadata"]
current=json.loads((root/"07-validate.log").read_text())
saved=json.loads((base/"validation_report.json").read_text())
nodes={n["node_id"]:n for n in data["structure"]["nodes"]}
paras={p["paragraph_id"]:p for p in data["paragraphs"]}
section_id="node_e1ee2dbacf6a8b0f6eeb1181"
scope=[p for p in data["paragraphs"] if p["section_id"]==section_id]
records=[]
for p in scope:
    records.append({k:p[k] for k in ("paragraph_id","paragraph_global_order","paragraph_local_order","classification","parent_id","chapter_id","section_id","previous_id","next_id","source_spans")}|{
        "local_pages":sorted({s["page_index"]+1 for s in p["source_spans"]}),
        "normalization_map_errors":validate_map(p),
        "text_raw_sha256":hashlib.sha256(p["text_raw"].encode()).hexdigest(),
        "text_clean_sha256":hashlib.sha256(p["text_clean"].encode()).hexdigest()})
quotes=[]
for e in data["elements"]:
    if e["kind"]!="block_quote":continue
    p=paras[e["paragraph_id"]]
    quotes.append({"element_id":e["element_id"],"paragraph_id":p["paragraph_id"],"global_order":p["paragraph_global_order"],"section_id":p["section_id"],"in_direct_scope":p["section_id"]==section_id,"reference_link_matches":p["quote_element_id"]==e["element_id"],"text_ownership":e["text_ownership"],"quality_status":e["quality_status"],"source_spans_match":e["source_spans"]==p["source_spans"]})
changes=[]
before=json.loads((root/"inputs_before.json").read_text())
for item in before["files"]:
    p=project/item["path"]
    now=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    if now!=item["sha256"]:changes.append({"path":item["path"],"before_sha256":item["sha256"],"after_sha256":now})
assert [c["path"] for c in changes]==["tests/test_tarefa_003.py"],changes
implementation=hashlib.sha256()
for path in sorted((project/"src/corpus_documental").glob("*.py")):
    implementation.update(path.name.encode()+b"\0"+path.read_bytes())
assert implementation.hexdigest()==meta["processing"]["implementation_sha256"]
fonts=[]
with pymupdf.open(project/"story-capitulo-1.pdf") as pdf:
    for index in (0,4,7,10):
        for block in pdf[index].get_text("dict")["blocks"]:
            for line in block.get("lines",[]):
                text="".join(s["text"] for s in line["spans"]).strip()
                if text in ("O PROBLEMA DA ESTÓRIA","O DECLÍNIO DA ESTÓRIA","A PERDA DO OFÍCIO","O IMPERATIVO DA ESTÓRIA","Boa estória bem contada"):
                    fonts.append({"local_page":index+1,"text":text,"bbox":line["bbox"],"spans":[{k:s[k] for k in ("text","font","size","flags","bbox")} for s in line["spans"]]})
def suite(name):
    xml=ET.parse(root/name).getroot()
    suites=[xml] if xml.tag=="testsuite" else list(xml.findall("testsuite"))
    return {key:sum(int(s.get(key,"0")) for s in suites) for key in ("tests","failures","errors","skipped")}
summary={
    "task":"tarefa-003",
    "operational_status":"verified_existing",
    "scope":"Intervalo direto 28–41; subseção filha posterior e revisões individuais das citações não aprovadas.",
    "completed_utc":datetime.now(timezone.utc).isoformat(),
    "corpus_version":meta["corpus_version"],
    "application_version":meta["processing"]["application_version"],
    "document_id":meta["document_id"],
    "pdf_sha256":meta["sha256"],
    "original_integral":"Não fornecido; vínculo externo preservado conforme source_context, sem revalidação independente das 493 páginas.",
    "source_context":meta["source_context"],
    "source_implementation_sha256":implementation.hexdigest(),
    "all_corpus_files_unchanged_since_receipt":True,
    "all_original_evidence_files_unchanged":True,
    "changed_received_files":changes,
    "section":nodes[section_id],
    "direct_record_count":len(records),
    "direct_local_pages":sorted({page for record in records for page in record["local_pages"]}),
    "records":records,
    "quotes":quotes,
    "section_quote_count":sum(q["in_direct_scope"] for q in quotes),
    "corpus_quote_count":len(quotes),
    "next_child_boundary":nodes["node_4f9c6d35163293a95053c9e4"],
    "junit_target":suite("target-final.xml"),
    "junit_full_suite":suite("full-suite.xml"),
    "runtime":{"python":sys.version,"platform":platform.platform(),"dependencies":{n:installed.version(n) for n in ("PyMuPDF","pytest","iniconfig","packaging","pluggy","Pygments")}},
    "validation":{"status":current["status"],"raw_integrity":current["raw_integrity"],"gate":current["chunking_gate"],"saved_report_semantically_matches_current":current==saved,"remaining_review_items":current["documentary_quality"]["review_items"],"human_approval_granted":False,"quote_reviews_approved":False},
    "pdf_heading_typography":fonts,
    "prior_local_test_run":"Não reconstituído. O novo resultado foi obtido nesta auditoria; afirmações anteriores de 90 casos não são reutilizadas como evidência.",
}
assert summary["junit_target"]=={"tests":11,"failures":0,"errors":0,"skipped":0}
assert summary["junit_full_suite"]=={"tests":101,"failures":0,"errors":0,"skipped":0}
assert len(records)==14 and summary["section_quote_count"]==2
assert current["chunking_gate"]["allowed"] is False
assert current["chunking_gate"]["pending_review_count"]==12
(root/"execution.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"operational_status":summary["operational_status"],"records":len(records),"section_quote_count":summary["section_quote_count"],"corpus_quote_count":len(quotes),"target":summary["junit_target"],"suite":summary["junit_full_suite"],"changed_received_files":changes,"implementation_matches_metadata":True,"stored_report_matches_revalidation":current==saved,"pdf_heading_typography":fonts},ensure_ascii=False,indent=2))

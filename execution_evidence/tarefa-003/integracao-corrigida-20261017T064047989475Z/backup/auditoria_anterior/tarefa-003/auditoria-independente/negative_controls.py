from copy import deepcopy
from pathlib import Path
import importlib.util
import json
from corpus_documental.storage import load_corpus

project = Path.cwd()
root = Path(__import__("sys").argv[1])
def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
old=module(root/"recebidos/tests/test_tarefa_003.py", "original_tarefa003")
new=module(project/"tests/test_tarefa_003.py", "corrected_tarefa003")
data=load_corpus(project/"corpora/corpora/story-capitulo-1-revisao-documental-v0.2.3")
new.test_block_quotes_and_references(data)
results=[]
for kind in ("forward_link", "reverse_link", "text_ownership", "pending_status"):
    candidate=deepcopy(data)
    p=next(p for p in candidate["paragraphs"] if p["paragraph_global_order"]==29)
    e=next(e for e in candidate["elements"] if e["element_id"]==p["quote_element_id"])
    if kind=="forward_link":p["quote_element_id"]="quote_inexistente"
    elif kind=="reverse_link":e["paragraph_id"]="para_inexistente"
    elif kind=="text_ownership":e["text_ownership"]="primary"
    else:e["quality_status"]="automated"
    try:
        old.test_block_quotes_and_references(candidate["elements"],candidate["paragraphs"])
        old_rejected=False
    except (AssertionError,KeyError):old_rejected=True
    try:
        new.test_block_quotes_and_references(candidate)
        new_rejected=False
    except (AssertionError,KeyError):new_rejected=True
    results.append({"mutation":kind,"original_rejected":old_rejected,"corrected_rejected":new_rejected})
    if not new_rejected:raise AssertionError("Mutação não detectada: "+kind)
print(json.dumps({"scope":"Somente cópias em memória; nenhum arquivo do corpus foi alterado.","controls":results},ensure_ascii=False,indent=2))

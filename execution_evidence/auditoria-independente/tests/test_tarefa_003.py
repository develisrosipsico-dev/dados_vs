"""Validação operacional do intervalo direto 28-41 da Tarefa 003.

Usa o corpus 0.2.3 existente e não aprova revisões humanas. A inspeção visual
é documentada separadamente, não simulada pela presença de arquivos PNG.
"""
import hashlib
import json
import math
from pathlib import Path

import pymupdf
import pytest

from corpus_documental.cli import main
from corpus_documental.inspection import get_paragraph
from corpus_documental.provenance import validate_map
from corpus_documental.storage import load_corpus
from corpus_documental.validation import validate_corpus

BASE_DIR = Path(__file__).resolve().parents[1]
CORPUS_DIR = BASE_DIR / "corpora/corpora/story-capitulo-1-revisao-documental-v0.2.3"
PDF_PATH = BASE_DIR / "story-capitulo-1.pdf"
EXPECTED_PDF_SHA256 = "dabd10538ffdc866c6fa24187ffb1b9f784f647a01d5286a9c6a91cd7015633d"
EXPECTED_CORPUS_VERSION = "corpus_9be43285a4ba3bc831b26b9e"
DOCUMENT_ID = "doc_68538e2dac8d252a47d272de"
SECTION_NODE_ID = "node_e1ee2dbacf6a8b0f6eeb1181"
CHAPTER_NODE_ID = "node_01abfd94af1f8ecc7a287936"
SECTION_TITLE = "O IMPERATIVO DA ESTÓRIA"
PREVIOUS_SECTION_NODE_ID = "node_74a997edbbc24ce02939270a"
NEXT_SUBSECTION_NODE_ID = "node_4f9c6d35163293a95053c9e4"


def sha256(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def index_by(records, key):
    result = {record[key]: record for record in records}
    assert len(result) == len(records), f"Valores duplicados em {key}"
    return result


def ancestry(data, node_id):
    nodes = index_by(data["structure"]["nodes"], "node_id")
    chain, visited = [], set()
    while node_id is not None:
        assert node_id not in visited, "Ciclo hierárquico"
        visited.add(node_id)
        node = nodes[node_id]
        chain.append(node)
        node_id = node["parent_id"]
    return list(reversed(chain))


def section_paragraphs(data):
    return [p for p in data["paragraphs"] if p["section_id"] == SECTION_NODE_ID]


@pytest.fixture(scope="module")
def corpus_data():
    return load_corpus(CORPUS_DIR)


def test_pdf_integrity_and_hash(corpus_data):
    assert sha256(PDF_PATH) == EXPECTED_PDF_SHA256
    assert sha256(CORPUS_DIR / "original.pdf") == EXPECTED_PDF_SHA256
    assert corpus_data["metadata"]["sha256"] == EXPECTED_PDF_SHA256
    with pymupdf.open(PDF_PATH) as pdf:
        assert len(pdf) == 18
    assert sha256(CORPUS_DIR / "pages_raw.jsonl") == corpus_data["metadata"]["processing"]["raw_pages_sha256"]


def test_corpus_version_and_metadata(corpus_data):
    metadata = corpus_data["metadata"]
    assert metadata["corpus_version"] == EXPECTED_CORPUS_VERSION
    assert metadata["processing"]["application_version"] == "0.2.3"
    assert metadata["document_id"] == DOCUMENT_ID
    assert metadata["page_count"] == 18
    assert metadata["selected_pages"] == list(range(18))
    assert len(corpus_data["paragraphs"]) == 72
    assert corpus_data["structure"]["corpus_version"] == EXPECTED_CORPUS_VERSION
    assert corpus_data["structure"]["document_id"] == DOCUMENT_ID
    assert metadata["source_context"]["page_index_offset"] == 18
    assert metadata["source_context"]["local_page_count"] == 18


def test_section_node_hierarchy(corpus_data):
    nodes = index_by(corpus_data["structure"]["nodes"], "node_id")
    node = nodes[SECTION_NODE_ID]
    assert (node["title"], node["kind"], node["level"]) == (SECTION_TITLE, "section", 3)
    assert node["parent_id"] == CHAPTER_NODE_ID
    assert [n["node_id"] for n in ancestry(corpus_data, SECTION_NODE_ID)] == [DOCUMENT_ID, CHAPTER_NODE_ID, SECTION_NODE_ID]
    assert nodes[CHAPTER_NODE_ID]["title"] == "O PROBLEMA DA ESTÓRIA"
    assert nodes[CHAPTER_NODE_ID]["kind"] == "chapter"
    assert node["element_id"] == "elem_e76300480d96eea39103df63"
    heading = index_by(corpus_data["elements"], "element_id")[node["element_id"]]
    assert heading["node_id"] == SECTION_NODE_ID
    assert heading["source_spans"] == node["source_spans"]
    assert heading["text_clean"] == SECTION_TITLE
    assert len(node["source_spans"]) == 1
    span = node["source_spans"][0]
    assert (span["page_index"], span["block_id"], span["char_start"], span["char_end"]) == (7, "p000007_b00000", 0, 23)


def test_section_contains_exactly_14_paragraphs(corpus_data):
    paragraphs = section_paragraphs(corpus_data)
    assert len(paragraphs) == 14
    assert len(index_by(paragraphs, "paragraph_id")) == 14
    assert len(index_by(paragraphs, "paragraph_global_order")) == 14
    assert {s["page_index"] for p in paragraphs for s in p["source_spans"]} == {7, 8, 9}
    for paragraph in paragraphs:
        assert paragraph["document_id"] == DOCUMENT_ID
        assert paragraph["parent_id"] == SECTION_NODE_ID
        assert paragraph["chapter_id"] == CHAPTER_NODE_ID


def test_paragraphs_global_order_sequence_and_lookup(corpus_data):
    paragraphs = section_paragraphs(corpus_data)
    assert [p["paragraph_global_order"] for p in paragraphs] == list(range(28, 42))
    assert [p["paragraph_local_order"] for p in paragraphs] == list(range(1, 15))
    for paragraph in paragraphs:
        chain = ancestry(corpus_data, paragraph["parent_id"])
        found = get_paragraph(corpus_data, paragraph["paragraph_id"])
        for key in ("paragraph_id", "text_raw", "text_clean", "source_spans"):
            assert found[key] == paragraph[key]
        assert found["hierarchy"] == [
            {key: n[key] for key in ("node_id", "kind", "title")} for n in chain
        ]


def test_paragraphs_chain_navigation_and_child_boundary(corpus_data):
    by_order = index_by(corpus_data["paragraphs"], "paragraph_global_order")
    for order in range(28, 42):
        current = by_order[order]
        previous, following = by_order[order - 1], by_order[order + 1]
        assert current["previous_id"] == previous["paragraph_id"]
        assert previous["next_id"] == current["paragraph_id"]
        assert current["next_id"] == following["paragraph_id"]
        assert following["previous_id"] == current["paragraph_id"]
    assert by_order[27]["section_id"] == PREVIOUS_SECTION_NODE_ID
    assert by_order[42]["section_id"] == NEXT_SUBSECTION_NODE_ID
    nodes = index_by(corpus_data["structure"]["nodes"], "node_id")
    child = nodes[NEXT_SUBSECTION_NODE_ID]
    assert (child["title"], child["kind"], child["level"], child["parent_id"]) == (
        "Boa estória bem contada", "subsection", 4, SECTION_NODE_ID
    )
    assert child["source_spans"][0]["page_index"] == 10
    first = by_order[28]["source_spans"][0]
    heading = nodes[SECTION_NODE_ID]["source_spans"][0]
    assert (heading["page_index"], heading["bbox"][3]) < (first["page_index"], first["bbox"][1])
    last = by_order[41]["source_spans"][-1]
    next_heading = child["source_spans"][0]
    assert (last["page_index"], last["bbox"][3]) < (next_heading["page_index"], next_heading["bbox"][1])
    assert [n["node_id"] for n in ancestry(corpus_data, by_order[42]["parent_id"])] == [
        DOCUMENT_ID, CHAPTER_NODE_ID, SECTION_NODE_ID, NEXT_SUBSECTION_NODE_ID
    ]


def test_source_spans_reconstruct_text_raw(corpus_data):
    pages = index_by(corpus_data["pages"], "page_index")
    for paragraph in section_paragraphs(corpus_data):
        assert paragraph["source_spans"]
        raw_parts = []
        for span in paragraph["source_spans"]:
            page = pages[span["page_index"]]
            block = index_by(page["blocks"], "block_id")[span["block_id"]]
            assert block["type"] == "text"
            a, b = span["char_start"], span["char_end"]
            x, y = span["block_char_start"], span["block_char_end"]
            assert 0 <= a < b <= len(page["text_raw"])
            assert 0 <= x < y <= len(block["text_raw"])
            assert (a, b) == (block["char_start"] + x, block["char_start"] + y)
            source = page["text_raw"][a:b]
            assert source == block["text_raw"][x:y]
            raw_parts.append(source)
            bbox = span["bbox"]
            assert len(bbox) == 4 and all(math.isfinite(v) for v in bbox)
            assert 0 <= bbox[0] <= bbox[2] <= page["width"]
            assert 0 <= bbox[1] <= bbox[3] <= page["height"]
        assert paragraph["text_raw"] == "\n".join(raw_parts)


def test_normalization_map_effective_validation(corpus_data):
    for paragraph in section_paragraphs(corpus_data):
        assert paragraph["normalization_map"]
        assert validate_map(paragraph) == [], paragraph["paragraph_id"]


def test_block_quotes_and_references(corpus_data):
    paragraphs = section_paragraphs(corpus_data)
    owners = [p for p in paragraphs if p["classification"] == "block_quote"]
    assert [p["paragraph_global_order"] for p in owners] == [29, 31]
    elements = index_by(corpus_data["elements"], "element_id")
    scoped_ids = {p["paragraph_id"] for p in paragraphs}
    references = [e for e in elements.values() if e["kind"] == "block_quote" and e["paragraph_id"] in scoped_ids]
    assert len(references) == 2
    assert {e["element_id"] for e in references} == {p["quote_element_id"] for p in owners}
    saved = json.loads((CORPUS_DIR / "validation_report.json").read_text(encoding="utf-8"))
    pending = {item["unit_id"] for item in saved["documentary_quality"]["review_items"]
               if item["code"] == "formatted_quote_requires_review"}
    for paragraph in owners:
        element = elements[paragraph["quote_element_id"]]
        assert element["paragraph_id"] == paragraph["paragraph_id"]
        assert element["kind"] == "block_quote"
        assert element["text_ownership"] == "reference"
        assert element["parent_id"] == paragraph["parent_id"] == SECTION_NODE_ID
        assert element["source_spans"] == paragraph["source_spans"]
        assert element["quality_status"] == paragraph["quality_status"] == "review_required"
        assert paragraph["paragraph_id"] in pending


def test_documentary_gate_and_pending_reviews(corpus_data, capsys):
    saved = json.loads((CORPUS_DIR / "validation_report.json").read_text(encoding="utf-8"))
    current = validate_corpus(CORPUS_DIR)
    for report in (saved, current):
        assert report["status"] == "review_required"
        assert report["raw_integrity"]["status"] == "passed"
        assert report["metrics"]["paragraphs"] == 72
        assert report["chunking_gate"]["allowed"] is False
        assert report["chunking_gate"]["pending_review_count"] == 12
        assert report["chunking_gate"]["blocking_error_count"] == 0
        assert not report["documentary_quality"]["blockers"]
        assert len(report["documentary_quality"]["review_items"]) == 12
    assert current["documentary_quality"]["review_items"] == saved["documentary_quality"]["review_items"]
    assert main(["check-ready", str(CORPUS_DIR)]) == 2
    gate = json.loads(capsys.readouterr().out)
    assert gate["allowed"] is False and gate["pending_review_count"] == 12
    assert any(i.get("node_id") == SECTION_NODE_ID for i in current["documentary_quality"]["review_items"])


def test_historical_review_correspondence(corpus_data):
    historical = json.loads((BASE_DIR / "reviews/tarefa-003-v1.json").read_text(encoding="utf-8"))
    assert historical["decision"] == "confirmed"
    assert historical["unit"]["title"] == SECTION_TITLE
    assert historical["unit"]["node_id"] == "node_3c218d9bc62678cc2593ecbf"
    nodes = index_by(corpus_data["structure"]["nodes"], "node_id")
    assert historical["unit"]["source_spans"] == nodes[SECTION_NODE_ID]["source_spans"]
    previous_records = historical["evidence"]["direct_record_scope"]["records"]
    current_records = section_paragraphs(corpus_data)
    assert len(previous_records) == len(current_records) == 14
    for previous, current in zip(previous_records, current_records, strict=True):
        assert previous["global_order"] == current["paragraph_global_order"]
        assert previous["source_spans"] == current["source_spans"]

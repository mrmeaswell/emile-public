import json
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "export_quiz.py"
QTI = "{http://www.imsglobal.org/xsd/ims_qtiasiv1p2}"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def test_qti_export_of_valid_quiz(tmp_path, valid_quiz):
    src = tmp_path / "quiz.json"
    src.write_text(json.dumps(valid_quiz))
    r = run(src, "--format", "qti")
    assert r.returncode == 0, r.stderr

    with zipfile.ZipFile(tmp_path / "quiz.qti.zip") as z:
        manifest = ET.fromstring(z.read("imsmanifest.xml"))
        href = manifest.find(".//{*}file").get("href")
        assessment = ET.fromstring(z.read(href))
    items = assessment.findall(f".//{QTI}item")
    assert len(items) == 35
    types = [i.find(f".//{QTI}qtimetadatafield/{QTI}fieldentry").text for i in items]
    assert types.count("multiple_choice_question") == 12
    assert types.count("essay_question") == 5
    ma = items[19]  # first multiple_answer item: answers [0, 2]
    assert [v.text for v in ma.findall(f".//{QTI}and/{QTI}varequal")] == ["q20_a0", "q20_a2"]
    assert [v.text for v in ma.findall(f".//{QTI}and/{QTI}not/{QTI}varequal")] == ["q20_a1", "q20_a3"]


def test_invalid_quiz_refused_without_force(tmp_path):
    r = run(ROOT / "examples" / "sample-quiz.json", "--format", "qti", "--out-dir", tmp_path)
    assert r.returncode != 0 and "total: 5 items" in r.stderr
    assert not list(tmp_path.iterdir())


def test_force_exports_spec_violations(tmp_path):
    r = run(ROOT / "examples" / "sample-quiz.json", "--format", "qti", "--out-dir", tmp_path, "--force")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "sample-quiz.qti.zip").exists()


def test_force_does_not_export_malformed_items(tmp_path, valid_quiz):
    valid_quiz["questions"][7]["answer"] = [9]
    src = tmp_path / "quiz.json"
    src.write_text(json.dumps(valid_quiz))
    r = run(src, "--format", "qti", "--force")
    assert r.returncode != 0 and "malformed" in r.stderr


def test_docx_export(tmp_path, valid_quiz):
    pytest.importorskip("docx")
    src = tmp_path / "quiz.json"
    src.write_text(json.dumps(valid_quiz))
    r = run(src, "--format", "docx")
    assert r.returncode == 0, r.stderr
    from docx import Document
    text = "\n".join(p.text for p in Document(tmp_path / "quiz.docx").paragraphs)
    assert "Answer Key" in text and "Main Street Coffee & Books" in text


def test_skill_md_is_up_to_date():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_skill.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

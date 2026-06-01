# -*- coding: utf-8 -*-
"""Тест OCR на образце заявки."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SAMPLE = Path(r"c:\My_App_OKiT\idps\Заявки\Заявки на приобретение билетов.pdf")


def main():
    from pdf_processor import extract_text_from_pdf, process_pdf_file, process_ticket_application_pdf

    if not SAMPLE.is_file():
        print("Sample not found:", SAMPLE)
        return 1

    text = extract_text_from_pdf(str(SAMPLE))
    out = ROOT / "data" / "sample_ocr.txt"
    out.write_text(text, encoding="utf-8")
    print("text length", len(text), "->", out)

    legacy = process_pdf_file(str(SAMPLE))
    new = process_ticket_application_pdf(str(SAMPLE))
    report = {"legacy": legacy, "structured": new}
    (ROOT / "data" / "sample_parse.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("parsed", len(new), "applications -> data/sample_parse.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

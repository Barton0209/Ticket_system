# pdf_processor.py
"""
Обработка PDF: сканы стандартной «Заявки на приобретение билетов».
"""

import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional

import fitz
import numpy as np

from config import TESSERACT_CMD
from app_logger import log
from ticket_form_parser import (
    parse_ticket_application_text,
    parse_ticket_application_text_to_legacy_list,
)

CV2_AVAILABLE = False
TESSERACT_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    pass

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    if TESSERACT_CMD and os.path.isfile(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    elif TESSERACT_CMD:
        # Путь указан, но файл не найден - отключаем OCR
        TESSERACT_AVAILABLE = False
        log.warning(f"Tesseract не найден по пути: {TESSERACT_CMD}. OCR отключен.")
except ImportError:
    pass

# Масштаб рендера для OCR сканов
OCR_MATRIX = fitz.Matrix(2.5, 2.5)
OCR_LANG = "rus+eng"
OCR_CONFIG = "--psm 6 -c preserve_interword_spaces=1"


def preprocess_image(image: np.ndarray) -> np.ndarray:
    if not CV2_AVAILABLE:
        return image
    if len(image.shape) == 3 and image.shape[2] >= 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    return cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


def _page_to_text(page: fitz.Page) -> str:
    native = page.get_text()
    if native and len(native.strip()) > 40:
        return native

    if not (TESSERACT_AVAILABLE and CV2_AVAILABLE):
        return native or ""

    try:
        pix = page.get_pixmap(matrix=OCR_MATRIX, alpha=False)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        prepared = preprocess_image(img)
        return pytesseract.image_to_string(
            prepared, lang=OCR_LANG, config=OCR_CONFIG, timeout=90
        ) or ""
    except Exception as e:
        log.warning("OCR страницы: %s", e)
        return ""


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        parts = [_page_to_text(doc[i]) for i in range(len(doc))]
        doc.close()
        return "\n\n".join(p for p in parts if p.strip())
    except Exception as e:
        log.error("PDF %s: %s", pdf_path, e)
        return ""


def extract_text_pages_from_pdf(pdf_path: str) -> List[str]:
    try:
        doc = fitz.open(pdf_path)
        pages = [_page_to_text(doc[i]) for i in range(len(doc))]
        doc.close()
        return pages
    except Exception as e:
        log.error("PDF pages %s: %s", pdf_path, e)
        return []


def process_ticket_application_pdf(pdf_path: str) -> List[Dict]:
    """
    Одна заявка = одна страница PDF (типичный пакет сканов).
  Возвращает список структур с полями маршрута туда/обратно.
    """
    filename = os.path.basename(pdf_path)
    pages = extract_text_pages_from_pdf(pdf_path)
    results: List[Dict] = []

    for i, text in enumerate(pages, start=1):
        parsed = parse_ticket_application_text(text, source_file=filename, page=i)
        if parsed:
            results.append(parsed)
            log.info(
                "PDF %s стр.%s: %s | %s | %s",
                filename,
                i,
                parsed.get("fio", ""),
                parsed.get("route1", ""),
                parsed.get("reason", ""),
            )

    if not results and pages:
        merged = parse_ticket_application_text("\n".join(pages), source_file=filename, page=1)
        if merged:
            results.append(merged)

    return results


# --- Совместимость со старыми вызовами и тестами ---

def extract_fio(text: str) -> str:
    from ticket_form_parser import extract_fio_from_form
    return extract_fio_from_form(text) or _legacy_extract_fio(text)


def _legacy_extract_fio(text: str) -> str:
    patterns = [
        r"([А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{5,})\s+\d{2}\.\d{2}\.\d{4}",
        r"(?:подмостей|лесов)\s+([А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{2,}\s+[А-ЯЁ][а-яё]{5,})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
    return ""


def extract_route_and_dates(text: str):
    from ticket_form_parser import _parse_route_rows, _rows_to_routes
    rows = _parse_route_rows(text)
    r1, r2, d1, d2 = _rows_to_routes(rows)
    return r1, r2, d1, d2


def extract_reason(text: str) -> str:
    from ticket_form_parser import extract_reason_from_form
    return extract_reason_from_form(text)


def extract_phone(text: str) -> str:
    patterns = [
        r"\+7\s?\(?\d{3}\)?\s?\d{3}\s?\d{2}\s?\d{2}",
        r"8\s?\d{3}\s?\d{3}\s?\d{2}\s?\d{2}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ""


def process_pdf_file(pdf_path: str) -> List[Dict]:
    """Разбор файла: предпочтительно постранично (скан-пакет)."""
    structured = process_ticket_application_pdf(pdf_path)
    if structured:
        legacy: List[Dict] = []
        for item in structured:
            legacy.extend(parse_ticket_application_text_to_legacy_list(item))
        return legacy

    filename = os.path.basename(pdf_path)
    text = extract_text_from_pdf(pdf_path)
    if not text or len(text.strip()) < 10:
        return []

    fio = extract_fio(text)
    route_tuda, route_obratno, date_tuda, date_obratno = extract_route_and_dates(text)
    reason = extract_reason(text)
    phone = extract_phone(text)

    results = []
    if fio or route_tuda:
        results.append(
            {
                "source_file": filename,
                "direction": "туда",
                "fio": fio,
                "route": route_tuda,
                "route1": route_tuda,
                "date": date_tuda,
                "date1": date_tuda,
                "reason": reason,
                "reason1": reason,
                "phone": phone,
            }
        )
        if route_obratno and date_obratno:
            results.append(
                {
                    "source_file": filename,
                    "direction": "обратно",
                    "fio": fio,
                    "route": route_obratno,
                    "route2": route_obratno,
                    "date": date_obratno,
                    "date2": date_obratno,
                    "reason": reason,
                    "phone": phone,
                }
            )
    return results


def process_pdf_folder(
    folder_path: str,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[Dict]:
    pdf_files = sorted(Path(folder_path).glob("*.pdf"))
    if not pdf_files:
        return []

    all_results: List[Dict] = []
    total = len(pdf_files)

    for idx, pdf_file in enumerate(pdf_files):
        if progress_callback:
            progress_callback(idx, total, f"Обработка: {pdf_file.name}")
        all_results.extend(process_ticket_application_pdf(str(pdf_file)))

    if progress_callback:
        progress_callback(total, total, "Готово!")
    return all_results

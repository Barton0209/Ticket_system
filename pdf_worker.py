# pdf_worker.py
"""Фоновая обработка PDF без блокировки UI."""

from __future__ import annotations

import threading
from typing import Callable, List, Optional

ProgressCallback = Callable[[int, int, str], None]
DoneCallback = Callable[[bool, str, List, Optional[Exception]], None]


def run_pdf_folder_async(
    folder_path: str,
    on_progress: Optional[ProgressCallback] = None,
    on_done: Optional[DoneCallback] = None,
) -> threading.Thread:
    def worker():
        results: List = []
        err: Optional[Exception] = None
        try:
            from pdf_processor import process_pdf_folder

            def progress(current, total, message):
                if on_progress:
                    on_progress(current, total, message)

            results = process_pdf_folder(folder_path, progress)
            msg = f"Готово: {len(results)} заявок"
            ok = True
        except Exception as e:
            err = e
            msg = str(e)
            ok = False
        if on_done:
            on_done(ok, msg, results, err)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def run_single_pdf_async(
    file_path: str,
    on_done: Optional[DoneCallback] = None,
) -> threading.Thread:
    def worker():
        results: List = []
        err: Optional[Exception] = None
        try:
            from pdf_processor import process_ticket_application_pdf

            results = process_ticket_application_pdf(file_path)
            msg = f"Готово: {len(results)} заявок"
            ok = True
        except Exception as e:
            err = e
            msg = str(e)
            ok = False
        if on_done:
            on_done(ok, msg, results, err)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t

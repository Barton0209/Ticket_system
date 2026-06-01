import React, { useEffect, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

export default function PdfViewer({ filePath, page = 1 }) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const [doc, setDoc] = useState(null);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(page);
  const [zoom, setZoom] = useState(1);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setDoc(null);
    setError("");
    if (!filePath) return undefined;

    (async () => {
      try {
        const url = await window.ticketConfig?.registerPdf?.(filePath);
        if (!url) throw new Error("Не удалось открыть файл");
        const pdf = await pdfjsLib.getDocument(url).promise;
        if (cancelled) return;
        setDoc(pdf);
        setTotalPages(pdf.numPages);
        setCurrentPage(Math.min(Math.max(1, page), pdf.numPages));
      } catch (e) {
        if (!cancelled) setError(e.message || "Ошибка PDF");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [filePath, page]);

  useEffect(() => {
    if (!doc || !canvasRef.current) return undefined;

    let cancelled = false;
    (async () => {
      try {
        const pdfPage = await doc.getPage(currentPage);
        if (cancelled) return;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        const base = pdfPage.getViewport({ scale: 1 });
        const wrapW = wrapRef.current?.clientWidth || base.width;
        const fitScale = (wrapW / base.width) * zoom;
        const viewport = pdfPage.getViewport({ scale: fitScale });
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        await pdfPage.render({ canvasContext: ctx, viewport }).promise;
      } catch (e) {
        if (!cancelled) setError(e.message || "Render error");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [doc, currentPage, zoom]);

  if (!filePath) {
    return (
      <div className="pdf-viewer-empty">
        Выберите PDF или выполните OCR
      </div>
    );
  }

  return (
    <div className="pdf-viewer">
      <div className="pdf-viewer-toolbar">
        <button type="button" disabled={currentPage <= 1} onClick={() => setCurrentPage((p) => p - 1)}>
          ◀
        </button>
        <span>
          {currentPage} / {totalPages || "-"}
        </span>
        <button
          type="button"
          disabled={!totalPages || currentPage >= totalPages}
          onClick={() => setCurrentPage((p) => p + 1)}
        >
          ▶
        </button>
        <button type="button" onClick={() => setZoom((z) => Math.max(0.5, z - 0.15))}>
          -
        </button>
        <span>{Math.round(zoom * 100)}%</span>
        <button type="button" onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}>
          +
        </button>
        <button type="button" onClick={() => setZoom(1)}>
          По ширине
        </button>
      </div>
      <div className="pdf-viewer-canvas-wrap" ref={wrapRef}>
        {error ? <p className="hint bad">{error}</p> : <canvas ref={canvasRef} />}
      </div>
    </div>
  );
}

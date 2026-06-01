import React, { useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import PdfViewer from "./PdfViewer";
import { api } from "./api";

const defaultColDef = {
  sortable: true,
  resizable: true,
  flex: 1,
  minWidth: 80,
};

function emptyItem() {
  return {
    fio: "",
    route1: "",
    date1: "",
    transport1: "АВИА",
    note1: "",
    route2: "",
    date2: "",
    reason1: "",
    reason2: "",
    source_file: "",
    page: 1,
    employee: null,
    status: "manual",
  };
}

export default function PdfWorkbench({
  items,
  setItems,
  pdfFileMap,
  deptFilter,
  onAddToApplication,
  onPickDuplicate,
}) {
  const [index, setIndex] = useState(0);
  const [routes, setRoutes] = useState([]);
  const [searchQ, setSearchQ] = useState("");
  const [searchRows, setSearchRows] = useState([]);
  const [empHint, setEmpHint] = useState("");

  useEffect(() => {
    api.routes().then((r) => setRoutes(r.routes || [])).catch(() => setRoutes([]));
  }, []);

  useEffect(() => {
    if (index >= items.length && items.length) setIndex(items.length - 1);
  }, [items.length, index]);

  const current = items[index] || emptyItem();
  const pdfPath = current.source_file ? pdfFileMap[current.source_file] : null;

  const updateCurrent = (patch) => {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...patch } : it)));
  };

  const loadFormFromItem = (it) => ({
    fio: it.fio || "",
    route1: it.route1 || it.route || "",
    date1: it.date1 || it.date || "",
    transport1: it.transport1 || "АВИА",
    note1: it.note1 || it.note || "",
    route2: it.route2 || "",
    date2: it.date2 || "",
    reason1: it.reason1 || it.reason || "",
    reason2: it.reason2 || "",
  });

  const syncToItem = (form) => {
    updateCurrent({ ...form, status: current.employee ? "selected" : "manual" });
  };

  const lookupFio = async (fio) => {
    if (!fio?.trim()) return;
    try {
      const r = await api.lookupFio(fio.trim(), deptFilter);
      if (r.status === "found" && r.employee) {
        updateCurrent({ employee: r.employee, status: "selected" });
        setEmpHint(`Из базы: ${r.employee.fio} | ${r.employee.department || ""}`);
      } else if (r.status === "multiple" && r.candidates?.length) {
        onPickDuplicate(r.candidates, (emp) => {
          updateCurrent({ employee: emp, fio: emp.fio, status: "selected" });
          setEmpHint(`Выбран: ${emp.fio}`);
        });
      } else {
        updateCurrent({ employee: null, status: "manual" });
        setEmpHint("Не найден в базе");
      }
    } catch (e) {
      setEmpHint(e.message);
    }
  };

  const searchInDb = async () => {
    try {
      const r = await api.searchEmployees({
        q: searchQ || current.fio,
        department: deptFilter,
        limit: 50,
      });
      setSearchRows(r.items || []);
    } catch {
      setSearchRows([]);
    }
  };

  const pickSearchRow = (emp) => {
    if (!emp) return;
    updateCurrent({ employee: emp, fio: emp.fio, status: "selected" });
    setEmpHint(`Выбран: ${emp.fio}`);
  };

  const searchColDefs = useMemo(
    () => [
      { field: "fio", headerName: "ФИО", flex: 2 },
      { field: "department", headerName: "ОП", flex: 1 },
      { field: "tab_num", headerName: "Таб. №", width: 90 },
    ],
    []
  );

  const form = loadFormFromItem(current);

  if (!items.length) {
    return (
      <p className="hint" style={{ padding: 24 }}>
        Нет распознанных заявок. Нажмите «PDF OCR» или «Просмотр PDF» в шапке.
      </p>
    );
  }

  return (
    <div className="pdf-workbench">
      <div className="pdf-workbench-nav">
        <span>
          Заявка {index + 1} из {items.length}
        </span>
        <button type="button" disabled={index <= 0} onClick={() => setIndex((i) => i - 1)}>
          ◀ Назад
        </button>
        <button
          type="button"
          disabled={index >= items.length - 1}
          onClick={() => setIndex((i) => i + 1)}
        >
          Следующий ▶
        </button>
        <button type="button" className="secondary" onClick={() => syncToItem(form)}>
          Сохранить правки
        </button>
        <button
          type="button"
          onClick={() => {
            const prepared = items.map((it) => ({
              ...it,
              ...(it.employee ? { status: "selected" } : { status: "manual", employee: null }),
            }));
            onAddToApplication(prepared);
          }}
        >
          Всё в заявку →
        </button>
      </div>

      <div className="pdf-workbench-split">
        <div className="pdf-workbench-pdf">
          <p className="hint">{current.source_file || "PDF"} · стр. {current.page || 1}</p>
          <PdfViewer filePath={pdfPath} page={Number(current.page) || 1} />
        </div>

        <div className="pdf-workbench-form">
          <label className="field-block">
            Список страниц
            <select
              value={index}
              onChange={(e) => setIndex(Number(e.target.value))}
            >
              {items.map((it, i) => (
                <option key={i} value={i}>
                  {i + 1}. {it.fio || "(без ФИО)"} — {it.source_file || "PDF"}
                </option>
              ))}
            </select>
          </label>

          <div className="form-grid">
            <label>
              ФИО
              <input
                value={form.fio}
                onChange={(e) => syncToItem({ ...form, fio: e.target.value })}
                onBlur={(e) => lookupFio(e.target.value)}
              />
            </label>
            <label>
              Маршрут 1
              <input
                list="routes-list"
                value={form.route1}
                onChange={(e) => syncToItem({ ...form, route1: e.target.value })}
              />
            </label>
            <label>
              Дата вылета 1
              <input
                value={form.date1}
                onChange={(e) => syncToItem({ ...form, date1: e.target.value })}
              />
            </label>
            <label>
              Транспорт 1
              <select
                value={form.transport1}
                onChange={(e) => syncToItem({ ...form, transport1: e.target.value })}
              >
                <option value="АВИА">АВИА</option>
                <option value="ЖД">ЖД</option>
              </select>
            </label>
            <label>
              Обоснование
              <input
                value={form.reason1}
                onChange={(e) => syncToItem({ ...form, reason1: e.target.value })}
              />
            </label>
            <label>
              Маршрут 2
              <input
                list="routes-list"
                value={form.route2}
                onChange={(e) => syncToItem({ ...form, route2: e.target.value })}
              />
            </label>
            <label>
              Дата вылета 2
              <input
                value={form.date2}
                onChange={(e) => syncToItem({ ...form, date2: e.target.value })}
              />
            </label>
            <label className="span2">
              Примечание
              <input
                value={form.note1}
                onChange={(e) => syncToItem({ ...form, note1: e.target.value })}
              />
            </label>
          </div>
          <datalist id="routes-list">
            {routes.map((r) => (
              <option key={r} value={r} />
            ))}
          </datalist>

          <p className={`hint ${current.employee ? "ok" : "warn"}`}>{empHint || "Поиск в базе по ФИО"}</p>

          <div className="toolbar-row">
            <input
              placeholder="Поиск в базе"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && searchInDb()}
            />
            <button type="button" className="secondary" onClick={searchInDb}>
              Найти
            </button>
          </div>
          <div style={{ height: 140, minHeight: 100 }}>
            <AgGridReact
              className="ag-theme-alpine-dark"
              rowData={searchRows}
              columnDefs={searchColDefs}
              defaultColDef={{ ...defaultColDef, editable: false }}
              rowSelection="single"
              onRowDoubleClicked={(e) => pickSearchRow(e.data)}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

import React, { useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { api } from "./api";
import PickModal from "./PickModal";

const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  editable: false,
  flex: 1,
  minWidth: 90,
};

function parseFios(text) {
  const seen = new Set();
  const out = [];
  for (const line of text.replace(/\r/g, "").split("\n")) {
    const parts = line.split(/\t|;/).map((p) => p.trim()).filter(Boolean);
    const items = parts.length > 1 ? parts : [line.trim()];
    for (const item of items) {
      const key = item.toLowerCase();
      if (item && !seen.has(key)) {
        seen.add(key);
        out.push(item);
      }
    }
  }
  return out;
}

function mapFioRow(item) {
  if (item.status === "found" && item.employee) {
    return {
      query: item.query,
      status: "found",
      statusText: "Найден",
      department: item.employee.department || "",
      tab_num: item.employee.tab_num || "",
      employee: item.employee,
      candidates: [],
    };
  }
  if (item.status === "multiple") {
    return {
      query: item.query,
      status: "multiple",
      statusText: "Несколько (двойной клик)",
      department: "",
      tab_num: "",
      employee: null,
      candidates: item.candidates || [],
    };
  }
  return {
    query: item.query,
    status: "not_found",
    statusText: "Не найден",
    department: "",
    tab_num: "",
    employee: null,
    candidates: [],
  };
}

export default function FioListModal({ deptFilter, onCreateApplication, onClose }) {
  const [fioText, setFioText] = useState("");
  const [fioRows, setFioRows] = useState([]);
  const [fioStatus, setFioStatus] = useState("Вставьте ФИО и нажмите «Поиск»");
  const [pickModal, setPickModal] = useState(null);
  const [busy, setBusy] = useState(false);

  const fioColDefs = useMemo(
    () => [
      { field: "query", headerName: "ФИО (запрос)", flex: 2 },
      { field: "statusText", headerName: "Результат", width: 180 },
      { field: "department", headerName: "Подразделение", flex: 1.2 },
      { field: "tab_num", headerName: "Таб. №", width: 90 },
    ],
    []
  );

  const doFioSearch = async () => {
    const fios = parseFios(fioText);
    if (!fios.length) {
      setFioStatus("Вставьте хотя бы одно ФИО");
      return;
    }
    setBusy(true);
    setFioStatus("Поиск…");
    try {
      const res = await api.lookupBatch(fios, deptFilter);
      const rows = (res.items || []).map(mapFioRow);
      setFioRows(rows);
      const found = rows.filter((r) => r.status === "found").length;
      setFioStatus(
        found ? `К заявке: ${found} из ${rows.length}` : `Найдено: 0 из ${rows.length}`
      );
    } catch (e) {
      setFioStatus(e.message);
    } finally {
      setBusy(false);
    }
  };

  const onFioRowDoubleClick = (e) => {
    const row = e.data;
    if (!row || row.status !== "multiple" || !row.candidates?.length) return;
    setPickModal({
      title: `Выбор: ${row.query}`,
      candidates: row.candidates,
      onPick: (emp) => {
        setFioRows((prev) => {
          const next = prev.map((r) =>
            r.query === row.query
              ? {
                  ...r,
                  status: "found",
                  statusText: "Найден",
                  department: emp.department || "",
                  tab_num: emp.tab_num || "",
                  employee: emp,
                  candidates: [],
                }
              : r
          );
          const found = next.filter((x) => x.status === "found").length;
          setFioStatus(`К заявке: ${found} из ${next.length}`);
          return next;
        });
        setPickModal(null);
      },
    });
  };

  const fioFoundCount = fioRows.filter((r) => r.status === "found").length;

  const buildFromFio = () => {
    const found = fioRows.filter((r) => r.status === "found" && r.employee);
    if (found.length) onCreateApplication(found.map((r) => r.employee));
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <h3>Из списка</h3>
        <div className="panel-split" style={{ flex: 1, minHeight: 360 }}>
          <div className="panel-left">
            <p className="hint">ФИО по строке или столбец из Excel (Ctrl+V)</p>
            <textarea value={fioText} onChange={(e) => setFioText(e.target.value)} />
            <div className="toolbar-row">
              <button type="button" onClick={doFioSearch} disabled={busy}>
                Поиск
              </button>
              <button type="button" onClick={buildFromFio} disabled={fioFoundCount === 0}>
                Составить заявку ({fioFoundCount})
              </button>
            </div>
          </div>
          <div className="panel-right">
            <p className={`hint ${fioFoundCount ? "ok" : ""}`}>{fioStatus}</p>
            <div className="grid-wrap">
              <AgGridReact
                className="ag-theme-alpine-dark"
                rowData={fioRows}
                columnDefs={fioColDefs}
                defaultColDef={defaultColDef}
                onRowDoubleClicked={onFioRowDoubleClick}
                getRowStyle={(p) => {
                  if (p.data?.status === "found") return { background: "#1a3d2e" };
                  if (p.data?.status === "multiple") return { background: "#3d351a" };
                  if (p.data?.status === "not_found") return { background: "#3d1a1a" };
                  return null;
                }}
              />
            </div>
          </div>
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            Закрыть
          </button>
        </div>
        {pickModal && (
          <PickModal
            title={pickModal.title}
            candidates={pickModal.candidates}
            onPick={pickModal.onPick}
            onClose={() => setPickModal(null)}
          />
        )}
      </div>
    </div>
  );
}

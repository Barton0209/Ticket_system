import React, { useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { api } from "./api";

const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  editable: false,
  flex: 1,
  minWidth: 90,
};

export default function CatalogModal({
  deptFilter,
  initialSearch = "",
  onPickEmployees,
  onClose,
}) {
  const [searchQ, setSearchQ] = useState(initialSearch);
  const [searchRows, setSearchRows] = useState([]);
  const [gridApi, setGridApi] = useState(null);

  const searchColDefs = useMemo(
    () => [
      { field: "fio", headerName: "ФИО", flex: 2 },
      { field: "department", headerName: "Подразделение", flex: 1.5 },
      { field: "tab_num", headerName: "Таб. №", width: 90 },
      { field: "position", headerName: "Должность", flex: 1 },
    ],
    []
  );

  const doSearch = async () => {
    const res = await api.searchEmployees({
      q: searchQ || null,
      department: deptFilter,
      limit: 200,
      offset: 0,
    });
    setSearchRows(res.items || []);
  };

  useEffect(() => {
    if (initialSearch) doSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addSelected = () => {
    const sel = gridApi?.getSelectedRows() || [];
    if (sel.length) onPickEmployees(sel);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>
        <h3>Каталог сотрудников</h3>
        <div className="toolbar-row">
          <input
            placeholder="ФИО или табельный №"
            value={searchQ}
            onChange={(e) => setSearchQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && doSearch()}
            style={{ minWidth: 240 }}
          />
          <button type="button" onClick={doSearch}>
            Найти
          </button>
          <button type="button" onClick={addSelected}>
            Добавить в заявку →
          </button>
        </div>
        <div className="grid-wrap" style={{ height: 400 }}>
          <AgGridReact
            className="ag-theme-alpine-dark"
            rowData={searchRows}
            columnDefs={searchColDefs}
            defaultColDef={defaultColDef}
            rowSelection="multiple"
            onGridReady={(p) => setGridApi(p.api)}
            onRowDoubleClicked={(e) => e.data && onPickEmployees([e.data])}
          />
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}

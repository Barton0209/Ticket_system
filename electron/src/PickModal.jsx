import React, { useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";

const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  editable: false,
  flex: 1,
  minWidth: 90,
};

export default function PickModal({ title, candidates, onPick, onClose }) {
  const colDefs = useMemo(
    () => [
      { field: "fio", headerName: "ФИО", flex: 2 },
      { field: "department", headerName: "Подразделение", flex: 1.5 },
      { field: "tab_num", headerName: "Таб. №", width: 100 },
      { field: "position", headerName: "Должность", flex: 1 },
    ],
    []
  );
  const [gridApi, setGridApi] = useState(null);
  const pick = () => {
    const rows = gridApi?.getSelectedRows() || [];
    if (rows[0]) onPick(rows[0]);
  };
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <div className="grid-wrap" style={{ height: 260 }}>
          <AgGridReact
            className="ag-theme-alpine-dark"
            rowData={candidates}
            columnDefs={colDefs}
            defaultColDef={defaultColDef}
            rowSelection="single"
            onGridReady={(p) => setGridApi(p.api)}
            onRowDoubleClicked={(e) => e.data && onPick(e.data)}
          />
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            Отмена
          </button>
          <button type="button" onClick={pick}>
            Выбрать
          </button>
        </div>
      </div>
    </div>
  );
}

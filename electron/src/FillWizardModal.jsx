import React from "react";
import PdfWorkbench from "./PdfWorkbench";

export default function FillWizardModal({
  items,
  setItems,
  pdfFileMap,
  deptFilter,
  onPickDuplicate,
  onAddToApplication,
  onClose,
}) {
  return (
    <div className="modal-backdrop modal-fill-backdrop">
      <div className="modal modal-fill" onClick={(e) => e.stopPropagation()}>
        <div className="modal-fill-header">
          <h3>Заполнить из базы</h3>
          <button type="button" className="secondary" onClick={onClose}>
            Закрыть
          </button>
        </div>
        <div className="modal-fill-body">
          <PdfWorkbench
            items={items}
            setItems={setItems}
            pdfFileMap={pdfFileMap}
            deptFilter={deptFilter}
            onAddToApplication={(prepared) => {
              onAddToApplication(prepared);
              onClose();
            }}
            onPickDuplicate={onPickDuplicate}
          />
        </div>
      </div>
    </div>
  );
}

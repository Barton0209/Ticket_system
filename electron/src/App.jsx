import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { api, dialogs } from "./api";
import { ALL_COLUMNS, buildBaseColumnDefs, emptyApplicationRow } from "./constants";
import Login from "./Login";
import PickModal from "./PickModal";
import FioListModal from "./FioListModal";
import CatalogModal from "./CatalogModal";
import FillWizardModal from "./FillWizardModal";

const BASE_PAGE_SIZE = 500;

const defaultColDef = {
  sortable: true,
  filter: true,
  resizable: true,
  editable: true,
  minWidth: 72,
};

function loadSession() {
  try {
    const raw = sessionStorage.getItem("ticketSession");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [session, setSession] = useState(loadSession);
  const [tab, setTab] = useState("work");
  const [health, setHealth] = useState(null);
  const [depts, setDepts] = useState([]);
  const [dept, setDept] = useState("");
  const [appRows, setAppRows] = useState([]);
  const [pdfItems, setPdfItems] = useState([]);
  const [pdfFileMap, setPdfFileMap] = useState({});
  const [selectedPdf, setSelectedPdf] = useState("");
  const [pdfBusy, setPdfBusy] = useState(false);
  const [dbBusy, setDbBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [statusText, setStatusText] = useState("Готов к работе");
  const [pickModal, setPickModal] = useState(null);
  const [showCatalog, setShowCatalog] = useState(false);
  const [showFioList, setShowFioList] = useState(false);
  const [showFillWizard, setShowFillWizard] = useState(false);
  const [baseQ, setBaseQ] = useState("");
  const [baseRows, setBaseRows] = useState([]);
  const [baseOffset, setBaseOffset] = useState(0);
  const [baseTotal, setBaseTotal] = useState(0);
  const [baseLoading, setBaseLoading] = useState(false);
  const [baseHint, setBaseHint] = useState("");
  const appGridRef = useRef(null);
  const baseGridRef = useRef(null);

  const deptFilter = useMemo(() => {
    if (session?.is_admin) return dept === "" || dept === "Все" ? null : dept;
    return session?.department || dept || null;
  }, [session, dept]);

  const loginDept = session?.department || dept || "";
  const dbReady = Boolean(health?.employees_ready);
  const hasApp = appRows.length > 0;
  const hasPdf = pdfItems.length > 0;

  const pdfFileList = useMemo(() => {
    const names = new Set(Object.keys(pdfFileMap));
    for (const it of pdfItems) {
      if (it.source_file) names.add(it.source_file);
    }
    return [...names].sort();
  }, [pdfFileMap, pdfItems]);

  const showToast = (msg, ms = 3500) => {
    setToast(msg);
    setTimeout(() => setToast(""), ms);
  };

  const loadHealth = useCallback(async () => {
    try {
      const h = await api.health();
      setHealth(h);
    } catch {
      setHealth(null);
    }
  }, []);

  const loadDepts = useCallback(async () => {
    try {
      const d = await api.departments();
      setDepts(["Все", ...(d.items || [])]);
    } catch {
      setDepts(["Все"]);
    }
  }, []);

  useEffect(() => {
    if (!session) return;
    loadHealth();
    loadDepts();
    if (!session.is_admin && session.department) setDept(session.department);
    const t = setInterval(loadHealth, 30000);
    return () => clearInterval(t);
  }, [session, loadHealth, loadDepts]);

  const logout = () => {
    sessionStorage.removeItem("ticketSession");
    setSession(null);
  };

  const switchUser = () => {
    sessionStorage.removeItem("ticketSession");
    setSession(null);
    setAppRows([]);
    setPdfItems([]);
    setPdfFileMap({});
  };

  const reloadCache = async () => {
    setDbBusy(true);
    setError("");
    try {
      const r = await api.reloadCache();
      await loadHealth();
      await loadDepts();
      showToast(r.message || "База обновлена");
      setStatusText("База обновлена");
    } catch (e) {
      setError(e.message);
    } finally {
      setDbBusy(false);
    }
  };

  const loadExcelBase = async () => {
    if (!session?.is_admin) return;
    const path = await dialogs.openExcelFile();
    if (!path) return;
    setDbBusy(true);
    try {
      const r = await api.loadDatabase(path);
      await loadHealth();
      await loadDepts();
      showToast(r.message || `Загружено: ${r.count}`);
    } catch (e) {
      setError(e.message);
    } finally {
      setDbBusy(false);
    }
  };

  const registerPdfPath = (path) => {
    const name = path.split(/[/\\]/).pop();
    setPdfFileMap((m) => ({ ...m, [name]: path }));
    return name;
  };

  const appendRowsFromApi = async (kind, payload) => {
    const start = appRows.length + 1;
    let newRows = [];
    if (kind === "employees") {
      const r = await api.rowsFromEmployees(payload, start, loginDept);
      newRows = r.rows || [];
    } else {
      const r = await api.rowsFromWizard(payload, start, loginDept);
      newRows = r.rows || [];
    }
    if (!newRows.length) return 0;
    setAppRows((prev) => [...prev, ...newRows]);
    setTab("work");
    return newRows.length;
  };

  const addEmployeesToApp = async (employees) => {
    if (!employees?.length) return;
    try {
      const n = await appendRowsFromApi("employees", employees);
      showToast(`Добавлено в заявку: ${n}`);
      setStatusText(`В заявке ${appRows.length + n} строк`);
    } catch (e) {
      setError(e.message);
    }
  };

  const addWizardToApp = async (items) => {
    if (!items?.length) return;
    try {
      const n = await appendRowsFromApi("wizard", items);
      showToast(`Из PDF в заявку: ${n}`);
    } catch (e) {
      setError(e.message);
    }
  };

  const processOnePdf = async (path) => {
    registerPdfPath(path);
    setStatusText(`OCR: ${path}…`);
    const r = await api.processPdf(path);
    setPdfItems((prev) => [...prev, ...(r.items || [])]);
    return r.count;
  };

  const selectPdfFile = async () => {
    if (!dbReady) {
      setError("Сначала загрузите базу сотрудников");
      return;
    }
    let paths = await dialogs.openPdfFiles();
    if (!paths?.length) {
      const one = await dialogs.openPdfFile();
      if (!one) return;
      paths = [one];
    }
    setPdfBusy(true);
    try {
      let total = 0;
      for (const p of paths) {
        total += (await processOnePdf(p)) || 0;
      }
      showToast(`PDF: распознано ${total} заявок`);
      setStatusText(`Распознано ${total} заявок из PDF`);
    } catch (e) {
      setError(e.message);
    } finally {
      setPdfBusy(false);
    }
  };

  const selectPdfFolder = async () => {
    if (!dbReady) {
      setError("Сначала загрузите базу сотрудников");
      return;
    }
    const folder = await dialogs.openPdfFolder();
    if (!folder) return;
    setPdfBusy(true);
    setStatusText(`Папка PDF: ${folder}…`);
    try {
      const r = await api.processPdfFolder(folder);
      const items = r.items || [];
      setPdfFileMap((m) => {
        const next = { ...m };
        for (const it of items) {
          const sf = it.source_file;
          if (sf && !next[sf]) next[sf] = `${folder}\\${sf}`;
        }
        return next;
      });
      setPdfItems(items);
      showToast(`Папка PDF: ${r.count} заявок`);
      setStatusText(`Из папки: ${r.count} заявок`);
    } catch (e) {
      setError(e.message);
    } finally {
      setPdfBusy(false);
    }
  };

  const openFillWizard = () => {
    if (!hasPdf) {
      showToast("Сначала обработайте PDF (файл или папка)");
      return;
    }
    setShowFillWizard(true);
  };

  const exportExcel = async () => {
    if (!hasApp) return;
    const name = `Заявка_${new Date().toISOString().slice(0, 10)}.xlsx`;
    const path = await dialogs.saveExcelFile(name);
    if (!path) return;
    try {
      const r = await api.exportApplication(appRows, path, loginDept);
      showToast(r.message || "Экспорт выполнен");
      setStatusText(`Экспорт: ${path}`);
    } catch (e) {
      setError(e.message);
    }
  };

  const addToDatabase = async () => {
    if (!hasApp) return;
    try {
      const r = await api.addFromApplication(appRows, deptFilter);
      showToast(`В базу: +${r.added}, пропущено: ${r.skipped}`);
      await loadHealth();
    } catch (e) {
      setError(e.message);
    }
  };

  const clearAll = () => {
    if (!hasApp && !hasPdf) return;
    if (!window.confirm("Очистить заявку и список PDF?")) return;
    setAppRows([]);
    setPdfItems([]);
    setPdfFileMap({});
    setSelectedPdf("");
    setStatusText("Очищено");
  };

  const loadBasePage = async (offset = 0) => {
    if (!dbReady) {
      setBaseRows([]);
      setBaseTotal(0);
      setBaseHint("База не загружена. Admin: Настройки → Загрузить Excel-базу.");
      return;
    }
    setBaseLoading(true);
    setBaseHint("Загрузка…");
    try {
      const res = await api.baseGrid({
        q: baseQ.trim() || null,
        department: deptFilter,
        limit: BASE_PAGE_SIZE,
        offset,
      });
      const items = res.items || [];
      const total = res.total || 0;
      setBaseRows(items);
      setBaseTotal(total);
      setBaseOffset(offset);
      if (!total) {
        setBaseHint("Ничего не найдено. Уточните поиск или фильтр ОП.");
      } else {
        const from = offset + 1;
        const to = offset + items.length;
        setBaseHint(`Строки ${from}–${to} из ${total.toLocaleString("ru")}`);
      }
      setError("");
    } catch (e) {
      setBaseRows([]);
      setBaseTotal(0);
      setBaseHint("");
      setError(e.message);
    } finally {
      setBaseLoading(false);
    }
  };

  useEffect(() => {
    if (tab === "base" && session && health) {
      loadBasePage(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, session, deptFilter, health?.employees_ready]);

  const appColDefs = useMemo(
    () => ALL_COLUMNS.map((c) => ({ field: c, headerName: c, width: c.length > 12 ? 140 : 100 })),
    []
  );

  const baseColDefs = useMemo(() => buildBaseColumnDefs(), []);

  if (!session) {
    return <Login onLogin={setSession} />;
  }

  const profile = session.profile || {};
  const profileLine = [profile.fio, profile.position, profile.dept_category]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="app">
      <header className="header">
        <h1>Система заявок на билеты</h1>
        <span className="status">
          {health
            ? `v${health.version} · ${health.employees_count?.toLocaleString("ru")} чел.`
            : "API недоступен — запустите run_api.bat"}
        </span>
        <div className="user-badge">
          <strong>{session.login}</strong>
          <span>{session.department}</span>
          {profileLine && <span className="hint">{profileLine}</span>}
        </div>
        {toast && <span className="hint ok header-toast">{toast}</span>}
        {error && <span className="hint bad header-toast">{error}</span>}
      </header>

      <nav className="toolbar-main">
        <button type="button" onClick={() => setShowCatalog(true)} disabled={!dbReady}>
          Каталог
        </button>
        <button type="button" onClick={selectPdfFile} disabled={pdfBusy || !dbReady}>
          PDF файл
        </button>
        <button type="button" onClick={selectPdfFolder} disabled={pdfBusy || !dbReady}>
          Папка PDF
        </button>
        <button type="button" onClick={() => setShowFioList(true)} disabled={!dbReady}>
          Из списка
        </button>
        <button type="button" onClick={openFillWizard} disabled={!hasPdf}>
          Заполнить из базы
        </button>
        <button type="button" onClick={addToDatabase} disabled={!hasApp || !dbReady}>
          Добавить в базу
        </button>
        <button type="button" className="accent" onClick={exportExcel} disabled={!hasApp}>
          Экспорт Excel
        </button>
        <button type="button" className="danger" onClick={clearAll} disabled={!hasApp && !hasPdf}>
          Очистить
        </button>
        <span className="toolbar-spacer" />
        <label className="dept-select">
          ОП
          <select
            value={dept}
            onChange={(e) => setDept(e.target.value)}
            disabled={!session.is_admin}
          >
            {depts.map((d) => (
              <option key={d} value={d === "Все" ? "" : d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="secondary" onClick={switchUser}>
          Сменить пользователя
        </button>
        <button type="button" className="secondary" onClick={logout}>
          Выход
        </button>
      </nav>

      <nav className="tabs">
        <button
          type="button"
          className={tab === "work" ? "active" : ""}
          onClick={() => setTab("work")}
        >
          Заявка ({appRows.length})
        </button>
        <button
          type="button"
          className={tab === "base" ? "active" : ""}
          onClick={() => setTab("base")}
        >
          База
        </button>
        {session.is_admin && (
          <button
            type="button"
            className={tab === "settings" ? "active" : ""}
            onClick={() => setTab("settings")}
          >
            Настройки
          </button>
        )}
      </nav>

      <main className="main">
        {tab === "work" && (
          <div className="work-layout">
            <section className="pdf-list-panel">
              <h2>Обработанные PDF</h2>
              {pdfBusy && <p className="hint warn">OCR выполняется…</p>}
              <select
                size={Math.min(6, Math.max(3, pdfFileList.length || 3))}
                value={selectedPdf}
                onChange={(e) => setSelectedPdf(e.target.value)}
                className="pdf-listbox"
              >
                {pdfFileList.length === 0 && <option value="">— нет PDF —</option>}
                {pdfFileList.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              <p className="hint">
                Распознанных заявок: {pdfItems.length}
                {selectedPdf ? ` · ${selectedPdf}` : ""}
              </p>
            </section>

            <section className="app-grid-panel">
              <div className="toolbar-row">
                <h2>Заявка — таблица Excel</h2>
                <button
                  type="button"
                  className="secondary"
                  onClick={() =>
                    setAppRows((r) => [...r, emptyApplicationRow(r.length + 1, loginDept)])
                  }
                >
                  + Строка
                </button>
              </div>
              <div className="grid-wrap app-grid-wrap">
                <AgGridReact
                  ref={appGridRef}
                  className="ag-theme-alpine-dark"
                  rowData={appRows}
                  columnDefs={appColDefs}
                  defaultColDef={defaultColDef}
                  onCellValueChanged={(e) => {
                    setAppRows((prev) => {
                      const next = [...prev];
                      next[e.rowIndex] = { ...e.data };
                      return next;
                    });
                  }}
                />
              </div>
            </section>
          </div>
        )}

        {tab === "base" && (
          <div className="tab-panel">
            <div className="toolbar-row">
              <input
                placeholder="Поиск (ФИО / таб. №)"
                value={baseQ}
                onChange={(e) => setBaseQ(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && loadBasePage(0)}
              />
              <button type="button" onClick={() => loadBasePage(0)} disabled={baseLoading}>
                Найти
              </button>
              <button
                type="button"
                className="secondary"
                disabled={baseLoading || baseOffset <= 0}
                onClick={() => loadBasePage(Math.max(0, baseOffset - BASE_PAGE_SIZE))}
              >
                ◀
              </button>
              <button
                type="button"
                className="secondary"
                disabled={baseLoading || baseOffset + BASE_PAGE_SIZE >= baseTotal}
                onClick={() => loadBasePage(baseOffset + BASE_PAGE_SIZE)}
              >
                ▶
              </button>
              <span className={`hint ${baseTotal ? "ok" : ""}`}>
                {baseHint || `До ${BASE_PAGE_SIZE} строк на странице`}
              </span>
            </div>
            <div className="grid-wrap base-grid-wrap">
              <AgGridReact
                ref={baseGridRef}
                className="ag-theme-alpine-dark"
                rowData={baseRows}
                columnDefs={baseColDefs}
                defaultColDef={{ ...defaultColDef, editable: false, suppressSizeToFit: true }}
                suppressColumnVirtualisation={false}
              />
            </div>
          </div>
        )}

        {tab === "settings" && session.is_admin && (
          <div className="settings-panel">
            <h2>Настройки (Admin)</h2>
            <div className="toolbar-row">
              <button type="button" onClick={loadExcelBase} disabled={dbBusy}>
                Загрузить Excel-базу
              </button>
              <button type="button" className="secondary" onClick={reloadCache} disabled={dbBusy}>
                Обновить кэш базы
              </button>
            </div>
            <p className="hint">
              Полный интерфейс как в desktop: run.bat (Tkinter). Electron использует тот же API и
              те же колонки заявки ({ALL_COLUMNS.length}).
            </p>
          </div>
        )}
      </main>

      <footer className="status-bar">{statusText}</footer>

      {showCatalog && (
        <CatalogModal
          deptFilter={deptFilter}
          onPickEmployees={addEmployeesToApp}
          onClose={() => setShowCatalog(false)}
        />
      )}

      {showFioList && (
        <FioListModal
          deptFilter={deptFilter}
          onCreateApplication={addEmployeesToApp}
          onClose={() => setShowFioList(false)}
        />
      )}

      {showFillWizard && (
        <FillWizardModal
          items={pdfItems}
          setItems={setPdfItems}
          pdfFileMap={pdfFileMap}
          deptFilter={deptFilter}
          onAddToApplication={addWizardToApp}
          onPickDuplicate={(candidates, onPick) =>
            setPickModal({ title: "Выбор сотрудника", candidates, onPick })
          }
          onClose={() => setShowFillWizard(false)}
        />
      )}

      {pickModal && (
        <PickModal
          title={pickModal.title}
          candidates={pickModal.candidates}
          onPick={(emp) => {
            pickModal.onPick(emp);
            setPickModal(null);
          }}
          onClose={() => setPickModal(null)}
        />
      )}
    </div>
  );
}

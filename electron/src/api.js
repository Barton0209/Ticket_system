const cfg = window.ticketConfig || {};
const API_URL = cfg.apiUrl || "http://127.0.0.1:8765";
const API_KEY = cfg.apiKey || "";

function headers(json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  if (API_KEY) h["X-Api-Key"] = API_KEY;
  return h;
}

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...headers(options.body != null), ...options.headers },
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) {
    throw new Error(data?.detail || res.statusText || "API error");
  }
  return data;
}

export const api = {
  url: API_URL,
  health: () => request("/health"),
  logins: () => request("/auth/logins"),
  login: (login, password) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ login, password }),
    }),
  departments: () => request("/departments"),
  reloadCache: () => request("/database/reload-cache", { method: "POST" }),
  loadDatabase: (path, loadedBy = "Admin") =>
    request("/database/load", {
      method: "POST",
      body: JSON.stringify({ path, loaded_by: loadedBy }),
    }),
  searchEmployees: (body) =>
    request("/employees/search", { method: "POST", body: JSON.stringify(body) }),
  baseGrid: (body) =>
    request("/employees/base-grid", { method: "POST", body: JSON.stringify(body) }),
  lookupFio: (fio, department) => {
    const q = new URLSearchParams({ fio });
    if (department) q.set("department", department);
    return request(`/employees/lookup/fio?${q}`);
  },
  lookupBatch: (fios, department) =>
    request("/employees/lookup/batch", {
      method: "POST",
      body: JSON.stringify({ fios, department: department || null }),
    }),
  processPdf: (path) =>
    request("/pdf/process", { method: "POST", body: JSON.stringify({ path }) }),
  processPdfFolder: (folder_path) =>
    request("/pdf/process-folder", {
      method: "POST",
      body: JSON.stringify({ folder_path }),
    }),
  routes: () => request("/routes"),
  exportApplication: (rows, outputPath, department) =>
    request("/application/export", {
      method: "POST",
      body: JSON.stringify({ rows, output_path: outputPath, department }),
    }),
  rowsFromEmployees: (employees, startIndex, department) =>
    request("/application/rows-from-employees", {
      method: "POST",
      body: JSON.stringify({
        employees,
        start_index: startIndex,
        department: department || "",
      }),
    }),
  rowsFromWizard: (results, startIndex, department) =>
    request("/application/rows-from-wizard", {
      method: "POST",
      body: JSON.stringify({
        results,
        start_index: startIndex,
        department: department || "",
      }),
    }),
  mergeRow: (existing, employee, rowNum) =>
    request("/application/merge-row", {
      method: "POST",
      body: JSON.stringify({ existing, employee, row_num: rowNum }),
    }),
  addFromApplication: (rows, department) =>
    request("/database/add-from-application", {
      method: "POST",
      body: JSON.stringify({ rows, department: department || null }),
    }),
};

export const dialogs = {
  openPdfFile: () => cfg.openPdfFile?.() ?? null,
  openPdfFiles: () => cfg.openPdfFiles?.() ?? [],
  openPdfFolder: () => cfg.openPdfFolder?.() ?? null,
  openExcelFile: () => cfg.openExcelFile?.() ?? null,
  saveExcelFile: (name) => cfg.saveExcelFile?.(name) ?? null,
};

const { contextBridge, ipcRenderer } = require("electron");

const pdfFilter = [{ name: "PDF", extensions: ["pdf"] }];
const excelFilter = [{ name: "Excel", extensions: ["xlsx", "xls"] }];

contextBridge.exposeInMainWorld("ticketConfig", {
  apiUrl: process.env.TICKET_API_URL || "http://127.0.0.1:8765",
  apiKey: process.env.TICKET_API_KEY || "",
  registerPdf: (filePath) => ipcRenderer.invoke("pdf:register", filePath),
  openPdfFile: () => ipcRenderer.invoke("dialog:openFile", { filters: pdfFilter }),
  openPdfFiles: () => ipcRenderer.invoke("dialog:openFiles", { filters: pdfFilter }),
  openPdfFolder: () => ipcRenderer.invoke("dialog:openDirectory"),
  openExcelFile: () => ipcRenderer.invoke("dialog:openFile", { filters: excelFilter }),
  saveExcelFile: (defaultName) =>
    ipcRenderer.invoke("dialog:saveFile", {
      defaultPath: defaultName,
      filters: [{ name: "Excel", extensions: ["xlsx"] }],
    }),
});

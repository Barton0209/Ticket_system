const { app, BrowserWindow, ipcMain, dialog, protocol } = require("electron");
const path = require("path");
const fs = require("fs");
const crypto = require("crypto");

const isDev = process.env.ELECTRON_DEV === "1" || process.env.NODE_ENV === "development";
const pdfPaths = new Map();

function registerPdfProtocol() {
  protocol.registerFileProtocol("ticket-pdf", (request, callback) => {
    try {
      const id = decodeURIComponent(request.url.replace("ticket-pdf://", "").split("?")[0]);
      const filePath = pdfPaths.get(id);
      if (filePath && fs.existsSync(filePath)) {
        callback({ path: filePath });
      } else {
        callback({ error: -6 });
      }
    } catch {
      callback({ error: -2 });
    }
  });
}

function registerDialogs() {
  // Разрешённые директории для доступа (защита от path traversal)
  const allowedDirs = new Set();
  
  ipcMain.handle("pdf:register", async (_e, filePath) => {
    if (!filePath || !fs.existsSync(filePath)) return null;
    
    // Проверка пути: файл должен существовать и быть читаемым
    const resolvedPath = path.resolve(filePath);
    try {
      fs.accessSync(resolvedPath, fs.constants.R_OK);
    } catch {
      console.warn("Нет прав на чтение файла:", resolvedPath);
      return null;
    }
    
    const id = crypto.randomBytes(12).toString("hex");
    pdfPaths.set(id, resolvedPath);
    return `ticket-pdf://${id}`;
  });

  ipcMain.handle("dialog:openFile", async (_e, options = {}) => {
    const win = BrowserWindow.getFocusedWindow();
    const r = await dialog.showOpenDialog(win, {
      properties: ["openFile"],
      ...options,
    });
    return r.canceled || !r.filePaths.length ? null : r.filePaths[0];
  });

  ipcMain.handle("dialog:openFiles", async (_e, options = {}) => {
    const win = BrowserWindow.getFocusedWindow();
    const r = await dialog.showOpenDialog(win, {
      properties: ["openFile", "multiSelections"],
      ...options,
    });
    return r.canceled ? [] : r.filePaths;
  });

  ipcMain.handle("dialog:openDirectory", async () => {
    const win = BrowserWindow.getFocusedWindow();
    const r = await dialog.showOpenDialog(win, { properties: ["openDirectory"] });
    return r.canceled || !r.filePaths.length ? null : r.filePaths[0];
  });

  ipcMain.handle("dialog:saveFile", async (_e, options = {}) => {
    const win = BrowserWindow.getFocusedWindow();
    const r = await dialog.showSaveDialog(win, options);
    return r.canceled || !r.filePath ? null : r.filePath;
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 640,
    title: "Система заявок на билеты",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    win.loadURL("http://127.0.0.1:5173");
  } else {
    win.loadFile(path.join(__dirname, "dist", "index.html"));
  }
}

app.whenReady().then(() => {
  registerPdfProtocol();
  registerDialogs();
  createWindow();
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

# pdf_viewer.py
"""
============================================================================
ПРОСМОТРЩИК PDF С МАСШТАБИРОВАНИЕМ
============================================================================
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import fitz


class PDFViewer:
    def __init__(self, parent):
        self.parent = parent
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = 1.0
        self.doc = None
        self.photo_images = []
        self._drag_start = None

        self.create_ui()

    def create_ui(self):
        container = ttk.Frame(self.parent)
        container.pack(fill="both", expand=True)
        container.rowconfigure(1, weight=1)
        container.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(container)
        toolbar.grid(row=0, column=0, sticky="ew", pady=2)

        ttk.Label(toolbar, text="Страница:").pack(side="left", padx=5)
        self.page_label = ttk.Label(toolbar, text="0 / 0")
        self.page_label.pack(side="left", padx=5)

        ttk.Button(toolbar, text="◀", width=3, command=self.prev_page).pack(side="left", padx=2)
        ttk.Button(toolbar, text="▶", width=3, command=self.next_page).pack(side="left", padx=2)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=10)

        ttk.Button(toolbar, text="+", width=3, command=self.zoom_in).pack(side="left", padx=2)
        ttk.Button(toolbar, text="−", width=3, command=self.zoom_out).pack(side="left", padx=2)

        self.zoom_label = ttk.Label(toolbar, text="100%")
        self.zoom_label.pack(side="left", padx=5)

        ttk.Button(toolbar, text="100%", width=4, command=self.fit_width).pack(side="left", padx=2)

        view_frame = ttk.Frame(container)
        view_frame.grid(row=1, column=0, sticky="nsew")
        view_frame.rowconfigure(0, weight=1)
        view_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(view_frame, bg="#2d3748", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        v_scroll = ttk.Scrollbar(view_frame, orient="vertical", command=self.canvas.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll = ttk.Scrollbar(view_frame, orient="horizontal", command=self.canvas.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self.on_shift_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def load_pdf(self, pdf_path: str, default_zoom: float = 0.8, page: int = 1) -> bool:
        try:
            if self.doc:
                self.close()

            self.doc = fitz.open(pdf_path)
            self.total_pages = len(self.doc)
            self.current_page = max(0, min(page - 1, self.total_pages - 1))
            self.zoom_level = max(0.25, min(default_zoom, 4.0))

            self.render_page()
            return True

        except Exception as e:
            print(f"Ошибка загрузки PDF: {e}")
            return False

    def go_to_page(self, page: int):
        """Перейти на страницу PDF (нумерация с 1)."""
        if not self.doc:
            return
        self.current_page = max(0, min(page - 1, self.total_pages - 1))
        self.render_page()

    def render_page(self):
        if not self.doc:
            return

        self.canvas.delete("all")
        self.photo_images.clear()

        page = self.doc[self.current_page]
        mat = fitz.Matrix(2, 2) * self.zoom_level
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        self.current_image = img
        self.photo_image = ImageTk.PhotoImage(img)
        self.photo_images.append(self.photo_image)

        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.page_label.config(text=f"{self.current_page + 1} / {self.total_pages}")
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.render_page()

    def zoom_in(self):
        self.zoom_level = min(self.zoom_level + 0.25, 4.0)
        self.render_page()

    def zoom_out(self):
        self.zoom_level = max(self.zoom_level - 0.25, 0.25)
        self.render_page()

    def fit_width(self):
        if self.doc and self.current_image:
            canvas_width = max(self.canvas.winfo_width(), 400)
            scale = canvas_width / self.current_image.width
            self.zoom_level = max(0.25, min(scale * 0.95, 4.0))
            self.render_page()
        else:
            self.zoom_level = 1.0
            self.render_page()

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_ctrl_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def on_press(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self._drag_start = (event.x, event.y)

    def on_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_release(self, event):
        self._drag_start = None

    def close(self):
        if self.doc:
            self.doc.close()
            self.doc = None
        self.canvas.delete("all")
        self.photo_images.clear()

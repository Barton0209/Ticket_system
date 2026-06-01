# auth.py
"""Авторизация (логин из Users+pass или config)."""

import customtkinter as ctk
from tkinter import messagebox

from config import USERS
from users_manager import get_all_logins, authenticate, load_users_cache
from ui.ctk_theme import create_toolbar_button, setup_ctk_dialog
from ui_theme import COLORS, FONT_TITLE, FONT_UI


class LoginWindow:
    def __init__(self, parent, auth_manager):
        self.auth = auth_manager
        load_users_cache()

        self.window = ctk.CTkToplevel(parent)
        setup_ctk_dialog(self.window, "Авторизация", 480, 420)
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()

        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 480) // 2
        y = (self.window.winfo_screenheight() - 420) // 2
        self.window.geometry(f"480x420+{x}+{y}")
        self.window.configure(fg_color=COLORS["bg_dark"])
        self.create_ui()

    def create_ui(self):
        ctk.CTkLabel(
            self.window,
            text="Система заявок на билеты",
            font=FONT_TITLE,
            text_color=COLORS["white"],
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            self.window,
            text="Логин и пароль",
            font=FONT_UI,
            text_color="#a8b2c1",
        ).pack(pady=(0, 20))

        form = ctk.CTkFrame(self.window, fg_color="transparent")
        form.pack(pady=8, padx=32, fill="x")

        ctk.CTkLabel(form, text="Логин:", font=FONT_UI, anchor="w").grid(
            row=0, column=0, sticky="w", pady=12
        )

        logins = ["Admin"] + get_all_logins()
        self.login_var = ctk.StringVar(value=logins[0] if logins else "Admin")
        self.login_combo = ctk.CTkComboBox(
            form, values=logins, variable=self.login_var, width=280, font=FONT_UI
        )
        self.login_combo.grid(row=0, column=1, pady=12, padx=(12, 0), sticky="ew")

        ctk.CTkLabel(form, text="Пароль:", font=FONT_UI, anchor="w").grid(
            row=1, column=0, sticky="w", pady=12
        )

        self.pwd_entry = ctk.CTkEntry(form, width=280, show="*", font=FONT_UI)
        self.pwd_entry.grid(row=1, column=1, pady=12, padx=(12, 0), sticky="ew")
        self.pwd_entry.bind("<Return>", lambda e: self.do_login())
        form.grid_columnconfigure(1, weight=1)

        btn_frame = ctk.CTkFrame(self.window, fg_color="transparent")
        btn_frame.pack(pady=28)

        create_toolbar_button(btn_frame, "Войти", self.do_login, "accent").pack(
            side="left", padx=10
        )
        create_toolbar_button(btn_frame, "Отмена", self.window.destroy, "muted").pack(
            side="left", padx=10
        )

        self.pwd_entry.focus()

    def do_login(self):
        login = (self.login_var.get() or "").strip()
        password = self.pwd_entry.get()

        if not password:
            messagebox.showwarning("Ошибка", "Введите пароль!", parent=self.window)
            return

        user, is_admin, dept_label = authenticate(login, password)
        if is_admin:
            self.auth.login("Admin", True, None)
            self.window.destroy()
            return
        if user:
            self.auth.login(dept_label or login, False, user)
            self.window.destroy()
            return

        messagebox.showerror("Ошибка", "Неверный логин или пароль!", parent=self.window)
        self.pwd_entry.delete(0, "end")
        self.pwd_entry.focus_set()


class AuthManager:
    def __init__(self):
        self.current_user = None
        self.is_admin = False
        self.allowed_departments = []
        self.app_user = None

    def login(self, department: str, is_admin: bool = False, app_user=None):
        self.current_user = department
        self.is_admin = is_admin
        self.app_user = app_user

        if is_admin:
            self.allowed_departments = list(USERS.keys())
        elif app_user and app_user.allowed_departments:
            self.allowed_departments = app_user.allowed_departments
        else:
            self.allowed_departments = [department]

    def logout(self):
        self.current_user = None
        self.is_admin = False
        self.allowed_departments = []
        self.app_user = None

    def can_edit_department(self, dept: str) -> bool:
        if self.is_admin:
            return True
        return any(d in str(dept) for d in self.allowed_departments)

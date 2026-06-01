import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Dict, Callable, List, Tuple

APP_NAME = "Finance Mate"
APP_VERSION = "0.3.0"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "finance_mate.db"

# Optik angelehnt an FiBu Mate – kleinere Kopfzeile / Fußzeile, keine Logos.
BLUE = "#004B93"
RED = "#E30613"
BG = "#E8EEF5"
HEADER = "#D3DEE9"
LINE = "#91A3B5"
TEXT = "#182431"
TEXT2 = "#445364"
WHITE = "#FFFFFF"
CARD_BORDER = "#B7C6D5"
SUCCESS = "#1F7A1F"

HEADER_HEIGHT = 72
FOOTER_HEIGHT = 26
SIDEBAR_WIDTH = 265
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 900


@dataclass(frozen=True)
class AppConfig:
    title: str = APP_NAME
    version: str = APP_VERSION
    width: int = WINDOW_WIDTH
    height: int = WINDOW_HEIGHT


def maximize_window(window: tk.Tk) -> None:
    try:
        window.state("zoomed")
    except Exception:
        try:
            window.attributes("-zoomed", True)
        except Exception:
            window.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")


def ensure_directories() -> None:
    (BASE_DIR / "data").mkdir(exist_ok=True)
    (BASE_DIR / "assets").mkdir(exist_ok=True)
    (BASE_DIR / "docs").mkdir(exist_ok=True)
    (BASE_DIR / "tests").mkdir(exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite() -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "INSERT OR IGNORE INTO app_meta(key, value) VALUES (?, ?)",
            ("app_version", APP_VERSION),
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS gl_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                city TEXT,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                city TEXT,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tax_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                rate REAL NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                due_days INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                iban TEXT NOT NULL UNIQUE,
                bank_name TEXT NOT NULL,
                account_owner TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


class StammdatenView(tk.Frame):
    def __init__(self, parent: tk.Widget, status_callback: Callable[[str], None]):
        super().__init__(parent, bg=BG)
        self.status_callback = status_callback
        self.current_tab = "Sachkonten"
        self.forms: Dict[str, Dict[str, tk.Entry | ttk.Combobox]] = {}
        self.trees: Dict[str, ttk.Treeview] = {}
        self.search_vars: Dict[str, tk.StringVar] = {}

        self.tab_configs = {
            "Sachkonten": {
                "table": "gl_accounts",
                "columns": [
                    ("id", "ID", 50),
                    ("account_no", "Konto", 110),
                    ("name", "Bezeichnung", 260),
                    ("account_type", "Typ", 130),
                    ("active", "Aktiv", 80),
                ],
                "form_fields": [
                    ("account_no", "Konto", "entry"),
                    ("name", "Bezeichnung", "entry"),
                    ("account_type", "Typ", "combo", ["Bilanz", "GuV"]),
                ],
                "insert_sql": "INSERT INTO gl_accounts (account_no, name, account_type) VALUES (?, ?, ?)",
                "search_column": "name",
            },
            "Debitoren": {
                "table": "customers",
                "columns": [
                    ("id", "ID", 50),
                    ("customer_no", "Debitor", 110),
                    ("name", "Name", 260),
                    ("city", "Ort", 160),
                    ("active", "Aktiv", 80),
                ],
                "form_fields": [
                    ("customer_no", "Debitor", "entry"),
                    ("name", "Name", "entry"),
                    ("city", "Ort", "entry"),
                ],
                "insert_sql": "INSERT INTO customers (customer_no, name, city) VALUES (?, ?, ?)",
                "search_column": "name",
            },
            "Kreditoren": {
                "table": "vendors",
                "columns": [
                    ("id", "ID", 50),
                    ("vendor_no", "Kreditor", 110),
                    ("name", "Name", 260),
                    ("city", "Ort", 160),
                    ("active", "Aktiv", 80),
                ],
                "form_fields": [
                    ("vendor_no", "Kreditor", "entry"),
                    ("name", "Name", "entry"),
                    ("city", "Ort", "entry"),
                ],
                "insert_sql": "INSERT INTO vendors (vendor_no, name, city) VALUES (?, ?, ?)",
                "search_column": "name",
            },
            "Steuerkennzeichen": {
                "table": "tax_codes",
                "columns": [
                    ("id", "ID", 50),
                    ("code", "Kennzeichen", 120),
                    ("description", "Beschreibung", 260),
                    ("rate", "Steuersatz %", 120),
                ],
                "form_fields": [
                    ("code", "Kennzeichen", "entry"),
                    ("description", "Beschreibung", "entry"),
                    ("rate", "Steuersatz %", "entry"),
                ],
                "insert_sql": "INSERT INTO tax_codes (code, description, rate) VALUES (?, ?, ?)",
                "search_column": "description",
            },
            "Zahlungsbedingungen": {
                "table": "payment_terms",
                "columns": [
                    ("id", "ID", 50),
                    ("code", "Code", 120),
                    ("description", "Beschreibung", 280),
                    ("due_days", "Tage", 100),
                ],
                "form_fields": [
                    ("code", "Code", "entry"),
                    ("description", "Beschreibung", "entry"),
                    ("due_days", "Tage", "entry"),
                ],
                "insert_sql": "INSERT INTO payment_terms (code, description, due_days) VALUES (?, ?, ?)",
                "search_column": "description",
            },
            "Bankkonten": {
                "table": "bank_accounts",
                "columns": [
                    ("id", "ID", 50),
                    ("iban", "IBAN", 210),
                    ("bank_name", "Bank", 200),
                    ("account_owner", "Kontoinhaber", 220),
                ],
                "form_fields": [
                    ("iban", "IBAN", "entry"),
                    ("bank_name", "Bank", "entry"),
                    ("account_owner", "Kontoinhaber", "entry"),
                ],
                "insert_sql": "INSERT INTO bank_accounts (iban, bank_name, account_owner) VALUES (?, ?, ?)",
                "search_column": "bank_name",
            },
        }

        self._build_ui()
        self.load_all_tables()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ttk.Label(self, text="Stammdaten", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(
            self,
            text="Block 3: Erste Stammdaten sind jetzt mit SQLite verbunden. Neue Einträge können direkt erfasst und gespeichert werden.",
            style="Hint.TLabel",
            wraplength=1000,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        shell = tk.Frame(self, bg=BG)
        shell.grid(row=2, column=0, sticky="nsew")
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=1)

        notebook_wrap = tk.Frame(shell, bg=CARD_BORDER)
        notebook_wrap.pack(fill="both", expand=True)
        body = tk.Frame(notebook_wrap, bg=WHITE)
        body.pack(fill="both", expand=True, padx=1, pady=1)

        notebook = ttk.Notebook(body)
        notebook.pack(fill="both", expand=True, padx=14, pady=14)
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.notebook = notebook

        for tab_name in self.tab_configs:
            tab = tk.Frame(notebook, bg=WHITE)
            notebook.add(tab, text=tab_name)
            self._build_tab(tab_name, tab)

    def _build_tab(self, tab_name: str, parent: tk.Frame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=2)
        parent.grid_columnconfigure(1, weight=1)

        toolbar = tk.Frame(parent, bg=WHITE)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 10))
        toolbar.grid_columnconfigure(1, weight=1)

        tk.Label(toolbar, text=f"{tab_name} verwalten", bg=WHITE, fg=TEXT, font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")

        search_var = tk.StringVar()
        self.search_vars[tab_name] = search_var
        search_entry = ttk.Entry(toolbar, textvariable=search_var)
        search_entry.grid(row=0, column=1, sticky="e", padx=(16, 6))
        search_entry.bind("<KeyRelease>", lambda _event, name=tab_name: self.load_table_data(name))
        ttk.Button(toolbar, text="Aktualisieren", command=lambda name=tab_name: self.load_table_data(name)).grid(row=0, column=2, sticky="e")

        left = tk.Frame(parent, bg=WHITE)
        left.grid(row=1, column=0, sticky="nsew", padx=(8, 12), pady=(0, 8))
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)

        right = tk.Frame(parent, bg=WHITE)
        right.grid(row=1, column=1, sticky="nsew", padx=(0, 8), pady=(0, 8))
        right.grid_columnconfigure(0, weight=1)

        tree = self._create_treeview(left, tab_name)
        self.trees[tab_name] = tree

        form_outer = tk.Frame(right, bg=CARD_BORDER)
        form_outer.pack(fill="both", expand=False, anchor="n")
        form_body = tk.Frame(form_outer, bg=WHITE)
        form_body.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(form_body, text="Neuen Eintrag anlegen", bg=WHITE, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 6))
        tk.Label(form_body, text=f"{tab_name}: Pflichtfelder direkt erfassen und in SQLite speichern.", bg=WHITE, fg=TEXT2, font=("Segoe UI", 9), wraplength=280, justify="left").pack(anchor="w", padx=16, pady=(0, 12))

        field_widgets: Dict[str, tk.Entry | ttk.Combobox] = {}
        for field_key, label_text, field_type, *rest in self.tab_configs[tab_name]["form_fields"]:
            row = tk.Frame(form_body, bg=WHITE)
            row.pack(fill="x", padx=16, pady=5)
            tk.Label(row, text=label_text, bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold"), width=16, anchor="w").pack(side="top", anchor="w")
            if field_type == "combo":
                values = rest[0] if rest else []
                widget = ttk.Combobox(row, values=values, state="readonly")
                if values:
                    widget.set(values[0])
            else:
                widget = ttk.Entry(row)
            widget.pack(fill="x", pady=(4, 0))
            field_widgets[field_key] = widget

        button_row = tk.Frame(form_body, bg=WHITE)
        button_row.pack(fill="x", padx=16, pady=(12, 16))
        ttk.Button(button_row, text="Speichern", command=lambda name=tab_name: self.save_record(name)).pack(side="left")
        ttk.Button(button_row, text="Felder leeren", command=lambda name=tab_name: self.clear_form(name)).pack(side="left", padx=(8, 0))

        self.forms[tab_name] = field_widgets

    def _create_treeview(self, parent: tk.Frame, tab_name: str) -> ttk.Treeview:
        config = self.tab_configs[tab_name]
        columns = [column_key for column_key, _label, _width in config["columns"]]

        outer = tk.Frame(parent, bg=CARD_BORDER)
        outer.grid(row=0, column=0, sticky="nsew")
        inner = tk.Frame(outer, bg=WHITE)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        inner.grid_rowconfigure(0, weight=1)
        inner.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(inner, columns=columns, show="headings", height=15)
        tree.grid(row=0, column=0, sticky="nsew")

        scrollbar_y = ttk.Scrollbar(inner, orient="vertical", command=tree.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar_y.set)

        for key, label, width in config["columns"]:
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="w")

        return tree

    def _on_tab_changed(self, _event=None) -> None:
        selected_index = self.notebook.index(self.notebook.select())
        self.current_tab = list(self.tab_configs.keys())[selected_index]
        self.status_callback(f"Stammdaten geöffnet: {self.current_tab}")
        self.load_table_data(self.current_tab)

    def load_all_tables(self) -> None:
        for tab_name in self.tab_configs:
            self.load_table_data(tab_name)

    def load_table_data(self, tab_name: str) -> None:
        tree = self.trees[tab_name]
        for item in tree.get_children():
            tree.delete(item)

        config = self.tab_configs[tab_name]
        search_text = self.search_vars[tab_name].get().strip()

        sql = f"SELECT * FROM {config['table']}"
        params: List[str] = []
        if search_text:
            sql += f" WHERE {config['search_column']} LIKE ?"
            params.append(f"%{search_text}%")
        sql += " ORDER BY id DESC"

        conn = get_connection()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

        for row in rows:
            values = []
            for key, _label, _width in config["columns"]:
                value = row[key]
                if key == "active":
                    value = "Ja" if value == 1 else "Nein"
                values.append(value)
            tree.insert("", "end", values=values)

    def clear_form(self, tab_name: str) -> None:
        for widget in self.forms[tab_name].values():
            if isinstance(widget, ttk.Combobox):
                values = widget.cget("values")
                widget.set(values[0] if values else "")
            else:
                widget.delete(0, tk.END)
        self.status_callback(f"Felder geleert: {tab_name}")

    def save_record(self, tab_name: str) -> None:
        config = self.tab_configs[tab_name]
        form = self.forms[tab_name]
        values: List[object] = []

        try:
            for field_key, _label_text, _field_type, *_ in config["form_fields"]:
                widget = form[field_key]
                raw_value = widget.get().strip()
                if not raw_value:
                    raise ValueError("Bitte alle Pflichtfelder ausfüllen.")

                if field_key in {"rate"}:
                    values.append(float(raw_value.replace(",", ".")))
                elif field_key in {"due_days"}:
                    values.append(int(raw_value))
                else:
                    values.append(raw_value)

            conn = get_connection()
            try:
                conn.execute(config["insert_sql"], values)
                conn.commit()
            finally:
                conn.close()

            self.load_table_data(tab_name)
            self.clear_form(tab_name)
            self.status_callback(f"Eintrag gespeichert: {tab_name}")
        except sqlite3.IntegrityError:
            messagebox.showerror(APP_NAME, "Der Eintrag konnte nicht gespeichert werden. Der Schlüssel existiert bereits.")
        except ValueError as exc:
            messagebox.showwarning(APP_NAME, str(exc))
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Speichern fehlgeschlagen:\n{exc}")


class FinanceMateApp(tk.Tk):
    def __init__(self, config: AppConfig | None = None):
        super().__init__()
        self.config_obj = config or AppConfig()
        self.title(f"{self.config_obj.title} {self.config_obj.version}")
        self.geometry(f"{self.config_obj.width}x{self.config_obj.height}")
        self.minsize(1220, 760)
        self.configure(bg=BG)
        maximize_window(self)

        self.nav_buttons: Dict[str, ttk.Button] = {}
        self.nav_order = [
            "Dashboard",
            "Stammdaten",
            "Finanzbuchhaltung",
            "Debitoren",
            "Kreditoren",
            "Zahlungen",
            "Reporting",
            "Audit",
            "Einstellungen",
        ]
        self.active_module = tk.StringVar(value="Dashboard")

        self._configure_ttk()
        self._build_layout()
        self._build_header()
        self._build_sidebar()
        self._build_workspace()
        self._build_footer()
        self.show_module("Dashboard")

    def _configure_ttk(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Nav.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 10),
            foreground=TEXT,
            background=WHITE,
            borderwidth=1,
            relief="solid",
            anchor="w",
        )
        style.map("Nav.TButton", background=[("active", "#F4F7FA"), ("pressed", "#E7EEF5")])
        style.configure(
            "NavActive.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 10),
            foreground=BLUE,
            background="#EAF1F8",
            borderwidth=1,
            relief="solid",
            anchor="w",
        )
        style.map("NavActive.TButton", background=[("active", "#EAF1F8"), ("pressed", "#EAF1F8")])
        style.configure("Card.TFrame", background=WHITE)
        style.configure("CardTitle.TLabel", background=WHITE, foreground=TEXT, font=("Segoe UI", 12, "bold"))
        style.configure("CardBody.TLabel", background=WHITE, foreground=TEXT2, font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 16, "bold"))
        style.configure("Hint.TLabel", background=BG, foreground=TEXT2, font=("Segoe UI", 10))

    def _build_layout(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _build_header(self) -> None:
        self.header_frame = tk.Frame(
            self,
            bg=HEADER,
            height=HEADER_HEIGHT,
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)

        title_wrap = tk.Frame(self.header_frame, bg=HEADER)
        title_wrap.grid(row=0, column=0, sticky="w", padx=18)

        tk.Label(title_wrap, text=APP_NAME, bg=HEADER, fg=BLUE, font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(
            title_wrap,
            text="Startarchitektur v0.1 – Desktop, Fullscreen, SQLite-Stammdaten aktiv",
            bg=HEADER,
            fg=TEXT2,
            font=("Segoe UI", 10),
        ).pack(anchor="w")

        widget_bar = tk.Frame(self.header_frame, bg=HEADER)
        widget_bar.grid(row=0, column=1, sticky="e", padx=(10, 18))
        self._mini_widget(widget_bar, "Änderung vorschlagen").pack(side="left", padx=(0, 8), pady=18)
        self._mini_widget(widget_bar, "[i] Hilfe").pack(side="left", pady=18)

    def _mini_widget(self, parent: tk.Widget, text: str) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=5,
            relief="solid",
            bd=1,
            highlightthickness=0,
        )

    def _build_sidebar(self) -> None:
        self.sidebar_frame = tk.Frame(self, bg=BG, width=SIDEBAR_WIDTH, highlightthickness=1, highlightbackground=LINE)
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        tk.Label(self.sidebar_frame, text="Module", bg=BG, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=18, pady=(18, 10))
        tk.Label(self.sidebar_frame, text="Finance-Mate-Startnavigation", bg=BG, fg=TEXT2, font=("Segoe UI", 9)).pack(anchor="w", padx=18, pady=(0, 12))

        for module_name in self.nav_order:
            btn = ttk.Button(
                self.sidebar_frame,
                text=module_name,
                style="Nav.TButton",
                command=lambda value=module_name: self.show_module(value),
            )
            btn.pack(fill="x", padx=14, pady=4)
            self.nav_buttons[module_name] = btn

    def _build_workspace(self) -> None:
        self.workspace_frame = tk.Frame(self, bg=BG)
        self.workspace_frame.grid(row=1, column=1, sticky="nsew")
        self.workspace_frame.grid_rowconfigure(1, weight=1)
        self.workspace_frame.grid_columnconfigure(0, weight=1)

        self.path_bar = tk.Frame(self.workspace_frame, bg=BG)
        self.path_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 6))
        self.path_label = tk.Label(self.path_bar, text="Finance Mate  >  Dashboard", bg=BG, fg=TEXT2, font=("Segoe UI", 9))
        self.path_label.pack(anchor="w")

        self.content_frame = tk.Frame(self.workspace_frame, bg=BG)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=(6, 12))
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

    def _build_footer(self) -> None:
        self.footer_frame = tk.Frame(self, bg=HEADER, height=FOOTER_HEIGHT, highlightthickness=1, highlightbackground=LINE)
        self.footer_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.footer_frame.grid_propagate(False)

        self.status_label = tk.Label(
            self.footer_frame,
            text=f"{APP_NAME} {APP_VERSION}  |  Datenbank: SQLite  |  Fullscreen aktiv",
            bg=HEADER,
            fg=TEXT2,
            font=("Segoe UI", 8),
        )
        self.status_label.pack(side="left", padx=14)

    def set_status(self, text: str) -> None:
        self.status_label.config(text=f"{APP_NAME} {APP_VERSION}  |  {text}")

    def show_module(self, module_name: str) -> None:
        self.active_module.set(module_name)
        self.path_label.config(text=f"Finance Mate  >  {module_name}")
        self.set_status(f"Modul: {module_name}  |  Datenbank: SQLite")

        for name, button in self.nav_buttons.items():
            button.configure(style="NavActive.TButton" if name == module_name else "Nav.TButton")

        for child in self.content_frame.winfo_children():
            child.destroy()

        render_map = {
            "Dashboard": self._render_dashboard,
            "Stammdaten": self._render_stammdaten,
            "Finanzbuchhaltung": self._render_finanzbuchhaltung,
            "Debitoren": self._render_debitoren,
            "Kreditoren": self._render_kreditoren,
            "Zahlungen": self._render_zahlungen,
            "Reporting": self._render_reporting,
            "Audit": self._render_audit,
            "Einstellungen": self._render_einstellungen,
        }
        render_map.get(module_name, self._render_dashboard)()

    def _render_dashboard(self) -> None:
        wrapper = self._create_two_by_two_grid()
        self._card(wrapper, 0, 0, "Systemstart", "Finance Mate startet jetzt im Fullscreen/Maximiert-Modus und initialisiert SQLite automatisch.")
        self._card(wrapper, 0, 1, "Stammdaten aktiv", "Sachkonten, Debitoren, Kreditoren, Steuerkennzeichen, Zahlungsbedingungen und Bankkonten sind jetzt als SQLite-Tabellen angelegt.")
        self._card(wrapper, 1, 0, "Nächste Coding-Blöcke", "1) Journalbuchungen\n2) Debitoren-/Kreditorenlogik\n3) Zahlungen\n4) Reporting")
        self._card(wrapper, 1, 1, "Projektstatus", "Start bei 0 Nutzern. Zielarchitektur bleibt vorbereitet für späteren PostgreSQL-Multiuser-Betrieb.")

    def _render_stammdaten(self) -> None:
        view = StammdatenView(self.content_frame, self.set_status)
        view.grid(row=0, column=0, sticky="nsew")

    def _render_finanzbuchhaltung(self) -> None:
        frame = self._create_single_area("Finanzbuchhaltung", "Geplant für Block 4: Journalbuchungen, Buchungsvalidierung, Soll/Haben-Logik, Belegnummern und Storno.")
        self._list_block(frame, ["Journalbuchung", "Buchungssätze", "Beleglogik", "Periodenprüfung", "Buchungshistorie"])

    def _render_debitoren(self) -> None:
        frame = self._create_single_area("Debitoren", "Hier entsteht die Forderungslogik: Ausgangsrechnungen, offene Posten, Zahlungseingänge und Ausgleich.")
        self._list_block(frame, ["Ausgangsrechnungen", "Offene Posten", "Zahlungseingänge", "Teilzahlungen", "Mahnstatus-Basis"])

    def _render_kreditoren(self) -> None:
        frame = self._create_single_area("Kreditoren", "Hier entsteht die Verbindlichkeitenlogik: Eingangsrechnungen, Fälligkeiten, Zahlungen und Ausgleich.")
        self._list_block(frame, ["Eingangsrechnungen", "Offene Posten", "Fälligkeitsübersicht", "Zahlungsausgang", "Ausgleich"])

    def _render_zahlungen(self) -> None:
        frame = self._create_single_area("Zahlungen", "Für v0.1 zunächst schlank: manuelle Zahlungsbuchung, Zuordnung zu offenen Posten und einfache Kontenabstimmung.")
        self._list_block(frame, ["Bankkonten", "Manuelle Zahlungen", "OP-Zuordnung", "Kontenabstimmung", "später: Bankimport / PostgreSQL-Betrieb"])

    def _render_reporting(self) -> None:
        frame = self._create_single_area("Reporting", "Die ersten Standardberichte werden auf diesem Bereich aufsetzen.")
        self._list_block(frame, ["Saldenliste", "Kontoblatt", "OP-Liste Debitoren", "OP-Liste Kreditoren", "Fälligkeitsreport", "Buchungsjournal"])

    def _render_audit(self) -> None:
        frame = self._create_single_area("Audit", "Von Anfang an vorgesehen: Nachvollziehbarkeit von Änderungen, Statuswechseln und späteren Freigaben.")
        self._list_block(frame, ["Änderungsprotokoll", "Benutzerhistorie", "Statuswechsel", "Freigabeverlauf (später)"])

    def _render_einstellungen(self) -> None:
        frame = self._create_single_area("Einstellungen", "Grundkonfiguration für Finance Mate – Start mit SQLite, später vorbereitet für PostgreSQL.")
        self._list_block(frame, ["Mandant/Firma (Single-Company Start)", "Systemparameter", "Nummernkreise", "Datenbankmodus: SQLite", "später: PostgreSQL-Umschaltung"])

    def _create_two_by_two_grid(self) -> tk.Frame:
        wrapper = tk.Frame(self.content_frame, bg=BG)
        wrapper.grid(row=0, column=0, sticky="nsew")
        for idx in range(2):
            wrapper.grid_columnconfigure(idx, weight=1, uniform="cards")
            wrapper.grid_rowconfigure(idx, weight=1, uniform="cards")
        return wrapper

    def _create_single_area(self, title: str, text: str) -> tk.Frame:
        wrapper = tk.Frame(self.content_frame, bg=BG)
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.grid_columnconfigure(0, weight=1)

        ttk.Label(wrapper, text=title, style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(wrapper, text=text, style="Hint.TLabel", wraplength=900, justify="left").grid(row=1, column=0, sticky="w", pady=(0, 12))
        return wrapper

    def _list_block(self, parent: tk.Frame, items: list[str]) -> None:
        outer = tk.Frame(parent, bg=CARD_BORDER)
        outer.grid(row=2, column=0, sticky="nsew")
        body = tk.Frame(outer, bg=WHITE)
        body.pack(fill="both", expand=True, padx=1, pady=1)

        for idx, item in enumerate(items):
            row = tk.Frame(body, bg=WHITE)
            row.pack(fill="x", padx=16, pady=(12 if idx == 0 else 6, 0))
            tk.Label(row, text="•", bg=WHITE, fg=BLUE, font=("Segoe UI", 11, "bold")).pack(side="left")
            tk.Label(row, text=item, bg=WHITE, fg=TEXT, font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))

    def _card(self, parent: tk.Widget, row: int, column: int, title: str, body: str) -> None:
        outer = tk.Frame(parent, bg=CARD_BORDER, bd=0, highlightthickness=0)
        outer.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
        inner = ttk.Frame(outer, style="Card.TFrame", padding=16)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        ttk.Label(inner, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(inner, text=body, style="CardBody.TLabel", wraplength=420, justify="left").pack(anchor="w", pady=(8, 0))


def main() -> None:
    ensure_directories()
    init_sqlite()
    app = FinanceMateApp()
    app.mainloop()


if __name__ == "__main__":
    main()

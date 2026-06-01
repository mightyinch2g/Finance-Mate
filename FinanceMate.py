
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, Callable, List, Optional, Any

APP_NAME = "Finance Mate"
APP_VERSION = "0.5.1"
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
WARNING = "#A15C00"

HEADER_HEIGHT = 72
FOOTER_HEIGHT = 26
SIDEBAR_WIDTH = 265
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 900
DATE_FMT = "%d.%m.%Y"
TAX_SCOPE_VALUES = ["V - Vorsteuer", "A - Ausgangssteuer", "X - Ausland"]
COUNTRY_HINT = "DE/AU/CH/CN/US/..."


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


def table_has_column(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, column_sql: str) -> None:
    if not table_has_column(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")


def parse_amount(raw_value: str) -> float:
    value = (raw_value or "").strip().replace(".", "").replace(",", ".")
    if not value:
        return 0.0
    return round(float(value), 2)


def format_amount(value: float) -> str:
    return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def validate_date(date_text: str) -> str:
    try:
        parsed = datetime.strptime(date_text.strip(), DATE_FMT)
        return parsed.strftime(DATE_FMT)
    except Exception as exc:
        raise ValueError("Datum muss im Format TT.MM.JJJJ eingegeben werden.") from exc


def calc_due_date(invoice_date: str, due_days: int) -> str:
    parsed = datetime.strptime(validate_date(invoice_date), DATE_FMT)
    return (parsed + timedelta(days=int(due_days))).strftime(DATE_FMT)


def yes_no_to_int(value: str) -> int:
    return 1 if (value or "").strip().lower() in {"ja", "1", "true"} else 0


def int_to_yes_no(value: Any) -> str:
    return "Ja" if int(value or 0) == 1 else "Nein"


def normalize_tax_code(scope_display: str, raw_code: str) -> str:
    prefix = (scope_display or "A")[:1].upper()
    cleaned = (raw_code or "").strip().upper().replace(" ", "")
    if not cleaned:
        raise ValueError("Bitte ein Steuerkennzeichen eingeben.")
    if cleaned[0] in {"V", "A", "X"}:
        cleaned = cleaned[1:]
    return f"{prefix}{cleaned}"


def format_partner_address(row: sqlite3.Row) -> str:
    parts = []
    street = (row.get("street") if isinstance(row, dict) else row["street"]) if "street" in row.keys() else ""
    postal = row["postal_code"] if "postal_code" in row.keys() else ""
    city = row["city"] if "city" in row.keys() else ""
    country = row["country_code"] if "country_code" in row.keys() else ""
    if street:
        parts.append(street)
    line2 = " ".join(part for part in [postal, city] if part)
    if line2:
        parts.append(line2)
    if country:
        parts.append(country)
    return ", ".join(parts)


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
        # Bankkonten bleiben aus Kompatibilitätsgründen in der DB bestehen,
        # werden aber fachlich nicht mehr im Stammdaten-UI verwendet.
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
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_no TEXT NOT NULL UNIQUE,
                booking_date TEXT NOT NULL,
                posting_text TEXT NOT NULL,
                total_debit REAL NOT NULL,
                total_credit REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS journal_entry_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_entry_id INTEGER NOT NULL,
                line_no INTEGER NOT NULL,
                account_no TEXT NOT NULL,
                account_name TEXT NOT NULL,
                debit REAL NOT NULL DEFAULT 0,
                credit REAL NOT NULL DEFAULT 0,
                line_text TEXT,
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT NOT NULL UNIQUE,
                customer_no TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                posting_text TEXT NOT NULL,
                amount REAL NOT NULL,
                tax_code TEXT,
                payment_term_code TEXT,
                status TEXT NOT NULL DEFAULT 'Offen',
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS open_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                reference_no TEXT NOT NULL UNIQUE,
                partner_no TEXT NOT NULL,
                partner_name TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                amount REAL NOT NULL,
                open_amount REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # Migrationen / Erweiterungen fuer Stammdaten
        for table in ("customers", "vendors"):
            ensure_column(conn, table, "street", "TEXT DEFAULT ''")
            ensure_column(conn, table, "country_code", "TEXT DEFAULT ''")
            ensure_column(conn, table, "postal_code", "TEXT DEFAULT ''")
            ensure_column(conn, table, "iban", "TEXT DEFAULT ''")
            ensure_column(conn, table, "vat_id", "TEXT DEFAULT ''")
            ensure_column(conn, table, "tax_no", "TEXT DEFAULT ''")
        ensure_column(conn, "tax_codes", "tax_scope", "TEXT DEFAULT 'A'")
        ensure_column(conn, "customer_invoices", "customer_address", "TEXT DEFAULT ''")

        conn.commit()
    finally:
        conn.close()


class StammdatenView(tk.Frame):
    def __init__(self, parent: tk.Widget, status_callback: Callable[[str], None]):
        super().__init__(parent, bg=BG)
        self.status_callback = status_callback
        self.current_tab = "Sachkonten"
        self.forms: Dict[str, Dict[str, tk.Widget]] = {}
        self.trees: Dict[str, ttk.Treeview] = {}
        self.search_vars: Dict[str, tk.StringVar] = {}
        self.edit_ids: Dict[str, Optional[int]] = {}
        self.mode_labels: Dict[str, tk.Label] = {}

        self.tab_configs = {
            "Sachkonten": {
                "table": "gl_accounts",
                "columns": [
                    ("id", "ID", 50),
                    ("account_no", "Konto-ID", 120),
                    ("name", "Bezeichnung", 260),
                    ("account_type", "Typ", 130),
                    ("active", "Aktiv", 80),
                ],
                "form_fields": [
                    ("account_no", "Konto-ID", "entry"),
                    ("name", "Kontenbezeichnung", "entry"),
                    ("account_type", "Typ", "combo", ["Bilanz", "GuV"]),
                    ("active", "Aktiv", "combo", ["Ja", "Nein"]),
                ],
                "insert_sql": "INSERT INTO gl_accounts (account_no, name, account_type, active) VALUES (?, ?, ?, ?)",
                "update_sql": "UPDATE gl_accounts SET account_no = ?, name = ?, account_type = ?, active = ? WHERE id = ?",
                "search_column": "name",
                "value_mapper": self._map_default_values,
                "load_mapper": self._load_default_values,
            },
            "Debitoren": {
                "table": "customers",
                "columns": [
                    ("id", "ID", 50),
                    ("customer_no", "Debitor-ID", 120),
                    ("name", "Name", 220),
                    ("street", "Straße / Hausnr.", 180),
                    ("postal_code", "PLZ", 80),
                    ("city", "Ort", 120),
                    ("country_code", "Land", 70),
                    ("iban", "IBAN", 170),
                    ("vat_id", "USt.-ID", 120),
                    ("tax_no", "Steuernummer", 140),
                    ("active", "Aktiv", 80),
                ],
                "form_fields": [
                    ("customer_no", "Debitor-ID", "entry"),
                    ("name", "Name", "entry"),
                    ("street", "Straße / Hausnummer", "entry"),
                    ("country_code", "Länderkürzel", "entry_placeholder", COUNTRY_HINT),
                    ("postal_code", "Postleitzahl", "entry"),
                    ("city", "Ort / Stadt", "entry"),
                    ("iban", "Kontoverbindung / IBAN", "entry"),
                    ("vat_id", "USt.-ID", "entry"),
                    ("tax_no", "Steuernummer", "entry"),
                    ("active", "Aktiv", "combo", ["Ja", "Nein"]),
                ],
                "insert_sql": "INSERT INTO customers (customer_no, name, street, country_code, postal_code, city, iban, vat_id, tax_no, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                "update_sql": "UPDATE customers SET customer_no = ?, name = ?, street = ?, country_code = ?, postal_code = ?, city = ?, iban = ?, vat_id = ?, tax_no = ?, active = ? WHERE id = ?",
                "search_column": "name",
                "value_mapper": self._map_default_values,
                "load_mapper": self._load_default_values,
            },
            "Kreditoren": {
                "table": "vendors",
                "columns": [
                    ("id", "ID", 50),
                    ("vendor_no", "Kreditor-ID", 120),
                    ("name", "Name", 220),
                    ("street", "Straße / Hausnr.", 180),
                    ("postal_code", "PLZ", 80),
                    ("city", "Ort", 120),
                    ("country_code", "Land", 70),
                    ("iban", "IBAN", 170),
                    ("vat_id", "USt.-ID", 120),
                    ("tax_no", "Steuernummer", 140),
                    ("active", "Aktiv", 80),
                ],
                "form_fields": [
                    ("vendor_no", "Kreditor-ID", "entry"),
                    ("name", "Name", "entry"),
                    ("street", "Straße / Hausnummer", "entry"),
                    ("country_code", "Länderkürzel", "entry_placeholder", COUNTRY_HINT),
                    ("postal_code", "Postleitzahl", "entry"),
                    ("city", "Ort / Stadt", "entry"),
                    ("iban", "Kontoverbindung / IBAN", "entry"),
                    ("vat_id", "USt.-ID", "entry"),
                    ("tax_no", "Steuernummer", "entry"),
                    ("active", "Aktiv", "combo", ["Ja", "Nein"]),
                ],
                "insert_sql": "INSERT INTO vendors (vendor_no, name, street, country_code, postal_code, city, iban, vat_id, tax_no, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                "update_sql": "UPDATE vendors SET vendor_no = ?, name = ?, street = ?, country_code = ?, postal_code = ?, city = ?, iban = ?, vat_id = ?, tax_no = ?, active = ? WHERE id = ?",
                "search_column": "name",
                "value_mapper": self._map_default_values,
                "load_mapper": self._load_default_values,
            },
            "Steuerkennzeichen": {
                "table": "tax_codes",
                "columns": [
                    ("id", "ID", 50),
                    ("code", "Kennzeichen", 120),
                    ("tax_scope", "Kategorie", 130),
                    ("description", "Beschreibung", 260),
                    ("rate", "Steuersatz %", 120),
                ],
                "form_fields": [
                    ("tax_scope", "Kategorie", "combo", TAX_SCOPE_VALUES),
                    ("code", "Kennzeichen", "entry"),
                    ("description", "Beschreibung", "entry"),
                    ("rate", "Steuersatz %", "entry"),
                ],
                "insert_sql": "INSERT INTO tax_codes (code, description, rate, tax_scope) VALUES (?, ?, ?, ?)",
                "update_sql": "UPDATE tax_codes SET code = ?, description = ?, rate = ?, tax_scope = ? WHERE id = ?",
                "search_column": "description",
                "value_mapper": self._map_tax_values,
                "load_mapper": self._load_tax_values,
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
                "update_sql": "UPDATE payment_terms SET code = ?, description = ?, due_days = ? WHERE id = ?",
                "search_column": "description",
                "value_mapper": self._map_default_values,
                "load_mapper": self._load_default_values,
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
            text="Block 5 Erweiterung: Bearbeitung bestehender Stammdaten inkl. bearbeitbarer fachlicher IDs für Sachkonten, Debitoren, Kreditoren und Steuerkennzeichen. Debitoren/Kreditoren enthalten jetzt vollständige Adress- und Steuerdaten. Der Reiter Bankkonten ist im UI entfallen, weil Kontoverbindungen direkt am Partner gepflegt werden.",
            style="Hint.TLabel",
            wraplength=1100,
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
            self.edit_ids[tab_name] = None

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
        tree.bind("<<TreeviewSelect>>", lambda _event, name=tab_name: self.load_selected_record(name))

        form_outer = tk.Frame(right, bg=CARD_BORDER)
        form_outer.pack(fill="both", expand=True, anchor="n")
        form_body = tk.Frame(form_outer, bg=WHITE)
        form_body.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(form_body, text="Eintrag anlegen / bearbeiten", bg=WHITE, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 6))
        mode_label = tk.Label(form_body, text="Modus: Neuer Eintrag", bg=WHITE, fg=TEXT2, font=("Segoe UI", 9), wraplength=320, justify="left")
        mode_label.pack(anchor="w", padx=16, pady=(0, 12))
        self.mode_labels[tab_name] = mode_label

        field_widgets: Dict[str, tk.Widget] = {}
        for field_key, label_text, field_type, *rest in self.tab_configs[tab_name]["form_fields"]:
            row = tk.Frame(form_body, bg=WHITE)
            row.pack(fill="x", padx=16, pady=5)
            tk.Label(row, text=label_text, bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold"), anchor="w").pack(side="top", anchor="w")
            if field_type == "combo":
                values = rest[0] if rest else []
                widget = ttk.Combobox(row, values=values, state="readonly")
                if values:
                    widget.set(values[0])
            else:
                widget = ttk.Entry(row)
                if field_type == "entry_placeholder" and rest:
                    widget.insert(0, str(rest[0]))
            widget.pack(fill="x", pady=(4, 0))
            field_widgets[field_key] = widget

        button_row = tk.Frame(form_body, bg=WHITE)
        button_row.pack(fill="x", padx=16, pady=(12, 16))
        ttk.Button(button_row, text="Speichern / Aktualisieren", command=lambda name=tab_name: self.save_record(name)).pack(side="left")
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

        tree = ttk.Treeview(inner, columns=columns, show="headings", height=16)
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
        self.clear_form(self.current_tab)

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
                value = row[key] if key in row.keys() else ""
                if key == "active":
                    value = int_to_yes_no(value)
                elif key == "rate":
                    value = format_amount(value)
                values.append(value)
            tree.insert("", "end", values=values)

    def load_selected_record(self, tab_name: str) -> None:
        tree = self.trees[tab_name]
        selected = tree.selection()
        if not selected:
            return
        item = tree.item(selected[0], "values")
        if not item:
            return
        record_id = int(item[0])
        config = self.tab_configs[tab_name]
        conn = get_connection()
        try:
            row = conn.execute(f"SELECT * FROM {config['table']} WHERE id = ?", (record_id,)).fetchone()
        finally:
            conn.close()
        if not row:
            return
        self.edit_ids[tab_name] = record_id
        self.mode_labels[tab_name].config(text=f"Modus: Bearbeitung des Eintrags mit DB-ID {record_id}", fg=WARNING)
        config["load_mapper"](tab_name, row)
        self.status_callback(f"Bearbeitung geladen: {tab_name} / ID {record_id}")

    def clear_form(self, tab_name: str) -> None:
        for widget in self.forms[tab_name].values():
            if isinstance(widget, ttk.Combobox):
                values = widget.cget("values")
                widget.set(values[0] if values else "")
            else:
                widget.delete(0, tk.END)
        # Placeholder ruecksetzen
        for field_key, _label, field_type, *rest in self.tab_configs[tab_name]["form_fields"]:
            if field_type == "entry_placeholder" and rest:
                widget = self.forms[tab_name][field_key]
                if isinstance(widget, ttk.Entry):
                    widget.insert(0, str(rest[0]))
        self.edit_ids[tab_name] = None
        self.mode_labels[tab_name].config(text="Modus: Neuer Eintrag", fg=TEXT2)
        self.status_callback(f"Felder geleert: {tab_name}")

    def _map_default_values(self, tab_name: str) -> List[object]:
        values: List[object] = []
        for field_key, _label_text, _field_type, *_ in self.tab_configs[tab_name]["form_fields"]:
            widget = self.forms[tab_name][field_key]
            raw_value = widget.get().strip()
            if not raw_value:
                raise ValueError("Bitte alle Pflichtfelder ausfüllen.")
            if field_key == "active":
                values.append(yes_no_to_int(raw_value))
            elif field_key == "rate":
                values.append(float(raw_value.replace(",", ".")))
            elif field_key == "due_days":
                values.append(int(raw_value))
            else:
                values.append(raw_value)
        return values

    def _load_default_values(self, tab_name: str, row: sqlite3.Row) -> None:
        for field_key, _label, field_type, *_ in self.tab_configs[tab_name]["form_fields"]:
            widget = self.forms[tab_name][field_key]
            value = row[field_key] if field_key in row.keys() else ""
            if isinstance(widget, ttk.Combobox):
                if field_key == "active":
                    widget.set(int_to_yes_no(value))
                else:
                    widget.set(str(value))
            else:
                widget.delete(0, tk.END)
                widget.insert(0, "" if value is None else str(value))

    def _map_tax_values(self, tab_name: str) -> List[object]:
        scope_display = self.forms[tab_name]["tax_scope"].get().strip()
        code_raw = self.forms[tab_name]["code"].get().strip()
        description = self.forms[tab_name]["description"].get().strip()
        rate_raw = self.forms[tab_name]["rate"].get().strip()
        if not scope_display or not description or not rate_raw:
            raise ValueError("Bitte alle Pflichtfelder des Steuerkennzeichens ausfüllen.")
        code = normalize_tax_code(scope_display, code_raw)
        rate = float(rate_raw.replace(",", "."))
        tax_scope = scope_display[:1].upper()
        return [code, description, rate, tax_scope]

    def _load_tax_values(self, tab_name: str, row: sqlite3.Row) -> None:
        mapping = {"V": TAX_SCOPE_VALUES[0], "A": TAX_SCOPE_VALUES[1], "X": TAX_SCOPE_VALUES[2]}
        self.forms[tab_name]["tax_scope"].set(mapping.get((row["tax_scope"] or "A")[:1].upper(), TAX_SCOPE_VALUES[1]))
        for key in ["code", "description", "rate"]:
            widget = self.forms[tab_name][key]
            if isinstance(widget, ttk.Entry):
                widget.delete(0, tk.END)
                if key == "rate":
                    widget.insert(0, str(row[key]))
                else:
                    widget.insert(0, "" if row[key] is None else str(row[key]))

    def save_record(self, tab_name: str) -> None:
        config = self.tab_configs[tab_name]
        values = config["value_mapper"](tab_name)
        edit_id = self.edit_ids.get(tab_name)
        try:
            conn = get_connection()
            try:
                if edit_id is None:
                    conn.execute(config["insert_sql"], values)
                else:
                    conn.execute(config["update_sql"], values + [edit_id])
                conn.commit()
            finally:
                conn.close()
            self.load_table_data(tab_name)
            self.clear_form(tab_name)
            self.status_callback(f"Eintrag gespeichert/aktualisiert: {tab_name}")
        except sqlite3.IntegrityError:
            messagebox.showerror(APP_NAME, "Der Eintrag konnte nicht gespeichert werden. Eine ID bzw. ein eindeutiger Schlüssel existiert bereits.")
        except ValueError as exc:
            messagebox.showwarning(APP_NAME, str(exc))
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Speichern fehlgeschlagen:\n{exc}")


class JournalView(tk.Frame):
    def __init__(self, parent: tk.Widget, status_callback: Callable[[str], None]):
        super().__init__(parent, bg=BG)
        self.status_callback = status_callback
        self.line_items: List[dict] = []
        self.account_map = self._load_accounts()
        self.account_display_map = {f"{no} | {name}": {"account_no": no, "name": name} for no, name in self.account_map.items()}
        self._build_ui()
        self.reload_journal_entries()
        self._update_totals()

    def _load_accounts(self) -> Dict[str, str]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT account_no, name FROM gl_accounts WHERE active = 1 ORDER BY account_no").fetchall()
            return {row["account_no"]: row["name"] for row in rows}
        finally:
            conn.close()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        ttk.Label(self, text="Finanzbuchhaltung", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(
            self,
            text="Block 4: Journalbuchungen mit Soll/Haben-Prüfung, Buchungszeilen und Speicherung in SQLite.",
            style="Hint.TLabel",
            wraplength=1000,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        shell = tk.Frame(self, bg=BG)
        shell.grid(row=2, column=0, sticky="nsew")
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=7)
        shell.grid_columnconfigure(1, weight=5)

        left_outer = tk.Frame(shell, bg=CARD_BORDER)
        left_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left = tk.Frame(left_outer, bg=WHITE)
        left.pack(fill="both", expand=True, padx=1, pady=1)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(3, weight=1)

        right_outer = tk.Frame(shell, bg=CARD_BORDER)
        right_outer.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right = tk.Frame(right_outer, bg=WHITE)
        right.pack(fill="both", expand=True, padx=1, pady=1)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        header = tk.Frame(left, bg=WHITE)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        for idx in range(4):
            header.grid_columnconfigure(idx, weight=1)

        self.document_no_var = tk.StringVar(value=self._generate_document_no())
        self.booking_date_var = tk.StringVar(value=datetime.now().strftime(DATE_FMT))
        self.posting_text_var = tk.StringVar()

        self._labeled_entry(header, 0, 0, "Belegnummer", self.document_no_var)
        self._labeled_entry(header, 0, 1, "Buchungsdatum", self.booking_date_var)
        self._labeled_entry(header, 0, 2, "Buchungstext", self.posting_text_var, columnspan=2)

        line_box_outer = tk.Frame(left, bg=CARD_BORDER)
        line_box_outer.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        line_box = tk.Frame(line_box_outer, bg=WHITE)
        line_box.pack(fill="both", expand=True, padx=1, pady=1)
        for idx in range(6):
            line_box.grid_columnconfigure(idx, weight=1)

        tk.Label(line_box, text="Buchungszeile hinzufügen", bg=WHITE, fg=TEXT, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, columnspan=6, sticky="w", padx=12, pady=(12, 8))

        account_choices = list(self.account_display_map.keys())
        self.line_account_var = tk.StringVar(value=account_choices[0] if account_choices else "")
        self.line_text_var = tk.StringVar()
        self.line_debit_var = tk.StringVar()
        self.line_credit_var = tk.StringVar()

        self._labeled_combo(line_box, 1, 0, "Konto", self.line_account_var, account_choices, width=34)
        self._labeled_entry(line_box, 1, 2, "Zeilentext", self.line_text_var)
        self._labeled_entry(line_box, 1, 3, "Soll", self.line_debit_var)
        self._labeled_entry(line_box, 1, 4, "Haben", self.line_credit_var)

        action_row = tk.Frame(line_box, bg=WHITE)
        action_row.grid(row=1, column=5, sticky="ew", padx=12, pady=(22, 12))
        ttk.Button(action_row, text="Zeile hinzufügen", command=self.add_line_item).pack(fill="x")
        ttk.Button(action_row, text="Zeile leeren", command=self.clear_line_inputs).pack(fill="x", pady=(8, 0))

        tree_outer = tk.Frame(left, bg=CARD_BORDER)
        tree_outer.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 12))
        tree_inner = tk.Frame(tree_outer, bg=WHITE)
        tree_inner.pack(fill="both", expand=True, padx=1, pady=1)
        tree_inner.grid_rowconfigure(0, weight=1)
        tree_inner.grid_columnconfigure(0, weight=1)

        self.lines_tree = ttk.Treeview(tree_inner, columns=("line_no", "account_no", "account_name", "line_text", "debit", "credit"), show="headings", height=10)
        self.lines_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y = ttk.Scrollbar(tree_inner, orient="vertical", command=self.lines_tree.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.lines_tree.configure(yscrollcommand=scrollbar_y.set)
        for key, title, width in [
            ("line_no", "Pos", 45), ("account_no", "Konto", 90), ("account_name", "Bezeichnung", 190),
            ("line_text", "Zeilentext", 200), ("debit", "Soll", 90), ("credit", "Haben", 90),
        ]:
            self.lines_tree.heading(key, text=title)
            self.lines_tree.column(key, width=width, anchor="w")

        footer_left = tk.Frame(left, bg=WHITE)
        footer_left.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
        footer_left.grid_columnconfigure(0, weight=1)
        self.total_label = tk.Label(footer_left, text="Soll: 0,00 | Haben: 0,00 | Differenz: 0,00", bg=WHITE, fg=TEXT2, font=("Segoe UI", 10, "bold"))
        self.total_label.grid(row=0, column=0, sticky="w")
        button_row = tk.Frame(footer_left, bg=WHITE)
        button_row.grid(row=0, column=1, sticky="e")
        ttk.Button(button_row, text="Markierte Zeile löschen", command=self.remove_selected_line).pack(side="left")
        ttk.Button(button_row, text="Beleg leeren", command=self.clear_journal_form).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Buchung speichern", command=self.save_journal_entry).pack(side="left", padx=(8, 0))

        tk.Label(right, text="Letzte Buchungen", bg=WHITE, fg=TEXT, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))
        tk.Label(right, text="Zu Kontrollzwecken werden die letzten 50 Journalbelege mit Summen angezeigt.", bg=WHITE, fg=TEXT2, font=("Segoe UI", 9), wraplength=360, justify="left").grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))
        history_outer = tk.Frame(right, bg=CARD_BORDER)
        history_outer.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        history_inner = tk.Frame(history_outer, bg=WHITE)
        history_inner.pack(fill="both", expand=True, padx=1, pady=1)
        history_inner.grid_rowconfigure(0, weight=1)
        history_inner.grid_columnconfigure(0, weight=1)
        self.history_tree = ttk.Treeview(history_inner, columns=("document_no", "booking_date", "posting_text", "total_debit", "line_count"), show="headings", height=18)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        history_scroll = ttk.Scrollbar(history_inner, orient="vertical", command=self.history_tree.yview)
        history_scroll.grid(row=0, column=1, sticky="ns")
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        for key, title, width in [
            ("document_no", "Beleg", 120), ("booking_date", "Datum", 90), ("posting_text", "Text", 180),
            ("total_debit", "Summe", 90), ("line_count", "Zeilen", 70),
        ]:
            self.history_tree.heading(key, text=title)
            self.history_tree.column(key, width=width, anchor="w")

    def _labeled_entry(self, parent: tk.Widget, row: int, column: int, label: str, variable: tk.StringVar, columnspan: int = 1) -> None:
        box = tk.Frame(parent, bg=WHITE)
        box.grid(row=row, column=column, columnspan=columnspan, sticky="ew", padx=12, pady=4)
        tk.Label(box, text=label, bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Entry(box, textvariable=variable).pack(fill="x", pady=(4, 0))

    def _labeled_combo(self, parent: tk.Widget, row: int, column: int, label: str, variable: tk.StringVar, values: List[str], width: int = 20) -> None:
        box = tk.Frame(parent, bg=WHITE)
        box.grid(row=row, column=column, columnspan=2, sticky="ew", padx=12, pady=4)
        tk.Label(box, text=label, bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        combo = ttk.Combobox(box, textvariable=variable, values=values, state="readonly", width=width)
        combo.pack(fill="x", pady=(4, 0))
        if values and not variable.get():
            combo.set(values[0])

    def _generate_document_no(self) -> str:
        return "FM-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    def clear_line_inputs(self) -> None:
        self.line_text_var.set("")
        self.line_debit_var.set("")
        self.line_credit_var.set("")
        choices = list(self.account_display_map.keys())
        if choices:
            self.line_account_var.set(choices[0])

    def add_line_item(self) -> None:
        if not self.account_display_map:
            messagebox.showwarning(APP_NAME, "Bitte zuerst mindestens ein Sachkonto im Modul Stammdaten anlegen.")
            return
        account_display = self.line_account_var.get().strip()
        line_text = self.line_text_var.get().strip()
        debit = parse_amount(self.line_debit_var.get())
        credit = parse_amount(self.line_credit_var.get())
        if account_display not in self.account_display_map:
            messagebox.showwarning(APP_NAME, "Bitte ein gültiges Konto auswählen.")
            return
        if debit > 0 and credit > 0:
            messagebox.showwarning(APP_NAME, "Eine Buchungszeile darf nur Soll oder Haben enthalten, nicht beides.")
            return
        if debit <= 0 and credit <= 0:
            messagebox.showwarning(APP_NAME, "Bitte einen Wert im Soll oder Haben eingeben.")
            return
        account_data = self.account_display_map[account_display]
        line = {
            "line_no": len(self.line_items) + 1,
            "account_no": account_data["account_no"],
            "account_name": account_data["name"],
            "line_text": line_text,
            "debit": debit,
            "credit": credit,
        }
        self.line_items.append(line)
        self._refresh_lines_tree()
        self._update_totals()
        self.clear_line_inputs()
        self.status_callback("Buchungszeile hinzugefügt")

    def _refresh_lines_tree(self) -> None:
        for item in self.lines_tree.get_children():
            self.lines_tree.delete(item)
        for idx, line in enumerate(self.line_items, start=1):
            line["line_no"] = idx
            self.lines_tree.insert("", "end", values=(idx, line["account_no"], line["account_name"], line["line_text"], format_amount(line["debit"]), format_amount(line["credit"])))

    def _update_totals(self) -> None:
        total_debit = round(sum(item["debit"] for item in self.line_items), 2)
        total_credit = round(sum(item["credit"] for item in self.line_items), 2)
        diff = round(total_debit - total_credit, 2)
        self.total_label.config(
            text=f"Soll: {format_amount(total_debit)} | Haben: {format_amount(total_credit)} | Differenz: {format_amount(diff)}",
            fg=SUCCESS if abs(diff) < 0.0001 and total_debit > 0 else RED,
        )

    def remove_selected_line(self) -> None:
        selected = self.lines_tree.selection()
        if not selected:
            messagebox.showinfo(APP_NAME, "Bitte zuerst eine Zeile markieren.")
            return
        values = self.lines_tree.item(selected[0], "values")
        line_no = int(values[0])
        self.line_items = [line for line in self.line_items if line["line_no"] != line_no]
        self._refresh_lines_tree()
        self._update_totals()
        self.status_callback("Buchungszeile gelöscht")

    def clear_journal_form(self) -> None:
        self.document_no_var.set(self._generate_document_no())
        self.booking_date_var.set(datetime.now().strftime(DATE_FMT))
        self.posting_text_var.set("")
        self.line_items.clear()
        self._refresh_lines_tree()
        self._update_totals()
        self.clear_line_inputs()
        self.status_callback("Journalmaske geleert")

    def save_journal_entry(self) -> None:
        try:
            document_no = self.document_no_var.get().strip() or self._generate_document_no()
            booking_date = validate_date(self.booking_date_var.get())
            posting_text = self.posting_text_var.get().strip()
            if not posting_text:
                raise ValueError("Bitte einen Buchungstext erfassen.")
            if len(self.line_items) < 2:
                raise ValueError("Für eine Buchung werden mindestens 2 Buchungszeilen benötigt.")
            total_debit = round(sum(item["debit"] for item in self.line_items), 2)
            total_credit = round(sum(item["credit"] for item in self.line_items), 2)
            if total_debit <= 0 or total_credit <= 0:
                raise ValueError("Soll- und Habensumme müssen größer 0 sein.")
            if round(total_debit - total_credit, 2) != 0:
                raise ValueError("Soll und Haben sind nicht ausgeglichen.")

            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO journal_entries (document_no, booking_date, posting_text, total_debit, total_credit, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (document_no, booking_date, posting_text, total_debit, total_credit, datetime.now().strftime("%d.%m.%Y %H:%M:%S")),
                )
                journal_entry_id = cur.lastrowid
                for idx, item in enumerate(self.line_items, start=1):
                    cur.execute(
                        "INSERT INTO journal_entry_lines (journal_entry_id, line_no, account_no, account_name, debit, credit, line_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (journal_entry_id, idx, item["account_no"], item["account_name"], item["debit"], item["credit"], item["line_text"]),
                    )
                conn.commit()
            finally:
                conn.close()
            self.reload_journal_entries()
            self.clear_journal_form()
            self.status_callback(f"Journalbuchung gespeichert: {document_no}")
            messagebox.showinfo(APP_NAME, f"Die Buchung {document_no} wurde erfolgreich gespeichert.")
        except sqlite3.IntegrityError:
            messagebox.showerror(APP_NAME, "Die Belegnummer existiert bereits. Bitte eine neue Belegnummer verwenden.")
        except ValueError as exc:
            messagebox.showwarning(APP_NAME, str(exc))
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Buchung konnte nicht gespeichert werden:\n{exc}")

    def reload_journal_entries(self) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT je.document_no, je.booking_date, je.posting_text, je.total_debit, COUNT(jel.id) AS line_count FROM journal_entries je LEFT JOIN journal_entry_lines jel ON je.id = jel.journal_entry_id GROUP BY je.id, je.document_no, je.booking_date, je.posting_text, je.total_debit ORDER BY je.id DESC LIMIT 50"
            ).fetchall()
        finally:
            conn.close()
        for row in rows:
            self.history_tree.insert("", "end", values=(row["document_no"], row["booking_date"], row["posting_text"], format_amount(row["total_debit"]), row["line_count"]))


class DebitorsView(tk.Frame):
    def __init__(self, parent: tk.Widget, status_callback: Callable[[str], None]):
        super().__init__(parent, bg=BG)
        self.status_callback = status_callback
        self.customer_choices: List[str] = []
        self.customer_display_map: Dict[str, Dict[str, str]] = {}
        self.payment_term_choices: List[str] = []
        self.payment_term_map: Dict[str, Dict[str, object]] = {}
        self.tax_code_choices: List[str] = []
        self.tax_code_map: Dict[str, Dict[str, object]] = {}
        self._load_reference_data()
        self._build_ui()
        self.reload_invoices()
        self.reload_open_items()

    def _load_reference_data(self) -> None:
        conn = get_connection()
        try:
            customer_rows = conn.execute("SELECT * FROM customers WHERE active = 1 ORDER BY customer_no").fetchall()
            self.customer_display_map = {
                f"{row['customer_no']} | {row['name']} | {format_partner_address(row)}": {
                    "customer_no": row['customer_no'],
                    "name": row['name'],
                    "address": format_partner_address(row),
                    "iban": row['iban'],
                    "vat_id": row['vat_id'],
                    "tax_no": row['tax_no'],
                }
                for row in customer_rows
            }
            self.customer_choices = list(self.customer_display_map.keys())

            pt_rows = conn.execute("SELECT code, description, due_days FROM payment_terms ORDER BY code").fetchall()
            self.payment_term_map = {f"{row['code']} | {row['description']} ({row['due_days']} Tage)": {"code": row['code'], "description": row['description'], "due_days": row['due_days']} for row in pt_rows}
            self.payment_term_choices = list(self.payment_term_map.keys())

            tax_rows = conn.execute("SELECT code, description, rate, tax_scope FROM tax_codes ORDER BY code").fetchall()
            self.tax_code_map = {f"{row['code']} | {row['description']} ({format_amount(row['rate'])} %)": {"code": row['code'], "description": row['description'], "rate": row['rate'], "tax_scope": row['tax_scope']} for row in tax_rows}
            self.tax_code_choices = list(self.tax_code_map.keys())
        finally:
            conn.close()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        ttk.Label(self, text="Debitoren", style="Section.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(
            self,
            text="Block 5: Ausgangsrechnungen, offene Posten und Fälligkeitslogik für Debitoren. Fine-Tuning wie Bearbeiten/Umbenennen ist projektweit eingeplant und wird nach den Kernprozessen umgesetzt.",
            style="Hint.TLabel",
            wraplength=1050,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        shell = tk.Frame(self, bg=BG)
        shell.grid(row=2, column=0, sticky="nsew")
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(0, weight=6)
        shell.grid_columnconfigure(1, weight=5)

        left_outer = tk.Frame(shell, bg=CARD_BORDER)
        left_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left = tk.Frame(left_outer, bg=WHITE)
        left.pack(fill="both", expand=True, padx=1, pady=1)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(3, weight=1)
        left.grid_rowconfigure(5, weight=1)

        right_outer = tk.Frame(shell, bg=CARD_BORDER)
        right_outer.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right = tk.Frame(right_outer, bg=WHITE)
        right.pack(fill="both", expand=True, padx=1, pady=1)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        form = tk.Frame(left, bg=WHITE)
        form.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        for idx in range(4):
            form.grid_columnconfigure(idx, weight=1)

        self.invoice_no_var = tk.StringVar(value=self._generate_invoice_no())
        self.invoice_date_var = tk.StringVar(value=datetime.now().strftime(DATE_FMT))
        self.posting_text_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.due_date_var = tk.StringVar(value=datetime.now().strftime(DATE_FMT))
        self.customer_var = tk.StringVar(value=self.customer_choices[0] if self.customer_choices else "")
        self.payment_term_var = tk.StringVar(value=self.payment_term_choices[0] if self.payment_term_choices else "")
        self.tax_code_var = tk.StringVar(value=self.tax_code_choices[0] if self.tax_code_choices else "")

        self._labeled_entry(form, 0, 0, "Rechnungsnummer", self.invoice_no_var)
        self._labeled_entry(form, 0, 1, "Rechnungsdatum", self.invoice_date_var)
        self._labeled_entry(form, 0, 2, "Fälligkeitsdatum", self.due_date_var)
        self._labeled_combo(form, 0, 3, "Debitor", self.customer_var, self.customer_choices, width=42)
        self._labeled_combo(form, 1, 0, "Zahlungsbedingung", self.payment_term_var, self.payment_term_choices, width=42)
        self._labeled_combo(form, 1, 1, "Steuerkennzeichen", self.tax_code_var, self.tax_code_choices, width=42)
        self._labeled_entry(form, 1, 2, "Betrag", self.amount_var)
        self._labeled_entry(form, 1, 3, "Buchungstext", self.posting_text_var)

        action_row = tk.Frame(left, bg=WHITE)
        action_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        ttk.Button(action_row, text="Fälligkeit aus Zahlungsbedingung", command=self.apply_payment_term).pack(side="left")
        ttk.Button(action_row, text="Rechnung speichern", command=self.save_invoice).pack(side="left", padx=(8, 0))
        ttk.Button(action_row, text="Felder leeren", command=self.clear_form).pack(side="left", padx=(8, 0))

        tk.Label(left, text="Ausgangsrechnungen", bg=WHITE, fg=TEXT, font=("Segoe UI", 12, "bold")).grid(row=2, column=0, sticky="w", padx=16, pady=(0, 8))
        inv_outer = tk.Frame(left, bg=CARD_BORDER)
        inv_outer.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 12))
        inv_inner = tk.Frame(inv_outer, bg=WHITE)
        inv_inner.pack(fill="both", expand=True, padx=1, pady=1)
        inv_inner.grid_rowconfigure(0, weight=1)
        inv_inner.grid_columnconfigure(0, weight=1)
        self.invoice_tree = ttk.Treeview(inv_inner, columns=("invoice_no", "customer_name", "invoice_date", "due_date", "amount", "status"), show="headings", height=10)
        self.invoice_tree.grid(row=0, column=0, sticky="nsew")
        inv_scroll = ttk.Scrollbar(inv_inner, orient="vertical", command=self.invoice_tree.yview)
        inv_scroll.grid(row=0, column=1, sticky="ns")
        self.invoice_tree.configure(yscrollcommand=inv_scroll.set)
        for key, title, width in [
            ("invoice_no", "Rechnung", 120), ("customer_name", "Debitor", 220), ("invoice_date", "Datum", 85),
            ("due_date", "Fälligkeit", 85), ("amount", "Betrag", 90), ("status", "Status", 90),
        ]:
            self.invoice_tree.heading(key, text=title)
            self.invoice_tree.column(key, width=width, anchor="w")

        tk.Label(left, text="Offene Posten Debitoren", bg=WHITE, fg=TEXT, font=("Segoe UI", 12, "bold")).grid(row=4, column=0, sticky="w", padx=16, pady=(0, 8))
        op_outer = tk.Frame(left, bg=CARD_BORDER)
        op_outer.grid(row=5, column=0, sticky="nsew", padx=16, pady=(0, 16))
        op_inner = tk.Frame(op_outer, bg=WHITE)
        op_inner.pack(fill="both", expand=True, padx=1, pady=1)
        op_inner.grid_rowconfigure(0, weight=1)
        op_inner.grid_columnconfigure(0, weight=1)
        self.open_item_tree = ttk.Treeview(op_inner, columns=("reference_no", "partner_name", "invoice_date", "due_date", "amount", "open_amount", "status"), show="headings", height=10)
        self.open_item_tree.grid(row=0, column=0, sticky="nsew")
        op_scroll = ttk.Scrollbar(op_inner, orient="vertical", command=self.open_item_tree.yview)
        op_scroll.grid(row=0, column=1, sticky="ns")
        self.open_item_tree.configure(yscrollcommand=op_scroll.set)
        for key, title, width in [
            ("reference_no", "Referenz", 120), ("partner_name", "Debitor", 200), ("invoice_date", "Datum", 85),
            ("due_date", "Fälligkeit", 85), ("amount", "Betrag", 90), ("open_amount", "Offen", 90), ("status", "Status", 90),
        ]:
            self.open_item_tree.heading(key, text=title)
            self.open_item_tree.column(key, width=width, anchor="w")

        tk.Label(right, text="Hinweise Block 5", bg=WHITE, fg=TEXT, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))
        tk.Label(
            right,
            text="Debitorenstammdaten enthalten jetzt vollständige Adress- und Steuerfelder. Die buchhalterische Verknüpfung zwischen Rechnung und Journal wird im späteren Integrations-/Fine-Tuning-Schritt vertieft. Der Reiter Bankkonten ist im UI obsolet, weil Kontoverbindungen direkt am Debitor/Kreditor gepflegt werden.",
            bg=WHITE,
            fg=TEXT2,
            font=("Segoe UI", 9),
            wraplength=360,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        help_outer = tk.Frame(right, bg=CARD_BORDER)
        help_outer.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        help_inner = tk.Frame(help_outer, bg=WHITE)
        help_inner.pack(fill="both", expand=True, padx=1, pady=1)
        help_inner.grid_columnconfigure(0, weight=1)
        infos = [
            'Debitor muss in den Stammdaten als aktiver Datensatz vorhanden sein.',
            'Rechnungsdatum und Fälligkeit muessen TT.MM.JJJJ sein.',
            'Betrag wird als offener Posten angelegt.',
            'Status startet bei Offen.',
            'Fine-Tuning wie Bearbeiten, Storno, Nachbuchung und Textaenderungen wird projektweit spaeter vorgesehen.'
        ]
        for idx, item in enumerate(infos):
            row = tk.Frame(help_inner, bg=WHITE)
            row.grid(row=idx, column=0, sticky="ew", padx=14, pady=(12 if idx == 0 else 6, 0))
            tk.Label(row, text='•', bg=WHITE, fg=BLUE, font=("Segoe UI", 11, "bold")).pack(side='left')
            tk.Label(row, text=item, bg=WHITE, fg=TEXT, font=("Segoe UI", 9), wraplength=330, justify='left').pack(side='left', padx=(8, 0))

    def _generate_invoice_no(self) -> str:
        return 'AR-' + datetime.now().strftime('%Y%m%d-%H%M%S')

    def _labeled_entry(self, parent: tk.Widget, row: int, column: int, label: str, variable: tk.StringVar) -> None:
        box = tk.Frame(parent, bg=WHITE)
        box.grid(row=row, column=column, sticky='ew', padx=12, pady=4)
        tk.Label(box, text=label, bg=WHITE, fg=TEXT, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        ttk.Entry(box, textvariable=variable).pack(fill='x', pady=(4, 0))

    def _labeled_combo(self, parent: tk.Widget, row: int, column: int, label: str, variable: tk.StringVar, choices: List[str], width: int = 24) -> None:
        box = tk.Frame(parent, bg=WHITE)
        box.grid(row=row, column=column, sticky='ew', padx=12, pady=4)
        tk.Label(box, text=label, bg=WHITE, fg=TEXT, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        combo = ttk.Combobox(box, textvariable=variable, values=choices, state='readonly', width=width)
        combo.pack(fill='x', pady=(4, 0))
        if choices and not variable.get():
            combo.set(choices[0])

    def apply_payment_term(self) -> None:
        choice = self.payment_term_var.get().strip()
        if choice and choice in self.payment_term_map:
            due_days = int(self.payment_term_map[choice]['due_days'])
            try:
                self.due_date_var.set(calc_due_date(self.invoice_date_var.get(), due_days))
                self.status_callback('Fälligkeit aus Zahlungsbedingung übernommen')
            except ValueError as exc:
                messagebox.showwarning(APP_NAME, str(exc))

    def clear_form(self) -> None:
        self.invoice_no_var.set(self._generate_invoice_no())
        self.invoice_date_var.set(datetime.now().strftime(DATE_FMT))
        self.posting_text_var.set('')
        self.amount_var.set('')
        self.due_date_var.set(datetime.now().strftime(DATE_FMT))
        if self.customer_choices:
            self.customer_var.set(self.customer_choices[0])
        if self.payment_term_choices:
            self.payment_term_var.set(self.payment_term_choices[0])
        if self.tax_code_choices:
            self.tax_code_var.set(self.tax_code_choices[0])
        self.status_callback('Debitorenformular geleert')

    def save_invoice(self) -> None:
        if not self.customer_choices:
            messagebox.showwarning(APP_NAME, 'Bitte zuerst mindestens einen Debitor in den Stammdaten anlegen.')
            return
        try:
            invoice_no = self.invoice_no_var.get().strip() or self._generate_invoice_no()
            customer_choice = self.customer_var.get().strip()
            if customer_choice not in self.customer_display_map:
                raise ValueError('Bitte einen gültigen Debitor auswählen.')
            customer = self.customer_display_map[customer_choice]
            invoice_date = validate_date(self.invoice_date_var.get())
            due_date = validate_date(self.due_date_var.get())
            posting_text = self.posting_text_var.get().strip()
            amount = parse_amount(self.amount_var.get())
            if not posting_text:
                raise ValueError('Bitte einen Buchungstext erfassen.')
            if amount <= 0:
                raise ValueError('Der Rechnungsbetrag muss größer 0 sein.')
            tax_choice = self.tax_code_var.get().strip()
            tax_code = self.tax_code_map[tax_choice]['code'] if tax_choice in self.tax_code_map else None
            pt_choice = self.payment_term_var.get().strip()
            payment_term_code = self.payment_term_map[pt_choice]['code'] if pt_choice in self.payment_term_map else None

            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO customer_invoices (invoice_no, customer_no, customer_name, invoice_date, due_date, posting_text, amount, tax_code, payment_term_code, status, created_at, customer_address) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (invoice_no, customer['customer_no'], customer['name'], invoice_date, due_date, posting_text, amount, tax_code, payment_term_code, 'Offen', datetime.now().strftime('%d.%m.%Y %H:%M:%S'), customer['address']),
                )
                cur.execute(
                    "INSERT INTO open_items (item_type, reference_no, partner_no, partner_name, invoice_date, due_date, amount, open_amount, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    ('Debitor', invoice_no, customer['customer_no'], customer['name'], invoice_date, due_date, amount, amount, 'Offen', datetime.now().strftime('%d.%m.%Y %H:%M:%S')),
                )
                conn.commit()
            finally:
                conn.close()
            self.reload_invoices()
            self.reload_open_items()
            self.clear_form()
            self.status_callback(f'Debitorenrechnung gespeichert: {invoice_no}')
            messagebox.showinfo(APP_NAME, f'Die Debitorenrechnung {invoice_no} wurde gespeichert und als offener Posten angelegt.')
        except sqlite3.IntegrityError:
            messagebox.showerror(APP_NAME, 'Die Rechnungsnummer existiert bereits.')
        except ValueError as exc:
            messagebox.showwarning(APP_NAME, str(exc))
        except Exception as exc:
            messagebox.showerror(APP_NAME, f'Debitorenrechnung konnte nicht gespeichert werden:\n{exc}')

    def reload_invoices(self) -> None:
        for item in self.invoice_tree.get_children():
            self.invoice_tree.delete(item)
        conn = get_connection()
        try:
            rows = conn.execute("SELECT invoice_no, customer_name, invoice_date, due_date, amount, status FROM customer_invoices ORDER BY id DESC LIMIT 100").fetchall()
        finally:
            conn.close()
        for row in rows:
            self.invoice_tree.insert('', 'end', values=(row['invoice_no'], row['customer_name'], row['invoice_date'], row['due_date'], format_amount(row['amount']), row['status']))

    def reload_open_items(self) -> None:
        for item in self.open_item_tree.get_children():
            self.open_item_tree.delete(item)
        conn = get_connection()
        try:
            rows = conn.execute("SELECT reference_no, partner_name, invoice_date, due_date, amount, open_amount, status FROM open_items WHERE item_type='Debitor' ORDER BY id DESC LIMIT 100").fetchall()
        finally:
            conn.close()
        for row in rows:
            self.open_item_tree.insert('', 'end', values=(row['reference_no'], row['partner_name'], row['invoice_date'], row['due_date'], format_amount(row['amount']), format_amount(row['open_amount']), row['status']))


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
        self.nav_order = ['Dashboard', 'Stammdaten', 'Finanzbuchhaltung', 'Debitoren', 'Kreditoren', 'Zahlungen', 'Reporting', 'Audit', 'Einstellungen']
        self.active_module = tk.StringVar(value='Dashboard')

        self._configure_ttk()
        self._build_layout()
        self._build_header()
        self._build_sidebar()
        self._build_workspace()
        self._build_footer()
        self.show_module('Dashboard')

    def _configure_ttk(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure('Nav.TButton', font=('Segoe UI', 10, 'bold'), padding=(12, 10), foreground=TEXT, background=WHITE, borderwidth=1, relief='solid', anchor='w')
        style.map('Nav.TButton', background=[('active', '#F4F7FA'), ('pressed', '#E7EEF5')])
        style.configure('NavActive.TButton', font=('Segoe UI', 10, 'bold'), padding=(12, 10), foreground=BLUE, background='#EAF1F8', borderwidth=1, relief='solid', anchor='w')
        style.map('NavActive.TButton', background=[('active', '#EAF1F8'), ('pressed', '#EAF1F8')])
        style.configure('Card.TFrame', background=WHITE)
        style.configure('CardTitle.TLabel', background=WHITE, foreground=TEXT, font=('Segoe UI', 12, 'bold'))
        style.configure('CardBody.TLabel', background=WHITE, foreground=TEXT2, font=('Segoe UI', 10))
        style.configure('Section.TLabel', background=BG, foreground=TEXT, font=('Segoe UI', 16, 'bold'))
        style.configure('Hint.TLabel', background=BG, foreground=TEXT2, font=('Segoe UI', 10))

    def _build_layout(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _build_header(self) -> None:
        self.header_frame = tk.Frame(self, bg=HEADER, height=HEADER_HEIGHT, highlightthickness=1, highlightbackground=LINE)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)
        title_wrap = tk.Frame(self.header_frame, bg=HEADER)
        title_wrap.grid(row=0, column=0, sticky='w', padx=18)
        tk.Label(title_wrap, text=APP_NAME, bg=HEADER, fg=BLUE, font=('Segoe UI', 24, 'bold')).pack(anchor='w')
        tk.Label(title_wrap, text='Startarchitektur v0.1 – Desktop, Fullscreen, Debitoren-Block erweitert', bg=HEADER, fg=TEXT2, font=('Segoe UI', 10)).pack(anchor='w')
        widget_bar = tk.Frame(self.header_frame, bg=HEADER)
        widget_bar.grid(row=0, column=1, sticky='e', padx=(10, 18))
        self._mini_widget(widget_bar, 'Änderung vorschlagen').pack(side='left', padx=(0, 8), pady=18)
        self._mini_widget(widget_bar, '[i] Hilfe').pack(side='left', pady=18)

    def _mini_widget(self, parent: tk.Widget, text: str) -> tk.Label:
        return tk.Label(parent, text=text, bg=WHITE, fg=TEXT, font=('Segoe UI', 9, 'bold'), padx=10, pady=5, relief='solid', bd=1, highlightthickness=0)

    def _build_sidebar(self) -> None:
        self.sidebar_frame = tk.Frame(self, bg=BG, width=SIDEBAR_WIDTH, highlightthickness=1, highlightbackground=LINE)
        self.sidebar_frame.grid(row=1, column=0, sticky='nsew')
        self.sidebar_frame.grid_propagate(False)
        tk.Label(self.sidebar_frame, text='Module', bg=BG, fg=TEXT, font=('Segoe UI', 14, 'bold')).pack(anchor='w', padx=18, pady=(18, 10))
        tk.Label(self.sidebar_frame, text='Finance-Mate-Startnavigation', bg=BG, fg=TEXT2, font=('Segoe UI', 9)).pack(anchor='w', padx=18, pady=(0, 12))
        for module_name in self.nav_order:
            btn = ttk.Button(self.sidebar_frame, text=module_name, style='Nav.TButton', command=lambda value=module_name: self.show_module(value))
            btn.pack(fill='x', padx=14, pady=4)
            self.nav_buttons[module_name] = btn

    def _build_workspace(self) -> None:
        self.workspace_frame = tk.Frame(self, bg=BG)
        self.workspace_frame.grid(row=1, column=1, sticky='nsew')
        self.workspace_frame.grid_rowconfigure(1, weight=1)
        self.workspace_frame.grid_columnconfigure(0, weight=1)
        self.path_bar = tk.Frame(self.workspace_frame, bg=BG)
        self.path_bar.grid(row=0, column=0, sticky='ew', padx=18, pady=(14, 6))
        self.path_label = tk.Label(self.path_bar, text='Finance Mate  >  Dashboard', bg=BG, fg=TEXT2, font=('Segoe UI', 9))
        self.path_label.pack(anchor='w')
        self.content_frame = tk.Frame(self.workspace_frame, bg=BG)
        self.content_frame.grid(row=1, column=0, sticky='nsew', padx=18, pady=(6, 12))
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

    def _build_footer(self) -> None:
        self.footer_frame = tk.Frame(self, bg=HEADER, height=FOOTER_HEIGHT, highlightthickness=1, highlightbackground=LINE)
        self.footer_frame.grid(row=2, column=0, columnspan=2, sticky='nsew')
        self.footer_frame.grid_propagate(False)
        self.status_label = tk.Label(self.footer_frame, text=f'{APP_NAME} {APP_VERSION}  |  Datenbank: SQLite  |  Fullscreen aktiv', bg=HEADER, fg=TEXT2, font=('Segoe UI', 8))
        self.status_label.pack(side='left', padx=14)

    def set_status(self, text: str) -> None:
        self.status_label.config(text=f'{APP_NAME} {APP_VERSION}  |  {text}')

    def show_module(self, module_name: str) -> None:
        self.active_module.set(module_name)
        self.path_label.config(text=f'Finance Mate  >  {module_name}')
        self.set_status(f'Modul: {module_name}  |  Datenbank: SQLite')
        for name, button in self.nav_buttons.items():
            button.configure(style='NavActive.TButton' if name == module_name else 'Nav.TButton')
        for child in self.content_frame.winfo_children():
            child.destroy()
        render_map = {
            'Dashboard': self._render_dashboard,
            'Stammdaten': self._render_stammdaten,
            'Finanzbuchhaltung': self._render_finanzbuchhaltung,
            'Debitoren': self._render_debitoren,
            'Kreditoren': self._render_kreditoren,
            'Zahlungen': self._render_zahlungen,
            'Reporting': self._render_reporting,
            'Audit': self._render_audit,
            'Einstellungen': self._render_einstellungen,
        }
        render_map.get(module_name, self._render_dashboard)()

    def _render_dashboard(self) -> None:
        wrapper = self._create_two_by_two_grid()
        self._card(wrapper, 0, 0, 'Systemstart', 'Finance Mate startet maximiert und initialisiert SQLite automatisch.')
        self._card(wrapper, 0, 1, 'Block 5 erweitert', 'Debitorenrechnungen, offene Posten und erweiterte Stammdatenpflege mit Bearbeitungsmodus sind umgesetzt.')
        self._card(wrapper, 1, 0, 'Fine-Tuning eingeplant', 'Ja: Bearbeiten/Umbenennen, Feldoptimierungen, Validierungs-Finishing, Such-/Filter-Finetuning und UI-Konsistenz werden projektweit als eigene Optimierungsphase mitgeführt.')
        self._card(wrapper, 1, 1, 'Nächste Coding-Blöcke', '1) Kreditorenlogik\n2) Zahlungen\n3) Reporting\n4) Audit/Fine-Tuning-Phase')

    def _render_stammdaten(self) -> None:
        view = StammdatenView(self.content_frame, self.set_status)
        view.grid(row=0, column=0, sticky='nsew')

    def _render_finanzbuchhaltung(self) -> None:
        view = JournalView(self.content_frame, self.set_status)
        view.grid(row=0, column=0, sticky='nsew')

    def _render_debitoren(self) -> None:
        view = DebitorsView(self.content_frame, self.set_status)
        view.grid(row=0, column=0, sticky='nsew')

    def _render_kreditoren(self) -> None:
        frame = self._create_single_area('Kreditoren', 'Naechster Block: Eingangsrechnungen, offene Posten, Faelligkeiten und spaeterer Ausgleich. Der gleiche erweiterte Stammdatenansatz wie bei Debitoren ist bereits vorbereitet.')
        self._list_block(frame, ['Eingangsrechnungen', 'Offene Posten', 'Faelligkeitsuebersicht', 'Zahlungsausgang', 'Ausgleich'])

    def _render_zahlungen(self) -> None:
        frame = self._create_single_area('Zahlungen', 'Fuer v0.1 zunaechst schlank: manuelle Zahlungsbuchung, OP-Zuordnung und spaeter Kontenabstimmung.')
        self._list_block(frame, ['Bankkonten', 'Manuelle Zahlungen', 'OP-Zuordnung', 'Kontenabstimmung', 'spaeter: Bankimport / PostgreSQL-Betrieb'])

    def _render_reporting(self) -> None:
        frame = self._create_single_area('Reporting', 'Die ersten Standardberichte bauen spaeter auf Journal, Debitoren und Kreditoren auf.')
        self._list_block(frame, ['Saldenliste', 'Kontoblatt', 'OP-Liste Debitoren', 'OP-Liste Kreditoren', 'Faelligkeitsreport', 'Buchungsjournal'])

    def _render_audit(self) -> None:
        frame = self._create_single_area('Audit', 'Von Anfang an vorgesehen: Nachvollziehbarkeit von Aenderungen, Statuswechseln und spaeteren Freigaben.')
        self._list_block(frame, ['Aenderungsprotokoll', 'Benutzerhistorie', 'Statuswechsel', 'Freigabeverlauf (spaeter)', 'projektweites Fine-Tuning'])

    def _render_einstellungen(self) -> None:
        frame = self._create_single_area('Einstellungen', 'Grundkonfiguration fuer Finance Mate – Start mit SQLite, spaeter vorbereitet fuer PostgreSQL.')
        self._list_block(frame, ['Mandant/Firma (Single-Company Start)', 'Systemparameter', 'Nummernkreise', 'Datenbankmodus: SQLite', 'spaeter: PostgreSQL-Umschaltung'])

    def _create_two_by_two_grid(self) -> tk.Frame:
        wrapper = tk.Frame(self.content_frame, bg=BG)
        wrapper.grid(row=0, column=0, sticky='nsew')
        for idx in range(2):
            wrapper.grid_columnconfigure(idx, weight=1, uniform='cards')
            wrapper.grid_rowconfigure(idx, weight=1, uniform='cards')
        return wrapper

    def _create_single_area(self, title: str, text: str) -> tk.Frame:
        wrapper = tk.Frame(self.content_frame, bg=BG)
        wrapper.grid(row=0, column=0, sticky='nsew')
        wrapper.grid_columnconfigure(0, weight=1)
        ttk.Label(wrapper, text=title, style='Section.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 8))
        ttk.Label(wrapper, text=text, style='Hint.TLabel', wraplength=900, justify='left').grid(row=1, column=0, sticky='w', pady=(0, 12))
        return wrapper

    def _list_block(self, parent: tk.Frame, items: list[str]) -> None:
        outer = tk.Frame(parent, bg=CARD_BORDER)
        outer.grid(row=2, column=0, sticky='nsew')
        body = tk.Frame(outer, bg=WHITE)
        body.pack(fill='both', expand=True, padx=1, pady=1)
        for idx, item in enumerate(items):
            row = tk.Frame(body, bg=WHITE)
            row.pack(fill='x', padx=16, pady=(12 if idx == 0 else 6, 0))
            tk.Label(row, text='•', bg=WHITE, fg=BLUE, font=('Segoe UI', 11, 'bold')).pack(side='left')
            tk.Label(row, text=item, bg=WHITE, fg=TEXT, font=('Segoe UI', 10)).pack(side='left', padx=(8, 0))

    def _card(self, parent: tk.Widget, row: int, column: int, title: str, body: str) -> None:
        outer = tk.Frame(parent, bg=CARD_BORDER, bd=0, highlightthickness=0)
        outer.grid(row=row, column=column, sticky='nsew', padx=8, pady=8)
        inner = ttk.Frame(outer, style='Card.TFrame', padding=16)
        inner.pack(fill='both', expand=True, padx=1, pady=1)
        ttk.Label(inner, text=title, style='CardTitle.TLabel').pack(anchor='w')
        ttk.Label(inner, text=body, style='CardBody.TLabel', wraplength=420, justify='left').pack(anchor='w', pady=(8, 0))


def main() -> None:
    ensure_directories()
    init_sqlite()
    app = FinanceMateApp()
    app.mainloop()


if __name__ == '__main__':
    main()

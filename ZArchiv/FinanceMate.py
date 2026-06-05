
# -*- coding: utf-8 -*-
"""
Finance Mate – rekonstruierte lokale Desktop-App
Stand: v0.6.16-rekonstruiert

Rekonstruktionsbasis: Projektprotokoll FinanceMate – Rekonstruktionsmaster V4 / Patch-für-Patch-Systemreferenz.
Technik: Python, tkinter/ttk, SQLite, lokale Dateipersistenz.

Hinweis: Diese Datei ist als konsolidierte, startfähige Rekonstruktion aufgebaut. Sie bildet die im
Projektprotokoll beschriebene Fachsemantik in einer bereinigten Ein-Datei-Struktur ab.
"""

from __future__ import annotations

import os
import sys
import shutil
import sqlite3
import mimetypes
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

APP_NAME = "Finance Mate"
APP_VERSION = "0.6.16-rekonstruiert"
STANDARD_DESIGN_NAME = "Reliefgrau"
DATE_FMT = "%d.%m.%Y"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ATTACHMENTS_DIR = BASE_DIR / "attachments"
IMPORTS_DIR = BASE_DIR / "imports"
DB_PATH = DATA_DIR / "finance_mate.sqlite3"

# Farben / Design
BG = "#eef1f4"
HEADER = "#dde3ea"
FOOTER = "#d8dee6"
LINE = "#b8c0ca"
TEXT = "#1f2933"
TEXT2 = "#5d6672"
WHITE = "#ffffff"
CARD_BG = "#f9fafb"
CARD_BORDER = "#cbd3dc"
BUTTON_GREEN = "#cfead1"
BUTTON_GREEN_ACTIVE = "#b9dfbd"
STANDARD_BUTTON_BG = "#d9dde3"
STANDARD_BUTTON_ACTIVE = "#cbd1d8"
STANDARD_BUTTON_BORDER = "#aeb7c2"
PLACEHOLDER_TEXT = "Suchen…"
PLACEHOLDER_COLOR = "#8a929c"
SOFT_GREEN = "#dff3e2"
SOFT_YELLOW = "#fff4c2"
SOFT_ORANGE = "#ffe1bf"
SOFT_RED = "#ffd4d4"

STATUS_OPEN = "Offen"
STATUS_PARTIAL = "Teilweise bezahlt"
STATUS_PAID = "Bezahlt"
STATUS_OVERDUE = "Überfällig"
STATUS_STORNO = "Storno"
PAYMENT_STATUS_VALUES = [STATUS_OPEN, STATUS_PARTIAL, STATUS_PAID, STATUS_OVERDUE, STATUS_STORNO]
TAX_SCOPE_VALUES = ["Inland", "EU", "Drittland"]
TRADE_COUNTRIES = ["Deutschland", "Österreich", "Schweiz", "Frankreich", "Italien", "Spanien", "Niederlande", "Belgien", "Polen", "Sonstige"]
SUPPORTED_ARCHIVE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".txt", ".csv", ".doc", ".docx", ".xls", ".xlsx"}


def ensure_directories() -> None:
    for p in (DATA_DIR, ATTACHMENTS_DIR, IMPORTS_DIR):
        p.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_directories()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def table_has_column(con: sqlite3.Connection, table: str, column: str) -> bool:
    rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def ensure_column(con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not table_has_column(con, table, column):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_sqlite() -> None:
    ensure_directories()
    with get_connection() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS gl_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                account_type TEXT DEFAULT '',
                tax_code TEXT DEFAULT '',
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                country TEXT DEFAULT 'Deutschland',
                street TEXT DEFAULT '', zip TEXT DEFAULT '', city TEXT DEFAULT '',
                email TEXT DEFAULT '', phone TEXT DEFAULT '', tax_id TEXT DEFAULT '', vat_id TEXT DEFAULT '',
                iban TEXT DEFAULT '', bic TEXT DEFAULT '', bank_name TEXT DEFAULT '',
                payment_term TEXT DEFAULT '', active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vendors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                country TEXT DEFAULT 'Deutschland',
                street TEXT DEFAULT '', zip TEXT DEFAULT '', city TEXT DEFAULT '',
                email TEXT DEFAULT '', phone TEXT DEFAULT '', tax_id TEXT DEFAULT '', vat_id TEXT DEFAULT '',
                iban TEXT DEFAULT '', bic TEXT DEFAULT '', bank_name TEXT DEFAULT '',
                payment_term TEXT DEFAULT '', active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tax_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                rate REAL DEFAULT 0,
                tax_scope TEXT DEFAULT 'Inland',
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS payment_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                days INTEGER DEFAULT 0,
                discount_days INTEGER DEFAULT 0,
                discount_percent REAL DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                iban TEXT DEFAULT '', bic TEXT DEFAULT '', bank_name TEXT DEFAULT '',
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_no TEXT UNIQUE NOT NULL,
                document_date TEXT NOT NULL,
                posting_date TEXT NOT NULL,
                description TEXT DEFAULT '',
                total_debit REAL DEFAULT 0,
                total_credit REAL DEFAULT 0,
                status TEXT DEFAULT 'Gebucht',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS journal_entry_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_no TEXT NOT NULL,
                account_no TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                tax_code TEXT DEFAULT '',
                text TEXT DEFAULT '',
                FOREIGN KEY(document_no) REFERENCES journal_entries(document_no) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS customer_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                customer_no TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                customer_address TEXT DEFAULT '',
                invoice_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                payment_term TEXT DEFAULT '',
                tax_code TEXT DEFAULT '',
                net_amount REAL DEFAULT 0,
                tax_amount REAL DEFAULT 0,
                gross_amount REAL DEFAULT 0,
                open_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'Offen',
                linked_journal_no TEXT DEFAULT '',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vendor_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                vendor_no TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                vendor_address TEXT DEFAULT '',
                invoice_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                payment_term TEXT DEFAULT '',
                tax_code TEXT DEFAULT '',
                net_amount REAL DEFAULT 0,
                tax_amount REAL DEFAULT 0,
                gross_amount REAL DEFAULT 0,
                open_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'Offen',
                linked_journal_no TEXT DEFAULT '',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS open_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                reference_no TEXT NOT NULL,
                partner_no TEXT NOT NULL,
                partner_name TEXT NOT NULL,
                due_date TEXT NOT NULL,
                original_amount REAL NOT NULL,
                open_amount REAL NOT NULL,
                status TEXT NOT NULL,
                linked_journal_no TEXT DEFAULT '',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                reference_no TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                added_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS invoice_import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hist_no TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                vendor_no TEXT DEFAULT '',
                vendor_name TEXT DEFAULT '',
                status TEXT DEFAULT 'Importiert',
                marked INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS invoice_import_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hist_no TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                mime_type TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(hist_no) REFERENCES invoice_import_batches(hist_no) ON DELETE CASCADE
            );
            """
        )
        # defensive schema compatibility
        for table, col, definition in [
            ("customer_invoices", "customer_address", "TEXT DEFAULT ''"),
            ("customer_invoices", "linked_journal_no", "TEXT DEFAULT ''"),
            ("vendor_invoices", "vendor_address", "TEXT DEFAULT ''"),
            ("vendor_invoices", "linked_journal_no", "TEXT DEFAULT ''"),
            ("open_items", "linked_journal_no", "TEXT DEFAULT ''"),
            ("tax_codes", "tax_scope", "TEXT DEFAULT 'Inland'"),
        ]:
            ensure_column(con, table, col, definition)
        now = now_str()
        con.execute("INSERT OR REPLACE INTO app_meta(key,value,updated_at) VALUES(?,?,?)", ("app_version", APP_VERSION, now))
        seed_defaults(con)
        con.commit()


def seed_defaults(con: sqlite3.Connection) -> None:
    now = now_str()
    defaults = [
        ("gl_accounts", "account_no", "1000", {"name": "Kasse", "account_type": "Aktiv"}),
        ("gl_accounts", "account_no", "1200", {"name": "Bank", "account_type": "Aktiv"}),
        ("gl_accounts", "account_no", "1400", {"name": "Forderungen", "account_type": "Aktiv"}),
        ("gl_accounts", "account_no", "1600", {"name": "Verbindlichkeiten", "account_type": "Passiv"}),
        ("gl_accounts", "account_no", "8400", {"name": "Erlöse", "account_type": "Ertrag"}),
        ("gl_accounts", "account_no", "3400", {"name": "Wareneingang", "account_type": "Aufwand"}),
    ]
    for table, keycol, keyval, vals in defaults:
        exists = con.execute(f"SELECT 1 FROM {table} WHERE {keycol}=?", (keyval,)).fetchone()
        if not exists:
            cols = [keycol] + list(vals.keys()) + ["created_at", "updated_at"]
            params = [keyval] + list(vals.values()) + [now, now]
            con.execute(f"INSERT INTO {table}({','.join(cols)}) VALUES({','.join(['?']*len(cols))})", params)
    for code, name, rate in [("V19", "Vorsteuer/Umsatzsteuer 19%", 19), ("V7", "Vorsteuer/Umsatzsteuer 7%", 7), ("O0", "Ohne Steuer", 0)]:
        if not con.execute("SELECT 1 FROM tax_codes WHERE code=?", (code,)).fetchone():
            con.execute("INSERT INTO tax_codes(code,name,rate,tax_scope,created_at,updated_at) VALUES(?,?,?,?,?,?)", (code, name, rate, "Inland", now, now))
    for code, name, days in [("SOFORT", "Sofort fällig", 0), ("14T", "14 Tage netto", 14), ("30T", "30 Tage netto", 30)]:
        if not con.execute("SELECT 1 FROM payment_terms WHERE code=?", (code,)).fetchone():
            con.execute("INSERT INTO payment_terms(code,name,days,created_at,updated_at) VALUES(?,?,?,?,?)", (code, name, days, now, now))


def now_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime(DATE_FMT)


def validate_date(value: str) -> bool:
    try:
        datetime.strptime(value.strip(), DATE_FMT)
        return True
    except Exception:
        return False


def parse_amount(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    s = str(value).strip().replace("€", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"Ungültiger Betrag: {value}")


def format_amount(value: Any) -> str:
    try:
        d = Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        d = Decimal("0.00")
    return f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calc_due_date(date_str: str, payment_term_code: str) -> str:
    base = datetime.strptime(date_str, DATE_FMT)
    days = 0
    with get_connection() as con:
        row = con.execute("SELECT days FROM payment_terms WHERE code=?", (payment_term_code,)).fetchone()
        if row:
            days = int(row[0] or 0)
    return (base + timedelta(days=days)).strftime(DATE_FMT)


def compute_status_from_open_amount(open_amount: Any, due_date: str) -> str:
    amount = parse_amount(open_amount)
    if amount <= 0:
        return STATUS_PAID
    if validate_date(due_date) and datetime.strptime(due_date, DATE_FMT).date() < datetime.now().date():
        return STATUS_OVERDUE
    return STATUS_OPEN


def urgency_bucket(due_date: str, open_amount: Any) -> str:
    if parse_amount(open_amount) <= 0:
        return "paid"
    if not validate_date(due_date):
        return "open"
    d = datetime.strptime(due_date, DATE_FMT).date()
    delta = (d - datetime.now().date()).days
    if delta < 0:
        return "overdue"
    if delta <= 7:
        return "soon"
    return "open"


def normalize_tax_code(code: str) -> str:
    return (code or "").strip().upper()


def yes_no_to_int(v: Any) -> int:
    return 1 if str(v).lower() in ("1", "ja", "true", "aktiv", "yes") else 0


def int_to_yes_no(v: Any) -> str:
    return "Ja" if int(v or 0) else "Nein"


def generate_number(prefix: str, meta_key: str, width: int = 5) -> str:
    with get_connection() as con:
        row = con.execute("SELECT value FROM app_meta WHERE key=?", (meta_key,)).fetchone()
        current = int(row[0]) if row else 0
        nxt = current + 1
        con.execute("INSERT OR REPLACE INTO app_meta(key,value,updated_at) VALUES(?,?,?)", (meta_key, str(nxt), now_str()))
        con.commit()
    return f"{prefix}{nxt:0{width}d}"


def next_hist_no() -> str:
    return generate_number("HIST-", "counter_hist", 6)


def clean_document_title(path: str) -> str:
    return Path(path).stem.replace("_", " ").replace("-", " ").strip() or Path(path).name


def iter_supported_files_from_folder(folder: str) -> Iterable[str]:
    for root, _dirs, files in os.walk(folder):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in SUPPORTED_ARCHIVE_EXTENSIONS:
                yield str(p)


def collect_preview_text(path: str, limit: int = 8000) -> str:
    p = Path(path)
    if not p.exists():
        return "Datei nicht gefunden."
    if p.suffix.lower() in {".txt", ".csv"}:
        try:
            return p.read_text(encoding="utf-8", errors="replace")[:limit]
        except Exception as exc:
            return f"Textvorschau nicht möglich: {exc}"
    return f"Dokumentkarte\n\nDatei: {p.name}\nTyp: {mimetypes.guess_type(str(p))[0] or p.suffix}\nPfad: {p}\n\nFür PDF-/Office-Dateien wird eine Dateikarte angezeigt. Öffnen über Doppelklick oder Kontextmenü."


def open_path(path: str) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as exc:
        messagebox.showerror("Öffnen nicht möglich", str(exc))


def apply_search_placeholder(entry: tk.Entry, placeholder: str = PLACEHOLDER_TEXT) -> None:
    def on_focus_in(_event=None):
        if entry.get() == placeholder and entry.cget("fg") == PLACEHOLDER_COLOR:
            entry.delete(0, tk.END)
            entry.config(fg=TEXT)
    def on_focus_out(_event=None):
        if not entry.get().strip():
            entry.insert(0, placeholder)
            entry.config(fg=PLACEHOLDER_COLOR)
    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    on_focus_out()


def create_standard_button(parent, text: str, command=None, confirm: bool = False, **kw):
    style = "Confirm.TButton" if confirm else "StandardGray.TButton"
    return ttk.Button(parent, text=text, command=command, style=style, **kw)


def configure_tree_tags(tree: ttk.Treeview) -> None:
    tree.tag_configure("paid", background=SOFT_GREEN)
    tree.tag_configure("soon", background=SOFT_YELLOW)
    tree.tag_configure("overdue", background=SOFT_RED)
    tree.tag_configure("open", background=WHITE)


def load_ui_preference(key: str, default: str = "") -> str:
    with get_connection() as con:
        row = con.execute("SELECT value FROM app_meta WHERE key=?", (f"ui:{key}",)).fetchone()
        return row[0] if row else default


def save_ui_preference(key: str, value: str) -> None:
    with get_connection() as con:
        con.execute("INSERT OR REPLACE INTO app_meta(key,value,updated_at) VALUES(?,?,?)", (f"ui:{key}", value, now_str()))
        con.commit()


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style="Vertical.TScrollbar")
        self.content = ttk.Frame(self.canvas)
        self.content_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.content_id, width=e.width))
        self._bind_mousewheel(self.canvas)
        self._bind_descendant_wheel(self.content)

    def _on_content_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_mousewheel(self, widget):
        widget.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel), add="+")
        widget.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"), add="+")

    def _bind_descendant_wheel(self, widget):
        # Wheel always scrolls frame; comboboxes explicitly do not change values by wheel.
        def bind_child(child):
            if isinstance(child, ttk.Combobox):
                child.bind("<MouseWheel>", lambda e: "break")
            else:
                child.bind("<MouseWheel>", self._on_mousewheel, add="+")
            for sub in child.winfo_children():
                bind_child(sub)
        self.after(100, lambda: bind_child(widget))

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"


class SortableTreeMixin:
    def _coerce_sort_value(self, value: str):
        if value is None:
            return ""
        s = str(value)
        try:
            return float(s.replace(".", "").replace(",", "."))
        except Exception:
            pass
        if validate_date(s):
            return datetime.strptime(s, DATE_FMT)
        return s.lower()

    def setup_sorting(self, tree: ttk.Treeview) -> None:
        for col in tree["columns"]:
            tree.heading(col, command=lambda c=col: self.sort_treeview(tree, c, False))

    def sort_treeview(self, tree: ttk.Treeview, col: str, reverse: bool) -> None:
        data = [(self._coerce_sort_value(tree.set(k, col)), k) for k in tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_val, k) in enumerate(data):
            tree.move(k, "", idx)
        tree.heading(col, command=lambda: self.sort_treeview(tree, col, not reverse))


class AttachmentMixin:
    def add_attachment_paths(self, entity_type: str, reference_no: str, paths: Sequence[str]) -> None:
        if not reference_no:
            messagebox.showwarning("Anhang", "Bitte zuerst einen Datensatz speichern oder auswählen.")
            return
        target_dir = ATTACHMENTS_DIR / entity_type / reference_no
        target_dir.mkdir(parents=True, exist_ok=True)
        with get_connection() as con:
            for p in paths:
                src = Path(p)
                if not src.exists():
                    continue
                dest = target_dir / src.name
                if dest.exists():
                    dest = target_dir / f"{src.stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}{src.suffix}"
                shutil.copy2(src, dest)
                con.execute(
                    "INSERT INTO attachments(entity_type,reference_no,file_name,file_path,added_at) VALUES(?,?,?,?,?)",
                    (entity_type, reference_no, dest.name, str(dest), now_str()),
                )
            con.commit()

    def get_attachment_count(self, entity_type: str, reference_no: str) -> int:
        with get_connection() as con:
            row = con.execute("SELECT COUNT(*) FROM attachments WHERE entity_type=? AND reference_no=?", (entity_type, reference_no)).fetchone()
            return int(row[0] if row else 0)

    def get_attachments(self, entity_type: str, reference_no: str) -> List[sqlite3.Row]:
        with get_connection() as con:
            return list(con.execute("SELECT * FROM attachments WHERE entity_type=? AND reference_no=? ORDER BY added_at DESC", (entity_type, reference_no)).fetchall())

    def open_attachment_popup(self, entity_type: str, reference_no: str) -> None:
        pop = tk.Toplevel()
        pop.title(f"Anhänge – {reference_no}")
        pop.geometry("900x520")
        pop.configure(bg=BG)
        ttk.Label(pop, text=f"Anhänge zu {entity_type} / {reference_no}", style="Section.TLabel").pack(anchor="w", padx=12, pady=8)
        cols = ("file_name", "file_path", "added_at")
        tree = ttk.Treeview(pop, columns=cols, show="headings")
        for col, w, txt in [("file_name", 220, "Dateiname"), ("file_path", 480, "Pfad"), ("added_at", 150, "Zeitstempel")]:
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="w")
        tree.pack(fill="both", expand=True, padx=12, pady=6)
        for r in self.get_attachments(entity_type, reference_no):
            tree.insert("", "end", values=(r["file_name"], r["file_path"], r["added_at"]))
        tree.bind("<Double-1>", lambda e: open_path(tree.set(tree.focus(), "file_path")) if tree.focus() else None)
        bar = ttk.Frame(pop)
        bar.pack(fill="x", padx=12, pady=10)
        create_standard_button(bar, "Datei hinzufügen", lambda: self._attachment_popup_add(entity_type, reference_no, tree), confirm=True).pack(side="left")
        create_standard_button(bar, "Schließen", pop.destroy).pack(side="right")

    def _attachment_popup_add(self, entity_type: str, reference_no: str, tree: ttk.Treeview):
        paths = filedialog.askopenfilenames(title="Anhänge auswählen")
        if paths:
            self.add_attachment_paths(entity_type, reference_no, paths)
            for i in tree.get_children(): tree.delete(i)
            for r in self.get_attachments(entity_type, reference_no):
                tree.insert("", "end", values=(r["file_name"], r["file_path"], r["added_at"]))


class TwoBlock(ttk.Frame):
    """Zentrale Zweiblock-Engine: freie Größenänderung ohne starre Wand."""
    def __init__(self, parent, left_title: str, right_title: str):
        super().__init__(parent)
        self.pane = ttk.PanedWindow(self, orient="horizontal")
        self.pane.pack(fill="both", expand=True)
        self.left = ttk.Frame(self.pane, style="Card.TFrame")
        self.right = ttk.Frame(self.pane, style="Card.TFrame")
        self.pane.add(self.left, weight=3)
        self.pane.add(self.right, weight=2)
        ttk.Label(self.left, text=left_title, style="Section.TLabel").pack(anchor="w", padx=10, pady=(8, 4))
        ttk.Label(self.right, text=right_title, style="Section.TLabel").pack(anchor="w", padx=10, pady=(8, 4))


def build_two_block_shell(parent, left_title: str, right_title: str) -> TwoBlock:
    tb = TwoBlock(parent, left_title, right_title)
    tb.pack(fill="both", expand=True)
    return tb


class StammdatenView(ttk.Frame, SortableTreeMixin):
    CONFIG = {
        "Sachkonten": {
            "table": "gl_accounts", "key": "account_no", "label": "Sachkonto",
            "fields": [("account_no", "Konto-Nr."), ("name", "Name"), ("account_type", "Kontotyp"), ("tax_code", "Steuerkennz."), ("active", "Aktiv")],
            "columns": [("id", 50, "ID"), ("account_no", 100, "Konto"), ("name", 220, "Name"), ("account_type", 120, "Typ"), ("tax_code", 100, "Steuer"), ("active", 70, "Aktiv")],
            "prefix": "SK"
        },
        "Debitoren": {
            "table": "customers", "key": "customer_no", "label": "Debitor",
            "fields": [("customer_no", "Debitor-Nr."), ("name", "Name"), ("country", "Land"), ("street", "Straße"), ("zip", "PLZ"), ("city", "Ort"), ("email", "E-Mail"), ("phone", "Telefon"), ("tax_id", "Steuer-Nr."), ("vat_id", "USt-IdNr."), ("iban", "IBAN"), ("bic", "BIC"), ("bank_name", "Bank"), ("payment_term", "Zahlungsbed."), ("active", "Aktiv")],
            "columns": [("id", 50, "ID"), ("customer_no", 110, "Nr."), ("name", 220, "Name"), ("city", 140, "Ort"), ("payment_term", 110, "ZB"), ("active", 70, "Aktiv")],
            "prefix": "D"
        },
        "Kreditoren": {
            "table": "vendors", "key": "vendor_no", "label": "Kreditor",
            "fields": [("vendor_no", "Kreditor-Nr."), ("name", "Name"), ("country", "Land"), ("street", "Straße"), ("zip", "PLZ"), ("city", "Ort"), ("email", "E-Mail"), ("phone", "Telefon"), ("tax_id", "Steuer-Nr."), ("vat_id", "USt-IdNr."), ("iban", "IBAN"), ("bic", "BIC"), ("bank_name", "Bank"), ("payment_term", "Zahlungsbed."), ("active", "Aktiv")],
            "columns": [("id", 50, "ID"), ("vendor_no", 110, "Nr."), ("name", 220, "Name"), ("city", 140, "Ort"), ("payment_term", 110, "ZB"), ("active", 70, "Aktiv")],
            "prefix": "K"
        },
        "Steuerkennzeichen": {
            "table": "tax_codes", "key": "code", "label": "Steuerkennzeichen",
            "fields": [("code", "Code"), ("name", "Name"), ("rate", "Satz %"), ("tax_scope", "Gültigkeit"), ("active", "Aktiv")],
            "columns": [("id", 50, "ID"), ("code", 90, "Code"), ("name", 240, "Name"), ("rate", 90, "%"), ("tax_scope", 120, "Gültigkeit"), ("active", 70, "Aktiv")],
            "prefix": "T"
        },
        "Zahlungsbedingungen": {
            "table": "payment_terms", "key": "code", "label": "Zahlungsbedingung",
            "fields": [("code", "Code"), ("name", "Name"), ("days", "Tage netto"), ("discount_days", "Skontotage"), ("discount_percent", "Skonto %"), ("active", "Aktiv")],
            "columns": [("id", 50, "ID"), ("code", 90, "Code"), ("name", 240, "Name"), ("days", 90, "Tage"), ("discount_percent", 100, "Skonto %"), ("active", 70, "Aktiv")],
            "prefix": "ZB"
        },
    }

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.vars: Dict[str, Dict[str, tk.StringVar]] = {}
        self.trees: Dict[str, ttk.Treeview] = {}
        self.search_vars: Dict[str, tk.StringVar] = {}
        self.selected_ids: Dict[str, Optional[int]] = {}
        self._build_ui()
        self.load_all_tables()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Stammdaten", style="CardTitle.TLabel").pack(side="left")
        create_standard_button(top, "Daten-Refresh", self.load_all_tables).pack(side="right")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        for title in self.CONFIG:
            self._build_tab(title)
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.load_all_tables())

    def _build_tab(self, title: str):
        cfg = self.CONFIG[title]
        frame = ttk.Frame(self.nb)
        self.nb.add(frame, text=title)
        shell = build_two_block_shell(frame, f"{title} – Liste", f"{title} – Formular")
        # left
        left_body = ttk.Frame(shell.left)
        left_body.pack(fill="both", expand=True, padx=10, pady=8)
        search = tk.Entry(left_body, relief="sunken", bg=WHITE, fg=TEXT)
        search.pack(fill="x", pady=(0, 6))
        apply_search_placeholder(search)
        search.bind("<KeyRelease>", lambda e, t=title, s=search: self.load_table_data(t, s.get()))
        cols = [c[0] for c in cfg["columns"]]
        tree = ttk.Treeview(left_body, columns=cols, show="headings", selectmode="browse")
        for col, w, txt in cfg["columns"]:
            tree.heading(col, text=txt)
            tree.column(col, width=w, anchor="w")
        tree.pack(fill="both", expand=True)
        tree.bind("<<TreeviewSelect>>", lambda e, t=title: self.load_selected_record(t))
        self.setup_sorting(tree)
        self.trees[title] = tree
        self.selected_ids[title] = None
        # right
        sf = ScrollableFrame(shell.right)
        sf.pack(fill="both", expand=True, padx=10, pady=8)
        self.vars[title] = {}
        for field, label in cfg["fields"]:
            row = ttk.Frame(sf.content)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=18).pack(side="left")
            var = tk.StringVar(value="Ja" if field == "active" else "")
            self.vars[title][field] = var
            if field == "country":
                cb = ttk.Combobox(row, textvariable=var, values=TRADE_COUNTRIES, state="readonly")
                cb.pack(side="left", fill="x", expand=True)
                cb.bind("<MouseWheel>", lambda e: "break")
            elif field == "tax_scope":
                cb = ttk.Combobox(row, textvariable=var, values=TAX_SCOPE_VALUES, state="readonly")
                cb.pack(side="left", fill="x", expand=True); cb.bind("<MouseWheel>", lambda e: "break")
            elif field == "payment_term":
                cb = ttk.Combobox(row, textvariable=var, values=self._load_payment_term_codes(), state="readonly")
                cb.pack(side="left", fill="x", expand=True); cb.bind("<MouseWheel>", lambda e: "break")
            elif field == "active":
                cb = ttk.Combobox(row, textvariable=var, values=["Ja", "Nein"], state="readonly")
                cb.pack(side="left", fill="x", expand=True); cb.bind("<MouseWheel>", lambda e: "break")
            else:
                ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)
        btns = ttk.Frame(sf.content)
        btns.pack(fill="x", pady=10)
        create_standard_button(btns, "Neu / Felder leeren", lambda t=title: self.clear_form(t)).pack(side="left", padx=3)
        create_standard_button(btns, "Speichern", lambda t=title: self.save_record(t), confirm=True).pack(side="left", padx=3)
        create_standard_button(btns, "Löschen", lambda t=title: self.delete_record(t)).pack(side="left", padx=3)

    def _load_payment_term_codes(self):
        with get_connection() as con:
            return [r[0] for r in con.execute("SELECT code FROM payment_terms ORDER BY code")]

    def load_all_tables(self):
        for t in self.CONFIG:
            self.load_table_data(t)

    def load_table_data(self, title: str, search: str = ""):
        if search == PLACEHOLDER_TEXT: search = ""
        cfg = self.CONFIG[title]
        tree = self.trees[title]
        for i in tree.get_children(): tree.delete(i)
        cols = [c[0] for c in cfg["columns"]]
        sql = f"SELECT {','.join(cols)} FROM {cfg['table']}"
        params: List[Any] = []
        if search.strip():
            where_cols = [c for c in cols if c != "id"]
            sql += " WHERE " + " OR ".join([f"CAST({c} AS TEXT) LIKE ?" for c in where_cols])
            params = [f"%{search.strip()}%"] * len(where_cols)
        sql += " ORDER BY id DESC"
        with get_connection() as con:
            for r in con.execute(sql, params):
                vals = [int_to_yes_no(r[c]) if c == "active" else r[c] for c in cols]
                tree.insert("", "end", values=vals)

    def load_selected_record(self, title: str):
        tree = self.trees[title]
        iid = tree.focus()
        if not iid: return
        item = tree.item(iid)
        rec_id = item["values"][0]
        self.selected_ids[title] = int(rec_id)
        cfg = self.CONFIG[title]
        with get_connection() as con:
            row = con.execute(f"SELECT * FROM {cfg['table']} WHERE id=?", (rec_id,)).fetchone()
        if not row: return
        for field, var in self.vars[title].items():
            if field == "active": var.set(int_to_yes_no(row[field]))
            else: var.set(str(row[field] or ""))

    def clear_form(self, title: str):
        self.selected_ids[title] = None
        cfg = self.CONFIG[title]
        for field, var in self.vars[title].items():
            if field == "active": var.set("Ja")
            elif field == "country": var.set("Deutschland")
            elif field == cfg["key"]: var.set(generate_number(cfg["prefix"], f"counter_{cfg['table']}", 5))
            else: var.set("")

    def save_record(self, title: str):
        cfg = self.CONFIG[title]
        vals = {field: var.get().strip() for field, var in self.vars[title].items()}
        if not vals.get(cfg["key"]):
            vals[cfg["key"]] = generate_number(cfg["prefix"], f"counter_{cfg['table']}", 5)
        if not vals.get("name") and "name" in vals:
            messagebox.showwarning("Pflichtfeld", "Bitte einen Namen eingeben.")
            return
        if "active" in vals: vals["active"] = yes_no_to_int(vals["active"])
        now = now_str()
        with get_connection() as con:
            if self.selected_ids[title]:
                cols = list(vals.keys()) + ["updated_at"]
                params = list(vals.values()) + [now, self.selected_ids[title]]
                con.execute(f"UPDATE {cfg['table']} SET " + ",".join([f"{c}=?" for c in cols]) + " WHERE id=?", params)
            else:
                vals["created_at"] = now; vals["updated_at"] = now
                cols = list(vals.keys())
                con.execute(f"INSERT INTO {cfg['table']}({','.join(cols)}) VALUES({','.join(['?']*len(cols))})", list(vals.values()))
                self.selected_ids[title] = con.execute("SELECT last_insert_rowid()").fetchone()[0]
            con.commit()
        self.app.set_status(f"{title}: Datensatz gespeichert.")
        self.load_table_data(title)

    def delete_record(self, title: str):
        rec_id = self.selected_ids[title]
        if not rec_id:
            messagebox.showinfo("Löschen", "Bitte zuerst einen Datensatz auswählen.")
            return
        cfg = self.CONFIG[title]
        name = self.vars[title].get("name", tk.StringVar(value="")).get() or self.vars[title].get("code", tk.StringVar(value="")).get()
        if not messagebox.askyesno("Unwiderruflich löschen", f"[{rec_id}] [{name}] unwiderruflich löschen?"):
            return
        with get_connection() as con:
            con.execute(f"DELETE FROM {cfg['table']} WHERE id=?", (rec_id,)); con.commit()
        self.clear_form(title)
        self.load_table_data(title)
        self.app.set_status(f"{title}: Datensatz gelöscht.")


class JournalView(ttk.Frame, SortableTreeMixin, AttachmentMixin):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pending_lines: List[Dict[str, Any]] = []
        self.pending_attachments: List[str] = []
        self.selected_doc = ""
        self._build_ui()
        self.reload_journal_entries()

    def _build_ui(self):
        shell = build_two_block_shell(self, "Buchung erfassen", "Historie / Kontrolle")
        left = ScrollableFrame(shell.left); left.pack(fill="both", expand=True, padx=10, pady=8)
        self.doc_no = tk.StringVar(value=generate_number("B", "counter_journal", 6))
        self.doc_date = tk.StringVar(value=today_str()); self.posting_date = tk.StringVar(value=today_str()); self.desc = tk.StringVar()
        for label, var in [("Beleg-Nr.", self.doc_no), ("Belegdatum", self.doc_date), ("Buchungsdatum", self.posting_date), ("Beschreibung", self.desc)]:
            self._labeled_entry(left.content, label, var)
        ttk.Separator(left.content).pack(fill="x", pady=8)
        self.line_account = tk.StringVar(); self.line_side = tk.StringVar(value="Soll"); self.line_amount = tk.StringVar(); self.line_tax = tk.StringVar(); self.line_text = tk.StringVar()
        self._labeled_combo(left.content, "Konto", self.line_account, self._load_accounts())
        self._labeled_combo(left.content, "Soll/Haben", self.line_side, ["Soll", "Haben"])
        self._labeled_entry(left.content, "Betrag", self.line_amount)
        self._labeled_combo(left.content, "Steuerkennz.", self.line_tax, self._load_tax_codes())
        self._labeled_entry(left.content, "Text", self.line_text)
        btns = ttk.Frame(left.content); btns.pack(fill="x", pady=6)
        create_standard_button(btns, "Zeile hinzufügen", self.add_line_item, confirm=True).pack(side="left", padx=3)
        create_standard_button(btns, "Zeile entfernen", self.remove_selected_line).pack(side="left", padx=3)
        cols = ("account", "side", "amount", "tax", "text")
        self.lines_tree = ttk.Treeview(left.content, columns=cols, show="headings", height=7)
        for c, t, w in [("account", "Konto", 110), ("side", "S/H", 70), ("amount", "Betrag", 100), ("tax", "Steuer", 90), ("text", "Text", 240)]:
            self.lines_tree.heading(c, text=t); self.lines_tree.column(c, width=w, anchor="w")
        self.lines_tree.pack(fill="x", pady=6)
        self.totals = ttk.Label(left.content, text="Soll 0,00 | Haben 0,00 | Differenz 0,00", style="Hint.TLabel")
        self.totals.pack(anchor="w", pady=5)
        btns2 = ttk.Frame(left.content); btns2.pack(fill="x", pady=10)
        create_standard_button(btns2, "Anhang vormerken", self.add_pending_attachments).pack(side="left", padx=3)
        create_standard_button(btns2, "Buchung speichern", self.save_journal_entry, confirm=True).pack(side="left", padx=3)
        create_standard_button(btns2, "Neu", self.clear_journal_form).pack(side="left", padx=3)
        # right history
        body = ttk.Frame(shell.right); body.pack(fill="both", expand=True, padx=10, pady=8)
        cols = ("document_no", "posting_date", "description", "debit", "credit", "att")
        self.hist_tree = ttk.Treeview(body, columns=cols, show="headings")
        for c, t, w in [("document_no", "Beleg", 110), ("posting_date", "Datum", 90), ("description", "Beschreibung", 240), ("debit", "Soll", 90), ("credit", "Haben", 90), ("att", "Anh.", 55)]:
            self.hist_tree.heading(c, text=t); self.hist_tree.column(c, width=w, anchor="w")
        self.hist_tree.pack(fill="both", expand=True)
        self.hist_tree.bind("<Double-1>", self._on_history_click)
        create_standard_button(body, "Anhang zu ausgewähltem Beleg", self.add_attachment_to_selected_history).pack(anchor="e", pady=8)
        self.setup_sorting(self.hist_tree)

    def _labeled_entry(self, parent, label, var):
        row = ttk.Frame(parent); row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=16).pack(side="left")
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

    def _labeled_combo(self, parent, label, var, values):
        row = ttk.Frame(parent); row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=16).pack(side="left")
        cb = ttk.Combobox(row, textvariable=var, values=values)
        cb.pack(side="left", fill="x", expand=True); cb.bind("<MouseWheel>", lambda e: "break")

    def _load_accounts(self):
        with get_connection() as con: return [f"{r['account_no']} {r['name']}" for r in con.execute("SELECT account_no,name FROM gl_accounts WHERE active=1 ORDER BY account_no")]
    def _load_tax_codes(self):
        with get_connection() as con: return [r[0] for r in con.execute("SELECT code FROM tax_codes WHERE active=1 ORDER BY code")]

    def add_line_item(self):
        try: amount = parse_amount(self.line_amount.get())
        except ValueError as exc: messagebox.showwarning("Betrag", str(exc)); return
        acc = self.line_account.get().split(" ")[0]
        if not acc or amount <= 0: messagebox.showwarning("Zeile", "Bitte Konto und positiven Betrag erfassen."); return
        self.pending_lines.append({"account": acc, "side": self.line_side.get(), "amount": float(amount), "tax": self.line_tax.get(), "text": self.line_text.get()})
        self._refresh_lines_tree(); self.clear_line_inputs()

    def remove_selected_line(self):
        iid = self.lines_tree.focus()
        if iid:
            idx = self.lines_tree.index(iid); self.pending_lines.pop(idx); self._refresh_lines_tree()

    def clear_line_inputs(self):
        self.line_account.set(""); self.line_side.set("Soll"); self.line_amount.set(""); self.line_tax.set(""); self.line_text.set("")

    def _refresh_lines_tree(self):
        for i in self.lines_tree.get_children(): self.lines_tree.delete(i)
        debit = Decimal("0"); credit = Decimal("0")
        for ln in self.pending_lines:
            self.lines_tree.insert("", "end", values=(ln["account"], ln["side"], format_amount(ln["amount"]), ln["tax"], ln["text"]))
            if ln["side"] == "Soll": debit += parse_amount(ln["amount"])
            else: credit += parse_amount(ln["amount"])
        diff = debit - credit
        self.totals.config(text=f"Soll {format_amount(debit)} | Haben {format_amount(credit)} | Differenz {format_amount(diff)}")

    def add_pending_attachments(self):
        paths = filedialog.askopenfilenames(title="Beleganhänge vormerken")
        if paths:
            self.pending_attachments.extend(paths)
            self.app.set_status(f"{len(paths)} Anhang/Anhänge vorgemerkt.")

    def save_journal_entry(self):
        if not validate_date(self.doc_date.get()) or not validate_date(self.posting_date.get()):
            messagebox.showwarning("Datum", "Datumsformat bitte TT.MM.JJJJ verwenden."); return
        if not self.pending_lines: messagebox.showwarning("Buchung", "Bitte mindestens eine Buchungszeile erfassen."); return
        debit = sum(parse_amount(ln["amount"]) for ln in self.pending_lines if ln["side"] == "Soll")
        credit = sum(parse_amount(ln["amount"]) for ln in self.pending_lines if ln["side"] == "Haben")
        if debit != credit:
            messagebox.showwarning("Nicht ausgeglichen", "Soll und Haben müssen identisch sein."); return
        with get_connection() as con:
            con.execute("INSERT INTO journal_entries(document_no,document_date,posting_date,description,total_debit,total_credit,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                        (self.doc_no.get(), self.doc_date.get(), self.posting_date.get(), self.desc.get(), float(debit), float(credit), "Gebucht", now_str(), now_str()))
            for ln in self.pending_lines:
                con.execute("INSERT INTO journal_entry_lines(document_no,account_no,side,amount,tax_code,text) VALUES(?,?,?,?,?,?)", (self.doc_no.get(), ln["account"], ln["side"], ln["amount"], ln["tax"], ln["text"]))
            con.commit()
        if self.pending_attachments:
            self.add_attachment_paths("journal", self.doc_no.get(), self.pending_attachments)
        self.app.set_status(f"Buchung {self.doc_no.get()} gespeichert.")
        self.clear_journal_form(); self.reload_journal_entries()

    def clear_journal_form(self):
        self.doc_no.set(generate_number("B", "counter_journal", 6)); self.doc_date.set(today_str()); self.posting_date.set(today_str()); self.desc.set("")
        self.pending_lines.clear(); self.pending_attachments.clear(); self._refresh_lines_tree(); self.clear_line_inputs()

    def reload_journal_entries(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        with get_connection() as con:
            for r in con.execute("SELECT * FROM journal_entries ORDER BY id DESC"):
                att = self.get_attachment_count("journal", r["document_no"])
                self.hist_tree.insert("", "end", values=(r["document_no"], r["posting_date"], r["description"], format_amount(r["total_debit"]), format_amount(r["total_credit"]), f"📎 {att}" if att else ""))

    def _on_history_click(self, _event=None):
        iid = self.hist_tree.focus()
        if iid:
            doc = self.hist_tree.set(iid, "document_no")
            self.open_attachment_popup("journal", doc)

    def add_attachment_to_selected_history(self):
        iid = self.hist_tree.focus()
        if not iid: messagebox.showinfo("Anhang", "Bitte Buchung auswählen."); return
        doc = self.hist_tree.set(iid, "document_no")
        paths = filedialog.askopenfilenames(title="Anhang auswählen")
        if paths:
            self.add_attachment_paths("journal", doc, paths); self.reload_journal_entries()


class InvoiceModuleBase(ttk.Frame, SortableTreeMixin, AttachmentMixin):
    entity_label = "Rechnung"
    partner_table = "customers"
    partner_no_col = "customer_no"
    invoice_table = "customer_invoices"
    entity_type = "customer_invoice"
    prefix = "AR"

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pending_attachments: List[str] = []
        self.selected_invoice = ""
        self._load_reference_data()
        self._build_ui()
        self.reload_invoices(); self.reload_open_items()

    def _load_reference_data(self):
        with get_connection() as con:
            self.partners = [f"{r[self.partner_no_col]} {r['name']}" for r in con.execute(f"SELECT {self.partner_no_col},name FROM {self.partner_table} WHERE active=1 ORDER BY name")]
            self.tax_codes = [r[0] for r in con.execute("SELECT code FROM tax_codes WHERE active=1 ORDER BY code")]
            self.payment_terms = [r[0] for r in con.execute("SELECT code FROM payment_terms WHERE active=1 ORDER BY code")]

    def _build_ui(self):
        shell = build_two_block_shell(self, f"{self.entity_label} erfassen", "Offene Posten / Kontrolle")
        left = ScrollableFrame(shell.left); left.pack(fill="both", expand=True, padx=10, pady=8)
        self.invoice_no = tk.StringVar(value=self._generate_invoice_no())
        self.partner = tk.StringVar(); self.invoice_date = tk.StringVar(value=today_str()); self.due_date = tk.StringVar(value=today_str())
        self.payment_term = tk.StringVar(); self.tax_code = tk.StringVar(value="V19"); self.net_amount = tk.StringVar(); self.tax_amount = tk.StringVar(); self.gross_amount = tk.StringVar()
        self._labeled_entry(left.content, "Rechnungs-Nr.", self.invoice_no)
        self._labeled_combo(left.content, "Partner", self.partner, self.partners)
        self._labeled_entry(left.content, "Rechnungsdatum", self.invoice_date)
        self._labeled_combo(left.content, "Zahlungsbed.", self.payment_term, self.payment_terms)
        self._labeled_entry(left.content, "Fälligkeit", self.due_date)
        self._labeled_combo(left.content, "Steuerkennz.", self.tax_code, self.tax_codes)
        self._labeled_entry(left.content, "Netto", self.net_amount)
        self._labeled_entry(left.content, "Steuer", self.tax_amount)
        self._labeled_entry(left.content, "Brutto", self.gross_amount)
        self.payment_term.trace_add("write", lambda *_: self.apply_payment_term())
        self.net_amount.trace_add("write", lambda *_: self._calculate_amounts())
        self.tax_code.trace_add("write", lambda *_: self._calculate_amounts())
        btns = ttk.Frame(left.content); btns.pack(fill="x", pady=8)
        create_standard_button(btns, "Anhang vormerken", self.add_pending_attachments).pack(side="left", padx=3)
        create_standard_button(btns, "Speichern", self.save_invoice, confirm=True).pack(side="left", padx=3)
        create_standard_button(btns, "Neu", self.clear_form).pack(side="left", padx=3)
        ttk.Label(left.content, text="Erfasste Rechnungen", style="Section.TLabel").pack(anchor="w", pady=(10, 4))
        cols = ("invoice_no", "partner", "date", "due", "gross", "open", "status", "att")
        self.inv_tree = ttk.Treeview(left.content, columns=cols, show="headings", height=9)
        for c, t, w in [("invoice_no", "Rechnung", 110), ("partner", "Partner", 180), ("date", "Datum", 90), ("due", "Fällig", 90), ("gross", "Brutto", 90), ("open", "Offen", 90), ("status", "Status", 110), ("att", "Anh.", 55)]:
            self.inv_tree.heading(c, text=t); self.inv_tree.column(c, width=w, anchor="w")
        self.inv_tree.pack(fill="both", expand=True)
        self.inv_tree.bind("<Double-1>", lambda e: self.add_attachment_to_selected_invoice())
        configure_tree_tags(self.inv_tree); self.setup_sorting(self.inv_tree)
        # right
        right = ttk.Frame(shell.right); right.pack(fill="both", expand=True, padx=10, pady=8)
        cols2 = ("reference_no", "partner", "due", "original", "open", "status")
        self.op_tree = ttk.Treeview(right, columns=cols2, show="headings")
        for c, t, w in [("reference_no", "Referenz", 120), ("partner", "Partner", 180), ("due", "Fällig", 90), ("original", "Original", 90), ("open", "Offen", 90), ("status", "Status", 120)]:
            self.op_tree.heading(c, text=t); self.op_tree.column(c, width=w, anchor="w")
        self.op_tree.pack(fill="both", expand=True)
        configure_tree_tags(self.op_tree); self.setup_sorting(self.op_tree)
        create_standard_button(right, "Anhang zu Rechnung", self.add_attachment_to_selected_invoice).pack(anchor="e", pady=8)

    def _generate_invoice_no(self): return generate_number(self.prefix, f"counter_{self.invoice_table}", 6)
    def _labeled_entry(self, parent, label, var):
        row = ttk.Frame(parent); row.pack(fill="x", pady=3); ttk.Label(row, text=label, width=16).pack(side="left"); ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)
    def _labeled_combo(self, parent, label, var, values):
        row = ttk.Frame(parent); row.pack(fill="x", pady=3); ttk.Label(row, text=label, width=16).pack(side="left")
        cb = ttk.Combobox(row, textvariable=var, values=values); cb.pack(side="left", fill="x", expand=True); cb.bind("<MouseWheel>", lambda e: "break")

    def apply_payment_term(self):
        if validate_date(self.invoice_date.get()) and self.payment_term.get():
            try: self.due_date.set(calc_due_date(self.invoice_date.get(), self.payment_term.get()))
            except Exception: pass

    def _calculate_amounts(self):
        try: net = parse_amount(self.net_amount.get())
        except Exception: return
        rate = Decimal("0")
        with get_connection() as con:
            row = con.execute("SELECT rate FROM tax_codes WHERE code=?", (self.tax_code.get(),)).fetchone()
            if row: rate = Decimal(str(row[0] or 0))
        tax = (net * rate / Decimal("100")).quantize(Decimal("0.01")); gross = net + tax
        self.tax_amount.set(format_amount(tax)); self.gross_amount.set(format_amount(gross))

    def _partner_parts(self):
        no = self.partner.get().split(" ")[0] if self.partner.get() else ""
        with get_connection() as con:
            row = con.execute(f"SELECT * FROM {self.partner_table} WHERE {self.partner_no_col}=?", (no,)).fetchone()
        if row:
            address = f"{row['street']}, {row['zip']} {row['city']}, {row['country']}".strip(', ')
            return no, row["name"], address
        return no, self.partner.get(), ""

    def add_pending_attachments(self):
        paths = filedialog.askopenfilenames(title="Beleganhänge vormerken")
        if paths: self.pending_attachments.extend(paths); self.app.set_status(f"{len(paths)} Anhang/Anhänge vorgemerkt.")

    def save_invoice(self):
        if not validate_date(self.invoice_date.get()) or not validate_date(self.due_date.get()): messagebox.showwarning("Datum", "Datumsformat TT.MM.JJJJ verwenden."); return
        no, name, address = self._partner_parts()
        if not no: messagebox.showwarning("Partner", "Bitte Partner auswählen."); return
        gross = parse_amount(self.gross_amount.get()); net = parse_amount(self.net_amount.get()); tax = parse_amount(self.tax_amount.get())
        status = compute_status_from_open_amount(gross, self.due_date.get())
        address_col = "customer_address" if self.invoice_table == "customer_invoices" else "vendor_address"
        partner_name_col = "customer_name" if self.invoice_table == "customer_invoices" else "vendor_name"
        partner_no_col = "customer_no" if self.invoice_table == "customer_invoices" else "vendor_no"
        with get_connection() as con:
            con.execute(f"INSERT INTO {self.invoice_table}(invoice_no,{partner_no_col},{partner_name_col},{address_col},invoice_date,due_date,payment_term,tax_code,net_amount,tax_amount,gross_amount,open_amount,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (self.invoice_no.get(), no, name, address, self.invoice_date.get(), self.due_date.get(), self.payment_term.get(), self.tax_code.get(), float(net), float(tax), float(gross), float(gross), status, now_str(), now_str()))
            con.execute("INSERT INTO open_items(entity_type,reference_no,partner_no,partner_name,due_date,original_amount,open_amount,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (self.entity_type, self.invoice_no.get(), no, name, self.due_date.get(), float(gross), float(gross), status, now_str(), now_str()))
            con.commit()
        if self.pending_attachments: self.add_attachment_paths(self.entity_type, self.invoice_no.get(), self.pending_attachments)
        self.app.set_status(f"{self.entity_label} {self.invoice_no.get()} gespeichert.")
        self.clear_form(); self.reload_invoices(); self.reload_open_items()

    def clear_form(self):
        self.invoice_no.set(self._generate_invoice_no()); self.partner.set(""); self.invoice_date.set(today_str()); self.due_date.set(today_str()); self.payment_term.set(""); self.tax_code.set("V19"); self.net_amount.set(""); self.tax_amount.set(""); self.gross_amount.set(""); self.pending_attachments.clear()

    def reload_invoices(self):
        for i in self.inv_tree.get_children(): self.inv_tree.delete(i)
        partner_name_col = "customer_name" if self.invoice_table == "customer_invoices" else "vendor_name"
        with get_connection() as con:
            for r in con.execute(f"SELECT * FROM {self.invoice_table} ORDER BY id DESC"):
                att = self.get_attachment_count(self.entity_type, r["invoice_no"])
                tag = urgency_bucket(r["due_date"], r["open_amount"])
                self.inv_tree.insert("", "end", values=(r["invoice_no"], r[partner_name_col], r["invoice_date"], r["due_date"], format_amount(r["gross_amount"]), format_amount(r["open_amount"]), r["status"], f"📎 {att}" if att else ""), tags=(tag,))

    def reload_open_items(self):
        for i in self.op_tree.get_children(): self.op_tree.delete(i)
        with get_connection() as con:
            for r in con.execute("SELECT * FROM open_items WHERE entity_type=? ORDER BY due_date", (self.entity_type,)):
                tag = urgency_bucket(r["due_date"], r["open_amount"])
                self.op_tree.insert("", "end", values=(r["reference_no"], r["partner_name"], r["due_date"], format_amount(r["original_amount"]), format_amount(r["open_amount"]), r["status"]), tags=(tag,))

    def add_attachment_to_selected_invoice(self):
        iid = self.inv_tree.focus()
        if not iid: messagebox.showinfo("Anhang", "Bitte Rechnung auswählen."); return
        inv = self.inv_tree.set(iid, "invoice_no")
        paths = filedialog.askopenfilenames(title="Anhang auswählen")
        if paths: self.add_attachment_paths(self.entity_type, inv, paths); self.reload_invoices()


class DebitorsView(InvoiceModuleBase):
    entity_label = "Ausgangsrechnung"
    partner_table = "customers"; partner_no_col = "customer_no"; invoice_table = "customer_invoices"; entity_type = "customer_invoice"; prefix = "AR"


class CreditorsView(InvoiceModuleBase):
    entity_label = "Eingangsrechnung"
    partner_table = "vendors"; partner_no_col = "vendor_no"; invoice_table = "vendor_invoices"; entity_type = "vendor_invoice"; prefix = "ER"

    def _build_ui(self):
        outer = ttk.PanedWindow(self, orient="vertical"); outer.pack(fill="both", expand=True)
        invoice_area = ttk.Frame(outer); stack_area = ttk.Frame(outer)
        outer.add(invoice_area, weight=3); outer.add(stack_area, weight=2)
        # temporarily build base UI into invoice_area by monkey parent composition
        old_parent = self.master
        shell = build_two_block_shell(invoice_area, "Eingangsrechnung erfassen", "OP / Freigabe")
        left = ScrollableFrame(shell.left); left.pack(fill="both", expand=True, padx=10, pady=8)
        self.invoice_no = tk.StringVar(value=self._generate_invoice_no())
        self.partner = tk.StringVar(); self.invoice_date = tk.StringVar(value=today_str()); self.due_date = tk.StringVar(value=today_str())
        self.payment_term = tk.StringVar(); self.tax_code = tk.StringVar(value="V19"); self.net_amount = tk.StringVar(); self.tax_amount = tk.StringVar(); self.gross_amount = tk.StringVar()
        self._labeled_entry(left.content, "Rechnungs-Nr.", self.invoice_no)
        prow = ttk.Frame(left.content); prow.pack(fill="x", pady=3)
        ttk.Label(prow, text="Kreditor", width=16).pack(side="left")
        cb = ttk.Combobox(prow, textvariable=self.partner, values=self.partners); cb.pack(side="left", fill="x", expand=True); cb.bind("<MouseWheel>", lambda e: "break")
        create_standard_button(prow, "+", self._open_vendor_quick_popup).pack(side="left", padx=3)
        self._labeled_entry(left.content, "Rechnungsdatum", self.invoice_date)
        self._labeled_combo(left.content, "Zahlungsbed.", self.payment_term, self.payment_terms)
        self._labeled_entry(left.content, "Fälligkeit", self.due_date)
        self._labeled_combo(left.content, "Steuerkennz.", self.tax_code, self.tax_codes)
        self._labeled_entry(left.content, "Netto", self.net_amount); self._labeled_entry(left.content, "Steuer", self.tax_amount); self._labeled_entry(left.content, "Brutto", self.gross_amount)
        self.payment_term.trace_add("write", lambda *_: self.apply_payment_term()); self.net_amount.trace_add("write", lambda *_: self._calculate_amounts()); self.tax_code.trace_add("write", lambda *_: self._calculate_amounts())
        btns = ttk.Frame(left.content); btns.pack(fill="x", pady=8)
        create_standard_button(btns, "Anhang vormerken", self.add_pending_attachments).pack(side="left", padx=3)
        create_standard_button(btns, "Speichern", self.save_invoice, confirm=True).pack(side="left", padx=3)
        create_standard_button(btns, "Neu", self.clear_form).pack(side="left", padx=3)
        ttk.Label(left.content, text="Eingangsrechnungen", style="Section.TLabel").pack(anchor="w", pady=(10, 4))
        cols = ("invoice_no", "partner", "date", "due", "gross", "open", "status", "att")
        self.inv_tree = ttk.Treeview(left.content, columns=cols, show="headings", height=7)
        for c, t, w in [("invoice_no", "Rechnung", 110), ("partner", "Kreditor", 180), ("date", "Datum", 90), ("due", "Fällig", 90), ("gross", "Brutto", 90), ("open", "Offen", 90), ("status", "Status", 110), ("att", "Anh.", 55)]: self.inv_tree.heading(c, text=t); self.inv_tree.column(c, width=w, anchor="w")
        self.inv_tree.pack(fill="both", expand=True); self.inv_tree.bind("<Double-1>", lambda e: self.add_attachment_to_selected_invoice()); configure_tree_tags(self.inv_tree); self.setup_sorting(self.inv_tree)
        right = ttk.Frame(shell.right); right.pack(fill="both", expand=True, padx=10, pady=8)
        cols2 = ("reference_no", "partner", "due", "original", "open", "status")
        self.op_tree = ttk.Treeview(right, columns=cols2, show="headings")
        for c, t, w in [("reference_no", "Referenz", 120), ("partner", "Kreditor", 180), ("due", "Fällig", 90), ("original", "Original", 90), ("open", "Offen", 90), ("status", "Status", 120)]: self.op_tree.heading(c, text=t); self.op_tree.column(c, width=w, anchor="w")
        self.op_tree.pack(fill="both", expand=True); configure_tree_tags(self.op_tree); self.setup_sorting(self.op_tree)
        create_standard_button(right, "Anhang zu Rechnung", self.add_attachment_to_selected_invoice).pack(anchor="e", pady=8)
        self._build_stack_ui(stack_area)

    def _open_vendor_quick_popup(self):
        pop = tk.Toplevel(self); pop.title("Quick-Kreditor"); pop.geometry("520x360"); pop.configure(bg=BG)
        vars = {k: tk.StringVar() for k in ["vendor_no", "name", "country", "street", "zip", "city", "payment_term"]}
        vars["vendor_no"].set(generate_number("K", "counter_vendors", 5)); vars["country"].set("Deutschland")
        for key, label in [("vendor_no", "Kreditor-Nr."), ("name", "Name"), ("country", "Land"), ("street", "Straße"), ("zip", "PLZ"), ("city", "Ort"), ("payment_term", "Zahlungsbed.")]:
            row = ttk.Frame(pop); row.pack(fill="x", padx=12, pady=4); ttk.Label(row, text=label, width=16).pack(side="left"); ttk.Entry(row, textvariable=vars[key]).pack(side="left", fill="x", expand=True)
        def save():
            if not vars["name"].get().strip(): messagebox.showwarning("Pflichtfeld", "Name fehlt."); return
            with get_connection() as con:
                con.execute("INSERT INTO vendors(vendor_no,name,country,street,zip,city,payment_term,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (vars["vendor_no"].get(), vars["name"].get(), vars["country"].get(), vars["street"].get(), vars["zip"].get(), vars["city"].get(), vars["payment_term"].get(), 1, now_str(), now_str())); con.commit()
            self._load_reference_data(); self.partner.set(f"{vars['vendor_no'].get()} {vars['name'].get()}"); pop.destroy()
        create_standard_button(pop, "Speichern", save, confirm=True).pack(pady=12)

    def _build_stack_ui(self, parent):
        shell = build_two_block_shell(parent, "Dokumentenstapel", "Vorschau")
        left = ttk.Frame(shell.left); left.pack(fill="both", expand=True, padx=10, pady=8)
        bar = ttk.Frame(left); bar.pack(fill="x", pady=(0, 6))
        create_standard_button(bar, "Dateien importieren", self.import_creditor_files, confirm=True).pack(side="left", padx=2)
        create_standard_button(bar, "Ordner importieren", self.import_creditor_folder).pack(side="left", padx=2)
        create_standard_button(bar, "Alle markieren", self._toggle_all_marks).pack(side="left", padx=2)
        create_standard_button(bar, "Markierte löschen", self._delete_marked_batches).pack(side="left", padx=2)
        create_standard_button(bar, "Markierte zusammenführen", self.merge_selected_batches).pack(side="left", padx=2)
        cols = ("mark", "hist_no", "title", "status", "files", "created")
        self.stack_tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="extended")
        for c, t, w in [("mark", "☐", 45), ("hist_no", "Hist.-Nr.", 120), ("title", "Titel", 260), ("status", "Status", 100), ("files", "Dateien", 70), ("created", "Importiert", 150)]: self.stack_tree.heading(c, text=t); self.stack_tree.column(c, width=w, anchor="w")
        self.stack_tree.pack(fill="both", expand=True); self.stack_tree.bind("<ButtonRelease-1>", self._on_stack_select); self.stack_tree.bind("<Double-1>", lambda e: self._open_selected_stack_file())
        right = ttk.Frame(shell.right); right.pack(fill="both", expand=True, padx=10, pady=8)
        self.preview = tk.Text(right, wrap="word", bg=WHITE, fg=TEXT, relief="sunken")
        self.preview.pack(fill="both", expand=True)
        self._load_import_batches()

    def import_creditor_files(self):
        paths = filedialog.askopenfilenames(title="Dokumente importieren", filetypes=[("Unterstützte Dateien", "*.pdf *.png *.jpg *.jpeg *.bmp *.gif *.txt *.csv *.doc *.docx *.xls *.xlsx"), ("Alle Dateien", "*.*")])
        if paths: self._import_archive_paths(paths)

    def import_creditor_folder(self):
        folder = filedialog.askdirectory(title="Importordner auswählen")
        if folder: self._import_archive_paths(list(iter_supported_files_from_folder(folder)))

    def _import_archive_paths(self, paths: Sequence[str]):
        imported = 0
        with get_connection() as con:
            for src in paths:
                p = Path(src)
                if not p.exists() or p.suffix.lower() not in SUPPORTED_ARCHIVE_EXTENSIONS: continue
                hist = next_hist_no(); target_dir = IMPORTS_DIR / hist; target_dir.mkdir(parents=True, exist_ok=True)
                dest = target_dir / p.name; shutil.copy2(p, dest)
                title = clean_document_title(str(p))
                con.execute("INSERT INTO invoice_import_batches(hist_no,title,status,marked,created_at,updated_at) VALUES(?,?,?,?,?,?)", (hist, title, "Importiert", 0, now_str(), now_str()))
                con.execute("INSERT INTO invoice_import_files(hist_no,file_name,file_path,mime_type,created_at) VALUES(?,?,?,?,?)", (hist, dest.name, str(dest), mimetypes.guess_type(str(dest))[0] or "", now_str()))
                imported += 1
            con.commit()
        self._load_import_batches(); self.app.set_status(f"{imported} Dokument(e) importiert.")

    def _load_import_batches(self):
        if not hasattr(self, "stack_tree"): return
        for i in self.stack_tree.get_children(): self.stack_tree.delete(i)
        with get_connection() as con:
            rows = con.execute("SELECT b.*, COUNT(f.id) files FROM invoice_import_batches b LEFT JOIN invoice_import_files f ON f.hist_no=b.hist_no GROUP BY b.hist_no ORDER BY b.id DESC").fetchall()
            for r in rows:
                self.stack_tree.insert("", "end", values=("☑" if r["marked"] else "☐", r["hist_no"], r["title"], r["status"], r["files"], r["created_at"]))

    def _on_stack_select(self, event=None):
        iid = self.stack_tree.focus()
        if not iid: return
        col = self.stack_tree.identify_column(event.x) if event else ""
        hist = self.stack_tree.set(iid, "hist_no")
        if col == "#1":
            with get_connection() as con:
                row = con.execute("SELECT marked FROM invoice_import_batches WHERE hist_no=?", (hist,)).fetchone(); new = 0 if row and row[0] else 1
                con.execute("UPDATE invoice_import_batches SET marked=?, updated_at=? WHERE hist_no=?", (new, now_str(), hist)); con.commit()
            self._load_import_batches(); return
        self._refresh_stack_preview(hist)

    def _refresh_stack_preview(self, hist_no: str):
        with get_connection() as con: row = con.execute("SELECT * FROM invoice_import_files WHERE hist_no=? ORDER BY id LIMIT 1", (hist_no,)).fetchone()
        self.preview.delete("1.0", tk.END)
        if row: self.preview.insert("1.0", collect_preview_text(row["file_path"]))
        else: self.preview.insert("1.0", "Keine Datei im Stapel.")

    def _open_selected_stack_file(self):
        iid = self.stack_tree.focus()
        if not iid: return
        hist = self.stack_tree.set(iid, "hist_no")
        with get_connection() as con: row = con.execute("SELECT file_path FROM invoice_import_files WHERE hist_no=? ORDER BY id LIMIT 1", (hist,)).fetchone()
        if row: open_path(row["file_path"])

    def _toggle_all_marks(self):
        with get_connection() as con:
            any_unmarked = con.execute("SELECT 1 FROM invoice_import_batches WHERE marked=0 LIMIT 1").fetchone()
            con.execute("UPDATE invoice_import_batches SET marked=?, updated_at=?", (1 if any_unmarked else 0, now_str())); con.commit()
        self._load_import_batches()

    def _delete_marked_batches(self):
        if not messagebox.askyesno("Bulk-Löschung", "Alle markierten Stapel unwiderruflich löschen?"): return
        with get_connection() as con:
            rows = con.execute("SELECT hist_no FROM invoice_import_batches WHERE marked=1").fetchall()
            for r in rows:
                shutil.rmtree(IMPORTS_DIR / r["hist_no"], ignore_errors=True)
                con.execute("DELETE FROM invoice_import_batches WHERE hist_no=?", (r["hist_no"],))
            con.commit()
        self._load_import_batches(); self.preview.delete("1.0", tk.END)

    def merge_selected_batches(self):
        with get_connection() as con:
            rows = con.execute("SELECT hist_no,title FROM invoice_import_batches WHERE marked=1 ORDER BY id").fetchall()
            if len(rows) < 2: messagebox.showinfo("Zusammenführen", "Bitte mindestens zwei Stapel markieren."); return
            new_hist = next_hist_no(); target_dir = IMPORTS_DIR / new_hist; target_dir.mkdir(parents=True, exist_ok=True)
            title = " + ".join([r["title"] for r in rows])[:240]
            con.execute("INSERT INTO invoice_import_batches(hist_no,title,status,marked,created_at,updated_at) VALUES(?,?,?,?,?,?)", (new_hist, title, "Zusammengeführt", 0, now_str(), now_str()))
            for r in rows:
                for f in con.execute("SELECT * FROM invoice_import_files WHERE hist_no=?", (r["hist_no"],)).fetchall():
                    src = Path(f["file_path"]); dest = target_dir / f"{r['hist_no']}_{src.name}"
                    if src.exists(): shutil.copy2(src, dest)
                    con.execute("INSERT INTO invoice_import_files(hist_no,file_name,file_path,mime_type,created_at) VALUES(?,?,?,?,?)", (new_hist, dest.name, str(dest), f["mime_type"], now_str()))
                con.execute("UPDATE invoice_import_batches SET status='Zusammengeführt in ' || ?, marked=0, updated_at=? WHERE hist_no=?", (new_hist, now_str(), r["hist_no"]))
            con.commit()
        self._load_import_batches(); self.app.set_status(f"Stapel {new_hist} erzeugt.")


class FinanceMateApp(tk.Tk):
    def __init__(self):
        super().__init__()
        init_sqlite()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1420x860")
        self.minsize(1100, 680)
        self.configure(bg=BG)
        self.sidebar_collapsed = load_ui_preference("sidebar_collapsed", "0") == "1"
        self.active_module = "Dashboard"
        self.nav_buttons: Dict[str, ttk.Button] = {}
        self._configure_ttk()
        self._build_layout()
        self.show_module("Dashboard")

    def _configure_ttk(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except Exception: pass
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD_BG, relief="raised", borderwidth=1)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("CardTitle.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 15, "bold"))
        style.configure("Section.TLabel", background=CARD_BG, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        style.configure("Hint.TLabel", background=BG, foreground=TEXT2)
        style.configure("StandardGray.TButton", background=STANDARD_BUTTON_BG, foreground=TEXT, bordercolor=STANDARD_BUTTON_BORDER, relief="raised", padding=(8, 4))
        style.map("StandardGray.TButton", background=[("active", STANDARD_BUTTON_ACTIVE)])
        style.configure("Confirm.TButton", background=BUTTON_GREEN, foreground=TEXT, relief="raised", padding=(8, 4))
        style.map("Confirm.TButton", background=[("active", BUTTON_GREEN_ACTIVE)])
        style.configure("Nav.TButton", background=STANDARD_BUTTON_BG, anchor="w", padding=(8, 7), relief="raised")
        style.configure("NavActive.TButton", background="#c5d3e6", anchor="w", padding=(8, 7), relief="sunken")
        style.configure("Treeview.Heading", background=STANDARD_BUTTON_BG, relief="raised", foreground=TEXT)
        style.configure("Treeview", rowheight=24, fieldbackground=WHITE, background=WHITE)
        style.configure("TNotebook", background=BG)
        style.configure("TNotebook.Tab", background=STANDARD_BUTTON_BG, padding=(10, 5))
        style.map("TNotebook.Tab", background=[("selected", CARD_BG)])
        style.configure("Vertical.TScrollbar", background=STANDARD_BUTTON_BG, troughcolor="#edf0f3", arrowsize=14, width=15)
        style.configure("TCombobox", fieldbackground=WHITE, background=STANDARD_BUTTON_BG)

    def _build_layout(self):
        self.header = ttk.Frame(self, style="Card.TFrame"); self.header.pack(fill="x", padx=6, pady=(6, 3))
        ttk.Label(self.header, text=APP_NAME, style="CardTitle.TLabel").pack(side="left", padx=12, pady=7)
        ttk.Label(self.header, text=f"{STANDARD_DESIGN_NAME} · lokale SQLite-Persistenz · {APP_VERSION}", style="Hint.TLabel").pack(side="left", padx=10)
        create_standard_button(self.header, "Datenbankordner", lambda: open_path(str(DATA_DIR))).pack(side="right", padx=8)
        body = ttk.Frame(self); body.pack(fill="both", expand=True, padx=6, pady=3)
        self.sidebar = ttk.Frame(body, style="Card.TFrame"); self.sidebar.pack(side="left", fill="y", padx=(0, 5))
        self.workspace = ttk.Frame(body); self.workspace.pack(side="left", fill="both", expand=True)
        self._build_sidebar()
        self.footer = ttk.Frame(self, style="Card.TFrame"); self.footer.pack(fill="x", padx=6, pady=(3, 6))
        self.status_var = tk.StringVar(value="Bereit.")
        ttk.Label(self.footer, textvariable=self.status_var, style="Hint.TLabel").pack(side="left", padx=12, pady=5)
        ttk.Label(self.footer, text="Mini-Widgets: Änderung vorschlagen · [i] Hilfe", style="Hint.TLabel").pack(side="right", padx=12)

    def _build_sidebar(self):
        for w in self.sidebar.winfo_children(): w.destroy()
        width = 42 if self.sidebar_collapsed else 210
        self.sidebar.configure(width=width)
        self.sidebar.pack_propagate(False)
        arrow = "»" if self.sidebar_collapsed else "«"
        create_standard_button(self.sidebar, arrow, self._toggle_sidebar).pack(fill="x", padx=5, pady=5)
        modules = [("Dashboard", "DB"), ("Stammdaten", "ST"), ("Finanzbuchhaltung", "FB"), ("Debitoren", "DE"), ("Kreditoren", "KR"), ("Zahlungen", "ZA"), ("Reporting", "RE"), ("Audit", "AU"), ("Einstellungen", "EI")]
        self.nav_buttons.clear()
        for name, abbr in modules:
            text = abbr if self.sidebar_collapsed else name
            btn = ttk.Button(self.sidebar, text=text, style="Nav.TButton", command=lambda n=name: self.show_module(n))
            btn.pack(fill="x", padx=5, pady=2)
            self.nav_buttons[name] = btn

    def _toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        save_ui_preference("sidebar_collapsed", "1" if self.sidebar_collapsed else "0")
        self._build_sidebar(); self._update_nav_styles()

    def _update_nav_styles(self):
        for name, btn in self.nav_buttons.items(): btn.configure(style="NavActive.TButton" if name == self.active_module else "Nav.TButton")

    def set_status(self, msg: str):
        self.status_var.set(msg)

    def show_module(self, module: str):
        self.active_module = module; self._update_nav_styles()
        for w in self.workspace.winfo_children(): w.destroy()
        title = ttk.Label(self.workspace, text=module, style="CardTitle.TLabel"); title.pack(anchor="w", pady=(0, 6))
        container = ttk.Frame(self.workspace); container.pack(fill="both", expand=True)
        render = {
            "Dashboard": self._render_dashboard,
            "Stammdaten": self._render_stammdaten,
            "Finanzbuchhaltung": self._render_finanzbuchhaltung,
            "Debitoren": self._render_debitoren,
            "Kreditoren": self._render_kreditoren,
            "Zahlungen": self._render_zahlungen,
            "Reporting": self._render_reporting,
            "Audit": self._render_audit,
            "Einstellungen": self._render_einstellungen,
        }.get(module, self._render_dashboard)
        render(container); self.set_status(f"Modul {module} geladen.")

    def _card(self, parent, title, body):
        f = ttk.Frame(parent, style="Card.TFrame"); f.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Label(f, text=title, style="Section.TLabel").pack(anchor="w", padx=12, pady=(10, 4))
        ttk.Label(f, text=body, style="Hint.TLabel", wraplength=520).pack(anchor="nw", padx=12, pady=(0, 12))
        return f

    def _render_dashboard(self, parent):
        grid = ttk.Frame(parent); grid.pack(fill="both", expand=True)
        for i in range(2): grid.columnconfigure(i, weight=1); grid.rowconfigure(i, weight=1)
        for idx, (title, text) in enumerate([
            ("Systemstatus", "Alle Kernmodule sind über die Sidebar erreichbar. SQLite wird lokal initialisiert."),
            ("Offene Posten", "Debitoren- und Kreditoren-OPs werden nach Fälligkeit farblich gekennzeichnet."),
            ("Dokumentenstapel", "Kreditorenimporte mit Hist.-Nr., Markierung, Bulk-Löschung, Merge und Vorschau."),
            ("Nächste Ausbaustufe", "Zahlungen, Reporting und Audit sind als funktionsfähige Vorbereitungsflächen angelegt."),
        ]):
            f = ttk.Frame(grid, style="Card.TFrame"); f.grid(row=idx//2, column=idx%2, sticky="nsew", padx=6, pady=6)
            ttk.Label(f, text=title, style="Section.TLabel").pack(anchor="w", padx=12, pady=10)
            ttk.Label(f, text=text, style="Hint.TLabel", wraplength=520).pack(anchor="nw", padx=12, pady=4)

    def _render_stammdaten(self, parent): StammdatenView(parent, self).pack(fill="both", expand=True)
    def _render_finanzbuchhaltung(self, parent): JournalView(parent, self).pack(fill="both", expand=True)
    def _render_debitoren(self, parent): DebitorsView(parent, self).pack(fill="both", expand=True)
    def _render_kreditoren(self, parent): CreditorsView(parent, self).pack(fill="both", expand=True)

    def _render_zahlungen(self, parent):
        shell = build_two_block_shell(parent, "Zahlungserfassung / OP-Ausgleich", "Vorbereitung Zahlungsläufe")
        ttk.Label(shell.left, text="Teilzahlungen, Vollausgleich und OP-Abgleich sind im Datenmodell vorbereitet.\nDie OP-Tabellen aus Debitoren/Kreditoren dienen als Grundlage für Block 7.", style="Hint.TLabel", wraplength=650).pack(anchor="nw", padx=12, pady=12)
        ttk.Label(shell.right, text="Workflow-Platzhalter für spätere Zahlungsläufe, Zuordnungsvorschläge und Statuswechsel.", style="Hint.TLabel", wraplength=420).pack(anchor="nw", padx=12, pady=12)

    def _render_reporting(self, parent):
        shell = build_two_block_shell(parent, "Standardberichte", "Kennzahlen")
        with get_connection() as con:
            counts = {"Debitorenrechnungen": con.execute("SELECT COUNT(*) FROM customer_invoices").fetchone()[0], "Kreditorenrechnungen": con.execute("SELECT COUNT(*) FROM vendor_invoices").fetchone()[0], "Offene Posten": con.execute("SELECT COUNT(*) FROM open_items WHERE open_amount>0").fetchone()[0], "Buchungen": con.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]}
        for k, v in counts.items(): ttk.Label(shell.left, text=f"{k}: {v}", style="Hint.TLabel").pack(anchor="w", padx=12, pady=4)
        ttk.Label(shell.right, text="Periodenfilter, Druck und Exportpfade sind als Zielarchitektur vorgesehen.", style="Hint.TLabel", wraplength=420).pack(anchor="nw", padx=12, pady=12)

    def _render_audit(self, parent):
        self._card(parent, "Audit / Kontrollpfade", "Änderungshistorien, Kontrollpfade, Berechtigungsoptionen und Compliance-Prüfungen sind als eigene Ausbauschicht vorbereitet. Revisionsrelevante Zeitstempel werden bereits in den Kerntabellen geführt.")

    def _render_einstellungen(self, parent):
        shell = build_two_block_shell(parent, "Systemparameter", "UI-Präferenzen")
        ttk.Label(shell.left, text=f"Datenbank: {DB_PATH}\nAnhänge: {ATTACHMENTS_DIR}\nImporte: {IMPORTS_DIR}\nVersion: {APP_VERSION}", style="Hint.TLabel", wraplength=700).pack(anchor="nw", padx=12, pady=12)
        create_standard_button(shell.left, "SQLite initialisieren / prüfen", lambda: (init_sqlite(), self.set_status("SQLite geprüft.")), confirm=True).pack(anchor="w", padx=12, pady=6)
        ttk.Label(shell.right, text=f"Sidebar kollabiert: {'Ja' if self.sidebar_collapsed else 'Nein'}\nDesignstandard: {STANDARD_DESIGN_NAME}", style="Hint.TLabel").pack(anchor="nw", padx=12, pady=12)


def maximize_window(root: tk.Tk) -> None:
    try: root.state("zoomed")
    except Exception: pass


def main() -> None:
    app = FinanceMateApp()
    app.mainloop()


if __name__ == "__main__":
    main()

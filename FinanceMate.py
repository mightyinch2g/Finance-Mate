import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Dict

APP_NAME = "Finance Mate"
APP_VERSION = "0.2.0"
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


def ensure_directories() -> None:
    (BASE_DIR / "data").mkdir(exist_ok=True)
    (BASE_DIR / "assets").mkdir(exist_ok=True)
    (BASE_DIR / "docs").mkdir(exist_ok=True)
    (BASE_DIR / "tests").mkdir(exist_ok=True)


def init_sqlite() -> None:
    conn = sqlite3.connect(DB_PATH)
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
        conn.commit()
    finally:
        conn.close()


class FinanceMateApp(tk.Tk):
    def __init__(self, config: AppConfig | None = None):
        super().__init__()
        self.config_obj = config or AppConfig()
        self.title(f"{self.config_obj.title} {self.config_obj.version}")
        self.geometry(f"{self.config_obj.width}x{self.config_obj.height}")
        self.minsize(1220, 760)
        self.configure(bg=BG)

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
        style.map(
            "Nav.TButton",
            background=[("active", "#F4F7FA"), ("pressed", "#E7EEF5")],
        )
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
        style.map(
            "NavActive.TButton",
            background=[("active", "#EAF1F8"), ("pressed", "#EAF1F8")],
        )
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

        tk.Label(
            title_wrap,
            text=APP_NAME,
            bg=HEADER,
            fg=BLUE,
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_wrap,
            text="Startarchitektur v0.1 – eigenständig, Desktop, SQLite-ready",
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
        self.sidebar_frame = tk.Frame(
            self,
            bg=BG,
            width=SIDEBAR_WIDTH,
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        tk.Label(
            self.sidebar_frame,
            text="Module",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=18, pady=(18, 10))

        tk.Label(
            self.sidebar_frame,
            text="Finance-Mate-Startnavigation",
            bg=BG,
            fg=TEXT2,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=18, pady=(0, 12))

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
        self.path_label = tk.Label(
            self.path_bar,
            text="Finance Mate  >  Dashboard",
            bg=BG,
            fg=TEXT2,
            font=("Segoe UI", 9),
        )
        self.path_label.pack(anchor="w")

        self.content_frame = tk.Frame(self.workspace_frame, bg=BG)
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=(6, 12))
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

    def _build_footer(self) -> None:
        self.footer_frame = tk.Frame(
            self,
            bg=HEADER,
            height=FOOTER_HEIGHT,
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.footer_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.footer_frame.grid_propagate(False)

        self.status_label = tk.Label(
            self.footer_frame,
            text=f"{APP_NAME} {APP_VERSION}  |  Datenbank: SQLite  |  Projektpfad: {BASE_DIR}",
            bg=HEADER,
            fg=TEXT2,
            font=("Segoe UI", 8),
        )
        self.status_label.pack(side="left", padx=14)

    def show_module(self, module_name: str) -> None:
        self.active_module.set(module_name)
        self.path_label.config(text=f"Finance Mate  >  {module_name}")
        self.status_label.config(text=f"{APP_NAME} {APP_VERSION}  |  Modul: {module_name}  |  Datenbank: SQLite")

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
        self._card(wrapper, 0, 0, "Systemstart", "Neues Projektgerüst für Finance Mate. SQLite ist aktiv vorbereitet; PostgreSQL folgt später.")
        self._card(wrapper, 0, 1, "Layoutbasis", "Optik an FiBu Mate angelehnt, aber mit kleinerer Kopfzeile, kleinerer Fußzeile und ohne Logos.")
        self._card(wrapper, 1, 0, "Nächste Coding-Blöcke", "1) Stammdaten\n2) Journalbuchungen\n3) Debitoren/Kreditoren\n4) Reporting")
        self._card(wrapper, 1, 1, "Projektstatus", "Start bei 0 Nutzern. Zielarchitektur vorbereitet für späteren Multiuser-Betrieb mit PostgreSQL.")

    def _render_stammdaten(self) -> None:
        frame = self._create_single_area("Stammdaten", "Hier bauen wir als Nächstes Sachkonten, Debitoren, Kreditoren, Steuerkennzeichen und Zahlungsbedingungen auf.")
        self._list_block(frame, [
            "Sachkonten",
            "Debitoren",
            "Kreditoren",
            "Steuerkennzeichen",
            "Zahlungsbedingungen",
            "Bankkonten",
        ])

    def _render_finanzbuchhaltung(self) -> None:
        frame = self._create_single_area("Finanzbuchhaltung", "Geplant für Block 3/4: Journalbuchungen, Buchungsvalidierung, Soll/Haben-Logik, Belegnummern und Storno.")
        self._list_block(frame, [
            "Journalbuchung",
            "Buchungssätze",
            "Beleglogik",
            "Periodenprüfung",
            "Buchungshistorie",
        ])

    def _render_debitoren(self) -> None:
        frame = self._create_single_area("Debitoren", "Hier entsteht die Forderungslogik: Ausgangsrechnungen, offene Posten, Zahlungseingänge und Ausgleich.")
        self._list_block(frame, [
            "Ausgangsrechnungen",
            "Offene Posten",
            "Zahlungseingänge",
            "Teilzahlungen",
            "Mahnstatus-Basis",
        ])

    def _render_kreditoren(self) -> None:
        frame = self._create_single_area("Kreditoren", "Hier entsteht die Verbindlichkeitenlogik: Eingangsrechnungen, Fälligkeiten, Zahlungen und Ausgleich.")
        self._list_block(frame, [
            "Eingangsrechnungen",
            "Offene Posten",
            "Fälligkeitsübersicht",
            "Zahlungsausgang",
            "Ausgleich",
        ])

    def _render_zahlungen(self) -> None:
        frame = self._create_single_area("Zahlungen", "Für v0.1 zunächst schlank: manuelle Zahlungsbuchung, Zuordnung zu offenen Posten und einfache Kontenabstimmung.")
        self._list_block(frame, [
            "Bankkonten",
            "Manuelle Zahlungen",
            "OP-Zuordnung",
            "Kontenabstimmung",
            "später: Bankimport / PostgreSQL-Betrieb",
        ])

    def _render_reporting(self) -> None:
        frame = self._create_single_area("Reporting", "Die ersten Standardberichte werden auf diesem Bereich aufsetzen.")
        self._list_block(frame, [
            "Saldenliste",
            "Kontoblatt",
            "OP-Liste Debitoren",
            "OP-Liste Kreditoren",
            "Fälligkeitsreport",
            "Buchungsjournal",
        ])

    def _render_audit(self) -> None:
        frame = self._create_single_area("Audit", "Von Anfang an vorgesehen: Nachvollziehbarkeit von Änderungen, Statuswechseln und späteren Freigaben.")
        self._list_block(frame, [
            "Änderungsprotokoll",
            "Benutzerhistorie",
            "Statuswechsel",
            "Freigabeverlauf (später)",
        ])

    def _render_einstellungen(self) -> None:
        frame = self._create_single_area("Einstellungen", "Grundkonfiguration für Finance Mate – zunächst nur als Platzhalterbereich.")
        self._list_block(frame, [
            "Mandant/Firma (Single-Company Start)",
            "Systemparameter",
            "Nummernkreise",
            "Datenbankmodus: SQLite",
            "später: PostgreSQL-Umschaltung",
        ])

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

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from pathlib import Path
import sqlite3

APP_NAME = "Finance Mate"
APP_VERSION = "0.1.0"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "finance_mate.db"

# Farbschema angelehnt an FiBu Mate – ohne Logos, mit kleinerer Kopf- und Fußzeile.
BLUE = "#004B93"
RED = "#E30613"
BG = "#E8EEF5"
HEADER = "#D3DEE9"
LINE = "#91A3B5"
TEXT = "#182431"
TEXT2 = "#445364"
WHITE = "#FFFFFF"
TILE_BG = "#D6DCE4"

HEADER_HEIGHT = 72   # bewusst kleiner als in FiBu Mate
FOOTER_HEIGHT = 26   # bewusst kleiner als in FiBu Mate
SIDEBAR_WIDTH = 260


@dataclass(frozen=True)
class AppConfig:
    title: str = APP_NAME
    version: str = APP_VERSION
    width: int = 1440
    height: int = 900


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
        self.minsize(1200, 760)
        self.configure(bg=BG)

        self._configure_ttk()
        self._build_layout()
        self._build_header()
        self._build_sidebar()
        self._build_workspace()
        self._build_footer()

    def _configure_ttk(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Nav.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 10), foreground=TEXT)
        style.configure("Card.TFrame", background=WHITE)
        style.configure("CardTitle.TLabel", background=WHITE, foreground=TEXT, font=("Segoe UI", 12, "bold"))
        style.configure("CardBody.TLabel", background=WHITE, foreground=TEXT2, font=("Segoe UI", 10))

    def _build_layout(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

    def _build_header(self) -> None:
        self.header_frame = tk.Frame(self, bg=HEADER, height=HEADER_HEIGHT, highlightthickness=1, highlightbackground=LINE)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)

        title_wrap = tk.Frame(self.header_frame, bg=HEADER)
        title_wrap.grid(row=0, column=0, sticky="w", padx=20)

        tk.Label(
            title_wrap,
            text=APP_NAME,
            bg=HEADER,
            fg=BLUE,
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_wrap,
            text="ERP-/Finance-Light für KMU – Startarchitektur v0.1",
            bg=HEADER,
            fg=TEXT2,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 2))

        widget_bar = tk.Frame(self.header_frame, bg=HEADER)
        widget_bar.grid(row=0, column=1, sticky="e", padx=(10, 20))

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

        nav_title = tk.Label(
            self.sidebar_frame,
            text="Module",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        )
        nav_title.pack(anchor="w", padx=18, pady=(18, 12))

        modules = [
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
        for name in modules:
            ttk.Button(self.sidebar_frame, text=name, style="Nav.TButton").pack(fill="x", padx=14, pady=4)

    def _build_workspace(self) -> None:
        self.workspace_frame = tk.Frame(self, bg=BG)
        self.workspace_frame.grid(row=1, column=1, sticky="nsew")
        self.workspace_frame.grid_rowconfigure(1, weight=1)
        self.workspace_frame.grid_columnconfigure(0, weight=1)

        path_bar = tk.Frame(self.workspace_frame, bg=BG)
        path_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 6))
        tk.Label(
            path_bar,
            text="Finance Mate  >  Dashboard",
            bg=BG,
            fg=TEXT2,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        content = tk.Frame(self.workspace_frame, bg=BG)
        content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(6, 12))
        for idx in range(2):
            content.grid_columnconfigure(idx, weight=1, uniform="cards")
            content.grid_rowconfigure(idx, weight=1, uniform="cards")

        self._card(
            content,
            0,
            0,
            "Systemstart",
            "Neues Projektgerüst für Finance Mate. SQLite ist aktiv vorbereitet; PostgreSQL folgt in einer späteren Ausbaustufe.",
        )
        self._card(
            content,
            0,
            1,
            "Layoutbasis",
            "Optik an FiBu Mate angelehnt, aber mit kleinerer Kopfzeile, kleinerer Fußzeile und ohne Logos.",
        )
        self._card(
            content,
            1,
            0,
            "Nächste Coding-Blöcke",
            "1) Projektstruktur\n2) Datenbank-Schicht\n3) Stammdaten\n4) Journalbuchungen",
        )
        self._card(
            content,
            1,
            1,
            "Projektstatus",
            "Start bei 0 Nutzern. Zielarchitektur vorbereitet für späteren Multiuser-Betrieb mit PostgreSQL.",
        )

    def _card(self, parent: tk.Widget, row: int, column: int, title: str, body: str) -> None:
        outer = tk.Frame(parent, bg=LINE, bd=0, highlightthickness=0)
        outer.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
        inner = ttk.Frame(outer, style="Card.TFrame", padding=16)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        ttk.Label(inner, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(inner, text=body, style="CardBody.TLabel", wraplength=420, justify="left").pack(anchor="w", pady=(8, 0))

    def _build_footer(self) -> None:
        self.footer_frame = tk.Frame(self, bg=HEADER, height=FOOTER_HEIGHT, highlightthickness=1, highlightbackground=LINE)
        self.footer_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.footer_frame.grid_propagate(False)
        tk.Label(
            self.footer_frame,
            text=f"{APP_NAME} {APP_VERSION}  |  Datenbank: SQLite  |  Projektpfad: {BASE_DIR}",
            bg=HEADER,
            fg=TEXT2,
            font=("Segoe UI", 8),
        ).pack(side="left", padx=14)


def main() -> None:
    ensure_directories()
    init_sqlite()
    app = FinanceMateApp()
    app.mainloop()


if __name__ == "__main__":
    main()

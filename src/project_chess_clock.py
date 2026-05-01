"""
Tk Tariff Tracker
=================

A small Tkinter desktop app for tracking project support-hour tariffs.

- One CSV ledger per project in ./projects/
- Time is stored internally as seconds
- Display uses HH:MM:SS
- Session use is logged when a timer is stopped
- Adjustments require a reason
- Corrections are logged as new rows rather than silently overwriting history

Run:
    python tk_tariff_tracker_app_v5.py
"""

from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Optional

from tkinter import messagebox

def show_about():
    messagebox.showinfo(
        "About Tariff Clock",
        "Tariff Clock v0.1.0\n\n"
        "A lightweight project time tracker with fixed tariffs.\n\n"
        "Data stored locally:\n~/Documents/tariff_clock_projects\n\n"
        "Chrissy Roberts\nLSHTM Global Health Analytics"
    )
    
APP_NAME = "Tariff Clock"
APP_VERSION = "0.1.0"
APP_TITLE = f"{APP_NAME} v{APP_VERSION}"

PROJECTS_DIR = Path.home() / "Documents" / "tariff_clock_projects"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
FIELDNAMES = [
    "timestamp",
    "event",
    "delta_seconds",
    "balance_seconds",
    "session_start",
    "session_end",
    "reason",
    "edited",
    "edit_reason",
]


def now_str() -> str:
    return datetime.now().strftime(DATETIME_FORMAT)


def seconds_to_hhmmss(seconds: int) -> str:
    sign = "-" if seconds < 0 else ""
    seconds = abs(int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{sign}{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_hhmmss(value: str) -> int:
    value = value.strip()
    if not value:
        raise ValueError("No time value supplied")
    if re.fullmatch(r"\d+(\.\d+)?", value):
        return int(float(value) * 3600)
    parts = value.split(":")
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
    elif len(parts) == 2:
        hours, minutes = map(int, parts)
        seconds = 0
    else:
        raise ValueError("Use HH:MM:SS, HH:MM, or decimal hours")
    return hours * 3600 + minutes * 60 + seconds


def safe_project_filename(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("Project name cannot be blank")
    safe = re.sub(r"[^A-Za-z0-9 _.-]", "_", name)
    safe = re.sub(r"\s+", " ", safe).strip()
    if not safe:
        raise ValueError("Project name does not contain usable characters")
    return f"{safe}.csv"


@dataclass
class LedgerRow:
    timestamp: str
    event: str
    delta_seconds: int
    balance_seconds: int
    session_start: str = ""
    session_end: str = ""
    reason: str = ""
    edited: str = "false"
    edit_reason: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "event": self.event,
            "delta_seconds": str(int(self.delta_seconds)),
            "balance_seconds": str(int(self.balance_seconds)),
            "session_start": self.session_start,
            "session_end": self.session_end,
            "reason": self.reason,
            "edited": self.edited,
            "edit_reason": self.edit_reason,
        }


class ProjectLedger:
    def __init__(self, path: Path):
        self.path = path
        self.name = self.path.stem
        self.ensure_exists()

    def ensure_exists(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()

    @classmethod
    def create(cls, name: str, initial_seconds: int) -> "ProjectLedger":
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        path = PROJECTS_DIR / safe_project_filename(name)
        if path.exists():
            raise FileExistsError(f"Project already exists: {path.stem}")
        ledger = cls(path)
        ledger.append_initial_allocation(initial_seconds, reason="Initial tariff allocation")
        return ledger

    def read_rows(self) -> list[dict[str, str]]:
        self.ensure_exists()
        with self.path.open("r", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return [{field: row.get(field, "") for field in FIELDNAMES} for row in rows]

    def current_balance(self) -> int:
        rows = self.read_rows()
        if not rows:
            return 0
        try:
            return int(rows[-1].get("balance_seconds") or 0)
        except ValueError:
            return self.recalculate_balance_from_deltas()

    def recalculate_balance_from_deltas(self) -> int:
        total = 0
        for row in self.read_rows():
            try:
                total += int(row.get("delta_seconds") or 0)
            except ValueError:
                continue
        return total

    def append_row(self, row: LedgerRow) -> None:
        self.ensure_exists()
        with self.path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row.as_dict())

    def append_initial_allocation(self, seconds: int, reason: str) -> None:
        balance = self.current_balance() + seconds
        self.append_row(LedgerRow(now_str(), "initial_allocation", seconds, balance, reason=reason))

    def append_session(self, start_time: datetime, end_time: datetime, reason: str = "") -> int:
        elapsed = max(0, int((end_time - start_time).total_seconds()))
        balance = self.current_balance() - elapsed
        self.append_row(
            LedgerRow(
                timestamp=now_str(),
                event="session",
                delta_seconds=-elapsed,
                balance_seconds=balance,
                session_start=start_time.strftime(DATETIME_FORMAT),
                session_end=end_time.strftime(DATETIME_FORMAT),
                reason=reason.strip(),
            )
        )
        return elapsed

    def append_adjustment(self, seconds: int, reason: str) -> None:
        if not reason.strip():
            raise ValueError("Adjustment reason is required")
        balance = self.current_balance() + seconds
        self.append_row(LedgerRow(now_str(), "adjustment", seconds, balance, reason=reason.strip()))

    def append_correction(self, seconds: int, reason: str, original_row_summary: str = "") -> None:
        if not reason.strip():
            raise ValueError("Correction reason is required")
        balance = self.current_balance() + seconds
        edit_reason = reason.strip()
        if original_row_summary:
            edit_reason = f"{edit_reason} | Related row: {original_row_summary}"
        self.append_row(
            LedgerRow(
                timestamp=now_str(),
                event="correction",
                delta_seconds=seconds,
                balance_seconds=balance,
                reason=reason.strip(),
                edited="true",
                edit_reason=edit_reason,
            )
        )


class TariffTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self._build_menu()
        self.geometry("980x600")
        self.minsize(820, 460)
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

        self.ledgers: dict[str, ProjectLedger] = {}
        self.project_rows: dict[str, dict[str, object]] = {}
        self.selected_project: Optional[str] = None
        self.running_project: Optional[str] = None
        self.running_start_time: Optional[datetime] = None
        self.running_display_balance: Optional[int] = None
        self.timer_job: Optional[str] = None

        self.timer_font = ("Menlo", 13, "bold")
        self.small_timer_font = ("Menlo", 11)
        self.running_bg = "#dff3e3"
        self.selected_bg = "#e8f0fe"
        self.default_bg = "#f7f7f7"

        style = ttk.Style()
        style.configure("Tiny.TButton", padding=(0, 0), font=("TkDefaultFont", 8))

        self._build_ui()
        self._bind_global_scrolling()
        self.load_projects()
        self.render_project_rows()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        app_menu = tk.Menu(menubar, tearoff=0)
        app_menu.add_command(label="About Tariff Clock", command=show_about)
        app_menu.add_separator()
        app_menu.add_command(label="Quit", command=self.on_close)
        menubar.add_cascade(label="Tariff Clock", menu=app_menu)
        self.config(menu=menubar)
        
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self, padding=(8, 6))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(4, weight=1)
        ttk.Button(toolbar, text="New project", width=12, command=self.create_project_dialog).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(toolbar, text="Refresh", width=9, command=self.refresh_all).grid(row=0, column=1, padx=(0, 4))
        ttk.Button(toolbar, text="Open folder", width=11, command=self.open_projects_folder).grid(row=0, column=2, padx=(0, 4))
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(toolbar, textvariable=self.status_var, anchor="e").grid(row=0, column=4, sticky="ew")

        self.main_pane = ttk.PanedWindow(self, orient="vertical")
        self.main_pane.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        project_panel = ttk.Frame(self.main_pane, padding=(0, 0, 0, 6))
        project_panel.columnconfigure(0, weight=1)
        project_panel.rowconfigure(1, weight=1)
        self.main_pane.add(project_panel, weight=1)
        ttk.Label(project_panel, text="Projects", font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.project_canvas = tk.Canvas(project_panel, highlightthickness=0, height=185)
        self.project_scrollbar = ttk.Scrollbar(project_panel, orient="vertical", command=self.project_canvas.yview)
        self.project_frame = ttk.Frame(self.project_canvas)
        self.project_frame.bind("<Configure>", lambda e: self.project_canvas.configure(scrollregion=self.project_canvas.bbox("all")))
        self.project_canvas_window = self.project_canvas.create_window((0, 0), window=self.project_frame, anchor="nw")
        self.project_canvas.configure(yscrollcommand=self.project_scrollbar.set)
        self.project_canvas.grid(row=1, column=0, sticky="nsew")
        self.project_scrollbar.grid(row=1, column=1, sticky="ns")
        self.project_canvas.bind("<Configure>", lambda e: self.project_canvas.itemconfigure(self.project_canvas_window, width=e.width))

        history_panel = ttk.Frame(self.main_pane, padding=(0, 6, 0, 0))
        history_panel.columnconfigure(0, weight=1)
        history_panel.rowconfigure(1, weight=1)
        self.main_pane.add(history_panel, weight=3)

        history_header = ttk.Frame(history_panel)
        history_header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        history_header.columnconfigure(0, weight=1)
        self.history_title_var = tk.StringVar(value="Project log")
        ttk.Label(history_header, textvariable=self.history_title_var, font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Button(history_header, text="Add correction", width=14, command=self.add_correction_dialog).grid(row=0, column=1, sticky="e")

        columns = ("timestamp", "event", "delta", "balance", "session_start", "session_end", "reason")
        self.history_tree = ttk.Treeview(history_panel, columns=columns, show="headings", height=10)
        config = [
            ("timestamp", "Timestamp", 135, "w"),
            ("event", "Event", 105, "w"),
            ("delta", "Delta", 80, "e"),
            ("balance", "Balance", 90, "e"),
            ("session_start", "Session start", 135, "w"),
            ("session_end", "Session end", 135, "w"),
            ("reason", "Reason", 360, "w"),
        ]
        for col, label, width, anchor in config:
            self.history_tree.heading(col, text=label)
            self.history_tree.column(col, width=width, anchor=anchor, stretch=(col == "reason"))

        hist_scroll_y = ttk.Scrollbar(history_panel, orient="vertical", command=self.history_tree.yview)
        hist_scroll_x = ttk.Scrollbar(history_panel, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=hist_scroll_y.set, xscrollcommand=hist_scroll_x.set)
        self.history_tree.grid(row=1, column=0, sticky="nsew")
        hist_scroll_y.grid(row=1, column=1, sticky="ns")
        hist_scroll_x.grid(row=2, column=0, sticky="ew")


    def _bind_global_scrolling(self) -> None:
        """Make mouse-wheel scrolling work across the main window.

        Tkinter does not automatically route mouse-wheel events to the nearest
        scrollable container. This binding captures wheel movement at the app
        level and sends it to the project list or the project log depending on
        where the pointer is.
        """
        self.bind_all("<MouseWheel>", self._on_mousewheel)      # macOS / Windows
        self.bind_all("<Button-4>", self._on_mousewheel_linux)  # Linux wheel up
        self.bind_all("<Button-5>", self._on_mousewheel_linux)  # Linux wheel down

    def _pointer_is_over(self, widget: tk.Widget) -> bool:
        """Return True when the mouse pointer is over widget or one of its children."""
        pointer_x, pointer_y = self.winfo_pointerxy()
        target = self.winfo_containing(pointer_x, pointer_y)
        return target is not None and str(target).startswith(str(widget))

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Route macOS/Windows mouse-wheel events to the appropriate scroller."""
        raw_delta = getattr(event, "delta", 0)
        if raw_delta == 0:
            return

        # Windows normally reports +/-120. macOS often reports small integers.
        if abs(raw_delta) >= 120:
            units = int(-raw_delta / 120)
        else:
            units = -1 if raw_delta > 0 else 1

        if self._pointer_is_over(self.history_tree):
            self.history_tree.yview_scroll(units, "units")
        else:
            self.project_canvas.yview_scroll(units, "units")

    def _on_mousewheel_linux(self, event: tk.Event) -> None:
        """Route Linux mouse-wheel events to the appropriate scroller."""
        units = -1 if getattr(event, "num", None) == 4 else 1
        if self._pointer_is_over(self.history_tree):
            self.history_tree.yview_scroll(units, "units")
        else:
            self.project_canvas.yview_scroll(units, "units")

    def load_projects(self) -> None:
        self.ledgers.clear()
        for path in sorted(PROJECTS_DIR.glob("*.csv"), key=lambda p: p.stem.lower()):
            ledger = ProjectLedger(path)
            self.ledgers[ledger.name] = ledger

    def render_project_rows(self) -> None:
        for child in self.project_frame.winfo_children():
            child.destroy()
        self.project_rows.clear()

        headers = ["Project", "Start/Stop", "+1/-1 h", "+1/-1 m", "Remaining", "Session"]
        header_widths = [28, 7, 8, 8, 14, 14]
        for col, (header, width) in enumerate(zip(headers, header_widths)):
            tk.Label(
                self.project_frame,
                text=header,
                font=("TkDefaultFont", 9, "bold"),
                anchor="w" if col < 4 else "e",
                width=width,
                bg=self.project_canvas.cget("background"),
            ).grid(row=0, column=col, sticky="ew", padx=3, pady=(0, 4))

        for col, weight in enumerate([3, 0, 0, 0, 1, 1]):
            self.project_frame.columnconfigure(col, weight=weight)

        if not self.ledgers:
            ttk.Label(self.project_frame, text="No projects yet. Click 'New project' to create one.", foreground="gray").grid(row=1, column=0, columnspan=len(headers), sticky="w", padx=4, pady=10)
            return

        for row_index, project_name in enumerate(sorted(self.ledgers, key=str.lower), start=1):
            ledger = self.ledgers[project_name]
            balance_var = tk.StringVar(value=seconds_to_hhmmss(ledger.current_balance()))
            session_var = tk.StringVar(value="00:00:00")

            name_label = tk.Label(
                self.project_frame,
                text=project_name,
                cursor="hand2",
                anchor="w",
                bg=self.default_bg,
                font=("TkDefaultFont", 10),
                padx=6,
                pady=5,
            )
            name_label.grid(row=row_index, column=0, sticky="ew", padx=(2, 1), pady=2)
            name_label.bind("<Button-1>", lambda e, name=project_name: self.select_project(name))

            control_frame = tk.Frame(self.project_frame, bg=self.default_bg, padx=0, pady=1)
            control_frame.grid(row=row_index, column=1, sticky="ew", padx=1, pady=2)
            start_button = ttk.Button(control_frame, text="▶", width=1, style="Tiny.TButton", command=lambda name=project_name: self.start_timer(name))
            stop_button = ttk.Button(control_frame, text="■", width=1, style="Tiny.TButton", command=lambda name=project_name: self.stop_timer(name))
            start_button.grid(row=0, column=0, padx=(0, 0))
            stop_button.grid(row=0, column=1, padx=(1, 0))
            stop_button.state(["disabled"])

            hour_frame = tk.Frame(self.project_frame, bg=self.default_bg, padx=0, pady=1)
            hour_frame.grid(row=row_index, column=2, sticky="ew", padx=1, pady=2)
            ttk.Button(hour_frame, text="+1h", width=2, style="Tiny.TButton", command=lambda name=project_name: self.adjust_time_dialog(name, 3600)).grid(row=0, column=0, padx=(0, 0))
            ttk.Button(hour_frame, text="-1h", width=2, style="Tiny.TButton", command=lambda name=project_name: self.adjust_time_dialog(name, -3600)).grid(row=0, column=1, padx=(1, 0))

            minute_frame = tk.Frame(self.project_frame, bg=self.default_bg, padx=0, pady=1)
            minute_frame.grid(row=row_index, column=3, sticky="ew", padx=1, pady=2)
            ttk.Button(minute_frame, text="+1m", width=2, style="Tiny.TButton", command=lambda name=project_name: self.adjust_time_dialog(name, 60)).grid(row=0, column=0, padx=(0, 0))
            ttk.Button(minute_frame, text="-1m", width=2, style="Tiny.TButton", command=lambda name=project_name: self.adjust_time_dialog(name, -60)).grid(row=0, column=1, padx=(1, 0))

            balance_label = tk.Label(
                self.project_frame,
                textvariable=balance_var,
                anchor="e",
                bg=self.default_bg,
                font=self.timer_font,
                padx=6,
                pady=5,
            )
            balance_label.grid(row=row_index, column=4, sticky="ew", padx=1, pady=2)

            session_label = tk.Label(
                self.project_frame,
                textvariable=session_var,
                anchor="e",
                bg=self.default_bg,
                font=self.small_timer_font,
                padx=6,
                pady=5,
            )
            session_label.grid(row=row_index, column=5, sticky="ew", padx=(1, 2), pady=2)

            self.project_rows[project_name] = {
                "balance_var": balance_var,
                "session_var": session_var,
                "start_button": start_button,
                "stop_button": stop_button,
                "name_label": name_label,
                "control_frame": control_frame,
                "hour_frame": hour_frame,
                "minute_frame": minute_frame,
                "balance_label": balance_label,
                "session_label": session_label,
            }

        next_project = self.selected_project if self.selected_project in self.ledgers else sorted(self.ledgers, key=str.lower)[0]
        self.select_project(next_project)
        self.apply_row_styles()

    def apply_row_styles(self) -> None:
        for name, widgets in self.project_rows.items():
            if name == self.running_project:
                bg = self.running_bg
                name_font = ("TkDefaultFont", 11, "bold")
                timer_font = ("Menlo", 15, "bold")
                relief = "solid"
                border = 2
            elif name == self.selected_project:
                bg = self.selected_bg
                name_font = ("TkDefaultFont", 10, "bold")
                timer_font = self.timer_font
                relief = "solid"
                border = 1
            else:
                bg = self.default_bg
                name_font = ("TkDefaultFont", 10)
                timer_font = self.timer_font
                relief = "flat"
                border = 0

            for key in ("name_label", "control_frame", "hour_frame", "minute_frame", "balance_label", "session_label"):
                widget = widgets.get(key)
                if widget:
                    widget.configure(bg=bg)
            widgets["name_label"].configure(font=name_font, relief=relief, bd=border)
            widgets["balance_label"].configure(font=timer_font, relief=relief, bd=border)
            widgets["session_label"].configure(relief=relief, bd=border)

    def refresh_all(self) -> None:
        if self.running_project:
            messagebox.showwarning("Timer running", "Stop the running timer before refreshing.")
            return
        self.load_projects()
        self.render_project_rows()
        self.status_var.set("Refreshed")

    def update_project_balance_display(self, project_name: str, seconds: int) -> None:
        row = self.project_rows.get(project_name)
        if row:
            row["balance_var"].set(seconds_to_hhmmss(seconds))

    def update_project_session_display(self, project_name: str, seconds: int) -> None:
        row = self.project_rows.get(project_name)
        if row:
            row["session_var"].set(seconds_to_hhmmss(seconds))

    def select_project(self, project_name: str) -> None:
        self.selected_project = project_name
        self.history_title_var.set(f"Project log: {project_name}")
        self.apply_row_styles()
        self.load_history(project_name)

    def load_history(self, project_name: str) -> None:
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        ledger = self.ledgers.get(project_name)
        if not ledger:
            return
        for idx, row in enumerate(ledger.read_rows()):
            try:
                delta = seconds_to_hhmmss(int(row.get("delta_seconds") or 0))
                balance = seconds_to_hhmmss(int(row.get("balance_seconds") or 0))
            except ValueError:
                delta = row.get("delta_seconds", "")
                balance = row.get("balance_seconds", "")
            self.history_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    row.get("timestamp", ""),
                    row.get("event", ""),
                    delta,
                    balance,
                    row.get("session_start", ""),
                    row.get("session_end", ""),
                    row.get("reason", ""),
                ),
            )
        children = self.history_tree.get_children()
        if children:
            self.history_tree.see(children[-1])

    def start_timer(self, project_name: str) -> None:
        if self.running_project == project_name:
            return
        if self.running_project and self.running_project != project_name:
            # Chess-clock behaviour: starting another project stops and logs the current one.
            if not self.stop_timer(self.running_project):
                return
        ledger = self.ledgers[project_name]
        self.running_project = project_name
        self.running_start_time = datetime.now()
        self.running_display_balance = ledger.current_balance()
        self.update_project_session_display(project_name, 0)
        self.project_rows[project_name]["start_button"].state(["disabled"])
        self.project_rows[project_name]["stop_button"].state(["!disabled"])
        self.status_var.set(f"Running: {project_name}")
        self.select_project(project_name)
        self.apply_row_styles()
        self.tick_timer()

    def tick_timer(self) -> None:
        if not self.running_project or not self.running_start_time or self.running_display_balance is None:
            return
        elapsed = int((datetime.now() - self.running_start_time).total_seconds())
        self.update_project_balance_display(self.running_project, self.running_display_balance - elapsed)
        self.update_project_session_display(self.running_project, elapsed)
        self.timer_job = self.after(1000, self.tick_timer)

    def stop_timer(self, project_name: str) -> bool:
        if self.running_project != project_name:
            return False

        start_time = self.running_start_time
        end_time = datetime.now()
        if not start_time:
            return False

        elapsed_preview = seconds_to_hhmmss(max(0, int((end_time - start_time).total_seconds())))
        summary = simpledialog.askstring(
            "Session summary",
            f"Summary of activity for {project_name} ({elapsed_preview}):",
            parent=self,
        )
        if summary is None:
            self.status_var.set("Stop cancelled; timer still running")
            return False

        if self.timer_job:
            self.after_cancel(self.timer_job)
            self.timer_job = None

        self.running_project = None
        self.running_start_time = None
        self.running_display_balance = None

        ledger = self.ledgers[project_name]
        elapsed = ledger.append_session(start_time, end_time, reason=summary)
        self.update_project_balance_display(project_name, ledger.current_balance())
        self.update_project_session_display(project_name, 0)
        self.project_rows[project_name]["start_button"].state(["!disabled"])
        self.project_rows[project_name]["stop_button"].state(["disabled"])
        self.load_history(project_name)
        self.apply_row_styles()
        self.status_var.set(f"Logged {seconds_to_hhmmss(elapsed)} against {project_name}")
        return True

    def create_project_dialog(self) -> None:
        name = simpledialog.askstring("New project", "Project name:", parent=self)
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showerror("Invalid project", "Project name cannot be blank.")
            return
        time_value = simpledialog.askstring("Initial tariff", "Initial time allocation, e.g. 30:00:00 or 30:", parent=self)
        if time_value is None:
            return
        try:
            seconds = parse_hhmmss(time_value)
            ProjectLedger.create(name, seconds)
        except Exception as exc:
            messagebox.showerror("Could not create project", str(exc))
            return
        self.load_projects()
        self.render_project_rows()
        self.select_project(Path(safe_project_filename(name)).stem)
        self.status_var.set(f"Created project: {name}")

    def adjust_time_dialog(self, project_name: str, seconds: int) -> None:
        if self.running_project == project_name:
            messagebox.showwarning("Timer running", "Stop the timer before adjusting this project.")
            return
        label = seconds_to_hhmmss(seconds)
        reason = simpledialog.askstring("Adjustment reason required", f"Reason for adjustment of {label} to {project_name}:", parent=self)
        if reason is None:
            return
        if not reason.strip():
            messagebox.showerror("Reason required", "A reason is required for all adjustments.")
            return
        try:
            ledger = self.ledgers[project_name]
            ledger.append_adjustment(seconds, reason)
            self.update_project_balance_display(project_name, ledger.current_balance())
            self.load_history(project_name)
            self.status_var.set(f"Adjusted {project_name} by {label}")
        except Exception as exc:
            messagebox.showerror("Adjustment failed", str(exc))

    def add_correction_dialog(self) -> None:
        project_name = self.selected_project
        if not project_name:
            messagebox.showwarning("No project selected", "Select a project first.")
            return
        if self.running_project == project_name:
            messagebox.showwarning("Timer running", "Stop the timer before adding a correction.")
            return

        selected = self.history_tree.selection()
        original_summary = ""
        if selected:
            values = self.history_tree.item(selected[0], "values")
            if values:
                original_summary = f"{values[0]} / {values[1]} / delta {values[2]}"

        time_value = simpledialog.askstring(
            "Correction amount",
            "Correction amount to apply. Use + or - HH:MM:SS, e.g. +00:10:00 or -00:05:00:",
            parent=self,
        )
        if time_value is None:
            return
        sign = 1
        cleaned = time_value.strip()
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        elif cleaned.startswith("-"):
            cleaned = cleaned[1:]
            sign = -1
        try:
            seconds = sign * parse_hhmmss(cleaned)
        except ValueError as exc:
            messagebox.showerror("Invalid correction", str(exc))
            return
        reason = simpledialog.askstring("Correction reason required", "Reason for correction:", parent=self)
        if reason is None:
            return
        if not reason.strip():
            messagebox.showerror("Reason required", "A reason is required for all corrections.")
            return
        try:
            ledger = self.ledgers[project_name]
            ledger.append_correction(seconds, reason, original_summary=original_summary)
            self.update_project_balance_display(project_name, ledger.current_balance())
            self.load_history(project_name)
            self.status_var.set(f"Correction added to {project_name}")
        except Exception as exc:
            messagebox.showerror("Correction failed", str(exc))

    def open_projects_folder(self) -> None:
        folder = PROJECTS_DIR.resolve()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(folder)], check=False)
            elif sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception as exc:
            messagebox.showerror("Could not open folder", str(exc))

    def on_close(self) -> None:
        if self.running_project:
            proceed = messagebox.askyesno("Timer running", "Stop and log the running timer before closing?")
            if proceed:
                if not self.stop_timer(self.running_project):
                    return
            else:
                return
        self.destroy()


if __name__ == "__main__":
    app = TariffTrackerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

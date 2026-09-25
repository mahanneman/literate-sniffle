# -*- coding: utf-8 -*-
"""
Firewall Blocker Pro v2.0
Developed by Mahan Neman MA.AD.GH - Python Edition
Requires: Windows + Administrator privileges
"""

import os
import sys
import json
import csv
import time
import ctypes
import tempfile
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ================== Constants ==================
APP_NAME = "Firewall Blocker Pro"
APP_VERSION = "2.0"
CONFIG_FILE = "fw_blocker_config.json"
LOG_FILE = "fw_blocker_log.txt"

PROTOCOLS = ["TCP", "UDP", "ICMPv4", "ICMPv6", "GRE", "IGMP", "ESP", "AH", "ANY", "IP"]
DIRECTIONS = ["out", "in", "both"]

# ================== Helpers ==================
def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def run_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    if script.lower().endswith(".py"):
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{script}" {params}', None, 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", script, params, None, 1)
    sys.exit(0)

def run_netsh(args, timeout=20):
    """Execute netsh silently, return (rc, stdout, stderr)."""
    cmd = ["netsh"] + args
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, startupinfo=si,
            creationflags=0x08000000, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return -1, "", str(e)


# ================== Main Application ==================
class FirewallBlockerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME}  v{APP_VERSION}")
        self.root.geometry("1100x720")
        self.root.minsize(950, 640)

        # State
        self.path_items = []          # list of dict {path, protocol, direction, enabled}
        self.rule_prefix = "Block_App"
        self.dark_mode = True
        self.log_entries = []
        self._context_row = None

        # Colors
        self.colors = self._get_theme_colors(self.dark_mode)

        # Build UI
        self._setup_style()
        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

        # Admin check
        self.root.after(300, self._check_admin_state)
        self.log("Application started", "INFO")

    # ---------- Theme ----------
    def _get_theme_colors(self, dark):
        if dark:
            return dict(
                bg="#0d1117", panel="#161b22", fg="#f0f6fc",
                accent="#ffb432", accent2="#00c8c8",
                entry_bg="#21262d", entry_fg="#ffb432",
                select="#1f6feb", tree_bg="#0d1117",
                tree_fg="#ffb432", header="#ffd700",
                ok="#3fb950", warn="#d29922", err="#f85149")
        return dict(
            bg="#f4f6f8", panel="#ffffff", fg="#101418",
            accent="#c25a00", accent2="#007b7b",
            entry_bg="#ffffff", entry_fg="#101418",
            select="#3b82f6", tree_bg="#ffffff",
            tree_fg="#101418", header="#8a5300",
            ok="#1a7f37", warn="#9a6700", err="#cf222e")

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        c = self.colors
        style.configure(".", background=c["bg"], foreground=c["fg"])
        style.configure("TFrame", background=c["bg"])
        style.configure("Panel.TFrame", background=c["panel"])
        style.configure("TLabel", background=c["bg"], foreground=c["accent"])
        style.configure("Header.TLabel", background=c["bg"],
                        foreground=c["header"], font=("Segoe UI", 14, "bold"))
        style.configure("Sub.TLabel", background=c["bg"],
                        foreground=c["accent2"], font=("Segoe UI", 9))
        style.configure("TCheckbutton", background=c["bg"], foreground=c["accent"])
        style.configure("TButton", padding=6, font=("Segoe UI", 9),
                        background=c["panel"], foreground=c["fg"])
        style.map("TButton",
                  background=[("active", c["accent2"])],
                  foreground=[("active", "#000000")])
        style.configure("Accent.TButton",
                        background=c["accent2"], foreground="#000000",
                        font=("Segoe UI", 9, "bold"))
        style.configure("Danger.TButton",
                        background=c["err"], foreground="#ffffff",
                        font=("Segoe UI", 9, "bold"))
        style.configure("Treeview",
                        background=c["tree_bg"], foreground=c["tree_fg"],
                        fieldbackground=c["tree_bg"], rowheight=24,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading",
                        background=c["panel"], foreground=c["header"],
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview",
                  background=[("selected", c["select"])],
                  foreground=[("selected", "#ffffff")])
        style.configure("TEntry", fieldbackground=c["entry_bg"],
                        foreground=c["entry_fg"], insertcolor=c["entry_fg"])
        style.configure("TCombobox", fieldbackground=c["entry_bg"],
                        foreground=c["entry_fg"], background=c["panel"])
        style.configure("Horizontal.TProgressbar",
                        background=c["accent2"], troughcolor=c["panel"])

    def _toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.colors = self._get_theme_colors(self.dark_mode)
        self._setup_style()
        for w in (self.root,):
            try:
                w.configure(bg=self.colors["bg"])
            except tk.TclError:
                pass
        self._repaint_widgets()
        self.log(f"Theme switched to {'Dark' if self.dark_mode else 'Light'}", "INFO")

    def _repaint_widgets(self):
        c = self.colors
        for w in self.root.winfo_children():
            self._repaint_recursive(w)

    def _repaint_recursive(self, w):
        c = self.colors
        try:
            if isinstance(w, (tk.Frame,)):
                w.configure(bg=c["bg"])
            elif isinstance(w, tk.Label):
                w.configure(bg=c["bg"], fg=c["accent"])
        except tk.TclError:
            pass
        for ch in w.winfo_children():
            self._repaint_recursive(ch)

    # ---------- Menu ----------
    def _build_menu(self):
        menubar = tk.Menu(self.root)

        # File
        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="📥 Import Paths from File...", command=self.import_paths)
        m_file.add_command(label="📤 Export Paths to File...", command=self.export_paths)
        m_file.add_separator()
        m_file.add_command(label="💾 Save Configuration", command=self.save_config)
        m_file.add_command(label="📂 Load Configuration", command=self.load_config)
        m_file.add_separator()
        m_file.add_command(label="📊 Export Rules to CSV", command=self.export_csv)
        m_file.add_separator()
        m_file.add_command(label="❌ Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=m_file)

        # Tools
        m_tools = tk.Menu(menubar, tearoff=0)
        m_tools.add_command(label="🔍 Scan Folder for .exe (recursive)", command=self.scan_folder)
        m_tools.add_command(label="⚙ Scan Running Processes", command=self.scan_processes)
        m_tools.add_separator()
        m_tools.add_command(label="🚪 Block by Port...", command=self.block_by_port)
        m_tools.add_command(label="🌐 Block by IP...", command=self.block_by_ip)
        m_tools.add_separator()
        m_tools.add_command(label="🛡 Backup Firewall Rules", command=self.backup_rules)
        m_tools.add_command(label="♻ Restore Firewall Rules", command=self.restore_rules)
        m_tools.add_separator()
        m_tools.add_command(label="⏱ Schedule Delayed Block...", command=self.schedule_block)
        m_tools.add_command(label="🧹 Remove Duplicate Rules", command=self.remove_duplicates)
        menubar.add_cascade(label="Tools", menu=m_tools)

        # View
        m_view = tk.Menu(menubar, tearoff=0)
        m_view.add_command(label="🌓 Toggle Dark/Light Theme", command=self._toggle_theme)
        m_view.add_command(label="📜 Show Activity Log", command=self.show_log_window)
        m_view.add_command(label="📈 Statistics Dashboard", command=self.show_stats)
        m_view.add_separator()
        m_view.add_command(label="✏ Set Rule Prefix...", command=self.set_prefix)
        menubar.add_cascade(label="View", menu=m_view)

        # Admin
        m_admin = tk.Menu(menubar, tearoff=0)
        m_admin.add_command(label="🔐 Request Administrator Privileges", command=self.request_admin)
        m_admin.add_command(label="ℹ About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=m_admin)

        self.root.config(menu=menubar)

    # ---------- Toolbar ----------
    def _build_toolbar(self):
        c = self.colors
        bar = tk.Frame(self.root, bg=c["panel"], height=42)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        def tb_btn(text, cmd, width=14):
            b = tk.Button(bar, text=text, command=cmd, bg=c["panel"], fg=c["accent"],
                          activebackground=c["accent2"], activeforeground="#000",
                          relief="flat", font=("Segoe UI", 9, "bold"),
                          padx=8, pady=4, cursor="hand2")
            b.pack(side="left", padx=2, pady=4)
            return b

        tb_btn("🔐 Admin", self.request_admin)
        tb_btn("📥 Import", self.import_paths)
        tb_btn("📤 Export", self.export_paths)
        tb_btn("💾 Save", self.save_config)
        tb_btn("📂 Load", self.load_config)
        tb_btn("🛡 Backup", self.backup_rules)
        tb_btn("♻ Restore", self.restore_rules)
        tb_btn("📜 Log", self.show_log_window)
        tb_btn("🌓 Theme", self._toggle_theme)
        tb_btn("📈 Stats", self.show_stats)

    # ---------- Body ----------
    def _build_body(self):
        c = self.colors
        container = tk.Frame(self.root, bg=c["bg"])
        container.pack(fill="both", expand=True, padx=10, pady=6)

        # ---- Header ----
        hdr = tk.Label(container, text="🛡  FIREWALL BLOCKER PRO",
                       bg=c["bg"], fg=c["header"],
                       font=("Segoe UI", 16, "bold"))
        hdr.pack(anchor="center", pady=(2, 0))
        sub = tk.Label(container,
                       text="Developed by Mahan Neman MA.AD.GH   |   GitHub: github.com/mahanneman",
                       bg=c["bg"], fg=c["accent2"], font=("Segoe UI", 9))
        sub.pack(anchor="center", pady=(0, 8))

        # ---- Input Row ----
        row = tk.Frame(container, bg=c["bg"])
        row.pack(fill="x", pady=4)

        tk.Label(row, text="Application Path:", bg=c["bg"], fg=c["accent"],
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.var_path = tk.StringVar()
        self.ent_path = ttk.Entry(row, textvariable=self.var_path, width=58)
        self.ent_path.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 6), pady=2)

        ttk.Button(row, text="Browse...", command=self.browse_path).grid(row=1, column=2, padx=2)

        tk.Label(row, text="Protocol:", bg=c["bg"], fg=c["accent"],
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=3, sticky="w", padx=(12, 0))
        self.var_proto = tk.StringVar(value="TCP")
        self.cmb_proto = ttk.Combobox(row, textvariable=self.var_proto,
                                      values=PROTOCOLS, width=10, state="readonly")
        self.cmb_proto.grid(row=1, column=3, padx=(12, 4), pady=2)

        tk.Label(row, text="Direction:", bg=c["bg"], fg=c["accent"],
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=4, sticky="w")
        self.var_dir = tk.StringVar(value="out")
        ttk.Combobox(row, textvariable=self.var_dir, values=DIRECTIONS,
                     width=7, state="readonly").grid(row=1, column=4, padx=4, pady=2)

        ttk.Button(row, text="➕ Add Path", style="Accent.TButton",
                   command=self.add_path).grid(row=1, column=5, padx=6)

        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=0)

        # ---- Search Row ----
        srow = tk.Frame(container, bg=c["bg"])
        srow.pack(fill="x", pady=(6, 2))
        tk.Label(srow, text="🔎 Filter:", bg=c["bg"], fg=c["accent"],
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *_: self.refresh_tree())
        ent = ttk.Entry(srow, textvariable=self.var_search, width=40)
        ent.pack(side="left", padx=6)
        tk.Label(srow, text="(live search by path / protocol)",
                 bg=c["bg"], fg=c["accent2"], font=("Segoe UI", 8, "italic")).pack(side="left")

        # ---- Treeview ----
        tree_frame = tk.Frame(container, bg=c["bg"])
        tree_frame.pack(fill="both", expand=True, pady=4)

        cols = ("check", "path", "protocol", "direction")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 selectmode="extended")
        self.tree.heading("check", text="✔")
        self.tree.heading("path", text="Path")
        self.tree.heading("protocol", text="Protocol")
        self.tree.heading("direction", text="Direction")
        self.tree.column("check", width=40, anchor="center", stretch=False)
        self.tree.column("path", width=640, anchor="w")
        self.tree.column("protocol", width=100, anchor="center")
        self.tree.column("direction", width=90, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Button-3>", self._on_tree_right_click)

        # Right-click context menu
        self.ctx_menu = tk.Menu(self.root, tearoff=0)
        self.ctx_menu.add_command(label="✔ Enable", command=lambda: self._ctx_set(True))
        self.ctx_menu.add_command(label="✘ Disable", command=lambda: self._ctx_set(False))
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="📋 Copy Path", command=self._ctx_copy_path)
        self.ctx_menu.add_command(label="🗑 Remove", command=self._ctx_remove)
        self.ctx_menu.add_command(label="🌐 Open Containing Folder", command=self._ctx_open_folder)

        # ---- Bottom buttons ----
        btns = tk.Frame(container, bg=c["bg"])
        btns.pack(fill="x", pady=6)

        def btn(text, cmd, style="TButton"):
            b = ttk.Button(btns, text=text, command=cmd, style=style)
            b.pack(side="left", padx=3)
            return b

        btn("✅ Select All",   self.select_all)
        btn("⬜ Deselect All", self.deselect_all)
        btn("🔁 Invert",       self.invert_selection)
        btn("🗑 Remove",       self.remove_selected)
        btn("🧹 Clear All",    self.clear_all)
        btn("🛡 Block Selected", self.block_selected, style="Accent.TButton")
        btn("♻ Restore All",   self.unblock_all,     style="Danger.TButton")
        btn("⚠ Whitelist Mode", self.whitelist_block)

        # ---- Progress bar ----
        self.progress = ttk.Progressbar(container, mode="determinate",
                                        style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(2, 6))

    # ---------- Status bar ----------
    def _build_statusbar(self):
        c = self.colors
        sb = tk.Frame(self.root, bg=c["panel"], height=26)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)
        self.lbl_status = tk.Label(sb, text="Ready.",
                                   bg=c["panel"], fg=c["accent2"],
                                   font=("Segoe UI", 9), anchor="w")
        self.lbl_status.pack(side="left", padx=8)
        self.lbl_admin = tk.Label(sb, text="● Checking admin...",
                                  bg=c["panel"], fg=c["warn"],
                                  font=("Segoe UI", 9, "bold"))
        self.lbl_admin.pack(side="right", padx=8)

    # =========================================================
    #  Logging & status
    # =========================================================
    def log(self, msg, level="INFO"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] [{level}] {msg}"
        self.log_entries.append(entry)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception:
            pass
        if hasattr(self, "lbl_status"):
            self.lbl_status.config(text=msg)

    def set_status(self, msg, color=None):
        if hasattr(self, "lbl_status"):
            self.lbl_status.config(text=msg,
                                   fg=color or self.colors["accent2"])

    # =========================================================
    #  Admin
    # =========================================================
    def _check_admin_state(self):
        if is_admin():
            self.lbl_admin.config(text="● Administrator", fg=self.colors["ok"])
            self.log("Running with administrator privileges", "INFO")
        else:
            self.lbl_admin.config(text="● NOT admin (limited)", fg=self.colors["err"])
            self.log("Running WITHOUT admin privileges", "WARN")
            messagebox.showwarning(
                "Administrator Required",
                "This tool needs Administrator privileges to modify firewall rules.\n\n"
                "Click 'Request Administrator Privileges' from the Help menu or the "
                "'Admin' toolbar button to relaunch with elevated rights.")

    def request_admin(self):
        if is_admin():
            messagebox.showinfo("Already Admin", "You already have admin privileges.")
            return
        if messagebox.askyesno("Relaunch as Administrator",
                               "Relaunch the application with administrator rights?"):
            run_as_admin()

    # =========================================================
    #  Tree operations
    # =========================================================
    def _filtered_indices(self):
        """Return indices of items matching current filter."""
        needle = self.var_search.get().strip().lower()
        if not needle:
            return list(range(len(self.path_items)))
        out = []
        for i, it in enumerate(self.path_items):
            if (needle in it["path"].lower() or
                    needle in it["protocol"].lower() or
                    needle in it["direction"].lower()):
                out.append(i)
        return out

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i in self._filtered_indices():
            it = self.path_items[i]
            mark = "☑" if it["enabled"] else "☐"
            self.tree.insert("", "end", iid=str(i),
                             values=(mark, it["path"], it["protocol"], it["direction"]))
        n = len(self.path_items)
        f = len(self._filtered_indices())
        self.set_status(f"Showing {f} / {n} entries.")

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            row = self.tree.identify_row(event.y)
            if col == "#1" and row:
                idx = int(row)
                self.path_items[idx]["enabled"] = not self.path_items[idx]["enabled"]
                self.refresh_tree()
                return "break"

    def _on_tree_right_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            if row not in self.tree.selection():
                self.tree.selection_set(row)
            self._context_row = row
            self.ctx_menu.tk_popup(event.x_root, event.y_root)

    def _ctx_set(self, state):
        for iid in self.tree.selection():
            self.path_items[int(iid)]["enabled"] = state
        self.refresh_tree()

    def _ctx_copy_path(self):
        for iid in self.tree.selection():
            p = self.path_items[int(iid)]["path"]
            self.root.clipboard_clear()
            self.root.clipboard_append(p)
            self.log(f"Copied: {p}", "INFO")
            break

    def _ctx_remove(self):
        idxs = sorted((int(i) for i in self.tree.selection()), reverse=True)
        for i in idxs:
            if 0 <= i < len(self.path_items):
                del self.path_items[i]
        self.refresh_tree()

    def _ctx_open_folder(self):
        for iid in self.tree.selection():
            p = self.path_items[int(iid)]["path"]
            folder = os.path.dirname(p) if os.path.isfile(p) else p
            if os.path.isdir(folder):
                try:
                    os.startfile(folder)
                except Exception as e:
                    self.log(f"Open folder failed: {e}", "ERR")
            break

    # =========================================================
    #  Path management
    # =========================================================
    def browse_path(self):
        folder = filedialog.askdirectory(title="Select installation folder")
        if folder:
            self.var_path.set(folder)

    def add_path(self):
        path = self.var_path.get().strip().strip('"')
        if not path:
            messagebox.showwarning("Empty", "Please enter or browse a path.")
            return
        proto = self.var_proto.get()
        direction = self.var_dir.get()

        for it in self.path_items:
            if it["path"].lower() == path.lower() and it["protocol"] == proto:
                messagebox.showinfo("Duplicate", "This path+protocol is already in the list.")
                return

        self.path_items.append({
            "path": path, "protocol": proto,
            "direction": direction, "enabled": True,
        })
        self.var_path.set("")
        self.refresh_tree()
        self.log(f"Added path: {path} [{proto}/{direction}]", "INFO")

    def select_all(self):
        for i in self._filtered_indices():
            self.path_items[i]["enabled"] = True
        self.refresh_tree()

    def deselect_all(self):
        for i in self._filtered_indices():
            self.path_items[i]["enabled"] = False
        self.refresh_tree()

    def invert_selection(self):
        for i in self._filtered_indices():
            self.path_items[i]["enabled"] = not self.path_items[i]["enabled"]
        self.refresh_tree()

    def remove_selected(self):
        idxs = sorted((int(i) for i in self.tree.selection()), reverse=True)
        if not idxs:
            messagebox.showinfo("Nothing selected",
                                "Select one or more rows in the list to remove.")
            return
        for i in idxs:
            if 0 <= i < len(self.path_items):
                del self.path_items[i]
        self.refresh_tree()
        self.log(f"Removed {len(idxs)} entries", "INFO")

    def clear_all(self):
        if not self.path_items:
            return
        if messagebox.askyesno("Confirm", "Remove ALL entries from the list?"):
            self.path_items.clear()
            self.refresh_tree()

    # =========================================================
    #  Firewall actions
    # =========================================================
    def _find_exe_files(self, folder):
        out = []
        if os.path.isfile(folder) and folder.lower().endswith(".exe"):
            out.append(os.path.abspath(folder))
            return out
        if os.path.isfile(folder):
            out.append(os.path.abspath(folder))
            return out
        if not os.path.isdir(folder):
            return out
        for root_, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(".exe"):
                    out.append(os.path.join(root_, f))
        return out

    def _protocol_args(self, proto):
        p = proto.upper()
        if p == "IP":
            return ["protocol=any"]
        if p == "ANY":
            return ["protocol=any"]
        return [f"protocol={p}"]

    def _build_rule_name(self, idx, proto):
        return f"{self.rule_prefix}_{idx}_{proto}"

    def block_selected(self):
        if not is_admin():
            if messagebox.askyesno("Not Admin",
                                   "Firewall changes require admin rights.\nRelaunch elevated?"):
                run_as_admin()
            return

        selected = [it for it in self.path_items if it["enabled"]]
        if not selected:
            messagebox.showwarning("No selection",
                                   "Enable (✔) at least one entry.")
            return

        # Expand to exe files
        all_tasks = []
        for it in selected:
            exes = self._find_exe_files(it["path"])
            if not exes:
                self.log(f"No .exe found in: {it['path']}", "WARN")
            for exe in exes:
                all_tasks.append((exe, it["protocol"], it["direction"]))

        if not all_tasks:
            messagebox.showinfo("Info", "No executable files found to block.")
            return

        if not messagebox.askyesno("Confirm Block",
                                   f"Create firewall rules for {len(all_tasks)} file(s)?"):
            return

        self._run_block_tasks(all_tasks)

    def _run_block_tasks(self, tasks):
        total = len(tasks)
        self.progress["maximum"] = total
        self.progress["value"] = 0
        self.log(f"Starting block operation for {total} task(s)", "INFO")

        done = 0
        success = 0

        def worker():
            nonlocal done, success
            ctr = 0
            for (exe, proto, direction) in tasks:
                directions = ["out", "in"] if direction == "both" else [direction]
                for d in directions:
                    name = self._build_rule_name(ctr, f"{proto}_{d}")
                    args = ["advfirewall", "firewall", "add", "rule",
                            f"name={name}", f"dir={d}",
                            f"program={exe}", "action=block"]
                    args += self._protocol_args(proto)
                    rc, _, err = run_netsh(args)
                    if rc == 0:
                        success += 1
                    else:
                        self.log(f"Failed rule {name}: {err.strip()}", "ERR")
                ctr += 1
                done += 1
                self.root.after(0, lambda v=done: self._set_progress(v))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        def wait():
            if t.is_alive():
                self.root.after(200, wait)
            else:
                self.progress["value"] = total
                self.log(f"Blocked {success}/{total} rule(s)", "OK")
                messagebox.showinfo("Done",
                                    f"Blocked successfully!\n\nRules created: {success}")
        self.root.after(200, wait)

    def _set_progress(self, v):
        self.progress["value"] = v
        self.set_status(f"Progress: {v}/{self.progress['maximum']}")

    def unblock_all(self):
        if not is_admin():
            if messagebox.askyesno("Not Admin",
                                   "Firewall changes require admin rights.\nRelaunch elevated?"):
                run_as_admin()
            return
        if not messagebox.askyesno("Confirm",
                                   f"Delete ALL rules starting with '{self.rule_prefix}_'?"):
            return

        def worker():
            rc, out, err = run_netsh(["advfirewall", "firewall", "show", "rule", "name=all"])
            if rc != 0:
                self.log(f"Show rules failed: {err}", "ERR")
                return
            names = []
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("Rule Name:") or line.startswith("نام قانون"):
                    n = line.split(":", 1)[1].strip()
                    if n.startswith(self.rule_prefix + "_"):
                        names.append(n)
            removed = 0
            for n in names:
                rc2, _, _ = run_netsh(["advfirewall", "firewall", "delete", "rule", f"name={n}"])
                if rc2 == 0:
                    removed += 1
            self.log(f"Removed {removed}/{len(names)} rule(s)", "OK")
            self.root.after(0, lambda: messagebox.showinfo(
                "Restore Complete", f"Removed {removed} rules."))
        threading.Thread(target=worker, daemon=True).start()

    def whitelist_block(self):
        """Block everything except the checked entries (aggressive)."""
        if not is_admin():
            if messagebox.askyesno("Not Admin", "Need admin. Relaunch?"):
                run_as_admin()
            return
        messagebox.showinfo(
            "Whitelist Mode",
            "Whitelist mode creates outbound BLOCK rules for all checked apps "
            "while leaving unchecked apps untouched.\n\n"
            "This is equivalent to 'Block Selected' — for true whitelisting use "
            "Windows Firewall outbound default = Block.")
        self.block_selected()

    # =========================================================
    #  Import / Export
    # =========================================================
    def import_paths(self):
        f = filedialog.askopenfilename(
            title="Import paths",
            filetypes=[("Text/JSON", "*.txt *.json"), ("All", "*.*")])
        if not f:
            return
        try:
            if f.lower().endswith(".json"):
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                for it in data:
                    self.path_items.append({
                        "path": it.get("path", ""),
                        "protocol": it.get("protocol", "TCP"),
                        "direction": it.get("direction", "out"),
                        "enabled": it.get("enabled", True),
                    })
            else:
                with open(f, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        self.path_items.append({
                            "path": line, "protocol": "TCP",
                            "direction": "out", "enabled": True})
            self.refresh_tree()
            self.log(f"Imported from {f}", "OK")
        except Exception as e:
            messagebox.showerror("Import failed", str(e))

    def export_paths(self):
        f = filedialog.asksaveasfilename(
            title="Export paths", defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("JSON", "*.json")])
        if not f:
            return
        try:
            if f.lower().endswith(".json"):
                with open(f, "w", encoding="utf-8") as fh:
                    json.dump(self.path_items, fh, indent=2, ensure_ascii=False)
            else:
                with open(f, "w", encoding="utf-8") as fh:
                    for it in self.path_items:
                        fh.write(f"# {it['protocol']} | {it['direction']}\n")
                        fh.write(it["path"] + "\n")
            self.log(f"Exported to {f}", "OK")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def save_config(self):
        f = filedialog.asksaveasfilename(
            title="Save configuration", defaultextension=".json",
            initialfile=CONFIG_FILE)
        if not f:
            return
        cfg = {
            "version": APP_VERSION,
            "rule_prefix": self.rule_prefix,
            "dark_mode": self.dark_mode,
            "items": self.path_items,
        }
        try:
            with open(f, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh, indent=2, ensure_ascii=False)
            self.log(f"Config saved: {f}", "OK")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def load_config(self):
        f = filedialog.askopenfilename(
            title="Load configuration",
            filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if not f:
            return
        try:
            with open(f, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
            self.path_items = cfg.get("items", [])
            self.rule_prefix = cfg.get("rule_prefix", "Block_App")
            self.refresh_tree()
            self.log(f"Config loaded: {f}", "OK")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))

    def export_csv(self):
        f = filedialog.asksaveasfilename(
            title="Export to CSV", defaultextension=".csv")
        if not f:
            return
        try:
            with open(f, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["Path", "Protocol", "Direction", "Enabled"])
                for it in self.path_items:
                    w.writerow([it["path"], it["protocol"],
                                it["direction"], it["enabled"]])
            self.log(f"CSV export: {f}", "OK")
        except Exception as e:
            messagebox.showerror("CSV export failed", str(e))

    # =========================================================
    #  Tools
    # =========================================================
    def scan_folder(self):
        folder = filedialog.askdirectory(title="Folder to scan for .exe files")
        if not folder:
            return
        exes = self._find_exe_files(folder)
        added = 0
        existing = {it["path"].lower() for it in self.path_items}
        for exe in exes:
            if exe.lower() not in existing:
                self.path_items.append({
                    "path": exe, "protocol": self.var_proto.get(),
                    "direction": self.var_dir.get(), "enabled": True})
                added += 1
        self.refresh_tree()
        self.log(f"Scanned {folder}: found {len(exes)}, added {added}", "OK")
        messagebox.showinfo("Scan Complete",
                            f"Found {len(exes)} .exe file(s).\nAdded {added} new entry(ies).")

    def scan_processes(self):
        """Add currently running processes from tasklist."""
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            r = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                               capture_output=True, text=True,
                               startupinfo=si, creationflags=0x08000000)
            rows = list(csv.reader(r.stdout.splitlines()))
        except Exception as e:
            messagebox.showerror("tasklist failed", str(e))
            return

        existing = {it["path"].lower() for it in self.path_items}
        added = 0
        for row in rows:
            if len(row) < 2:
                continue
            name = row[0]
            if not name.lower().endswith(".exe"):
                continue
            # locate full path
            for base in (os.environ.get("SystemRoot", "C:\\Windows"),
                         os.environ.get("ProgramFiles", "C:\\Program Files"),
                         os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")):
                cand = os.path.join(base, "System32", name) if "Windows" in base else None
            full = name  # fallback
            if full.lower() not in existing:
                self.path_items.append({
                    "path": full, "protocol": self.var_proto.get(),
                    "direction": self.var_dir.get(), "enabled": False})
                existing.add(full.lower())
                added += 1
        self.refresh_tree()
        self.log(f"Scanned running processes: added {added}", "OK")
        messagebox.showinfo("Processes",
                            f"Added {added} running process(es) to the list (disabled by default).\n"
                            "Enable the ones you wish to block.")

    def block_by_port(self):
        port = simpledialog.askstring("Block by Port",
                                      "Enter port number(s), comma-separated (e.g. 80,443):")
        if not port:
            return
        proto = simpledialog.askstring("Protocol",
                                       "Protocol (TCP / UDP):", initialvalue="TCP")
        if not proto:
            return
        if not is_admin():
            if messagebox.askyesno("Not Admin", "Relaunch as admin?"):
                run_as_admin()
            return
        direction = self.var_dir.get()
        directions = ["out", "in"] if direction == "both" else [direction]
        for p in [x.strip() for x in port.split(",") if x.strip()]:
            for d in directions:
                name = f"{self.rule_prefix}_port_{proto}_{p}_{d}"
                args = ["advfirewall", "firewall", "add", "rule",
                        f"name={name}", f"dir={d}",
                        f"protocol={proto}", f"localport={p}", "action=block"]
                rc, _, err = run_netsh(args)
                if rc == 0:
                    self.log(f"Blocked port {p}/{proto}/{d}", "OK")
                else:
                    self.log(f"Port block failed: {err}", "ERR")
        messagebox.showinfo("Done", "Port block rules created.")

    def block_by_ip(self):
        ip = simpledialog.askstring("Block by IP",
                                    "Enter IP or CIDR (e.g. 8.8.8.8 or 192.168.0.0/24):")
        if not ip:
            return
        direction = self.var_dir.get()
        if not is_admin():
            if messagebox.askyesno("Not Admin", "Relaunch as admin?"):
                run_as_admin()
            return
        directions = ["out", "in"] if direction == "both" else [direction]
        for d in directions:
            name = f"{self.rule_prefix}_ip_{ip.replace('/', '_')}_{d}"
            args = ["advfirewall", "firewall", "add", "rule",
                    f"name={name}", f"dir={d}", f"remoteip={ip}",
                    "action=block"]
            rc, _, err = run_netsh(args)
            if rc == 0:
                self.log(f"Blocked IP {ip}/{d}", "OK")
            else:
                self.log(f"IP block failed: {err}", "ERR")
        messagebox.showinfo("Done", "IP block rules created.")

    def backup_rules(self):
        f = filedialog.asksaveasfilename(
            title="Backup firewall rules", defaultextension=".wfw",
            initialfile="firewall_backup.wfw")
        if not f:
            return
        rc, _, err = run_netsh(["advfirewall", "export", f])
        if rc == 0:
            self.log(f"Rules backed up: {f}", "OK")
            messagebox.showinfo("Backup", "Firewall rules backed up successfully.")
        else:
            messagebox.showerror("Backup failed", err)

    def restore_rules(self):
        f = filedialog.askopenfilename(
            title="Restore firewall rules from backup",
            filetypes=[("Firewall backup", "*.wfw"), ("All", "*.*")])
        if not f:
            return
        if not is_admin():
            if messagebox.askyesno("Not Admin", "Relaunch as admin?"):
                run_as_admin()
            return
        rc, _, err = run_netsh(["advfirewall", "import", f])
        if rc == 0:
            self.log(f"Rules restored: {f}", "OK")
            messagebox.showinfo("Restore", "Firewall rules restored.")
        else:
            messagebox.showerror("Restore failed", err)

    def schedule_block(self):
        delay = simpledialog.askinteger("Schedule Block",
                                        "Delay in seconds before blocking:",
                                        minvalue=1, maxvalue=86400, initialvalue=10)
        if not delay:
            return
        self.log(f"Block scheduled in {delay}s", "INFO")
        self.set_status(f"Block scheduled in {delay}s...")
        self.root.after(delay * 1000, self.block_selected)

    def remove_duplicates(self):
        seen = set()
        cleaned = []
        for it in self.path_items:
            key = (it["path"].lower(), it["protocol"], it["direction"])
            if key not in seen:
                seen.add(key)
                cleaned.append(it)
        removed = len(self.path_items) - len(cleaned)
        self.path_items = cleaned
        self.refresh_tree()
        self.log(f"Removed {removed} duplicate(s)", "OK")
        messagebox.showinfo("Cleanup", f"Removed {removed} duplicate entry(ies).")

    # =========================================================
    #  View
    # =========================================================
    def set_prefix(self):
        p = simpledialog.askstring("Rule Prefix",
                                   "Prefix for created firewall rules:",
                                   initialvalue=self.rule_prefix)
        if p:
            self.rule_prefix = p.strip()
            self.log(f"Rule prefix set to: {self.rule_prefix}", "INFO")

    def show_log_window(self):
        w = tk.Toplevel(self.root)
        w.title("Activity Log")
        w.geometry("800x500")
        c = self.colors
        w.configure(bg=c["bg"])
        txt = tk.Text(w, bg=c["entry_bg"], fg=c["entry_fg"],
                      font=("Consolas", 9), wrap="word")
        txt.pack(fill="both", expand=True, padx=6, pady=6)
        txt.insert("end", "\n".join(self.log_entries) or "(empty)")
        txt.see("end")
        ttk.Button(w, text="Clear Log",
                   command=lambda: (self.log_entries.clear(), txt.delete("1.0", "end"))
                   ).pack(pady=4)

    def show_stats(self):
        total = len(self.path_items)
        enabled = sum(1 for it in self.path_items if it["enabled"])
        protocols = {}
        for it in self.path_items:
            protocols[it["protocol"]] = protocols.get(it["protocol"], 0) + 1

        # count existing rules
        rc, out, _ = run_netsh(["advfirewall", "firewall", "show", "rule", "name=all"])
        rule_count = out.count("Rule Name:") if rc == 0 else "?"

        msg = [
            f"Total entries: {total}",
            f"Enabled entries: {enabled}",
            f"Disabled entries: {total - enabled}",
            f"Firewall rules on system: {rule_count}",
            "",
            "Protocol breakdown:",
        ]
        for k, v in sorted(protocols.items()):
            msg.append(f"   • {k}: {v}")

        messagebox.showinfo("Statistics Dashboard", "\n".join(msg))

    def show_about(self):
        messagebox.showinfo(
            f"About {APP_NAME}",
            f"{APP_NAME} v{APP_VERSION}\n\n"
            "Developed by Mahan Neman MA.AD.GH\n"
            "GitHub: github.com/mahanneman\n\n"
            "A professional Windows Firewall management tool.\n"
            "Requires Administrator privileges for rule changes.")


# ================== Entry Point ==================
def main():
    if os.name != "nt":
        print("This application requires Windows.")
        sys.exit(1)
    root = tk.Tk()
    app = FirewallBlockerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
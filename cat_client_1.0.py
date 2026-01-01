#!/usr/bin/env python3
"""
CAT CLIENT 1.0
[C] SAMSOFT 2025 - CRACKED/OFFLINE MODE SUPPORT
DARK/LIGHT/SYSTEM THEME TOGGLE
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import urllib.request
import subprocess
import zipfile
import ssl
import threading
import sys
import os
import platform
from pathlib import Path
import uuid
import io
import hashlib
import concurrent.futures

# Bypass SSL
ssl._create_default_https_context = ssl._create_unverified_context

# Paths
if sys.platform == "win32":
    GAME_DIR = Path.home() / "AppData" / "Roaming" / ".minecraft"
elif sys.platform == "darwin":
    GAME_DIR = Path.home() / "Library" / "Application Support" / "minecraft"
else:
    GAME_DIR = Path.home() / ".minecraft"

SKIN_SERVER = "https://mc-heads.net"
VERSION_MANIFEST = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
ASSETS_URL = "https://resources.download.minecraft.net"
CLASSPATH_SEP = ";" if sys.platform == "win32" else ":"

# ============== CAT CLIENT THEMES ==============
THEMES = {
    "dark": {
        "bg_dark": "#1a1a2e",
        "bg_darker": "#16213e",
        "bg_panel": "#1f2937",
        "bg_input": "#374151",
        "bg_header": "#7c3aed",  # Purple cat theme
        "accent": "#a78bfa",
        "accent_hover": "#c4b5fd",
        "accent_green": "#10b981",
        "accent_green_hover": "#34d399",
        "accent_orange": "#f59e0b",
        "accent_blue": "#3b82f6",
        "text_primary": "#ffffff",
        "text_secondary": "#9ca3af",
        "text_muted": "#6b7280",
        "border": "#374151",
        "button_play": "#10b981",
        "button_play_hover": "#34d399",
    },
    "light": {
        "bg_dark": "#f3f4f6",
        "bg_darker": "#e5e7eb",
        "bg_panel": "#ffffff",
        "bg_input": "#f9fafb",
        "bg_header": "#8b5cf6",  # Purple cat theme
        "accent": "#7c3aed",
        "accent_hover": "#6d28d9",
        "accent_green": "#059669",
        "accent_green_hover": "#047857",
        "accent_orange": "#d97706",
        "accent_blue": "#2563eb",
        "text_primary": "#111827",
        "text_secondary": "#4b5563",
        "text_muted": "#9ca3af",
        "border": "#d1d5db",
        "button_play": "#059669",
        "button_play_hover": "#047857",
    }
}

# ============== UTILITY FUNCTIONS ==============
def get_system_theme():
    """Detect system dark/light mode"""
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if value else "dark"
        elif sys.platform == "darwin":
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True
            )
            return "dark" if "Dark" in result.stdout else "light"
    except:
        pass
    return "dark"


def find_java():
    candidates = []
    if sys.platform == "win32":
        candidates = [
            Path(os.environ.get("JAVA_HOME", "")) / "bin" / "java.exe",
            Path("C:/Program Files/Java/jdk-17/bin/java.exe"),
            Path("C:/Program Files/Java/jdk-21/bin/java.exe"),
            Path("C:/Program Files/Eclipse Adoptium/jdk-17/bin/java.exe"),
            Path("C:/Program Files/Eclipse Adoptium/jdk-21/bin/java.exe"),
            Path("C:/Program Files/BellSoft/LibericaJDK-21/bin/java.exe"),
            Path("C:/Program Files/BellSoft/LibericaJDK-17/bin/java.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            Path("/opt/homebrew/opt/openjdk@17/bin/java"),
            Path("/opt/homebrew/opt/openjdk@21/bin/java"),
            Path("/opt/homebrew/opt/openjdk/bin/java"),
            Path("/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/java"),
            Path("/usr/bin/java"),
        ]
    else:
        candidates = [
            Path("/usr/lib/jvm/java-17-openjdk/bin/java"),
            Path("/usr/lib/jvm/java-17-openjdk-amd64/bin/java"),
            Path("/usr/bin/java"),
        ]
    
    for path in candidates:
        if path.exists():
            return str(path)
    return "java"


def get_os_name():
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "osx"
    return "linux"


def get_arch():
    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x64"
    elif machine in ("aarch64", "arm64"):
        return "arm64"
    return "x86"


def check_rules(rules):
    if not rules:
        return True
    
    os_name = get_os_name()
    arch = get_arch()
    result = False
    
    for rule in rules:
        action = rule.get("action", "allow")
        matches = True
        
        if "os" in rule:
            os_rule = rule["os"]
            if "name" in os_rule and os_rule["name"] != os_name:
                matches = False
            if "arch" in os_rule and os_rule["arch"] != arch:
                matches = False
        
        if matches:
            result = (action == "allow")
    
    return result


def generate_offline_uuid(username):
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, f"OfflinePlayer:{username}"))


def calculate_sha1(filepath):
    sha1 = hashlib.sha1()
    try:
        with open(filepath, 'rb') as f:
            while chunk := f.read(65536):
                sha1.update(chunk)
        return sha1.hexdigest()
    except:
        return None


# ============== ASSET DOWNLOADER ==============
class AssetDownloader:
    def __init__(self, game_dir, progress_callback=None, status_callback=None):
        self.game_dir = Path(game_dir)
        self.assets_dir = self.game_dir / "assets"
        self.objects_dir = self.assets_dir / "objects"
        self.indexes_dir = self.assets_dir / "indexes"
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.downloaded = 0
        self.total = 0
        self.failed = []
    
    def download_file(self, url, dest_path, expected_hash=None):
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if dest_path.exists():
                if expected_hash:
                    if calculate_sha1(dest_path) == expected_hash:
                        return True
                else:
                    return True
            
            req = urllib.request.Request(url, headers={'User-Agent': 'CatClient/1.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(dest_path, 'wb') as f:
                    f.write(resp.read())
            
            return True
        except:
            return False
    
    def download_asset(self, asset_hash, asset_size=None):
        prefix = asset_hash[:2]
        asset_path = self.objects_dir / prefix / asset_hash
        url = f"{ASSETS_URL}/{prefix}/{asset_hash}"
        
        success = self.download_file(url, asset_path, asset_hash)
        
        self.downloaded += 1
        if self.progress_callback and self.total > 0:
            progress = int((self.downloaded / self.total) * 100)
            self.progress_callback(progress)
        
        if not success:
            self.failed.append(asset_hash)
        
        return success
    
    def download_all_assets(self, asset_index_id, asset_index_url=None):
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        self.indexes_dir.mkdir(parents=True, exist_ok=True)
        
        index_path = self.indexes_dir / f"{asset_index_id}.json"
        if not index_path.exists() and asset_index_url:
            if self.status_callback:
                self.status_callback("Downloading asset index...")
            self.download_file(asset_index_url, index_path)
        
        if not index_path.exists():
            raise FileNotFoundError(f"Asset index not found: {index_path}")
        
        with open(index_path) as f:
            asset_index = json.load(f)
        
        objects = asset_index.get("objects", {})
        self.total = len(objects)
        self.downloaded = 0
        self.failed = []
        
        if self.status_callback:
            self.status_callback(f"Checking {self.total} assets...")
        
        assets_to_download = []
        for asset_name, asset_info in objects.items():
            asset_hash = asset_info["hash"]
            prefix = asset_hash[:2]
            asset_path = self.objects_dir / prefix / asset_hash
            
            if asset_path.exists():
                existing_hash = calculate_sha1(asset_path)
                if existing_hash == asset_hash:
                    self.downloaded += 1
                    continue
            
            assets_to_download.append((asset_hash, asset_info.get("size", 0)))
        
        if self.status_callback:
            self.status_callback(f"Downloading {len(assets_to_download)} assets...")
        
        if assets_to_download:
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                futures = []
                for asset_hash, asset_size in assets_to_download:
                    future = executor.submit(self.download_asset, asset_hash, asset_size)
                    futures.append(future)
                
                concurrent.futures.wait(futures)
        
        if self.status_callback:
            if self.failed:
                self.status_callback(f"Assets done ({len(self.failed)} failed)")
            else:
                self.status_callback("All assets downloaded!")
        
        return len(self.failed) == 0


# ============== THEME TOGGLE WIDGET ==============
class ThemeToggle(tk.Frame):
    """Custom theme toggle slider: Dark | Light | System"""
    
    def __init__(self, parent, callback, initial="system", **kwargs):
        super().__init__(parent, **kwargs)
        self.callback = callback
        self.current = initial
        self.options = ["dark", "light", "system"]
        self.labels = ["🌙", "☀️", "💻"]
        
        self.configure(bg=kwargs.get("bg", "#16213e"))
        
        self.buttons = []
        for i, (opt, lbl) in enumerate(zip(self.options, self.labels)):
            btn = tk.Label(
                self, text=lbl, font=("Segoe UI", 12),
                fg="#ffffff" if opt == initial else "#6b7280",
                bg=self["bg"], padx=8, pady=4, cursor="hand2"
            )
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, o=opt: self.select(o))
            self.buttons.append(btn)
    
    def select(self, option):
        self.current = option
        for btn, opt in zip(self.buttons, self.options):
            if opt == option:
                btn.config(fg="#ffffff", font=("Segoe UI", 12, "bold"))
            else:
                btn.config(fg="#6b7280", font=("Segoe UI", 12))
        self.callback(option)
    
    def update_bg(self, bg):
        self.configure(bg=bg)
        for btn in self.buttons:
            btn.configure(bg=bg)


# ============== CAT CLIENT UI ==============
class CatClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cat Client 1.0")
        self.root.geometry("900x560")
        self.root.resizable(False, False)
        
        # Theme
        self.theme_mode = "system"
        self.current_theme = THEMES[get_system_theme()]
        
        # Variables
        self.username = tk.StringVar(value="Player")
        self.version = tk.StringVar(value="1.20.1")
        self.account_type = tk.StringVar(value="Cat Client")
        self.ram = tk.IntVar(value=4)
        self.skin_photo = None
        self.status_text = tk.StringVar(value="Ready to play 🐱")
        self.java_bin = find_java()
        
        GAME_DIR.mkdir(parents=True, exist_ok=True)
        
        self.setup_styles()
        self.build_ui()
        self.apply_theme()
        self.load_versions()
        
        self.root.after(500, self.update_skin)
    
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
    
    def apply_theme(self):
        """Apply current theme to all widgets"""
        t = self.current_theme
        
        self.root.configure(bg=t["bg_dark"])
        
        # Update style
        self.style.configure("Cat.TCombobox",
            fieldbackground=t["bg_input"],
            background=t["bg_input"],
            foreground=t["text_primary"],
            arrowcolor=t["text_primary"],
            borderwidth=0
        )
        self.style.map("Cat.TCombobox",
            fieldbackground=[("readonly", t["bg_input"])],
            selectbackground=[("readonly", t["accent"])],
            selectforeground=[("readonly", t["text_primary"])]
        )
        
        self.style.configure("Cat.Horizontal.TProgressbar",
            troughcolor=t["bg_darker"],
            background=t["accent_green"],
            thickness=6
        )
        
        # Update all widgets
        if hasattr(self, 'header'):
            self.header.configure(bg=t["bg_header"])
            for child in self.header.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=t["bg_header"])
                elif isinstance(child, tk.Frame):
                    child.configure(bg=t["bg_header"])
                    for c in child.winfo_children():
                        if isinstance(c, (tk.Label, tk.Frame)):
                            c.configure(bg=t["bg_header"])
        
        if hasattr(self, 'nav_bar'):
            self.nav_bar.configure(bg=t["bg_darker"])
            for child in self.nav_bar.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=t["bg_darker"])
        
        if hasattr(self, 'main_content'):
            self.update_frame_theme(self.main_content, t)
        
        if hasattr(self, 'bottom_bar'):
            self.bottom_bar.configure(bg=t["bg_darker"])
            self.update_frame_theme(self.bottom_bar, t, is_bottom=True)
        
        if hasattr(self, 'theme_toggle'):
            self.theme_toggle.update_bg(t["bg_header"])
        
        # Update play button
        if hasattr(self, 'play_button'):
            self.play_button.configure(
                bg=t["button_play"],
                activebackground=t["button_play_hover"]
            )
    
    def update_frame_theme(self, frame, t, is_bottom=False):
        """Recursively update frame and children"""
        bg = t["bg_darker"] if is_bottom else t["bg_dark"]
        try:
            frame.configure(bg=bg)
        except:
            pass
        
        for child in frame.winfo_children():
            try:
                widget_class = child.winfo_class()
                
                if widget_class == "Frame":
                    if child.cget("bg") in [THEMES["dark"]["bg_panel"], THEMES["light"]["bg_panel"], "#1f2937", "#ffffff"]:
                        child.configure(bg=t["bg_panel"])
                    elif child.cget("bg") in [THEMES["dark"]["bg_input"], THEMES["light"]["bg_input"], "#374151", "#f9fafb"]:
                        child.configure(bg=t["bg_input"])
                    else:
                        child.configure(bg=bg)
                    self.update_frame_theme(child, t, is_bottom)
                    
                elif widget_class == "Label":
                    parent_bg = child.master.cget("bg") if hasattr(child.master, 'cget') else bg
                    child.configure(bg=parent_bg)
                    
                    # Update text color based on current color
                    current_fg = child.cget("fg")
                    if current_fg in ["#ffffff", "#111827", t["text_primary"]]:
                        child.configure(fg=t["text_primary"])
                    elif current_fg in ["#9ca3af", "#4b5563", t["text_secondary"]]:
                        child.configure(fg=t["text_secondary"])
                    elif current_fg in ["#6b7280", t["text_muted"]]:
                        child.configure(fg=t["text_muted"])
                    elif current_fg in ["#10b981", "#059669", t["accent_green"]]:
                        child.configure(fg=t["accent_green"])
                    elif current_fg in ["#f59e0b", "#d97706", t["accent_orange"]]:
                        child.configure(fg=t["accent_orange"])
                
                elif widget_class == "Entry":
                    child.configure(
                        bg=t["bg_input"],
                        fg=t["text_primary"],
                        insertbackground=t["text_primary"]
                    )
                
                elif widget_class == "Button":
                    if "ENTER" in child.cget("text") or "PLAY" in child.cget("text"):
                        child.configure(
                            bg=t["button_play"],
                            activebackground=t["button_play_hover"]
                        )
                    else:
                        child.configure(
                            bg=t["bg_panel"],
                            fg=t["text_secondary"],
                            activebackground=t["bg_input"]
                        )
                
                elif widget_class == "Scale":
                    child.configure(
                        bg=bg,
                        fg=t["text_primary"],
                        troughcolor=t["bg_input"],
                        activebackground=t["accent_green"],
                        highlightbackground=bg
                    )
                
                elif widget_class == "Checkbutton":
                    child.configure(
                        bg=bg,
                        fg=t["text_secondary"],
                        activebackground=bg,
                        selectcolor=t["bg_input"]
                    )
            except:
                pass
    
    def on_theme_change(self, mode):
        """Handle theme toggle"""
        self.theme_mode = mode
        
        if mode == "system":
            theme_name = get_system_theme()
        else:
            theme_name = mode
        
        self.current_theme = THEMES[theme_name]
        self.apply_theme()
    
    def build_ui(self):
        t = self.current_theme
        
        # ============== TOP HEADER BAR ==============
        self.header = tk.Frame(self.root, bg=t["bg_header"], height=50)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        
        # Logo
        logo_frame = tk.Frame(self.header, bg=t["bg_header"])
        logo_frame.pack(side="left", padx=15)
        
        tk.Label(
            logo_frame, text="🐱 Cat Client", font=("Segoe UI", 14, "bold"),
            fg="#ffffff", bg=t["bg_header"]
        ).pack(side="left")
        
        tk.Label(
            logo_frame, text="1.0", font=("Segoe UI", 9),
            fg="#e0e0ff", bg=t["bg_header"]
        ).pack(side="left", padx=(8, 0))
        
        # Header right side
        header_right = tk.Frame(self.header, bg=t["bg_header"])
        header_right.pack(side="right", padx=10)
        
        # Theme toggle
        self.theme_toggle = ThemeToggle(
            header_right, self.on_theme_change, 
            initial="system", bg=t["bg_header"]
        )
        self.theme_toggle.pack(side="left", padx=(0, 20))
        
        # Window controls
        for icon in ["─", "□", "✕"]:
            btn = tk.Label(
                header_right, text=icon, font=("Segoe UI", 12),
                fg="#ffffff", bg=t["bg_header"],
                padx=10, cursor="hand2"
            )
            btn.pack(side="left")
            if icon == "✕":
                btn.bind("<Button-1>", lambda e: self.root.quit())
                btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#e81123"))
                btn.bind("<Leave>", lambda e, b=btn: b.config(bg=t["bg_header"]))
    
        # ============== NAVIGATION TABS ==============
        self.nav_bar = tk.Frame(self.root, bg=t["bg_darker"], height=40)
        self.nav_bar.pack(fill="x")
        self.nav_bar.pack_propagate(False)
        
        tabs = ["PLAY", "MODS", "SKINS", "SETTINGS", "ABOUT"]
        self.tab_labels = []
        
        for i, tab in enumerate(tabs):
            lbl = tk.Label(
                self.nav_bar, text=tab, font=("Segoe UI", 10),
                fg=t["text_secondary"] if i > 0 else t["text_primary"],
                bg=t["bg_darker"], padx=20, pady=10, cursor="hand2"
            )
            lbl.pack(side="left")
            self.tab_labels.append(lbl)
            
            if i == 0:
                indicator = tk.Frame(lbl, bg=t["accent"], height=3)
                indicator.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
        
        # ============== MAIN CONTENT ==============
        self.main_content = tk.Frame(self.root, bg=t["bg_dark"])
        self.main_content.pack(fill="both", expand=True, padx=20, pady=15)
        
        # Left panel - Skin preview
        left_panel = tk.Frame(self.main_content, bg=t["bg_dark"], width=200)
        left_panel.pack(side="left", fill="y", padx=(0, 20))
        left_panel.pack_propagate(False)
        
        skin_frame = tk.Frame(left_panel, bg=t["bg_panel"], width=180, height=200)
        skin_frame.pack(pady=(0, 15))
        skin_frame.pack_propagate(False)
        
        self.skin_label = tk.Label(
            skin_frame, text="🐱", font=("Segoe UI", 48),
            fg=t["text_secondary"], bg=t["bg_panel"]
        )
        self.skin_label.place(relx=0.5, rely=0.5, anchor="center")
        
        self.username_display = tk.Label(
            left_panel, textvariable=self.username, font=("Segoe UI", 11, "bold"),
            fg=t["text_primary"], bg=t["bg_dark"]
        )
        self.username_display.pack()
        
        self.account_indicator = tk.Label(
            left_panel, text="Cat Client Account", font=("Segoe UI", 9),
            fg=t["accent_green"], bg=t["bg_dark"]
        )
        self.account_indicator.pack(pady=(2, 15))
        
        manage_btn = tk.Button(
            left_panel, text="Manage accounts", font=("Segoe UI", 9),
            fg=t["text_secondary"], bg=t["bg_panel"],
            activeforeground=t["text_primary"],
            activebackground=t["bg_input"],
            relief="flat", cursor="hand2", padx=15, pady=5
        )
        manage_btn.pack()
        
        # Right panel - Settings
        right_panel = tk.Frame(self.main_content, bg=t["bg_dark"])
        right_panel.pack(side="right", fill="both", expand=True)
        
        # ============== ACCOUNT TYPE ==============
        account_frame = tk.Frame(right_panel, bg=t["bg_dark"])
        account_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            account_frame, text="Account type:", font=("Segoe UI", 10),
            fg=t["text_secondary"], bg=t["bg_dark"]
        ).pack(side="left", padx=(0, 10))
        
        account_types = ["Cat Client", "Microsoft Account", "Mojang Account (Legacy)"]
        self.account_combo = ttk.Combobox(
            account_frame, textvariable=self.account_type,
            values=account_types, state="readonly", width=25,
            style="Cat.TCombobox", font=("Segoe UI", 10)
        )
        self.account_combo.pack(side="left")
        self.account_combo.bind("<<ComboboxSelected>>", self.on_account_type_change)
        
        self.cracked_label = tk.Label(
            account_frame, text="✓ OFFLINE MODE", font=("Segoe UI", 9, "bold"),
            fg=t["accent_green"], bg=t["bg_dark"]
        )
        self.cracked_label.pack(side="left", padx=(15, 0))
        
        # ============== USERNAME ==============
        username_frame = tk.Frame(right_panel, bg=t["bg_dark"])
        username_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            username_frame, text="Username:", font=("Segoe UI", 10),
            fg=t["text_secondary"], bg=t["bg_dark"]
        ).pack(side="left", padx=(0, 10))
        
        self.username_entry = tk.Entry(
            username_frame, textvariable=self.username, font=("Segoe UI", 11),
            fg=t["text_primary"], bg=t["bg_input"],
            insertbackground=t["text_primary"],
            relief="flat", width=30
        )
        self.username_entry.pack(side="left", ipady=8, padx=2)
        self.username_entry.bind("<KeyRelease>", self.on_username_change)
        
        # ============== VERSION ==============
        version_frame = tk.Frame(right_panel, bg=t["bg_dark"])
        version_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            version_frame, text="Version:", font=("Segoe UI", 10),
            fg=t["text_secondary"], bg=t["bg_dark"]
        ).pack(side="left", padx=(0, 10))
        
        version_container = tk.Frame(version_frame, bg=t["bg_input"])
        version_container.pack(side="left")
        
        self.version_combo = ttk.Combobox(
            version_container, textvariable=self.version,
            state="readonly", width=35, style="Cat.TCombobox",
            font=("Segoe UI", 10)
        )
        self.version_combo.pack(side="left", ipady=6)
        
        refresh_btn = tk.Label(
            version_container, text="↻", font=("Segoe UI", 14),
            fg=t["text_secondary"], bg=t["bg_input"],
            padx=10, cursor="hand2"
        )
        refresh_btn.pack(side="left")
        refresh_btn.bind("<Button-1>", lambda e: self.load_versions())
        refresh_btn.bind("<Enter>", lambda e: refresh_btn.config(fg=t["text_primary"]))
        refresh_btn.bind("<Leave>", lambda e: refresh_btn.config(fg=t["text_secondary"]))
        
        # ============== RAM ==============
        ram_frame = tk.Frame(right_panel, bg=t["bg_dark"])
        ram_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            ram_frame, text="RAM:", font=("Segoe UI", 10),
            fg=t["text_secondary"], bg=t["bg_dark"]
        ).pack(side="left", padx=(0, 10))
        
        self.ram_display = tk.Label(
            ram_frame, text="4096 MB", font=("Segoe UI", 10, "bold"),
            fg=t["accent_green"], bg=t["bg_dark"], width=10
        )
        self.ram_display.pack(side="left")
        
        ram_slider = tk.Scale(
            ram_frame, variable=self.ram, from_=1, to=16,
            orient="horizontal", length=300,
            bg=t["bg_dark"], fg=t["text_primary"],
            highlightthickness=0, troughcolor=t["bg_input"],
            activebackground=t["accent_green"],
            sliderrelief="flat", sliderlength=20, width=12,
            showvalue=False, command=self.on_ram_change
        )
        ram_slider.pack(side="left", padx=(10, 0))
        
        # ============== OPTIONS ==============
        options_frame = tk.Frame(right_panel, bg=t["bg_dark"])
        options_frame.pack(fill="x", pady=(10, 20))
        
        self.fullscreen_var = tk.BooleanVar(value=False)
        self.download_assets_var = tk.BooleanVar(value=True)
        
        for text, var in [("Fullscreen", self.fullscreen_var), ("Download All Assets", self.download_assets_var)]:
            cb_frame = tk.Frame(options_frame, bg=t["bg_dark"])
            cb_frame.pack(side="left", padx=(0, 25))
            
            cb = tk.Checkbutton(
                cb_frame, text=text, variable=var,
                font=("Segoe UI", 10), fg=t["text_secondary"],
                bg=t["bg_dark"], activebackground=t["bg_dark"],
                activeforeground=t["text_primary"],
                selectcolor=t["bg_input"], cursor="hand2"
            )
            cb.pack()
        
        # ============== BOTTOM BAR ==============
        self.bottom_bar = tk.Frame(self.root, bg=t["bg_darker"], height=80)
        self.bottom_bar.pack(side="bottom", fill="x")
        self.bottom_bar.pack_propagate(False)
        
        status_frame = tk.Frame(self.bottom_bar, bg=t["bg_darker"])
        status_frame.pack(side="left", padx=20, pady=10)
        
        self.status_label = tk.Label(
            status_frame, textvariable=self.status_text, font=("Segoe UI", 9),
            fg=t["text_secondary"], bg=t["bg_darker"]
        )
        self.status_label.pack(anchor="w")
        
        self.progress_bar = ttk.Progressbar(
            status_frame, mode="determinate", length=400,
            style="Cat.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(anchor="w", pady=(5, 0))
        
        # ============== PLAY BUTTON ==============
        play_container = tk.Frame(self.bottom_bar, bg=t["bg_darker"])
        play_container.pack(side="right", padx=20, pady=15)
        
        self.play_button = tk.Button(
            play_container, text="🐱  PLAY MINECRAFT", font=("Segoe UI", 14, "bold"),
            fg="#ffffff", bg=t["button_play"],
            activeforeground="#ffffff",
            activebackground=t["button_play_hover"],
            relief="flat", cursor="hand2", padx=40, pady=12,
            command=self.play
        )
        self.play_button.pack()
        
        self.play_button.bind("<Enter>", lambda e: self.play_button.config(bg=self.current_theme["button_play_hover"]))
        self.play_button.bind("<Leave>", lambda e: self.play_button.config(bg=self.current_theme["button_play"]))
    
    # ============== EVENT HANDLERS ==============
    def on_account_type_change(self, event=None):
        t = self.current_theme
        acc_type = self.account_type.get()
        
        if acc_type == "Cat Client":
            self.cracked_label.config(text="✓ OFFLINE MODE", fg=t["accent_green"])
            self.account_indicator.config(text="Cat Client Account", fg=t["accent_green"])
            self.username_entry.config(state="normal")
        elif acc_type == "Microsoft Account":
            self.cracked_label.config(text="⚠ REQUIRES LOGIN", fg=t["accent_orange"])
            self.account_indicator.config(text="Not Logged In", fg=t["accent_orange"])
            messagebox.showinfo("Cat Client", 
                "Microsoft authentication is not available.\n\n"
                "Use 'Cat Client' mode for offline play! 🐱")
            self.account_type.set("Cat Client")
            self.on_account_type_change()
        else:
            self.cracked_label.config(text="⚠ DEPRECATED", fg=t["accent_orange"])
            messagebox.showinfo("Cat Client", 
                "Mojang accounts have been migrated to Microsoft.\n\n"
                "Use 'Cat Client' mode for offline play! 🐱")
            self.account_type.set("Cat Client")
            self.on_account_type_change()
    
    def on_username_change(self, event=None):
        if hasattr(self, '_skin_timer'):
            self.root.after_cancel(self._skin_timer)
        self._skin_timer = self.root.after(600, self.update_skin)
    
    def on_ram_change(self, value):
        mb = int(float(value)) * 1024
        self.ram_display.config(text=f"{mb} MB")
    
    def update_skin(self):
        username = self.username.get().strip()
        if not username:
            self.skin_label.config(text="🐱", image="", font=("Segoe UI", 48))
            return
        
        def load():
            try:
                url = f"{SKIN_SERVER}/head/{username}/150.png"
                req = urllib.request.Request(url, headers={'User-Agent': 'CatClient/1.0'})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = resp.read()
                
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(io.BytesIO(data))
                    self.skin_photo = ImageTk.PhotoImage(img)
                    self.root.after(0, lambda: self.skin_label.config(image=self.skin_photo, text=""))
                except ImportError:
                    self.root.after(0, lambda: self.skin_label.config(text=f"🐱\n{username[:8]}", font=("Segoe UI", 24)))
            except:
                self.root.after(0, lambda: self.skin_label.config(text=f"🐱\n{username[:8]}", font=("Segoe UI", 24)))
        
        threading.Thread(target=load, daemon=True).start()
    
    def load_versions(self):
        self.status_text.set("Loading versions... 🐱")
        
        def load():
            try:
                req = urllib.request.Request(VERSION_MANIFEST, headers={'User-Agent': 'CatClient/1.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                
                versions = []
                for v in data["versions"]:
                    if v["type"] == "release":
                        versions.append(f"{v['id']} (release)")
                    elif v["type"] == "snapshot" and len(versions) < 60:
                        versions.append(f"{v['id']} (snapshot)")
                    
                    if len(versions) >= 80:
                        break
                
                self.root.after(0, lambda: self.set_versions(versions))
            except:
                fallback = ["1.21.4 (release)", "1.20.1 (release)", "1.19.4 (release)", "1.18.2 (release)"]
                self.root.after(0, lambda: self.set_versions(fallback))
        
        threading.Thread(target=load, daemon=True).start()
    
    def set_versions(self, versions):
        self.version_combo["values"] = versions
        if versions:
            self.version.set(versions[0])
        self.status_text.set("Ready to play 🐱")
    
    # ============== DOWNLOAD & LAUNCH ==============
    def download_file(self, url, dest_path, expected_hash=None):
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if dest_path.exists() and expected_hash:
                if calculate_sha1(dest_path) == expected_hash:
                    return True
            
            req = urllib.request.Request(url, headers={'User-Agent': 'CatClient/1.0'})
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(dest_path, 'wb') as f:
                    f.write(resp.read())
            
            return True
        except Exception as e:
            print(f"Download failed: {e}")
            return False
    
    def download_version(self, version_id, progress_cb=None, status_cb=None):
        actual_id = version_id.split(" (")[0] if " (" in version_id else version_id
        
        if status_cb:
            status_cb(f"Fetching {actual_id}... 🐱")
        
        req = urllib.request.Request(VERSION_MANIFEST, headers={'User-Agent': 'CatClient/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            manifest = json.loads(resp.read().decode())
        
        version_url = None
        for v in manifest["versions"]:
            if v["id"] == actual_id:
                version_url = v["url"]
                break
        
        if not version_url:
            raise ValueError(f"Version {actual_id} not found")
        
        req = urllib.request.Request(version_url, headers={'User-Agent': 'CatClient/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            version_info = json.loads(resp.read().decode())
        
        version_dir = GAME_DIR / "versions" / actual_id
        version_dir.mkdir(parents=True, exist_ok=True)
        natives_dir = version_dir / "natives"
        natives_dir.mkdir(parents=True, exist_ok=True)
        libs_dir = GAME_DIR / "libraries"
        libs_dir.mkdir(parents=True, exist_ok=True)
        
        version_json_path = version_dir / f"{actual_id}.json"
        with open(version_json_path, 'w') as f:
            json.dump(version_info, f, indent=2)
        
        jar_path = version_dir / f"{actual_id}.jar"
        if not jar_path.exists():
            if status_cb:
                status_cb(f"Downloading {actual_id}.jar... 🐱")
            client_url = version_info["downloads"]["client"]["url"]
            client_sha1 = version_info["downloads"]["client"].get("sha1")
            self.download_file(client_url, jar_path, client_sha1)
        
        libraries = version_info.get("libraries", [])
        total = len(libraries)
        os_name = get_os_name()
        
        for i, lib in enumerate(libraries):
            if "rules" in lib and not check_rules(lib["rules"]):
                continue
            
            if status_cb and i % 5 == 0:
                name = lib.get("name", "").split(":")[-1]
                status_cb(f"Libraries ({i}/{total}): {name} 🐱")
            
            if "downloads" in lib:
                if "artifact" in lib["downloads"]:
                    artifact = lib["downloads"]["artifact"]
                    lib_path = libs_dir / artifact["path"]
                    if not lib_path.exists():
                        self.download_file(artifact["url"], lib_path, artifact.get("sha1"))
                
                if "natives" in lib:
                    native_key = lib["natives"].get(os_name, "")
                    if "${arch}" in native_key:
                        bits = "64" if get_arch() in ("x64", "arm64") else "32"
                        native_key = native_key.replace("${arch}", bits)
                    
                    if native_key and "classifiers" in lib["downloads"]:
                        native_info = lib["downloads"]["classifiers"].get(native_key)
                        if native_info:
                            native_path = libs_dir / native_info["path"]
                            if not native_path.exists():
                                self.download_file(native_info["url"], native_path, native_info.get("sha1"))
                            
                            try:
                                with zipfile.ZipFile(native_path, 'r') as z:
                                    for f in z.namelist():
                                        if not f.startswith("META-INF/"):
                                            if f.endswith(('.so', '.dll', '.dylib', '.jnilib')):
                                                target = natives_dir / Path(f).name
                                                with z.open(f) as src, open(target, 'wb') as dst:
                                                    dst.write(src.read())
                                                if sys.platform != "win32":
                                                    os.chmod(target, 0o755)
                            except:
                                pass
        
        if self.download_assets_var.get():
            asset_index = version_info["assetIndex"]
            asset_index_id = asset_index["id"]
            asset_index_url = asset_index["url"]
            
            if status_cb:
                status_cb(f"Downloading assets... 🐱")
            
            asset_downloader = AssetDownloader(
                GAME_DIR,
                progress_callback=progress_cb,
                status_callback=status_cb
            )
            
            asset_downloader.download_all_assets(asset_index_id, asset_index_url)
        else:
            asset_index = version_info["assetIndex"]
            index_path = GAME_DIR / "assets" / "indexes" / f"{asset_index['id']}.json"
            if not index_path.exists():
                self.download_file(asset_index["url"], index_path, asset_index.get("sha1"))
        
        if status_cb:
            status_cb(f"{actual_id} ready! 🐱")
        
        return version_info, actual_id
    
    def play(self):
        username = self.username.get().strip()
        if not username:
            messagebox.showwarning("Cat Client", "Enter a username! 🐱")
            return
        
        if not all(c.isalnum() or c == "_" for c in username):
            messagebox.showwarning("Cat Client", "Invalid username! Use only letters, numbers, underscore. 🐱")
            return
        
        if len(username) < 3 or len(username) > 16:
            messagebox.showwarning("Cat Client", "Username must be 3-16 characters! 🐱")
            return
        
        version = self.version.get()
        if not version:
            messagebox.showwarning("Cat Client", "Select a version! 🐱")
            return
        
        if self.account_type.get() != "Cat Client":
            messagebox.showwarning("Cat Client", "Only Cat Client (offline) mode is available. 🐱")
            self.account_type.set("Cat Client")
            return
        
        self.play_button.config(state="disabled", text="LAUNCHING... 🐱")
        self.progress_bar.config(value=0)
        
        def launch():
            try:
                version_info, actual_id = self.download_version(
                    version,
                    progress_cb=lambda p: self.root.after(0, lambda: self.progress_bar.config(value=p)),
                    status_cb=lambda s: self.root.after(0, lambda: self.status_text.set(s))
                )
                
                version_dir = GAME_DIR / "versions" / actual_id
                jar_path = version_dir / f"{actual_id}.jar"
                natives_dir = version_dir / "natives"
                libs_dir = GAME_DIR / "libraries"
                
                classpath_parts = []
                for lib in version_info.get("libraries", []):
                    if "rules" in lib and not check_rules(lib["rules"]):
                        continue
                    if "downloads" in lib and "artifact" in lib["downloads"]:
                        lib_path = libs_dir / lib["downloads"]["artifact"]["path"]
                        if lib_path.exists():
                            classpath_parts.append(str(lib_path))
                
                classpath_parts.append(str(jar_path))
                classpath = CLASSPATH_SEP.join(classpath_parts)
                
                main_class = version_info.get("mainClass", "net.minecraft.client.main.Main")
                offline_uuid = generate_offline_uuid(username)
                ram_mb = self.ram.get() * 1024
                
                args = [
                    self.java_bin,
                    f"-Xmx{ram_mb}M",
                    "-Xms512M",
                    f"-Djava.library.path={natives_dir.resolve()}",
                    "-Dminecraft.launcher.brand=CatClient",
                    "-Dminecraft.launcher.version=1.0",
                    "-cp", classpath,
                    main_class,
                    "--username", username,
                    "--version", actual_id,
                    "--gameDir", str(GAME_DIR.resolve()),
                    "--assetsDir", str((GAME_DIR / "assets").resolve()),
                    "--assetIndex", version_info["assetIndex"]["id"],
                    "--uuid", offline_uuid,
                    "--accessToken", "0",
                    "--userType", "legacy",
                    "--versionType", version_info.get("type", "release")
                ]
                
                if self.fullscreen_var.get():
                    args.extend(["--fullscreen"])
                
                self.root.after(0, lambda: self.status_text.set(f"Launching {actual_id}... 🐱"))
                
                popen_kwargs = {
                    'cwd': str(GAME_DIR),
                    'stdout': subprocess.PIPE,
                    'stderr': subprocess.STDOUT,
                    'text': True
                }
                
                if sys.platform == "win32":
                    popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                
                process = subprocess.Popen(args, **popen_kwargs)
                
                def monitor():
                    try:
                        for line in process.stdout:
                            print(f"[MC] {line}", end="")
                        process.wait()
                        self.root.after(0, lambda: self.status_text.set("Game closed 🐱"))
                    except:
                        pass
                
                threading.Thread(target=monitor, daemon=True).start()
                
                self.root.after(2000, lambda: self.status_text.set(f"Playing {actual_id} 🐱"))
                
            except Exception as e:
                import traceback
                self.root.after(0, lambda: self.status_text.set("Launch failed! 😿"))
                self.root.after(0, lambda: messagebox.showerror("Cat Client", f"Error:\n{e}"))
                print(traceback.format_exc())
            finally:
                self.root.after(0, lambda: self.play_button.config(state="normal", text="🐱  PLAY MINECRAFT"))
        
        threading.Thread(target=launch, daemon=True).start()


# ============== MAIN ==============
if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
    
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("Install Pillow for skin previews: pip install pillow")
    
    root = tk.Tk()
    app = CatClientApp(root)
    root.mainloop()

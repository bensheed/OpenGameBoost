"""
OpenGameBoost - Open Source Gaming Optimizer
A transparent, open-source alternative for Windows gaming optimization.
"""
import sys
import os
import logging
import threading
from typing import Optional

# Ensure log directory exists
if os.name == 'nt':
    _log_dir = os.path.join(os.environ.get('APPDATA', '.'), 'OpenGameBoost')
    os.makedirs(_log_dir, exist_ok=True)
    _log_file = os.path.join(_log_dir, 'app.log')
else:
    _log_file = None

# Set up logging
_handlers = [logging.StreamHandler()]
if _log_file:
    _handlers.append(logging.FileHandler(_log_file, mode='a'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=_handlers
)
logger = logging.getLogger(__name__)

# Import UI library
try:
    import customtkinter as ctk
    CTK_AVAILABLE = True
except ImportError:
    CTK_AVAILABLE = False
    logger.warning("customtkinter not available, using tkinter")
    import tkinter as tk
    from tkinter import ttk

# Import services
from config import Config

# Conditional imports for Windows-specific services
if os.name == 'nt':
    from services import (
        GameDetectorService,
        MemoryService,
        NetworkService,
        PowerService,
        RegistryService,
        SuspendService,
    )


class ServiceCard(ctk.CTkFrame if CTK_AVAILABLE else object):
    """A card widget representing a service with toggle and status."""
    
    def __init__(self, parent, title: str, description: str, 
                 icon: str = "⚡", on_toggle=None, on_optimize=None):
        if CTK_AVAILABLE:
            super().__init__(parent, corner_radius=10, fg_color="#1a1a2e")
        
        self.title = title
        self.on_toggle = on_toggle
        self.on_optimize = on_optimize
        self.enabled = True
        self.status = "Ready"
        
        self._setup_ui(title, description, icon)
    
    def _setup_ui(self, title: str, description: str, icon: str):
        if not CTK_AVAILABLE:
            return
        
        # Header frame
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))
        
        # Icon and title
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="x", expand=True)
        
        icon_label = ctk.CTkLabel(
            title_frame, text=icon, font=("Segoe UI", 24),
            text_color="#00d4ff"
        )
        icon_label.pack(side="left", padx=(0, 10))
        
        title_label = ctk.CTkLabel(
            title_frame, text=title, font=("Segoe UI", 16, "bold"),
            text_color="#ffffff"
        )
        title_label.pack(side="left")
        
        # Toggle switch
        self.toggle_var = ctk.BooleanVar(value=True)
        self.toggle = ctk.CTkSwitch(
            header, text="", variable=self.toggle_var,
            command=self._on_toggle_changed,
            progress_color="#00d4ff", button_color="#ffffff",
            button_hover_color="#e0e0e0"
        )
        self.toggle.pack(side="right")
        
        # Description
        desc_label = ctk.CTkLabel(
            self, text=description, font=("Segoe UI", 11),
            text_color="#888888", wraplength=280, justify="left"
        )
        desc_label.pack(fill="x", padx=15, pady=(0, 10))
        
        # Status and button frame
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.status_label = ctk.CTkLabel(
            action_frame, text="● Ready", font=("Segoe UI", 11),
            text_color="#00ff88"
        )
        self.status_label.pack(side="left")
        
        self.optimize_btn = ctk.CTkButton(
            action_frame, text="Optimize", width=80, height=28,
            font=("Segoe UI", 11), fg_color="#00d4ff",
            hover_color="#00a8cc", text_color="#000000",
            command=self._on_optimize_clicked
        )
        self.optimize_btn.pack(side="right")
    
    def _on_toggle_changed(self):
        self.enabled = self.toggle_var.get()
        if self.on_toggle:
            self.on_toggle(self.enabled)
        self._update_status()
    
    def _on_optimize_clicked(self):
        if self.on_optimize and self.enabled:
            self.set_status("Optimizing...", "#ffaa00")
            # Run optimization in thread to not block UI
            threading.Thread(target=self._run_optimization, daemon=True).start()
    
    def _run_optimization(self):
        try:
            if self.on_optimize:
                result = self.on_optimize()
                if result:
                    self.set_status("Optimized", "#00ff88")
                else:
                    self.set_status("Partial", "#ffaa00")
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            self.set_status("Error", "#ff4444")
    
    def _update_status(self):
        if self.enabled:
            self.set_status("Ready", "#00ff88")
            self.optimize_btn.configure(state="normal")
        else:
            self.set_status("Disabled", "#666666")
            self.optimize_btn.configure(state="disabled")
    
    def set_status(self, status: str, color: str = "#00ff88"):
        if CTK_AVAILABLE:
            self.status = status
            self.status_label.configure(text=f"● {status}", text_color=color)


class OpenGameBoostApp:
    """Main application class for OpenGameBoost."""
    
    VERSION = "1.0.0"
    
    def __init__(self):
        self.config = Config()
        self.game_mode_active = False
        
        # Initialize UI label attributes (set to None, will be created if CTK is available)
        self.mem_label = None
        self.power_label = None
        self.system_label = None
        
        # Initialize services (Windows only)
        if os.name == 'nt':
            self.suspend_service = SuspendService()
            self.game_detector = GameDetectorService()
            self.memory_service = MemoryService()
            self.network_service = NetworkService()
            self.power_service = PowerService()
            self.registry_service = RegistryService()
            
            # Configure services from config
            self._configure_services()
            
            # Set up game detection callbacks
            self.game_detector.on_game_detected = self._on_game_detected
            self.game_detector.on_game_closed = self._on_game_closed
        else:
            self.suspend_service = None
            self.game_detector = None
            self.memory_service = None
            self.network_service = None
            self.power_service = None
            self.registry_service = None
        
        # Set up UI
        self._setup_ui()
    
    def _configure_services(self):
        """Configure services from saved config."""
        if self.game_detector:
            self.game_detector.enabled = self.config.get("game_detector", "enabled", True)
            self.game_detector.auto_optimize = self.config.get("game_detector", "auto_optimize", True)
        
        if self.memory_service:
            self.memory_service.enabled = self.config.get("memory", "enabled", True)
        
        if self.network_service:
            self.network_service.enabled = self.config.get("network", "enabled", True)
            self.network_service.disable_nagle = self.config.get("network", "disable_nagle", True)
            self.network_service.disable_netbios = self.config.get("network", "disable_netbios", True)
        
        if self.power_service:
            self.power_service.enabled = self.config.get("power", "enabled", True)
        
        if self.registry_service:
            self.registry_service.enabled = self.config.get("registry", "enabled", True)
    
    def _setup_ui(self):
        """Set up the main UI window."""
        if CTK_AVAILABLE:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
            
            self.root = ctk.CTk()
            self.root.title("OpenGameBoost")
            self.root.geometry("520x620")
            self.root.minsize(500, 600)
            self.root.configure(fg_color="#0a0a12")
            
            # Set window icon (if available)
            try:
                self.root.iconbitmap("assets/icon.ico")
            except:
                pass
            
            # Configure grid
            self.root.grid_columnconfigure(0, weight=1)
            self.root.grid_rowconfigure(1, weight=1)
            
            # Create the focused UI
            self._create_main_ui()
        else:
            # Fallback to basic tkinter
            self.root = tk.Tk()
            self.root.title("OpenGameBoost")
            self.root.geometry("420x650")
            label = tk.Label(self.root, text="OpenGameBoost - Install customtkinter for full UI")
            label.pack(pady=20)
    
    def _create_main_ui(self):
        """Create the main focused UI - Game Mode with toggles."""
        # Main container
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # === LOGO SECTION ===
        logo_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        logo_frame.pack(pady=(10, 15))
        
        # Logo icon
        logo = ctk.CTkLabel(
            logo_frame, text="⚡", font=("Segoe UI", 36),
            text_color="#00d4ff"
        )
        logo.pack()
        
        title = ctk.CTkLabel(
            logo_frame, text="OpenGameBoost",
            font=("Segoe UI", 18, "bold"), text_color="#ffffff"
        )
        title.pack(pady=(2, 0))
        
        subtitle = ctk.CTkLabel(
            logo_frame, text="Open Source Gaming Optimizer",
            font=("Segoe UI", 10), text_color="#666666"
        )
        subtitle.pack()
        
        # === MAIN GAME MODE BUTTON ===
        self.game_mode_btn = ctk.CTkButton(
            main_frame,
            text="ACTIVATE GAME MODE",
            width=260, height=45,
            font=("Segoe UI", 14, "bold"),
            fg_color="#00d4ff",
            hover_color="#00a8cc",
            text_color="#000000",
            corner_radius=10,
            command=self._toggle_game_mode
        )
        self.game_mode_btn.pack(pady=(8, 15))
        
        # Status indicator
        self.status_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.status_frame.pack(pady=(0, 20))
        
        self.status_indicator = ctk.CTkLabel(
            self.status_frame, text="●", font=("Segoe UI", 14),
            text_color="#666666"
        )
        self.status_indicator.pack(side="left", padx=(0, 8))
        
        self.status_text = ctk.CTkLabel(
            self.status_frame, text="Ready",
            font=("Segoe UI", 12), text_color="#888888"
        )
        self.status_text.pack(side="left")
        
        # === TWO COLUMN LAYOUT FOR TOGGLES ===
        columns_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        columns_frame.pack(fill="x", pady=(10, 15))
        columns_frame.grid_columnconfigure((0, 1), weight=1)
        
        # --- LEFT COLUMN: GAME MODE MODULES ---
        left_frame = ctk.CTkFrame(columns_frame, fg_color="#12121e", corner_radius=12)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        left_title = ctk.CTkLabel(
            left_frame, text="GAME MODE",
            font=("Segoe UI", 9, "bold"), text_color="#666666"
        )
        left_title.pack(anchor="w", padx=15, pady=(12, 8))
        
        # Toggle: Suspend Explorer
        self.suspend_explorer_var = ctk.BooleanVar(value=True)
        self._create_toggle_row_compact(
            left_frame, "Suspend Explorer",
            self.suspend_explorer_var,
            desc="Pause desktop shell"
        )
        
        # Toggle: Suspend Browsers
        self.suspend_browsers_var = ctk.BooleanVar(value=True)
        self._create_toggle_row_compact(
            left_frame, "Suspend Browsers",
            self.suspend_browsers_var,
            desc="Pause Chrome, Firefox, Edge"
        )
        
        # Toggle: Suspend Launchers
        self.suspend_launchers_var = ctk.BooleanVar(value=True)
        self._create_toggle_row_compact(
            left_frame, "Suspend Launchers",
            self.suspend_launchers_var,
            desc="Pause Steam, Epic, etc."
        )
        
        # Toggle: Memory Optimization
        self.memory_opt_var = ctk.BooleanVar(value=True)
        self._create_toggle_row_compact(
            left_frame, "Memory Optimization",
            self.memory_opt_var,
            last=True,
            desc="Flush unused RAM"
        )
        
        # --- RIGHT COLUMN: ADVANCED ---
        right_frame = ctk.CTkFrame(columns_frame, fg_color="#12121e", corner_radius=12)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        right_title = ctk.CTkLabel(
            right_frame, text="ADVANCED",
            font=("Segoe UI", 9, "bold"), text_color="#666666"
        )
        right_title.pack(anchor="w", padx=15, pady=(12, 8))
        
        # Toggle: Power Optimization
        self.power_opt_var = ctk.BooleanVar(value=True)
        self._create_toggle_row_compact(
            right_frame, "High Perf. Power",
            self.power_opt_var,
            desc="Use performance power plan"
        )
        
        # Toggle: Network Optimization
        self.network_opt_var = ctk.BooleanVar(value=False)
        self._create_toggle_row_compact(
            right_frame, "Network Tweaks",
            self.network_opt_var,
            desc="Disable Nagle, NetBIOS"
        )
        
        # Toggle: GPU & Registry Tweaks
        self.registry_opt_var = ctk.BooleanVar(value=False)
        self._create_toggle_row_compact(
            right_frame, "GPU Priority",
            self.registry_opt_var,
            desc="Set GPU scheduling priority"
        )
        
        # Toggle: Auto Game Detection
        self.game_detect_var = ctk.BooleanVar(value=False)
        self._create_toggle_row_compact(
            right_frame, "Auto Detection",
            self.game_detect_var,
            last=True,
            command=self._toggle_game_detection,
            desc="Activate when games launch"
        )
        
        # === FOOTER ===
        footer = ctk.CTkFrame(main_frame, fg_color="transparent")
        footer.pack(side="bottom", fill="x", pady=(20, 0))
        
        # Copy specs button
        specs_btn = ctk.CTkButton(
            footer,
            text="📋 Copy System Specs",
            width=200, height=35,
            font=("Segoe UI", 11),
            fg_color="transparent",
            hover_color="#1a1a2e",
            text_color="#00d4ff",
            border_width=1,
            border_color="#333344",
            command=self._copy_specs
        )
        specs_btn.pack(pady=(0, 10))
        
        version_label = ctk.CTkLabel(
            footer, text=f"v{self.VERSION} • Open Source • MIT License",
            font=("Segoe UI", 9), text_color="#444444"
        )
        version_label.pack()
    
    def _create_toggle_row_compact(self, parent, title: str,
                                    variable: ctk.BooleanVar, last: bool = False,
                                    command: callable = None, desc: str = None):
        """Create a compact toggle row with title and optional description."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0, 12 if last else 5))
        
        text_frame = ctk.CTkFrame(row, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)
        
        title_label = ctk.CTkLabel(
            text_frame, text=title,
            font=("Segoe UI", 11), text_color="#ffffff",
            anchor="w"
        )
        title_label.pack(anchor="w")
        
        if desc:
            desc_label = ctk.CTkLabel(
                text_frame, text=desc,
                font=("Segoe UI", 8), text_color="#555555",
                anchor="w"
            )
            desc_label.pack(anchor="w")
        
        toggle = ctk.CTkSwitch(
            row, text="", variable=variable,
            width=40, height=20,
            progress_color="#00d4ff",
            button_color="#ffffff",
            button_hover_color="#e0e0e0",
            fg_color="#333344",
            command=command
        )
        toggle.pack(side="right")
    
    def _toggle_game_detection(self):
        """Toggle auto game detection on/off."""
        if self.game_detect_var.get():
            # Enable game detection
            if self.game_detector:
                self.game_detector.on_game_detected = self._on_game_detected
                self.game_detector.on_game_closed = self._on_game_closed
                self.game_detector.start()
                logger.info("Game detection enabled")
        else:
            # Disable game detection
            if self.game_detector:
                self.game_detector.stop()
                logger.info("Game detection disabled")
    
    def _toggle_game_mode(self):
        """Toggle Game Mode on/off."""
        if self.game_mode_active:
            self._deactivate_game_mode()
        else:
            self._activate_game_mode()
    
    def _activate_game_mode(self):
        """Activate Game Mode - suspend processes and apply optimizations."""
        self.game_mode_btn.configure(
            text="⏳ Activating...",
            state="disabled"
        )
        self.root.update()
        
        def run_activation():
            try:
                results = {"suspended": 0}
                
                # Configure and run suspend service from toggles
                if self.suspend_service:
                    self.suspend_service.should_suspend_explorer = self.suspend_explorer_var.get()
                    self.suspend_service.should_suspend_browsers = self.suspend_browsers_var.get()
                    self.suspend_service.should_suspend_launchers = self.suspend_launchers_var.get()
                    
                    result = self.suspend_service.activate_game_mode()
                    results["suspended"] = result.get("total_suspended", 0)
                
                # Memory optimization
                if self.memory_opt_var.get() and self.memory_service:
                    self.memory_service.optimize_memory()
                
                # Power optimization
                if self.power_opt_var.get() and self.power_service:
                    self.power_service.set_high_performance()
                
                # Network optimization
                if self.network_opt_var.get() and self.network_service:
                    self.network_service.optimize_network()
                
                # GPU/Registry tweaks
                if self.registry_opt_var.get() and self.registry_service:
                    self.registry_service.apply_all_optimizations()
                
                # Update UI on main thread
                self.root.after(0, lambda: self._on_game_mode_activated(results))
                
            except Exception as e:
                logger.error(f"Activation error: {e}")
                self.root.after(0, self._on_game_mode_error)
        
        threading.Thread(target=run_activation, daemon=True).start()
    
    def _on_game_mode_activated(self, results):
        """Called when Game Mode is activated."""
        self.game_mode_active = True
        self.game_mode_btn.configure(
            text="DEACTIVATE GAME MODE",
            fg_color="#ff4444",
            hover_color="#cc3333",
            text_color="#ffffff",
            state="normal"
        )
        self.status_indicator.configure(text_color="#00ff88")
        self.status_text.configure(
            text=f"Active • {results.get('suspended', 0)} processes suspended",
            text_color="#00ff88"
        )
    
    def _deactivate_game_mode(self):
        """Deactivate Game Mode - resume all suspended processes."""
        self.game_mode_btn.configure(
            text="⏳ Restoring...",
            state="disabled"
        )
        self.root.update()
        
        def run_deactivation():
            try:
                # Resume suspended processes
                if self.suspend_service:
                    self.suspend_service.deactivate_game_mode()
                
                # Restore power plan
                if self.power_service:
                    self.power_service.restore_power_plan()
                
                # Restore network settings (if they were changed)
                if self.network_opt_var.get() and self.network_service:
                    self.network_service.restore_network()
                
                self.root.after(0, self._on_game_mode_deactivated)
                
            except Exception as e:
                logger.error(f"Deactivation error: {e}")
                self.root.after(0, self._on_game_mode_error)
        
        threading.Thread(target=run_deactivation, daemon=True).start()
    
    def _on_game_mode_deactivated(self):
        """Called when Game Mode is deactivated."""
        self.game_mode_active = False
        self.game_mode_btn.configure(
            text="ACTIVATE GAME MODE",
            fg_color="#00d4ff",
            hover_color="#00a8cc",
            text_color="#000000",
            state="normal"
        )
        self.status_indicator.configure(text_color="#666666")
        self.status_text.configure(text="Ready", text_color="#888888")
    
    def _on_game_mode_error(self):
        """Called when an error occurs."""
        self.game_mode_btn.configure(
            text="ACTIVATE GAME MODE",
            fg_color="#00d4ff",
            hover_color="#00a8cc",
            text_color="#000000",
            state="normal"
        )
        self.status_indicator.configure(text_color="#ff4444")
        self.status_text.configure(text="Error - check logs", text_color="#ff4444")
    
    def _copy_specs(self):
        """Copy system specs to clipboard."""
        specs = []
        specs.append("=== OpenGameBoost System Specs ===")
        
        if self.memory_service:
            mem = self.memory_service.get_memory_info()
            specs.append(f"RAM: {mem.get('total_gb', 'N/A')} GB")
        
        if self.power_service:
            specs.append(f"Power Plan: {self.power_service.get_current_plan_name()}")
            system_type = "Desktop" if self.power_service.is_desktop else "Laptop"
            specs.append(f"System Type: {system_type}")
        
        try:
            import platform
            specs.append(f"OS: {platform.system()} {platform.release()}")
            specs.append(f"Processor: {platform.processor()}")
        except:
            pass
        
        specs_text = "\n".join(specs)
        
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(specs_text)
            self.status_text.configure(text="Specs copied!", text_color="#00d4ff")
            self.root.after(2000, lambda: self.status_text.configure(
                text="Ready" if not self.game_mode_active else f"Active",
                text_color="#888888" if not self.game_mode_active else "#00ff88"
            ))
        except Exception as e:
            logger.error(f"Failed to copy specs: {e}")

    def _create_header(self):
        """Create the header section with logo and status."""
        header = ctk.CTkFrame(self.root, height=100, fg_color="#0f0f1a")
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(1, weight=1)
        
        # Logo and title
        logo_frame = ctk.CTkFrame(header, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Logo icon (stylized)
        logo = ctk.CTkLabel(
            logo_frame, text="🎮", font=("Segoe UI", 36)
        )
        logo.pack(side="left", padx=(0, 15))
        
        title_frame = ctk.CTkFrame(logo_frame, fg_color="transparent")
        title_frame.pack(side="left")
        
        title = ctk.CTkLabel(
            title_frame, text="OpenGameBoost",
            font=("Segoe UI", 24, "bold"), text_color="#ffffff"
        )
        title.pack(anchor="w")
        
        subtitle = ctk.CTkLabel(
            title_frame, text="Open Source Gaming Optimizer",
            font=("Segoe UI", 11), text_color="#888888"
        )
        subtitle.pack(anchor="w")
        
        # Status indicator
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.grid(row=0, column=1, padx=20, pady=15, sticky="e")
        
        self.mode_label = ctk.CTkLabel(
            status_frame, text="STANDBY MODE",
            font=("Segoe UI", 12, "bold"), text_color="#666666"
        )
        self.mode_label.pack(side="right", padx=10)
        
        self.mode_indicator = ctk.CTkLabel(
            status_frame, text="●", font=("Segoe UI", 20),
            text_color="#666666"
        )
        self.mode_indicator.pack(side="right")
    
    def _create_main_content(self):
        """Create the main content area with service cards."""
        # Create scrollable frame for content
        main_frame = ctk.CTkScrollableFrame(
            self.root, fg_color="#0a0a14",
            scrollbar_button_color="#333344",
            scrollbar_button_hover_color="#444455"
        )
        main_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        main_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Quick Actions Section
        quick_section = ctk.CTkFrame(main_frame, fg_color="transparent")
        quick_section.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(20, 10))
        
        section_title = ctk.CTkLabel(
            quick_section, text="⚡ Quick Actions",
            font=("Segoe UI", 14, "bold"), text_color="#ffffff"
        )
        section_title.pack(anchor="w", pady=(0, 10))
        
        # Quick action buttons
        btn_frame = ctk.CTkFrame(quick_section, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        self.boost_btn = ctk.CTkButton(
            btn_frame, text="🚀 BOOST NOW", width=200, height=50,
            font=("Segoe UI", 14, "bold"), fg_color="#00d4ff",
            hover_color="#00a8cc", text_color="#000000",
            command=self._boost_all
        )
        self.boost_btn.pack(side="left", padx=(0, 10))
        
        restore_btn = ctk.CTkButton(
            btn_frame, text="↩ Restore Defaults", width=150, height=50,
            font=("Segoe UI", 12), fg_color="#333344",
            hover_color="#444455", text_color="#ffffff",
            command=self._restore_all
        )
        restore_btn.pack(side="left", padx=(0, 10))
        
        # Game Detection Status
        self.game_status = ctk.CTkLabel(
            btn_frame, text="No games detected",
            font=("Segoe UI", 11), text_color="#666666"
        )
        self.game_status.pack(side="right", padx=10)
        
        # Services Section
        services_title = ctk.CTkLabel(
            main_frame, text="🔧 Optimization Services",
            font=("Segoe UI", 14, "bold"), text_color="#ffffff"
        )
        services_title.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))
        
        # Service Cards
        self.memory_card = ServiceCard(
            main_frame, "Memory Optimizer", 
            "Flushes unused memory from processes to free up RAM for your games.",
            icon="💾",
            on_toggle=lambda e: self._toggle_service("memory", e),
            on_optimize=self._optimize_memory
        )
        self.memory_card.grid(row=2, column=0, sticky="nsew", padx=(20, 10), pady=10)
        
        self.network_card = ServiceCard(
            main_frame, "Network Optimizer",
            "Disables Nagle's algorithm and NetBIOS to reduce network latency.",
            icon="🌐",
            on_toggle=lambda e: self._toggle_service("network", e),
            on_optimize=self._optimize_network
        )
        self.network_card.grid(row=2, column=1, sticky="nsew", padx=(10, 20), pady=10)
        
        self.power_card = ServiceCard(
            main_frame, "Power Optimizer",
            "Switches to High Performance power plan for maximum CPU/GPU performance.",
            icon="⚡",
            on_toggle=lambda e: self._toggle_service("power", e),
            on_optimize=self._optimize_power
        )
        self.power_card.grid(row=3, column=0, sticky="nsew", padx=(20, 10), pady=10)
        
        self.registry_card = ServiceCard(
            main_frame, "GPU & System Tweaks",
            "Applies registry optimizations for GPU priority and gaming performance.",
            icon="🎮",
            on_toggle=lambda e: self._toggle_service("registry", e),
            on_optimize=self._optimize_registry
        )
        self.registry_card.grid(row=3, column=1, sticky="nsew", padx=(10, 20), pady=10)
        
        # Game Detection Card
        self.game_card = ServiceCard(
            main_frame, "Game Detector",
            "Automatically detects running games and applies optimizations.",
            icon="🎯",
            on_toggle=lambda e: self._toggle_service("game_detector", e),
            on_optimize=self._scan_games
        )
        self.game_card.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        
        # System Info Section
        info_title = ctk.CTkLabel(
            main_frame, text="📊 System Status",
            font=("Segoe UI", 14, "bold"), text_color="#ffffff"
        )
        info_title.grid(row=5, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 10))
        
        info_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a2e", corner_radius=10)
        info_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        info_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Memory info
        self.mem_label = ctk.CTkLabel(
            info_frame, text="Memory: --", font=("Segoe UI", 12),
            text_color="#ffffff"
        )
        self.mem_label.grid(row=0, column=0, padx=20, pady=15)
        
        # Power info
        self.power_label = ctk.CTkLabel(
            info_frame, text="Power: --", font=("Segoe UI", 12),
            text_color="#ffffff"
        )
        self.power_label.grid(row=0, column=1, padx=20, pady=15)
        
        # System type
        self.system_label = ctk.CTkLabel(
            info_frame, text="System: --", font=("Segoe UI", 12),
            text_color="#ffffff"
        )
        self.system_label.grid(row=0, column=2, padx=20, pady=15)
        
        # Update system info
        self._update_system_info()
    
    def _create_footer(self):
        """Create the footer with version and links."""
        footer = ctk.CTkFrame(self.root, height=40, fg_color="#0f0f1a")
        footer.grid(row=2, column=0, sticky="ew")
        
        version_label = ctk.CTkLabel(
            footer, text=f"v{self.VERSION} | Open Source | MIT License",
            font=("Segoe UI", 10), text_color="#555555"
        )
        version_label.pack(side="left", padx=20, pady=10)
        
        github_btn = ctk.CTkButton(
            footer, text="⭐ GitHub", width=80, height=25,
            font=("Segoe UI", 10), fg_color="transparent",
            hover_color="#333344", text_color="#00d4ff",
            command=self._open_github
        )
        github_btn.pack(side="right", padx=20, pady=10)
    
    def _toggle_service(self, service: str, enabled: bool):
        """Toggle a service on/off."""
        self.config.set(service, "enabled", enabled)
        self.config.save()
        
        if service == "memory" and self.memory_service:
            self.memory_service.enabled = enabled
        elif service == "network" and self.network_service:
            self.network_service.enabled = enabled
        elif service == "power" and self.power_service:
            self.power_service.enabled = enabled
        elif service == "registry" and self.registry_service:
            self.registry_service.enabled = enabled
        elif service == "game_detector" and self.game_detector:
            self.game_detector.enabled = enabled
            if enabled:
                self.game_detector.start()
            else:
                self.game_detector.stop()
    
    def _optimize_memory(self) -> bool:
        """Run memory optimization."""
        if not self.memory_service:
            return False
        result = self.memory_service.optimize_memory()
        logger.info(f"Memory optimization: {result}")
        self._update_system_info()
        return result.get("status") == "completed"
    
    def _optimize_network(self) -> bool:
        """Run network optimization."""
        if not self.network_service:
            return False
        result = self.network_service.optimize_network()
        logger.info(f"Network optimization: {result}")
        return result.get("status") == "completed"
    
    def _optimize_power(self) -> bool:
        """Run power optimization."""
        if not self.power_service:
            return False
        result = self.power_service.optimize_power_settings()
        logger.info(f"Power optimization: {result}")
        self._update_system_info()
        return result.get("status") == "completed"
    
    def _optimize_registry(self) -> bool:
        """Run registry optimization."""
        if not self.registry_service:
            return False
        result = self.registry_service.apply_all_optimizations()
        logger.info(f"Registry optimization: {result}")
        return result.get("status") == "completed"
    
    def _scan_games(self) -> bool:
        """Scan for running games."""
        if not self.game_detector:
            return False
        self.game_detector._check_games()
        games = self.game_detector.get_running_games()
        if games:
            self.game_status.configure(text=f"Detected: {', '.join(games)}")
            self._set_game_mode(True)
        else:
            self.game_status.configure(text="No games detected")
            self._set_game_mode(False)
        return True
    
    def _boost_all(self):
        """Apply all optimizations."""
        self.boost_btn.configure(text="⏳ Boosting...", state="disabled")
        
        def run_boost():
            try:
                results = []
                if self.memory_service and self.memory_service.enabled:
                    self.memory_card.set_status("Optimizing...", "#ffaa00")
                    results.append(self._optimize_memory())
                    self.memory_card.set_status("Optimized", "#00ff88")
                
                if self.network_service and self.network_service.enabled:
                    self.network_card.set_status("Optimizing...", "#ffaa00")
                    results.append(self._optimize_network())
                    self.network_card.set_status("Optimized", "#00ff88")
                
                if self.power_service and self.power_service.enabled:
                    self.power_card.set_status("Optimizing...", "#ffaa00")
                    results.append(self._optimize_power())
                    self.power_card.set_status("Optimized", "#00ff88")
                
                if self.registry_service and self.registry_service.enabled:
                    self.registry_card.set_status("Optimizing...", "#ffaa00")
                    results.append(self._optimize_registry())
                    self.registry_card.set_status("Optimized", "#00ff88")
                
                self._set_game_mode(True)
                logger.info("All optimizations applied")
            finally:
                self.root.after(0, lambda: self.boost_btn.configure(
                    text="🚀 BOOST NOW", state="normal"
                ))
        
        threading.Thread(target=run_boost, daemon=True).start()
    
    def _restore_all(self):
        """Restore all settings to defaults."""
        if self.power_service:
            self.power_service.restore_power_plan()
        if self.network_service:
            self.network_service.restore_network()
        
        self._set_game_mode(False)
        self._update_system_info()
        
        # Reset card statuses
        for card in [self.memory_card, self.network_card, 
                     self.power_card, self.registry_card, self.game_card]:
            card.set_status("Ready", "#00ff88")
        
        logger.info("All settings restored to defaults")
    
    def _set_game_mode(self, active: bool):
        """Set the game mode indicator."""
        self.game_mode_active = active
        if active:
            self.mode_label.configure(text="GAME MODE ACTIVE", text_color="#00ff88")
            self.mode_indicator.configure(text_color="#00ff88")
        else:
            self.mode_label.configure(text="STANDBY MODE", text_color="#666666")
            self.mode_indicator.configure(text_color="#666666")
    
    def _update_system_info(self):
        """Update the system information display."""
        try:
            # Memory info
            if self.memory_service and self.mem_label:
                mem_info = self.memory_service.get_memory_info()
                if "percent" in mem_info:
                    self.mem_label.configure(
                        text=f"Memory: {mem_info['used_gb']:.1f} / {mem_info['total_gb']:.1f} GB ({mem_info['percent']:.0f}%)"
                    )
            
            # Power info
            if self.power_service and self.power_label:
                plan = self.power_service.get_current_plan_name()
                self.power_label.configure(text=f"Power: {plan}")
                
                if self.system_label:
                    system_type = "Desktop" if self.power_service.is_desktop else "Laptop"
                    self.system_label.configure(text=f"System: {system_type}")
        except Exception as e:
            logger.error(f"Error updating system info: {e}")
    
    def _on_game_detected(self, game_name: str):
        """Handle game detection event."""
        logger.info(f"Game detected: {game_name}")
        self.root.after(0, lambda: self._handle_game_detected(game_name))
    
    def _handle_game_detected(self, game_name: str):
        """Handle game detection on main thread."""
        self.game_status.configure(text=f"🎮 Playing: {game_name}")
        if self.game_detector.auto_optimize:
            self._boost_all()
    
    def _on_game_closed(self, game_name: str):
        """Handle game closed event."""
        logger.info(f"Game closed: {game_name}")
        self.root.after(0, lambda: self._handle_game_closed(game_name))
    
    def _handle_game_closed(self, game_name: str):
        """Handle game closed on main thread."""
        games = self.game_detector.get_running_games() if self.game_detector else []
        if games:
            self.game_status.configure(text=f"Detected: {', '.join(games)}")
        else:
            self.game_status.configure(text="No games detected")
            self._restore_all()
    
    def _open_github(self):
        """Open the GitHub repository."""
        import webbrowser
        webbrowser.open("https://github.com/opengameboost/opengameboost")
    
    def run(self):
        """Run the application."""
        # Start game detector if enabled
        if self.game_detector and self.config.get("game_detector", "enabled", True):
            self.game_detector.start()
        
        # Update system info periodically
        def update_loop():
            self._update_system_info()
            self.root.after(5000, update_loop)
        
        self.root.after(1000, update_loop)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Run the main loop
        self.root.mainloop()
    
    def _on_close(self):
        """Handle application close."""
        if self.game_detector:
            self.game_detector.stop()
        self.config.save()
        self.root.destroy()


def main():
    """Main entry point."""
    # Ensure app data directory exists
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    app_dir = os.path.join(appdata, 'OpenGameBoost')
    os.makedirs(app_dir, exist_ok=True)
    
    # Check for admin rights on Windows
    if os.name == 'nt':
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                logger.warning("Running without admin rights - some features may be limited")
        except:
            pass
    
    # Create and run app
    app = OpenGameBoostApp()
    app.run()


if __name__ == "__main__":
    main()

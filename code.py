# Standard libraries
import datetime
import html
import json
import logging
import os
import re
import sys
import threading
from pathlib import Path
from typing import Optional
import xml.dom.minidom
import xml.etree.ElementTree as ET

# Third party libraries
from lxml import etree

# Graceful Tkinter color picking import
try:
    from tkcolorpicker import askcolor
except ImportError:
    from tkinter.colorchooser import askcolor

# Tkinter and related
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont

# Constants
PREFERENCES_FILE = "preferences.json"
THEMES_FILE = "themecolors.json"
DEFAULT_SASH_POSITION = 300
DEFAULT_WIDTH = 1400
DEFAULT_HEIGHT = 1050
DEFAULT_FONT = "Arial"
DEFAULT_FONT_SIZE = "11"

# Set up basic logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Base path for executable or script
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
xml_default_path = os.path.join(base_path, "ia_all.xml")


# =====================================================================
# UTILITIES
# =====================================================================

class ToolTip:
    """A robust tooltip class constrained within the application window."""
    def __init__(self, widget, text, state_provider=None):
        self.widget = widget
        self.text = text
        self.state_provider = state_provider
        self.tip_window = None
        self.delay_id = None  # Tracks the 200ms delay timer
        
        # Bind events
        self.widget.bind("<Enter>", self.schedule_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def schedule_tip(self, event=None):
        """Schedules the tooltip to show after a 200ms delay."""
        if self.state_provider and not self.state_provider.get():
            return
        if self.tip_window or not self.text:
            return
            
        # Cancel any existing timer just in case, then start a 200ms delay
        self.cancel_delay()
        self.delay_id = self.widget.after(200, self.show_tip)

    def show_tip(self):
        """Creates and positions the tooltip strictly inside the app window."""
        self.delay_id = None
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)

        # 1. Get main application window boundaries (winfo_toplevel)
        root = self.widget.winfo_toplevel()
        root_x = root.winfo_rootx()
        root_y = root.winfo_rooty()
        root_w = root.winfo_width()
        root_h = root.winfo_height()

        # 2. Prevent tooltip from exceeding application window width
        max_wrap = min(300, max(150, root_w - 40))

        label = tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background="#ffffe0", relief=tk.SOLID, borderwidth=1,
            font=("Arial", "10", "normal"),
            wraplength=max_wrap
        )
        label.pack(ipadx=1)

        # 3. Force rendering to fetch accurate physical sizes (winfo_reqwidth)
        tw.update_idletasks()
        tip_width = tw.winfo_reqwidth()
        tip_height = tw.winfo_reqheight()

        # 4. Set ideal default position (below and slightly right)
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 25

        # 5. Constrain X to the application's right border
        if x + tip_width > root_x + root_w:
            x = root_x + root_w - tip_width - 10

        # 6. Constrain Y to the application's bottom border (flip upwards if needed)
        if y + tip_height > root_y + root_h:
            y = self.widget.winfo_rooty() - tip_height - 5

        # 7. Fallback clamp to ensure it never bleeds past top or left app borders
        x = max(x, root_x + 5)
        y = max(y, root_y + 5)

        # 8. Render final geometry
        tw.wm_geometry(f"+{x}+{y}")

    def hide_tip(self, event=None):
        """Safely cleans up active windows and cancels pending timers."""
        self.cancel_delay()
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

    def cancel_delay(self):
        """Cancels the after() loop timer to prevent ghost popups."""
        if self.delay_id:
            self.widget.after_cancel(self.delay_id)
            self.delay_id = None


# =====================================================================
# MODELS LAYER
# =====================================================================

class ThemeModel:
    """Manages application theme data, loading, saving, and querying color schemes."""
    def __init__(self):
        self.themes = {}
        self.current_theme = "Default"
        self.load_themes()
        if not self.themes:
            self.set_default_themes()
            self.current_theme = "Default"

    def set_default_themes(self):
        """Sets default themes if no theme configuration is found on disk."""
        # Clean, highly dense representation of the dozens of built-in themes to preserve the full aesthetic.
        self.themes = {
            "Default": {"bg": "#333333", "fg": "#ffffff", "selectbg": "#717171", "button_bg": "#717171", "button_fg": "#ffffff", "entry_bg": "#262626", "scrollbar_bg": "#717171", "scrollbar_trough": "#3B3B3B"},
            "DEMO": {"bg": "#F6CB68", "fg": "#FF0000", "selectbg": "#67FFDB", "button_bg": "#90008B", "button_fg": "#A2FF00", "entry_bg": "#193B00", "scrollbar_bg": "#0000FF", "scrollbar_trough": "#359AB6"},
            "Light": {"bg": "#FFFFFF", "fg": "#000000", "selectbg": "#d0d0d0", "button_bg": "#e0e0e0", "button_fg": "#000000", "entry_bg": "#ffffff", "scrollbar_bg": "#e0e0e0", "scrollbar_trough": "#d0d0d0"},
            "Pearl Mist": {"bg": "#f0f8ff", "fg": "#3c2f2f", "selectbg": "#e0e8f0", "button_bg": "#e6e4e4", "button_fg": "#3c2f2f", "entry_bg": "#ffffff", "scrollbar_bg": "#e6e4e4", "scrollbar_trough": "#e0e8f0"},
            "Ivory Mist": {"bg": "#f0e6e6", "fg": "#3c2f2f", "selectbg": "#d9d2d2", "button_bg": "#e6e4e4", "button_fg": "#3c2f2f", "entry_bg": "#fff8f8", "scrollbar_bg": "#e6e4e4", "scrollbar_trough": "#d9d2d2"},
            "Birch Bark": {"bg": "#e3dac9", "fg": "#3c2f2f", "selectbg": "#d9d2c4", "button_bg": "#e0d7ce", "button_fg": "#3c2f2f", "entry_bg": "#e6e4df", "scrollbar_bg": "#e0d7ce", "scrollbar_trough": "#d9d2c4"},
            "Beige": {"bg": "#f5f5dc", "fg": "#3c2f2f", "selectbg": "#e0d8b0", "button_bg": "#e6e4c5", "button_fg": "#3c2f2f", "entry_bg": "#fff8e7", "scrollbar_bg": "#e6e4c5", "scrollbar_trough": "#d9d2a3"},
            "Granite Mist": {"bg": "#6c6c6c", "fg": "#e6e6e6", "selectbg": "#8a8a8a", "button_bg": "#7c7c7c", "button_fg": "#e6e6e6", "entry_bg": "#6f6f6f", "scrollbar_bg": "#7c7c7c", "scrollbar_trough": "#6c6c6c"},
            "Ashen Whisper": {"bg": "#4a4a4a", "fg": "#e6e6e6", "selectbg": "#666666", "button_bg": "#5c5c5c", "button_fg": "#e6e6e6", "entry_bg": "#4d4d4d", "scrollbar_bg": "#5c5c5c", "scrollbar_trough": "#4a4a4a"},
            "Shadowed Slate": {"bg": "#3c3f40", "fg": "#d9d9d9", "selectbg": "#5c5f60", "button_bg": "#4d5051", "button_fg": "#d9d9d9", "entry_bg": "#3f4243", "scrollbar_bg": "#4d5051", "scrollbar_trough": "#3c3f40"},
            "Titanium": {"bg": "#2b2e33", "fg": "#d9d9d9", "selectbg": "#4a4e55", "button_bg": "#3a3e44", "button_fg": "#d9d9d9", "entry_bg": "#35383d", "scrollbar_bg": "#3a3e44", "scrollbar_trough": "#2b2e33"},
            "Charcoal Echo": {"bg": "#2b2b2b", "fg": "#e6e6e6", "selectbg": "#404040", "button_bg": "#363636", "button_fg": "#e6e6e6", "entry_bg": "#2e2e2e", "scrollbar_bg": "#363636", "scrollbar_trough": "#2b2b2b"},
            "Ebony Whisper": {"bg": "#1f2526", "fg": "#d9d9d9", "selectbg": "#3a3f40", "button_bg": "#2c3233", "button_fg": "#d9d9d9", "entry_bg": "#282d2e", "scrollbar_bg": "#2c3233", "scrollbar_trough": "#1f2526"},
            "Black": {"bg": "#000000", "fg": "#ffffff", "selectbg": "#333333", "button_bg": "#2C2C2C", "button_fg": "#ffffff", "entry_bg": "#000000", "scrollbar_bg": "#434343", "scrollbar_trough": "#000000"},
            "Forest": {"bg": "#1f2f27", "fg": "#d9e6d9", "selectbg": "#3a4e42", "button_bg": "#2a3c33", "button_fg": "#d9e6d9", "entry_bg": "#263630", "scrollbar_bg": "#2a3c33", "scrollbar_trough": "#1f2f27"},
            "Pine Tree": {"bg": "#1c352d", "fg": "#d9e6d9", "selectbg": "#2f4f42", "button_bg": "#26433a", "button_fg": "#d9e6d9", "entry_bg": "#1f382f", "scrollbar_bg": "#26433a", "scrollbar_trough": "#1c352d"},
            "Moonlit Grove": {"bg": "#2d3a3c", "fg": "#d9e6e6", "selectbg": "#3f4f51", "button_bg": "#354648", "button_fg": "#d9e6e6", "entry_bg": "#2e3f41", "scrollbar_bg": "#354648", "scrollbar_trough": "#2d3a3c"},
            "Frosted Pine": {"bg": "#2F4F4F", "fg": "#e6f0ff", "selectbg": "#468c8c", "button_bg": "#3b6b6b", "button_fg": "#e6f0ff", "entry_bg": "#395959", "scrollbar_bg": "#3b6b6b", "scrollbar_trough": "#2f4f4f"},
            "Pear": {"bg": "#2f3c2a", "fg": "#e6f0d9", "selectbg": "#4e5c46", "button_bg": "#3c4a36", "button_fg": "#e6f0d9", "entry_bg": "#374432", "scrollbar_bg": "#3c4a36", "scrollbar_trough": "#2f3c2a"},
            "Splash": {"bg": "#1c3a3a", "fg": "#e6ffff", "selectbg": "#2e5c5c", "button_bg": "#264a4a", "button_fg": "#e6ffff", "entry_bg": "#233f3f", "scrollbar_bg": "#264a4a", "scrollbar_trough": "#1c3a3a"},
            "Spring": {"bg": "#d9f0d3", "fg": "#2d4a3b", "selectbg": "#b8d9b0", "button_bg": "#c8e0c2", "button_fg": "#2d4a3b", "entry_bg": "#e6f5e6", "scrollbar_bg": "#c8e0c2", "scrollbar_trough": "#b3d9a8"},
            "Willow Breeze": {"bg": "#a9ba9d", "fg": "#3c4a3b", "selectbg": "#c9d9cc", "button_bg": "#c0d0c3", "button_fg": "#3c4a3b", "entry_bg": "#b5c1b8", "scrollbar_bg": "#c0d0c3", "scrollbar_trough": "#a9ba9d"},
            "Mist": {"bg": "#536878", "fg": "#1C2B40", "selectbg": "#779ecb", "button_bg": "#5d8aa8", "button_fg": "#e6e6fa", "entry_bg": "#9FA3B6", "scrollbar_bg": "#5d8aa8", "scrollbar_trough": "#36454f"},
            "Serenity": {"bg": "#bcd4e6", "fg": "#2d4a3b", "selectbg": "#96ded1", "button_bg": "#a3c1ad", "button_fg": "#2d4a3b", "entry_bg": "#e6f5e6", "scrollbar_bg": "#a3c1ad", "scrollbar_trough": "#b2beb5"},
            "Velvet Dawn": {"bg": "#915c83", "fg": "#FFF8E9", "selectbg": "#b784a7", "button_bg": "#CAA2DC", "button_fg": "#FFF8E9", "entry_bg": "#A77C5C", "scrollbar_bg": "#6E4266", "scrollbar_trough": "#79443b"},
            "Blue": {"bg": "#1e3a5f", "fg": "#ffffff", "selectbg": "#2e5a8f", "button_bg": "#2e5a8f", "button_fg": "#ffffff", "entry_bg": "#2a4a7a", "scrollbar_bg": "#2e5a8f", "scrollbar_trough": "#1e3a5f"},
            "Jade": {"bg": "#2f4f4f", "fg": "#ffffff", "selectbg": "#468c8c", "button_bg": "#3b6b6b", "button_fg": "#ffffff", "entry_bg": "#395959", "scrollbar_bg": "#3b6b6b", "scrollbar_trough": "#2f4f4f"},
            "Rose": {"bg": "#4a2e3b", "fg": "#ffffff", "selectbg": "#734d5c", "button_bg": "#5c3a49", "button_fg": "#ffffff", "entry_bg": "#553443", "scrollbar_bg": "#5c3a49", "scrollbar_trough": "#4a2e3b"},
            "Chocolate": {"bg": "#3c2f2f", "fg": "#ffffff", "selectbg": "#5c4a4a", "button_bg": "#4f3d3d", "button_fg": "#ffffff", "entry_bg": "#483838", "scrollbar_bg": "#4f3d3d", "scrollbar_trough": "#3c2f2f"},
            "Bahama": {"bg": "#1a3c4d", "fg": "#ffffff", "selectbg": "#2a5c6d", "button_bg": "#244c5d", "button_fg": "#ffffff", "entry_bg": "#223a47", "scrollbar_bg": "#244c5d", "scrollbar_trough": "#1a3c4d"},
            "Pomegranate": {"bg": "#3d1c25", "fg": "#ffffff", "selectbg": "#5c2e3a", "button_bg": "#4a2330", "button_fg": "#ffffff", "entry_bg": "#451e2b", "scrollbar_bg": "#4a2330", "scrollbar_trough": "#3d1c25"},
            "Dusk": {"bg": "#2e2a3f", "fg": "#e6e6e6", "selectbg": "#4d4666", "button_bg": "#3c3752", "button_fg": "#e6e6e6", "entry_bg": "#37324a", "scrollbar_bg": "#3c3752", "scrollbar_trough": "#2e2a3f"},
            "Vintage": {"bg": "#3a2f26", "fg": "#F1DAB6", "selectbg": "#5c4a3a", "button_bg": "#4a3c33", "button_fg": "#f0d9b5", "entry_bg": "#45382e", "scrollbar_bg": "#4a3c33", "scrollbar_trough": "#3a2f26"},
            "Blueberry": {"bg": "#2a2f4d", "fg": "#e6e6ff", "selectbg": "#464a73", "button_bg": "#363c5f", "button_fg": "#e6e6ff", "entry_bg": "#323856", "scrollbar_bg": "#363c5f", "scrollbar_trough": "#2a2f4d"},
            "Dream": {"bg": "#1e2e3f", "fg": "#d9e6ff", "selectbg": "#3a4e66", "button_bg": "#2a3c52", "button_fg": "#d9e6ff", "entry_bg": "#26364a", "scrollbar_bg": "#2a3c52", "scrollbar_trough": "#1e2e3f"},
            "Retro": {"bg": "#2f2a2f", "fg": "#ffb3b3", "selectbg": "#4e464e", "button_bg": "#3c363c", "button_fg": "#ffb3b3", "entry_bg": "#373237", "scrollbar_bg": "#3c363c", "scrollbar_trough": "#2f2a2f"},
            "CS04": {"bg": "#1a2f3a", "fg": "#d9f0ff", "selectbg": "#2e4e5c", "button_bg": "#233c4a", "button_fg": "#d9f0ff", "entry_bg": "#213641", "scrollbar_bg": "#233c4a", "scrollbar_trough": "#1a2f3a"},
            "Midnight": {"bg": "#0f1e2d", "fg": "#e6e6ff", "selectbg": "#2a3a4e", "button_bg": "#1e2c3c", "button_fg": "#e6e6ff", "entry_bg": "#182533", "scrollbar_bg": "#1e2c3c", "scrollbar_trough": "#0f1e2d"},
            "Twilight": {"bg": "#2a263f", "fg": "#f0e6ff", "selectbg": "#464266", "button_bg": "#363252", "button_fg": "#f0e6ff", "entry_bg": "#322e4a", "scrollbar_bg": "#363252", "scrollbar_trough": "#2a263f"},
            "Citrus Breeze": {"bg": "#ffcc33", "fg": "#3f2a1d", "selectbg": "#f8d568", "button_bg": "#ffae42", "button_fg": "#3f2a1d", "entry_bg": "#fffacd", "scrollbar_bg": "#ffae42", "scrollbar_trough": "#e9d66b"},
            "Emerald": {"bg": "#50C878", "fg": "#1f2f27", "selectbg": "#74c365", "button_bg": "#3EB68A", "button_fg": "#1f2f27", "entry_bg": "#a0d6b4", "scrollbar_bg": "#3eb489", "scrollbar_trough": "#006b3c"},
            "Coral Dream": {"bg": "#FF7E4F", "fg": "#3c2f2f", "selectbg": "#f88379", "button_bg": "#ff9966", "button_fg": "#3c2f2f", "entry_bg": "#ffdab9", "scrollbar_bg": "#ff9966", "scrollbar_trough": "#e97451"},
            "Amethyst": {"bg": "#9A67CD", "fg": "#f0d9b5", "selectbg": "#bf94e4", "button_bg": "#B667D2", "button_fg": "#f0d9b5", "entry_bg": "#6F449A", "scrollbar_bg": "#b666d2", "scrollbar_trough": "#734f96"},
            "Golden": {"bg": "#FFD900", "fg": "#483c32", "selectbg": "#ffcc00", "button_bg": "#e4d00a", "button_fg": "#483c32", "entry_bg": "#fafad2", "scrollbar_bg": "#e4d00a", "scrollbar_trough": "#b8860b"},
            "Lavender": {"bg": "#E8E8FB", "fg": "#5a4fcf", "selectbg": "#c8a2c8", "button_bg": "#b19cd9", "button_fg": "#5a4fcf", "entry_bg": "#fff0f5", "scrollbar_bg": "#b19cd9", "scrollbar_trough": "#967bb6"},
            "Ocean Whisper": {"bg": "#32D7CA", "fg": "#003153", "selectbg": "#73c2fb", "button_bg": "#0abab5", "button_fg": "#003153", "entry_bg": "#b2ffff", "scrollbar_bg": "#0abab5", "scrollbar_trough": "#006994"},
            "Rose Petal": {"bg": "#D7207C", "fg": "#015500", "selectbg": "#f9429e", "button_bg": "#e25098", "button_fg": "#ffffff", "entry_bg": "#ffbcd9", "scrollbar_bg": "#e25098", "scrollbar_trough": "#b3446c"},
            "Mossy Stone": {"bg": "#addfad", "fg": "#3c2f2f", "selectbg": "#93c572", "button_bg": "#77dd77", "button_fg": "#3c2f2f", "entry_bg": "#d0f0c0", "scrollbar_bg": "#77dd77", "scrollbar_trough": "#507d2a"},
            "Flamingo Sunset": {"bg": "#fc8eac", "fg": "#4a2c00", "selectbg": "#ff91a4", "button_bg": "#f78fa7", "button_fg": "#4a2c00", "entry_bg": "#ffd1dc", "scrollbar_bg": "#f78fa7", "scrollbar_trough": "#e4717a"},
            "Indigo Night": {"bg": "#4b0082", "fg": "#e6e6ff", "selectbg": "#6f00ff", "button_bg": "#3f00ff", "button_fg": "#e6e6ff", "entry_bg": "#8f00ff", "scrollbar_bg": "#3f00ff", "scrollbar_trough": "#32127a"},
            "Peachy Glow": {"bg": "#ffdab9", "fg": "#79443b", "selectbg": "#fadfad", "button_bg": "#ffbd88", "button_fg": "#79443b", "entry_bg": "#fffacd", "scrollbar_bg": "#ffbd88", "scrollbar_trough": "#fad6a5"},
            "Jade Serenity": {"bg": "#00a86b", "fg": "#ffffff", "selectbg": "#3eb489", "button_bg": "#50c878", "button_fg": "#ffffff", "entry_bg": "#a0d6b4", "scrollbar_bg": "#50c878", "scrollbar_trough": "#006d5b"},
            "Cherry Blossom": {"bg": "#ffb7c5", "fg": "#3c2f2f", "selectbg": "#ffa6c9", "button_bg": "#f6adc6", "button_fg": "#3c2f2f", "entry_bg": "#fff0f5", "scrollbar_bg": "#f6adc6", "scrollbar_trough": "#e7accf"},
            "Saffron Spice": {"bg": "#f4c430", "fg": "#4a2c00", "selectbg": "#ffcc00", "button_bg": "#ffa700", "button_fg": "#4a2c00", "entry_bg": "#fff44f", "scrollbar_bg": "#ffa700", "scrollbar_trough": "#e49b0f"},
            "Midnight Rose": {"bg": "#733037", "fg": "#f0e6ff", "selectbg": "#b57281", "button_bg": "#ab4e52", "button_fg": "#f0e6ff", "entry_bg": "#c08081", "scrollbar_bg": "#ab4e52", "scrollbar_trough": "#65000b"},
            "Frosty Mint": {"bg": "#aaf0d1", "fg": "#21421e", "selectbg": "#98ff98", "button_bg": "#3cd070", "button_fg": "#21421e", "entry_bg": "#f5fffa", "scrollbar_bg": "#3cd070", "scrollbar_trough": "#006a4e"},
            "Amber Twilight": {"bg": "#ffbf00", "fg": "#483c32", "selectbg": "#ffa812", "button_bg": "#f94d00", "button_fg": "#483c32", "entry_bg": "#ffefd5", "scrollbar_bg": "#f94d00", "scrollbar_trough": "#cd7f32"},
            "Blue Harmony": {"bg": "#4169e1", "fg": "#d9e6ff", "selectbg": "#73a9c2", "button_bg": "#0073cf", "button_fg": "#003192", "entry_bg": "#324FA7", "scrollbar_bg": "#0073cf", "scrollbar_trough": "#0033aa"},
            "Plum Elegance": {"bg": "#dda0dd", "fg": "#3c2f2f", "selectbg": "#ee82ee", "button_bg": "#c154c1", "button_fg": "#3c2f2f", "entry_bg": "#fbcce7", "scrollbar_bg": "#c154c1", "scrollbar_trough": "#915f6d"},
            "Sepia Scroll": {"bg": "#8b6f47", "fg": "#f0e6d9", "selectbg": "#a78c5e", "button_bg": "#9d7d53", "button_fg": "#f0e6d9", "entry_bg": "#8f734c", "scrollbar_bg": "#9d7d53", "scrollbar_trough": "#8b6f47"},
            "Slate Serenity": {"bg": "#4f5d6e", "fg": "#e6f0f0", "selectbg": "#6a7888", "button_bg": "#5c6a7b", "button_fg": "#e6f0f0", "entry_bg": "#526373", "scrollbar_bg": "#5c6a7b", "scrollbar_trough": "#4f5d6e"},
            "Cedar Haven": {"bg": "#3f2f2a", "fg": "#f0d9d9", "selectbg": "#5c4a45", "button_bg": "#4c3a35", "button_fg": "#f0d9d9", "entry_bg": "#42322d", "scrollbar_bg": "#4c3a35", "scrollbar_trough": "#3f2f2a"},
            "Sage Whisper": {"bg": "#8a9a8b", "fg": "#3c4a3b", "selectbg": "#a3b3a4", "button_bg": "#9ca99d", "button_fg": "#3c4a3b", "entry_bg": "#8f9f90", "scrollbar_bg": "#9ca99d", "scrollbar_trough": "#8a9a8b"},
            "Rustic Oak": {"bg": "#5c4a3a", "fg": "#f0d9b5", "selectbg": "#7a634f", "button_bg": "#6d5a46", "button_fg": "#f0d9b5", "entry_bg": "#5f4d3d", "scrollbar_bg": "#6d5a46", "scrollbar_trough": "#5c4a3a"},
            "Willow Shade": {"bg": "#4f7942", "fg": "#e6f0d9", "selectbg": "#6a9f5c", "button_bg": "#5c8a4f", "button_fg": "#e6f0d9", "entry_bg": "#527f45", "scrollbar_bg": "#5c8a4f", "scrollbar_trough": "#4f7942"},
            "Pewter Glow": {"bg": "#6e7f80", "fg": "#d9e6e6", "selectbg": "#8a9a9b", "button_bg": "#7c8d8e", "button_fg": "#d9e6e6", "entry_bg": "#718486", "scrollbar_bg": "#7c8d8e", "scrollbar_trough": "#6e7f80"},
            "Copper Dusk": {"bg": "#8b4513", "fg": "#f0e6d9", "selectbg": "#a85a1c", "button_bg": "#9c5020", "button_fg": "#f0e6d9", "entry_bg": "#8e4816", "scrollbar_bg": "#9c5020", "scrollbar_trough": "#8b4513"},
            "Muted Lavender": {"bg": "#8A4A6B", "fg": "#f0e6ff", "selectbg": "#a65c85", "button_bg": "#9c5280", "button_fg": "#f0e6ff", "entry_bg": "#8d4d6e", "scrollbar_bg": "#9c5280", "scrollbar_trough": "#8a496b"},
            "Iron Veil": {"bg": "#414a4c", "fg": "#e6e6e6", "selectbg": "#5c6a6c", "button_bg": "#4d5a5c", "button_fg": "#e6e6e6", "entry_bg": "#445054", "scrollbar_bg": "#4d5a5c", "scrollbar_trough": "#414a4c"},
            "Hazelwood Calm": {"bg": "#8b6f47", "fg": "#f0e6d9", "selectbg": "#a78c5e", "button_bg": "#9d7d53", "button_fg": "#f0e6d9", "entry_bg": "#8f734c", "scrollbar_bg": "#9d7d53", "scrollbar_trough": "#8b6f47"},
            "Olive Retreat": {"bg": "#556b2f", "fg": "#e6f0d9", "selectbg": "#6a8f3c", "button_bg": "#5c7a34", "button_fg": "#e6f0d9", "entry_bg": "#596e32", "scrollbar_bg": "#5c7a34", "scrollbar_trough": "#556b2f"},
            "Cobalt Quiet": {"bg": "#1e3a5f", "fg": "#e6f0ff", "selectbg": "#2e5a8f", "button_bg": "#2a4a7a", "button_fg": "#e6f0ff", "entry_bg": "#223f6a", "scrollbar_bg": "#2a4a7a", "scrollbar_trough": "#1e3a5f"},
            "Velvet Shadow": {"bg": "#4a2e3b", "fg": "#f0e6ff", "selectbg": "#734d5c", "button_bg": "#5c3a49", "button_fg": "#f0e6ff", "entry_bg": "#553443", "scrollbar_bg": "#5c3a49", "scrollbar_trough": "#4a2e3b"},
            "Twilight Ember": {"bg": "#2a263f", "fg": "#f0e6ff", "selectbg": "#464266", "button_bg": "#363252", "button_fg": "#f0e6ff", "entry_bg": "#322e4a", "scrollbar_bg": "#363252", "scrollbar_trough": "#2a263f"},
            "Sandstone Whisper": {"bg": "#c2b280", "fg": "#3c2f2f", "selectbg": "#d9d2c4", "button_bg": "#d0ceac", "button_fg": "#3c2f2f", "entry_bg": "#e6e4c6", "scrollbar_bg": "#d0ceac", "scrollbar_trough": "#c2b280"},
            "Clay Earth": {"bg": "#8b6f47", "fg": "#f0e6d9", "selectbg": "#a78c5e", "button_bg": "#9d7d53", "button_fg": "#f0e6d9", "entry_bg": "#8f734c", "scrollbar_bg": "#9d7d53", "scrollbar_trough": "#8b6f47"},
            "Mystic Blue": {"bg": "#2a4d69", "fg": "#e6f0ff", "selectbg": "#3f6a8c", "button_bg": "#2e4f6b", "button_fg": "#e6f0ff", "entry_bg": "#2b4a66", "scrollbar_bg": "#2e4f6b", "scrollbar_trough": "#2a4d69"},
            "Heather Hush": {"bg": "#8a496b", "fg": "#f0e6ff", "selectbg": "#a65c85", "button_bg": "#9c5280", "button_fg": "#f0e6ff", "entry_bg": "#8d4d6e", "scrollbar_bg": "#9c5280", "scrollbar_trough": "#8a496b"},
            "Bronze Age": {"bg": "#cd7f32", "fg": "#f0e6d9", "selectbg": "#e99b6a", "button_bg": "#d68a59", "button_fg": "#f0e6d9", "entry_bg": "#d08f3c", "scrollbar_bg": "#d68a59", "scrollbar_trough": "#cd7f32"},
            "Midnight Sapphire": {"bg": "#0f1e2d", "fg": "#e6f0ff", "selectbg": "#2a3a4e", "button_bg": "#1e2c3c", "button_fg": "#e6f0ff", "entry_bg": "#182533", "scrollbar_bg": "#1e2c3c", "scrollbar_trough": "#0f1e2d"},
            "Terra Cotta": {"bg": "#e2725b", "fg": "#3c2f2f", "selectbg": "#f3836c", "button_bg": "#e67d64", "button_fg": "#3c2f2f", "entry_bg": "#e5775f", "scrollbar_bg": "#e67d64", "scrollbar_trough": "#e2725b"},
            "Stormy Sea": {"bg": "#2e4d69", "fg": "#e6f0ff", "selectbg": "#3f6a8c", "button_bg": "#2e4f6b", "button_fg": "#e6f0ff", "entry_bg": "#2b4a66", "scrollbar_bg": "#2e4f6b", "scrollbar_trough": "#2e4d69"}
        }

    def load_themes(self):
        """Loads themes from a JSON file or sets defaults if loading fails."""
        if os.path.exists(THEMES_FILE):
            try:
                with open(THEMES_FILE, 'r') as f:
                    self.themes = json.load(f)
                logging.debug(f"Loaded themes from {THEMES_FILE}")
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding {THEMES_FILE}: {str(e)}")
                self.set_default_themes()
        else:
            logging.info(f"{THEMES_FILE} not found, using default themes")
            self.set_default_themes()

    def get_colors(self) -> dict:
        """Returns the color dictionary for the current theme."""
        if self.current_theme not in self.themes:
            return self.themes.get("Default", {})
        return self.themes[self.current_theme]

    def set_theme(self, theme_name: str):
        """Sets the current theme by name."""
        if theme_name in self.themes:
            self.current_theme = theme_name

    def save_themes(self, themes_dict: dict):
        """Saves the themes dictionary to the JSON file."""
        self.themes = themes_dict
        try:
            with open(THEMES_FILE, 'w') as f:
                json.dump(self.themes, f, indent=4)
            logging.info(f"Saved themes to {THEMES_FILE}")
        except Exception as e:
            logging.error(f"Failed to save themes: {e}")


class PreferencesModel:
    """Manages loading, validating, and saving of user preferences."""
    def __init__(self):
        self.filename = PREFERENCES_FILE
        self.data = {}

    def load_preferences(self, theme_model: ThemeModel):
        """Loads preferences from a JSON file, validating loaded options."""
        default_prefs = {
            "selected_translations": ["Arabic", "Muhammad Asad"],
            "favorite_translations": ["Arabic", "Muhammad Asad"],
            "font": DEFAULT_FONT,
            "font_size": DEFAULT_FONT_SIZE,
            "last_reference": "1-114",
            "theme": "Default",
            "last_keyword": "",
            "broad_search": False,
            "broad_results": False,
            "notes_enabled": False,
            "tooltips_enabled": True
        }

        if not os.path.exists(self.filename):
            self.data = default_prefs
            logging.info("No preferences.json found, using default preferences")
        else:
            try:
                with open(self.filename, 'r') as f:
                    self.data = json.load(f)
                
                # Validation of theme
                available_themes = list(theme_model.themes.keys())
                if self.data.get("theme") not in available_themes:
                    self.data["theme"] = default_prefs["theme"]
                    theme_model.set_theme(default_prefs["theme"])
                else:
                    theme_model.set_theme(self.data["theme"])

                # Validation of font
                if self.data.get("font") not in tkfont.families():
                    self.data["font"] = default_prefs["font"]
                logging.debug("Loaded and validated preferences from preferences.json")
            except Exception as e:
                self.data = default_prefs
                logging.error(f"Error loading preferences.json ({str(e)}), reverting to defaults")

    def save_preferences(self):
        """Saves current preferences dictionary to JSON file."""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.data, f)
            logging.info(f"Saved preferences to {self.filename}")
        except Exception as e:
            logging.error(f"Failed to save preferences: {e}")


class QuranModel:
    """Handles parsing and storage of Quran XML corpus and User Notes XML."""
    def __init__(self):
        self.translations = []
        self.surahs = {}
        self.verses = {}
        self.surah_names = {}
        self.ayah_counts = {}
        self.notes_file = os.path.join(base_path, "notes.xml")
        self.user_notes = {}  # Thread-safe copy of user notes loaded from notes.xml: { "surah.ayah": "text" }

    def parse_xml(self, xml_path: Path):
        """Streams XML database into optimized dictionary lookups."""
        try:
            context = etree.iterparse(str(xml_path), events=('end',), tag='Rendition')
            for _, elem in context:
                try:
                    source = elem.get('Source')
                    text = html.unescape(elem.text.strip()) if elem.text else ""
                    ayah_elem = elem.getparent()
                    surah_elem = ayah_elem.getparent()
                    surah_num = surah_elem.get('SurahNumber')
                    ayah_num = ayah_elem.get('AyahNumber')

                    if surah_num not in self.surah_names:
                        self.surah_names[surah_num] = (
                            html.unescape(surah_elem.get('SurahArabicName', '')),
                            html.unescape(surah_elem.get('SurahTransliteratedName', '')),
                            html.unescape(surah_elem.get('SurahEnglishNames', ''))
                        )

                    if surah_num not in self.surahs:
                        self.surahs[surah_num] = set()
                    self.surahs[surah_num].add(ayah_num)
                    
                    if surah_num not in self.verses:
                        self.verses[surah_num] = {}
                    if ayah_num not in self.verses[surah_num]:
                        self.verses[surah_num][ayah_num] = {}
                    
                    self.verses[surah_num][ayah_num][source] = text
                    
                    if source == "Arabic" and "Arabic" not in self.translations:
                        self.translations.insert(0, "Arabic")
                    elif source and source not in self.translations:
                        self.translations.append(source)
                finally:
                    elem.clear()
                    while elem.getprevious() is not None:
                        del elem.getparent()[0]
            self.ayah_counts = {surah: max(int(ayah) for ayah in self.surahs[surah]) for surah in self.surahs}
        except etree.LxmlError as e:
            raise ValueError(f"Failed to parse XML: {str(e)}")

    def load_notes(self):
        """Loads user notes XML from disk if it exists."""
        self.user_notes.clear()
        if os.path.exists(self.notes_file):
            try:
                tree = ET.parse(self.notes_file)
                root = tree.getroot()
                for surah in root.findall(".//Surah"):
                    surah_num = surah.get("SurahNumber")
                    for ayah in surah.findall(".//Ayah"):
                        ayah_num = ayah.get("AyahNumber")
                        rendition = ayah.find("./Rendition[@Source='User Notes']")
                        if rendition is not None:
                            ref = f"{surah_num}.{ayah_num}"
                            self.user_notes[ref] = rendition.text.strip()
                            
                            # Ensure "User Notes" is loaded as an available translation translation
                            if surah_num not in self.surahs:
                                self.surahs[surah_num] = set()
                            self.surahs[surah_num].add(ayah_num)
                            if surah_num not in self.verses:
                                self.verses[surah_num] = {}
                            if ayah_num not in self.verses[surah_num]:
                                self.verses[surah_num][ayah_num] = {}
                            self.verses[surah_num][ayah_num]["User Notes"] = rendition.text.strip()
                            
                if "User Notes" not in self.translations:
                    self.translations.insert(0, "User Notes")
            except Exception as e:
                logging.error(f"Failed to load notes.xml: {e}")

    def save_notes(self, notes_dict: dict):
        """Saves current memory buffer of user notes to notes.xml in canonical format."""
        self.user_notes = notes_dict.copy()
        
        # Inject user notes back into active model structures for consistency
        for ref, text in self.user_notes.items():
            if "." in ref:
                surah_num, ayah_num = ref.split(".")
                if surah_num in self.verses and ayah_num in self.verses[surah_num]:
                    self.verses[surah_num][ayah_num]["User Notes"] = text
                    
        if not self.user_notes:
            return

        root = ET.Element("IslamAwakenedQuranDatabase", GenerationDate=datetime.datetime.now().strftime("%Y-%m-%d"))
        suwar = ET.SubElement(root, "Suwar")

        surah_notes = {}
        for ref, text in self.user_notes.items():
            if "." in ref:
                surah, ayah = ref.split(".")
                if surah not in surah_notes:
                    surah_notes[surah] = {}
                surah_notes[surah][ayah] = text

        for surah_num in sorted(surah_notes.keys(), key=int):
            surah_elem = ET.SubElement(suwar, "Surah", SurahNumber=surah_num)
            for ayah_num in sorted(surah_notes[surah_num].keys(), key=int):
                ayah_elem = ET.SubElement(surah_elem, "Ayah", AyahNumber=ayah_num)
                ET.SubElement(ayah_elem, "Rendition", Source="User Notes").text = surah_notes[surah_num][ayah_num]

        # Formatting
        rough_string = ET.tostring(root, 'utf-8')
        parsed = xml.dom.minidom.parseString(rough_string)
        pretty_xml = parsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")

        try:
            with open(self.notes_file, "w", encoding="utf-8") as f:
                f.write(pretty_xml)
            logging.info("Saved notes.xml successfully.")
        except Exception as e:
            logging.error(f"Failed to write notes.xml: {e}")


# =====================================================================
# CONTROLLER LAYER
# =====================================================================

class QuranController:
    """
    Coordinates interactions between Models and Views.
    Encapsulates computational logic (reference resolution, keyword searches) making them unit-testable.
    """
    def __init__(self):
        self.quran_model = QuranModel()
        self.theme_model = ThemeModel()
        self.prefs_model = PreferencesModel()
        self.prefs_model.load_preferences(self.theme_model)
        
        # Working state variables
        self.search_results_cache = None
        self.last_ref_cache = None

    def start_data_load_async(self, xml_path: Path, on_success_callback, on_error_callback):
        """Executes data loading inside a background daemon thread for GUI responsiveness."""
        def worker():
            try:
                logging.info("Async load started.")
                self.quran_model.parse_xml(xml_path)
                self.quran_model.load_notes()
                # Safely execute callback on main UI thread
                on_success_callback()
            except Exception as e:
                logging.exception("Background loading error occurred.")
                on_error_callback(e)

        threading.Thread(target=worker, daemon=True).start()

    def parse_reference(self, ref: str) -> tuple[str, str, str, str]:
        """Resolves notation strings into standard coordinate bounds."""
        single_surah = r'^(\d+)$'
        surah_range = r'^(\d+)-(\d+)$'
        verse_single = r'^(\d+)\.(\d+)$'
        verse_to_ayah = r'^(\d+)\.(\d+)-(\d+)$'
        surah_to_verse = r'^(\d+)-(\d+)\.(\d+)$'
        verse_range = r'^(\d+)\.(\d+)-(\d+)\.(\d+)$'

        if re.match(single_surah, ref):
            surah_start = ref
            surah_end = surah_start
            start_ayah = '1'
            end_ayah = str(max(int(ayah) for ayah in self.quran_model.surahs.get(surah_start, set())) if surah_start in self.quran_model.surahs else 0)
        elif re.match(surah_range, ref):
            match = re.match(surah_range, ref)
            surah_start, surah_end = match.groups()
            start_ayah = '1'
            end_ayah = str(max(int(ayah) for ayah in self.quran_model.surahs.get(surah_end, set())) if surah_end in self.quran_model.surahs else 0)
        elif re.match(verse_single, ref):
            match = re.match(verse_single, ref)
            surah_start, start_ayah = match.groups()
            surah_end = surah_start
            end_ayah = start_ayah
            if start_ayah == '0':
                if surah_start in self.quran_model.surahs:
                    start_ayah = '1'
                    end_ayah = str(max(int(ayah) for ayah in self.quran_model.surahs[surah_start]))
                else:
                    raise ValueError(f"Surah {surah_start} not found")
        elif re.match(verse_to_ayah, ref):
            match = re.match(verse_to_ayah, ref)
            surah_start, start_ayah, end_value = match.groups()
            if int(end_value) <= int(surah_start):
                surah_end = surah_start
                end_ayah = end_value
            else:
                surah_end = end_value
                end_ayah = str(max(int(ayah) for ayah in self.quran_model.surahs.get(surah_end, set())) if surah_end in self.quran_model.surahs else 0)
        elif re.match(surah_to_verse, ref):
            match = re.match(surah_to_verse, ref)
            surah_start, surah_end, end_ayah = match.groups()
            start_ayah = '1'
        elif re.match(verse_range, ref):
            match = re.match(verse_range, ref)
            surah_start, start_ayah, surah_end, end_ayah = match.groups()
        else:
            raise ValueError("Invalid reference format\n\n  Try :\n One surah (e.g., 1)\n A specific verse (e.g., 2.225)\n A surah range (e.g., 3-4)\n A specific range (e.g., 5-7.9)\n\n Use 1-114 to search the entire Quran")

        if surah_start not in self.quran_model.surahs or surah_end not in self.quran_model.surahs:
            raise ValueError(f"Surah {surah_start} or {surah_end} not found")
        return surah_start, start_ayah, surah_end, end_ayah

    def get_previous_verse(self, surah: str, ayah: str) -> Optional[tuple[str, str]]:
        """Calculates previous structural coordinates."""
        surah_int = int(surah)
        ayah_int = int(ayah)
        if ayah_int > 1:
            return (surah, str(ayah_int - 1))
        elif surah_int > 1:
            prev_surah = str(surah_int - 1)
            max_ayah = self.quran_model.ayah_counts[prev_surah]
            return (prev_surah, str(max_ayah))
        else:
            return None

    def get_next_verse(self, surah: str, ayah: str) -> Optional[tuple[str, str]]:
        """Calculates next structural coordinates."""
        surah_int = int(surah)
        ayah_int = int(ayah)
        max_ayah = self.quran_model.ayah_counts[surah]
        if ayah_int < max_ayah:
            return (surah, str(ayah_int + 1))
        elif surah_int < 114:
            next_surah = str(surah_int + 1)
            return (next_surah, "1")
        else:
            return None

    def query_verses(self, ref_str: str, keyword: str, selected_translations: list, 
                     broad_search: bool, broad_results: bool, notes_active: bool, 
                     from_navigation: bool = False) -> dict:
        """
        Processes and filters matching Quranic verses based on reference syntax and keywords.
        Decoupled from GUI elements: safe for unit testing.
        """
        try:
            surah_start, start_ayah, surah_end, end_ayah = self.parse_reference(ref_str)
            is_single_verse = (surah_start == surah_end and start_ayah == end_ayah)

            # Enforce single-verse bounds if User Notes are open
            if notes_active and not is_single_verse and not from_navigation:
                if self.last_ref_cache:
                    surah_start, start_ayah, surah_end, end_ayah = self.parse_reference(self.last_ref_cache)
                    is_single_verse = True
                else:
                    surah_start, start_ayah, surah_end, end_ayah = self.parse_reference("1.1")
                    is_single_verse = True

            start_surah = int(surah_start)
            end_surah = int(surah_end)

            # Build patterns
            patterns = []
            phrase_pattern = None
            if keyword:
                keyword = keyword.lower()
                if keyword.startswith('"') and keyword.endswith('"'):
                    phrase = keyword[1:-1]
                    pattern_str = re.escape(phrase).replace(r'\*', '.*').replace(r'\?', '.')
                    phrase_pattern = re.compile(pattern_str, re.IGNORECASE)
                else:
                    words = keyword.split()
                    for word in words:
                        base = re.escape(word).replace(r'\*', '.*').replace(r'\?', '.')
                        pattern_str = rf'\b{base}\w*'
                        patterns.append(re.compile(pattern_str, re.IGNORECASE))

            # Broad Search Precomputation
            matching_verses = set()
            translation_matches = {}  # { (surah, ayah): [trans] }
            if keyword and broad_search:
                for surah_num in range(start_surah, end_surah + 1):
                    surah_key = str(surah_num)
                    if surah_key in self.quran_model.verses:
                        start = int(start_ayah) if surah_num == start_surah else 1
                        end = int(end_ayah) if surah_num == end_surah else max(int(ayah) for ayah in self.quran_model.surahs[surah_key])
                        for ayah in range(start, end + 1):
                            ayah_key = str(ayah)
                            if ayah_key in self.quran_model.verses[surah_key]:
                                for trans in self.quran_model.translations:
                                    if trans in self.quran_model.verses[surah_key][ayah_key]:
                                        text = self.quran_model.verses[surah_key][ayah_key][trans]
                                        match = False
                                        if phrase_pattern:
                                            if phrase_pattern.search(text):
                                                match = True
                                        elif patterns:
                                            if all(pattern.search(text) for pattern in patterns):
                                                match = True
                                        if match:
                                            matching_verses.add((surah_key, ayah_key))
                                            if (surah_key, ayah_key) not in translation_matches:
                                                translation_matches[(surah_key, ayah_key)] = []
                                            translation_matches[(surah_key, ayah_key)].append(trans)

            # Compile matching list
            results_list = []
            all_displayed_translations = set()
            search_results_temp = [] if keyword and not is_single_verse else None

            # Precompute prioritized translation order once to eliminate redundant allocations
            base_display_translations = []
            # Arabic first, then User Notes per original requirement
            if 'Arabic' in selected_translations:
                base_display_translations.append('Arabic')
            if 'User Notes' in selected_translations:
                base_display_translations.append('User Notes')
            for trans in self.quran_model.translations:
                if trans in selected_translations and trans not in base_display_translations:
                    base_display_translations.append(trans)

            for surah_num in range(start_surah, end_surah + 1):
                surah_key = str(surah_num)
                if surah_key in self.quran_model.verses:
                    start = int(start_ayah) if surah_num == start_surah else 1
                    end = int(end_ayah) if surah_num == end_surah else max(int(ayah) for ayah in self.quran_model.surahs[surah_key])
                    for ayah in range(start, end + 1):
                        ayah_key = str(ayah)
                        if ayah_key in self.quran_model.verses[surah_key]:
                            matching_translations = []
                            if is_single_verse and notes_active and not keyword:
                                match = True
                            elif keyword:
                                if broad_search:
                                    match = (surah_key, ayah_key) in matching_verses
                                    if match:
                                        matching_translations = translation_matches.get((surah_key, ayah_key), [])
                                else:
                                    match = False
                                    for trans in selected_translations:
                                        if trans in self.quran_model.verses[surah_key][ayah_key]:
                                            text = self.quran_model.verses[surah_key][ayah_key][trans]
                                            if phrase_pattern:
                                                if phrase_pattern.search(text):
                                                    match = True
                                                    matching_translations.append(trans)
                                            elif patterns:
                                                if all(pattern.search(text) for pattern in patterns):
                                                    match = True
                                                    matching_translations.append(trans)
                            else:
                                match = True

                            if match:
                                if keyword and not is_single_verse:
                                    search_results_temp.append(f"{surah_key}.{ayah_key}")
                                
                                surah_info = self.quran_model.surah_names.get(surah_key, ('', '', ''))
                                
                                # Simply copy the precomputed base list (Incredibly Fast O(1))
                                display_translations = list(base_display_translations)
                                
                                if broad_search and broad_results and not is_single_verse:
                                    display_translations.extend([t for t in matching_translations if t not in display_translations])

                                trans_texts = {}
                                for trans in display_translations:
                                    if trans in self.quran_model.verses[surah_key][ayah_key]:
                                        if trans == "User Notes" and not self.quran_model.verses[surah_key][ayah_key][trans].strip():
                                            continue  # skip empty notes
                                        trans_texts[trans] = self.quran_model.verses[surah_key][ayah_key][trans]
                                        all_displayed_translations.add(trans)

                                results_list.append({
                                    'surah_num': surah_key,
                                    'ayah_num': ayah_key,
                                    'arabic_name': surah_info[0],
                                    'transliterated_name': surah_info[1],
                                    'english_name': surah_info[2],
                                    'display_translations': display_translations,
                                    'texts': trans_texts
                                })

            self.last_ref_cache = f"{surah_start}.{start_ayah}" if is_single_verse else None
            
            # Direct cache clearing/updating fixed here to match 930 functionality
            self.search_results_cache = search_results_temp

            return {
                'success': True,
                'verses': results_list,
                'is_single_verse': is_single_verse,
                'last_ref': self.last_ref_cache,
                'all_displayed_translations': all_displayed_translations,
                'verse_count': len(results_list)
            }

        except ValueError as e:
            return {
                'success': False,
                'error_message': str(e),
                'fallback_ref': '1-114'
            }


# =====================================================================
# VIEW LAYER (THEME CUSTOMIZER WINDOW)
# =====================================================================

class ThemeCustomizer(tk.Toplevel):
    """Visual Toplevel interface for creating, modifying, and saving palette schemes."""
    def __init__(self, parent_view, theme_model: ThemeModel, on_theme_applied_callback):
        super().__init__(parent_view.root)
        self.parent_view = parent_view
        self.theme_model = theme_model
        self.on_theme_applied_callback = on_theme_applied_callback

        self.title("Theme Color Customizer")
        self.geometry("1280x1000")

        # Make copy of working dictionary
        self.working_themes = self.theme_model.themes.copy()
        self.theme_order = list(self.working_themes.keys())
        self.selected_themes = {theme: tk.BooleanVar(self, value=True) for theme in self.theme_order}
        
        self.color_types = ['bg', 'fg', 'selectbg', 'button_bg', 'button_fg', 'entry_bg', 'scrollbar_bg', 'scrollbar_trough']
        self.setup_ui()

    def get_luminance(self, hex_color: str) -> float:
        """Determines contrast coefficient of a color to pick readable text backgrounds."""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255

    def setup_ui(self):
        # Master scroll frames
        scroll_frame = tk.Frame(self, width=1100)
        scroll_frame.pack(side="left", fill="y")
        scroll_frame.pack_propagate(False)

        initial_preview_theme = "Default"
        if "DEMO" in self.working_themes:
            initial_preview_theme = "DEMO"
        elif self.theme_order:
            initial_preview_theme = self.theme_order[0]

        self.preview_frame = tk.Frame(self, bg=self.working_themes[initial_preview_theme]['bg'])
        self.preview_frame.pack(side="right", fill="both", expand=True)
        self.update_preview(initial_preview_theme)

        self.canvas = tk.Canvas(scroll_frame)
        scrollbar = tk.Scrollbar(scroll_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Bindings
        def on_mousewheel(event):
            if self.canvas.winfo_exists():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind("<MouseWheel>", on_mousewheel)
        self.inner_frame.bind("<MouseWheel>", on_mousewheel)
        self.bind("<MouseWheel>", on_mousewheel)

        self.refresh_grid()
        self.protocol("WM_DELETE_WINDOW", self.on_editor_closing)

    def refresh_grid(self):
        for widget in self.inner_frame.winfo_children():
            widget.destroy()

        # Table headers
        tk.Label(self.inner_frame, text="Select", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
        tk.Label(self.inner_frame, text="Theme", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(self.inner_frame, text="", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=5)
        for i, color_type in enumerate(self.color_types):
            tk.Label(self.inner_frame, text=color_type, font=("Arial", 10, "bold")).grid(row=0, column=i+3, padx=5, pady=5)
        tk.Label(self.inner_frame, text="Move", font=("Arial", 10, "bold")).grid(row=0, column=len(self.color_types)+3, padx=5, pady=5)

        for row, theme in enumerate(self.theme_order, start=1):
            chk = tk.Checkbutton(self.inner_frame, variable=self.selected_themes[theme], command=self.refresh_grid)
            chk.grid(row=row, column=0, padx=5, pady=5)

            name_entry = tk.Entry(self.inner_frame, width=15)
            name_entry.insert(0, theme)
            name_entry.grid(row=row, column=1, padx=5, pady=5, sticky="e")

            rename_btn = tk.Button(self.inner_frame, text="Rename", command=lambda t=theme, e=name_entry: self.rename_theme(t, e))
            rename_btn.grid(row=row, column=2, padx=2, pady=2)

            for col, color_type in enumerate(self.color_types):
                color = self.working_themes[theme][color_type]
                luminance = self.get_luminance(color)
                btn = tk.Button(self.inner_frame, bg=color, fg="#000000" if luminance > 0.5 else "#ffffff", text=color, width=10, height=2, relief="raised")
                btn.grid(row=row, column=col+3, padx=2, pady=2)
                btn.config(command=lambda c=color, b=btn, t=theme, ct=color_type: self.open_color_picker(c, b, t, ct))

            up_btn = tk.Button(self.inner_frame, text="↑", command=lambda t=theme: self.move_theme(t, -1), width=2)
            down_btn = tk.Button(self.inner_frame, text="↓", command=lambda t=theme: self.move_theme(t, 1), width=2)
            up_btn.grid(row=row, column=len(self.color_types)+3, padx=2, pady=2, sticky="w")
            down_btn.grid(row=row, column=len(self.color_types)+4, padx=2, pady=2, sticky="w")

        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def open_color_picker(self, current_color, button, theme, color_type):
        def check_and_center():
            for widget in self.winfo_children():
                try:
                    toplevel = widget.winfo_toplevel()
                    if "Choose color" in toplevel.title() and toplevel != self:
                        toplevel.update_idletasks()
                        root_x = self.winfo_x()
                        root_y = self.winfo_y()
                        root_width = self.winfo_width()
                        root_height = self.winfo_height()
                        dialog_width = toplevel.winfo_width()
                        dialog_height = toplevel.winfo_height()
                        x = root_x + (root_width - dialog_width) // 2
                        y = root_y + (root_height - dialog_height) // 2
                        toplevel.geometry(f"+{x}+{y}")
                        return True
                except AttributeError:
                    continue
            return False

        def poll_for_dialog():
            if not check_and_center():
                self.after(10, poll_for_dialog)

        self.after(0, poll_for_dialog)
        new_color = askcolor(color=current_color, title=f"Choose color for {theme} - {color_type}", parent=self)
        
        if new_color and new_color[1]:
            hex_color = new_color[1]
            button.config(bg=hex_color, text=hex_color)
            self.working_themes[theme][color_type] = hex_color
            luminance = self.get_luminance(hex_color)
            button.config(fg="#000000" if luminance > 0.5 else "#ffffff")
            self.update_preview(theme)

    def rename_theme(self, old_name, name_entry):
        """Renames a theme, safely synchronizing active parents/preferences if renamed."""
        new_name = name_entry.get().strip()
        if new_name and new_name != old_name and new_name not in self.working_themes:
            self.working_themes[new_name] = self.working_themes.pop(old_name)
            index = self.theme_order.index(old_name)
            self.theme_order[index] = new_name
            self.selected_themes[new_name] = self.selected_themes.pop(old_name)
            
            # Sync parent active settings if the renamed theme was currently active
            if old_name == self.parent_view.theme_var.get():
                self.parent_view.theme_var.set(new_name)
                self.theme_model.current_theme = new_name
                # Persist the renamed theme actively in preferences
                prefs = self.parent_view.controller.prefs_model.data
                prefs['theme'] = new_name
                self.parent_view.controller.prefs_model.save_preferences()

            self.refresh_grid()

    def move_theme(self, theme, direction):
        index = self.theme_order.index(theme)
        new_index = index + direction
        if 0 <= new_index < len(self.theme_order):
            self.theme_order[index], self.theme_order[new_index] = self.theme_order[new_index], self.theme_order[index]
            self.refresh_grid()

    def update_preview(self, theme):
        for widget in self.preview_frame.winfo_children():
            widget.destroy()

        colors = self.working_themes[theme]
        self.preview_frame.configure(bg=colors['bg'])

        tk.Label(self.preview_frame, text=theme, bg=colors['bg'], fg=colors['fg'], font=("Arial", 12, "bold")).pack(pady=10)
        tk.Button(self.preview_frame, text="Sample Button", bg=colors['button_bg'], fg=colors['button_fg']).pack(pady=5)
        tk.Entry(self.preview_frame, bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg']).pack(pady=5)

        # Full combobox preview styling restored
        style = ttk.Style()
        style.configure("Preview.TCombobox",
                        fieldbackground=colors['entry_bg'],
                        background=colors['button_bg'],
                        foreground=colors['fg'],
                        arrowcolor=colors['fg'],
                        bordercolor=colors['fg'],
                        lightcolor=colors['button_bg'],
                        darkcolor=colors['button_bg'],
                        borderwidth=2,
                        padding=1)                            
        style.map("Preview.TCombobox",
                  fieldbackground=[('disabled', colors['entry_bg'])],
                  background=[('disabled', colors['button_bg'])],
                  foreground=[('disabled', colors['fg'])])

        sample_combo = ttk.Combobox(self.preview_frame, values=["Option 1", "Option 2", "Option 3"], style="Preview.TCombobox", state="readonly")
        sample_combo.set("Option 1")
        sample_combo.pack(pady=5)

        # Restored 6 demo checkboxes to match original preview aesthetic
        for i in range(6):
            check_var = tk.BooleanVar(value=True)
            sample_check = tk.Checkbutton(self.preview_frame, text="Sample Checkbox", variable=check_var,
                                          bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
            sample_check.pack(pady=5)

        text_frame = tk.Frame(self.preview_frame, bg=colors['bg'])
        text_frame.pack(pady=5, fill="both", expand=True)

        scrollbar_preview = ttk.Scrollbar(text_frame, orient="vertical")
        scrollbar_preview.pack(side=tk.RIGHT, fill="y")

        sample_text = tk.Text(text_frame, height=6, width=20, bg=colors['entry_bg'], fg=colors['fg'], 
                              insertbackground=colors['fg'], wrap="word")
        sample_text.pack(side=tk.LEFT, fill="both", expand=True)
        sample_text.insert(tk.END, "--- NOTES ---\n\nTo preview click colors & select apply.\n\n")
        sample_text.configure(yscrollcommand=scrollbar_preview.set)
        scrollbar_preview.configure(command=sample_text.yview)

        style.configure("Preview.Vertical.TScrollbar",
                        background=colors['scrollbar_bg'],
                        troughcolor=colors['scrollbar_trough'],
                        arrowcolor=colors['fg'])
        style.map("Preview.Vertical.TScrollbar",
                  background=[('disabled', colors['scrollbar_bg'])])
        scrollbar_preview.configure(style="Preview.Vertical.TScrollbar")

    def on_editor_closing(self):
        response = messagebox.askyesnocancel("Save Changes", "Save changes to themecolors.json before exiting?")
        if response is True:
            filtered_themes = {theme: self.working_themes[theme] for theme in self.theme_order if self.selected_themes[theme].get()}
            self.theme_model.save_themes(filtered_themes)
            self.on_theme_applied_callback()
            self.destroy()
        elif response is False:
            self.destroy()


# =====================================================================
# VIEW LAYER (MAIN EXPLORER WINDOW)
# =====================================================================

class QuranView:
    """Standardizes main program's frames, buttons, checkboxes, texts, scroll binding and events."""
    def __init__(self, root: tk.Tk, controller: QuranController):
        self.root = root
        self.controller = controller
        
        self.root.title("Quran Verse Explorer")
        self.set_window_geometry()

        # Local User Notes Memory Buffer
        self.notes_buffer = {}

        # View variables mapped to properties
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add('write', self.filter_translations)
        
        # Pull pref values safely
        pref_data = self.controller.prefs_model.data
        self.last_reference = tk.StringVar(value=pref_data.get('last_reference', '1-114'))
        self.keyword_var = tk.StringVar(value=pref_data.get('last_keyword', ''))
        self.current_font = tk.StringVar(value=pref_data.get('font', DEFAULT_FONT))
        self.current_font_size = tk.StringVar(value=pref_data.get('font_size', DEFAULT_FONT_SIZE))
        self.theme_var = tk.StringVar(value=pref_data.get('theme', 'Default'))
        
        self.broad_search_var = tk.BooleanVar(value=pref_data.get('broad_search', False))
        self.broad_results_var = tk.BooleanVar(value=pref_data.get('broad_results', False))
        self.notes_var = tk.BooleanVar(value=pref_data.get('notes_enabled', False))
        self.tooltips_var = tk.BooleanVar(value=pref_data.get('tooltips_enabled', True))

        self.available_fonts = sorted(list(tkfont.families()))
        self.font_sizes = [str(size) for size in range(4, 37)]

        self.translation_vars = {}
        self.translation_checkbuttons = {}

        # Loading cover label
        self.loading_label = tk.Label(self.root, text="Loading data, please wait...", font=("Arial", 14))
        self.loading_label.pack(expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_closing)

    def set_window_geometry(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        usable_height = screen_height - 100
        if DEFAULT_WIDTH > screen_width or DEFAULT_HEIGHT > usable_height:
            self.root.state('zoomed')
        else:
            self.root.geometry(f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(800, 600)

        # Application Icon
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "quran.png")
        else:
            icon_path = os.path.join(base_path, "quran.png")
        try:
            self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
        except Exception as e:
            logging.error(f"Failed to load window icon: {e}")

    def on_window_closing(self):
        """Thread-safe and structural clean up during exit."""
        try:
            # Save active open note before exit
            if self.notes_var.get() and hasattr(self, 'notes_text') and self.notes_text and self.controller.last_ref_cache:
                current_note = self.notes_text.get("1.0", tk.END).strip()
                if current_note:
                    self.notes_buffer[self.controller.last_ref_cache] = current_note
                elif self.controller.last_ref_cache in self.notes_buffer:
                    del self.notes_buffer[self.controller.last_ref_cache]

            self.controller.quran_model.save_notes(self.notes_buffer)

            # Sync GUI preference values
            prefs = self.controller.prefs_model.data
            prefs['selected_translations'] = [trans for trans, var in self.translation_vars.items() if var.get()]
            prefs['broad_search'] = self.broad_search_var.get()
            prefs['broad_results'] = self.broad_results_var.get()
            prefs['notes_enabled'] = self.notes_var.get()
            prefs['tooltips_enabled'] = self.tooltips_var.get()
            prefs['last_reference'] = self.last_reference.get()
            prefs['font'] = self.current_font.get()
            prefs['font_size'] = self.current_font_size.get()
            prefs['theme'] = self.theme_var.get()
            prefs['last_keyword'] = self.keyword_var.get()

            self.controller.prefs_model.save_preferences()
        except Exception as e:
            logging.warning(f"Error saving states on closing: {e}")
        self.root.destroy()

    def build_gui(self):
        """Builds main frame splits and widgets."""
        if self.loading_label.winfo_exists():
            self.loading_label.destroy()

        colors = self.controller.theme_model.get_colors()
        self.root.configure(bg=colors['bg'])

        # Paned splitting window
        self.main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=colors['bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left split frame (Presets + Filter + Translations checklist)
        self.left_frame = tk.Frame(self.main_container, bg=colors['bg'], relief=tk.RAISED, bd=2)
        self.main_container.add(self.left_frame, width=DEFAULT_SASH_POSITION)
        self.left_frame.grid_rowconfigure(2, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Preset Frame on Row 0
        self.preset_frame = tk.Frame(self.left_frame, bg=colors['bg'])
        self.preset_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        for i in range(4):
            self.preset_frame.grid_columnconfigure(i, weight=1)

        self.save_preset_btn = tk.Button(self.preset_frame, text="Save", command=self.save_favorites_preset,
                                         bg=colors['button_bg'], fg=colors['button_fg'])
        self.save_preset_btn.grid(row=0, column=0, sticky="ew", padx=2)

        self.load_preset_btn = tk.Button(self.preset_frame, text="Load Saved", command=self.load_favorites_preset,
                                         bg=colors['button_bg'], fg=colors['button_fg'])
        self.load_preset_btn.grid(row=0, column=1, sticky="ew", padx=2)

        self.all_btn = tk.Button(self.preset_frame, text="All", command=self.select_all_translations,
                                 bg=colors['button_bg'], fg=colors['button_fg'])
        self.all_btn.grid(row=0, column=2, sticky="ew", padx=2)

        self.clear_btn = tk.Button(self.preset_frame, text="Clear", command=self.clear_all_translations,
                                   bg=colors['button_bg'], fg=colors['button_fg'])
        self.clear_btn.grid(row=0, column=3, sticky="ew", padx=2)

        # Filter Frame on Row 1
        self.filter_frame = tk.Frame(self.left_frame, bg=colors['bg'])
        self.filter_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.filter_label = tk.Label(self.filter_frame, text="Filter:", bg=colors['bg'], fg=colors['fg'])
        self.filter_label.pack(side=tk.LEFT, padx=5)

        self.filter_entry = tk.Entry(self.filter_frame, textvariable=self.filter_var,
                                     bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Canvas scroll frame for checklists on Row 2
        self.canvas = tk.Canvas(self.left_frame, bg=colors['bg'], highlightthickness=0)
        self.translations_scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical",
                                                    command=self.canvas.yview, style="Vertical.TScrollbar")
        self.scrollable_frame = tk.Frame(self.canvas, bg=colors['bg'], padx=3, pady=3)
        self.canvas.configure(yscrollcommand=self.translations_scrollbar.set)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        self.translations_scrollbar.grid(row=2, column=1, sticky="ns")

        # Scroll Wheel bindings for canvas
        for widget in (self.canvas, self.scrollable_frame):
            widget.bind("<MouseWheel>", self.on_canvas_mousewheel)
            widget.bind("<Button-4>", self.on_canvas_mousewheel)
            widget.bind("<Button-5>", self.on_canvas_mousewheel)

        # Populate translation checklists
        self.translation_vars.clear()
        self.translation_checkbuttons.clear()
        selected_prefs = self.controller.prefs_model.data.get('selected_translations', [])
        for i, trans in enumerate(self.controller.quran_model.translations):
            var = tk.BooleanVar(value=trans in selected_prefs)
            cb = tk.Checkbutton(self.scrollable_frame, text=trans, variable=var,
                                bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'],
                                command=self.trigger_search)
            cb.grid(row=i, column=0, sticky="w", padx=2, pady=0)
            cb.bind("<MouseWheel>", self.on_canvas_mousewheel)
            cb.bind("<Button-4>", self.on_canvas_mousewheel)
            cb.bind("<Button-5>", self.on_canvas_mousewheel)
            
            self.translation_vars[trans] = var
            self.translation_checkbuttons[trans] = cb

        # Right Split frame (Search toolbar + Results area)
        self.right_frame = tk.Frame(self.main_container, bg=colors['bg'])
        self.main_container.add(self.right_frame)
        self.right_frame.grid_rowconfigure(0, weight=0)
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        # Search framing
        self.search_frame = tk.Frame(self.right_frame, bg=colors['bg'], relief=tk.RAISED, bd=2)
        self.search_frame.grid(row=0, column=0, sticky="new", padx=5, pady=5)

        self.top_frame = tk.Frame(self.search_frame, bg=colors['bg'])
        self.top_frame.pack(fill=tk.X)

        tk.Label(self.top_frame, text="Surah.Verse-Range:\n(e.g., 36, 1-114, 2.255-27.30)",
                 bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)

        # Navigation controls
        self.navigate_prev_btn = tk.Button(self.top_frame, text="<", command=self.navigate_previous, width=2,
                                           bg=colors['button_bg'], fg=colors['button_fg'])
        self.navigate_prev_btn.pack(side=tk.LEFT, padx=2)

        self.ref_entry = tk.Entry(self.top_frame, textvariable=self.last_reference,
                                  bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.ref_entry.pack(side=tk.LEFT, padx=5)
        self.ref_entry.bind("<Return>", self.trigger_search)
        self.ref_entry.bind("<Double-Button-1>", self.reset_ref_range)

        self.navigate_next_btn = tk.Button(self.top_frame, text=">", command=self.navigate_next, width=2,
                                           bg=colors['button_bg'], fg=colors['button_fg'])
        self.navigate_next_btn.pack(side=tk.LEFT, padx=2)

        self.show_verses_btn = tk.Button(self.top_frame, text="Show Verses", command=self.trigger_search,
                                         bg=colors['button_bg'], fg=colors['button_fg'])
        self.show_verses_btn.pack(side=tk.LEFT, padx=5)

        self.copy_all_btn = tk.Button(self.top_frame, text="Copy", command=self.copy_all_results_to_clipboard,
                                      bg=colors['button_bg'], fg=colors['button_fg'])
        self.copy_all_btn.pack(side=tk.LEFT, padx=5)

        tk.Label(self.top_frame, text="Search Query:", bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)
        self.keyword_entry = tk.Entry(self.top_frame, textvariable=self.keyword_var,
                                      bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.keyword_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.keyword_entry.bind("<Return>", self.trigger_search)
        self.keyword_entry.bind("<Double-Button-1>", self.show_search_tips)

        self.broad_search_cb = tk.Checkbutton(self.top_frame, text="Broad Search",
                                              variable=self.broad_search_var, command=self.trigger_search,
                                              bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.broad_search_cb.pack(side=tk.LEFT, padx=5)
        
        self.broad_results_cb = tk.Checkbutton(self.top_frame, text="Broad Results",
                                               variable=self.broad_results_var, state="disabled", command=self.trigger_search,
                                               bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.broad_results_cb.pack(side=tk.LEFT, padx=5)
        self.broad_search_var.trace_add('write', self.toggle_broad_results_interactive)
        self.toggle_broad_results_interactive()

        # Toolbar Frame Font / Theme Selector
        self.font_frame = tk.Frame(self.search_frame, bg=colors['bg'])
        self.font_frame.pack(fill=tk.X, pady=2)

        tk.Label(self.font_frame, text="Font:", bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)
        self.font_combo = ttk.Combobox(self.font_frame, textvariable=self.current_font,
                                       values=self.available_fonts, state="readonly", style="MyCombo.TCombobox")
        self.font_combo.pack(side=tk.LEFT, padx=5)
        self.font_combo.bind("<<ComboboxSelected>>", self.update_active_font)
        self.font_combo.bind("<Leave>", lambda e: self.font_combo.selection_clear())

        tk.Label(self.font_frame, text="Size:", bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)
        self.size_combo = ttk.Combobox(self.font_frame, textvariable=self.current_font_size,
                                       values=self.font_sizes, state="readonly", style="MyCombo.TCombobox")
        self.size_combo.pack(side=tk.LEFT, padx=5)
        self.size_combo.bind("<<ComboboxSelected>>", self.update_active_font)
        self.size_combo.bind("<Leave>", lambda e: self.size_combo.selection_clear())

        tk.Label(self.font_frame, text="Theme:", bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)
        self.theme_combo = ttk.Combobox(self.font_frame, textvariable=self.theme_var,
                                        values=list(self.controller.theme_model.themes.keys()), state="readonly", style="MyCombo.TCombobox")
        self.theme_combo.pack(side=tk.LEFT, padx=5)
        self.theme_combo.bind("<<ComboboxSelected>>", self.apply_visual_theme)
        self.theme_combo.bind("<Leave>", lambda e: self.theme_combo.selection_clear())

        self.customize_btn = tk.Button(self.font_frame, text="Customize", command=self.open_custom_theme_editor,
                  bg=colors['button_bg'], fg=colors['button_fg'])
        self.customize_btn.pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(self.font_frame, textvariable=self.status_var, bg=colors['bg'], fg=colors['fg'])
        self.status_label.pack(side=tk.LEFT, padx=15)

        self.notes_checkbox = tk.Checkbutton(self.font_frame, text="Notes", variable=self.notes_var,
                                             bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'],
                                             command=self.toggle_notes_pane)
        self.notes_checkbox.pack(side=tk.RIGHT, padx=5)

        self.tooltips_checkbox = tk.Checkbutton(self.font_frame, text="Tips", variable=self.tooltips_var,
                                                bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.tooltips_checkbox.pack(side=tk.RIGHT, padx=5)

        # Primary Results Box Frame
        self.result_frame = tk.Frame(self.right_frame, bg=colors['bg'], relief=tk.FLAT, bd=0)
        self.result_frame.grid(row=1, column=0, sticky="nsew", padx=3, pady=2)
        self.result_frame.grid_rowconfigure(0, weight=1)
        self.result_frame.grid_columnconfigure(0, weight=1)

        self.result_text = tk.Text(self.result_frame, wrap=tk.WORD,
                                   font=(self.current_font.get(), int(self.current_font_size.get())),
                                   bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'],
                                   padx=13, pady=5)
        self.result_scrollbar = ttk.Scrollbar(self.result_frame, orient="vertical", command=self.result_text.yview, style="Vertical.TScrollbar")
        
        arabic_font_name = "Noto Naskh Arabic" if "Noto Naskh Arabic" in tkfont.families() else "Arial"
        self.arabic_font = tkfont.Font(family=arabic_font_name, size=int(self.current_font_size.get()) + 12)
        
        self.result_text.configure(yscrollcommand=self.result_scrollbar.set)
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.result_scrollbar.grid(row=0, column=1, sticky="ns")

        # Global bindings
        self.root.bind("<Prior>", lambda event: self.result_text.yview_scroll(-1, "pages"))
        self.root.bind("<Next>", lambda event: self.result_text.yview_scroll(1, "pages"))

        self.setup_text_tags()
        self.create_result_context_menus()
        
        self.main_container.sash_place(0, DEFAULT_SASH_POSITION, 0)

# tooltips

        # Bind Tooltips to Left Frame Preset Buttons
        ToolTip(self.save_preset_btn, "Save your currently selected translations", self.tooltips_var)
        ToolTip(self.load_preset_btn, "Restore your saved translations", self.tooltips_var)
        ToolTip(self.all_btn, "Select all translations", self.tooltips_var)
        ToolTip(self.clear_btn, "Deselect all translations", self.tooltips_var)
        # Bind Tooltips to Toolbar Controls
        ToolTip(self.ref_entry, "Type numbers here then press 'Enter' on keyboard\n\nTIP: Double-click inside this box to set range to 1-114", self.tooltips_var)
        ToolTip(self.keyword_entry, "Type query here then press 'Enter' on keyboard\n\nDouble-click inside this box to show the help guide", self.tooltips_var)
        ToolTip(self.broad_search_cb, "Expand search query across all translations,\n but only display selected translation(s)", self.tooltips_var)
        ToolTip(self.broad_results_cb, "Include all translations containing the search query irrespective of selected translation(s)", self.tooltips_var)
        ToolTip(self.notes_checkbox, "Show or hide the User Notes window pane\n\nTIP: After making your first note, a file will be saved to the program folder named 'Notes.xml'.  On the next program launch, select the box 'User Notes' at the top of the list of translators\n\nNote-taking is limited to 1 verse at a time", self.tooltips_var)
        ToolTip(self.tooltips_checkbox, "Enable/Disable floating tooltips (like this one)", self.tooltips_var)
        # Filter
        ToolTip(self.filter_entry, "Type here to filter the below translators list\n\nTIP:\nAfter typing...\nKeyboard 'TAB' to highlight a translation\n(or Shift-Tab to move up)\n& 'Spacebar' to select/deselect", self.tooltips_var)
        # Navigation
        ToolTip(self.navigate_prev_btn, "Navigate to the previous verse", self.tooltips_var)
        ToolTip(self.navigate_next_btn, "Navigate to the next verse", self.tooltips_var)
        # Action Buttons
        ToolTip(self.show_verses_btn, "Apply verse range & search criteria\n(or press 'Enter' on keyboard).", self.tooltips_var)
        ToolTip(self.copy_all_btn, "Copy all displayed results to the clipboard, which can be a lot.!!\nTo be selective, use mouse:\nHighlight any portion of displayed text\nRight click ->'copy'", self.tooltips_var)
        # ComboBoxes
        ToolTip(self.font_combo, "Choose a font\nTIP: mouse-over + scroll with mousewheel", self.tooltips_var)
        ToolTip(self.size_combo, "Change font size\nTIP: mouse-over + scroll with mousewheel", self.tooltips_var)
        ToolTip(self.theme_combo, "Select color theme\nTIP: mouse-over + scroll with mousewheel", self.tooltips_var)
        # Theme Editor
        ToolTip(self.customize_btn, "Open the Theme Customizer", self.tooltips_var)
   
        self.apply_visual_theme()

        # Render Welcoming splash screen AKA help guide
        self.render_welcome_screen()
        # Check notes preference and toggle open notes pane - important upon initial program launch
        if self.notes_var.get():
            self.toggle_notes_pane()
   
    def render_welcome_screen(self):
        """ Both the splash screen and the help screen (appears when double clicking in the Search Query field)"""        
        self.result_text.delete(1.0, tk.END)

        self.result_text.insert(tk.END, "\n")
        self.result_text.insert(tk.END, "Bismillah  ---  SalamunAlaykum", ("bold", "center"))
        self.result_text.insert(tk.END, "\n\n")
        self.result_text.insert(tk.END, "Click the  ", ("bold", "center"))
        self.result_text.insert(tk.END, "Show Verses", ("border", "bold", "center"))
        self.result_text.insert(tk.END, "  button above\n\n", ("bold", "center"))

        self.result_text.insert(tk.END, "General Use Tips:\n\n", ("bold", "underline"))
        self.result_text.insert(tk.END, "• Read this more easily by choosing a font & size to your liking\n")
        self.result_text.insert(tk.END, "  .. try 'Leelawadee UI' if using MS Windows\n")
        self.result_text.insert(tk.END, "  .. mouse over the 'Size' and scroll with mouse wheel to dynamically change it\n\n")
        self.result_text.insert(tk.END, "• Enable the ")
        self.result_text.insert(tk.END, "' Tips '", "bold")
        self.result_text.insert(tk.END, " checkbox and hold mouse over items for interactive help\n\n")
        self.result_text.insert(tk.END, "• Return to this help guide by double clicking inside the 'Search Query' field\n\n")

        self.result_text.insert(tk.END, "Search Tips:\n\n", ("bold", "underline"))

        self.result_text.insert(tk.END, "• Pressing ")
        self.result_text.insert(tk.END, "Enter", "bold")
        self.result_text.insert(tk.END, " is equivalent to clicking 'Show Verses'\n\n")

        self.result_text.insert(tk.END, "• All searches are ")
        self.result_text.insert(tk.END, "CaSe-INsensitive\n\n", "bold")

        self.result_text.insert(tk.END, "• The order of terms does ")
        self.result_text.insert(tk.END, "not", "bold")
        self.result_text.insert(tk.END, " matter: (crescent moons = moons crescent)\n")
        self.result_text.insert(tk.END, "  .. if order is important, then use ")
        self.result_text.insert(tk.END, "\"quotes\"", "bold")
        self.result_text.insert(tk.END, " to find an exact phrase (e.g., \"upon his sons\")\n\n")
        self.result_text.insert(tk.END, "• Surrounding the search term in ")
        self.result_text.insert(tk.END, "\"quotes\"", "bold")
        self.result_text.insert(tk.END, " includes the 'space' character in the search\n")
        self.result_text.insert(tk.END, "  .. \"ent m\" finds: s")
        self.result_text.insert(tk.END, "ent m", "bold")
        self.result_text.insert(tk.END, "essengers & cresc")
        self.result_text.insert(tk.END, "ent m", "bold")
        self.result_text.insert(tk.END, "oons\n")
        self.result_text.insert(tk.END, "  .. each of these 5 examples gives unique results: \" here\" / \" here \" / \"here \" / \"here\" / here (without quotes)\n\n")

        self.result_text.insert(tk.END, "• ")
        self.result_text.insert(tk.END, " ' * ' ", "bold")
        self.result_text.insert(tk.END, " = multi-character wildcard - ' ")
        self.result_text.insert(tk.END, "*after", "bold")
        self.result_text.insert(tk.END, " ' will find: HEREafter\n")
        self.result_text.insert(tk.END, "  .. wildcard is ")
        self.result_text.insert(tk.END, "not ", "bold")
        self.result_text.insert(tk.END, "required on term endings (' test ' will find: testED)\n\n")

        self.result_text.insert(tk.END, "• ")
        self.result_text.insert(tk.END, " ' ? '", "bold")
        self.result_text.insert(tk.END, " = single character wildcard\n .. ")
        self.result_text.insert(tk.END, "' m?ha '", "bold")
        self.result_text.insert(tk.END, " finds both: MUhammad & MOhamed\n\n")

        self.result_text.insert(tk.END, "• Wildcards may be combined - ")
        self.result_text.insert(tk.END, " ' ?brah*m ' ", "bold")
        self.result_text.insert(tk.END, " finds both: AbrahAm & IbrahEEm\n\n")

        self.result_text.insert(tk.END, "• Broad Search\n", "bold")
        self.result_text.insert(tk.END, "  .. When disabled, looks only inside the selected translation(s) for your query\n")
        self.result_text.insert(tk.END, "  .. When enabled, looks in all translations, but only your selected translation(s) are displayed\n")
        self.result_text.insert(tk.END, "  .. Search is nearly instantaneous when disabled; slow when enabled\n")
        self.result_text.insert(tk.END, "  .. Useful because Arabic words get translated into various synonymous English words by different translators\n\n")
        self.result_text.insert(tk.END, "• Broad Results\n", "bold")
        self.result_text.insert(tk.END, "  .. Adds all translations matching the query irrespective of selected translation(s)\n\n")

        self.result_text.insert(tk.END, "Training Example:\n", ("bold", "underline"))
        self.result_text.insert(tk.END, " 1) Select these 2 translators only: 'Abdel Haleem' & 'Abdul Hye'\n")
        self.result_text.insert(tk.END, " 2) Set surah.verse-range to ")
        self.result_text.insert(tk.END, "'1-114'", "bold")
        self.result_text.insert(tk.END, " (The entire Quran)\n")
        self.result_text.insert(tk.END, " 3) Disable 'Broad Search'\n")
        self.result_text.insert(tk.END, " 4) Search for the keyword:  ")
        self.result_text.insert(tk.END, "hive", ("bold"))
        self.result_text.insert(tk.END, "\n")
        self.result_text.insert(tk.END, " 5) You will see:  'No verses match the search criteria'\n")
        self.result_text.insert(tk.END, " 6) Enable 'Broad Search' but leave 'Broad Results' disabled\n")
        self.result_text.insert(tk.END, " 7) Now it finds 1 verse, and displays it for the 2 selected translations\n")
        self.result_text.insert(tk.END, " 8) Notice that 'hive' does not appear in the results, as Abdel Haleem used 'houses' & Abdul Hye used 'habitations'\n")
        self.result_text.insert(tk.END, " 9) Next, enable: ")
        self.result_text.insert(tk.END, "'Broad Results'",("bold"))
        self.result_text.insert(tk.END, "\n")
        self.result_text.insert(tk.END, " 10) An additional 26 translations are shown; all those containing the word 'hive'\n")
        self.result_text.insert(tk.END, " 11) Notice the status bar reports: 'Found 1 verse in 2+26 translations'\n\n")

        self.result_text.insert(tk.END, "code base 960\n", "right")
        self.result_text.insert(tk.END, "June 2026\n", "right")
        self.result_text.insert(tk.END, "reez@hotmail.com\n", "right")
        self.result_text.insert(tk.END, "https://github.com/reez79/IslamAwakened_XML", "right")

        self.status_var.set("Ready - Click the 'Show Verses' button")

    def toggle_broad_results_interactive(self, *args):
        state = "normal" if self.broad_search_var.get() else "disabled"
        self.broad_results_cb.configure(state=state)

    def on_canvas_mousewheel(self, event):
        """Standardized wheel interaction for list checklist bounds."""
        if event.delta:
            delta = -1 if event.delta > 0 else 1
        elif event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = 0
        if delta:
            self.canvas.yview_scroll(delta, "units")

    def filter_translations(self, *args):
        """Filters scrollable checkbox list search matches interactively."""
        search_text = self.filter_var.get().lower()
        for i, trans in enumerate(self.controller.quran_model.translations):
            cb = self.translation_checkbuttons[trans]
            if search_text in trans.lower():
                cb.grid(row=i, column=0, sticky="w", padx=2, pady=0)
            else:
                cb.grid_forget()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def setup_text_tags(self):
        """Formats layout, spacing, colors and fonts of nested text views."""
        colors = self.controller.theme_model.get_colors()
        self.result_text.tag_configure("spacing", spacing1=5)
        self.result_text.tag_configure("border", borderwidth=1, relief="raised")
        self.result_text.tag_configure("bold", font=(self.current_font.get(), int(self.current_font_size.get()), "bold"))
        self.result_text.tag_configure("underline", underline=True)
        self.result_text.tag_configure("highlight", foreground=colors['selectbg'])
        self.result_text.tag_configure("center", justify="center")
        self.result_text.tag_configure("right", justify="right")      
        self.result_text.tag_configure("arabic_rtl", font=self.arabic_font)
        self.result_text.tag_configure("arabic_space", spacing3=3)
        self.result_text.tag_configure("english_space", spacing3=1)
        self.result_text.tag_configure("header_space", spacing1=12)

    def open_custom_theme_editor(self):
        """Launches detached, decoupled Toplevel window for custom color curation."""
        ThemeCustomizer(self, self.controller.theme_model, self.on_theme_editor_callback)

    def on_theme_editor_callback(self):
        """Fires when theme editor exits with modifications."""
        self.theme_combo['values'] = list(self.controller.theme_model.themes.keys())
        self.theme_var.set(self.controller.theme_model.current_theme)
        self.apply_visual_theme()

    def update_active_font(self, event=None):
        """Updates standard result views with dynamically adapted fonts."""
        font_name = self.current_font.get()
        if font_name not in tkfont.families():
            font_name = DEFAULT_FONT
            self.current_font.set(font_name)
        try:
            self.result_text.configure(font=(font_name, int(self.current_font_size.get())))
            self.arabic_font.configure(size=int(self.current_font_size.get()) + 12)
            self.result_text.tag_configure("arabic_rtl", font=self.arabic_font)
            self.setup_text_tags()
        except tk.TclError:
            self.current_font.set(DEFAULT_FONT)
            self.current_font_size.set(DEFAULT_FONT_SIZE)
            self.result_text.configure(font=(DEFAULT_FONT, int(DEFAULT_FONT_SIZE)))
            self.arabic_font.configure(family=DEFAULT_FONT, size=int(DEFAULT_FONT_SIZE) + 12)
            self.result_text.tag_configure("arabic_rtl", font=self.arabic_font)
            self.setup_text_tags()

    def apply_visual_theme(self, event=None):
        """Applies loaded colors selectively across standard/TTK components."""
        theme_name = self.theme_var.get()
        self.controller.theme_model.set_theme(theme_name)
        colors = self.controller.theme_model.get_colors()

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("MyCombo.TCombobox",
                        fieldbackground=colors['entry_bg'],
                        background=colors['button_bg'],
                        foreground=colors['fg'],
                        arrowcolor=colors['fg'],
                        bordercolor=colors['fg'],
                        lightcolor=colors['button_bg'],
                        darkcolor=colors['button_bg'],
                        borderwidth=2,
                        padding=1)
        style.map("MyCombo.TCombobox",
                  fieldbackground=[('readonly', colors['entry_bg'])],
                  background=[('readonly', colors['button_bg'])])

        style.configure("Vertical.TScrollbar",
                        background=colors['scrollbar_bg'],
                        troughcolor=colors['scrollbar_trough'],
                        arrowcolor=colors['fg'])
        style.map("Vertical.TScrollbar",
                  background=[('disabled', colors['scrollbar_bg'])])

        self.root.configure(bg=colors['bg'])
        self.main_container.configure(bg=colors['bg'])
        self.left_frame.configure(bg=colors['bg'])
        self.filter_frame.configure(bg=colors['bg'])
        self.canvas.configure(bg=colors['bg'])
        self.scrollable_frame.configure(bg=colors['bg'])
        self.right_frame.configure(bg=colors['bg'])
        self.search_frame.configure(bg=colors['bg'])
        self.top_frame.configure(bg=colors['bg'])
        self.font_frame.configure(bg=colors['bg'])
        self.result_frame.configure(bg=colors['bg'])

        for cb in self.translation_checkbuttons.values():
            cb.configure(bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.broad_search_cb.configure(bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.broad_results_cb.configure(bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])

        self.filter_entry.configure(bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.ref_entry.configure(bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.keyword_entry.configure(bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])

        self.preset_frame.configure(bg=colors['bg'])
        for widget in self.top_frame.winfo_children() + self.font_frame.winfo_children() + self.filter_frame.winfo_children() + self.preset_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.configure(bg=colors['button_bg'], fg=colors['button_fg'])
            elif isinstance(widget, tk.Label):
                widget.configure(bg=colors['bg'], fg=colors['fg'])

        self.notes_checkbox.configure(bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.tooltips_checkbox.configure(bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.result_text.configure(bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.result_scrollbar.configure(style="Vertical.TScrollbar")
        self.translations_scrollbar.configure(style="Vertical.TScrollbar")

        # Dynamically scale User Notes split panes if present
        if hasattr(self, 'result_pane'):
            self.result_pane.configure(bg=colors['bg'])
        if hasattr(self, 'notes_frame'):
            self.notes_frame.configure(bg=colors['bg'])
        if hasattr(self, 'notes_text'):
            self.notes_text.configure(bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        if hasattr(self, 'notes_scrollbar'):
            self.notes_scrollbar.configure(style="Vertical.TScrollbar")

        self.canvas.configure(scrollregion=self.canvas.bbox("all") or (0, 0, 300, 400))

    def create_result_context_menus(self):
        """Creates copy selections inside main viewing text area."""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selected_text)
        self.result_text.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        if self.result_text.tag_ranges("sel"):
            self.context_menu.post(event.x_root, event.y_root)

    def copy_selected_text(self):
        try:
            selected_text = self.result_text.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.status_var.set("Selected text copied to clipboard")
        except tk.TclError:
            self.status_var.set("No text selected to copy")

    def copy_all_results_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result_text.get(1.0, tk.END))
        self.status_var.set("All verses copied to clipboard")

    def reset_ref_range(self, event=None):
        self.last_reference.set("1-114")
        self.trigger_search()
        return "break"

    def navigate_previous(self):
        """Navigates sequence backward using standard parsed bounds."""
        try:
            surah_start, start_ayah, surah_end, end_ayah = self.controller.parse_reference(self.ref_entry.get())
            if surah_start == surah_end and start_ayah == end_ayah:
                prev_verse = self.controller.get_previous_verse(surah_start, start_ayah)
                if prev_verse:
                    new_ref = f"{prev_verse[0]}.{prev_verse[1]}"
                    self.last_reference.set(new_ref)
                    self.trigger_search(from_navigation=True)
            else:
                new_ref = f"{surah_start}.{start_ayah}"
                self.last_reference.set(new_ref)
                self.trigger_search(from_navigation=True)
        except ValueError:
            pass

    def navigate_next(self):
        """Navigates sequence forward using standard parsed bounds."""
        try:
            surah_start, start_ayah, surah_end, end_ayah = self.controller.parse_reference(self.ref_entry.get())
            if surah_start == surah_end and start_ayah == end_ayah:
                next_verse = self.controller.get_next_verse(surah_start, start_ayah)
                if next_verse:
                    new_ref = f"{next_verse[0]}.{next_verse[1]}"
                    self.last_reference.set(new_ref)
                    self.trigger_search(from_navigation=True)
            else:
                new_ref = f"{surah_end}.{end_ayah}"
                self.last_reference.set(new_ref)
                self.trigger_search(from_navigation=True)
        except ValueError:
            pass

    def toggle_notes_pane(self):
        """Adapts split-pane structure to reveal user notes dynamically next to verse panels."""
        colors = self.controller.theme_model.get_colors()
        
        if self.notes_var.get():
            # Clear keyword focus unconditionally
            self.keyword_var.set("")

            # Resolve coordinates
            if self.controller.search_results_cache:
                new_ref = self.controller.search_results_cache[0]
                self.last_reference.set(new_ref)
            else:
                try:
                    s_start, a_start, s_end, a_end = self.controller.parse_reference(self.last_reference.get())
                    if s_start != s_end or a_start != a_end:
                        self.last_reference.set(f"{s_start}.{a_start}")
                except ValueError:
                    self.last_reference.set('1.1')

            # Empty results pane
            for widget in self.result_frame.winfo_children():
                widget.destroy()

            # Construct dual Paned split layout
            self.result_pane = tk.PanedWindow(self.result_frame, orient=tk.HORIZONTAL, bg=colors['bg'],
                                             sashwidth=5, sashrelief=tk.RAISED)
            self.result_pane.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

            # Left split (verses)
            verse_frame = tk.Frame(self.result_pane, bg=colors['bg'])
            self.result_text = tk.Text(verse_frame, wrap=tk.WORD,
                                       font=(self.current_font.get(), int(self.current_font_size.get())),
                                       bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'],
                                       padx=14, pady=9)
            self.result_scrollbar = ttk.Scrollbar(verse_frame, orient="vertical", command=self.result_text.yview, style="Vertical.TScrollbar")
            self.result_text.configure(yscrollcommand=self.result_scrollbar.set)
            self.result_text.grid(row=0, column=0, sticky="nsew")
            self.result_scrollbar.grid(row=0, column=1, sticky="ns")
            self.setup_text_tags()
            verse_frame.grid_rowconfigure(0, weight=1)
            verse_frame.grid_columnconfigure(0, weight=1)
            self.result_pane.add(verse_frame, minsize=400)

            # Right split (notes)
            self.notes_frame = tk.Frame(self.result_pane, bg=colors['bg'])
            self.notes_text = tk.Text(self.notes_frame, wrap=tk.WORD,
                                      font=(self.current_font.get(), int(self.current_font_size.get())),
                                      bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'],
                                      padx=14, pady=9)
            self.notes_scrollbar = ttk.Scrollbar(self.notes_frame, orient="vertical", command=self.notes_text.yview, style="Vertical.TScrollbar")
            self.notes_text.configure(yscrollcommand=self.notes_scrollbar.set)
            self.notes_text.grid(row=0, column=0, sticky="nsew")
            self.notes_scrollbar.grid(row=0, column=1, sticky="ns")
            self.notes_frame.grid_rowconfigure(0, weight=1)
            self.notes_frame.grid_columnconfigure(0, weight=1)
            self.result_pane.add(self.notes_frame, minsize=200)

            # Map mousewheel mappings back
            self.root.bind("<Prior>", lambda event: self.result_text.yview_scroll(-1, "pages"))
            self.root.bind("<Next>", lambda event: self.result_text.yview_scroll(1, "pages"))

            # Sync note text contents
            active_ref = self.last_reference.get()
            if active_ref in self.notes_buffer:
                self.notes_text.insert("1.0", self.notes_buffer[active_ref])

            self.trigger_search(from_notes=True)
        else:
            # Save notes before exit notes layout
            if hasattr(self, 'notes_text') and self.notes_text and self.controller.last_ref_cache:
                current_note = self.notes_text.get("1.0", tk.END).strip()
                if current_note:
                    self.notes_buffer[self.controller.last_ref_cache] = current_note
                elif self.controller.last_ref_cache in self.notes_buffer:
                    del self.notes_buffer[self.controller.last_ref_cache]
                self.controller.quran_model.save_notes(self.notes_buffer)

            if hasattr(self, 'result_pane'):
                self.result_pane.destroy()
            self.notes_text = None

            # Reconstruct basic output block
            self.result_text = tk.Text(self.result_frame, wrap=tk.WORD,
                                       font=(self.current_font.get(), int(self.current_font_size.get())),
                                       bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'],
                                       padx=14, pady=9)
            self.result_scrollbar = ttk.Scrollbar(self.result_frame, orient="vertical", command=self.result_text.yview, style="Vertical.TScrollbar")
            self.result_text.configure(yscrollcommand=self.result_scrollbar.set)
            self.result_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            self.result_scrollbar.grid(row=0, column=1, sticky="ns")
            
            self.setup_text_tags()
            self.root.bind("<Prior>", lambda event: self.result_text.yview_scroll(-1, "pages"))
            self.root.bind("<Next>", lambda event: self.result_text.yview_scroll(1, "pages"))
            
            self.trigger_search()

    def save_favorites_preset(self):
        """Saves current selected translations to favorites key in preferences."""
        prefs = self.controller.prefs_model.data
        prefs['favorite_translations'] = [trans for trans, var in self.translation_vars.items() if var.get()]
        self.controller.prefs_model.save_preferences()
        self.status_var.set("Saved current translations to favorites")

    def load_favorites_preset(self):
        """Loads favorite translations from preferences, updates checkboxes, and triggers search."""
        favs = self.controller.prefs_model.data.get('favorite_translations', [])
        if not favs:
            self.status_var.set("No saved favorites found")
            return
        for trans, var in self.translation_vars.items():
            var.set(trans in favs)
        self.trigger_search()
        self.status_var.set("Loaded saved translation favorites")

    def select_all_translations(self):
        """Selects all translation checkboxes and triggers search."""
        for var in self.translation_vars.values():
            var.set(True)
        self.trigger_search()
        self.status_var.set("All translations selected")

    def clear_all_translations(self):
        """Deselects all translation checkboxes and triggers search."""
        for var in self.translation_vars.values():
            var.set(False)
        self.trigger_search()
        self.status_var.set("All translations cleared")

    def show_search_tips(self, event=None):
        """Displays search tips in the results window."""
        self.render_welcome_screen()
        self.status_var.set("Showing search tips.")

    def trigger_search(self, event=None, from_notes=False, from_navigation=False):
        """Invokes search from user actions, formatting text outputs in view cleanly."""
        if self.notes_var.get() and not from_navigation and not from_notes:
            ref_val = self.ref_entry.get().strip()
            try:
                s_s, a_s, s_e, a_e = self.controller.parse_reference(ref_val)
                if not (s_s == s_e and a_s == a_e):
                    messagebox.showwarning("Notes Mode", "only single verses may be selected when notes pane is open")
                    return
            except ValueError:
                pass

        if not from_notes and self.notes_var.get() and self.keyword_var.get().strip():
            messagebox.showinfo("Close your 'Notes' - or - Clear the search field", 
                                "Before searching, clear the 'Notes' checkbox \n and choose a search range, typically: 1-114")
            return

        # Save buffer note
        if hasattr(self, 'notes_text') and self.notes_text and self.controller.last_ref_cache:
            prev_note_text = self.notes_text.get("1.0", tk.END).strip()
            if prev_note_text:
                self.notes_buffer[self.controller.last_ref_cache] = prev_note_text
            elif self.controller.last_ref_cache in self.notes_buffer:
                del self.notes_buffer[self.controller.last_ref_cache]
            self.controller.quran_model.save_notes(self.notes_buffer)

        ref_val = self.ref_entry.get().strip()
        keyword_val = self.keyword_var.get().strip()
        selected_translations = [trans for trans, var in self.translation_vars.items() if var.get()]

        if not selected_translations:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "Select at least one translation to display verses.")
            self.status_var.set("No translations selected")
            return

        # Execute business query safely in Controller
        outcome = self.controller.query_verses(
            ref_str=ref_val,
            keyword=keyword_val,
            selected_translations=selected_translations,
            broad_search=self.broad_search_var.get(),
            broad_results=self.broad_results_var.get(),
            notes_active=self.notes_var.get(),
            from_navigation=from_navigation
        )

        if not outcome['success']:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"'{self.ref_entry.get().strip()}' is an invalid verse reference format\n\nPress 'Enter' now to accept '1-114'\n\nOr try:\n- Any surah (e.g., 1)\n- A specific verse (e.g., 2.225)\n- Range of surahs (e.g., 3-4)\n- Specific range (e.g., 1.6-1.7)\n\nUse 1-114 while searching the entire Quran")
            self.status_var.set("invalid range - reset to 1-114 - press 'Enter'")
            self.last_reference.set(outcome['fallback_ref'])
            self.ref_entry.update()
            return

        # Clear viewer and format output
        self.result_text.delete(1.0, tk.END)
        verses = outcome['verses']

        if outcome['verse_count'] == 0:
            self.result_text.insert(tk.END, "No verses match the search criteria.\n")
            self.status_var.set("No verses match the search criteria")
            return

        # Populate structured output
        for v in verses:
            # FIX: If there is no translation text to display, skip the header entirely
            if not v['texts']:
                continue
                
            self.result_text.insert(tk.END, f"Surah {v['surah_num']} - {v['arabic_name']} ({v['english_name']}): Ayah {v['ayah_num']}\n", "header_space")
            
            # Restored exact vertical line spacing layout from 930
            added_spacing = "\n" if "Arabic" not in v['display_translations'] else ""
            self.result_text.insert(tk.END, f"{'=' * 40}\n{added_spacing}")
            
            # Formatted text insertion
            for trans, text in v['texts'].items():
                tags = ("arabic_rtl", "arabic_space") if trans == "Arabic" else ("english_space",) if trans != "User Notes" else ()
                label = "" if trans == "Arabic" else f"{trans}:\n"
                
                if trans == "Arabic":
                    self.result_text.insert(tk.END, f"{label}{text}", tags)
                    self.result_text.insert(tk.END, "\n\n", "english_space")
                else:
                    self.result_text.insert(tk.END, f"{label}{text}\n\n", tags)

        # Update note text area if open
        if hasattr(self, 'notes_text') and self.notes_text and outcome['last_ref']:
            self.notes_text.delete("1.0", tk.END)
            if outcome['last_ref'] in self.notes_buffer:
                self.notes_text.insert("1.0", self.notes_buffer[outcome['last_ref']])

        # Update labels / statuses
        verse_count = outcome['verse_count']
        verse_label = "verse" if verse_count == 1 else "verses"
        # Simple arithmetic for the label
        translation_count = len(selected_translations)
        if 'Arabic' in selected_translations:
            translation_count -= 1
        if 'User Notes' in selected_translations:
            translation_count -= 1

        if self.broad_search_var.get() and self.broad_results_var.get():
            extra_count = len(outcome['all_displayed_translations'] - set(selected_translations))
            total_trans = translation_count + extra_count
            trans_label = "translation" if total_trans == 1 else "translations"
            self.status_var.set(f"Found {verse_count} {verse_label} in {translation_count}+{extra_count} {trans_label}")
        else:
            trans_label = "translation" if translation_count == 1 else "translations"
            self.status_var.set(f"Found {verse_count} {verse_label} in {translation_count} {trans_label}")


# =====================================================================
# MAIN RUNNER (THREAD-SAFE BOOTSTRAPPING)
# =====================================================================

def main():
    root = tk.Tk()
    controller = QuranController()
    view = QuranView(root, controller)

    # 1. Thread-safe: Execute I/O prompt check directly on main thread BEFORE spawning threads
    resolved_xml_path = Path(xml_default_path)
    if not resolved_xml_path.exists():
        messagebox.showinfo("Select XML File", 
                            "Database file (ia_all.xml) not found alongside program file.\n"
                            "Did you extract it (unzip) ?\n"
                            "Press 'OK' to specify an alternate location.\n\n"
                            "TIP: ia_all.xml loads automatically when saved in the same folder as the program file.\n\n"
                            "NOTE: This program is capable of reading the NON-English traslations database if you select IA_all_multilang.xml during the next step.\n\n"
                            "The latest XML datadase may be downloaded from:\n"
                            "IslamAwakened.com\n"
                            "(Follow link to 'Downloadable Database')\n\n"
                            "ia_all.zip is also at github\n"
                            "https://github.com/reez79/IslamAwakened_XML\n")
        
        selected_file = filedialog.askopenfilename(
            title="Select Quran XML File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        
        if not selected_file:
            messagebox.showinfo("No File Selected", "No file selected. The application will now exit.")
            root.destroy()
            sys.exit("No XML file selected")
        
        resolved_xml_path = Path(selected_file)

    # 2. Spawn async XML data parsing cleanly
    def on_load_success():
        # Copy loaded user notes directly to view panel buffers
        view.notes_buffer = controller.quran_model.user_notes.copy()
        view.build_gui()

    def on_load_error(error):
        messagebox.showerror("Error", f"An error occurred loading database XML:\n{error}")
        root.destroy()

    controller.start_data_load_async(
        xml_path=resolved_xml_path,
        on_success_callback=on_load_success,
        on_error_callback=on_load_error
    )

    root.mainloop()


if __name__ == "__main__":
    main()

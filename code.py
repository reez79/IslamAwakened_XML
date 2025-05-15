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
from tkcolorpicker import askcolor
# from PIL import Image, ImageTk  # Pillow for program icon in titlebar

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

class ToolTip:
    """A simple tooltip class for Tkinter widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Arial", "10", "normal"))
        label.pack()

    def hide_tip(self, event):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

# Custom Theme Class
class Theme:
    """Manages application themes, including loading, saving, and applying color schemes."""
    def __init__(self):
        self.themes = {}
        self.current_theme = "Default"  # Initial guess, overridden by prefs
        self.load_themes()
        # Ensure defaults if no themes exist
        if not self.themes:
            self.themes["Default"] = {
                "bg": "#333333",
                "fg": "#ffffff",
                "selectbg": "#717171",
                "button_bg": "#717171",
                "button_fg": "#ffffff",
                "entry_bg": "#262626",
                "scrollbar_bg": "#717171",
                "scrollbar_trough": "#3B3B3B"
            }
            self.current_theme = "Default"

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

    def set_default_themes(self):
        """Sets the default themes if no theme file is found."""
        self.themes = {
            "DEMO": {
                "bg": "#F6CB68",
                "fg": "#FF0000",
                "selectbg": "#67FFDB",
                "button_bg": "#90008B",
                "button_fg": "#A2FF00",
                "entry_bg": "#193B00",
                "scrollbar_bg": "#0000FF",
                "scrollbar_trough": "#359AB6"
            },
            "Light": {
                "bg": "#FFFFFF",
                "fg": "#000000",
                "selectbg": "#d0d0d0",
                "button_bg": "#e0e0e0",
                "button_fg": "#000000",
                "entry_bg": "#ffffff",
                "scrollbar_bg": "#e0e0e0",
                "scrollbar_trough": "#d0d0d0"
            },
            "Beige": {
                "bg": "#f5f5dc",
                "fg": "#3c2f2f",
                "selectbg": "#e0d8b0",
                "button_bg": "#e6e4c5",
                "button_fg": "#3c2f2f",
                "entry_bg": "#fff8e7",
                "scrollbar_bg": "#e6e4c5",
                "scrollbar_trough": "#d9d2a3"
            },
            "Honey": {
                "bg": "#f5f5dc",
                "fg": "#3f2a1d",
                "selectbg": "#e0c080",
                "button_bg": "#e8c88c",
                "button_fg": "#3f2a1d",
                "entry_bg": "#ffebcc",
                "scrollbar_bg": "#e8c88c",
                "scrollbar_trough": "#d9b973"
            },
            "Spring": {
                "bg": "#d9f0d3",
                "fg": "#2d4a3b",
                "selectbg": "#b8d9b0",
                "button_bg": "#c8e0c2",
                "button_fg": "#2d4a3b",
                "entry_bg": "#e6f5e6",
                "scrollbar_bg": "#c8e0c2",
                "scrollbar_trough": "#b3d9a8"
            },
            "Default": {
                "bg": "#333333",
                "fg": "#ffffff",
                "selectbg": "#717171",
                "button_bg": "#717171",
                "button_fg": "#ffffff",
                "entry_bg": "#262626",
                "scrollbar_bg": "#717171",
                "scrollbar_trough": "#3B3B3B"
            },
            "Black": {
                "bg": "#000000",
                "fg": "#ffffff",
                "selectbg": "#333333",
                "button_bg": "#2C2C2C",
                "button_fg": "#ffffff",
                "entry_bg": "#000000",
                "scrollbar_bg": "#434343",
                "scrollbar_trough": "#000000"
            },
            "Blue": {
                "bg": "#1e3a5f",
                "fg": "#ffffff",
                "selectbg": "#2e5a8f",
                "button_bg": "#2e5a8f",
                "button_fg": "#ffffff",
                "entry_bg": "#2a4a7a",
                "scrollbar_bg": "#2e5a8f",
                "scrollbar_trough": "#1e3a5f"
            },
            "Jade": {
                "bg": "#2f4f4f",
                "fg": "#ffffff",
                "selectbg": "#468c8c",
                "button_bg": "#3b6b6b",
                "button_fg": "#ffffff",
                "entry_bg": "#395959",
                "scrollbar_bg": "#3b6b6b",
                "scrollbar_trough": "#2f4f4f"
            },
            "Rose": {
                "bg": "#4a2e3b",
                "fg": "#ffffff",
                "selectbg": "#734d5c",
                "button_bg": "#5c3a49",
                "button_fg": "#ffffff",
                "entry_bg": "#553443",
                "scrollbar_bg": "#5c3a49",
                "scrollbar_trough": "#4a2e3b"
            },
            "Chocolate": {
                "bg": "#3c2f2f",
                "fg": "#ffffff",
                "selectbg": "#5c4a4a",
                "button_bg": "#4f3d3d",
                "button_fg": "#ffffff",
                "entry_bg": "#483838",
                "scrollbar_bg": "#4f3d3d",
                "scrollbar_trough": "#3c2f2f"
            },
            "Bahama": {
                "bg": "#1a3c4d",
                "fg": "#ffffff",
                "selectbg": "#2a5c6d",
                "button_bg": "#244c5d",
                "button_fg": "#ffffff",
                "entry_bg": "#223a47",
                "scrollbar_bg": "#244c5d",
                "scrollbar_trough": "#1a3c4d"
            },
            "Pomegranate": {
                "bg": "#3d1c25",
                "fg": "#ffffff",
                "selectbg": "#5c2e3a",
                "button_bg": "#4a2330",
                "button_fg": "#ffffff",
                "entry_bg": "#451e2b",
                "scrollbar_bg": "#4a2330",
                "scrollbar_trough": "#3d1c25"
            },
            "Titanium": {
                "bg": "#2b2e33",
                "fg": "#d9d9d9",
                "selectbg": "#4a4e55",
                "button_bg": "#3a3e44",
                "button_fg": "#d9d9d9",
                "entry_bg": "#35383d",
                "scrollbar_bg": "#3a3e44",
                "scrollbar_trough": "#2b2e33"
            },
            "Dusk": {
                "bg": "#2e2a3f",
                "fg": "#e6e6e6",
                "selectbg": "#4d4666",
                "button_bg": "#3c3752",
                "button_fg": "#e6e6e6",
                "entry_bg": "#37324a",
                "scrollbar_bg": "#3c3752",
                "scrollbar_trough": "#2e2a3f"
            },
            "Vintage": {
                "bg": "#3a2f26",
                "fg": "#F1DAB6",
                "selectbg": "#5c4a3a",
                "button_bg": "#4a3c33",
                "button_fg": "#f0d9b5",
                "entry_bg": "#45382e",
                "scrollbar_bg": "#4a3c33",
                "scrollbar_trough": "#3a2f26"
            },
            "Forest": {
                "bg": "#1f2f27",
                "fg": "#d9e6d9",
                "selectbg": "#3a4e42",
                "button_bg": "#2a3c33",
                "button_fg": "#d9e6d9",
                "entry_bg": "#263630",
                "scrollbar_bg": "#2a3c33",
                "scrollbar_trough": "#1f2f27"
            },
            "Pear": {
                "bg": "#2f3c2a",
                "fg": "#e6f0d9",
                "selectbg": "#4e5c46",
                "button_bg": "#3c4a36",
                "button_fg": "#e6f0d9",
                "entry_bg": "#374432",
                "scrollbar_bg": "#3c4a36",
                "scrollbar_trough": "#2f3c2a"
            },
            "Blueberry": {
                "bg": "#2a2f4d",
                "fg": "#e6e6ff",
                "selectbg": "#464a73",
                "button_bg": "#363c5f",
                "button_fg": "#e6e6ff",
                "entry_bg": "#323856",
                "scrollbar_bg": "#363c5f",
                "scrollbar_trough": "#2a2f4d"
            },
            "Dream": {
                "bg": "#1e2e3f",
                "fg": "#d9e6ff",
                "selectbg": "#3a4e66",
                "button_bg": "#2a3c52",
                "button_fg": "#d9e6ff",
                "entry_bg": "#26364a",
                "scrollbar_bg": "#2a3c52",
                "scrollbar_trough": "#1e2e3f"
            },
            "Splash": {
                "bg": "#1c3a3a",
                "fg": "#e6ffff",
                "selectbg": "#2e5c5c",
                "button_bg": "#264a4a",
                "button_fg": "#e6ffff",
                "entry_bg": "#233f3f",
                "scrollbar_bg": "#264a4a",
                "scrollbar_trough": "#1c3a3a"
            },
            "Retro": {
                "bg": "#2f2a2f",
                "fg": "#ffb3b3",
                "selectbg": "#4e464e",
                "button_bg": "#3c363c",
                "button_fg": "#ffb3b3",
                "entry_bg": "#373237",
                "scrollbar_bg": "#3c363c",
                "scrollbar_trough": "#2f2a2f"
            },
            "CS04": {
                "bg": "#1a2f3a",
                "fg": "#d9f0ff",
                "selectbg": "#2e4e5c",
                "button_bg": "#233c4a",
                "button_fg": "#d9f0ff",
                "entry_bg": "#213641",
                "scrollbar_bg": "#233c4a",
                "scrollbar_trough": "#1a2f3a"
            },
            "Midnight": {
                "bg": "#0f1e2d",
                "fg": "#e6e6ff",
                "selectbg": "#2a3a4e",
                "button_bg": "#1e2c3c",
                "button_fg": "#e6e6ff",
                "entry_bg": "#182533",
                "scrollbar_bg": "#1e2c3c",
                "scrollbar_trough": "#0f1e2d"
            },
            "Obsidian": {
                "bg": "#1f2526",
                "fg": "#d9d9d9",
                "selectbg": "#3a3f40",
                "button_bg": "#2c3233",
                "button_fg": "#d9d9d9",
                "entry_bg": "#282d2e",
                "scrollbar_bg": "#2c3233",
                "scrollbar_trough": "#1f2526"
            },
            "Mist": {
                "bg": "#536878",
                "fg": "#1C2B40",
                "selectbg": "#779ecb",
                "button_bg": "#5d8aa8",
                "button_fg": "#e6e6fa",
                "entry_bg": "#9FA3B6",
                "scrollbar_bg": "#5d8aa8",
                "scrollbar_trough": "#36454f"
            },
            "Twilight": {
                "bg": "#2a263f",
                "fg": "#f0e6ff",
                "selectbg": "#464266",
                "button_bg": "#363252",
                "button_fg": "#f0e6ff",
                "entry_bg": "#322e4a",
                "scrollbar_bg": "#363252",
                "scrollbar_trough": "#2a263f"
            },
            "Serenity": {
                "bg": "#bcd4e6",
                "fg": "#2d4a3b",
                "selectbg": "#96ded1",
                "button_bg": "#a3c1ad",
                "button_fg": "#2d4a3b",
                "entry_bg": "#e6f5e6",
                "scrollbar_bg": "#a3c1ad",
                "scrollbar_trough": "#b2beb5"
            },
            "Velvet Dawn": {
                "bg": "#915c83",
                "fg": "#FFF8E9",
                "selectbg": "#b784a7",
                "button_bg": "#CAA2DC",
                "button_fg": "#FFF8E9",
                "entry_bg": "#A77C5C",
                "scrollbar_bg": "#6E4266",
                "scrollbar_trough": "#79443b"
            },
            "Citrus Breeze": {
                "bg": "#ffcc33",
                "fg": "#3f2a1d",
                "selectbg": "#f8d568",
                "button_bg": "#ffae42",
                "button_fg": "#3f2a1d",
                "entry_bg": "#fffacd",
                "scrollbar_bg": "#ffae42",
                "scrollbar_trough": "#e9d66b"
            },
            "Emerald": {
                "bg": "#50C878",
                "fg": "#1f2f27",
                "selectbg": "#74c365",
                "button_bg": "#3EB68A",
                "button_fg": "#1f2f27",
                "entry_bg": "#a0d6b4",
                "scrollbar_bg": "#3eb489",
                "scrollbar_trough": "#006b3c"
            },
            "Coral Dream": {
                "bg": "#FF7E4F",
                "fg": "#3c2f2f",
                "selectbg": "#f88379",
                "button_bg": "#ff9966",
                "button_fg": "#3c2f2f",
                "entry_bg": "#ffdab9",
                "scrollbar_bg": "#ff9966",
                "scrollbar_trough": "#e97451"
            },
            "Amethyst": {
                "bg": "#9A67CD",
                "fg": "#f0d9b5",
                "selectbg": "#bf94e4",
                "button_bg": "#B667D2",
                "button_fg": "#f0d9b5",
                "entry_bg": "#6F449A",
                "scrollbar_bg": "#b666d2",
                "scrollbar_trough": "#734f96"
            },
            "Golden": {
                "bg": "#FFD900",
                "fg": "#483c32",
                "selectbg": "#ffcc00",
                "button_bg": "#e4d00a",
                "button_fg": "#483c32",
                "entry_bg": "#fafad2",
                "scrollbar_bg": "#e4d00a",
                "scrollbar_trough": "#b8860b"
            },
            "Lavender": {
                "bg": "#E8E8FB",
                "fg": "#5a4fcf",
                "selectbg": "#c8a2c8",
                "button_bg": "#b19cd9",
                "button_fg": "#5a4fcf",
                "entry_bg": "#fff0f5",
                "scrollbar_bg": "#b19cd9",
                "scrollbar_trough": "#967bb6"
            },
            "Ocean Whisper": {
                "bg": "#32D7CA",
                "fg": "#003153",
                "selectbg": "#73c2fb",
                "button_bg": "#0abab5",
                "button_fg": "#003153",
                "entry_bg": "#b2ffff",
                "scrollbar_bg": "#0abab5",
                "scrollbar_trough": "#006994"
            },
            "Rose Petal": {
                "bg": "#D7207C",
                "fg": "#015500",
                "selectbg": "#f9429e",
                "button_bg": "#e25098",
                "button_fg": "#ffffff",
                "entry_bg": "#ffbcd9",
                "scrollbar_bg": "#e25098",
                "scrollbar_trough": "#b3446c"
            },
            "Mossy Stone": {
                "bg": "#addfad",
                "fg": "#3c2f2f",
                "selectbg": "#93c572",
                "button_bg": "#77dd77",
                "button_fg": "#3c2f2f",
                "entry_bg": "#d0f0c0",
                "scrollbar_bg": "#77dd77",
                "scrollbar_trough": "#507d2a"
            },
            "Flamingo Sunset": {
                "bg": "#fc8eac",
                "fg": "#4a2c00",
                "selectbg": "#ff91a4",
                "button_bg": "#f78fa7",
                "button_fg": "#4a2c00",
                "entry_bg": "#ffd1dc",
                "scrollbar_bg": "#f78fa7",
                "scrollbar_trough": "#e4717a"
            },
            "Indigo Night": {
                "bg": "#4b0082",
                "fg": "#e6e6ff",
                "selectbg": "#6f00ff",
                "button_bg": "#3f00ff",
                "button_fg": "#e6e6ff",
                "entry_bg": "#8f00ff",
                "scrollbar_bg": "#3f00ff",
                "scrollbar_trough": "#32127a"
            },
            "Peachy Glow": {
                "bg": "#ffdab9",
                "fg": "#79443b",
                "selectbg": "#fadfad",
                "button_bg": "#ffbd88",
                "button_fg": "#79443b",
                "entry_bg": "#fffacd",
                "scrollbar_bg": "#ffbd88",
                "scrollbar_trough": "#fad6a5"
            },
            "Jade Serenity": {
                "bg": "#00a86b",
                "fg": "#ffffff",
                "selectbg": "#3eb489",
                "button_bg": "#50c878",
                "button_fg": "#ffffff",
                "entry_bg": "#a0d6b4",
                "scrollbar_bg": "#50c878",
                "scrollbar_trough": "#006d5b"
            },
            "Cherry Blossom": {
                "bg": "#ffb7c5",
                "fg": "#3c2f2f",
                "selectbg": "#ffa6c9",
                "button_bg": "#f6adc6",
                "button_fg": "#3c2f2f",
                "entry_bg": "#fff0f5",
                "scrollbar_bg": "#f6adc6",
                "scrollbar_trough": "#e7accf"
            },
            "Saffron Spice": {
                "bg": "#f4c430",
                "fg": "#4a2c00",
                "selectbg": "#ffcc00",
                "button_bg": "#ffa700",
                "button_fg": "#4a2c00",
                "entry_bg": "#fff44f",
                "scrollbar_bg": "#ffa700",
                "scrollbar_trough": "#e49b0f"
            },
            "Midnight Rose": {
                "bg": "#733037",
                "fg": "#f0e6ff",
                "selectbg": "#b57281",
                "button_bg": "#ab4e52",
                "button_fg": "#f0e6ff",
                "entry_bg": "#c08081",
                "scrollbar_bg": "#ab4e52",
                "scrollbar_trough": "#65000b"
            },
            "Frosty Mint": {
                "bg": "#aaf0d1",
                "fg": "#21421e",
                "selectbg": "#98ff98",
                "button_bg": "#3cd070",
                "button_fg": "#21421e",
                "entry_bg": "#f5fffa",
                "scrollbar_bg": "#3cd070",
                "scrollbar_trough": "#006a4e"
            },
            "Amber Twilight": {
                "bg": "#ffbf00",
                "fg": "#483c32",
                "selectbg": "#ffa812",
                "button_bg": "#f94d00",
                "button_fg": "#483c32",
                "entry_bg": "#ffefd5",
                "scrollbar_bg": "#f94d00",
                "scrollbar_trough": "#cd7f32"
            },
            "Blue Harmony": {
                "bg": "#4169e1",
                "fg": "#d9e6ff",
                "selectbg": "#73a9c2",
                "button_bg": "#0073cf",
                "button_fg": "#003192",
                "entry_bg": "#324FA7",
                "scrollbar_bg": "#0073cf",
                "scrollbar_trough": "#0033aa"
            },
            "Honey Dew": {
                "bg": "#f0fff0",
                "fg": "#3f2a1d",
                "selectbg": "#d0f0c0",
                "button_bg": "#e6f5e6",
                "button_fg": "#3f2a1d",
                "entry_bg": "#f5fffa",
                "scrollbar_bg": "#e6f5e6",
                "scrollbar_trough": "#bdda57"
            },
            "Plum Elegance": {
                "bg": "#dda0dd",
                "fg": "#3c2f2f",
                "selectbg": "#ee82ee",
                "button_bg": "#c154c1",
                "button_fg": "#3c2f2f",
                "entry_bg": "#fbcce7",
                "scrollbar_bg": "#c154c1",
                "scrollbar_trough": "#915f6d"
            },
            "Moonlit Grove": {
                "bg": "#2d3a3c",
                "fg": "#d9e6e6",
                "selectbg": "#3f4f51",
                "button_bg": "#354648",
                "button_fg": "#d9e6e6",
                "entry_bg": "#2e3f41",
                "scrollbar_bg": "#354648",
                "scrollbar_trough": "#2d3a3c"
            },
            "Ashen Whisper": {
                "bg": "#4a4a4a",
                "fg": "#e6e6e6",
                "selectbg": "#666666",
                "button_bg": "#5c5c5c",
                "button_fg": "#e6e6e6",
                "entry_bg": "#4d4d4d",
                "scrollbar_bg": "#5c5c5c",
                "scrollbar_trough": "#4a4a4a"
            },
            "Sepia Scroll": {
                "bg": "#8b6f47",
                "fg": "#f0e6d9",
                "selectbg": "#a78c5e",
                "button_bg": "#9d7d53",
                "button_fg": "#f0e6d9",
                "entry_bg": "#8f734c",
                "scrollbar_bg": "#9d7d53",
                "scrollbar_trough": "#8b6f47"
            },
            "Slate Serenity": {
                "bg": "#4f5d6e",
                "fg": "#e6f0f0",
                "selectbg": "#6a7888",
                "button_bg": "#5c6a7b",
                "button_fg": "#e6f0f0",
                "entry_bg": "#526373",
                "scrollbar_bg": "#5c6a7b",
                "scrollbar_trough": "#4f5d6e"
            },
            "Cedar Haven": {
                "bg": "#3f2f2a",
                "fg": "#f0d9d9",
                "selectbg": "#5c4a45",
                "button_bg": "#4c3a35",
                "button_fg": "#f0d9d9",
                "entry_bg": "#42322d",
                "scrollbar_bg": "#4c3a35",
                "scrollbar_trough": "#3f2f2a"
            },
            "Ivory Mist": {
                "bg": "#f0e6e6",
                "fg": "#3c2f2f",
                "selectbg": "#d9d2d2",
                "button_bg": "#e6e4e4",
                "button_fg": "#3c2f2f",
                "entry_bg": "#fff8f8",
                "scrollbar_bg": "#e6e4e4",
                "scrollbar_trough": "#d9d2d2"
            },
            "Charcoal Echo": {
                "bg": "#2b2b2b",
                "fg": "#e6e6e6",
                "selectbg": "#404040",
                "button_bg": "#363636",
                "button_fg": "#e6e6e6",
                "entry_bg": "#2e2e2e",
                "scrollbar_bg": "#363636",
                "scrollbar_trough": "#2b2b2b"
            },
            "Sage Whisper": {
                "bg": "#8a9a8b",
                "fg": "#3c4a3b",
                "selectbg": "#a3b3a4",
                "button_bg": "#9ca99d",
                "button_fg": "#3c4a3b",
                "entry_bg": "#8f9f90",
                "scrollbar_bg": "#9ca99d",
                "scrollbar_trough": "#8a9a8b"
            },
            "Rustic Oak": {
                "bg": "#5c4a3a",
                "fg": "#f0d9b5",
                "selectbg": "#7a634f",
                "button_bg": "#6d5a46",
                "button_fg": "#f0d9b5",
                "entry_bg": "#5f4d3d",
                "scrollbar_bg": "#6d5a46",
                "scrollbar_trough": "#5c4a3a"
            },
            "Nightshade Veil": {
                "bg": "#2a263f",
                "fg": "#f0e6ff",
                "selectbg": "#464266",
                "button_bg": "#363252",
                "button_fg": "#f0e6ff",
                "entry_bg": "#322e4a",
                "scrollbar_bg": "#363252",
                "scrollbar_trough": "#2a263f"
            },
            "Stonewashed Calm": {
                "bg": "#b2beb5",
                "fg": "#3c4a3b",
                "selectbg": "#c9d9cc",
                "button_bg": "#c0d0c3",
                "button_fg": "#3c4a3b",
                "entry_bg": "#b5c1b8",
                "scrollbar_bg": "#c0d0c3",
                "scrollbar_trough": "#b2beb5"
            },
            "Ebony Whisper": {
                "bg": "#1f2526",
                "fg": "#d9d9d9",
                "selectbg": "#3a3f40",
                "button_bg": "#2c3233",
                "button_fg": "#d9d9d9",
                "entry_bg": "#282d2e",
                "scrollbar_bg": "#2c3233",
                "scrollbar_trough": "#1f2526"
            },
            "Willow Shade": {
                "bg": "#4f7942",
                "fg": "#e6f0d9",
                "selectbg": "#6a9f5c",
                "button_bg": "#5c8a4f",
                "button_fg": "#e6f0d9",
                "entry_bg": "#527f45",
                "scrollbar_bg": "#5c8a4f",
                "scrollbar_trough": "#4f7942"
            },
            "Pewter Glow": {
                "bg": "#6e7f80",
                "fg": "#d9e6e6",
                "selectbg": "#8a9a9b",
                "button_bg": "#7c8d8e",
                "button_fg": "#d9e6e6",
                "entry_bg": "#718486",
                "scrollbar_bg": "#7c8d8e",
                "scrollbar_trough": "#6e7f80"
            },
            "Copper Dusk": {
                "bg": "#8b4513",
                "fg": "#f0e6d9",
                "selectbg": "#a85a1c",
                "button_bg": "#9c5020",
                "button_fg": "#f0e6d9",
                "entry_bg": "#8e4816",
                "scrollbar_bg": "#9c5020",
                "scrollbar_trough": "#8b4513"
            },
            "Frosted Pine": {
                "bg": "#1c352d",
                "fg": "#d9e6d9",
                "selectbg": "#2f4f42",
                "button_bg": "#26433a",
                "button_fg": "#d9e6d9",
                "entry_bg": "#1f382f",
                "scrollbar_bg": "#26433a",
                "scrollbar_trough": "#1c352d"
            },
            "Muted Lavender": {
                "bg": "#8A4A6B",
                "fg": "#f0e6ff",
                "selectbg": "#a65c85",
                "button_bg": "#9c5280",
                "button_fg": "#f0e6ff",
                "entry_bg": "#8d4d6e",
                "scrollbar_bg": "#9c5280",
                "scrollbar_trough": "#8a496b"
            },
            "Birch Bark": {
                "bg": "#e3dac9",
                "fg": "#3c2f2f",
                "selectbg": "#d9d2c4",
                "button_bg": "#e0d7ce",
                "button_fg": "#3c2f2f",
                "entry_bg": "#e6e4df",
                "scrollbar_bg": "#e0d7ce",
                "scrollbar_trough": "#d9d2c4"
            },
            "Iron Veil": {
                "bg": "#414a4c",
                "fg": "#e6e6e6",
                "selectbg": "#5c6a6c",
                "button_bg": "#4d5a5c",
                "button_fg": "#e6e6e6",
                "entry_bg": "#445054",
                "scrollbar_bg": "#4d5a5c",
                "scrollbar_trough": "#414a4c"
            },
            "Granite Mist": {
                "bg": "#6c6c6c",
                "fg": "#e6e6e6",
                "selectbg": "#8a8a8a",
                "button_bg": "#7c7c7c",
                "button_fg": "#e6e6e6",
                "entry_bg": "#6f6f6f",
                "scrollbar_bg": "#7c7c7c",
                "scrollbar_trough": "#6c6c6c"
            },
            "Hazelwood Calm": {
                "bg": "#8b6f47",
                "fg": "#f0e6d9",
                "selectbg": "#a78c5e",
                "button_bg": "#9d7d53",
                "button_fg": "#f0e6d9",
                "entry_bg": "#8f734c",
                "scrollbar_bg": "#9d7d53",
                "scrollbar_trough": "#8b6f47"
            },
            "Shadowed Slate": {
                "bg": "#3c3f40",
                "fg": "#d9d9d9",
                "selectbg": "#5c5f60",
                "button_bg": "#4d5051",
                "button_fg": "#d9d9d9",
                "entry_bg": "#3f4243",
                "scrollbar_bg": "#4d5051",
                "scrollbar_trough": "#3c3f40"
            },
            "Olive Retreat": {
                "bg": "#556b2f",
                "fg": "#e6f0d9",
                "selectbg": "#6a8f3c",
                "button_bg": "#5c7a34",
                "button_fg": "#e6f0d9",
                "entry_bg": "#596e32",
                "scrollbar_bg": "#5c7a34",
                "scrollbar_trough": "#556b2f"
            },
            "Silk Whisper": {
                "bg": "#f0e6e6",
                "fg": "#4a2e3b",
                "selectbg": "#e0d6d6",
                "button_bg": "#e6e4e4",
                "button_fg": "#4a2e3b",
                "entry_bg": "#fff8f8",
                "scrollbar_bg": "#e6e4e4",
                "scrollbar_trough": "#e0d6d6"
            },
            "Cobalt Quiet": {
                "bg": "#1e3a5f",
                "fg": "#e6f0ff",
                "selectbg": "#2e5a8f",
                "button_bg": "#2a4a7a",
                "button_fg": "#e6f0ff",
                "entry_bg": "#223f6a",
                "scrollbar_bg": "#2a4a7a",
                "scrollbar_trough": "#1e3a5f"
            },
            "Amber Hush": {
                "bg": "#d68a59",
                "fg": "#3c2f2f",
                "selectbg": "#e99b6a",
                "button_bg": "#e08d3c",
                "button_fg": "#3c2f2f",
                "entry_bg": "#e6955b",
                "scrollbar_bg": "#e08d3c",
                "scrollbar_trough": "#d68a59"
            },
            "Velvet Shadow": {
                "bg": "#4a2e3b",
                "fg": "#f0e6ff",
                "selectbg": "#734d5c",
                "button_bg": "#5c3a49",
                "button_fg": "#f0e6ff",
                "entry_bg": "#553443",
                "scrollbar_bg": "#5c3a49",
                "scrollbar_trough": "#4a2e3b"
            },
            "Lichen Glow": {
                "bg": "#78866b",
                "fg": "#3c4a3b",
                "selectbg": "#9aa08f",
                "button_bg": "#8c9a8a",
                "button_fg": "#3c4a3b",
                "entry_bg": "#7b8f7a",
                "scrollbar_bg": "#8c9a8a",
                "scrollbar_trough": "#78866b"
            },
            "Marble Veil": {
                "bg": "#d9d9d9",
                "fg": "#3c2f2f",
                "selectbg": "#e6e6e6",
                "button_bg": "#e0e0e0",
                "button_fg": "#3c2f2f",
                "entry_bg": "#ffffff",
                "scrollbar_bg": "#e0e0e0",
                "scrollbar_trough": "#d9d9d9"
            },
            "Twilight Ember": {
                "bg": "#2a263f",
                "fg": "#f0e6ff",
                "selectbg": "#464266",
                "button_bg": "#363252",
                "button_fg": "#f0e6ff",
                "entry_bg": "#322e4a",
                "scrollbar_bg": "#363252",
                "scrollbar_trough": "#2a263f"
            },
            "Sandstone Whisper": {
                "bg": "#c2b280",
                "fg": "#3c2f2f",
                "selectbg": "#d9d2c4",
                "button_bg": "#d0ceac",
                "button_fg": "#3c2f2f",
                "entry_bg": "#e6e4c6",
                "scrollbar_bg": "#d0ceac",
                "scrollbar_trough": "#c2b280"
            },
            "Deep Forest": {
                "bg": "#1f2f27",
                "fg": "#e6f0d9",
                "selectbg": "#3a4e42",
                "button_bg": "#2a3c33",
                "button_fg": "#e6f0d9",
                "entry_bg": "#263630",
                "scrollbar_bg": "#2a3c33",
                "scrollbar_trough": "#1f2f27"
            },
            "Pearl Mist": {
                "bg": "#f0f8ff",
                "fg": "#3c2f2f",
                "selectbg": "#e0e8f0",
                "button_bg": "#e6e4e4",
                "button_fg": "#3c2f2f",
                "entry_bg": "#ffffff",
                "scrollbar_bg": "#e6e4e4",
                "scrollbar_trough": "#e0e8f0"
            },
            "Onyx Night": {
                "bg": "#0f0f0f",
                "fg": "#e6e6e6",
                "selectbg": "#2b2b2b",
                "button_bg": "#1a1a1a",
                "button_fg": "#e6e6e6",
                "entry_bg": "#131313",
                "scrollbar_bg": "#1a1a1a",
                "scrollbar_trough": "#0f0f0f"
            },
            "Clay Earth": {
                "bg": "#8b6f47",
                "fg": "#f0e6d9",
                "selectbg": "#a78c5e",
                "button_bg": "#9d7d53",
                "button_fg": "#f0e6d9",
                "entry_bg": "#8f734c",
                "scrollbar_bg": "#9d7d53",
                "scrollbar_trough": "#8b6f47"
            },
            "Mystic Blue": {
                "bg": "#2a4d69",
                "fg": "#e6f0ff",
                "selectbg": "#3f6a8c",
                "button_bg": "#2e4f6b",
                "button_fg": "#e6f0ff",
                "entry_bg": "#2b4a66",
                "scrollbar_bg": "#2e4f6b",
                "scrollbar_trough": "#2a4d69"
            },
            "Heather Hush": {
                "bg": "#8a496b",
                "fg": "#f0e6ff",
                "selectbg": "#a65c85",
                "button_bg": "#9c5280",
                "button_fg": "#f0e6ff",
                "entry_bg": "#8d4d6e",
                "scrollbar_bg": "#9c5280",
                "scrollbar_trough": "#8a496b"
            },
            "Bronze Age": {
                "bg": "#cd7f32",
                "fg": "#f0e6d9",
                "selectbg": "#e99b6a",
                "button_bg": "#d68a59",
                "button_fg": "#f0e6d9",
                "entry_bg": "#d08f3c",
                "scrollbar_bg": "#d68a59",
                "scrollbar_trough": "#cd7f32"
            },
            "Willow Breeze": {
                "bg": "#a9ba9d",
                "fg": "#3c4a3b",
                "selectbg": "#c9d9cc",
                "button_bg": "#c0d0c3",
                "button_fg": "#3c4a3b",
                "entry_bg": "#b5c1b8",
                "scrollbar_bg": "#c0d0c3",
                "scrollbar_trough": "#a9ba9d"
            },
            "Shadow Pine": {
                "bg": "#2F4F4F",
                "fg": "#e6f0ff",
                "selectbg": "#468c8c",
                "button_bg": "#3b6b6b",
                "button_fg": "#e6f0ff",
                "entry_bg": "#395959",
                "scrollbar_bg": "#3b6b6b",
                "scrollbar_trough": "#2f4f4f"
            },
            "Ivory Scroll": {
                "bg": "#f0ead6",
                "fg": "#3c2f2f",
                "selectbg": "#e0d8d0",
                "button_bg": "#e6e4e4",
                "button_fg": "#3c2f2f",
                "entry_bg": "#fff8f8",
                "scrollbar_bg": "#e6e4e4",
                "scrollbar_trough": "#e0d8d0"
            },
            "Midnight Sapphire": {
                "bg": "#0f1e2d",
                "fg": "#e6f0ff",
                "selectbg": "#2a3a4e",
                "button_bg": "#1e2c3c",
                "button_fg": "#e6f0ff",
                "entry_bg": "#182533",
                "scrollbar_bg": "#1e2c3c",
                "scrollbar_trough": "#0f1e2d"
            },
            "Terra Cotta": {
                "bg": "#e2725b",
                "fg": "#3c2f2f",
                "selectbg": "#f3836c",
                "button_bg": "#e67d64",
                "button_fg": "#3c2f2f",
                "entry_bg": "#e5775f",
                "scrollbar_bg": "#e67d64",
                "scrollbar_trough": "#e2725b"
            },
            "Frosted": {
                "bg": "#D5D5D5",
                "fg": "#02074D",
                "selectbg": "#DCE7E4",
                "button_bg": "#e0e0e0",
                "button_fg": "#331585",
                "entry_bg": "#ffffff",
                "scrollbar_bg": "#B3CDCA",
                "scrollbar_trough": "#CEDBE7"
            },
            "Cedar Twilight": {
                "bg": "#3c2f2f",
                "fg": "#f0e6ff",
                "selectbg": "#5c4a4a",
                "button_bg": "#4f3d3d",
                "button_fg": "#f0e6ff",
                "entry_bg": "#483838",
                "scrollbar_bg": "#4f3d3d",
                "scrollbar_trough": "#3c2f2f"
            },
            "Lichen Whisper": {
                "bg": "#78866b",
                "fg": "#e6f0d9",
                "selectbg": "#9aa08f",
                "button_bg": "#8c9a8a",
                "button_fg": "#e6f0d9",
                "entry_bg": "#7b8f7a",
                "scrollbar_bg": "#8c9a8a",
                "scrollbar_trough": "#78866b"
            },
            "Stormy Sea": {
                "bg": "#2e4d69",
                "fg": "#e6f0ff",
                "selectbg": "#3f6a8c",
                "button_bg": "#2e4f6b",
                "button_fg": "#e6f0ff",
                "entry_bg": "#2b4a66",
                "scrollbar_bg": "#2e4f6b",
                "scrollbar_trough": "#2e4d69"
            },
            "Sandstone Echo": {
                "bg": "#c2b280",
                "fg": "#3c2f2f",
                "selectbg": "#d9d2c4",
                "button_bg": "#d0ceac",
                "button_fg": "#3c2f2f",
                "entry_bg": "#e6e4c6",
                "scrollbar_bg": "#d0ceac",
                "scrollbar_trough": "#c2b280"
            },
            "Deep Moss": {
                "bg": "#1f2f27",
                "fg": "#e6f0d9",
                "selectbg": "#3a4e42",
                "button_bg": "#2a3c33",
                "button_fg": "#e6f0d9",
                "entry_bg": "#263630",
                "scrollbar_bg": "#2a3c33",
                "scrollbar_trough": "#1f2f27"
            },
            "Onyx Shadow": {
                "bg": "#0f0f0f",
                "fg": "#e6e6e6",
                "selectbg": "#2b2b2b",
                "button_bg": "#1a1a1a",
                "button_fg": "#e6e6e6",
                "entry_bg": "#131313",
                "scrollbar_bg": "#1a1a1a",
                "scrollbar_trough": "#0f0f0f"
            },
            "Pearl Glow": {
                "bg": "#f0f8ff",
                "fg": "#3c2f2f",
                "selectbg": "#e0e8f0",
                "button_bg": "#e6e4e4",
                "button_fg": "#3c2f2f",
                "entry_bg": "#ffffff",
                "scrollbar_bg": "#e6e4e4",
                "scrollbar_trough": "#e0e8f0"
            }
        }

    def get_colors(self) -> dict:
        if self.current_theme not in self.themes:
            return {
                "bg": "#333333",
                "fg": "#ffffff",
                "selectbg": "#717171",
                "button_bg": "#717171",
                "button_fg": "#ffffff",
                "entry_bg": "#262626",
                "scrollbar_bg": "#717171",
                "scrollbar_trough": "#3B3B3B"
            }
        """Returns the color dictionary for the current theme."""
        return self.themes[self.current_theme]

    def set_theme(self, theme_name: str):
        """Sets the current theme by name."""
        self.current_theme = theme_name

    def save_themes(self, themes_dict: dict):
        """Saves the themes dictionary to the JSON file."""
        self.themes = themes_dict
        with open(THEMES_FILE, 'w') as f:
            json.dump(self.themes, f, indent=4)
        logging.info(f"Saved themes to {THEMES_FILE}")

class DataLoader:
    """Handles loading and parsing of XML data."""
    def __init__(self):
        self.translations = []
        self.surahs = {}
        self.verses = {}
        self.surah_names = {}
        self.ayah_counts = {}
        self.notes_file = os.path.join(base_path, "notes.xml")
        
    def parse_xml(self, xml_path: Path):
        """Parses the XML file and populates the data structures."""
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
                    if source not in self.translations:
                        self.translations.append(source)
                finally:
                    elem.clear()
                    while elem.getprevious() is not None:
                        del elem.getparent()[0]
            self.ayah_counts = {surah: max(int(ayah) for ayah in self.surahs[surah]) for surah in self.surahs}
        except etree.LxmlError as e:
            raise ValueError(f"Failed to parse XML: {str(e)}")

    def load_notes(self):
            """Load user notes from notes.xml if it exists."""
            if os.path.exists(self.notes_file):
                try:
                    tree = ET.parse(self.notes_file)
                    root = tree.getroot()
                    for surah in root.findall(".//Surah"):
                        surah_num = surah.get("SurahNumber")
                        if surah_num not in self.surahs:
                            self.surahs[surah_num] = set()
                        if surah_num not in self.verses:
                            self.verses[surah_num] = {}
                        for ayah in surah.findall(".//Ayah"):
                            ayah_num = ayah.get("AyahNumber")
                            rendition = ayah.find("./Rendition[@Source='User Notes']")
                            if rendition is not None:
                                if ayah_num not in self.surahs[surah_num]:
                                    self.surahs[surah_num].add(ayah_num)
                                if ayah_num not in self.verses[surah_num]:
                                    self.verses[surah_num][ayah_num] = {}
                                self.verses[surah_num][ayah_num]["User Notes"] = rendition.text.strip()
                    if "User Notes" not in self.translations:
                        self.translations.insert(0, "User Notes")  # Top of list
                except Exception as e:
                    logging.error(f"Failed to load notes.xml: {e}")

    def load_data(self):
        """Loads XML data and notes in a separate thread."""
        xml_path = self.locate_xml_file()
        self.parse_xml(xml_path)
        self.load_notes()  # Add this line to load notes after main XML

class PreferencesManager:
    """Manages loading and saving of user preferences."""
    def __init__(self):
        self.filename = PREFERENCES_FILE
        self.data = {}

    def load_preferences(self, theme_manager):
        """Loads preferences from a JSON file or sets defaults if not found or invalid."""
        default_prefs = {
            "selected_translations": ["Arabic", "Muhammad Asad"],
            "font": DEFAULT_FONT,
            "font_size": DEFAULT_FONT_SIZE,
            "last_reference": "1-114",
            "theme": "Default",
            "last_keyword": "",
            "broad_search": False,
            "broad_results": False
        }

        if not os.path.exists(self.filename):
            self.data = default_prefs
            logging.info("No preferences.json found, using default preferences")
        else:
            try:
                with open(self.filename, 'r') as f:
                    self.data = json.load(f)
                # Validate theme exists in available themes
                available_themes = list(theme_manager.themes.keys())  # From ThemeManager
                if self.data.get("theme") not in available_themes:
                    self.data["theme"] = default_prefs["theme"]  # Use default theme
                    theme_manager.set_theme(default_prefs["theme"])
                    logging.warning(f"Theme '{self.data.get('theme')}' not found, using '{default_prefs['theme']}'")
                # Validate font (basic check, refine if needed)
                if self.data.get("font") not in tkfont.families():
                    self.data["font"] = default_prefs["font"]  # Use default font
                    logging.warning(f"Font '{self.data.get('font')}' not available, using '{default_prefs['font']}'")
                logging.debug("Loaded and validated preferences from preferences.json")
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
                self.data = default_prefs
                logging.error(f"Error loading preferences.json ({str(e)}), reverting to defaults")

    def save_preferences(self):
        """Saves the current preferences to the JSON file."""
        with open(self.filename, 'w') as f:
            json.dump(self.data, f)
        logging.info(f"Saved preferences to {self.filename}")

class QuranSearchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Quran Verse Explorer")
        self.theme = Theme()
        
        desired_width = DEFAULT_WIDTH
        desired_height = DEFAULT_HEIGHT
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        usable_height = screen_height - 100
        if desired_width > screen_width or desired_height > usable_height:
            self.root.state('zoomed')
        else:
            self.root.geometry(f"{desired_width}x{desired_height}")
            self.center_window()
        self.root.minsize(800, 600)

        # Set custom window icon
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "quran.png")
        else:
            icon_path = os.path.join(base_path, "quran.png")
        self.root.iconphoto(True, tk.PhotoImage(file=icon_path))

        self.data_loader = DataLoader()
        self.prefs = PreferencesManager()
        self.prefs.load_preferences(self.theme)

        # Instance variables for GUI controls
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add('write', self.filter_translations)
        self.last_reference = tk.StringVar(value=self.prefs.data.get('last_reference', '1-114'))
        self.keyword_var = tk.StringVar(value=self.prefs.data.get('last_keyword', ''))
        self.current_font = tk.StringVar(value=self.prefs.data.get('font', DEFAULT_FONT))
        self.current_font_size = tk.StringVar(value=self.prefs.data.get('font_size', DEFAULT_FONT_SIZE))
        self.font_sizes = [str(size) for size in range(4, 37)]
        self.available_fonts = sorted(list(tkfont.families()))
        self.theme_var = tk.StringVar(value=self.prefs.data["theme"])
        self.broad_search_var = tk.BooleanVar(value=self.prefs.data.get('broad_search', False))
        self.broad_results_var = tk.BooleanVar(value=self.prefs.data.get('broad_results', False))
        self.notes_var = tk.BooleanVar(value=self.prefs.data.get('notes', False))
        self.notes = {}  # { "surah.ayah": "note text" }
        self.last_ref = None  # Track previous single-verse reference for saving
        self.search_results = None
        self.loading_label = tk.Label(self.root, text="Loading data, please wait...")
        self.loading_label.pack(expand=True)

        threading.Thread(target=self.load_data, daemon=True).start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        """Centers the application window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def apply_theme(self, event=None):
        theme_name = self.theme_var.get()
        self.theme.set_theme(theme_name)
        colors = self.theme.get_colors()

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

        for widget in self.top_frame.winfo_children() + self.font_frame.winfo_children() + self.filter_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.configure(bg=colors['button_bg'], fg=colors['button_fg'])
            elif isinstance(widget, tk.Label):
                widget.configure(bg=colors['bg'], fg=colors['fg'])

        self.notes_checkbox.configure(bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.result_text.configure(bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.result_scrollbar.configure(style="Vertical.TScrollbar")
        self.translations_scrollbar.configure(style="Vertical.TScrollbar")

        # Update notes pane widgets if they exist
        if hasattr(self, 'result_pane'):
            self.result_pane.configure(bg=colors['bg'])
        if hasattr(self, 'notes_frame'):
            self.notes_frame.configure(bg=colors['bg'])
        if hasattr(self, 'notes_text'):
            self.notes_text.configure(bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        if hasattr(self, 'notes_scrollbar'):
            self.notes_scrollbar.configure(style="Vertical.TScrollbar")

        self.canvas.configure(scrollregion=self.canvas.bbox("all") or (0, 0, 300, 400))
    
    def create_gui(self):
        colors = self.theme.get_colors()
        self.root.configure(bg=colors['bg'])

        self.main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=colors['bg'])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.left_frame = tk.Frame(self.main_container, bg=colors['bg'], relief=tk.RAISED, bd=2)
        self.main_container.add(self.left_frame, width=DEFAULT_SASH_POSITION)  # 300
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.filter_frame = tk.Frame(self.left_frame, bg=colors['bg'])
        self.filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.filter_label = tk.Label(self.filter_frame, text="Filter:", bg=colors['bg'], fg=colors['fg'])
        self.filter_label.pack(side=tk.LEFT, padx=5)
        self.filter_entry = tk.Entry(self.filter_frame, textvariable=self.filter_var,
                                    bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.canvas = tk.Canvas(self.left_frame, bg=colors['bg'], highlightthickness=0)
        self.translations_scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical",
                                                    command=self.canvas.yview,
                                                    style="Vertical.TScrollbar")
        self.scrollable_frame = tk.Frame(self.canvas, bg=colors['bg'], padx=3, pady=3)
        self.canvas.configure(yscrollcommand=self.translations_scrollbar.set)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.translations_scrollbar.grid(row=1, column=1, sticky="ns")

        for widget in (self.canvas, self.scrollable_frame):
            widget.bind("<MouseWheel>", self.on_mousewheel)
            widget.bind("<Button-4>", self.on_mousewheel)
            widget.bind("<Button-5>", self.on_mousewheel)

        self.translation_vars = {}
        self.translation_checkbuttons = {}
        for i, trans in enumerate(self.data_loader.translations):
            var = tk.BooleanVar(value=trans in self.prefs.data.get('selected_translations', []))
            cb = tk.Checkbutton(self.scrollable_frame, text=trans, variable=var,
                               bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'],
                               command=self.show_verses)
            cb.grid(row=i, column=0, sticky="w", padx=2, pady=0)
            cb.bind("<MouseWheel>", self.on_mousewheel)
            cb.bind("<Button-4>", self.on_mousewheel)
            cb.bind("<Button-5>", self.on_mousewheel)
            self.translation_vars[trans] = var
            self.translation_checkbuttons[trans] = cb

        self.right_frame = tk.Frame(self.main_container, bg=colors['bg'])
        self.main_container.add(self.right_frame)
        self.right_frame.grid_rowconfigure(0, weight=0)
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.search_frame = tk.Frame(self.right_frame, bg=colors['bg'], relief=tk.RAISED, bd=2)
        self.search_frame.grid(row=0, column=0, sticky="new", padx=5, pady=5)

        self.top_frame = tk.Frame(self.search_frame, bg=colors['bg'])
        self.top_frame.pack(fill=tk.X)
        tk.Label(self.top_frame, text="Surah.Verse-Range:\n(e.g., 36, 1-114, 2.255-27.30)",
                bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)
        tk.Button(self.top_frame, text="<", command=self.go_previous, width=2,
                 bg=colors['button_bg'], fg=colors['button_fg']).pack(side=tk.LEFT, padx=2)
        self.ref_entry = tk.Entry(self.top_frame, textvariable=self.last_reference,
                                 bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.ref_entry.pack(side=tk.LEFT, padx=5)
        self.ref_entry.bind("<Return>", self.show_verses)
        tk.Button(self.top_frame, text=">", command=self.go_next, width=2,
                 bg=colors['button_bg'], fg=colors['button_fg']).pack(side=tk.LEFT, padx=2)
        tk.Button(self.top_frame, text="Show Verses", command=self.show_verses,
                 bg=colors['button_bg'], fg=colors['button_fg']).pack(side=tk.LEFT, padx=5)
        tk.Button(self.top_frame, text="Copy", command=self.copy_to_clipboard,
                 bg=colors['button_bg'], fg=colors['button_fg']).pack(side=tk.LEFT, padx=5)
        tk.Label(self.top_frame, text="Search keywords:", bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)
        self.keyword_entry = tk.Entry(self.top_frame, textvariable=self.keyword_var,
                                     bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'])
        self.keyword_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.keyword_entry.bind("<Return>", self.show_verses)
        tooltip_text = "Search Tips:\n\n" \
                       "Pressing 'Enter' is equivalent to clicking 'Show Verses' \n" \
                       "All searches are CasE inSEnsiTIVe \n\n" \
                       "The order of terms doesn't matter: (crescent moons = moons crescent) \n" \
                       " .. unless using \"quotes\" to find an exact phrase (e.g., \"upon his sons\")\n" \
                       "Use of \"quotes\" will find all fragments (\"ent m\" finds sENT Messengers & crescENT Moons)\n\n" \
                       "* = multicharacter wildcard (' *after' will find 'HEREafter' )\n" \
                       " .. wildcard is not required on term endings ('test' will find 'testED')\n\n" \
                       "? = single wildcard ('m?ha' finds MUhammad & MOhamed) \n" \
                       "wildcard combinations (?brah*m finds AbrahAm & IbrahEEm) \n\n" \
                       "Disable 'Broad Search' to only search the selected translation(s) \n" \
                       " .. very fast search speed \n" \
                       "Enable 'Broad Search' to search all translations, but only display your selected translation(s) \n" \
                       " .. useful because Arabic words are translated into various synonymous English words \n" \
                       "Enable 'Broad Results' to also include any translation that contains your search term \n" \
                       " .. ony if you care to see by whom is was used \n\n" \
                       "Training Example: \n" \
                       " 1) Select translator 'Abdel Haleem' only \n" \
                       " 2) Set surah.verse-range to '1-114' (The entire Quran) \n" \
                       " 3) Disable 'Broad Search' \n" \
                       " 4) Search for the keyword:  hive \n" \
                       " 5) You get: 'No verses match the search criteria.' \n" \
                       " 6) Enable 'Broad Search' but also Disable 'Broad Results'\n" \
                       " 7) Now it 'Found 1 verse', and only in the 1 selected translation (Abdel Haleem)\n" \
                       " 8) Notice that 'hive' does not exist in Abdel Haleem's translation; he translated as 'houses'\n" \
                       " 9) Now enable 'Broad Reslts'\n" \
                       " 10) 27 additional translations are shown; all those containing the word 'hive'" 
        self.keyword_tooltip = ToolTip(self.keyword_entry, tooltip_text)

        self.broad_search_cb = tk.Checkbutton(self.top_frame, text="Broad Search",
                                             variable=self.broad_search_var, command=self.show_verses,
                                             bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.broad_search_cb.pack(side=tk.LEFT, padx=5)
        self.broad_results_cb = tk.Checkbutton(self.top_frame, text="Broad Results",
                                              variable=self.broad_results_var, state="disabled",
                                              bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
        self.broad_results_cb.pack(side=tk.LEFT, padx=5)
        self.broad_search_var.trace_add('write', self.toggle_broad_results)
        self.toggle_broad_results()  # Sync state

        self.font_frame = tk.Frame(self.search_frame, bg=colors['bg'])
        self.font_frame.pack(fill=tk.X, pady=2)
        tk.Label(self.font_frame, text="Font:", bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)
        self.font_combo = ttk.Combobox(self.font_frame, textvariable=self.current_font,
                                      values=self.available_fonts, state="readonly",
                                      style="MyCombo.TCombobox")
        self.font_combo.pack(side=tk.LEFT, padx=5)
        self.font_combo.bind("<<ComboboxSelected>>", self.update_font)
        self.font_combo.bind("<Leave>", lambda e: self.font_combo.selection_clear())

        tk.Label(self.font_frame, text="Size:", bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)
        self.size_combo = ttk.Combobox(self.font_frame, textvariable=self.current_font_size,
                                      values=self.font_sizes, state="readonly",
                                      style="MyCombo.TCombobox")
        self.size_combo.pack(side=tk.LEFT, padx=5)
        self.size_combo.bind("<<ComboboxSelected>>", self.update_font)
        self.size_combo.bind("<Leave>", lambda e: self.size_combo.selection_clear())

        tk.Label(self.font_frame, text="Theme:", bg=colors['bg'], fg=colors['fg']).pack(side=tk.LEFT, padx=5)
        self.theme_combo = ttk.Combobox(self.font_frame, textvariable=self.theme_var,
                                       values=list(self.theme.themes.keys()), state="readonly",
                                       style="MyCombo.TCombobox")
        self.theme_combo.pack(side=tk.LEFT, padx=5)
        self.theme_combo.bind("<<ComboboxSelected>>", self.apply_theme)
        self.theme_combo.bind("<Leave>", lambda e: self.theme_combo.selection_clear())

        tk.Button(self.font_frame, text="Customize", command=self.open_theme_editor,
                 bg=colors['button_bg'], fg=colors['button_fg']).pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(self.font_frame, textvariable=self.status_var,
                                    bg=colors['bg'], fg=colors['fg'])
        self.status_label.pack(side=tk.LEFT, padx=15)

        self.notes_checkbox = tk.Checkbutton(self.font_frame, text="Notes", variable=self.notes_var,
                                            bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'],
                                            command=self.toggle_notes)
        self.notes_checkbox.pack(side=tk.RIGHT, padx=5)

        self.result_frame = tk.Frame(self.right_frame, bg=colors['bg'], relief=tk.FLAT, bd=0)
        self.result_frame.grid(row=1, column=0, sticky="nsew", padx=3, pady=2)
        self.result_frame.grid_rowconfigure(0, weight=1)
        self.result_frame.grid_columnconfigure(0, weight=1)

        self.result_text = tk.Text(self.result_frame, wrap=tk.WORD,
                                  font=(self.current_font.get(), int(self.current_font_size.get())),
                                  bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'],
                                  padx=14, pady=9)
        self.result_scrollbar = ttk.Scrollbar(self.result_frame, orient="vertical",
                                             command=self.result_text.yview,
                                             style="Vertical.TScrollbar")
        self.result_text.configure(yscrollcommand=self.result_scrollbar.set)
        self.result_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.result_scrollbar.grid(row=0, column=1, sticky="ns")

        self.root.bind("<Prior>", lambda event: self.result_text.yview_scroll(-1, "pages"))
        self.root.bind("<Next>", lambda event: self.result_text.yview_scroll(1, "pages"))

        self.create_context_menu()
        self.main_container.sash_place(0, DEFAULT_SASH_POSITION, 0)
        self.apply_theme()
        self.loading_label.destroy()

    def open_theme_editor(self):
        """Opens the theme editor window for customizing themes."""
        editor_window = tk.Toplevel(self.root)
        editor_window.title("Theme Color Customizer")
        editor_window.geometry("1280x1000")

        # Theme editor variables
        themes_dict = self.theme.themes.copy()
        theme_order = list(themes_dict.keys())
        selected_themes = {theme: tk.BooleanVar(editor_window, value=True) for theme in theme_order}
        color_types = ['bg', 'fg', 'selectbg', 'button_bg', 'button_fg', 'entry_bg', 'scrollbar_bg', 'scrollbar_trough']

        def get_luminance(hex_color):
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (0.299 * r + 0.587 * g + 0.114 * b) / 255

        def open_color_chooser(current_color, button, theme, color_type):
            print(f"Opening color picker for {theme}.{color_type}")
            from tkcolorpicker import askcolor
            def check_and_center():
                for widget in editor_window.winfo_children():
                    try:
                        toplevel = widget.winfo_toplevel()
                        if "Choose color" in toplevel.title() and toplevel != editor_window:
                            toplevel.update_idletasks()
                            root_x = editor_window.winfo_x()
                            root_y = editor_window.winfo_y()
                            root_width = editor_window.winfo_width()
                            root_height = editor_window.winfo_height()
                            dialog_width = toplevel.winfo_width()
                            dialog_height = toplevel.winfo_height()
                            x = root_x + (root_width - dialog_width) // 2
                            y = root_y + (root_height - dialog_height) // 2
                            toplevel.geometry(f"+{x}+{y}")
                            print(f"Centered at: {x},{y} (dialog size: {dialog_width}x{dialog_height})")
                            return True
                    except AttributeError:
                        continue
                return False

            def poll_for_dialog():
                if not check_and_center():
                    editor_window.after(10, poll_for_dialog)

            editor_window.after(0, poll_for_dialog)
            new_color = askcolor(color=current_color, title=f"Choose color for {theme} - {color_type}", parent=editor_window)
            
            if new_color[1]:
                hex_color = new_color[1]
                button.config(bg=hex_color, text=hex_color)
                themes_dict[theme][color_type] = hex_color
                luminance = get_luminance(hex_color)
                button.config(fg="#000000" if luminance > 0.5 else "#ffffff")
                print(f"Selected color: {hex_color}")
                update_preview(theme)

        def rename_theme(old_name, new_name_entry):
            new_name = new_name_entry.get().strip()
            if new_name and new_name != old_name and new_name not in themes_dict:
                themes_dict[new_name] = themes_dict.pop(old_name)
                index = theme_order.index(old_name)
                theme_order[index] = new_name
                selected_themes[new_name] = selected_themes.pop(old_name)
                if old_name == self.theme_var.get():
                    self.theme_var.set(new_name)
                    self.save_preferences()
                refresh_grid()

        def move_theme(theme, direction):
            index = theme_order.index(theme)
            new_index = index + direction
            if 0 <= new_index < len(theme_order):
                theme_order[index], theme_order[new_index] = theme_order[new_index], theme_order[index]
                refresh_grid()

        def toggle_selection(theme):
            refresh_grid()

        def refresh_grid():
            for widget in inner_frame.winfo_children():
                widget.destroy()

            tk.Label(inner_frame, text="Select", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
            tk.Label(inner_frame, text="Theme", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=5)
            tk.Label(inner_frame, text="", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=5)
            for i, color_type in enumerate(color_types, start=0):
                tk.Label(inner_frame, text=color_type, font=("Arial", 10, "bold")).grid(row=0, column=i+3, padx=5, pady=5)
            tk.Label(inner_frame, text="Move", font=("Arial", 10, "bold")).grid(row=0, column=len(color_types)+3, padx=5, pady=5)

            for row, theme in enumerate(theme_order, start=1):
                chk = tk.Checkbutton(inner_frame, variable=selected_themes[theme], command=lambda t=theme: toggle_selection(t))
                chk.grid(row=row, column=0, padx=5, pady=5)

                name_entry = tk.Entry(inner_frame, width=15)
                name_entry.insert(0, theme)
                name_entry.grid(row=row, column=1, padx=5, pady=5, sticky="e")

                rename_btn = tk.Button(inner_frame, text="Rename", command=lambda t=theme, e=name_entry: rename_theme(t, e))
                rename_btn.grid(row=row, column=2, padx=2, pady=2)

                for col, color_type in enumerate(color_types, start=0):
                    color = themes_dict[theme][color_type]
                    luminance = get_luminance(color)
                    btn = tk.Button(inner_frame, bg=color, fg="#000000" if luminance > 0.5 else "#ffffff", text=color, width=10, height=2, relief="raised")
                    btn.grid(row=row, column=col+3, padx=2, pady=2)
                    btn.config(command=lambda c=color, b=btn, t=theme, ct=color_type: open_color_chooser(c, b, t, ct))

                up_btn = tk.Button(inner_frame, text="↑", command=lambda t=theme: move_theme(t, -1), width=2)
                down_btn = tk.Button(inner_frame, text="↓", command=lambda t=theme: move_theme(t, 1), width=2)
                up_btn.grid(row=row, column=len(color_types)+3, padx=2, pady=2, sticky="w")
                down_btn.grid(row=row, column=len(color_types)+4, padx=2, pady=2, sticky="w")

            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_preview(theme):
            for widget in preview_frame.winfo_children():
                widget.destroy()

            colors = themes_dict[theme]
            
            tk.Label(preview_frame, text=theme, bg=colors['bg'], fg=colors['fg'], font=("Arial", 12, "bold")).pack(pady=10)
            preview_frame.configure(bg=colors['bg'])
            tk.Button(preview_frame, text="Sample Button", bg=colors['button_bg'], fg=colors['button_fg']).pack(pady=5)
            tk.Entry(preview_frame, bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg']).pack(pady=5)

            # Sample dropdown (Combobox)
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
            sample_combo = ttk.Combobox(preview_frame, values=["Option 1", "Option 2", "Option 3"], 
                                       style="Preview.TCombobox", state="readonly")
            sample_combo.set("Option 1")
            sample_combo.pack(pady=5)

            # Sample checkbox for selectbg
            for i in range(6):
                check_var = tk.BooleanVar(value=True)  # Always checked for demo
                sample_check = tk.Checkbutton(preview_frame, text="Sample Checkbox", variable=check_var,
                                              bg=colors['bg'], fg=colors['fg'], selectcolor=colors['selectbg'])
                sample_check.pack(pady=5)

            # Scrollable sample text area
            text_frame = tk.Frame(preview_frame, bg=colors['bg'])
            text_frame.pack(pady=5, fill="both", expand=True)

            scrollbar_preview = ttk.Scrollbar(text_frame, orient="vertical")
            scrollbar_preview.pack(side=tk.RIGHT, fill="y")

            sample_text = tk.Text(text_frame, height=6, width=20, bg=colors['entry_bg'], fg=colors['fg'], 
                                  insertbackground=colors['fg'], wrap="word")
            sample_text.pack(side=tk.LEFT, fill="both", expand=True)
            sample_text.insert(tk.END, "--- NOTES ---\n\nTo preview a theme, click any color & click 'Ok'.\n\nChanges are saved to a new file:\nthemecolors.json\ndeleting this file will revert to defaults\n\nWhen renaming themes, do so one at a time.\n\n")
            for i in range(100):  # 100 lines of sample text
                sample_text.insert(tk.END, f"Sample Text\n")

            sample_text.configure(yscrollcommand=scrollbar_preview.set)
            scrollbar_preview.configure(command=sample_text.yview)

            style.configure("Preview.Vertical.TScrollbar",
                            background=colors['scrollbar_bg'],
                            troughcolor=colors['scrollbar_trough'],
                            arrowcolor=colors['fg'])
            style.map("Preview.Vertical.TScrollbar",
                      background=[('disabled', colors['scrollbar_bg'])])
            scrollbar_preview.configure(style="Preview.Vertical.TScrollbar")

        def on_editor_closing():
            response = messagebox.askyesnocancel("Save Changes", "Do you want to save changes to themecolors.json before exiting?")
            if response is True:
                filtered_themes = {theme: themes_dict[theme] for theme in theme_order if selected_themes[theme].get()}
                self.theme.save_themes(filtered_themes)
                self.theme_combo['values'] = list(filtered_themes.keys())
                self.apply_theme()
                editor_window.destroy()
            elif response is False:
                editor_window.destroy()

        scroll_frame = tk.Frame(editor_window, width=1100)
        scroll_frame.pack(side="left", fill="y")
        scroll_frame.pack_propagate(False)

        initial_preview_theme = "DEMO" if "DEMO" in themes_dict else theme_order[0]
        preview_frame = tk.Frame(editor_window, bg=themes_dict[initial_preview_theme]['bg'])
        preview_frame.pack(side="right", fill="both", expand=True)
        update_preview(initial_preview_theme)

        canvas = tk.Canvas(scroll_frame)
        scrollbar = tk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        inner_frame.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        def on_mousewheel(event):
            if canvas.winfo_exists():
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind("<MouseWheel>", on_mousewheel)
        inner_frame.bind("<MouseWheel>", on_mousewheel)
        editor_window.bind("<MouseWheel>", on_mousewheel)

        refresh_grid()
        editor_window.protocol("WM_DELETE_WINDOW", on_editor_closing)

    def on_mousewheel(self, event):
        """Handles mouse wheel events for scrolling."""
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

    def toggle_broad_results(self, *args):
        """Enables/disables Broad Results checkbox based on Broad Search state."""
        state = "normal" if self.broad_search_var.get() else "disabled"
        self.broad_results_cb.configure(state=state)

    def load_data(self):
        """Loads the XML data in a separate thread."""
        try:
            logging.info("Starting load_data")
            xml_path = self.locate_xml_file()
            self.data_loader.parse_xml(xml_path)  # Parse main XML
            self.data_loader.load_notes()  # Load notes separately
            self.root.after(0, self.on_data_loaded)
        except FileNotFoundError as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"File not found: {str(e)}"))
        except etree.LxmlError as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"XML parsing failed: {str(e)}"))
        except Exception as e:
            logging.exception("Unexpected error in load_data")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Unexpected error: {str(e)}"))

    def locate_xml_file(self) -> Path:
        """Locates the XML file, prompting the user if necessary."""
        try:
            default_path = Path(xml_default_path)
            if default_path.exists():
                return default_path
            messagebox.showinfo("Select XML File", "XML file (ia_all.xml) not found in program folder.\nPress 'OK' to find its location.\nBypass this step next time by placing the XML file in the program folder (with the .exe)\nThe latest XML file may be downloaded from the IslamAwakened website.")
            file_path = filedialog.askopenfilename(
                title="Select Quran XML File",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
            )
            if not file_path:
                messagebox.showerror("Error", "XML file not found.\nDownload it from IslamAwakened.com\nPlace it in program folder.\nApplication will now close.")
                raise SystemExit("No XML file selected")
            return Path(file_path)
        except FileNotFoundError as e:
            logging.error(f"File not found: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error in locate_xml_file: {str(e)}")
            raise

    def on_data_loaded(self):
        """Callback after data is loaded to set up the GUI."""
        self.loading_label.destroy()
        self.load_preferences()
        self.load_notes_into_memory()
        self.create_gui()
        self.apply_theme()
        self.show_verses()

    def toggle_notes(self):
        colors = self.theme.get_colors()
        if self.notes_var.get():
            # Clear the keyword field unconditionally when enabling notes
            self.keyword_var.set("")

            # Set reference to first search result if available
            if self.search_results:
                new_ref = self.search_results[0]
                self.last_reference.set(new_ref)
            else:
                try:
                    surah_start, start_ayah, surah_end, end_ayah = self.parse_reference(self.last_reference.get())
                    if surah_start != surah_end or start_ayah != end_ayah:  # Range detected
                        new_ref = f"{surah_start}.{start_ayah}"
                        self.last_reference.set(new_ref)
                except ValueError:
                    self.last_reference.set('1.1')

            # Destroy existing widgets and create pane
            for widget in self.result_frame.winfo_children():
                widget.destroy()

            self.result_pane = tk.PanedWindow(self.result_frame, orient=tk.HORIZONTAL, bg=colors['bg'],
                                             sashwidth=5, sashrelief=tk.RAISED)
            self.result_pane.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

            # Verse frame
            verse_frame = tk.Frame(self.result_pane, bg=colors['bg'])
            self.result_text = tk.Text(verse_frame, wrap=tk.WORD,
                                      font=(self.current_font.get(), int(self.current_font_size.get())),
                                      bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'],
                                      padx=14, pady=9)
            self.result_scrollbar = ttk.Scrollbar(verse_frame, orient="vertical",
                                                 command=self.result_text.yview,
                                                 style="Vertical.TScrollbar")
            self.result_text.configure(yscrollcommand=self.result_scrollbar.set)
            self.result_text.grid(row=0, column=0, sticky="nsew")
            self.result_scrollbar.grid(row=0, column=1, sticky="ns")
            verse_frame.grid_rowconfigure(0, weight=1)
            verse_frame.grid_columnconfigure(0, weight=1)
            self.result_pane.add(verse_frame, minsize=400)

            # Notes frame
            self.notes_frame = tk.Frame(self.result_pane, bg=colors['bg'])
            self.notes_text = tk.Text(self.notes_frame, wrap=tk.WORD,
                                     font=(self.current_font.get(), int(self.current_font_size.get())),
                                     bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'],
                                     padx=14, pady=9)
            self.notes_scrollbar = ttk.Scrollbar(self.notes_frame, orient="vertical",
                                                command=self.notes_text.yview,
                                                style="Vertical.TScrollbar")
            self.notes_text.configure(yscrollcommand=self.notes_scrollbar.set)
            self.notes_text.grid(row=0, column=0, sticky="nsew")
            self.notes_scrollbar.grid(row=0, column=1, sticky="ns")
            self.notes_frame.grid_rowconfigure(0, weight=1)
            self.notes_frame.grid_columnconfigure(0, weight=1)
            self.result_pane.add(self.notes_frame, minsize=200)

            # Load existing note
            ref = self.last_reference.get()
            if ref in self.notes:
                self.notes_text.insert("1.0", self.notes[ref])

            self.root.bind("<Prior>", lambda event: self.result_text.yview_scroll(-1, "pages"))
            self.root.bind("<Next>", lambda event: self.result_text.yview_scroll(1, "pages"))
            self.show_verses(from_notes=True)  # Call with from_notes=True
        else:
            # Save note before closing
            if hasattr(self, 'notes_text') and self.notes_text and self.last_ref:
                note = self.notes_text.get("1.0", tk.END).strip()
                if note:
                    self.notes[self.last_ref] = note
                elif self.last_ref in self.notes:
                    del self.notes[self.last_ref]
                self.save_notes()

            if hasattr(self, 'result_pane'):
                self.result_pane.destroy()
            self.notes_text = None

            self.result_text = tk.Text(self.result_frame, wrap=tk.WORD,
                                      font=(self.current_font.get(), int(self.current_font_size.get())),
                                      bg=colors['entry_bg'], fg=colors['fg'], insertbackground=colors['fg'],
                                      padx=14, pady=9)
            self.result_scrollbar = ttk.Scrollbar(self.result_frame, orient="vertical",
                                                 command=self.result_text.yview,
                                                 style="Vertical.TScrollbar")
            self.result_text.configure(yscrollcommand=self.result_scrollbar.set)
            self.result_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            self.result_scrollbar.grid(row=0, column=1, sticky="ns")

            self.root.bind("<Prior>", lambda event: self.result_text.yview_scroll(-1, "pages"))
            self.root.bind("<Next>", lambda event: self.result_text.yview_scroll(1, "pages"))
            self.show_verses()

    def save_notes(self):
        """Save notes to notes.xml in ia_all.xml format."""
        if not self.notes:
#            if os.path.exists(self.data_loader.notes_file): # checks if any notes exist
#                os.remove(self.data_loader.notes_file)      # deletes notes.xml - unwanted behavoir
            return

        root = ET.Element("IslamAwakenedQuranDatabase", GenerationDate=datetime.datetime.now().strftime("%Y-%m-%d"))
        suwar = ET.SubElement(root, "Suwar")

        surah_notes = {}
        for ref, text in self.notes.items():
            surah, ayah = ref.split(".")
            if surah not in surah_notes:
                surah_notes[surah] = {}
            surah_notes[surah][ayah] = text

        for surah_num in sorted(surah_notes.keys(), key=int):
            surah_elem = ET.SubElement(suwar, "Surah", SurahNumber=surah_num)
            for ayah_num in sorted(surah_notes[surah_num].keys(), key=int):
                ayah_elem = ET.SubElement(surah_elem, "Ayah", AyahNumber=ayah_num)
                ET.SubElement(ayah_elem, "Rendition", Source="User Notes").text = surah_notes[surah_num][ayah_num]

        # Convert to string and pretty-print
        rough_string = ET.tostring(root, 'utf-8')
        import xml.dom.minidom
        parsed = xml.dom.minidom.parseString(rough_string)
        pretty_xml = parsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")

        with open(self.data_loader.notes_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

    def load_notes_into_memory(self):
        """Load notes from DataLoader into self.notes."""
        for surah in self.data_loader.verses:
            for ayah in self.data_loader.verses[surah]:
                if "User Notes" in self.data_loader.verses[surah][ayah]:
                    ref = f"{surah}.{ayah}"
                    self.notes[ref] = self.data_loader.verses[surah][ayah]["User Notes"]

    def load_preferences(self):
        """Loads user preferences into the GUI."""
        selected_translations = self.prefs.data.get('selected_translations', [])
        self.translation_vars = {}
        self.translation_checkbuttons = {}
        for trans in self.data_loader.translations:
            self.translation_vars[trans] = tk.BooleanVar(value=trans in selected_translations)

    def save_preferences(self):
        """Saves the current user preferences."""
        selected = [trans for trans, var in self.translation_vars.items() if var.get()]
        preferences = {
            'selected_translations': selected,
            'font': self.current_font.get(),
            'font_size': self.current_font_size.get(),
            'last_reference': self.ref_entry.get(),
            'theme': self.theme_var.get(),
            'last_keyword': self.keyword_var.get(),
            'broad_search': self.broad_search_var.get(),
            'broad_results': self.broad_results_var.get()
        }
        self.prefs.data = preferences
        self.prefs.save_preferences()

    def filter_translations(self, *args):
        """Filters the translation list based on search text."""
        search_text = self.filter_var.get().lower()
        for i, trans in enumerate(self.data_loader.translations):
            cb = self.translation_checkbuttons[trans]
            if search_text in trans.lower():
                cb.grid(row=i, column=0, sticky="w", padx=2, pady=0)
            else:
                cb.grid_forget()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def create_context_menu(self):
        """Creates the context menu for copying text."""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selected_text)
        self.result_text.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Shows the context menu if text is selected."""
        if self.result_text.tag_ranges("sel"):
            self.context_menu.post(event.x_root, event.y_root)

    def copy_selected_text(self):
        """Copies selected text to the clipboard."""
        try:
            selected_text = self.result_text.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.status_var.set("Selected text copied to clipboard")
        except tk.TclError:
            self.status_var.set("No text selected to copy")

    def copy_to_clipboard(self):
        """Copies all text in the result area to the clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result_text.get(1.0, tk.END))
        self.status_var.set("All verses copied to clipboard")

    def update_font(self, event=None):
        """Updates the font of the result text area."""
        font_name = self.current_font.get()
        if font_name not in tkfont.families():
            font_name = DEFAULT_FONT
            self.current_font.set(font_name)
        try:
            self.result_text.configure(
                font=(font_name, int(self.current_font_size.get()))
            )
        except tk.TclError:
            self.current_font.set(DEFAULT_FONT)
            self.current_font_size.set(DEFAULT_FONT_SIZE)
            self.result_text.configure(font=(DEFAULT_FONT, int(DEFAULT_FONT_SIZE)))

    def parse_reference(self, ref: str) -> tuple[str, str, str, str]:
        """Parses the reference string into surah and ayah ranges."""
        import re
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
            end_ayah = str(max(int(ayah) for ayah in self.data_loader.surahs.get(surah_start, set())) if surah_start in self.data_loader.surahs else 0)
        elif re.match(surah_range, ref):
            match = re.match(surah_range, ref)
            surah_start, surah_end = match.groups()
            start_ayah = '1'
            end_ayah = str(max(int(ayah) for ayah in self.data_loader.surahs.get(surah_end, set())) if surah_end in self.data_loader.surahs else 0)
        elif re.match(verse_single, ref):
            match = re.match(verse_single, ref)
            surah_start, start_ayah = match.groups()
            surah_end = surah_start
            end_ayah = start_ayah
            if start_ayah == '0':
                if surah_start in self.data_loader.surahs:
                    start_ayah = '1'
                    end_ayah = str(max(int(ayah) for ayah in self.data_loader.surahs[surah_start]))
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
                end_ayah = str(max(int(ayah) for ayah in self.data_loader.surahs.get(surah_end, set())) if surah_end in self.data_loader.surahs else 0)
        elif re.match(surah_to_verse, ref):
            match = re.match(surah_to_verse, ref)
            surah_start, surah_end, end_ayah = match.groups()
            start_ayah = '1'
        elif re.match(verse_range, ref):
            match = re.match(verse_range, ref)
            surah_start, start_ayah, surah_end, end_ayah = match.groups()
        else:
            raise ValueError("Invalid reference format\n\n  Try :\n One surah (e.g., 1)\n A specific verse (e.g., 2.225)\n A surah range (e.g., 3-4)\n A specific range (e.g., 5-7.9)\n\n Use 1-114 to search the entire Quran")

        if surah_start not in self.data_loader.surahs or surah_end not in self.data_loader.surahs:
            raise ValueError(f"Surah {surah_start} or {surah_end} not found")
        return surah_start, start_ayah, surah_end, end_ayah

    def get_previous_verse(self, surah: str, ayah: str) -> Optional[tuple[str, str]]:
        """Returns the previous verse as (surah, ayah) or None if at the first verse."""
        surah_int = int(surah)
        ayah_int = int(ayah)
        if ayah_int > 1:
            return (surah, str(ayah_int - 1))
        elif surah_int > 1:
            prev_surah = str(surah_int - 1)
            max_ayah = self.data_loader.ayah_counts[prev_surah]
            return (prev_surah, str(max_ayah))
        else:
            return None  # At 1.1, no previous verse

    def get_next_verse(self, surah: str, ayah: str) -> Optional[tuple[str, str]]:
        """Returns the next verse as (surah, ayah) or None if at the last verse."""
        surah_int = int(surah)
        ayah_int = int(ayah)
        max_ayah = self.data_loader.ayah_counts[surah]
        if ayah_int < max_ayah:
            return (surah, str(ayah_int + 1))
        elif surah_int < 114:
            next_surah = str(surah_int + 1)
            return (next_surah, "1")
        else:
            return None  # At 114.6, no next verse

    def go_previous(self):
        """Handles the '<' button click to navigate to the previous verse or start of range."""
        try:
            surah_start, start_ayah, surah_end, end_ayah = self.parse_reference(self.ref_entry.get())
            if surah_start == surah_end and start_ayah == end_ayah:
                # Single verse, go to previous
                prev_verse = self.get_previous_verse(surah_start, start_ayah)
                if prev_verse:
                    new_ref = f"{prev_verse[0]}.{prev_verse[1]}"
                    self.last_reference.set(new_ref)
                    self.show_verses(from_navigation=True)
            else:
                # Range, go to start verse
                new_ref = f"{surah_start}.{start_ayah}"
                self.last_reference.set(new_ref)
                self.show_verses(from_navigation=True)
        except ValueError:
            # Invalid reference, do nothing
            pass

    def go_next(self):
        """Handles the '>' button click to navigate to the next verse or end of range."""
        try:
            surah_start, start_ayah, surah_end, end_ayah = self.parse_reference(self.ref_entry.get())
            if surah_start == surah_end and start_ayah == end_ayah:
                # Single verse, go to next
                next_verse = self.get_next_verse(surah_start, start_ayah)
                if next_verse:
                    new_ref = f"{next_verse[0]}.{next_verse[1]}"
                    self.last_reference.set(new_ref)
                    self.show_verses(from_navigation=True)
            else:
                # Range, go to end verse
                new_ref = f"{surah_end}.{end_ayah}"
                self.last_reference.set(new_ref)
                self.show_verses(from_navigation=True)
        except ValueError:
            # Invalid reference, do nothing
            pass

    def show_verses(self, event=None, from_notes=False, from_navigation=False):
        # Block search if Notes is active and keywords are entered
        # Bypass warning if called from toggle_notes
        if not from_notes and self.notes_var.get() and self.keyword_var.get().strip():
            messagebox.showinfo("Close your 'Notes' - or - Clear the search field", "Before searching, clear the 'Notes' checkbox \n and choose a search range, typically: 1-114")
            return

        # Save previous note if Notes pane is active
        if hasattr(self, 'notes_text') and self.notes_text and self.last_ref:
            prev_note = self.notes_text.get("1.0", tk.END).strip()
            if prev_note:
                self.notes[self.last_ref] = prev_note
            elif self.last_ref in self.notes:
                del self.notes[self.last_ref]
            self.save_notes()

        ref = self.ref_entry.get().strip()
        keyword = self.keyword_var.get().strip().lower()
        selected_translations = [trans for trans, var in self.translation_vars.items() if var.get()]
        if not selected_translations:
            messagebox.showwarning("Warning", "Please select at least one translation.")
            return
        try:
            surah_start, start_ayah, surah_end, end_ayah = self.parse_reference(ref)
            is_single_verse = (surah_start == surah_end and start_ayah == end_ayah)

            # If notes are active and it's a range, revert to last single verse (unless from navigation)
            if self.notes_var.get() and not is_single_verse and not from_navigation:
                if self.last_ref:
                    messagebox.showinfo("First close your 'Notes'", "Notes can only be applied to a single verse\nTo view a surah-range, first close the 'Notes'")
                    self.last_reference.set(self.last_ref)
                    self.ref_entry.update()
                    surah_start, start_ayah, surah_end, end_ayah = self.parse_reference(self.last_ref)
                    is_single_verse = True
                else:
                    messagebox.showinfo("Notes Active", "Close the 'Notes' to view a range")
                    self.last_reference.set("1.1")
                    self.ref_entry.update()
                    surah_start, start_ayah, surah_end, end_ayah = self.parse_reference("1.1")
                    self.last_ref = "1.1"
                    is_single_verse = True

            self.result_text.delete(1.0, tk.END)
            verse_count = 0
            translation_count = len(selected_translations)
            start_surah = int(surah_start)
            end_surah = int(surah_end)

            # Determine if it's a single verse
#            is_single_verse = (surah_start == surah_end and start_ayah == end_ayah)

            # Initialize search_results: list if keyword search on range, None otherwise
            if keyword and not is_single_verse:
                self.search_results = []
            else:
                self.search_results = None

            if self.broad_search_var.get():
                translations_to_check = self.data_loader.translations
            else:
                translations_to_check = selected_translations

            additional_translations = set()

            patterns = []
            phrase_pattern = None
            if keyword:
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

            for surah_num in range(start_surah, end_surah + 1):
                surah = str(surah_num)
                if surah in self.data_loader.verses:
                    start = int(start_ayah) if surah_num == start_surah else 1
                    end = int(end_ayah) if surah_num == end_surah else max(int(ayah) for ayah in self.data_loader.surahs[surah])
                    for ayah in range(start, end + 1):
                        ayah_str = str(ayah)
                        if ayah_str in self.data_loader.verses[surah]:
                            matching_translations = []
                            # Single verse: always display
                            if is_single_verse:
                                match = True
                            elif keyword:
                                match = False
                                for trans in translations_to_check:
                                    if trans in self.data_loader.verses[surah][ayah_str]:
                                        text = self.data_loader.verses[surah][ayah_str][trans]
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
                                # Store result if it's a keyword search over a range
                                if keyword and not is_single_verse:
                                    self.search_results.append(f"{surah}.{ayah}")
                                surah_name = self.data_loader.surah_names.get(surah, ('', '', ''))
                                verse_text = f"Surah {surah} - {surah_name[0]} ({surah_name[2]}): Ayah {ayah}\n"
                                verse_text += "=" * 40 + "\n"
                                has_content = False

                                display_translations = selected_translations.copy()
                                if self.broad_search_var.get() and self.broad_results_var.get():
                                    for trans in matching_translations:
                                        if trans not in display_translations:
                                            display_translations.append(trans)
                                    additional_translations.update([trans for trans in matching_translations 
                                                                  if trans not in selected_translations])

                                for trans in display_translations:
                                    if trans in self.data_loader.verses[surah][ayah_str]:
                                        text = self.data_loader.verses[surah][ayah_str][trans]
                                        verse_text += f"{trans}:\n{text}\n\n"
                                        has_content = True

                                if has_content:
                                    self.result_text.insert(tk.END, verse_text)
                                    verse_count += 1

            # Update last_ref for single verse
            self.last_ref = f"{surah_start}.{start_ayah}" if is_single_verse else None

            # Load note if Notes pane is active
            if hasattr(self, 'notes_text') and self.notes_text and self.last_ref:
                self.notes_text.delete("1.0", tk.END)
                if self.last_ref in self.notes:
                    self.notes_text.insert("1.0", self.notes[self.last_ref])

            if verse_count == 0:
                self.result_text.insert(tk.END, "No verses match the search criteria.\n")
                self.status_var.set("No verses match the search criteria")
            else:
                verse_label = "verse" if verse_count == 1 else "verses"
                if self.broad_search_var.get() and self.broad_results_var.get() and additional_translations:
                    extra_count = len(additional_translations)
                    total_trans = translation_count + extra_count
                    trans_label = "translation" if total_trans == 1 else "translations"
                    self.status_var.set(f"Found {verse_count} {verse_label} in {translation_count}+{extra_count} {trans_label}")
                else:
                    trans_label = "translation" if translation_count == 1 else "translations"
                    self.status_var.set(f"Found {verse_count} {verse_label} in {translation_count} {trans_label}")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error in reference format")
            self.last_reference.set("1-114")  # fix the mistake to something useful
            self.ref_entry.update()  # reflects change in GUI
            self.show_verses() # and call for the output of 1-114
        
    def on_closing(self):
        # Save current note if notes pane is active
        if self.notes_var.get() and hasattr(self, 'notes_text') and self.notes_text and self.last_ref:
            note = self.notes_text.get("1.0", tk.END).strip()
            if note:
                self.notes[self.last_ref] = note
            elif self.last_ref in self.notes:
                del self.notes[self.last_ref]
        self.save_notes()  # Save all notes to notes.xml
        self.save_preferences()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = QuranSearchApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
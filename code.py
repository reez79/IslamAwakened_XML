import json
from lxml import etree
from ttkbootstrap import Window, ScrolledText, Style
import ttkbootstrap as ttk
import tkinter as tk
from tkinter import messagebox, filedialog
import sys
from pathlib import Path
import threading
import html
import os
import logging

# Set up basic logging to console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Base path for executable or script
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
xml_default_path = os.path.join(base_path, "ia_all.xml")

class DataLoader:
    """Handles loading and parsing of Quran XML data."""
    def __init__(self):
        self.translations = []
        self.surahs = {}
        self.verses = {}
        self.surah_names = {}

    def parse_xml(self, xml_path):
        """Parses the XML file using streaming to minimize memory usage."""
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
        except etree.LxmlError as e:
            raise ValueError(f"Failed to parse XML: {str(e)}")

class PreferencesManager:
    """Manages saving and loading of user preferences."""
    def __init__(self):
        self.filename = "preferences.json"
        self.data = {}

    def load_preferences(self):
        """Loads preferences from the JSON file or sets defaults if it doesn't exist."""
        if not os.path.exists(self.filename):
            # First run: set default preferences
            self.data = {
                "selected_translations": ["Arabic", "Muhammad Asad"],
                "font": "Arial",
                "font_size": "12",
                "last_reference": "1",
                "theme": "darkly",  # Internal name
                "last_keyword": ""
            }
            logging.debug("No preferences.json found, using default preferences")
        else:
            try:
                with open(self.filename, 'r') as f:
                    self.data = json.load(f)
                logging.debug("Loaded preferences from preferences.json")
            except FileNotFoundError:
                self.data = {}  # This should not happen due to the os.path.exists check, but kept for safety
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding preferences.json: {str(e)}, using empty preferences")
                self.data = {}

    def save_preferences(self):
        """Saves preferences to the JSON file."""
        with open(self.filename, 'w') as f:
            json.dump(self.data, f)

class QuranSearchApp:
    def _get_color(self, index):
        """Returns a color from a predefined set of readable colors."""
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                 '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        return colors[index % len(colors)]

    def __init__(self, root: Window):
        try:
            logging.debug("Initializing QuranSearchApp")
            self.root = root
            self.root.title("Quran Verse Explorer")

            # Desired window size
            desired_width = 1400
            desired_height = 1050

            # Get screen dimensions
            self.root.update_idletasks()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            # Account for taskbar/dock
            usable_height = screen_height - 100

            # Check if desired size fits
            if desired_width > screen_width or desired_height > usable_height:
                logging.debug(f"Screen too small ({screen_width}x{screen_height}), maximizing window")
                self.root.state('normal')
            else:
                logging.debug(f"Setting window to {desired_width}x{desired_height}")
                self.root.geometry(f"{desired_width}x{desired_height}")
                self.center_window()

            self.root.minsize(800, 600)
            self.data_loader = DataLoader()
            self.prefs = PreferencesManager()
            self.prefs.load_preferences()

            # Set initial theme
            self.style = Style()
            self.style.theme_use('flatly')

            # Font settings
            self.available_fonts = sorted(list(tk.font.families()))
            self.current_font = tk.StringVar(value=self.prefs.data.get('font', 'Arial'))
            self.current_font_size = tk.StringVar(value=self.prefs.data.get('font_size', '12'))
            self.font_sizes = [str(size) for size in range(8, 25)]

            # Search filter for translations
            self.filter_var = tk.StringVar()
            self.filter_var.trace_add('write', self.filter_translations)

            # Verse reference and keyword search
            self.last_reference = tk.StringVar(value=self.prefs.data.get('last_reference', ''))
            self.keyword_var = tk.StringVar(value=self.prefs.data.get('last_keyword', ''))

            # Theme selection with mapping
            self.theme_mapping = {
                'Light': 'flatly',
                'White': 'litera',
                'Mint': 'minty',
                'Dark': 'darkly',
                'Darker': 'cyborg',
                'Blue': 'superhero',
                'Aqua': 'solar',
                'Neon': 'vapor'
            }
            self.theme_display_names = list(self.theme_mapping.keys())
            default_display = next(key for key, value in self.theme_mapping.items() 
                                 if value == self.prefs.data.get('theme', 'darkly'))
            self.theme_var = tk.StringVar(value=default_display)

            # Loading label
            self.loading_label = ttk.Label(self.root, text="Loading data, please wait...", bootstyle="info")
            self.loading_label.pack(expand=True)

            # Start data loading in background
            threading.Thread(target=self.load_data, daemon=True).start()

            # Bind window closing event
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            logging.debug("Initialization complete")
        except Exception as e:
            logging.error(f"Error in QuranSearchApp.__init__: {str(e)}")
            raise

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def load_data(self):
        try:
            logging.debug("Starting load_data")
            xml_path = self.locate_xml_file()
            self.data_loader.parse_xml(xml_path)
            self.root.after(0, self.on_data_loaded)
        except SystemExit:
            logging.info("SystemExit triggered, closing application")
            self.root.after(0, self.root.destroy)
        except Exception as e:
            logging.error(f"Error in load_data: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load data: {str(e)}"))
            self.root.after(0, self.root.destroy)

    def locate_xml_file(self):
        try:
            default_path = Path(xml_default_path)
            if default_path.exists():
                return default_path
            messagebox.showinfo("Select XML File", "XML file (ia_all.xml) not found in program folder.\nProvide its location.")
            file_path = filedialog.askopenfilename(
                title="Select Quran XML File",
                filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
            )
            if not file_path:
                messagebox.showerror("Error", "XML file not found.\nDownload it from IslamAwakened.com\nPlace it in program folder.\nApplication will now close.")
                raise SystemExit("No XML file selected")
            return Path(file_path)
        except Exception as e:
            logging.error(f"Error in locate_xml_file: {str(e)}")
            raise

    def on_data_loaded(self):
        try:
            logging.debug("Data loaded, setting up GUI")
            self.loading_label.destroy()
            self.load_preferences()
            self.create_gui()
            self.apply_theme()
            self.show_verses()
        except Exception as e:
            logging.error(f"Error in on_data_loaded: {str(e)}")
            raise

    def load_preferences(self):
        selected_translations = self.prefs.data.get('selected_translations', [])
        self.translation_vars = {}
        self.translation_checkbuttons = {}
        for trans in self.data_loader.translations:
            self.translation_vars[trans] = tk.BooleanVar(value=trans in selected_translations)
        # Set theme_var from saved internal theme name
        internal_theme = self.prefs.data.get('theme', 'darkly')
        display_name = next(key for key, value in self.theme_mapping.items() 
                          if value == internal_theme)
        self.theme_var.set(display_name)

    def save_preferences(self):
        selected = [trans for trans, var in self.translation_vars.items() if var.get()]
        # Convert display name to internal theme name
        display_name = self.theme_var.get()
        internal_theme = self.theme_mapping.get(display_name, 'flatly')
        preferences = {
            'selected_translations': selected,
            'font': self.current_font.get(),
            'font_size': self.current_font_size.get(),
            'last_reference': self.ref_entry.get(),
            'theme': internal_theme,  # Save internal name
            'last_keyword': self.keyword_var.get()
        }
        self.prefs.data = preferences
        self.prefs.save_preferences()

    def apply_theme(self, event=None):
        # Map display name to internal theme name
        selected_display = self.theme_var.get()
        theme_name = self.theme_mapping.get(selected_display, 'flatly')
        self.style.theme_use(theme_name)
        logging.debug(f"Applied theme '{theme_name}' (displayed as '{selected_display}')")

    def filter_translations(self, *args):
        search_text = self.filter_var.get().lower()

        # Remove all checkbuttons from the grid
        for trans in self.data_loader.translations:
            cb = self.translation_checkbuttons[trans]
            cb.grid_remove()

        # Re-grid only matching checkbuttons in sequence
        row = 0
        for trans in self.data_loader.translations:
            if search_text in trans.lower():
                cb = self.translation_checkbuttons[trans]
                cb.grid(row=row, column=0, sticky="w", padx=2, pady=0)
                row += 1

        # Update canvas scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.update_idletasks()

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self.copy_selected_text)
        self.result_text.bind("<Button-3>", self.show_context_menu)
        self.result_text.bind("<Button-2>", self.show_context_menu)

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

    def copy_to_clipboard(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result_text.get(1.0, tk.END))
        self.status_var.set("All verses copied to clipboard")

    def create_gui(self):
        try:
            logging.debug("Creating GUI")
            # Main horizontal PanedWindow
            self.main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
            self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            logging.debug("Main container created and packed")

            # Left Pane: Translations (full height)
            self.left_frame = ttk.LabelFrame(self.main_container, text="Translations")
            self.main_container.add(self.left_frame, weight=1)
            self.left_frame.grid_rowconfigure(1, weight=1)
            self.left_frame.grid_columnconfigure(0, weight=1)
            logging.debug("Left frame added to main container")

            # Filter Frame (Translations Search)
            self.filter_frame = ttk.Frame(self.left_frame)
            self.filter_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
            self.toggle_all_var = tk.BooleanVar(value=False)
            self.toggle_all_cb = ttk.Checkbutton(
                self.filter_frame,
                text="Toggle All",
                variable=self.toggle_all_var,
                command=self.toggle_all_translations
            )
            self.toggle_all_cb.pack(side=tk.TOP, padx=5, pady=5) # Moved to top
            ttk.Label(self.filter_frame, text="Search:").pack(side=tk.LEFT, padx=5)
            self.filter_entry = ttk.Entry(self.filter_frame, textvariable=self.filter_var)
            self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            logging.debug("Filter frame setup complete")

            # Translations List with Scrollbar
            self.canvas = tk.Canvas(self.left_frame)
            scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.canvas.yview)
            self.scrollable_frame = tk.Frame(self.canvas)

            self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
            self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
            self.canvas.configure(yscrollcommand=scrollbar.set)

            # Bind mouse wheel events to canvas and frame
            for widget in (self.canvas, self.scrollable_frame):
                widget.bind("<MouseWheel>", self.on_mouse_wheel)
                widget.bind("<Button-4>", self.on_mouse_wheel)
                widget.bind("<Button-5>", self.on_mouse_wheel)

            # Add checkbuttons with focus underline using tk.Checkbutton
            self.checkbuttons = []
            for i, trans in enumerate(self.data_loader.translations):
                cb = tk.Checkbutton(
                    self.scrollable_frame,
                    text=trans,
                    variable=self.translation_vars[trans],
                    font=('Arial', 10),
                    underline=-1,
                )
                cb.grid(row=i, column=0, sticky="w", padx=2, pady=0)
                cb.bind("<MouseWheel>", self.on_mouse_wheel)
                cb.bind("<Button-4>", self.on_mouse_wheel)
                cb.bind("<Button-5>", self.on_mouse_wheel)
                cb.bind("<FocusIn>", lambda event, c=cb: c.configure(underline=0))
                cb.bind("<FocusOut>", lambda event, c=cb: c.configure(underline=-1))
                self.translation_checkbuttons[trans] = cb
                self.checkbuttons.append(cb)
            logging.debug(f"Added {len(self.checkbuttons)} checkbuttons")

            self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
            scrollbar.grid(row=1, column=1, sticky="ns")
            logging.debug("Canvas and scrollbar gridded in left frame")

            # Right vertical PanedWindow
            self.right_container = ttk.PanedWindow(self.main_container, orient=tk.VERTICAL)
            self.main_container.add(self.right_container, weight=3)
            logging.debug("Right container added to main container")

            # Upper right: Search Verses
            self.search_frame = ttk.LabelFrame(self.right_container, text="Search Verses")
            self.right_container.add(self.search_frame, weight=0)
            self.search_frame.grid_columnconfigure(0, weight=1)
            logging.debug("Search frame added to right container")

            # Top row: Reference and buttons
            self.top_frame = ttk.Frame(self.search_frame)
            self.top_frame.pack(fill="x", padx=5, pady=2)
            ttk.Label(self.top_frame, text="Surah.Verse-Range:\n(e.g., 36, 1-114, 2.255-27.30)").pack(side="left", padx=5)
            self.ref_entry = ttk.Entry(self.top_frame, textvariable=self.last_reference, width=20)
            self.ref_entry.pack(side="left", padx=5)
            self.ref_entry.bind('<Return>', self.show_verses)
            ttk.Button(self.top_frame, text="Show Verses", command=self.show_verses).pack(side="left", padx=5)
            ttk.Button(self.top_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(side="left", padx=5)
            ttk.Label(self.top_frame, text="Search keywords:").pack(side="left", padx=5)
            self.keyword_entry = ttk.Entry(self.top_frame, textvariable=self.keyword_var)
            self.keyword_entry.pack(side="left", fill="x", expand=True, padx=5)
            self.keyword_entry.bind('<Return>', self.show_verses)
            logging.debug("Top frame (search controls) packed")

            # Show titles checkbox and Font controls
            self.font_frame = ttk.Frame(self.search_frame)
            self.font_frame.pack(fill="x", padx=5, pady=2)
            self.show_titles_var = tk.BooleanVar(value=False)
            self.show_titles_cb = ttk.Checkbutton(
                self.font_frame, 
                text="Show titles",
                variable=self.show_titles_var,
                command=self.show_verses
            )
            self.show_titles_cb.pack(side="left", padx=5)
            ttk.Label(self.font_frame, text="Font:").pack(side="left", padx=5)
            self.font_combo = ttk.Combobox(
                self.font_frame,
                textvariable=self.current_font,
                values=self.available_fonts,
                width=20
            )
            self.font_combo.pack(side="left", padx=5)
            self.font_combo.bind('<<ComboboxSelected>>', self.update_font)
            ttk.Label(self.font_frame, text="Size:").pack(side="left", padx=5)
            self.size_combo = ttk.Combobox(
                self.font_frame,
                textvariable=self.current_font_size,
                values=self.font_sizes,
                width=5
            )
            self.size_combo.pack(side="left", padx=5)
            self.size_combo.bind('<<ComboboxSelected>>', self.update_font)
            ttk.Label(self.font_frame, text="Theme:").pack(side="left", padx=5)
            self.theme_combo = ttk.Combobox(
                self.font_frame,
                textvariable=self.theme_var,
                values=self.theme_display_names,  # Use display names
                state='readonly',
                width=15  # Adjusted for longer names
            )
            self.theme_combo.pack(side="left", padx=5)
            self.theme_combo.bind('<<ComboboxSelected>>', self.apply_theme)
            self.status_var = tk.StringVar(value="Ready")
            self.status_label = ttk.Label(self.font_frame, textvariable=self.status_var, font=16)
            self.status_label.pack(side="right", padx=15, pady=5)
            logging.debug("Font and theme controls packed")

            # Lower right: Verses with custom Text and ttk.Scrollbar
            self.result_frame = ttk.LabelFrame(self.right_container, text="Verses")
            self.right_container.add(self.result_frame, weight=3)
            self.result_frame.grid_rowconfigure(0, weight=1)
            self.result_frame.grid_columnconfigure(0, weight=1)
            logging.debug("Result frame added to right container")

            self.result_text = tk.Text(
                self.result_frame,
                wrap=tk.WORD,
                font=(self.current_font.get(), int(self.current_font_size.get()))
            )
            result_scrollbar = ttk.Scrollbar(self.result_frame, orient="vertical", command=self.result_text.yview)
            self.result_text.configure(yscrollcommand=result_scrollbar.set)
            self.result_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            result_scrollbar.grid(row=0, column=1, sticky="ns")
            logging.debug("Result text and scrollbar gridded")

            # Bind Page Up and Page Down to scroll the verses text
            self.root.bind("<Prior>", self.page_up)
            self.root.bind("<Next>", self.page_down)

            self.create_context_menu()
            self.root.update()
            self.main_container.sashpos(0, 300)
            self.right_container.sashpos(0, 100)
            logging.debug("GUI created successfully")
        except Exception as e:
            logging.error(f"Error in create_gui: {str(e)}")
            messagebox.showerror("Error", f"GUI creation failed: {str(e)}")
            raise

    def on_tab(self, event):
        current_focus = self.root.focus_get()
        try:
            current_index = self.checkbuttons.index(current_focus)
        except ValueError:
            current_index = -1
        next_index = (current_index + 1) % len(self.checkbuttons)
        self.checkbuttons[next_index].focus_set()
        return "break"

    def on_mouse_wheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def page_up(self, event):
        self.result_text.yview_scroll(-1, "pages")
        return "break"

    def page_down(self, event):
        self.result_text.yview_scroll(1, "pages")
        return "break"

    def update_font(self, event=None):
        try:
            self.result_text.configure(
                font=(self.current_font.get(), int(self.current_font_size.get()))
            )
        except tk.TclError:
            self.current_font.set("Arial")
            self.current_font_size.set("11")
            self.result_text.configure(font=("Arial", 11))

    def parse_reference(self, ref: str) -> tuple:
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
            raise ValueError("Invalid reference format\n  Try :\n One surah (e.g., 1)\n A specific verse (e.g., 2.225)\n A surah range (e.g., 3-4)\n A specific range (e.g., 5-7.9)")

        if surah_start not in self.data_loader.surahs or surah_end not in self.data_loader.surahs:
            raise ValueError(f"Surah {surah_start} or {surah_end} not found")
        return surah_start, start_ayah, surah_end, end_ayah

    def show_verses(self, event=None):
        ref = self.ref_entry.get().strip()
        keyword = self.keyword_var.get().strip().lower()
        selected_translations = [trans for trans, var in self.translation_vars.items() if var.get()]
        if not selected_translations:
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "Please select at least one translation to display verses.")
            self.status_var.set("No translations selected")
            return
        try:
            surah_start, start_ayah, surah_end, end_ayah = self.parse_reference(ref)
            self.result_text.delete(1.0, tk.END)
            verse_count = 0
            translation_count = len(selected_translations)
            start_surah = int(surah_start)
            end_surah = int(surah_end)
            for surah_num in range(start_surah, end_surah + 1):
                surah = str(surah_num)
                if surah in self.data_loader.verses:
                    start = int(start_ayah) if surah_num == start_surah else 1
                    end = int(end_ayah) if surah_num == end_surah else max(int(ayah) for ayah in self.data_loader.surahs[surah])
                    for ayah in range(start, end + 1):
                        ayah_str = str(ayah)
                        if ayah_str in self.data_loader.verses[surah]:
                            if keyword:
                                if keyword.startswith('"') and keyword.endswith('"'):
                                    phrase = keyword[1:-1]
                                    match = any(phrase in self.data_loader.verses[surah][ayah_str][trans].lower()
                                                for trans in selected_translations
                                                if trans in self.data_loader.verses[surah][ayah_str])
                                else:
                                    words = keyword.split()
                                    match = any(all(word in self.data_loader.verses[surah][ayah_str][trans].lower()
                                                    for word in words)
                                                for trans in selected_translations
                                                if trans in self.data_loader.verses[surah][ayah_str])
                            else:
                                match = True
                            if match:
                                # Show surah name at start of new surah
                                if self.show_titles_var.get() and (verse_count == 0 or (int(ayah) == 1)):
                                    surah_name = self.data_loader.surah_names.get(surah, ('', '', ''))
                                    arabic_name = ''.join(surah_name[0])  # Reverse the Arabic text for proper RTL display
                                    self.result_text.tag_configure("arabic", justify='right')  # Configure tag for Arabic text
                                    self.result_text.insert(tk.END, f"\nSurah {surah} - ", "surah_title")
                                    self.result_text.insert(tk.END, arabic_name, "arabic")  # Insert Arabic with RTL tag
                                    self.result_text.insert(tk.END, f" ({surah_name[2]})\n", "surah_title")

                                    # Show selected translators with their colors
                                    for i, trans in enumerate(selected_translations):
                                        color = f"color_{i}"
                                        self.result_text.tag_configure(color, foreground=self._get_color(i))
                                        self.result_text.insert(tk.END, f"{trans}\n", color)

                                    self.result_text.insert(tk.END, "="*40 + "\n\n")

                                for i, trans in enumerate(selected_translations):
                                    if trans in self.data_loader.verses[surah][ayah_str]:
                                        color = f"color_{i}"
                                        text = self.data_loader.verses[surah][ayah_str][trans]
                                        if self.show_titles_var.get():
                                            self.result_text.insert(tk.END, f"[{ayah}] ", color)
                                        self.result_text.insert(tk.END, f"{text}\n", color)
                                verse_count += 1
            if verse_count == 0:
                self.result_text.insert(tk.END, "No verses match the search criteria.\n")
                self.status_var.set("No verses match the search criteria")
            else:
                self.status_var.set(f"Showing {verse_count} verses across {translation_count} translations")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("Error in reference format")

    def toggle_all_translations(self):
        state = self.toggle_all_var.get()
        for trans, var in self.translation_vars.items():
            var.set(state)

    def on_closing(self):
        self.save_preferences()
        self.root.destroy()

def main():
    try:
        logging.debug("Starting main")
        root = Window()
        app = QuranSearchApp(root)
        root.mainloop()
    except Exception as e:
        logging.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()

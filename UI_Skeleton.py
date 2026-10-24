import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QTextEdit, QLineEdit, QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy,
                             QToolButton, QCheckBox, QComboBox, QDialog, QSlider)
from PyQt5.QtCore import (Qt, QPropertyAnimation, QEasingCurve, QSize, pyqtSignal)

from PyQt5.QtGui import (QFont, QPixmap, QColor, QPalette, QIcon, QTextCursor, QPixmap)

# THEME CONSTANTS

BG_DEEP      = "#0d0d0f"   
BG_PANEL     = "#13141a"
BG_SURFACE   = "#1a1b24" 
BG_INPUT     = "#1e1f2b" 
ACCENT       = "#c8882a"
ACCENT_HOVER = "#e0a03a"
TEXT_PRIMARY = "#e8e4d9"
TEXT_MUTED   = "#6b6a72" 
BORDER       = "#2a2b38"
USER_BUBBLE  = "#1f2535"
BOT_BUBBLE   = "#161720"
 
# SIDEBAR WIDTH
MENU_W_OPEN   = 250 
MENU_W_CLOSED = 0

# CLASS: SIDEBAR
# SIGNALTS IT EMITS (Outbound events)
#   • settings_requested  — user clicked the settings button
#   • session_selected    — user clicked a session in the list
#   • session_deleted     — user clicked ✕ on a session
#   • new_chat_requested  — user clicked "+ New Chat"

class Sidebar(QWidget):
    settings_requested = pyqtSignal()       # No data - just a notification
    session_selected   = pyqtSignal(object) # Emits a Python object (ChatSession)
    session_deleted    = pyqtSignal(str)    # Emits a string (the session ID)
    new_chat_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent) # Always call super().__init__ in QWidget subclasses.
        self.setObjectName("sidebar") # Giving QWidget an ID for styling e.g. QWidget#sidebar
        self.setMinimumWidth(0)
        self.setMaximumWidth(MENU_W_CLOSED) # Starts hidden (maxWidth=0). The animation widens it to MENU_W_OPEN

        # ---- LAYOUT ----
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16) # (left, top, right, bottom) adds padding inside the widget
        layout.setSpacing(8) # sets spacing between adjacent child widgets.

        # ---- TITLE LABEL ----
        title = QLabel("SESSIONS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 3px;
            padding-bottom: 8px;
            border-bottom: 1px solid {BORDER};
    """)
        layout.addWidget(title)

        # --- NEW CHAT BUTTON ---
        self.new_chat_btn = QPushButton("+  New Chat")
        self.new_chat_btn.setCursor(Qt.PointingHandCursor)
        self.new_chat_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: {BG_DEEP};
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
                text-align: left;
            }}
            QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
    """)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        layout.addWidget(self.new_chat_btn)

        # --- SCROLLABLE SESSION LIST ---
        self.chat_scroll = QScrollArea() # QScollArea() adds scrollbars when the inner widget is too tall/wide.
        self.chat_scroll.setWidgetResizable(True)
        # True = the inner widget stretches to fill the scroll area's width.
        # False = the inner widget keeps its natural size
        self.chat_scroll.setFrameShape(QFrame.NoFrame) # Removes the default sunken border around QScrollArea.
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        # The sidebar is narrow - we never want a horizontal scrollbar.
        self.chat_scroll.setStyleSheet("background: transparent;")

        # The actual container that holds the session items:
        self.chat_list_widget = QWidget()
        self.chat_list_widget.setStyleSheet("background: transparent;")
        self.chat_list_layout = QVBoxLayout(self.chat_list_widget)
        self.chat_list_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_list_layout.setSpacing(4)
        self.chat_list_layout.addStretch() # adds a expanding spacer at the bottom, pushing all session items to the top of the list
        
        self.chat_scroll.setWidget(self.chat_list_widget)
        # Tells QScrollArea: "this is the content you should scroll over"
        layout.addWidget(self.chat_scroll)

        # --- SETTINGS BUTTON ---
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {TEXT_MUTED};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
                text-align: left;
            }}
            QPushButton:hover{{
                background-color: {BG_SURFACE};
                color: {TEXT_PRIMARY};
                border-color: {ACCENT};
            }}
    """)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        layout.addWidget(self.settings_btn)

    def add_session_item(self, session, active=False):
        # Builds one session row widget and inserts it above the stretch.
        item = self._build_item(session, active)
        self.chat_list_layout.insertWidget(self.chat_list_layout.count() - 1, item)
        # inserts at index (count - 1) = just before the stretch spacer at the bottom

    def _build_item(self, session, active=False):
        # Builds a single session list entry - a QWidget containing:
        # [title label] [date • model] [✕ delete button]
        # This is not a QPushButton - it's a plain QWidget with a custom mousePressEvent
        item = QWidget()
        item.setMinimumWidth(0)
        item.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        # QSizePolicy.Expanding: grow to fill available horizontal space.
        # QSizePolicy.Preffered: use natural height, don't expand vertically.
        item.setObjectName(f"session_{session.id}")
        item.setCursor(Qt.PointingHandCursor)

        border_color = ACCENT if active else BORDER
        item.setStyleSheet(f"""
            QWidget {{
                background-color: {"#1f2535" if active else BG_SURFACE};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QWidget:hover {{
                background-color: #1f2535;
                border-color: {ACCENT};
            }}
    """)
        
        # --- ROW LAYOUT inside the item ----
        row = QHBoxLayout(item)
        row.setContentsMargins(8, 6, 4, 6)
        row.setSpacing(4)

        # TEXT COLUMN (title + meta stacked vertically)
        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        title_lbl = QLabel(session.title)
        title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; border: none;")
        title_lbl.setWordWrap(False) # False = text never wraps, it truncates if too long (clean look)
        title_lbl.setMaximumWidth(MENU_W_OPEN - 60) # reserve 60px for the delete button

        meta_lbl = QLabel(f"{session.created_at} • {session.model.split(':')[0]}")
        meta_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; border: none;")

        text_col.addWidget(title_lbl)
        text_col.addWidget(meta_lbl)
        row.addLayout(text_col, stretch=1)
        # stretch=1 means: give this layout as much horizontal space as possible, leaving only what the delete button needs

        # --- Delete Button ---
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(20, 20) # prevents the layout from resizing this button.
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT_MUTED};
                border: none;
                font-size: 11px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                color: #e05050;
                background: rgba(200,80,80,0.15);
            }}
    """)
        # rgba() in Qt stylesheets: red=200, green=80, blue=80, alpha=0.15 (15% opaque).
        del_btn.clicked.connect(lambda: self.session_deleted.emit(session.id))
        # Lambda captures the session.id from the current loop iteration.
        row.addWidget(del_btn)

        # ---Click handler---
        # overriding mousePressEvent directly on the widget object.
        # the lambda received the QMouseEvent 'e' but ignores it (no coordinates)
        item.mousePressEvent = lambda e: self.session_selected.emit(session)
        return item
    
    def rebuild_list(self, sessions, active_id, current_model):
        # Clears all session items and rebuilds the list from scratch/only shows sessions matching currently selected model.
        while self.chat_list_layout.count() > 1:
            item = self.chat_list_layout.takeAt(0) # takeAt(index) removes the item from the layout and returns it
            if item.widget():
                item.widget().deleteLater() # deleteLater() is PyQt5's safe way to destroy a widget.
        for session in reversed(sessions): # newest first
            if session.model == current_model:
                self.add_session_item(session, active=(session.id == active_id))
    
# CLASS: ChatPanel
# Main chat area - takes up the left half of the content region.
# Contains: title label, message display (QTextEdit), input box + send button.
class ChatPanel(QWidget):
    send_message = pyqtSignal(str) # Carries the message text as a string

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 14, 16)
        layout.setSpacing(10)

        # --- SESSION TITLE ---
        self.title_label = QLabel("[ HERMES-3 LOCAL SESSION ]")
        self.title_label.setObjectName("chatTitle")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.title_label)

        self.current_bot_name = "Hermes"

        # --- CHAT DISPLAY ---
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True) # can scroll and select, but cannot type.
        self.chat_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # both directions expanding, widget will grow to fill all space
        layout.addWidget(self.chat_display, stretch=1) # give this vertical widget extra space

        # --- INPUT ROW ---
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.input_box = QLineEdit()
        self.input_box.setObjectName("inputBox")
        self.input_box.setPlaceholderText("Send a message to Hermes...")
        self.input_box.setFixedHeight(44)
        self.input_box.returnPressed.connect(self._on_send) # fires when the user hits Enter
        input_row.addWidget(self.input_box, stretch=1)

        self.send_btn = QPushButton("Send ▶️")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setFixedHeight(44)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row) # adds a layout (not a widget) as a child of the parent layout

        self.setStyleSheet(f"""
            QLabel#chatTitle {{
                font-size: 20px;
            }}
            QTextEdit#chatDisplay {{
                background-color: {BG_PANEL};
            }}
    """)
        
    def _on_send(self):
        # Called when Enter is pressed or Send is clicked
        text = self.input_box.text().strip()
        if not text:
            return
        self._append_message("You", text, user=True)
        self.input_box.clear()
        self.send_message.emit(text) # Notifies MainWindow to start the AI worker

    def _append_message(self, sender, text, user=False):
        # Appends a styled HTML chat bubble to the QTextEdit
        bubble_bg = USER_BUBBLE if user else BOT_BUBBLE
        html = (
            f'<div style="margin: 8px 0; padding: 10px 14px; '
            f'background-color:{bubble_bg}; border-radius:6px;">'
            f'<span style="color:{ACCENT}; font-weight:bold; '
            f'font-size:12px; letter-spacing:2px;">{sender}</span>'
            f'<div style="color:{TEXT_PRIMARY}; font-size:14px; '
            f'line-height:1.6; margin-top:4px;">{text}</div>'
            f'</div>'
        )
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End) # Move to the very end of the document so we always append
        self.chat_display.setTextCursor(cursor) # Apply the moved cursor back to the widget
        self.chat_display.insertHtml(html)
        self.chat_display.insertPlainText('\n') # plain newline adds visual spacing between bubbles
        self.chat_display.moveCursor(QTextCursor.End) # scroll to bottom so the newest message is always visible

    def append_bot_message(self, text):
        # Public convenience method - called by MainWindow when AI responds.
        self._append_message(self.current_bot_name, text, user=False)

# CLASS: ImagePanel
# The right panel - displays the selected model's logo image, web search toggle checkbox and model dropdown selector
class ImagePanel(QWidget):
    model_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("imagePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(10)

        # --- CONTROLS ROW (toggle + dropdown) ---
        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        # --- WEB SEARCH TOGGLE ---
        self.web_toggle = QCheckBox(" Web Search")
        self.web_toggle.setChecked(False) # Checkbox is boolean, checked = search on, unchecked = off
        self.web_toggle.setStyleSheet(f"""
            QCheckBox {{
                color: {TEXT_MUTED};
                font-size: 12px;
                letter-spacing: 1px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 36px;
                height: 18px;
                border-radius: 9px;
                background-color: {BORDER};
                border: 1px solid {BORDER};
            }}
            QCheckBox::indicator:checked {{
                background-color: {ACCENT};
                border-color: {ACCENT};
            }}
    """) # border-radius: 9px on an 18px tall indicator creates a pill/toggle look.
        controls_row.addWidget(self.web_toggle)

        # --- MODEL SELECTOR DROPDOWN ---
        self.model_selector = QComboBox()
        self.model_selector.addItem("Hermes 3",     "hermes3") # AddItem(display_text, user_data) user_data is retrieved via .currentData()
        self.model_selector.addItem("Qwen 2.5 Coder", "qwen2.5-coder:14b")
        self.model_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {BG_SURFACE};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-family: 'Consolas', monospace;
            }}
            QComboBox:hover {{ border-color: {ACCENT}; }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {BG_SURFACE};
                color: {TEXT_PRIMARY};
                selection-background-color: {ACCENT};
                selection-color: {BG_DEEP};
                border: 1px solid {BORDER};
            }}
    """) # QComboBox::drop-down - the arrow area on the right side of the dropdown; QAbstractItemView - the popup list that appears when you click.
        self.model_selector.currentIndexChanged.connect(self._on_model_changed) # currentIndexChanged fires every time the selection changes.
        controls_row.addWidget(self.model_selector)

        layout.addLayout(controls_row)

        # --- MODEL IMAGE ---
        self.image_label = QLabel()
        self.image_label.setObjectName("modelImageLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setScaledContents(False) # False = manually scale the pixmap to fit. True = QLabel stretches it.
        self._load_image("hermes3")
        layout.addWidget(self.image_label, stretch=1)

    def _load_image(self, model_id):
        path = "Pictures_icons/Hermes_3_logo.png" if model_id == "hermes3" else "Pictures_icons/qwen_logo.jpg"
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.set_image(pixmap)
        else:
            self.image_label.setText("Image not found")
        self.image_label.setTextFormat(Qt.RichText)

    def set_image(self, pixmap):
        scaled = pixmap.scaled(
            800, 800,
            Qt.KeepAspectRatio, # Dont distort - preserve width/height ratio
            Qt.SmoothTransformation # Use bilinear filtering for a clean resize
        )
        self.image_label.setPixmap(scaled)

    def _on_model_changed(self, index):
        model_id = self.model_selector.itemData(index)
        self._load_image(model_id)
        self.model_changed.emit(model_id)

    def get_selected_model(self):
        return self.model_selector.currentData() # currentData() returns the user_data for the selected item
    
# CLASS: SettingsWindow
# QDialog popup window for adjusting per-model context length
# .exec() blocks the main window until the dialog is closed.

class SettingsWindow(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 300)

        self.settings = settings # Reference to the dict in MainWindow - changes here persist.

        layout = QVBoxLayout(self)

        # --- BACK BUTTON ---
        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedWidth(80)
        self.back_btn.clicked.connect(self.close) # close() on a QDialog hides it and returns from .exec()
        layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)

        # -- LABEL --
        self.label = QLabel("Context Length")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # -- SLIDER --
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(4)

        self.ctx_values = [4096, 8192, 16384, 32768, 65536]

        layout.addWidget(self.slider)

        # -- VALUE DISPLAY --
        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)

        self.current_model = self.parent()._current_model
         # self.parent() returns the widget passed as parent= in __init__, which is MainWindow.
        
        self._load_value()
        self.slider.valueChanged.connect(self._on_change)
        # valueChanged fires every time the slider moves (not just on release)
        
    def _load_value(self):
        key = "hermes3_ctx" if self.current_model == "hermes3" else "qwen_ctx"
        value = self.settings[key]
        index = self.ctx_values.index(value) # index() finds the position of a value in a list
        self.slider.setValue(index)
        self.value_label.setText(f"{value // 1024}K") # 8192 // 1024 = 8 -> "8K"

    def _on_change(self, index):
        value = self.ctx_values[index]
        self.value_label.setText(f"{value // 1024}K")
        key = "hermes3_ctx" if self.current_model == "hermes3" else "qwen_ctx"
        self.settings[key] = value
        self.parent()._save_settings() # Persists immediately on every slider move

# CLASS: MainWindow
# This is where all the panels are assembled and wired together

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("▶ LLM Launcher by OG")
        self.setWindowIcon(QIcon("Pictures_icons\\HERMES_LOGO_ICON.png"))
        self.resize(1920, 1080)
        # self.setStyleSheet(STYLESHEET) create later
        self._sidebar_open = False # tracks current sidebar state
        self._current_model = "hermes3"
        self._settings = {"hermes3_ctx": 8192, "qwen_ctx": 8192}

        # --- ROOT WIDGET ---
        root = QWidget()
        self.setCentralWidget(root)
        # QMainWindow requires a central widget - it's where the UI lives.
        # can't add addWidget to QMainWindow directly.

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- SIDEBAR ---
        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        # --- MAIN AREA ---
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- TOGGLE BAR (thin strip at the top for the ☰ button) ---
        toggle_bar = QWidget()
        toggle_bar.setFixedHeight(40)
        toggle_bar.setStyleSheet(f"background: {BG_DEEP};")

        toggle_bar_layout = QHBoxLayout(toggle_bar)
        toggle_bar_layout.setContentsMargins(8, 0, 0, 0)

        self.toggle_btn = QToolButton() # QToolButton is like QPushButton but designed for icon-style compact controls
        self.toggle_btn.setObjectName("toggleBtn")
        self.toggle_btn.setText("☰")
        self.toggle_btn.setFixedSize(36, 36)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        toggle_bar_layout.addWidget(self.toggle_btn)
        toggle_bar_layout.addStretch() # pushes the button to the LEFT - remaining space goes right

        main_layout.addWidget(toggle_bar)

        # --- CONTENT ROW (chat + divider + image) ---
        content_row = QHBoxLayout()
        content_row.setSpacing(0)
        content_row.setContentsMargins(0, 0, 0, 0)

        self.chat_panel = ChatPanel()
        self.chat_panel.send_message.connect(self._on_message)
        content_row.addWidget(self.chat_panel, stretch=1)

        # --- VERTICAL DIVIDER ---
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setFrameShadow(QFrame.Plain) # QFrame.Plain = flat line (no 3D sunked/raised effect)
        content_row.addWidget(divider)
        # No stretch - divider keeps its natural width

        self.image_panel = ImagePanel()
        content_row.addWidget(self.image_panel, stretch=1) # stretch=1 matches chat_panel's stretch=1, so they space equally
        self.image_panel.model_changed.connect(self._on_model_changed)

        main_layout.addLayout(content_row, stretch=1) # stretch=1 means the content_row fills all vertical space not used by toggle_bar

        root_layout.addWidget(main_area, stretch=1) # stretch=1 means the main_area fills all horizontal space not taken by the sidebar

        # --- SIDEBAR ANIMATION ---
        # b"maximumWidth" - the byte-string name of the property to animate

        self._anim = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self._anim.setDuration(300) # 300 milliseconds
        self._anim.setEasingCurve(QEasingCurve.InOutCubic) # InOutCubic: slow start -> fast middle -> slow end

        self._anim2 = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self._anim2.setDuration(300)
        self._anim2.setEasingCurve(QEasingCurve.InOutCubic)
        # Animate both min and max width together.
        # If you animate only maxWidth, the layout snaps from mix to max at the start.

        # --- WIRE SIDEBAR SIGNALS ---
        self.sidebar.new_chat_requested.connect(self._on_new_chat)
        self.sidebar.session_selected.connect(self._on_session_selected)
        self.sidebar.session_deleted.connect(self._on_session_deleted)
        self.sidebar.settings_requested.connect(self._open_settings)

    # --- SETTINGS ---
    def _open_settings(self):
        self.settings_window = SettingsWindow(self._settings, self)
        self.settings_window.exec() # .exec() opens the dialog and BLOCK until it's closed

    # --- MODEL SWITCH ---
    def _on_model_changed(self, model_id):
        self._current_model = model_id
        if model_id == "hermes3":
            self.chat_panel.title_label.setText("[ HERMES-3 LOCAL SESSION ]")
            self.chat_panel.input_box.setPlaceholderText("Send a message to Hermes...")
        else:
            self.chat_panel.title_label.setText("[ QWEN 2.5 CODER SESSION ]")
            self.chat_panel.input_box.setPlaceholderText("Send a message to Qwen...")
            self.chat_panel.current_bot_name = "Qwen"

    def toggle_sidebar(self):
        if self._sidebar_open:
            start, end = MENU_W_OPEN, MENU_W_CLOSED # Close: shrink to 0
        else:
            start, end = MENU_W_CLOSED, MENU_W_OPEN # Open: grow to 250

        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim2.setStartValue(start)
        self._anim2.setEndValue(end)

        self._anim.start()
        self._anim2.start() # Both animations run simultaneously

        self._sidebar_open = not self._sidebar_open

    # --- MESSAGE FLOW (stub - business logic stripped) ---
    def _on_message(self, text):
        pass # OllamaWorker thread

    def _on_new_chat(self):
        self.chat_panel.chat_display.clear()

    def _on_session_selected(self, session):
        self.chat_panel.chat_display.clear()

    def _on_session_deleted(self, session_id):
        pass # Session removal

    def _save_settings(self):
        pass # Writes self._settings to settings.json

if __name__ == "__main__":
    # Create application
    app = QApplication(sys.argv) # QApplication is the foundation, it initializes QT's rendering engine
    app.setStyle("Fusion") # Fusion is a Qt built-in Qt style - modern flat look

    # GLOBAL PALETTE
    # QPalette defines default colors for every Qt widget role
    # Stylesheets override these for specific widgets
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(BG_DEEP)) # background of windows and dialogs
    palette.setColor(QPalette.WindowText,      QColor(TEXT_PRIMARY)) # default text on windows

    palette.setColor(QPalette.Base,            QColor(BG_PANEL)) # background of text-entry widgets (QLineEdit, QTextEdit)
    palette.setColor(QPalette.AlternateBase,   QColor(BG_SURFACE)) # alternating row color  in QListView, QTreeView, etc.

    palette.setColor(QPalette.Text,            QColor(TEXT_PRIMARY)) # text color inside input widgets

    palette.setColor(QPalette.Button,          QColor(BG_SURFACE)) # background of buttons
    palette.setColor(QPalette.HighlightedText, QColor(BG_DEEP)) # text color on top of a highlight

    app.setPalette(palette)

    # --- CREATE AND SHOW WINDOW ---
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())





        






        
        







        

        



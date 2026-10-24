import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QTextEdit, QLineEdit, QPushButton, QLabel, QScrollArea, QFrame,
                             QSizePolicy, QToolButton, QCheckBox, QComboBox, QDialog, QSlider)
from PyQt5.QtCore import (Qt, QPropertyAnimation, QEasingCurve, QSize, pyqtSignal, QThread)
from PyQt5.QtGui import (QFont, QFontDatabase, QPixmap, QColor, QPalette, QIcon, QTextCursor)
import uuid
from dataclasses import dataclass, field
from datetime import datetime as dt
import json
import os
import pathlib
from docx import Document
from openpyxl import Workbook, load_workbook
import shutil
import re

def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

# Theme constants
BG_DEEP       = "#0d0d0f"
BG_PANEL      = "#13141a"
BG_SURFACE    = "#1a1b24"
BG_INPUT      = "#1e1f2b"
ACCENT        = "#c8882a"
ACCENT_HOVER  = "#e0a03a"
TEXT_PRIMARY  = "#e8e4d9"
TEXT_MUTED    = "#6b6a72"
BORDER        = "#2a2b38"
USER_BUBBLE   = "#1f2535"
BOT_BUBBLE    = "#161720"
MENU_W_OPEN   = 250
MENU_W_CLOSED = 0

STYLESHEET = f"""
    QMainWindow, QWidget{{
        background-color: {BG_DEEP};
        color: {TEXT_PRIMARY};
        font-family: 'Consolas', 'Courier New', monospace;
    }}
"""

@dataclass
class ChatSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Chat"
    model: str = "hermes3"
    history: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: dt.now().strftime("%b %d, %H:%M"))

class Sidebar(QWidget):
    settings_requested = pyqtSignal()
    session_selected = pyqtSignal(object) # emits ChatSession
    session_deleted = pyqtSignal(str) # emits session id
    new_chat_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(0)
        self.setMaximumWidth(MENU_W_CLOSED)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)

        # --- TOP Label ------
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

        # New chat button
        self.new_chat_btn = QPushButton("+  New Chat")
        self.new_chat_btn.setCursor(Qt.PointingHandCursor)
        self.new_chat_btn.setStyleSheet(f"""
            QPushButton{{
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
            QPushButton:hover{{ background-color: {ACCENT_HOVER}; }}
""")
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        layout.addWidget(self.new_chat_btn)

        # --- Chat list area ---
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setStyleSheet("background: transparent;")

        self.chat_list_widget = QWidget()
        self.chat_list_widget.setStyleSheet("background: transparent;")
        self.chat_list_layout = QVBoxLayout(self.chat_list_widget)
        self.chat_list_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_list_layout.setSpacing(4)
        self.chat_list_layout.addStretch()

        self.chat_scroll.setWidget(self.chat_list_widget)
        layout.addWidget(self.chat_scroll)
        self.chat_list_widget.setMinimumWidth(0)
        self.chat_scroll.setMidLineWidth(0)

        # --- Settings button ----
        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet(f"""
            QPushButton{{
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
        self.settings_btn.clicked.connect(self.settings_requested.emit) # create method later
        layout.addWidget(self.settings_btn)

    def add_session_item(self, session: ChatSession, active: bool = False):
        # Add a session entry to the sidebar list.
        item = self._build_item(session, active)
        # Insert before the stretch (last item)
        self.chat_list_layout.insertWidget(
            self.chat_list_layout.count() - 1, item
        )

    def _build_item(self, session: ChatSession, active: bool = False) -> QWidget:
        item = QWidget()
        item.setMinimumWidth(0)
        item.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        item.setObjectName(f"session_{session.id}")
        item.setCursor(Qt.PointingHandCursor)
        border_color = ACCENT if active else BORDER
        item.setStyleSheet(f"""
            QWidget{{
                background-color: {"#1f2535" if active else BG_SURFACE};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
            QWidget:hover{{
                background-color: #1f2535;
                border-color: {ACCENT};
            }}
""")
        row = QHBoxLayout(item)
        row.setContentsMargins(8, 6, 4, 6)
        row.setSpacing(4)

        # Text block
        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        title_lbl = QLabel(session.title)
        title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; border: none;")
        title_lbl.setWordWrap(False)
        title_lbl.setMaximumWidth(MENU_W_OPEN - 60)

        meta_lbl = QLabel(f"{session.created_at} • {session.model.split(':')[0]}")
        meta_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; border: none;")

        text_col.addWidget(title_lbl)
        text_col.addWidget(meta_lbl)
        row.addLayout(text_col, stretch=1)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton{{
                              background: transparent;
                              color: {TEXT_MUTED};
                              border: none;
                              font-size: 11px;
                              border-radius: 4px;
            }}
            QPushButton:hover{{
                color: #e05050;
                background: rgba(200,80,80,0.15);
            }}
""")
        del_btn.clicked.connect(lambda: self.session_deleted.emit(session.id))
        row.addWidget(del_btn)

        # Click on item body selects session
        item.mousePressEvent = lambda e: self.session_selected.emit(session)
        return item
    
    def rebuild_list(self, sessions: list, active_id: str, current_model: str):
        # Clear and repopulate the session list filtered by model.
        while self.chat_list_layout.count() > 1:
            item = self.chat_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for session in reversed(sessions): # newest first
            if session.model == current_model:
                self.add_session_item(session, active=(session.id == active_id))

class ChatPanel(QWidget):
    send_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 14, 16)
        layout.setSpacing(10)

        # --- Title ----
        self.tite_label = QLabel("[ HERMES-3 LOCAL SESSION ]")
        self.tite_label.setObjectName("chatTitle")
        self.tite_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.tite_label)
        self.current_bot_name = "Hermes"

        # --- Message Display ----
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        self.chat_display.setReadOnly(True)
        self.chat_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.chat_display, stretch=1)

        # --- Input row ----
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self.input_box = QLineEdit()
        self.input_box.setObjectName("inputBox")
        self.input_box.setObjectName("inputBox")
        self.input_box.setPlaceholderText("Send a message to Hermes...")
        self.input_box.setFixedHeight(44)
        self.input_box.returnPressed.connect(self._on_send)
        input_row.addWidget(self.input_box, stretch=1)

        self.send_btn = QPushButton("Send ▶️")
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setFixedHeight(44)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)

        self.setStyleSheet(f"""
            QLabel#chatTitle{{
                        font-size: 20px;
                           }}
            QTextEdit#chatDisplay{{
                        background-color: {BG_PANEL};
                           }}
""")

    def _on_send(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self._append_message("You", text, user=True)
        self.input_box.clear()
        self.send_message.emit(text)

    def _append_message(self, sender: str, text: str, user: bool = False):
        color = ACCENT if user else TEXT_PRIMARY
        bubble_bg = USER_BUBBLE if user else BOT_BUBBLE

        import re # Convert markdown-like code blocks to <pre> for readable indentation
        def replace_code(match):
            code = match.group(1).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return (f'<pre style="background-color:#0d0d0f; color:#e8e4d9; '
                f'padding:8px; border-left:2px solid {ACCENT}; '
                f'margin:4px 0; white-space:pre-wrap; font-size:13px;">'
                f'{code}</pre>')
        
        # Escape HTML in the text first, then restore code blocks
        safe_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        safe_text = re.sub(r'```(?:\w+)?\n?(.*?)```', replace_code, safe_text, flags=re.DOTALL)

        # Convert newlines to <br> for paragraph spacing
        safe_text = safe_text.replace('\n\n', '<br><br>').replace('\n', '<br>')

        html = (
            f'<div style="margin: 8px 0; padding: 10px 14px; '
            f'background-color:{bubble_bg}; border-radius:6px;">'
            f'<span style="color:{ACCENT}; font-weight:bold; '
            f'font-size:12px; letter-spacing:2px;">{sender}</span>'
            f'<div style="color:{TEXT_PRIMARY}; font-size:14px; '
            f'line-height:1.6; margin-top:4px;">{safe_text}</div>'
            f'</div>'
        )
        
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.insertHtml(html)
        self.chat_display.insertPlainText('\n') # spacing between bubbles
        self.chat_display.moveCursor(QTextCursor.End)

    def append_bot_message(self, text: str):
        self._append_message(self.current_bot_name, text, user=False)
        
class ImagePanel(QWidget):
    model_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("imagePanel")
        #self.setFixedWidth(800) # uncomment to set the divider split size manually

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(10)

        # --- Top controls row (toggle + dropdown) ---
        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        self.web_toggle = QCheckBox(" Web Search")
        self.web_toggle.setChecked(False)
        self.web_toggle.setStyleSheet(f"""
            QCheckBox{{
                color: {TEXT_MUTED};
                font-size: 12px;
                letter-spacing: 1px;
                spacing: 8px;
            }}
            QCheckBox::indicator{{
                width: 36px;
                height: 18px;
                border-radius: 9px;
                background-color: {BORDER};
                border: 1px solid {BORDER};
            }}
            QCheckBox::indicator:checked{{
                background-color: {ACCENT};
                border-color: {ACCENT};
            }}
""")
        controls_row.addWidget(self.web_toggle)

        # Model dropdown selector
        self.model_selector = QComboBox()
        self.model_selector.addItem("Hermes 3",        "hermes3")
        self.model_selector.addItem("Qwen 2.5 Coder",  "qwen2.5-coder:14b")
        self.model_selector.setStyleSheet(f"""
            QComboBox{{
                background-color: {BG_SURFACE};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-family: 'Consolas', monospace;
            }}
            QComboBox:hover{{ border-color: {ACCENT}; }}
            QComboBox:drop-down{{
                border: none; width: 20px;
            }}
            QComboBox QAbstractItemView{{
                background-color: {BG_SURFACE};
                color: {TEXT_PRIMARY};
                selection-background-color: {ACCENT};
                selection-color: {BG_DEEP};
                border: 1px solid {BORDER};
            }}
""")
        self.model_selector.currentIndexChanged.connect(self._on_model_changed)
        controls_row.addWidget(self.model_selector)

        layout.addLayout(controls_row)

        # --- Model image ----
        self.image_label = QLabel()
        self.image_label.setObjectName("modelImageLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setScaledContents(False)
        self._load_image("hermes3")
        layout.addWidget(self.image_label, stretch=1)

    def _on_model_changed(self, index):
        model_id = self.model_selector.itemData(index)
        self._load_image(model_id)
        self.model_changed.emit(model_id)

    def _load_image(self, model_id: str):
        if model_id == "hermes3":
            path = resource_path("Pictures_icons/Hermes_3_logo.png")
        else:
            path = resource_path("Pictures_icons/qwen_logo.jpg")
        
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.set_image(pixmap)
        else:
            self.image_label.setText(
                f'<span style="color:{ACCENT}; font-size:60px;">⚙</span><br>'
                f'<span style="color:{TEXT_MUTED}; font-size:11px;">'
                f'{model_id}<br>image not found</span>'
            )
            self.image_label.setTextFormat(Qt.RichText)

    def set_image(self, pixmap: QPixmap):
        scaled = pixmap.scaled(
            800, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)

    def get_selected_model(self) -> str:
        return self.model_selector.currentData()

class OllamaWorker(QThread): # Adding the Model
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, messages: list, web_enabled: bool = False, model: str = "hermes3", ctx: int = 8192):
        super().__init__()
        self.messages = messages # full conversation history
        self.web_enabled = web_enabled
        self.model = model
        self.ctx = ctx

    def run(self):
        try:
            import requests
            from datetime import datetime
            messages = self.messages.copy()

            now = datetime.now().strftime("%A, %B %d, %Y %H: %M")
            messages.insert(0, {
                "role": "system",
                "content": (
                    f"Today is {now}. This is your ground truth - do not question or search for the current date, "
                    "you already have it exactly."
                    "You are a professional AI assistant. Never use roleplay or actions like "
                    "*clears throat*, *speaks enthusiastically*, *performs web search*, or any similar "
                    "theatrical expressions. Respond directly and professionally at all times."
                    "If asked what model or AI you are, say you are running locally via Ollama and do not "
                    "claim to be GPT-4, ChatGPT, or any OpenAI product."
                )
            })
            if self.web_enabled:
                messages.insert(0, {
        "role": "system",
        "content": (
            f"Today's date is {now}. "
            "You have a web_search tool. You MUST call it before answering "
            "any question about current events, dates, news, or time-sensitive facts."
        )
    })
                messages.insert(1, {
        "role": "system",
        "content": (
            "You have a web_search tool. Use it for any question about "
            "current events, news, prices, or facts that may have changed. "
            "When reporting what people think or say, be specific — quote or paraphrase "
            "actual opinions from the search results, mention sources by name, "
            "and avoid vague summaries like 'people seem excited'. "
            "Give concrete details from what you actually found."
        )
    })
                messages.insert(2, {
        "role": "system",
        "content": (
            "When answering coding questions: always provide complete, runnable code — "
            "never truncate with '...' or 'rest of code here'. "
            "Include all imports. Explain what each key section does. "
            "If there are multiple approaches, show the best one and briefly mention alternatives. "
            "For errors, explain the root cause before showing the fix. "
            "Prefer modern, idiomatic solutions over outdated ones."
            "When writing code, especially UI/PyQt5: "
            "Use proper layouts with margins and spacing — never stack widgets blindly. "
            "Apply stylesheets for colors, fonts, and borders — never leave default grey Qt styling. "
            "Variable names must exactly match their declarations — double-check every reference. "
            "Never write placeholder code like 'add widgets here' or stub functions. "
            "Complete every function fully. Test the logic mentally before outputting. "
            "For PyQt5 specifically: always use QMainWindow as base, always call show(), "
            "always wrap in if __name__ == '__main__'."
        )
                })
            # Qwen commands and search results
            if self.web_enabled and self.model != "hermes3":
                last_user_msg = next(
                    (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
                )
                search_result = self._do_search(last_user_msg)
                messages.insert(0, {
                    "role": "system",
                    "content": (
                        f"The user has web search enabled. Here are real-time search results "
                        f"retrieved for their query. Use them to answer accurately:\n\n{search_result}"   
                    )
                })
            # --- Tool definition Ollama will know about ---
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": (
                "Search the internet for current, real-time information. "
                "For opinion/review questions, include 'reddit' in your query. "
                "For coding problems, include the language and error message in the query. "
                "For recent news, include the year. "
                "For documentation, include 'docs' or 'official' in the query. "
                "Always use specific, targeted queries — never vague ones."
            ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The search query to look up"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
            ] if (self.web_enabled and self.model == "hermes3") else []

            # Tools for write/edit files on PC
            file_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "create_file",
                        "description": (
                            "Create or overwrite a file on the user's Desktop. "
                            "Supports .txt, .py, .js, .html, .css, .md, .docx, .xlsx. "
                            "For docx and xlsx, content should be plain text — formatting is applied automatically. "
                            "Use subfolder to create the file inside a new folder on the Desktop."
                        ),
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "filename": {
                                    "type": "string",
                                    "description": "The file name including extension, e.g. 'report.docx'"
                                },
                                "content": {
                                    "type": "string",
                                    "description": "The text content to write into the file"
                                },
                                "subfolder": {
                                    "type": "string",
                                    "description": "Optional subfolder name to create inside the Desktop, e.g. 'MyProject'"
                                }
                            },
                            "required": ["filename", "content"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "description": "Read the contents of a file on the user's Desktop.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "filepath": {
                                    "type": "string",
                                    "description": "Path relative to the Desktop ONLY. Example: 'thoughts' or 'thoughts/file.docx'. NEVER include full absolute paths."
                                }
                            },
                            "required": ["filepath"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "delete_file",
                        "description": "Delete a file or a folder (including non-empty folders) on the user's Desktop.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "filepath": {
                                    "type": "string",
                                    "description": "Path relative to the Desktop to delete"
                                }
                            },
                            "required": ["filepath"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "list_files",
                        "description": "List files and folders on the user's Desktop or in a subfolder of it.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "subfolder": {
                                    "type": "string",
                                    "description": "Optional subfolder on the Desktop to list. Leave to list the Desktop itself."
                                }
                            },
                            "required": []
                        }
                    }
                }
            ] if self.model != "hermes3" else []

            if self.model != "hermes3":
                messages.insert(0, {
                    "role": "system",
                    "content": (
                        "You are a helpful coding assistant.\n\n"
                        "You have file system tools available: create_file, read_file, delete_file, list_files.\n\n"
                        "ONLY use these tools when the user EXPLICITLY asks to:\n"
                        "- Save, create, or write a file to their Desktop\n"
                        "- Delete a file or folder\n"
                        "- Read or list files\n\n"
                        "If the user asks you to 'write code', 'show me code', 'give me a script', or similar — "
                        "respond normally with the code in your message. Do NOT create a file unless they say "
                        "'save it', 'put it on my desktop', 'create a file', or similar explicit file intent.\n\n"
                        "When you DO need to create a file, respond ONLY with a JSON tool call:\n"
                        "{ \"name\": \"tool_name\", \"arguments\": { ... } }\n\n"
                        "Do NOT write Python code to do file operations — use the tools directly."
                    )
                })

            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": 2048,
                    "num_ctx": self.ctx
                }
            }

            all_tools = tools + file_tools
            if all_tools:
                payload["tools"] = all_tools

            response = requests.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=120
            )
            data = response.json()
            message = data.get("message", {})
            print("=== OLLAMA RESPONSE ===")
            print("finish_reason:", data.get("done_reason"))
            print("tool_calls:", message.get("tool_calls"))

            tool_calls = message.get("tool_calls", [])
            print("FINAL TOOL CALLS:", tool_calls)
            print("content:", message.get("content", "")[:100])
            print("=======================")

            # --- Fallback: Qwen returns tool calls as JSON in content ---
            if not tool_calls:
                content = message.get("content", "").strip()
                print("RAW CONTENT FOR FALLBACK:", repr(content[:200]))

                json_blocks = re.findall(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
                if not json_blocks:
                    json_blocks = [chunk.strip() for chunk in re.split(r'\n\s*\n', content) if chunk.strip()]

                for block in json_blocks:
                    try:
                        parsed = json.loads(block.strip())
                        if isinstance(parsed, list):
                            for item in parsed:
                                if isinstance(item, dict) and "name" in item:
                                    tool_calls.append({"function": {"name": item["name"], "arguments": item.get("arguments", {})}})
                        elif isinstance(parsed, dict) and "name" in parsed:
                            tool_calls.append({"function": {"name": parsed["name"], "arguments": parsed.get("arguments", {})}})
                    except json.JSONDecodeError:
                        pass

                if tool_calls:     
                    print(f"Parsed {len(tool_calls)} tool call(s) from content JSON")

            if tool_calls and (self.web_enabled or self.model != "hermes3"):
                messages.append(message)

                # Execute each tool call
                for tool_call in tool_calls:
                    fn = tool_call.get("function", {})
                    fn_name = fn.get("name")
                    fn_args = fn.get("arguments", {})

                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except:
                            fn_args = {}

                    if "file_path" in fn_args and "filename" not in fn_args:
                        fn_args["filename"] = fn_args["file_path"].split("/")[-1]

                    if "file_path" in fn_args and "subfolder" not in fn_args:
                        parts = fn_args["file_path"].split("/")
                        if len(parts) > 1:
                            fn_args["subfolder"] = parts[0]
                    # Optional fallback safety
                    if not fn_args.get("filename") and fn_name == "create_file":
                        return self.response_ready.emit("Error: filename missing in tool call")

                    if fn_name in ("create_file", "read_file", "delete_file", "list_files"):
                        result_content = self._execute_file_tool(fn_name, fn_args)

                    elif fn_name == "web_search":
                        result_content = self._do_search(fn_args.get("query", ""))
                    
                    else:
                        result_content = f"Unknown tool: {fn_name}"

                        # Send tool result back to Ollama
                    messages.append({
                        "role": "tool",
                        "content": result_content,
                        "tool_name": fn_name
                    })

                # --- Second call: Hermes now has the search results ---
                final_response = requests.post(
                    "http://localhost:11434/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "num_predict": 2048,
                            "num_ctx": self.ctx
                        }
                    },
                    timeout=120
                )
                result = final_response.json()["message"]["content"]

            else:
                # No tool call needed, use first response directly
                result = message.get("content", "").strip()

                if not result:
                    result = "[No response received - try again]"
                    self.response_ready.emit(result)
                    return

                # If response contains code, do a self-review pass
                if "```" in result:
                    messages.append({"role": "assistant", "content": result})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Review the code you just wrote. Check for: variable name errors, "
                            "missing imports, incomplete implementations, poor UI layout, and "
                            "hardcoded sizes under 800px. Fix ALL issues and return the complete "
                            "corrected code only, no explanations."
                        )
                    })
                    review_response = requests.post(
                        "http://localhost:11434/api/chat",
                        json={"model": self.model, "messages": messages, "stream": False},
                        json={
                            "model": self.model,
                            "messages": messages,
                            "stream": False,
                            "options": {
                                "num_predict": 2048,
                                "num_ctx": self.ctx
                            }
                        },
                        timeout=120
                    )
                    result = review_response.json()["message"]["content"]

            self.response_ready.emit(result)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def _do_search(self, query: str) -> str:
        try:
            from ddgs import DDGS
            results = []
            with DDGS() as ddgs:
                # General web
                for r in ddgs.text(query, max_results=6):
                    results.append(
                        f"Source: {r['href']}\n"
                        f"Title: {r['title']}\n"
                        f"Snippet: {r['body']}\n"
                    )
                # Reddit-specific search
                for r in ddgs.text(f"{query} site:reddit.com", max_results=5):
                    results.append(
                        f"[REDDIT] {r['href']}\n"
                        f"Title: {r['title']}\n"
                        f"Snippet: {r['body']}\n"
                )
                # Recent news (last week)
                for r in ddgs.text(query, max_results=4, timelimit="w"):
                    results.append(
                        f"[NEWS-RECENT] {r['href']}\n"
                        f"Title: {r['title']}\n"
                        f"Snippet: {r['body']}\n"
                )

                # --- Stack Overflow for coding questions ---
                if any(kw in query.lower() for kw in [
                    "code", "python", "error", "bug", "fix", "how to",
                    "function", "class", "import", "install", "library",
                    "javascript", "rust", "c++", "java", "sql", "api"
            ]):
                    for r in ddgs.text(f"{query} site:stackoverflow.com", max_results=4):
                        results.append(
                            f"[STACKOVERFLOW] {r['href']}\n"
                            f"Title: {r['title']}\n"
                            f"Snippet: {r['body']}\n"
                    )
                    for r in ddgs.text(f"{query} site:github.com", max_results=3):
                        results.append(
                            f"[GITHUB] {r['href']}\n"
                            f"Title: {r['title']}\n"
                            f"Snippet: {r['body']}\n"
                    )
            
            if results:
                return "=== Search Results ===\n\n" + "\n---\n".join(results)
            else:
                return "No results found."
        except Exception as e:
            return f"Web search failed: {str(e)}"
        
    def _execute_file_tool(self, fn_name: str, fn_args: dict) -> str:
        desktop = pathlib.Path.home() / "Desktop"
        onedrive = os.environ.get("OneDrive")
        if onedrive:
            onedrive_desktop = pathlib.Path(onedrive) / "Desktop"
            if onedrive_desktop.exists():
                desktop = onedrive_desktop

        def safe_path(relative: str) -> pathlib.Path:
            p = pathlib.Path(relative)
            # If absolute -> accept only if inside Desktop
            if p.is_absolute():
                if not str(p.resolve()).startswith(str(desktop.resolve())):
                    return None, "Access denied: path outside Desktop"
                
            # Resolve a relative path under Desktop, refusing to escape it.
            resolved = (desktop / relative).resolve()
            if not str(resolved).startswith(str(desktop.resolve())):
                return None, "Access denied: path outside Desktop"
            print("CREATING FILE AT:", resolved)
            return resolved, None
        
        if fn_name == "create_file":
            filename = fn_args.get("filename")
            subfolder = fn_args.get("subfolder", "")

            if not fn_args.get("filepath") and filename:
                fn_args["filepath"] = f"{subfolder}/{filename}" if subfolder else filename

            filepath = fn_args.get("filepath", "")
            content = fn_args.get("content", "")
            
            path, err = safe_path(filepath)
            if err:
                return err
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                ext = path.suffix.lower()
                if ext == ".docx":
                    doc = Document()
                    for line in content.split("\n"):
                        doc.add_paragraph(line)
                    doc.save(path)
                elif ext == ".xlsx":
                    wb = Workbook()
                    ws = wb.active
                    for i, line in enumerate(content.split("\n"), 1):
                        for j, cell in enumerate(line.split("\t"), 1):
                            ws.cell(row=i, column=j, value=cell)
                    wb.save(path)
                else:
                    path.write_text(content, encoding="utf-8")
                return f"File created succesfully: {path}"
            except Exception as e:
                return f"Failed to create file: {str(e)}"
            
        elif fn_name == "read_file":
            filepath = fn_args.get("filepath", "")
            path, err = safe_path(filepath)
            if err:
                return err
            try:
                ext = path.suffix.lower()
                if ext == ".docx":
                    doc = Document(path)
                    return "\n".join(p.text for p in doc.paragraphs)
                elif ext == ".xlsx":
                    wb = load_workbook(path)
                    ws = wb.active
                    rows = []
                    for row in ws.iter_rows(values_only=True):
                        rows.append("\t".join(str(c) if c else "" for c in row))
                    return "\n".join(rows)
                else:
                    return path.read_text(encoding="utf-8")
            except Exception as e:
                return f"Failed to read file: {str(e)}"
            
        elif fn_name == "delete_file":
            filepath = fn_args.get("filepath", "")
            path, err = safe_path(filepath)
            if err:
                return err
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                    return f"Folder deleted: {path}"
                else:
                    path.unlink()
                    return f"File deleted: {path}"
            except Exception as e:
                return f"Failed to delete: {str(e)}"
            
        elif fn_name == "list_files":
            subfolder = fn_args.get("subfolder", "")
            base = desktop / subfolder if subfolder else desktop
            path, err = safe_path(subfolder if subfolder else ".")
            if err:
                return err
            try:
                entries = sorted(base.iterdir(), key=lambda p: (p.is_file(), p.name))
                lines = [f"{'[DIR] ' if e.is_dir() else '[FILE]'} {e.name}" for e in entries]
                return "\n".join(lines) if lines else "Empty folder."
            except Exception as e:
                return f"Failed to list files: {str(e)}"
            
        return f"Unknown tool: {fn_name}"

class SettingsWindow(QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 300)

        self.settings = settings

        layout = QVBoxLayout(self)

        # --- Back button ---
        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedWidth(80)
        self.back_btn.clicked.connect(self.close)
        layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)

        # --- Label ---
        self.label = QLabel("Context Length")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        # --- Slider ---
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(4)

        # Map positions -> values
        self.ctx_values = [4096, 8192, 16384, 32768, 65536]

        layout.addWidget(self.slider)

        # --- Value display ---
        self.value_label = QLabel()
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)

        # Load current model value
        self.current_model = self.parent()._current_model
        self._load_value()

        self.slider.valueChanged.connect(self._on_change)

    def _load_value(self):
        key = "hermes3_ctx" if self.current_model == "hermes3" else "qwen_ctx"
        value = self.settings[key]

        index = self.ctx_values.index(value)
        self.slider.setValue(index)
        self.value_label.setText(f"{value // 1024}K")

    def _on_change(self, index):
        value = self.ctx_values[index]
        self.value_label.setText(f"{value // 1024}K")

        key = "hermes3_ctx" if self.current_model == "hermes3" else "qwen_ctx"
        self.settings[key] = value
        
        self.parent()._save_settings()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("▶ LLM Launcher by OG")
        self.setWindowIcon(QIcon(resource_path("Pictures_icons\\HERMES_LOGO_ICON.png")))
        self.resize(1920, 1080)
        self.setStyleSheet(STYLESHEET)

        self._worker = None
        self._sidebar_open = False
        self._current_model = "hermes3"
        self._settings = {
            "hermes3_ctx": 8192,
            "qwen_ctx": 8192
        }
        self._load_settings()

        # Session management
        self._sessions: list[ChatSession] = []
        self._active_session: ChatSession = self._create_new_session()

        # --- Root Widget ----
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Sidebar ----
        self.sidebar = Sidebar()
        root_layout.addWidget(self.sidebar)

        # --- Center + right area ----
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toggle button bar at the top
        toggle_bar = QWidget()
        toggle_bar.setFixedHeight(40)
        toggle_bar.setStyleSheet(f"background: {BG_DEEP};")
        toggle_bar_layout = QHBoxLayout(toggle_bar)
        toggle_bar_layout.setContentsMargins(8, 0, 0, 0)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setObjectName("toggleBtn")
        self.toggle_btn.setText("☰")
        self.toggle_btn.setFixedSize(36, 36)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        toggle_bar_layout.addWidget(self.toggle_btn)
        toggle_bar_layout.addStretch()
        main_layout.addWidget(toggle_bar)

        # Content row: chat + image
        content_row = QHBoxLayout()
        content_row.setSpacing(0)
        content_row.setContentsMargins(0, 0, 0, 0)

        self.chat_panel = ChatPanel()
        self.chat_panel.send_message.connect(self._on_message)
        content_row.addWidget(self.chat_panel, stretch=1)

        # Vertical divider
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setFrameShadow(QFrame.Plain)
        content_row.addWidget(divider)

        self.image_panel = ImagePanel()
        content_row.addWidget(self.image_panel, stretch=1)
        self.image_panel.model_changed.connect(self._on_model_changed)

        main_layout.addLayout(content_row, stretch=1)
        root_layout.addWidget(main_area, stretch=1)

        # --- Sidebar animation ----
        self._anim = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._anim2 = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self._anim2.setDuration(300)
        self._anim2.setEasingCurve(QEasingCurve.InOutCubic)

        # Sidebar signals
        self.sidebar.new_chat_requested.connect(self._on_new_chat)
        self.sidebar.session_selected.connect(self._on_session_selected)
        self.sidebar.session_deleted.connect(self._on_session_deleted)
        self.sidebar.settings_requested.connect(self._open_settings)

        # Load persisted sessions from disk
        self._load_sessions()

    def _open_settings(self):
        self.settings_window = SettingsWindow(self._settings, self)
        self.settings_window.exec()

    # --- Session helpers --------------
    def _create_new_session(self) -> ChatSession:
        session = ChatSession(model=self._current_model if hasattr(self, '_current_model') else "hermes3")
        self._sessions.append(session) if hasattr(self, '_sessions') else None
        return session
    
    def _save_active_session(self):
        # Persistent current conversation into the active session object.
        self._active_session.history = list(self._active_session.history)

    def _refresh_sidebar(self):
        self.sidebar.rebuild_list(
            self._sessions, self._active_session.id, self._current_model
        )

    def _auto_tite(self, text: str):
        # Use first user message as session title (trimmed).
        if self._active_session.title == "New Chat":
            self._active_session.title = text[:40] + ("⋯" if len(text) > 40 else "")
            self._refresh_sidebar()

    # --- Session handlers -------------
    def _on_new_chat(self):
        self._save_active_session()
        self._active_session = ChatSession(model=self._current_model)
        self._sessions.append(self._active_session)
        self.chat_panel.chat_display.clear()
        self._refresh_sidebar()

    def _on_session_selected(self, session: ChatSession):
        self._save_active_session()
        self._active_session = session

        # Switch model if needed
        if session.model != self._current_model:
            idx = self.image_panel.model_selector.findData(session.model)
            if idx >= 0:
                self.image_panel.model_selector.setCurrentIndex(idx)

        # Restore chat display
        self.chat_panel.chat_display.clear()
        for msg in session.history:
            if msg["role"] == "user":
                self.chat_panel._append_message("You", msg["content"], user=True)
            elif msg["role"] == "assistant":
                self.chat_panel._append_message(self.chat_panel.current_bot_name, msg["content"], user=False)

        self._refresh_sidebar()

    def _on_session_deleted(self, session_id: str):
        self._sessions = [s for s in self._sessions if s.id != session_id]

        # If delete the active session -> start a new one
        if self._active_session.id == session_id:
            self._active_session = ChatSession(model=self._current_model)
            self._sessions.append(self._active_session)
            self.chat_panel.chat_display.clear()

        self._save_sessions()
        self._refresh_sidebar()

    # SETTINGS -----------------------
    def _settings_file(self) -> str:
        base = (
            os.path.dirname(sys.executable)
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__))
        )

        return os.path.join(base, "settings.json")
    
    def _load_settings(self): # Load settings on startup
        path = self._settings_file()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._settings.update(data)
        except Exception as e:
            print(f"Failed to load settings: {e}")

    def _save_settings(self):
        try:
            with open(self._settings_file(), "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    # --- Model switch ---------
    def _on_model_changed(self, model_id: str):
        self._current_model = model_id

        # Update active session model if it hasn't been used yet
        if not self._active_session.history:
            self._active_session.model = model_id

        if model_id == "hermes3":
            self.chat_panel.tite_label.setText("[ HERMES-3 LOCAL SESSION ]")
            self.chat_panel.input_box.setPlaceholderText("Send a message to Hermes...")
            self.chat_panel.current_bot_name = "Hermes"
        else:
            self.chat_panel.tite_label.setText("[ QWEN 2.5 CODER SESSION ]")
            self.chat_panel.input_box.setPlaceholderText("Send a message to Qwen...")
            self.chat_panel.current_bot_name = "Qwen"
        self._refresh_sidebar()

    # --- Sidebar toggle ----
    def toggle_sidebar(self):
        if self._sidebar_open:
            start, end = MENU_W_OPEN, MENU_W_CLOSED
        else:
            start, end = MENU_W_CLOSED, MENU_W_OPEN

        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim2.setStartValue(start)
        self._anim2.setEndValue(end)

        self._anim.start()
        self._anim2.start()

        self._sidebar_open = not self._sidebar_open

        print(f"Toggling sidebar: open={self._sidebar_open}, target={MENU_W_OPEN}")

    # --- Message flow ----
    def _on_message(self, text: str):
        self._auto_tite(text)
        # Add user message to history
        self._active_session.history.append({"role": "user", "content": text})

        # Disable input while waiting
        self.chat_panel.input_box.setEnabled(False)
        self.chat_panel.send_btn.setEnabled(False)
        self.chat_panel.send_btn.setText("⌛ Thinking...")
        # Thinking indicator
        self._thinking_cursor_pos = self.chat_panel.chat_display.document().characterCount()
        self.chat_panel.append_bot_message("...")
        self._thinking_inserted = True

        # Spin up the worker
        web_enabled = self.image_panel.web_toggle.isChecked()
        model = self.image_panel.get_selected_model()
        ctx = self._settings["hermes3_ctx"] if model == "hermes3" else self._settings["qwen_ctx"]

        # Kill previous worker completely before spawning new one
        if self._worker is not None:
            self._worker.response_ready.disconnect()
            self._worker.error_occurred.disconnect()
            self._worker.quit()
            self._worker.wait()
            self._worker = None

        self._worker = OllamaWorker(self._active_session.history.copy(), web_enabled, model, ctx)
        self._worker.response_ready.connect(self._on_response, Qt.UniqueConnection)
        self._worker.error_occurred.connect(self._on_error, Qt.UniqueConnection)
        self._worker.start()

    def _on_response(self, text: str):
        self._remove_thinking_bubble()
        self.chat_panel.append_bot_message(text)
        # Add assistant reply to history
        self._active_session.history.append({"role": "assistant", "content": text})
        self._save_sessions()
        self._re_enable_input()

    def _on_error(self, error: str):
        self._remove_thinking_bubble()
        self.chat_panel.append_bot_message(f"[Error: {error}]")
        self._save_sessions()
        self._re_enable_input()

    def _remove_thinking_bubble(self):
        if not getattr(self, '_thinking_inserted', False):
            return
        # Move to end, select the last paragraph block and delete it
        display = self.chat_panel.chat_display
        display.setReadOnly(False)
        cursor = display.textCursor()
        cursor.setPosition(self._thinking_cursor_pos - 1)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        # Select all content from the last inserted block back
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        display.setReadOnly(True)
        self._thinking_inserted = False

    def _re_enable_input(self):
        self.chat_panel.input_box.setEnabled(True)
        self.chat_panel.send_btn.setEnabled(True)
        self.chat_panel.send_btn.setText("Send ▶️")

    # --- Adding persistent memmory (memmory exists after restarting the app) -----
    def _sessions_file(self) -> str:
        base = (
            os.path.dirname(sys.executable)
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__))
        )

        return os.path.join(base, "sessions.json")
    
    def _save_sessions(self):
        data = []
        for s in self._sessions:
            # Don't save empty sessions with no history
            if not s.history:
                continue
            data.append({
                "id": s.id,
                "title": s.title,
                "model": s.model,
                "history": s.history,
                "created_at": s.created_at
            })
        try:
            with open(self._sessions_file(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save sessions: {e}")

    def _load_sessions(self):
        path = self._sessions_file()
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._sessions.clear()
            for item in data:
                s = ChatSession(
                    id=item["id"],
                    title=item["title"],
                    model=item["model"],
                    history=item["history"],
                    created_at=item["created_at"]
                )
                self._sessions.append(s)

            # Start with a fresh session on top, don't auto-restore last
            self._active_session = ChatSession(model=self._current_model)
            self._sessions.append(self._active_session)
            self._refresh_sidebar()
        except Exception as e:
            print(f"Failed to load sessions: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(BG_DEEP))
    palette.setColor(QPalette.WindowText,      QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Base,            QColor(BG_PANEL))
    palette.setColor(QPalette.AlternateBase,   QColor(BG_SURFACE))
    palette.setColor(QPalette.Text,            QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Button,          QColor(BG_SURFACE))
    palette.setColor(QPalette.ButtonText,      QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Highlight,       QColor(ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor(BG_DEEP))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
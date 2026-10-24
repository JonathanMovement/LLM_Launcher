import sys
import requests
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton)
from PyQt5.QtCore import QThread, pyqtSignal

class OllamaWorker(QThread):
    response_ready = pyqtSignal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "hermes3",
                "messages": [{"role": "user", "content": self.prompt}],
                "stream": False
            }
        )
        result = response.json()["message"]["content"]
        self.response_ready.emit(result)

class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hermes3 Local Chat")
        layout = QVBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Type a message...")
        layout.addWidget(self.input_box)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        layout.addWidget(self.send_btn)

        self.setLayout(layout)

    def send_message(self):
        prompt = self.input_box.text().strip()
        if not prompt:
            return
        self.chat_display.append(f"You: {prompt}")
        self.input_box.clear()
        self.send_btn.setEnabled(False)

        self.worker = OllamaWorker(prompt)
        self.worker.response_ready.connect(self.display_response)
        self.worker.start()

    def display_response(self, text):
        self.chat_display.append(f"Hermes: {text}\n")
        self.send_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec_())
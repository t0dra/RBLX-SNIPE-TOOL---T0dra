import sys
import random
import string
import requests
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSpinBox, QCheckBox, QPushButton, QListWidget, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QPoint, QEasingCurve, QTimer

class Notification(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.layout = QHBoxLayout(self)
        self.label = QLabel()
        self.layout.addWidget(self.label)
        self.setStyleSheet("""
            QWidget {
                background-color: #000;
                color: #39ff14;
                border: 1.5px solid #39ff14;
                border-radius: 5px;
                font-family: 'Consolas', 'Menlo', 'Courier', monospace;
                font-size: 12px;
                padding: 5px 10px;
            }
        """)
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.animation.setDuration(300)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_animated)
        self.hide()

    def show_message(self, text):
        self.label.setText(text)
        self.adjustSize()
        parent_widget = self.parent()
        if not parent_widget: return
        start_pos = QPoint((parent_widget.width() - self.width()) // 2, -self.height())
        end_pos = QPoint((parent_widget.width() - self.width()) // 2, 10)
        self.move(start_pos)
        self.show()
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()
        self.hide_timer.start(2500)

    def hide_animated(self):
        self.hide_timer.stop()
        start_pos = self.pos()
        end_pos = QPoint(start_pos.x(), -self.height())
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.finished.connect(self.hide)
        self.animation.start()

class UsernameWorker(QThread):
    username_found = pyqtSignal(str)
    checking_username = pyqtSignal(str)
    network_error = pyqtSignal(str)
    stopped = False

    def __init__(self, length, use_upper, use_lower, use_digits):
        super().__init__()
        self.length = length
        self.use_upper = use_upper
        self.use_lower = use_lower
        self.use_digits = use_digits
        self.stopped = False
        self.session = requests.Session()

    def _refresh_csrf(self):
        try:
            response = self.session.post("https://auth.roblox.com/v2/login", timeout=10)
            if "x-csrf-token" in response.headers:
                self.session.headers["x-csrf-token"] = response.headers["x-csrf-token"]
                return True
        except requests.RequestException:
            pass
        return False

    def _is_available(self, username):
        url = "https://auth.roblox.com/v1/usernames/validate"
        params = {
            "username": username,
            "birthday": "2000-01-01T00:00:00.000Z"
        }
        try:
            response = self.session.get(url, params=params, timeout=5)
            if response.status_code == 403: # CSRF token failure
                if not self._refresh_csrf():
                    return False # Could not refresh token
                response = self.session.get(url, params=params, timeout=5) # Retry
            
            return response.status_code == 200 and response.json().get("code") == 0
        except requests.RequestException:
            return False

    def run(self):
        if not self._refresh_csrf():
            self.network_error.emit("Failed to get security token.\nCheck internet connection and try again.")
            return
            
        chars = ""
        if self.use_upper: chars += string.ascii_uppercase
        if self.use_lower: chars += string.ascii_lowercase
        if self.use_digits: chars += string.digits
        if not chars: return

        checked = set()
        while not self.stopped:
            uname = ''.join(random.choices(chars, k=self.length))
            if uname in checked: continue
            checked.add(uname)
            self.checking_username.emit(uname)
            if self._is_available(uname):
                self.username_found.emit(uname)
            time.sleep(0.8)

    def stop(self):
        self.stopped = True

class UsernameCheckerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.is_searching = False
        self.setupUI()
        self.notification = Notification(self)

    def setupUI(self):
        self.setWindowTitle('RBLX SNIPE TOOL - T0dra')
        self.setStyleSheet("""
            QWidget {
                background-color: #000;
                color: #39ff14;
                font-family: 'Consolas', 'Menlo', 'Courier', monospace;
                font-size: 14px;
            }
            QLabel#statusLabel {
                color: #888;
                font-size: 12px;
                padding-right: 10px;
            }
            QLabel {
                color: #39ff14;
                font-weight: bold;
            }
            QSpinBox, QListWidget {
                background-color: #000;
                color: #39ff14;
                border: 1.5px solid #39ff14;
                font-weight: bold;
            }
            QPushButton {
                background-color: #000;
                color: #39ff14;
                border: 2px solid #39ff14;
                border-radius: 7px;
                padding: 5px 18px;
                font-weight: bold;
            }
            QPushButton:pressed {
                background-color: #39ff14;
                color: #000;
            }
            QCheckBox {
                spacing: 10px;
                font-weight: bold;
                color: #555;
            }
            QCheckBox:checked {
                color: #39ff14;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2.5px solid #555;
                background: #000;
            }
            QCheckBox::indicator:checked {
                border: 2.5px solid #39ff14;
                background: #39ff14;
            }
            QListWidget {
                selection-background-color: #222;
                selection-color: #39ff14;
            }
        """)
        layout = QVBoxLayout()
        input_row = QHBoxLayout()
        layout.addLayout(input_row)
        input_row.addWidget(QLabel("Username Length:"))
        self.length_box = QSpinBox()
        self.length_box.setRange(3, 20)
        self.length_box.setValue(20)
        input_row.addWidget(self.length_box)
        input_row.addStretch()
        self.uppercase = QCheckBox("A-Z")
        self.uppercase.setChecked(True)
        input_row.addWidget(self.uppercase)
        self.lowercase = QCheckBox("a-z")
        self.lowercase.setChecked(True)
        input_row.addWidget(self.lowercase)
        self.digits = QCheckBox("0-9")
        self.digits.setChecked(True)
        input_row.addWidget(self.digits)
        
        status_row = QHBoxLayout()
        self.status_label = QLabel("Status: Idle")
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addLayout(status_row)
        
        btn_row = QHBoxLayout()
        layout.addLayout(btn_row)
        self.search_btn = QPushButton("Start Search")
        self.search_btn.clicked.connect(self.toggle_search)
        btn_row.addWidget(self.search_btn)
        self.clear_btn = QPushButton("Clear Results")
        self.clear_btn.clicked.connect(self.on_clear)
        btn_row.addWidget(self.clear_btn)
        
        layout.addWidget(QLabel("Available Usernames:"))
        self.listbox = QListWidget()
        self.listbox.itemClicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.listbox)
        self.setLayout(layout)

    def toggle_search(self):
        if not self.is_searching: self.start_search()
        else: self.stop_search()

    def start_search(self):
        use_any = self.uppercase.isChecked() or self.lowercase.isChecked() or self.digits.isChecked()
        if not use_any:
            QMessageBox.warning(self, "Error", "Select at least one character type!")
            return

        self.is_searching = True
        self.search_btn.setText("Stop Search")
        self.worker = UsernameWorker(
            self.length_box.value(),
            self.uppercase.isChecked(),
            self.lowercase.isChecked(),
            self.digits.isChecked()
        )
        self.worker.username_found.connect(self.add_username)
        self.worker.checking_username.connect(self.update_status)
        self.worker.network_error.connect(self.on_network_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def stop_search(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        
    def on_worker_finished(self):
        self.is_searching = False
        self.search_btn.setText("Start Search")
        self.status_label.setText("Status: Idle")

    def on_network_error(self, message):
        QMessageBox.critical(self, "Network Error", message)
        self.on_worker_finished()

    def add_username(self, uname):
        self.listbox.addItem(uname)
        self.listbox.scrollToBottom()

    def update_status(self, uname):
        self.status_label.setText(f"Checking: {uname}")

    def on_clear(self):
        self.listbox.clear()

    def copy_to_clipboard(self, item):
        username = item.text()
        clipboard = QApplication.clipboard()
        clipboard.setText(username)
        self.notification.show_message(f"Copied '{username}'")
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.notification.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = UsernameCheckerGUI()
    ui.resize(520, 450)
    ui.show()
    sys.exit(app.exec_())
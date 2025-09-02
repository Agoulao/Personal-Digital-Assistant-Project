import sys
import threading
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer

from core.voice_recognition import SpeechRecognitionModule
from core.tts import TTSModule
from core.backend import Backend
from config import Config 

# Custom Widget for a chat bubble
class ChatBubble(QtWidgets.QWidget):
    def __init__(self, text, is_user, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.text_label = QtWidgets.QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse) # Allow text selection

        # Set specific styles for the bubble
        if self.is_user:
            self.text_label.setStyleSheet(
                "background-color: #007bff;"  # Blue for user
                "color: white;"
                "border-radius: 10px;"
                "padding: 5px 14px;" 
                "margin-left: 30%;" 
                "font-size: 14px;" 
            )
            self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter) # Align text to the left
        else:
            self.text_label.setStyleSheet(
                "background-color: #4a4a4a;"  # Dark grey for assistant
                "color: white;"
                "border-radius: 10px;"
                "padding: 5px 14px;" 
                "margin-right: 30%;" # Push assistant bubble to the left
                "font-size: 14px;" 
            )
            self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter) # Align text to the left

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5) # Added margins for spacing from edges

        if self.is_user:
            # Spacer on the left to push the bubble right
            layout.addStretch()
            layout.addWidget(self.text_label)
        else:
            layout.addWidget(self.text_label)
            # Spacer on the right to push the bubble left
            layout.addStretch()

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Minimum)


class SignalBridge(QObject):
    update_text = pyqtSignal(str, bool)  # text, is_user
    replace_last = pyqtSignal(str)       # text for last assistant message
    speak_text = pyqtSignal(str)
    reenable_input = pyqtSignal()
    clear_chat = pyqtSignal()

class AssistantGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_listening = False
        self.auto_speak = False
        self.current_theme = 'dark'

        # Core modules
        self.tts = TTSModule()
        self.voice = SpeechRecognitionModule()
        self.backend = Backend(self.voice, self.tts)

        # Signals
        self.signals = SignalBridge()
        self.signals.update_text.connect(self.append_chat)
        self.signals.replace_last.connect(self.replace_last_assistant)
        self.signals.speak_text.connect(self.tts.speak)
        self.signals.reenable_input.connect(self.reenable_ui)
        self.signals.clear_chat.connect(self.clear_console)

        # Animation timer
        self.dot_count = 0
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(500)
        self.anim_timer.timeout.connect(self.update_dots)

        self.build_ui()
        self.apply_theme(self.current_theme)
        self.setup_ui_text()
        self.populate_input_devices()

    def build_ui(self):
        self.resize(Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT) # Use Config for window size
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Chat Display (now a QScrollArea containing a QVBoxLayout)
        self.chat_scroll_area = QtWidgets.QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Hide horizontal scrollbar
        self.chat_display_content = QtWidgets.QWidget()
        self.chat_display_layout = QtWidgets.QVBoxLayout(self.chat_display_content)
        self.chat_display_layout.setAlignment(Qt.AlignTop) # Align messages to the top
        self.chat_display_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_display_layout.setSpacing(5) # Spacing between bubbles
        self.chat_scroll_area.setWidget(self.chat_display_content)
        layout.addWidget(self.chat_scroll_area, stretch=1)

        # Input
        self.text_input = QtWidgets.QLineEdit()
        self.text_input.setPlaceholderText("Type a message and press Enter to submit…")
        self.text_input.returnPressed.connect(self.submit_text)
        layout.addWidget(self.text_input)

        # Device & volume
        settings_layout = QtWidgets.QHBoxLayout()
        settings_layout.setSpacing(20)
        dev_layout = QtWidgets.QVBoxLayout()
        dev_layout.setSpacing(5)
        self.input_device_label = QtWidgets.QLabel("Input Device:")
        dev_layout.addWidget(self.input_device_label)
        self.input_device = QtWidgets.QComboBox()
        dev_layout.addWidget(self.input_device)
        settings_layout.addLayout(dev_layout, stretch=1)
        vol_layout = QtWidgets.QVBoxLayout()
        vol_layout.setSpacing(5)
        self.volume_label = QtWidgets.QLabel("Volume")
        vol_layout.addWidget(self.volume_label)
        self.volume_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(Config.VOICE_VOLUME * 100)) # Use Config for initial volume
        self.volume_slider.valueChanged.connect(self.on_volume_change)
        vol_layout.addWidget(self.volume_slider)
        settings_layout.addLayout(vol_layout, stretch=1)
        layout.addLayout(settings_layout)

        # Actions
        action_layout = QtWidgets.QHBoxLayout()
        action_layout.setSpacing(10)
        self.listen_button = QtWidgets.QPushButton()
        self.listen_button.clicked.connect(self.toggle_listening)
        action_layout.addWidget(self.listen_button)
        self.auto_speak_checkbox = QtWidgets.QCheckBox("TTS")
        self.auto_speak_checkbox.stateChanged.connect(self.on_auto_speak_toggle)
        action_layout.addWidget(self.auto_speak_checkbox)
        self.clear_button = QtWidgets.QPushButton("Clear Console")
        self.clear_button.clicked.connect(lambda: self.signals.clear_chat.emit())
        action_layout.addWidget(self.clear_button)
        layout.addLayout(action_layout)

        # Theme menu
        menubar = self.menuBar()
        self.menu_theme = menubar.addMenu("Theme")
        self.action_dark = self.menu_theme.addAction("Dark Mode")
        self.action_light = self.menu_theme.addAction("Light Mode")
        self.action_dark.triggered.connect(lambda: self.change_theme('dark'))
        self.action_light.triggered.connect(lambda: self.change_theme('light'))

    def apply_dark_theme(self):
        QtWidgets.QApplication.setStyle("Fusion")
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.WindowText, Qt.white)
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ToolTipBase, Qt.white)
        palette.setColor(QtGui.QPalette.ToolTipText, Qt.white)
        palette.setColor(QtGui.QPalette.Text, Qt.white)
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ButtonText, Qt.white)
        palette.setColor(QtGui.QPalette.BrightText, Qt.red)
        palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.HighlightedText, Qt.white)
        QtWidgets.QApplication.setPalette(palette)
        # Apply theme to the scroll area and its content
        self.chat_scroll_area.setStyleSheet("background-color: #363636;")
        self.chat_display_content.setStyleSheet("background-color: #363636;")

    def apply_light_theme(self):
        QtWidgets.QApplication.setStyle("Fusion")
        QtWidgets.QApplication.setPalette(QtWidgets.QApplication.style().standardPalette())
        # Apply theme to the scroll area and its content
        self.chat_scroll_area.setStyleSheet("background-color: white;")
        self.chat_display_content.setStyleSheet("background-color: white;")

    def apply_theme(self, theme):
        if theme == 'dark': self.apply_dark_theme()
        else: self.apply_light_theme()

    def setup_ui_text(self):
        self.update_listen_button()
        self.setWindowTitle(Config.APP_NAME) # Set window title from Config

    def change_theme(self, theme):
        self.current_theme = theme
        self.apply_theme(theme)

    def populate_input_devices(self):
        import speech_recognition as sr
        try:
            names = sr.Microphone.list_microphone_names()
            mics = [n for n in names if "mic" in n.lower()]
        except:
            mics = []
        if not mics and 'names' in locals():
            mics = names
        self.input_device.clear()
        self.input_device.addItems(mics or ["Default Microphone"])

    def on_volume_change(self, value): self.tts.set_volume(value / 100.0)
    def on_auto_speak_toggle(self, state): self.auto_speak = (state == Qt.Checked)

    def update_listen_button(self):
        text = "Stop Listening" if self.is_listening else "Start Listening"
        self.listen_button.setText(text)

    def toggle_listening(self):
        if not self.is_listening: self.start_listening()
        else: self.stop_listening()

    def submit_text(self):
        text = self.text_input.text().strip()
        if not text: return
        self.signals.update_text.emit(text, True) # True for user message
        self.text_input.setEnabled(False)
        self.text_input.setStyleSheet("background-color: #2e2e2e; color: #777;")
        self.listen_button.setEnabled(False)
        self.listen_button.setStyleSheet("background-color: #555; color: #aaa;")
        self.dot_count = 0
        self.signals.update_text.emit(".", False) # False for assistant message
        self.anim_timer.start()
        threading.Thread(target=self.handle_text_submission, args=(text,), daemon=True).start()

    def handle_text_submission(self, text):
        response = self.backend.process_command(text)
        if self.anim_timer.isActive(): self.anim_timer.stop()
        self.signals.replace_last.emit(response)
        if self.auto_speak and response: self.signals.speak_text.emit(response)
        self.signals.reenable_input.emit()

    def start_listening(self):
        self.is_listening = True
        self.update_listen_button()
        self.text_input.setEnabled(False)
        self.text_input.setStyleSheet("background-color: #2e2e2e; color: #777;")
        self.listen_thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.listen_thread.start()

    def stop_listening(self):
        self.is_listening = False
        self.update_listen_button()
        self.text_input.setEnabled(True)
        self.text_input.setStyleSheet("")
        self.listen_button.setEnabled(True)
        self.listen_button.setStyleSheet("")
        self.text_input.setFocus()
        if self.anim_timer.isActive(): self.anim_timer.stop()

    def listen_loop(self):
        while self.is_listening:
            cmd = self.voice.listen()
            if not self.is_listening: break
            self.signals.update_text.emit(cmd, True) # True for user message
            self.dot_count = 0
            self.signals.update_text.emit(".", False) # False for assistant message
            self.anim_timer.start()
            response = self.backend.process_command(cmd)
            if self.anim_timer.isActive(): self.anim_timer.stop()
            self.signals.replace_last.emit(response)
            if self.auto_speak and response: self.signals.speak_text.emit(response)
            self.stop_listening()
            break
            

    def update_dots(self):
        # Get the last item in the chat_display_layout, which should be the assistant's message bubble
        if self.chat_display_layout.count() > 0:
            last_bubble_widget = self.chat_display_layout.itemAt(self.chat_display_layout.count() - 1).widget()
            if isinstance(last_bubble_widget, ChatBubble) and not last_bubble_widget.is_user:
                current_text = last_bubble_widget.text_label.text()
                self.dot_count = (self.dot_count + 1) % 3
                new_dots = '.' * (self.dot_count + 1)
                last_bubble_widget.text_label.setText(new_dots)
                self.scroll_to_bottom()

    def reenable_ui(self):
        self.text_input.clear()
        self.text_input.setEnabled(True)
        self.text_input.setStyleSheet("")
        self.listen_button.setEnabled(True)
        self.listen_button.setStyleSheet("")
        self.update_listen_button()
        self.text_input.setFocus()

    def append_chat(self, text, is_user):
        bubble = ChatBubble(text, is_user)
        self.chat_display_layout.addWidget(bubble)
        self.scroll_to_bottom()

    def replace_last_assistant(self, text):
        if self.chat_display_layout.count() > 0:
            last_bubble_widget = self.chat_display_layout.itemAt(self.chat_display_layout.count() - 1).widget()
            if isinstance(last_bubble_widget, ChatBubble) and not last_bubble_widget.is_user:
                last_bubble_widget.text_label.setText(text)
                self.scroll_to_bottom()
        else:
            # Fallback: if no messages, just append
            self.append_chat(text, False)

    def clear_console(self):
        # Clear the chat display
        while self.chat_display_layout.count():
            item = self.chat_display_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Reset the backend's conversation history
        self.backend.clear_conversation_history()

    def scroll_to_bottom(self):
        self.chat_scroll_area.verticalScrollBar().setValue(self.chat_scroll_area.verticalScrollBar().maximum())

    def closeEvent(self, event):
        self.is_listening = False
        if hasattr(self, 'listen_thread') and self.listen_thread.is_alive(): self.listen_thread.join(1)
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = AssistantGUI()
    window.show()
    sys.exit(app.exec_())
#########################################################
# IMPORTANT: Portuguese language currently not supported
# WORK IN PROGRESS
#########################################################

import sys
import threading
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from voice_recognition import SpeechRecognitionModule
from tts import TTSModule
from backend import Backend

translations = {
    'en': {
        'window_title': "Voice Assistant",
        'assistant_label': "Assistant:",
        'text_input_placeholder': "Type a message and press Enter to submit…",
        'input_device_label': "Input Device:",
        'volume_label': "Volume",
        'start_listening': "Start Listening",
        'stop_listening': "Stop Listening",
        'auto_speak': "TTS",
        'clear_console': "Clear Console",
        'menu_language': "Language",
        'action_english': "English (US)",
        'action_portuguese': "Português (PT)"
    },
    'pt': {
        'window_title': "Assistente de Voz",
        'assistant_label': "Assistente:",
        'text_input_placeholder': "Digite uma mensagem e pressione Enter…",
        'input_device_label': "Dispositivo de Entrada:",
        'volume_label': "Volume",
        'start_listening': "Iniciar Escuta",
        'stop_listening': "Parar Escuta",
        'auto_speak': "Falar Automaticamente",
        'clear_console': "Limpar Console",
        'menu_language': "Idioma",
        'action_english': "English (US)",
        'action_portuguese': "Português (PT)"
    }
}

class SignalBridge(QObject):
    update_text = pyqtSignal(str)
    replace_last = pyqtSignal(str)
    speak_text = pyqtSignal(str)
    reenable_input = pyqtSignal()
    clear_chat = pyqtSignal()

class AssistantGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_lang = 'en'
        self.is_listening = False
        self.auto_speak = False

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

        # Animation timer for "Assistant: . .. ..."
        self.dot_count = 0
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(500)  # 500 ms between dot updates
        self.anim_timer.timeout.connect(self.update_dots)

        # Build UI
        self.build_ui()
        self.apply_dark_theme()
        self.retranslate_ui()
        self.populate_input_devices()

    def build_ui(self):
        self.setWindowTitle("Voice Assistant")
        self.resize(800, 600)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Chat display
        self.assistant_label = QtWidgets.QLabel()
        self.assistant_label.setWordWrap(True)
        layout.addWidget(self.assistant_label)

        self.chat_display = QtWidgets.QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display, stretch=1)

        # Text input
        self.text_input = QtWidgets.QLineEdit()
        self.text_input.returnPressed.connect(self.submit_text)
        layout.addWidget(self.text_input)

        # Settings: input device & volume
        settings_layout = QtWidgets.QHBoxLayout()
        settings_layout.setSpacing(20)

        dev_layout = QtWidgets.QVBoxLayout()
        dev_layout.setSpacing(5)
        self.input_device_label = QtWidgets.QLabel()
        dev_layout.addWidget(self.input_device_label)
        self.input_device = QtWidgets.QComboBox()
        dev_layout.addWidget(self.input_device)
        settings_layout.addLayout(dev_layout, stretch=1)

        vol_layout = QtWidgets.QVBoxLayout()
        vol_layout.setSpacing(5)
        self.volume_label = QtWidgets.QLabel()
        vol_layout.addWidget(self.volume_label)
        self.volume_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.valueChanged.connect(self.on_volume_change)
        vol_layout.addWidget(self.volume_slider)
        settings_layout.addLayout(vol_layout, stretch=1)

        layout.addLayout(settings_layout)

        # Action buttons: listen, auto-speak, clear console
        action_layout = QtWidgets.QHBoxLayout()
        action_layout.setSpacing(10)

        # Start/Stop Listening
        self.listen_button = QtWidgets.QPushButton()
        self.listen_button.clicked.connect(self.toggle_listening)
        action_layout.addWidget(self.listen_button)

        # Auto Speak checkbox
        self.auto_speak_checkbox = QtWidgets.QCheckBox()
        self.auto_speak_checkbox.stateChanged.connect(self.on_auto_speak_toggle)
        action_layout.addWidget(self.auto_speak_checkbox)

        # Clear Console button
        self.clear_button = QtWidgets.QPushButton()
        self.clear_button.clicked.connect(lambda: self.signals.clear_chat.emit())
        action_layout.addWidget(self.clear_button)

        layout.addLayout(action_layout)

        # Menu for language
        menubar = self.menuBar()
        self.menu_language = menubar.addMenu("")
        self.action_en = self.menu_language.addAction("")
        self.action_pt = self.menu_language.addAction("")
        self.action_en.triggered.connect(lambda: self.change_language('en'))
        self.action_pt.triggered.connect(lambda: self.change_language('pt'))

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

    def retranslate_ui(self):
        t = translations[self.current_lang]
        self.setWindowTitle(t['window_title'])
        self.assistant_label.setText(t['assistant_label'])
        self.text_input.setPlaceholderText(t['text_input_placeholder'])
        self.input_device_label.setText(t['input_device_label'])
        self.volume_label.setText(t['volume_label'])
        self.update_listen_button()
        self.auto_speak_checkbox.setText(t['auto_speak'])
        self.clear_button.setText(t['clear_console'])
        self.menu_language.setTitle(t['menu_language'])
        self.action_en.setText(t['action_english'])
        self.action_pt.setText(t['action_portuguese'])

    def change_language(self, lang_code):
        self.current_lang = lang_code
        self.retranslate_ui()
        if lang_code == 'pt':
            self.tts.set_language("pt-PT")
            self.voice.set_language("pt-PT")
        else:
            self.tts.set_language("en-US")
            self.voice.set_language("en-US")

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

    def on_volume_change(self, value):
        self.tts.set_volume(value / 100.0)

    def on_auto_speak_toggle(self, state):
        self.auto_speak = (state == Qt.Checked)

    def update_listen_button(self):
        t = translations[self.current_lang]
        self.listen_button.setText(t['stop_listening'] if self.is_listening else t['start_listening'])

    def toggle_listening(self):
        if not self.is_listening:
            self.start_listening()
        else:
            self.stop_listening()

    def submit_text(self):
        text = self.text_input.text().strip()
        if not text:
            return

        # Show user message immediately
        self.signals.update_text.emit(f"User: {text}")

        # Disable input & grey out until response
        self.text_input.setEnabled(False)
        self.text_input.setStyleSheet("background-color: #2e2e2e; color: #777;")
        self.listen_button.setEnabled(False)
        self.listen_button.setStyleSheet("background-color: #555; color: #aaa;")

        # Append "Assistant: ." and start animating dots
        self.dot_count = 0
        self.signals.update_text.emit("Assistant: .")
        self.anim_timer.start()

        # Process in background
        threading.Thread(
            target=self.handle_text_submission,
            args=(text,),
            daemon=True
        ).start()

    def handle_text_submission(self, text):
        response = self.backend.process_command(text)

        # Stop animation and replace placeholder with actual response
        if self.anim_timer.isActive():
            self.anim_timer.stop()
        self.signals.replace_last.emit(f"Assistant: {response}")

        if self.auto_speak and response:
            self.signals.speak_text.emit(response)

        # Re-enable input after
        self.signals.reenable_input.emit()

    def start_listening(self):
        self.is_listening = True
        self.update_listen_button()

        # Disable typing until a voice is detected; listen button remains enabled so user can cancel
        self.text_input.setEnabled(False)
        self.text_input.setStyleSheet("background-color: #2e2e2e; color: #777;")

        # Shift focus away from text_input
        self.chat_display.setFocus()

        # Begin listening in background
        self.listen_thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.listen_thread.start()

    def stop_listening(self):
        # Immediately prevent further processing
        self.is_listening = False
        self.update_listen_button()

        # Re-enable typing & listen button, restore style
        self.text_input.setEnabled(True)
        self.text_input.setStyleSheet("")
        self.listen_button.setEnabled(True)
        self.listen_button.setStyleSheet("")
        self.text_input.setFocus()

        # Stop any ongoing animation
        if self.anim_timer.isActive():
            self.anim_timer.stop()

    def listen_loop(self):
        # Continuously call listen() until is_listening becomes False
        while self.is_listening:
            cmd = self.voice.listen()
            if not self.is_listening:
                # If stop_listening() was pressed during blocking listen(), exit
                break
            # If voice recognized:
            self.signals.update_text.emit(f"User: {cmd}")

            # Append "Assistant: ." and start animating
            self.dot_count = 0
            self.signals.update_text.emit("Assistant: .")
            self.anim_timer.start()

            response = self.backend.process_command(cmd)

            # Stop animation and replace placeholder
            if self.anim_timer.isActive():
                self.anim_timer.stop()
            self.signals.replace_last.emit(f"Assistant: {response}")
            if self.auto_speak and response:
                self.signals.speak_text.emit(response)

            # After processing one voice input, stop listening
            self.stop_listening()
            break

    def update_dots(self):
        self.dot_count = (self.dot_count + 1) % 3
        dots = "." * (self.dot_count + 1)
        self.signals.replace_last.emit(f"Assistant: {dots}")

    def reenable_ui(self):
        self.text_input.clear()
        self.text_input.setEnabled(True)
        self.text_input.setStyleSheet("")
        self.listen_button.setEnabled(True)
        self.listen_button.setStyleSheet("")
        self.update_listen_button()
        self.text_input.setFocus()

    def append_chat(self, text):
        self.chat_display.append(text)

    def replace_last_assistant(self, text):
        """
        Replace the most recent line starting with "Assistant:" without
        altering any other lines.
        """
        all_text = self.chat_display.toPlainText().splitlines()
        for i in range(len(all_text) - 1, -1, -1):
            if all_text[i].startswith("Assistant:"):
                all_text[i] = text
                break
        self.chat_display.setPlainText("\n".join(all_text))
        cursor = self.chat_display.textCursor()
        cursor.movePosition(cursor.End)
        self.chat_display.setTextCursor(cursor)

    def clear_console(self):
        self.chat_display.clear()
        # The backend's state (like last_filename) is now implicitly managed
        # by the LLM's context, so no explicit clear_state call is needed here.

    def closeEvent(self, event):
        self.is_listening = False
        if hasattr(self, 'listen_thread') and self.listen_thread.is_alive():
            self.listen_thread.join(1)
        event.accept()

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = AssistantGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

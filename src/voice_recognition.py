# Enhanced version with better noise handling and language switching

import speech_recognition as sr
from config import Config

class VoiceRecognitionBase:
    def listen(self):
        raise NotImplementedError("listen() must be implemented by subclass.")

class SpeechRecognitionModule(VoiceRecognitionBase):
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = Config.ENERGY_THRESHOLD
        self.recognizer.pause_threshold = Config.PAUSE_THRESHOLD
        self.microphone = sr.Microphone()
        # Default language code: 'en-US'
        self.language = 'en-US'
        
        # Adjust for ambient noise once at initialization
        with self.microphone as source:
            print("Calibrating for ambient noise... Please wait.")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("Calibration complete.")

    def set_language(self, lang_code):
        self.language = lang_code

    def listen(self):
        print("Listening using SpeechRecognition...")
        with self.microphone as source:
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                # Use the set language code when recognizing speech
                command = self.recognizer.recognize_google(audio, language=self.language)
                print(f"Recognized: {command}")
                return command
            except sr.WaitTimeoutError:
                print("Listening timed out")
            except sr.UnknownValueError:
                print("Could not understand audio")
            except sr.RequestError as e:
                print(f"Request error from SpeechRecognition service; {e}")
        return None

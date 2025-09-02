# Enhanced text-to-speech with dedicated thread for safe TTS invocation and language switching

import pyttsx3
import threading
import queue
from config import Config 

class TTSBase:
    def speak(self, text):
        raise NotImplementedError("speak() must be implemented by subclass.")

class TTSModule(TTSBase):
    def __init__(self):
        # Store initial TTS settings
        self.rate = Config.VOICE_RATE
        self.volume = Config.VOICE_VOLUME
        self.language = 'en-US'  # default language code
        self.voice_index = 0     # default index

        self.queue = queue.Queue()
        self._engine_ready_event = threading.Event()
        self.thread = threading.Thread(target=self._process_queue, daemon=True)
        self.thread.start()
        # This will block the main thread until the TTS engine is initialized in the other thread.
        self._engine_ready_event.wait()

    def _process_queue(self):
        # Initialize the TTS engine in this thread
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', self.rate)
        self.engine.setProperty('volume', self.volume)
        voices = self.engine.getProperty('voices')
        selected = False
        # Attempt to select a voice matching the language
        for voice in voices:
            if hasattr(voice, 'languages'):
                langs = []
                for l in voice.languages:
                    if isinstance(l, bytes):
                        langs.append(l.decode('utf-8').lower())
                    else:
                        langs.append(l.lower())
                if any(self.language.split('-')[0] in l for l in langs):
                    self.engine.setProperty('voice', voice.id)
                    selected = True
                    break
        if not selected and voices:
            self.engine.setProperty('voice', voices[0].id)
            
        self._engine_ready_event.set()
        
        while True:
            text = self.queue.get()
            if text is None: # Use None as a sentinel value to stop the thread
                self.engine.endLoop()
                break
            
            self.engine.say(text)
            self.engine.runAndWait()
            self.queue.task_done()
    
    def speak(self, text):
        # Put the text to be spoken into the queue
        self.queue.put(text)
        
    def stop(self):
        # Use None to stop the queue processing loop
        self.queue.put(None)
        
    def set_voice_by_index(self, voice_index):
        if hasattr(self, 'engine'):
            voices = self.engine.getProperty('voices')
            if 0 <= voice_index < len(voices):
                self.engine.setProperty('voice', voices[voice_index].id)
                return True
        return False
        
    def set_rate(self, rate):
        self.rate = rate
        if hasattr(self, 'engine'):
            self.engine.setProperty('rate', rate)
        
    def set_volume(self, volume):
        self.volume = volume
        if hasattr(self, 'engine'):
            self.engine.setProperty('volume', volume)
            
    def set_language(self, lang_code):
        self.language = lang_code
        if hasattr(self, 'engine'):
            voices = self.engine.getProperty('voices')
            selected = False
            for voice in voices:
                if hasattr(voice, 'languages'):
                    langs = []
                    for l in voice.languages:
                        if isinstance(l, bytes):
                            langs.append(l.decode('utf-8').lower())
                        else:
                            langs.append(l.lower())
                    if any(lang_code.split('-')[0] in l for l in langs):
                        self.engine.setProperty('voice', voice.id)
                        selected = True
                        break
            if not selected and voices:
                self.engine.setProperty('voice', voices[0].id)
            return selected
        return False

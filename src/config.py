# Configuration settings for voice assistant

class Config:
    # Voice Recognition settings
    ENERGY_THRESHOLD = 3000  # Energy level threshold for detecting speech
    PAUSE_THRESHOLD = 0.8    # Seconds of non-speaking before a phrase is considered complete
    
    # TTS settings
    VOICE_RATE = 200         # Default speech rate (words per minute)
    VOICE_VOLUME = 1.0       # Default volume (0.0 to 1.0)
    
    # GUI settings
    WINDOW_WIDTH = 1000
    WINDOW_HEIGHT = 600
    
    # Application settings
    APP_NAME = "Voice Assistant"
    DEBUG_MODE = True        # Enable debug output
    
    # --- Module Loading Settings ---
    # List the filenames (without .py extension) of the automation modules you want to enable.
    # These files should be located in the 'modules/' directory.
    ENABLED_MODULES = (
        "modules.system.system_automation",
        "modules.emails.gmail_automation",
        "modules.calendar.google_calendar_automation",
        "modules.meteorology.meteorology_automation",
    )

    # LLM settings
    LLM_PROVIDER     = "gemini"       # or "gemini", "novita", "awan".
    # Awan LLM settings
    AWAN_API_URL     = "https://api.awanllm.com/v1/chat/completions"
    AWAN_API_KEY     = "YOUR_AWAN_API_KEY" # IMPORTANT: Replace with your actual Awan API key
    AWAN_MODEL_NAME  = "Meta-Llama-3.1-70B-Instruct" # Example model, check Awan docs for available models (e.g., "Meta-Llama-3.1-70B-Instruct")

    # Gemini API settings
    GEMINI_API_KEY   = "YOUR_GEMINI_API_KEY" # Replace with your actual Gemini API key
    GEMINI_MODEL     = "models/gemini-2.5-flash"         # Or other Gemini models like "gemini-1.5-pro-latest"
    
    # Novita LLM settings
    NOVITA_API_URL = "https://api.novita.ai/v3/openai/chat/completions" # Novita AI URL
    NOVITA_API_KEY = "YOUR_NOVITA_API_KEY" # IMPORTANT: Replace with your actual Novita API token
    NOVITA_MODEL_NAME = "meta-llama/llama-3.3-70b-instruct" # Novita AI model

    # Sampling hyperparams
    LLM_TEMPERATURE  = 0.7 
    LLM_TOP_P        = 0.9 
    LLM_TOP_K        = 50  
    LLM_MAX_TOKENS   = 512 
    LLM_REPETITION_PENALTY = 1.0 
    LLM_MIN_P = 0.0 
    LLM_PRESENCE_PENALTY = 0.0 
    LLM_FREQUENCY_PENALTY = 0.0 
    LLM_REQUEST_TIMEOUT = 30 
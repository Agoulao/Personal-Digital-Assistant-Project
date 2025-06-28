# Configuration settings for voice assistant

class Config:
    # Voice Recognition settings
    ENERGY_THRESHOLD = 3000  # Energy level threshold for detecting speech
    PAUSE_THRESHOLD = 0.8    # Seconds of non-speaking before a phrase is considered complete
    
    # TTS settings
    VOICE_RATE = 200         # Default speech rate (words per minute)
    VOICE_VOLUME = 1.0       # Default volume (0.0 to 1.0)
    
    # GUI settings
    WINDOW_WIDTH = 600
    WINDOW_HEIGHT = 400
    
    # Application settings
    APP_NAME = "Voice Assistant"
    DEBUG_MODE = True        # Enable debug output

    # LLM settings
    LLM_PROVIDER     = "gemini"       # or "scaleway", "huggingface", "awan".
    # Awan LLM settings
    AWAN_API_URL     = "https://api.awanllm.com/v1/chat/completions"
    AWAN_API_KEY     = "" # IMPORTANT: Replace with your actual Awan API key 
    AWAN_MODEL_NAME  = "Meta-Llama-3.1-70B-Instruct" # Example model, check Awan docs for available models (e.g., "Meta-Llama-3.1-70B-Instruct")

    # Gemini API settings
    GEMINI_API_KEY   = "" # Replace with your actual Gemini API key
    GEMINI_MODEL     = "models/gemini-2.0-flash"         # Or other Gemini models like "gemini-1.5-pro-latest"
    
    # Hugging Face LLM settings
    HUGGINGFACE_API_URL = "https://api.novita.ai/v3/openai/chat/completions" # Novita AI URL
    HUGGINGFACE_API_KEY = "" # IMPORTANT: Replace with your actual Hugging Face token (Novita AI token)
    HUGGINGFACE_MODEL_NAME = "qwen/qwen2.5-7b-instruct" # Novita AI model
    HUGGINGFACE_PROVIDER_NAME = "novita" # Keeping for context, but not directly used in the client
    
    # Scaleway LLM settings 
    SCALEWAY_API_URL = "https://api.scaleway.ai/233511a8-7086-4a38-8e48-7c8c17727d83/v1" 
    SCALEWAY_API_KEY = "" # IMPORTANT: Replace with your actual Scaleway API Key.
    SCALEWAY_MODEL_NAME = "llama-3.3-70b-instruct" # Example model, check Scaleway docs for available models (e.g., llama-3.1-8b-instruct)
    
    # Sampling hyperparams
    LLM_TEMPERATURE  = 1.0 
    LLM_TOP_P        = 1.0 
    LLM_TOP_K        = 50  
    LLM_MAX_TOKENS   = 512 
    LLM_REPETITION_PENALTY = 1.0 
    LLM_MIN_P = 0.0 
    LLM_PRESENCE_PENALTY = 0.0 
    LLM_FREQUENCY_PENALTY = 0.0 
    LLM_REQUEST_TIMEOUT = 30 
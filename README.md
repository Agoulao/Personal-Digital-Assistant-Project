# Personal Digital Assistant

This project presents a modular Windows desktop application designed to act as a personal digital assistant. It supports both voice commands and text input, allowing users to interact with their computer and various online services through natural language. The core of the assistant is built with extensibility in mind, leveraging a pluggable Large Language Model (LLM) adapter and specialized functionality modules.

## Features

* **Natural Language Understanding:** Interprets user commands via an integrated LLM (Google Gemini API, Meta LLaMA).

* **Voice Interaction:**

    * **Automatic Speech Recognition (ASR):** Utilizes `SpeechRecognition` (Google's Chrome Speech API) for accurate speech-to-text conversion with noise calibration.

    * **Text-to-Speech (TTS):** Employs `pyttsx3` for offline text-to-speech, ensuring responsive voice output.

* **Graphical User Interface (GUI):** A responsive desktop interface built with `PyQt5`.

* **Modular Architecture:** Easily extendable with new functionalities through a pluggable module system.

* **Core Functionality Modules:**

  * **Operating System Automation:** Manages files and folders (`pathlib`, `shutil`) and controls mouse and keyboard (`pyautogui`).

  * **Google Calendar Integration:** Manages events and appointments (`google-api-python-client`, `google-auth`, `google-auth-httplib2`, `google-auth-oauthlib`, `pytz`, `dateutil`).

  * **Gmail Integration:** Read, send, and manage emails via Gmail API.
  
  * **Schedule and Task Management:** Integrates with Google Calendar or other calendar APIs

  * **Weather (OpenWeatherMap):** Current conditions, 5-day/3-hour forecast, and air pollution (AQI).

## Setup and Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Ensure Python 3.10 is installed.**

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Before running the application, you need to configure API keys for the LLM and other services.

1.  **Open `config.py`** in the project directory.

2.  **Update API Keys:**

    * For Google Gemini API, replace `"YOUR_GEMINI_API_KEY"` with your actual API key.

    * If using other LLM providers (e.g., Awan, Novita), ensure `[PROVIDER]_API_KEY` is set correctly and update their respective API keys.

## Google Calendar Integration and Gmail Setup

For Google Calendar and Gmail functionality, you need to obtain OAuth 2.0 credentials:

1.  **Navigate to Google Cloud Console:** `https://console.cloud.google.com`

2.  **Create a new project** (or select an existing one).

3.  **Enable the Google Calendar API and Gmail API** for your project.

4.  **Create OAuth 2.0 Client ID credentials:**

    * Go to "APIs & Services" > "Credentials".

    * Click "CREATE CREDENTIALS" > "OAuth client ID".

    * Select "Desktop app" as the application type.

    * Download the generated `client_secret-<something>.json` file.

5.  **Rename this downloaded file to `client_secret.json`** and place it in the `modules` directory of this project. This file is crucial for the application to authenticate with your Google Calendar and Gmail.

6.  **Add required OAuth scopes:**

    * Go to **APIs & Services** > **OAuth consent screen**.  
    * Under **Scopes**, click **Add or Remove Scopes**.  
    * Add the following scopes:  
      - `https://mail.google.com/` – Full Gmail access or another gmail scope if you don't want to give full permission
      - `https://www.googleapis.com/auth/calendar.events` – Create, edit, and delete calendar events  
    * Save changes.  

## Running the Application

To start the Personal Digital Assistant, execute the `main.py` file:

```bash
python main.py
```

This will launch the graphical user interface, and you can begin interacting with the assistant via text input or voice commands (if your microphone is set up).
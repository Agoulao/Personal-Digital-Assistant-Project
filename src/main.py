import sys
import os

# Add the project root to the Python path
# This allows absolute imports from top-level directories like 'core', 'LLM', 'Modules', 'ui'
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

from ui.gui import main as run_assistant_gui

if __name__ == "__main__":
    run_assistant_gui()

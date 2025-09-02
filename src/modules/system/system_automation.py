import functools
import logging
import os
import subprocess
import pyautogui
from pathlib import Path
from shutil import copy2
import shutil 
from modules.base_automation import BaseAutomationModule # Ensure this is imported

# Decorator for safe execution and uniform error handling
def safe_action(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            logging.error(f"Error in {func.__name__}:", exc_info=True)
            return f"[FAIL] Failed to {func.__name__.replace('_', ' ')}."
    return wrapper

class SystemAutomation(BaseAutomationModule):
    """
    Provides basic OS automation: file management, application launch,
    mouse and keyboard control via pyautogui.
    """

    def __init__(self):
        pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort

    def get_description(self) -> str:
        """
        Returns a brief description of the module's capabilities for the LLM's conversational context.
        """
        return "perform system automation tasks such as listing, creating, reading, writing, moving, and deleting files and folders, launching applications, and controlling mouse and keyboard"

    def get_supported_actions(self) -> dict:
        """
        Maps action names (from LLM intent) to internal method names, descriptions, and examples.
        """
        return {
            "create_folder": {
                "method_name": "create_folder",
                "description": "Creates a new folder at the specified path.",
                "example_json": '{"action":"create_folder","folder":"DIRECTORY"}'
            },
            "create_file": {
                "method_name": "create_file",
                "description": "Creates a new empty file at the specified path.",
                "example_json": '{"action":"create_file","filename":"DIRECTORY/FILENAME"}'
            },
            "write_file": {
                "method_name": "write_file",
                "description": "Writes content to a file, creating it if it doesn't exist. This action overwrites existing content.",
                "example_json": '{"action":"write_file","filename":"myfile.txt","content":"Hello World"}'
            },
            "append_file": { 
                "method_name": "append_file",
                "description": "Appends content to an existing file. If the file does not exist, it will be created.",
                "example_json": '{"action":"append_file","filename":"mylog.txt","content":"New log entry."}'
            },
            "read_file": {
                "method_name": "read_file",
                "description": "Reads and returns the text content of a specified file.",
                "example_json": '{"action":"read_file","filename":"my_document.txt"}'
            },
            "delete_file": {
                "method_name": "delete_file",
                "description": "Deletes a file.",
                "example_json": '{"action":"delete_file","filename":"FILENAME"}'
            },
            "delete_folder": {
                "method_name": "delete_folder",
                "description": "Deletes a folder and its contents.",
                "example_json": '{"action":"delete_folder","folder":"DIRECTORY"}'
            },
            "list_directory": {
                "method_name": "list_directory",
                "description": "Lists the contents (files and subfolders) of a specified **directory**.",
                "example_json": '{"action":"list_directory","directory":"my_folder"}'
            },
            "rename_file": {
                "method_name": "rename_file",
                "description": "Renames a file.",
                "example_json": '{"action":"rename_file","src":"old_name.txt","dest":"new_name.txt"}'
            },
            "copy_file": {
                "method_name": "copy_file",
                "description": "Copies a file from source to destination.",
                "example_json": '{"action":"copy_file","src":"source.txt","dest":"destination/copy.txt"}'
            },
            "move_file": {
                "method_name": "move_file",
                "description": "Moves a file from source to destination.",
                "example_json": '{"action":"move_file","src":"source.txt","dest":"destination/moved.txt"}'
            },
            "open_application": {
                "method_name": "open_application",
                "description": "Opens an application by its full path or common name. On Windows, it tries to find the executable in PATH or uses shell execution.",
                "example_json": '{"action":"open_application","path":"notepad.exe"}' 
            },
            "move_mouse": {
                "method_name": "move_mouse",
                "description": "Moves the mouse cursor to specific X and Y coordinates.",
                "example_json": '{"action":"move_mouse","x":100,"y":200}'
            },
            "click": {
                "method_name": "click",
                "description": "Performs a mouse click at the current cursor position or specified coordinates.",
                "example_json": '{"action":"click"}'
            },
            "type_text": {
                "method_name": "type_text",
                "description": "Types the specified text using the keyboard.",
                "example_json": '{"action":"type_text","text":"Hello World"}'
            },
            "press_key": {
                "method_name": "press_key",
                "description": "Presses a specific keyboard key (e.g., 'enter', 'esc', 'alt').",
                "example_json": '{"action":"press_key","key":"enter"}'
            },
        }

    # --- File Management ---
    @safe_action
    def create_folder(self, folder: str) -> str:
        if Path(folder).exists():
            return f"Folder already exists: {folder}"
        Path(folder).mkdir(parents=True, exist_ok=True)
        return f"Folder created: {folder}"

    @safe_action
    def create_file(self, filename: str) -> str:
        if Path(filename).exists():
            return f"File already exists: {filename}"
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        Path(filename).write_text('')
        return f"File created: {filename}"

    @safe_action
    def write_file(self, filename: str, content: str) -> str:
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f: # "w" mode overwrites
            f.write(content or "")
        return f"File written: {filename}"

    @safe_action
    def append_file(self, filename: str, content: str) -> str: 
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "a", encoding="utf-8") as f: 
            f.write(content or "")
        return f"Content appended to file: {filename}"

    @safe_action
    def read_file(self, filename: str) -> str:
        """
        Reads and returns the text content of a specified file.
        """
        filepath = Path(filename)
        if not filepath.exists():
            return f"Error: File '{filename}' does not exist."
        if not filepath.is_file():
            return f"Error: Path '{filename}' is not a file. Please specify a file to read its contents."
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return f"Content of '{filename}':\n---\n{content}\n---"
        except Exception as e:
            return f"Error reading file '{filename}': {e}"

    @safe_action
    def delete_file(self, filename: str) -> str:
        Path(filename).unlink()
        return f"File deleted: {filename}"
    
    @safe_action
    def delete_folder(self, folder: str) -> str:
        try:
            shutil.rmtree(folder)
            return f"Folder deleted: {folder}"
        except Exception as e:
            return f"Error deleting folder '{folder}': {e}"    

    @safe_action
    def list_directory(self, directory: str) -> str:
        # Check if the path exists and is a directory
        if not Path(directory).exists():
            return f"Error: Directory '{directory}' does not exist."
        if not Path(directory).is_dir():
            return f"Error: Path '{directory}' is not a directory. Please specify a folder to list its contents."

        files = os.listdir(directory)
        return "\n".join(files) if files else "<empty>"

    # --- File Operations: rename, copy, move ---
    @safe_action
    def rename_file(self, src: str, dest: str) -> str:
        Path(src).rename(dest)
        return f"File renamed: {src} -> {dest}"

    @safe_action
    def copy_file(self, src: str, dest: str) -> str:
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        copy2(src, dest)
        return f"File copied: {src} -> {dest}"

    @safe_action
    def move_file(self, src: str, dest: str) -> str:
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(src).rename(dest)
        return f"File moved: {src} -> {dest}"

    # --- Application Control ---
    @safe_action
    def open_application(self, path: str) -> str:
        # Windows-specific logic (since only Windows is used)
        # 1. Try to find the executable in PATH
        found_path = shutil.which(path)
        if found_path:
            try:
                os.startfile(found_path)
                return f"Launched application: {found_path}"
            except Exception as e:
                return f"Error launching '{found_path}' via os.startfile: {e}"
        else:
            # 2. If not found in PATH, try to launch directly via shell (relies on Windows' own lookup)
            try:
                os.startfile(path)
                return f"Attempted to launch application: {path} (Windows shell lookup)"
            except Exception as e:
                return f"Could not find or launch application '{path}'. Please provide a full path or ensure it's in your system's PATH or a well-known Windows application. Error: {e}"

    # --- Mouse & Keyboard ---
    @safe_action
    def move_mouse(self, x: int, y: int) -> str:
        pyautogui.moveTo(x, y)
        return f"Mouse moved to ({x}, {y})"

    @safe_action
    def click(self, x: int = None, y: int = None) -> str:
        if x is not None and y is not None:
            pyautogui.click(x, y)
        else:
            pyautogui.click()
        return "Mouse click executed"

    @safe_action
    def type_text(self, text: str) -> str:
        pyautogui.write(text)
        return f"Typed text: {text}"

    @safe_action
    def press_key(self, key: str) -> str:
        pyautogui.press(key)
        return f"Key pressed: {key}"


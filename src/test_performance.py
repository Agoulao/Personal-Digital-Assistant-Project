import time
import os
import datetime
from backend import Backend
from pathlib import Path
import shutil
import logging
from typing import Any

# Configure logging to show DEBUG messages from the backend and modules
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

# Initialize the backend (this will load modules and prepare LLM prompts)
print("Initializing Backend...")
backend = Backend()
print("Backend initialized.")

# --- Comprehensive Cleanup Function for File Operations ---
def cleanup_file_operations():
    """Ensures all perf_test_* files and folders are removed."""
    print("Running comprehensive file operations cleanup...")
    shutil.rmtree('perf_test_folder', ignore_errors=True)
    Path('perf_test_file.txt').unlink(missing_ok=True)
    Path('perf_renamed_file.txt').unlink(missing_ok=True)
    Path('perf_moved_file.txt').unlink(missing_ok=True)
    Path('perf_copied_file.txt').unlink(missing_ok=True)
    print("Comprehensive file operations cleanup complete.")


# Define test cases for each action
# Each test case is a tuple: (user_command, expected_substring_in_response, cleanup_function_or_command)
# Cleanup functions will be called after the test, or a command will be processed by the backend.
test_cases = {
    "file_operations": [
        ("create a folder named 'perf_test_folder'", "Folder created: perf_test_folder", None),
        ("create a file named 'perf_test_file.txt'", "File created: perf_test_file.txt", None),
        ("write 'This is performance test content.' into 'perf_test_file.txt'", "File written: perf_test_file.txt", None),
        ("read the contents of 'perf_test_file.txt'", "Content of 'perf_test_file.txt':\n---\nThis is performance test content.\n---", None),
        ("list contents of '.'", "perf_test_folder", None),
        ("rename 'perf_test_file.txt' to 'perf_renamed_file.txt'", "File renamed: perf_test_file.txt -> perf_renamed_file.txt", None),
        ("copy 'perf_renamed_file.txt' to 'perf_test_folder/perf_copied_file.txt'", "File copied: perf_renamed_file.txt -> perf_test_folder/perf_copied_file.txt", None),
        ("move 'perf_test_folder/perf_copied_file.txt' to 'perf_moved_file.txt'", "File moved: perf_test_folder/perf_copied_file.txt -> perf_moved_file.txt", None),
        ("delete the file 'perf_renamed_file.txt'", "File deleted: perf_renamed_file.txt", None),
        ("delete the folder 'perf_test_folder'", "Folder deleted: perf_test_folder", None),
    ],
    "google_calendar_operations": [
        # Note: These will only work if Google Calendar API is properly authenticated.
        # The LLM needs current date context to resolve "tomorrow", "next week" etc.
        # Ensure your client_secret.json is in the 'modules' directory and you've authenticated once.
        ("schedule a meeting called 'Perf Test Meeting' for tomorrow at 10 AM", "Event 'Perf Test Meeting' created successfully", None),
        ("list my events for tomorrow", "Perf Test Meeting", None),
        ("create an all-day event for next Monday called 'Perf Test All Day'", "Event 'Perf Test All Day' created successfully", None),
        ("list my events for next week", "Perf Test All Day", None),
        ("delete the Perf Test Meeting for tomorrow", "Event 'Perf Test Meeting' deleted successfully", None),
        ("delete the Perf Test All Day event for next Monday", "Event 'Perf Test All Day' deleted successfully", None),
    ],
    "mouse_keyboard_operations": [
        # These actions will physically move the mouse and type.
        # Ensure you are ready for this, and know how to use pyautogui.FAILSAFE (move mouse to top-left corner).
        ("move mouse to 50 50", "Mouse moved to (50, 50)", None),
        ("click", "Mouse click executed", None),
        ("type 'Performance test typing'", "Typed text: Performance test typing", None),
        ("press enter", "Key pressed: enter", None),
    ]
}

def run_test(command: str, expected_response_substring: str, cleanup_action: Any = None) -> tuple[bool, float]:
    """
    Runs a single test command, measures its execution time, and verifies the response.

    Args:
        command (str): The user command string to send to the backend.
        expected_response_substring (str): A substring expected in the successful response.
        cleanup_action (Any): A function to call or a command string to execute for cleanup.

    Returns:
        tuple[bool, float]: A tuple containing (test_passed, duration_in_seconds).
    """
    print(f"\n--- Testing Command: '{command}' ---")
    start_time = time.time()
    response = backend.process_command(command)
    end_time = time.time()
    duration = end_time - start_time
    print(f"Assistant Response: {response}")
    print(f"Time taken: {duration:.2f} seconds")

    test_passed = expected_response_substring in response
    print(f"Test Passed: {test_passed}")

    if cleanup_action:
        try:
            if callable(cleanup_action):
                print("Running cleanup function...")
                cleanup_action()
            else: # Assume it's a command string to be processed by backend
                print(f"Running cleanup command: '{cleanup_action}'")
                cleanup_response = backend.process_command(cleanup_action)
                print(f"Cleanup Response: {cleanup_response}")
        except Exception as e:
            print(f"ERROR during cleanup for command '{command}': {e}")
    return test_passed, duration

def main():
    print("Starting performance and functionality tests...\n")
    overall_results = []

    # Ensure a clean slate before starting ALL tests
    print("Performing initial comprehensive cleanup...")
    cleanup_file_operations() # Run the comprehensive file cleanup
    print("Initial comprehensive cleanup complete.\n")


    for category, cases in test_cases.items():
        print(f"\n===== Running {category.replace('_', ' ').upper()} Tests =====")
        for command, expected, cleanup in cases:
            passed, duration = run_test(command, expected, cleanup)
            overall_results.append((command, passed, duration))
            time.sleep(3) # 3-second delay between commands to ensure token limits are respected
            
    print("\n===== Test Summary =====")
    total_tests = len(overall_results)
    passed_tests = sum(1 for _, passed, _ in overall_results if passed)
    
    print(f"Total Tests Run: {total_tests}")
    print(f"Tests Passed: {passed_tests}")
    print(f"Tests Failed: {total_tests - passed_tests}")

    print("\nDetailed Results:")
    for command, passed, duration in overall_results:
        status = "PASSED" if passed else "FAILED"
        print(f"- Command: '{command}' -> Status: {status}, Time: {duration:.2f}s")

    print("\nPerformance Insights:")
    print("Refer to the 'DEBUG:' messages in the console output above for detailed timing of LLM inference and API calls.")

if __name__ == "__main__":
    main()

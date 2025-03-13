import logging

import cv2
import numpy as np
import psutil
import pyautogui
import pygetwindow as gw
import win32gui
import win32process

logger = logging.getLogger("window_extractor")


class WindowInformationExtractor:
    def __init__(self, window_title=None):
        """
        Initialize window information extraction.

        :param window_title: Title or partial title of the window to analyze
        """
        self.window = None

        self.find_window(window_title)

    def find_window(self, window_title):
        """
        Find a window by its title.

        :param window_title: Title or partial title of the window
        """
        if window_title:
            # Find windows matching the title (case-insensitive)
            matching_windows = [
                w for w in gw.getAllTitles() if window_title.lower() in w.lower()
            ]

            if not matching_windows:
                logger.error(f"No window found with title containing: {window_title}")
                raise ValueError(
                    f"No window found with title containing: {window_title}"
                )

            # Use the first matching window
            self.window = gw.getWindowsWithTitle(matching_windows[0])[0]
            logger.info(f"Found window: {self.window.title}")

            # Activate and bring the window to the foreground
            self.window.activate()
        else:
            logger.warning("No window title specified. Please provide a window title.")
            print("No window title specified. Please provide a window title.")

    def capture_window(self):
        """
        Capture the specified window.

        :return: Screenshot of the window as a numpy array
        """
        if not self.window:
            logger.error("No window selected for capture")
            raise ValueError("No window selected for capture")

        # Get window position and size
        x, y, width, height = (
            self.window.left,
            self.window.top,
            self.window.width,
            self.window.height,
        )

        # Capture the specific window area
        screenshot = pyautogui.screenshot(region=(x, y, width, height))

        # Convert PIL Image to numpy array for OpenCV compatibility
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    def get_window_details(self):
        """
        Retrieve detailed information about the window.

        :return: Dictionary of window details
        """
        if not self.window:
            logger.error("No window selected")
            raise ValueError("No window selected")

        try:
            # Get window handle
            hwnd = win32gui.FindWindow(None, self.window.title)

            # Get process information
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)

            details = {
                "title": self.window.title,
                "size": {"width": self.window.width, "height": self.window.height},
                "position": {"x": self.window.left, "y": self.window.top},
                "process_name": process.name(),
                "process_path": process.exe(),
                "is_active": self.window.isActive,
                "is_minimized": self.window.isMinimized,
                "is_maximized": self.window.isMaximized,
            }

            logger.info(
                f"Window details retrieved: process={process.name()}, size={self.window.width}x{self.window.height}"
            )
            return details

        except Exception as e:
            logger.error(f"Error getting window details: {e}", exc_info=True)
            raise

import os
import zipfile
import subprocess
import sys
import threading
import sqlite3
import shutil
from datetime import datetime, timezone

from . import database
from .destinations_ui import open_destinations_window
from .job_runner import run_job_in_thread, zip_path, ConflictResolution # Import ConflictResolution

import sched
import http.server
import socketserver
import json
import webbrowser
from urllib.parse import urlparse, parse_qs
import time
from datetime import datetime, timezone, timedelta
import io

# endregion

import argparse

# region Optional Imports
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from PIL import Image, ImageTk
    from tkcalendar import Calendar
except ImportError:
    tk = None
    Calendar = None

try:
    import msal
    import requests
except ImportError:
    msal = None
# endregion

# This script provides a graphical and command-line interface for compressing files and folders into ZIP archives.
# It records metadata about each compressed file—such as its original path, size, and modification time—into an
# SQLite database. The script also includes functionality for searching the database, managing compression jobs,
# and optionally uploading archives to Microsoft OneDrive. It is designed to be self-contained, handling
# dependencies gracefully and defaulting to a CLI if GUI libraries are unavailable.
#
# Features:
# - GUI and CLI interfaces for file and folder compression.
# - SQLite database for tracking file metadata and compression jobs.
# - Search functionality to locate files within archives.
# - Job management for automating recurring compression tasks.
# - Optional integration with Microsoft OneDrive for cloud uploads.
# - Automatic extraction of location data from image files (if available).
# - Graceful fallback to CLI mode if GUI components are not installed.


# Optional libs for OneDrive (MS Graph)
try:
    import msal
except Exception:
    msal = None

try:

    import requests
except Exception:
    requests = None

# Robust workaround for older pydevd / debugpy sys_monitoring (pydevd 3.14.0)
try:
    if not hasattr(threading.Thread, "_handle"):
        threading.Thread._handle = None
    mt = threading.main_thread()
    if not hasattr(mt, "_handle"):
        mt._handle = None
except Exception:
    pass

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception:
    tk = None  # GUI won't be available in headless environments

# Database (records each file added to archives)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "filezipper_records.db")








# ---------- Model Context Protocol (MCP) over HTTP Server ----------
MCP_PORT = 8999

class MCPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles HTTP requests for the Model Context Protocol."""

    def do_GET(self):
        """Handle GET requests to expose application data model."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        try:
            if path == '/files':
                search_query = query_params.get('search', [''])[0]
                data = database.search_files(search_query)
                self.send_json_response(data)
            elif path == '/jobs':
                data = database.list_jobs()
                self.send_json_response(data)
            elif path == '/destinations':
                data = database.list_destinations()
                self.send_json_response(data)
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")

    def send_json_response(self, data, status_code=200):
        """Sends a JSON response."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        # Use a custom default to handle non-serializable types like datetime
        json_str = json.dumps(data, indent=2, default=str).encode('utf-8')
        self.wfile.write(json_str)

    def log_message(self, format, *args):
        """Suppress HTTP server logging to keep the console clean."""
        return

def start_mcp_server(port=MCP_PORT):
    """Starts the MCP HTTP server in a separate thread."""
    def run_server():
        with socketserver.TCPServer(("", port), MCPRequestHandler) as httpd:
            # This print is useful for confirming the server started.
            print(f"MCP server running on http://localhost:{port}")
            httpd.serve_forever()

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True  # Allows main program to exit even if thread is running
    server_thread.start()





# ---------- GUI ----------



# ---------- CLI ----------



# ---------- Entrypoint ----------
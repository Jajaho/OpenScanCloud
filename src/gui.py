import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from pathlib import Path
import webbrowser
import json
import os
import time

from api import OpenScanAPI, OpenScanAPIError
from backend import OpenScanBackend, OpenScanBackendError

class OpenScanGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title('OpenScan Cloud Uploader')
        self.window.geometry('240x260')  # Increased height by 20px
        self.window.resizable(False, False)

        # Configuration
        self.config = {
            'server': 'http://openscanfeedback.dnsuser.de:1334/',
            'user': 'openscan',
            'password': 'free',
            'allowed_extensions': ['.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG'],
            'size_to_split': 200_000_000
        }

        # State variables
        self.status_text = tk.StringVar()
        self.folder_path = tk.StringVar()
        self.token = tk.StringVar()
        
        # Add status update variables
        self.server_status = tk.StringVar(value="Server: Unknown")
        self.queue_status = tk.StringVar(value="Queue: Unknown")
        self._status_update_running = True
        
        # Initialize API and backend
        self.api = OpenScanAPI(
            self.config['server'],
            self.config['user'],
            self.config['password']
        )
        self.backend = OpenScanBackend(
            self.config['allowed_extensions'],
            self.config['size_to_split']
        )

        self._create_widgets()
        self._load_token()
        
        # Start status update thread
        threading.Thread(target=self._update_status_loop, daemon=True).start()

    def _create_widgets(self):
        """Create and layout all GUI widgets"""
        # Status indicators (new)
        status_frame = ttk.Frame(self.window)
        status_frame.grid(row=0, columnspan=2, sticky="ew", padx=5, pady=5)

        server_label = ttk.Label(status_frame, textvariable=self.server_status)
        server_label.pack(side="left", padx=5)

        queue_label = ttk.Label(status_frame, textvariable=self.queue_status)
        queue_label.pack(side="right", padx=5)

        # Main status bar
        status = ttk.Label(self.window, textvariable=self.status_text)
        status.grid(row=1, columnspan=2, sticky="ew", padx=5, pady=5)

        # Token frame
        token_frame = ttk.LabelFrame(self.window, text="Token")
        token_frame.grid(row=2, columnspan=2, sticky="ew", padx=5, pady=5)

        token_entry = ttk.Entry(token_frame, textvariable=self.token)
        token_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        verify_btn = ttk.Button(token_frame, text="Verify", command=self._verify_token_bg)
        verify_btn.pack(side="right", padx=5, pady=5)

        # Folder selection
        folder_frame = ttk.LabelFrame(self.window, text="Image Folder")
        folder_frame.grid(row=3, columnspan=2, sticky="ew", padx=5, pady=5)

        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path)
        folder_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)

        browse_btn = ttk.Button(folder_frame, text="Browse", command=self._browse_folder)
        browse_btn.pack(side="right", padx=5, pady=5)

        # Upload button
        self.upload_btn = ttk.Button(
            self.window, 
            text="Upload Photos", 
            command=self._upload_photos_bg,
            state="disabled"
        )
        self.upload_btn.grid(row=4, columnspan=2, sticky="ew", padx=5, pady=5)

        # Links
        link_frame = ttk.Frame(self.window)
        link_frame.grid(row=5, columnspan=2, sticky="ew", padx=5, pady=5)

        github_link = ttk.Label(
            link_frame, 
            text="GitHub", 
            foreground="blue", 
            cursor="hand2"
        )
        github_link.pack(side="left")
        github_link.bind("<Button-1>", lambda e: webbrowser.open(
            "https://github.com/OpenScanEu/OpenScanCloud"
        ))

        donate_link = ttk.Label(
            link_frame, 
            text="Donate", 
            foreground="blue", 
            cursor="hand2"
        )
        donate_link.pack(side="right")
        donate_link.bind("<Button-1>", lambda e: webbrowser.open(
            "https://www.patreon.com/bePatron?u=51974655"
        ))

    def _load_token(self):
        """Load token from file if it exists"""
        token_file = Path("token.txt")
        if token_file.exists():
            self.token.set(token_file.read_text().strip())
            self._verify_token_bg()

    def _save_token(self):
        """Save token to file"""
        with open("token.txt", "w") as f:
            f.write(self.token.get())

    def _verify_token_bg(self):
        """Run token verification in background"""
        # Disable button while verifying
        self.upload_btn.configure(state='disabled')
        threading.Thread(target=self._verify_token_worker, daemon=True).start()

    def _verify_token_worker(self):
        """Worker thread for token verification"""
        try:
            info = self.api.verify_token(self.token.get())
            # Schedule GUI updates for main thread
            self.window.after(0, self._verify_token_success, info)
        except OpenScanAPIError as e:
            # Schedule error handling for main thread
            self.window.after(0, self._verify_token_error, str(e))

    def _verify_token_success(self, info):
        """Handle successful token verification (runs in main thread)"""
        self.status_text.set(f"Token valid - Credit: {info['credit']/1e9:.2f}GB")
        self.upload_btn.configure(state='normal')
        self._save_token()

    def _verify_token_error(self, error_msg):
        """Handle token verification error (runs in main thread)"""
        self.status_text.set(f"Token error: {error_msg}")
        self.upload_btn.configure(state='disabled')

    def _browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.status_text.set(f"Selected folder: {folder}")

    def _upload_photos_bg(self):
        """Run photo upload in background"""
        threading.Thread(target=self._upload_photos).start()

    def _upload_photos(self):
        """Handle photo upload process"""
        try:
            # Disable upload button
            self.upload_btn['state'] = 'disabled'

            # Prepare images
            input_dir = Path(self.folder_path.get())
            self.status_text.set("Preparing images...")
            image_list = self.backend.prepare_image_list(input_dir)

            # Create temp directory
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)

            # Create zip file
            self.status_text.set("Creating zip archive...")
            project_name, parts, total_size = self.backend.zip_and_split(
                image_list, input_dir, temp_dir
            )

            # Create project
            self.status_text.set("Creating project...")
            project = self.api.create_project(
                self.token.get(),
                project_name,
                len(image_list),
                len(parts),
                total_size
            )

            # Upload parts
            for i, part in enumerate(parts, 1):
                self.status_text.set(f"Uploading part {i}/{len(parts)}...")
                self.api.upload_part(part, project['ulink'][i-1])

            # Start processing
            self.status_text.set("Starting processing...")
            self.api.start_project(self.token.get(), project_name)
            
            self.status_text.set("Upload complete! You'll receive an email when done.")
            messagebox.showinfo(
                "Success",
                "Photos uploaded successfully! You will receive an email when processing is complete."
            )

        except (OpenScanAPIError, OpenScanBackendError) as e:
            self.status_text.set(f"Error: {e}")
            messagebox.showerror("Error", str(e))

        finally:
            # Cleanup and re-enable upload
            self.backend.cleanup_temp_dir(temp_dir)
            self.upload_btn['state'] = 'normal'

    def _update_status_loop(self):
        """Continuously update server and queue status"""
        while self._status_update_running:
            try:
                # Try to ping server with token verification
                self.api.get_server_status()
                self.window.after_idle(
                    lambda: self.server_status.set("Server: 🟢 Online")
                )
            except OpenScanAPIError:
                self.window.after_idle(
                    lambda: self.server_status.set("Server: 🔴 Offline")
                )

            # Update queue status from project info if available
            if self.token.get():
                try:
                    info = self.api.verify_token(self.token.get())
                    self.window.after_idle(
                        lambda: self.queue_status.set(
                            f"Credit: {info['credit']/1e9:.2f}GB"
                        )
                    )
                except OpenScanAPIError:
                    self.window.after_idle(
                        lambda: self.queue_status.set("Credit: Unknown")
                    )

            time.sleep(30)  # Update every 30 seconds

    def run(self):
        """Start the GUI application"""
        try:
            self.window.mainloop()
        finally:
            self._status_update_running = False

if __name__ == "__main__":
    app = OpenScanGUI()
    app.run()
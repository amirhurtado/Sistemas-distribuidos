import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from datetime import datetime


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Servidor de Chat - Logs")
        self.root.geometry("600x400")

        self.text_area = ScrolledText(
            root, wrap=tk.WORD, state="disabled", font=("Segoe UI", 9)
        )
        self.text_area.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

    def log(self, msg):
        """Añade un mensaje al área de texto de logs. Es thread-safe."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {msg}\n"

        self.text_area.config(state="normal")
        self.text_area.insert(tk.END, log_message)
        self.text_area.see(tk.END)
        self.text_area.config(state="disabled")

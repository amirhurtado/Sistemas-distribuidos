import tkinter as tk
from tkinter import Listbox, filedialog
from datetime import datetime
from client import config
import base64


class GuiManager:
    def __init__(self, root, callbacks):
        self.root = root
        self.callbacks = callbacks
        self.nickname = ""
        self.widgets = {}
        self.active_chat = "public"
        self.received_files = {}
        self._setup_main_window()

    def _setup_main_window(self):
        self.root.title("Chat Sirius")
        self.root.geometry("800x600")
        self.root.configure(bg=config.COLOR_FONDO)
        self.root.minsize(700, 500)
        main_frame = tk.Frame(self.root, bg=config.COLOR_FONDO)
        main_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        self._create_sidebar(main_frame)
        self._create_chat_area(main_frame)
        self._create_input_bar()
        self._configure_chat_styles()

    def _create_sidebar(self, parent):
        sidebar_frame = tk.Frame(parent, bg=config.COLOR_BARRA_LATERAL, width=220)
        sidebar_frame.grid(row=0, column=0, sticky="nswe", padx=(0, 10))
        sidebar_frame.pack_propagate(False)
        tk.Label(
            sidebar_frame,
            text="Conversaciones",
            font=config.FONT_BOLD,
            bg=config.COLOR_BARRA_LATERAL,
        ).pack(pady=(10, 2))
        self.widgets["conversations_list"] = Listbox(
            sidebar_frame,
            height=8,
            font=config.FONT_NORMAL,
            bg=config.COLOR_BARRA_LATERAL,
            highlightthickness=0,
            borderwidth=0,
        )
        self.widgets["conversations_list"].pack(fill=tk.X, padx=5)
        self.widgets["conversations_list"].insert(tk.END, "💬 Chat Público")
        self.widgets["conversations_list"].bind(
            "<<ListboxSelect>>", self._on_select_conversation
        )
        tk.Label(
            sidebar_frame,
            text="Usuarios Conectados",
            font=config.FONT_BOLD,
            bg=config.COLOR_BARRA_LATERAL,
        ).pack(pady=(10, 2))
        self.widgets["user_list"] = Listbox(
            sidebar_frame,
            font=config.FONT_NORMAL,
            bg=config.COLOR_BARRA_LATERAL,
            highlightthickness=0,
            borderwidth=0,
        )
        self.widgets["user_list"].pack(expand=True, fill=tk.BOTH, padx=5, pady=(0, 5))
        self.widgets["user_list"].bind("<Double-Button-1>", self._on_start_private_chat)

    def _create_chat_area(self, parent):
        chat_container = tk.Frame(parent, bg=config.COLOR_FONDO_SECUNDARIO)
        chat_container.grid(row=0, column=1, sticky="nswe")
        chat_container.grid_rowconfigure(0, weight=1)
        chat_container.grid_columnconfigure(0, weight=1)
        self.widgets["chat_area"] = tk.Text(
            chat_container,
            wrap=tk.WORD,
            state="disabled",
            bg=config.COLOR_FONDO_SECUNDARIO,
            font=config.FONT_NORMAL,
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self.widgets["chat_area"].grid(row=0, column=0, sticky="nswe")
        scrollbar = tk.Scrollbar(
            chat_container, command=self.widgets["chat_area"].yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.widgets["chat_area"]["yscrollcommand"] = scrollbar.set

    def _create_input_bar(self):
        input_frame = tk.Frame(self.root, bg=config.COLOR_FONDO_SECUNDARIO, height=50)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        input_frame.grid_columnconfigure(1, weight=1)
        btn_archivo = tk.Button(
            input_frame,
            text="📎",
            command=self._handle_send_file,
            font=("Segoe UI Symbol", 14),
            bg=config.COLOR_FONDO_SECUNDARIO,
            fg=config.COLOR_PRIMARIO,
            relief="flat",
        )
        btn_archivo.grid(row=0, column=0, padx=5, pady=10)
        self.widgets["entry_msg"] = tk.Entry(
            input_frame,
            font=config.FONT_NORMAL,
            bg=config.COLOR_FONDO,
            fg=config.COLOR_TEXTO,
            borderwidth=0,
        )
        self.widgets["entry_msg"].grid(
            row=0, column=1, sticky="we", padx=10, pady=10, ipady=5
        )
        self.widgets["entry_msg"].bind("<Return>", self._handle_send_message)
        btn_enviar = tk.Button(
            input_frame,
            text="➤",
            command=self._handle_send_message,
            font=("Segoe UI Symbol", 14),
            bg=config.COLOR_FONDO_SECUNDARIO,
            fg=config.COLOR_PRIMARIO,
            relief="flat",
        )
        btn_enviar.grid(row=0, column=2, padx=5, pady=10)

    def _configure_chat_styles(self):
        chat_area = self.widgets["chat_area"]
        chat_area.tag_configure(
            "info",
            foreground=config.COLOR_TEXTO_SECUNDARIO,
            justify="center",
            font=config.FONT_ITALIC_PEQUEÑA,
        )
        chat_area.tag_configure(
            "nombre_otro_linea", font=config.FONT_BOLD, foreground=config.COLOR_PRIMARIO
        )
        chat_area.tag_configure(
            "nombre_mio_linea",
            font=config.FONT_BOLD,
            foreground=config.COLOR_TEXTO_SECUNDARIO,
            justify="right",
        )
        chat_area.tag_configure(
            "otro_usuario_burbuja",
            background=config.COLOR_BARRA_LATERAL,
            lmargin1=15,
            lmargin2=15,
            rmargin=120,
            spacing3=5,
            relief="raised",
            borderwidth=1,
            wrap="word",
        )
        chat_area.tag_configure(
            "mi_burbuja",
            background=config.COLOR_MI_BURBUJA,
            foreground=config.COLOR_TEXTO_MI_MENSAJE,
            justify="right",
            lmargin1=120,
            lmargin2=120,
            rmargin=15,
            spacing3=5,
            relief="raised",
            borderwidth=1,
            wrap="word",
        )
        chat_area.tag_configure(
            "file_link", foreground="blue", underline=True, font=config.FONT_NORMAL
        )
        chat_area.tag_bind("file_link", "<Button-1>", self._on_click_file_link)
        chat_area.tag_bind(
            "file_link", "<Enter>", lambda e: chat_area.config(cursor="hand2")
        )
        chat_area.tag_bind(
            "file_link", "<Leave>", lambda e: chat_area.config(cursor="")
        )

    def _handle_send_message(self, event=None):
        msg = self.widgets["entry_msg"].get().strip()
        if msg:
            self.callbacks["send_message"](self.active_chat, msg)
            self.widgets["entry_msg"].delete(0, "end")

    def _handle_send_file(self):
        filepath = filedialog.askopenfilename(parent=self.root)
        if filepath:
            self.callbacks["send_file"](self.active_chat, filepath)

    def _on_start_private_chat(self, event=None):
        selection = self.widgets["user_list"].curselection()
        if not selection:
            return
        recipient_display = self.widgets["user_list"].get(selection[0])
        recipient = recipient_display.replace(" (tú)", "")
        if recipient == self.nickname:
            return
        self.callbacks["start_private_chat"](recipient)

    def _on_select_conversation(self, event=None):
        selection = self.widgets["conversations_list"].curselection()
        if not selection:
            return
        conv_name_raw = self.widgets["conversations_list"].get(selection[0])
        conv_name = conv_name_raw.replace("💬 ", "").replace("👤 ", "")
        self.active_chat = "public" if conv_name == "Chat Público" else conv_name
        self.callbacks["switch_chat_view"](self.active_chat)

    def _on_click_file_link(self, event):
        index = self.widgets["chat_area"].index(f"@{event.x},{event.y}")
        tags = self.widgets["chat_area"].tag_names(index)
        file_id_tag = next((t for t in tags if t.startswith("fileid_")), None)
        if file_id_tag:
            file_id = file_id_tag.split("_", 1)[1]
            file_info = self.received_files.get(file_id)
            if file_info:
                save_path = filedialog.asksaveasfilename(
                    parent=self.root, initialfile=file_info["filename"]
                )
                if save_path:
                    file_content = base64.b64decode(file_info["content"])
                    with open(save_path, "wb") as f:
                        f.write(file_content)
                    self._add_system_message(
                        f"Archivo '{file_info['filename']}' guardado."
                    )

    def display_conversation(self, messages):
        chat_area = self.widgets["chat_area"]
        chat_area.config(state="normal")
        chat_area.delete(1.0, tk.END)
        for msg in messages:
            if msg["type"] == "system":
                self._add_system_message(msg["content"])
            elif msg["type"] == "file":
                self._add_file_display(msg["sender"], msg["filename"], msg["content"])
            else:
                self._add_message_bubble(msg["sender"], msg["content"])
        chat_area.config(state="disabled")
        chat_area.yview(tk.END)

    def add_message_to_view(self, msg):
        """Appends a single message dictionary to the currently visible chat area."""
        chat_area = self.widgets["chat_area"]
        chat_area.config(state="normal")
        
        if msg["type"] == "system":
            chat_area.insert(tk.END, f"{msg['content']}\n", "info")
        elif msg["type"] == "file":
            self._add_file_display(msg["sender"], msg["filename"], msg["content"])
        else:
            self._add_message_bubble(msg["sender"], msg["content"])
            
        chat_area.see(tk.END)
        chat_area.config(state="disabled")

    def _add_system_message(self, text):
        """
        Añade un mensaje de sistema (como una notificación) al área de chat.
        Este mensaje es efímero y no se guarda en el historial.
        """
        chat_area = self.widgets["chat_area"]
        chat_area.config(state="normal")
        chat_area.insert(tk.END, f"{text}\n", "info")
        chat_area.see(tk.END)
        chat_area.config(state="disabled")

    def _add_message_bubble(self, sender, text):
        chat_area = self.widgets["chat_area"]
        timestamp = datetime.now().strftime("%H:%M")
        if sender == self.nickname:
            chat_area.insert(
                tk.END, f"{sender} (tú) ({timestamp})\n", "nombre_mio_linea"
            )
            chat_area.insert(tk.END, f"{text}\n\n", "mi_burbuja")
        else:
            chat_area.insert(tk.END, f"{sender} ({timestamp})\n", "nombre_otro_linea")
            chat_area.insert(tk.END, f"{text}\n\n", "otro_usuario_burbuja")

    def _add_file_display(self, sender, filename, b64_content):
        chat_area = self.widgets["chat_area"]
        timestamp = datetime.now().strftime("%H:%M")
        file_id = f"{sender}_{filename}_{len(b64_content)}"
        self.received_files[file_id] = {"filename": filename, "content": b64_content}
        file_tag = f"fileid_{file_id}"
        if sender == self.nickname:
            chat_area.insert(
                tk.END, f"{sender} (tú) ({timestamp})\n", "nombre_mio_linea"
            )
            chat_area.insert(tk.END, f"Archivo enviado: ", "mi_burbuja")
            chat_area.insert(
                tk.END, f"{filename}\n\n", ("mi_burbuja", "file_link", file_tag)
            )
        else:
            chat_area.insert(tk.END, f"{sender} ({timestamp})\n", "nombre_otro_linea")
            chat_area.insert(tk.END, f"Archivo recibido: ", "otro_usuario_burbuja")
            chat_area.insert(
                tk.END,
                f"{filename}\n\n",
                ("otro_usuario_burbuja", "file_link", file_tag),
            )

    def add_conversation_to_list(self, name):
        conv_listbox = self.widgets["conversations_list"]
        if f"👤 {name}" not in conv_listbox.get(0, tk.END):
            conv_listbox.insert(tk.END, f"👤 {name}")

    def update_user_list(self, users):
        user_listbox = self.widgets["user_list"]
        user_listbox.delete(0, tk.END)
        for user in sorted(users):
            display_name = f"{user} (tú)" if user == self.nickname else user
            user_listbox.insert(tk.END, display_name)

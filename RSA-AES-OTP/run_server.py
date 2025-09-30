import tkinter as tk
from server.server import ChatServer
from server.gui import ServerGUI
from server import config

if __name__ == "__main__":
    root = tk.Tk()
    gui = ServerGUI(root)
    server = ChatServer(config.HOST, config.PORT, logger=gui.log)
    server.start_in_thread()
    root.mainloop()

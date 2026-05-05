import tkinter as tk
from gui.app import AppPromedios

if __name__ == "__main__":
    # Inicialización del entorno gráfico
    root = tk.Tk()
    app = AppPromedios(root)
    root.mainloop()
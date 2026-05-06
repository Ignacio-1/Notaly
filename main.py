import tkinter as tk
from gui.app import AppPromedios

def main():
    # Inicializa el motor gráfico principal
    root = tk.Tk()
    
    # Instancia nuestra aplicación inyectando la ventana raíz
    app = AppPromedios(root)
    
    # Inicia el bucle de eventos, manteniendo la ventana abierta
    root.mainloop()

if __name__ == "__main__":
    main()
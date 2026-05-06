import customtkinter as ctk
from gui.app import AppPromedios

def main():
    # NOTA: Esta versión utiliza la librería 'customtkinter' para una apariencia moderna.
    # Asegúrate de instalarla con: pip install customtkinter
    
    # Inicializa el motor gráfico principal
    root = ctk.CTk()
    
    # Instancia nuestra aplicación inyectando la ventana raíz
    app = AppPromedios(root)
    
    # Inicia el bucle de eventos, manteniendo la ventana abierta
    root.mainloop()

if __name__ == "__main__":
    main()
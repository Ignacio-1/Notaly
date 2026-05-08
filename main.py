"""
Punto de entrada principal de la aplicación Gestor Educativo.

Inicializa el motor gráfico y lanza la interfaz de usuario.
"""

import logging

import customtkinter as ctk

from gui.app import AppPromedios


def main():
    # Configurar logging básico para la aplicación
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Inicializa el motor gráfico principal
    root = ctk.CTk()

    # Instancia nuestra aplicación inyectando la ventana raíz
    app = AppPromedios(root)
    logger.info("Aplicación iniciada correctamente.")

    # Inicia el bucle de eventos, manteniendo la ventana abierta
    root.mainloop()


if __name__ == "__main__":
    main()
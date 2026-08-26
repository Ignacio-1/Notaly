"""
Punto de entrada oficial para la aplicacion movil Notaly (Flet).
Permite empaquetar tanto el modulo 'core' como 'mobile' en la APK.
"""
import flet as ft
from mobile.main import main

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")

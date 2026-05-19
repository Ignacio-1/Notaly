import os
import sys
import subprocess
import hashlib
import time
import winreg
import base64
import tkinter.messagebox as messagebox

import customtkinter as ctk

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet

# ==========================================
# CONFIGURACIÓN DE SEGURIDAD (DRM)
# ==========================================

# LLAVE PÚBLICA (Ed25519) - SOLO LECTURA
# (Genera tu propio par de claves y coloca aquí la pública para producción)
PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEApUk/15ZbrD6dFifrS2Gzm1wXOU/biENA/Pg336DlhxE=
-----END PUBLIC KEY-----""" 

# CLAVE SIMÉTRICA (Para cifrar/descifrar la fecha localmente - Anti-Fraude)
# ¡Cambia esta clave en tu entorno de producción!
FERNET_KEY = b'K5pOGxFKFIgeOiULveSOMmJ33dZCC6g75KtJ9ENh9os='
fernet = Fernet(FERNET_KEY)

APP_NAME = "TuApp_Sec"
REGISTRY_PATH = rf"Software\{APP_NAME}"
APPDATA_PATH = os.path.join(os.environ.get("APPDATA", ""), f".{APP_NAME.lower()}_data")
RESIDUAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), f".{APP_NAME.lower()}_residual")


def hide_file(filepath: str):
    """Oculta un archivo en Windows usando attrib."""
    try:
        subprocess.run(["attrib", "+h", filepath], creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass


# ==========================================
# 1. GENERACIÓN DEL HARDWARE ID
# ==========================================
def get_hardware_id() -> str:
    """Calcula el Hardware ID único basado en la Placa Madre y Procesador."""
    try:
        # Extraer UUID de la Placa Madre
        hw_uuid = subprocess.check_output(
            ["wmic", "csproduct", "get", "uuid"], 
            creationflags=subprocess.CREATE_NO_WINDOW
        ).decode('utf-8').split('\n')[1].strip()
        
        # Extraer ID del Procesador
        hw_cpu = subprocess.check_output(
            ["wmic", "cpu", "get", "processorid"], 
            creationflags=subprocess.CREATE_NO_WINDOW
        ).decode('utf-8').split('\n')[1].strip()
        
        combined = f"{hw_uuid}_{hw_cpu}"
    except Exception:
        # En caso extremo de error de permisos de WMI
        combined = "UNKNOWN_HARDWARE_ID_FALLBACK"

    # Pasar por SHA-256
    sha256_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest().upper()
    
    # Formatear los primeros 12 caracteres (Ej: A1B2-C3D4-E5F6)
    hwid = sha256_hash[:12]
    return f"{hwid[:4]}-{hwid[4:8]}-{hwid[8:12]}"


# ==========================================
# 2. SISTEMA ANTI-FRAUDE DE TIEMPO
# ==========================================
def get_saved_times() -> list[float]:
    """Obtiene las fechas registradas desde las 3 ubicaciones."""
    times = []
    
    # a) Registro de Windows
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "LastRun")
        winreg.CloseKey(key)
        times.append(float(fernet.decrypt(value).decode('utf-8')))
    except Exception:
        pass
        
    # b) Archivo oculto en AppData
    try:
        if os.path.exists(APPDATA_PATH):
            with open(APPDATA_PATH, "rb") as f:
                times.append(float(fernet.decrypt(f.read()).decode('utf-8')))
    except Exception:
        pass
        
    # c) Archivo residual
    try:
        if os.path.exists(RESIDUAL_PATH):
            with open(RESIDUAL_PATH, "rb") as f:
                times.append(float(fernet.decrypt(f.read()).decode('utf-8')))
    except Exception:
        pass
        
    return times


def save_current_time():
    """Guarda la fecha actual en las 3 ubicaciones de forma redundante."""
    current_time_bytes = str(time.time()).encode('utf-8')
    encrypted_time = fernet.encrypt(current_time_bytes)
    
    # a) Registro de Windows
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
        winreg.SetValueEx(key, "LastRun", 0, winreg.REG_BINARY, encrypted_time)
        winreg.CloseKey(key)
    except Exception:
        pass
        
    # b) Archivo oculto en AppData
    try:
        with open(APPDATA_PATH, "wb") as f:
            f.write(encrypted_time)
        hide_file(APPDATA_PATH)
    except Exception:
        pass
        
    # c) Archivo residual
    try:
        with open(RESIDUAL_PATH, "wb") as f:
            f.write(encrypted_time)
        hide_file(RESIDUAL_PATH)
    except Exception:
        pass


def check_time_fraud():
    """Verifica si el reloj del sistema fue atrasado."""
    saved_times = get_saved_times()
    current_time = time.time()
    
    for t in saved_times:
        if current_time < t:
            # FRAUDE DETECTADO (El usuario atrasó el reloj)
            messagebox.showerror(
                "Infracción de Seguridad", 
                "Se ha detectado una alteración fraudulenta en la hora del sistema operativo.\nEl acceso ha sido bloqueado de forma preventiva."
            )
            sys.exit(1)


# ==========================================
# 3. VERIFICACIÓN CRIPTOGRÁFICA
# ==========================================
def verify_license(hwid: str, license_key: str) -> bool:
    """
    Verifica la licencia asimétrica.
    Formato esperado: YYYYMMDD-FirmaBase64
    """
    try:
        parts = license_key.split("-", 1)
        if len(parts) != 2:
            return False
            
        expiration_date_str, signature_b64 = parts
        
        # Validar formato de fecha (YYYYMMDD)
        if len(expiration_date_str) != 8 or not expiration_date_str.isdigit():
            return False
            
        # Reconstruir el mensaje original que fue firmado
        message = f"{hwid}{expiration_date_str}".encode('utf-8')
        signature = base64.urlsafe_b64decode(signature_b64)
        
        # Cargar llave pública
        public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM)
        
        # Verificar firma (esto lanza InvalidSignature si falla)
        public_key.verify(signature, message)  # type: ignore
        
        # Verificar fecha de expiración
        exp_year = int(expiration_date_str[:4])
        exp_month = int(expiration_date_str[4:6])
        exp_day = int(expiration_date_str[6:8])
        
        # Crear límite de expiración para las 23:59:59 de ese día
        expiration_epoch = time.mktime((exp_year, exp_month, exp_day, 23, 59, 59, 0, 0, -1))
        
        if time.time() > expiration_epoch:
            return False # Licencia expirada
            
        return True
    except InvalidSignature:
        messagebox.showerror("Debug Criptográfico", "Fallo: La firma matemática no coincide. La Llave Pública del iniciador no corresponde a la Llave Privada del generador.")
        return False
    except Exception as e:
        messagebox.showerror("Debug de Código", f"Fallo en la lectura de datos. Error técnico: {repr(e)}")
        return False


# ==========================================
# 4. INTERFAZ GRÁFICA DE ACTIVACIÓN
# ==========================================
class ActivationWindow(ctk.CTk):
    def __init__(self, hwid):
        super().__init__()
        
        self.hwid = hwid
        
        self.title("Activación de Software")
        self.geometry("500x380")
        self.resizable(False, False)
        
        # Tema profesional y minimalista
        try:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")
        except Exception:
            pass # Si usa fallback a tkinter estándar
        
        self.grid_columnconfigure(0, weight=1)
        
        # Encabezado
        self.label_title = ctk.CTkLabel(self, text="Activación de Software", font=("Segoe UI", 24, "bold"))
        self.label_title.grid(row=0, column=0, padx=20, pady=(30, 10))
        
        # Instrucciones
        self.label_inst = ctk.CTkLabel(self, text="Para activar tu suscripción, envía tu\nCódigo de Equipo al soporte.", font=("Segoe UI", 14))
        self.label_inst.grid(row=1, column=0, padx=20, pady=10)
        
        # Código de Equipo (Hardware ID)
        self.frame_hwid = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_hwid.grid(row=2, column=0, padx=20, pady=10)
        
        self.label_hwid = ctk.CTkLabel(self.frame_hwid, text=self.hwid, font=("Consolas", 26, "bold"), text_color="#00a8ff")
        self.label_hwid.grid(row=0, column=0, padx=15, pady=10)
        
        self.btn_copy = ctk.CTkButton(self.frame_hwid, text="Copiar Código", width=120, command=self.copy_hwid)
        self.btn_copy.grid(row=0, column=1, padx=(0, 15), pady=10)
        
        # Entrada de la Licencia
        self.entry_license = ctk.CTkEntry(self, placeholder_text="Pega aquí tu Licencia", width=380, height=35)
        self.entry_license.grid(row=3, column=0, padx=20, pady=20)
        
        # Botón para Activar
        self.btn_activate = ctk.CTkButton(self, text="Activar", width=220, height=45, font=("Segoe UI", 16, "bold"), command=self.activate)
        self.btn_activate.grid(row=4, column=0, padx=20, pady=10)

    def copy_hwid(self):
        """Copia el Hardware ID al portapapeles de Windows."""
        self.clipboard_clear()
        self.clipboard_append(self.hwid)
        self.update()
        
        # Efecto visual
        original_text = self.btn_copy.cget("text")
        self.btn_copy.configure(text="¡Copiado!")
        self.after(2000, lambda: self.btn_copy.configure(text=original_text))

    def activate(self):
        """Intenta activar la app validando el input."""
        license_key = self.entry_license.get().strip()
        if verify_license(self.hwid, license_key):
            # Guardar en el registro si es válida
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH)
                winreg.SetValueEx(key, "License", 0, winreg.REG_SZ, license_key)
                winreg.CloseKey(key)
            except Exception:
                pass
                
            # Cierra la ventana exitosamente
            self.destroy()
        else:
            messagebox.showerror("Error de Activación", "La licencia ingresada es inválida o ha expirado.", parent=self)


# ==========================================
# 5. CONTROLADOR PRINCIPAL DEL WRAPPER
# ==========================================
def load_license() -> str:
    """Carga la licencia desde el registro si existe."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "License")
        winreg.CloseKey(key)
        return value
    except Exception:
        return ""


def run_main_app():
    """Importa y ejecuta la aplicación original sin modificarla."""
    try:
        import main
        main.main()  # <--- Esto dispara la aplicación
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo cargar la aplicación principal.\nDetalles: {str(e)}")
        sys.exit(1)


def main():
    # 1. Comprobar si hay intento de fraude de tiempo
    check_time_fraud()
    
    # 2. Extraer Hardware ID de la PC
    hwid = get_hardware_id()
    
    # 3. Cargar licencia si ya fue activada previamente
    license_key = load_license()
    
    # 4. Flujo de validación
    if not verify_license(hwid, license_key):
        # Desplegar la GUI si la licencia no existe o está vencida
        app = ActivationWindow(hwid)
        app.mainloop()
        
        # Una vez que la ventana se cierra, verificamos nuevamente
        # (por si el usuario acaba de ingresar una licencia válida)
        license_key = load_license()
        if not verify_license(hwid, license_key):
            # Si a pesar de cerrarse sigue sin haber licencia, salimos.
            sys.exit(0)
            
    # -- SI EL CÓDIGO LLEGA HASTA AQUÍ, LA LICENCIA ES VÁLIDA --
    
    # 5. Actualizar la marca de tiempo Anti-Fraude
    save_current_time()
    
    # 6. Lanzar la aplicación principal original de forma transparente
    run_main_app()

if __name__ == "__main__":
    main()

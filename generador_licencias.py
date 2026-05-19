import os
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

def generar_llaves_si_no_existen():
    if not os.path.exists(PRIVATE_KEY_FILE) or not os.path.exists(PUBLIC_KEY_FILE):
        print("=========================================")
        print("🔑 Generando nuevo par de llaves criptográficas...")
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        with open(PRIVATE_KEY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(PUBLIC_KEY_FILE, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        print("✅ ¡Llaves generadas con éxito!")
        print("⚠️ IMPORTANTE: Abre el archivo 'public_key.pem' recién creado.")
        print("Copia todo su contenido y reemplaza la variable PUBLIC_KEY_PEM en iniciador.py")
        print("=========================================\n")
    else:
        print("✅ Llaves criptográficas existentes encontradas.\n")

def generar_licencia():
    print("--- CREADOR DE LICENCIAS COMERCIALES ---")
    hwid = input("1. Pega el Código de Equipo (HWID) del cliente: ").strip()
    if not hwid:
        print("❌ HWID inválido.")
        return

    fecha_exp = input("2. Ingresa fecha de expiración (YYYYMMDD) [Ej: 20261231]: ").strip()
    if len(fecha_exp) != 8 or not fecha_exp.isdigit():
        print("❌ Formato de fecha inválido. Debe tener 8 números (Ej: 20261231).")
        return

    try:
        # Cargar llave privada para firmar
        with open(PRIVATE_KEY_FILE, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

        # El mensaje a firmar DEBE coincidir con la lógica del iniciador (HWID + YYYYMMDD)
        message = f"{hwid}{fecha_exp}".encode('utf-8')
        
        # Generar firma
        signature = private_key.sign(message)
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        licencia_final = f"{fecha_exp}-{signature_b64}"
        
        print("\n" + "★"*60)
        print("LICENCIA GENERADA EXITOSAMENTE. ENVIAR ESTO AL CLIENTE:")
        print(licencia_final)
        print("★"*60 + "\n")
        
    except Exception as e:
        print(f"❌ Ocurrió un error al firmar: {e}")

if __name__ == "__main__":
    generar_llaves_si_no_existen()
    generar_licencia()
    input("Presiona ENTER para salir...")

"""Módulo principal de la interfaz gráfica del Gestor Educativo."""

import logging
import os
import platform
import sys

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog

from core import gestor_datos
from core.calculos import procesar_calificaciones_alumno
from core.constants import (
    K_ALUMNOS,
    K_COLEGIOS,
    K_CURSOS,
    K_EXTRAS,
    K_NOMBRE,
    K_NOMBRES_COLUMNAS,
    K_PRINCIPALES,
    K_RECUPERATORIO,
    K_TRIMESTRES,
    NOMBRES_COLUMNAS_DEFAULT,
    NOMBRES_TRIMESTRES,
    NOTA_MAXIMA,
    NOTA_MINIMA_APROBACION,
    NUM_EXTRAS,
    NUM_PRINCIPALES,
    UMBRAL_RECUPERATORIO,
    crear_trimestre_vacio,
    crear_trimestres_vacios,
)
from core.exportador import exportar_a_csv, exportar_a_texto, exportar_a_pdf

logger = logging.getLogger(__name__)

class AppPromedios:
    def __init__(self, root):
        ctk.set_appearance_mode("light")

        self.root = root
        self.root.title("Notaly - Gestor de Notas")
        
        # Usamos una resolución más amigable para pantallas pequeñas (ej. laptops de 1366x768)
        self.root.geometry("1200x700")
        
        # Maximizar por defecto en Windows para aprovechar todo el espacio
        try:
            self.root.state('zoomed')
        except:
            pass
        
        # --- Configurar icono de la ventana ---
        def resource_path(relative_path):
            """ Obtiene la ruta absoluta al recurso, funciona para dev y para PyInstaller """
            # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
            base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
            return os.path.join(base_path, relative_path)
            
        try:
            icon_path = resource_path("app_icon.ico")
            self.root.iconbitmap(icon_path)
        except Exception as e:
            logger.warning(f"No se pudo cargar el icono de la ventana: {e}")

        # --- Fuentes (Cross-platform) ---
        # Seleccionar una fuente base según el sistema operativo para una apariencia nativa.
        if platform.system() == "Darwin":  # macOS
            base_font = "Helvetica"
        elif platform.system() == "Windows": # Windows
            base_font = "Segoe UI"
        else:  # Linux y otros
            # Usamos una fuente común y de alta calidad para Linux.
            base_font = "DejaVu Sans"

        # --- Fuentes ---
        self.font_title = (base_font, 34, "bold")
        self.font_card_title = (base_font, 22, "bold")
        self.font_button = (base_font, 13, "bold")
        self.font_body = (base_font, 14)
        self.font_grid_header = (base_font, 13, "bold")
        self.font_grid_subheader = (base_font, 11)
        self.font_grid_body = (base_font, 14)
        self.font_grid_body_bold = (base_font, 14, "bold")

        # --- Paleta de Colores ---
        self.paleta = {
            "fondo_app": "#F3F4F6",      
            "fondo_card": "#FFFFFF",
            "texto_principal": "#111827", 
            "texto_secundario": "#6B7280",
            "borde_sutil": "#E5E7EB",
            "grid_bg": "#E5E7EB",        

            "azul_fg": "#2563EB", "azul_hover": "#1D4ED8",
            "verde_fg": "#10B981", "verde_hover": "#059669",
            "rojo_fuerte": "#EF4444",

            "card_btn_fg": "#F9FAFB",
            "card_btn_hover": "#F3F4F6",
            
            "card_azul_texto": "#2563EB",
            "card_verde_texto": "#10B981",
            "card_rojo_texto": "#EF4444",

            "trimestre_1": "#E0F2FE", "trimestre_2": "#D1FAE5", "trimestre_3": "#EDE9FE", "final": "#FEF3C7",
            "zebra_par": "#F9FAFB",
            "zebra_impar": "#FFFFFF",
            "texto_notas": "#111827",
            "texto_subtitulo": "#4B5563"
        }
        
        # --- Inicialización de Datos y Configuración ---
        self.root.configure(fg_color=self.paleta["fondo_app"])
        self.ruta_datos = self._obtener_o_configurar_ruta_datos()
        if not self.ruta_datos:
            messagebox.showerror("Configuración Requerida", "Se requiere una carpeta de datos para iniciar. La aplicación se cerrará.")
            sys.exit()

        self.datos = gestor_datos.cargar_datos(self.ruta_datos)
        self.frame_actual = None
        self.colegio_seleccionado = None
        self.curso_seleccionado = None
        self.hay_cambios_sin_guardar = False
        self.grid_container = None
        self._resize_timer = None

        # Validación para notas (0-10, permite decimales)
        self.vcmd = (self.root.register(self.solo_numeros), '%P')
        # Validación para cantidades (solo enteros positivos)
        self.vcmd_int = (self.root.register(self.solo_enteros), '%P')

        # Protocolo de cierre para advertir sobre cambios sin guardar
        self.root.protocol("WM_DELETE_WINDOW", self.al_cerrar)
        self.root.bind('<Configure>', self._on_resize) # Bind resize event

        # Firma fija
        footer_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=15)
        ctk.CTkLabel(
            footer_frame, 
            text="Software desarrollado por Ignacio Olmedo © 2026",
            font=(base_font, 12, "italic"),
            text_color=self.paleta["texto_secundario"]
        ).pack()

        self.mostrar_pantalla_colegios()

    def _on_resize(self, event):
        # Este evento se dispara con cualquier cambio de configuración, solo nos importa el tamaño de la ventana principal
        if event.widget == self.root:
            # Si estamos en la pantalla de la planilla, desactivamos temporalmente la columna responsiva para evitar el lag
            if self.grid_container:
                self.grid_container.grid_columnconfigure(2, weight=0)
            # Cancelamos el temporizador anterior para reiniciar la cuenta
            if self._resize_timer:
                self.root.after_cancel(self._resize_timer)
            # Establecemos un nuevo temporizador que se activará después de un breve retraso
            self._resize_timer = self.root.after(150, self._on_resize_end) # 150ms de retraso

    def _on_resize_end(self):
        # Esto se llama cuando el redimensionamiento se ha detenido
        # Si estamos en la pantalla de la planilla, reactivamos la columna responsiva
        if self.grid_container:
            self.grid_container.grid_columnconfigure(2, weight=1)

    def _marcar_cambios_pendientes(self, event=None):
        self.hay_cambios_sin_guardar = True

    def solo_numeros(self, P):
        if P == "":
            return True
        
        # Reemplazamos la coma por un punto para una validación unificada.
        P_normalized = P.replace(',', '.')

        # Permitir estados intermedios como empezar con un punto decimal.
        if P_normalized == ".":
            return True

        try:
            # Intentamos convertir el valor a un número flotante.
            valor = float(P_normalized)
        except ValueError:
            # Si la conversión falla, el formato es inválido (ej: "5.5.5" o "abc").
            return False

        # Validamos que el número esté en el rango de 0 a 10.
        return 0 <= valor <= NOTA_MAXIMA
        
    def solo_enteros(self, P):
        """Función de validación que solo permite números enteros positivos."""
        # Permite una cadena vacía (cuando el usuario borra el campo)
        # o una cadena que contiene solo dígitos.
        if P == "" or P.isdigit():
            return True
        else:
            return False
        
    def limpiar_pantalla(self):
        # Desvinculamos el scroll global por si venimos de la planilla
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Shift-MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")
        self.root.unbind_all("<Shift-Button-4>")
        self.root.unbind_all("<Shift-Button-5>")
        
        if hasattr(self, 'search_dropdown') and self.search_dropdown:
            self.search_dropdown.destroy()
            self.search_dropdown = None
            
        if self.frame_actual:
            self.frame_actual.pack_forget()
            self.frame_actual.destroy()

    # --- CRUD COLEGIOS ---
    def mostrar_pantalla_colegios(self):
        self.limpiar_pantalla()
        self.colegio_seleccionado = None
        self.curso_seleccionado = None
        self.grid_container = None
        self.frame_actual = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame_actual.pack(fill=tk.BOTH, expand=True)
        
        scroll_frame = ctk.CTkScrollableFrame(self.frame_actual, fg_color="transparent")
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        header.pack(fill=tk.X, pady=(10, 30), padx=10)

        # 1. Extremo Izquierdo (Identidad de Marca)
        left_frame = ctk.CTkFrame(header, fg_color="transparent")
        left_frame.pack(side=tk.LEFT)
        
        # --- Nivel Superior: Logo + NOTALY ---
        top_brand_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        top_brand_frame.pack(side=tk.TOP, anchor="w")
        
        try:
            from PIL import Image
            import os, sys
            base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
            icon_path = os.path.join(base_path, "app_icon.ico")
            img = ctk.CTkImage(light_image=Image.open(icon_path), size=(32, 32))
            ctk.CTkLabel(top_brand_frame, text="", image=img).pack(side=tk.LEFT, padx=(0, 10))
        except Exception:
            ctk.CTkLabel(top_brand_frame, text="✏️", font=("Segoe UI Emoji", 26)).pack(side=tk.LEFT, padx=(0, 10))
            
        ctk.CTkLabel(
            top_brand_frame, 
            text="NOTALY", 
            font=("Inter", 26, "bold"), 
            text_color=self.paleta["azul_fg"]
        ).pack(side=tk.LEFT)
        
        # --- Nivel Inferior: Contexto de Sección ---
        ctk.CTkLabel(
            left_frame, 
            text="Mis Instituciones", 
            font=("Inter", 16), 
            text_color="#4B5563"
        ).pack(side=tk.TOP, anchor="w", pady=(2, 0))

        # 3. Extremo Derecho (Botones de Acción Global)
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side=tk.RIGHT)
        
        ctk.CTkButton(
            right_frame, text="+ Nueva Institución", 
            fg_color=self.paleta["texto_principal"], hover_color="#374151",
            text_color="#FFFFFF", font=self.font_button, corner_radius=8, height=36,
            command=lambda: self.modal_crear("colegio")
        ).pack(side=tk.RIGHT)
        
        ctk.CTkButton(
            right_frame, text="📥 Importar Datos", 
            fg_color="transparent", border_width=1, border_color=self.paleta["borde_sutil"],
            text_color=self.paleta["texto_secundario"], hover_color=self.paleta["card_btn_hover"],
            font=self.font_button, corner_radius=8, height=36,
            command=self.importar_datos
        ).pack(side=tk.RIGHT, padx=10)

        # 2. Centro (Barra de Búsqueda Predictiva Global)
        center_frame = ctk.CTkFrame(header, fg_color="transparent")
        center_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=40)
        
        search_entry = ctk.CTkEntry(
            center_frame, 
            placeholder_text="Buscar alumno por nombre, curso o colegio...",
            height=40, font=(self.font_body[0], 14), 
            fg_color="#FFFFFF", text_color="#111827",
            border_color="#D1D5DB", border_width=1, corner_radius=8
        )
        search_entry.pack(fill=tk.X, padx=20)
        
        # Desplegable Flotante (Menú Predictivo)
        self.search_dropdown = ctk.CTkScrollableFrame(
            self.root, fg_color="#FFFFFF", border_width=1, border_color="#E5E7EB", 
            corner_radius=8, height=200
        )
        self.search_dropdown.place_forget()

        def ocultar_dropdown(event=None):
            if hasattr(self, 'search_dropdown') and self.search_dropdown:
                self.search_dropdown.place_forget()

        def mostrar_dropdown(event=None):
            if self.search_dropdown is None:
                return
            # Calcular posición absoluta respecto al root para que flote por encima del scroll_frame
            x = search_entry.winfo_rootx() - self.root.winfo_rootx()
            y = search_entry.winfo_rooty() - self.root.winfo_rooty() + search_entry.winfo_height() + 4
            width = search_entry.winfo_width()
            self.search_dropdown.configure(width=width)
            self.search_dropdown.place(x=x, y=y)
            self.search_dropdown.lift()

        def on_key_release(event):
            texto = search_entry.get().strip()
            self.filtrar_busqueda_predictiva(texto, self.search_dropdown)
            if texto:
                mostrar_dropdown()
            else:
                ocultar_dropdown()

        search_entry.bind("<KeyRelease>", on_key_release)
        # Ocultar si pierde el foco (pequeño delay para permitir clicks en los resultados)
        search_entry.bind("<FocusOut>", lambda e: self.root.after(150, ocultar_dropdown))

        grid_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        grid_frame.pack(fill=tk.BOTH, expand=True)
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        for idx, nombre_ant in enumerate(list(self.datos.get(K_COLEGIOS, {}).keys())):
            row = idx // 4
            col = idx % 4
            
            # Calcular subtítulo
            cursos = self.datos[K_COLEGIOS][nombre_ant].get(K_CURSOS, {})
            num_cursos = len(cursos)
            total_alumnos = sum(len(c.get(K_ALUMNOS, {})) for c in cursos.values())
            
            txt_cursos = "1 Curso" if num_cursos == 1 else f"{num_cursos} Cursos"
            txt_alumnos = "1 Alumno" if total_alumnos == 1 else f"{total_alumnos} Alumnos"
            subtitulo = f"{txt_cursos}  •  {txt_alumnos}"

            self._crear_tarjeta(
                parent=grid_frame,
                nombre_entidad=nombre_ant,
                tipo_entidad="colegio",
                boton_principal_config={
                    "text": "Entrar →",
                    "fg_color": self.paleta["azul_fg"],
                    "hover_color": self.paleta["azul_hover"],
                    "text_color": "#FFFFFF",
                    "accion": self.renombrar_y_abrir_colegio
                },
                row=row,
                col=col,
                subtitulo=subtitulo
            )

    def _crear_tarjeta(self, parent, nombre_entidad, tipo_entidad, boton_principal_config, row, col, subtitulo=""):
        card = ctk.CTkFrame(parent, fg_color="#FFFFFF", border_width=1, border_color=self.paleta["borde_sutil"], corner_radius=12)
        card.grid(row=row, column=col, sticky="nsew", padx=15, pady=15)
        
        # Top Bar (Esquina superior derecha para la Papelera)
        top_bar = ctk.CTkFrame(card, fg_color="transparent")
        top_bar.pack(fill=tk.X, padx=8, pady=(8, 0))
        
        ctk.CTkButton(
            top_bar, text="🗑",
            fg_color="transparent",
            hover_color="#ef4444",
            text_color="#9CA3AF",
            corner_radius=6, width=28, height=28, font=("Segoe UI Emoji", 14),
            command=lambda n=nombre_entidad: self.eliminar_entidad(tipo_entidad, n)
        ).pack(side=tk.RIGHT)
        
        # Avatar (Monograma Dinámico) - Solo para colegios
        if tipo_entidad == "colegio":
            avatar_frame = ctk.CTkFrame(card, fg_color="#E0E7FF", corner_radius=100, width=70, height=70)
            avatar_frame.pack(pady=(0, 15))
            avatar_frame.pack_propagate(False) # Mantiene el círculo perfecto
            inicial = nombre_entidad[0].upper() if nombre_entidad else "?"
            ctk.CTkLabel(avatar_frame, text=inicial, font=(self.font_title[0], 32, "bold"), text_color="#3730A3").pack(expand=True)
            
        # Jerarquía del Bloque de Información
        entry_font = (self.font_body[0], 20, "bold")
        ent_nombre = ctk.CTkEntry(card, font=entry_font, fg_color="transparent", text_color=self.paleta["texto_principal"], border_width=0, justify="center")
        ent_nombre.insert(0, nombre_entidad)
        
        if subtitulo:
            ent_nombre.pack(fill=tk.X, padx=20, pady=(0, 2)) # Margen reducido para agrupar visualmente
            ctk.CTkLabel(card, text=subtitulo, font=(self.font_body[0], 12), text_color="#4B5563").pack(pady=(0, 20))
        else:
            ent_nombre.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Corrección de Asimetría en la Base (Botón Centrado)
        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(0, 20), padx=20)
        
        ctk.CTkButton(
            btn_frame, text=boton_principal_config["text"],
            fg_color=boton_principal_config["fg_color"],
            hover_color=boton_principal_config["hover_color"],
            text_color=boton_principal_config["text_color"],
            font=self.font_button, corner_radius=8, height=36,
            command=lambda n=nombre_entidad, e=ent_nombre: boton_principal_config["accion"](n, e)
        ).pack(expand=True, fill=tk.X)

    def renombrar_y_abrir_colegio(self, nombre_ant, widget_entry):
        nuevo = widget_entry.get().strip().upper()
        if nuevo and nuevo != nombre_ant:
            if nuevo in self.datos[K_COLEGIOS]:
                messagebox.showerror("Error al Renombrar", f"Ya existe una institución con el nombre '{nuevo}'.\nPor favor, elige un nombre diferente.")
                widget_entry.delete(0, tk.END)
                widget_entry.insert(0, nombre_ant) # Revertir texto en la UI
                return

            self.datos[K_COLEGIOS][nuevo] = self.datos[K_COLEGIOS].pop(nombre_ant)
            self._guardar_datos_con_recuperacion()
        self.mostrar_pantalla_cursos(nuevo if nuevo else nombre_ant)

    # --- CRUD CURSOS ---
    def mostrar_pantalla_cursos(self, nombre_colegio):
        self.limpiar_pantalla()
        self.colegio_seleccionado = nombre_colegio
        self.curso_seleccionado = None
        self.grid_container = None
        self.frame_actual = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame_actual.pack(fill=tk.BOTH, expand=True)

        scroll_frame = ctk.CTkScrollableFrame(self.frame_actual, fg_color="transparent")
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        header.pack(fill=tk.X, pady=(10, 30), padx=10)
        
        ctk.CTkButton(
            header, text="← Volver", font=self.font_body, 
            command=self.mostrar_pantalla_colegios,
            fg_color="transparent", text_color=self.paleta["texto_secundario"],
            hover_color=self.paleta["card_btn_hover"], width=80
        ).pack(side=tk.LEFT)
        
        ctk.CTkLabel(header, text=f"Cursos en: {nombre_colegio}", font=self.font_title, 
                     text_color=self.paleta["texto_principal"]).pack(side=tk.LEFT, padx=30)

        ctk.CTkButton(
            header, text="+ Nuevo Curso", 
            fg_color=self.paleta["texto_principal"], hover_color="#374151",
            text_color="#FFFFFF", font=self.font_button, corner_radius=8, height=36,
            command=lambda: self.modal_crear("curso")
        ).pack(side=tk.RIGHT)

        grid_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        grid_frame.pack(fill=tk.BOTH, expand=True)
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        cursos = self.datos[K_COLEGIOS][nombre_colegio].get(K_CURSOS, {})
        for idx, nombre_curso in enumerate(list(cursos.keys())):
            row = idx // 4
            col = idx % 4
            
            # Calcular subtítulo
            alumnos_data = cursos[nombre_curso].get(K_ALUMNOS, {})
            num_alumnos = len(alumnos_data)
            
            aprobados = 0
            desaprobados = 0
            try:
                from core.calculos import procesar_calificaciones_alumno
                for al_data in alumnos_data.values():
                    res = procesar_calificaciones_alumno(al_data["trimestres"])
                    nota_final = res.get("nota_final_total_redondeada")
                    if nota_final is not None:
                        if nota_final >= 6:
                            aprobados += 1
                        else:
                            desaprobados += 1
            except Exception:
                pass
                
            subtitulo = "1 Alumno" if num_alumnos == 1 else f"{num_alumnos} Alumnos"
            if aprobados > 0 or desaprobados > 0:
                subtitulo += f"\n✅ {aprobados} aprobados  •  ❌ {desaprobados} desaprobados"

            self._crear_tarjeta(
                parent=grid_frame,
                nombre_entidad=nombre_curso,
                tipo_entidad="curso",
                boton_principal_config={
                    "text": "Ver Planilla",
                    "fg_color": self.paleta["azul_fg"],
                    "hover_color": self.paleta["azul_hover"],
                    "text_color": "#FFFFFF",
                    "accion": self.renombrar_y_abrir_planilla
                },
                row=row,
                col=col,
                subtitulo=subtitulo
            )

    def renombrar_y_abrir_planilla(self, nombre_ant, widget_e):
        nuevo = widget_e.get().strip().upper()
        if nuevo and nuevo != nombre_ant:
            col = self.colegio_seleccionado
            if nuevo in self.datos[K_COLEGIOS][col][K_CURSOS]:
                messagebox.showerror("Error al Renombrar", f"Ya existe un curso con el nombre '{nuevo}' en esta institución.\nPor favor, elige un nombre diferente.")
                widget_e.delete(0, tk.END)
                widget_e.insert(0, nombre_ant) # Revertir texto en la UI
                return

            self.datos[K_COLEGIOS][col][K_CURSOS][nuevo] = self.datos[K_COLEGIOS][col][K_CURSOS].pop(nombre_ant)
            self._guardar_datos_con_recuperacion()
        self.mostrar_apartado_curso(nuevo if nuevo else nombre_ant)

    # --- MODALES ---
    def modal_crear(self, tipo):
        ventana = ctk.CTkToplevel(self.root)
        ventana.title(f"Añadir {tipo.capitalize()}")
        alto = 350 if tipo == "curso" else 250
        ventana.geometry(f"450x{alto}")
        ventana.configure(fg_color="white")
        
        try:
            import os, sys
            base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
            icon_path = os.path.join(base_path, "app_icon.ico")
            ventana.after(200, lambda: ventana.iconbitmap(icon_path))
        except Exception:
            pass
            
        ventana.grab_set()

        ctk.CTkLabel(ventana, text=f"Nuevo {tipo.capitalize()}", font=self.font_card_title, text_color=self.paleta["azul_fg"]).pack(pady=20)
        
        instruccion = "Nombre de la Institución:" if tipo == "colegio" else "Año y División:"
        ctk.CTkLabel(ventana, text=instruccion, font=self.font_body).pack(anchor=tk.W, padx=50)
        ent_nom = ctk.CTkEntry(ventana, font=self.font_body, border_width=1, border_color="#ccc", corner_radius=6)
        ent_nom.pack(pady=10, padx=50, fill=tk.X, ipady=5)

        ent_cant = None
        if tipo == "curso":
            ctk.CTkLabel(ventana, text="Cantidad inicial de alumnos:", font=self.font_body).pack(anchor=tk.W, padx=50)
            ent_cant = ctk.CTkEntry(ventana, font=self.font_body, justify=tk.CENTER, border_width=1, 
                                    border_color="#ccc", corner_radius=6, validate='key', 
                                    validatecommand=self.vcmd_int)
            ent_cant.insert(0, "")
            ent_cant.pack(pady=10, padx=50, fill=tk.X, ipady=5)

        def confirmar():
            nom = ent_nom.get().strip().upper()
            if not nom: return
            
            col = self.colegio_seleccionado
            if tipo == "colegio":
                if K_COLEGIOS not in self.datos: self.datos[K_COLEGIOS] = {}
                if nom not in self.datos[K_COLEGIOS]:
                    self.datos[K_COLEGIOS][nom] = {K_CURSOS: {}}
                    self.mostrar_pantalla_colegios()
            else:
                # Asegurarse de que el diccionario de cursos exista antes de intentar acceder a él.
                # Esto previene el KeyError si los datos están incompletos.
                if K_CURSOS not in self.datos[K_COLEGIOS][col]:
                    self.datos[K_COLEGIOS][col][K_CURSOS] = {}

                cant_s = ent_cant.get().strip() if ent_cant else "1"
                cant = int(cant_s) if cant_s.isdigit() else 1
                if nom not in self.datos[K_COLEGIOS][col][K_CURSOS]:
                    alumnos = {
                        str(i): {
                            K_NOMBRE: "",
                            K_TRIMESTRES: crear_trimestres_vacios(),
                        } for i in range(1, cant + 1)
                    }
                    self.datos[K_COLEGIOS][col][K_CURSOS][nom] = {
                        K_NOMBRES_COLUMNAS: {
                            t: list(NOMBRES_COLUMNAS_DEFAULT) for t in NOMBRES_TRIMESTRES
                        },
                        K_ALUMNOS: alumnos,
                    }
                    self.mostrar_pantalla_cursos(col)
            
            self._guardar_datos_con_recuperacion()
            ventana.destroy()

        ctk.CTkButton(ventana, text="Confirmar", fg_color=self.paleta["azul_fg"], hover_color=self.paleta["azul_hover"], 
                      command=confirmar, height=35, corner_radius=8).pack(pady=20, padx=50, fill=tk.X)

    # --- PLANILLA DE NOTAS ---
    def mostrar_apartado_curso(self, nombre_curso):
        self.limpiar_pantalla()
        self.curso_seleccionado = nombre_curso
        self.hay_cambios_sin_guardar = False
        self.frame_actual = ctk.CTkFrame(self.root, fg_color=self.paleta["fondo_card"], corner_radius=0)
        self.frame_actual.pack(fill=tk.BOTH, expand=True)

        toolbar = ctk.CTkFrame(self.frame_actual, fg_color=self.paleta["fondo_card"], border_width=0, corner_radius=0)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=20, pady=15)
        
        left_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        ctk.CTkButton(left_frame, text="← Volver", command=self.accion_volver_desde_planilla, fg_color="transparent", text_color=self.paleta["texto_secundario"], hover_color=self.paleta["card_btn_hover"], font=self.font_body, width=80).pack(side=tk.LEFT, padx=(0, 15))
        
        texto_cabecera = f"{self.colegio_seleccionado}   |   {nombre_curso}"
        ctk.CTkLabel(left_frame, text=texto_cabecera, font=self.font_card_title, text_color=self.paleta["texto_principal"]).pack(side=tk.LEFT)
        
        right_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        export_frame = ctk.CTkFrame(right_frame, fg_color=self.paleta["fondo_app"], corner_radius=6)
        export_frame.pack(side=tk.LEFT, padx=15)
        ctk.CTkButton(export_frame, text="PDF", fg_color="transparent", text_color=self.paleta["texto_secundario"], hover_color=self.paleta["card_btn_hover"], font=self.font_body, width=40, command=lambda: self.exportar_planilla_pdf(nombre_curso)).pack(side=tk.LEFT, padx=2, pady=2)
        ctk.CTkButton(export_frame, text="TXT", fg_color="transparent", text_color=self.paleta["texto_secundario"], hover_color=self.paleta["card_btn_hover"], font=self.font_body, width=40, command=lambda: self.exportar_planilla_texto(nombre_curso)).pack(side=tk.LEFT, padx=2, pady=2)
        ctk.CTkButton(export_frame, text="CSV", fg_color="transparent", text_color=self.paleta["texto_secundario"], hover_color=self.paleta["card_btn_hover"], font=self.font_body, width=40, command=lambda: self.exportar_planilla(nombre_curso)).pack(side=tk.LEFT, padx=2, pady=2)
        
        ctk.CTkButton(right_frame, text="+ Alumno", fg_color=self.paleta["texto_principal"], hover_color="#374151", corner_radius=6, font=self.font_button, width=100, command=lambda: self.agregar_alumno(nombre_curso)).pack(side=tk.LEFT, padx=10)
        ctk.CTkButton(right_frame, text="GUARDAR Y CALCULAR", fg_color=self.paleta["azul_fg"], hover_color=self.paleta["azul_hover"], font=self.font_button, corner_radius=6, width=150, command=lambda: self.guardar_notas_cuadricula(nombre_curso)).pack(side=tk.LEFT)

        # Usamos un CTkScrollableFrame para simplificar enormemente el manejo del scroll
        # --- Contenedor con Scrollbars Horizontal y Vertical ---
        canvas_container = ctk.CTkFrame(self.frame_actual, fg_color="transparent")
        canvas_container.pack(fill=tk.BOTH, expand=True)
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)

        canvas = ctk.CTkCanvas(canvas_container, bg=self.paleta["grid_bg"], highlightthickness=0)
        
        v_scrollbar = ctk.CTkScrollbar(canvas_container, orientation="vertical", command=canvas.yview)
        h_scrollbar = ctk.CTkScrollbar(canvas_container, orientation="horizontal", command=canvas.xview)
        
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        canvas.grid(row=0, column=0, sticky="nsew")

        # --- Bindings para Scroll con la Rueda del Ratón ---
        # --- Bindings para Scroll con la Rueda del Ratón ---
        def _on_mousewheel_v(event):
            if not canvas.winfo_exists(): return
            delta = -1 * event.delta if sys.platform == "darwin" else int(-1 * (event.delta / 120))
            if delta != 0:
                canvas.yview_scroll(delta, "units")

        def _on_mousewheel_h(event):
            if not canvas.winfo_exists(): return
            delta = -1 * event.delta if sys.platform == "darwin" else int(-1 * (event.delta / 120))
            if delta != 0:
                canvas.xview_scroll(delta, "units")

        def bind_scroll_events():
            canvas.bind_all("<MouseWheel>", _on_mousewheel_v)
            canvas.bind_all("<Shift-MouseWheel>", _on_mousewheel_h)
            canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units") if canvas.winfo_exists() else None)
            canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units") if canvas.winfo_exists() else None)
            canvas.bind_all("<Shift-Button-4>", lambda e: canvas.xview_scroll(-1, "units") if canvas.winfo_exists() else None)
            canvas.bind_all("<Shift-Button-5>", lambda e: canvas.xview_scroll(1, "units") if canvas.winfo_exists() else None)

        def unbind_scroll_events(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Shift-MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
            canvas.unbind_all("<Shift-Button-4>")
            canvas.unbind_all("<Shift-Button-5>")

        bind_scroll_events()
        canvas.bind("<Destroy>", unbind_scroll_events)
        
        # Permitir arrastrar la planilla con clic derecho o botón medio
        def start_pan(event):
            canvas.scan_mark(event.x, event.y)
            
        def pan(event):
            canvas.scan_dragto(event.x, event.y, gain=1)

        canvas.bind("<ButtonPress-2>", start_pan)
        canvas.bind("<B2-Motion>", pan)
        canvas.bind("<ButtonPress-3>", start_pan)
        canvas.bind("<B3-Motion>", pan)

        self.grid_container = ctk.CTkFrame(canvas, fg_color=self.paleta["grid_bg"])
        self.canvas_window = canvas.create_window((0, 0), window=self.grid_container, anchor="nw")

        def on_frame_configure(event):
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)

        def on_canvas_configure(event):
            if self.grid_container is None or not self.grid_container.winfo_exists():
                return
            req_w = self.grid_container.winfo_reqwidth()
            if event.width > req_w:
                canvas.itemconfig(self.canvas_window, width=event.width)
            else:
                canvas.itemconfig(self.canvas_window, width="")

        self.grid_container.bind("<Configure>", on_frame_configure)
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Hacemos que la columna del nombre del alumno sea la que se expanda
        self.grid_container.grid_columnconfigure(2, weight=1, minsize=250) # Asegura un ancho mínimo de 250px

        curso_data = self.datos[K_COLEGIOS][self.colegio_seleccionado][K_CURSOS][nombre_curso]
        self.widgets_entradas, self.widgets_resultados, self.widgets_nombres_alumnos, self.widgets_recuperatorios = {}, {}, {}, {}
        self.widgets_nombres_cols = {t: [] for t in NOMBRES_TRIMESTRES}
        self.matriz_entradas = {}

        # Headers  
        ctk.CTkLabel(self.grid_container, text="N°", font=self.font_grid_header, fg_color=self.paleta["fondo_card"], text_color=self.paleta["texto_principal"], corner_radius=0).grid(row=0, column=1, rowspan=2, sticky="nsew", padx=1, pady=1)
        ctk.CTkLabel(self.grid_container, text="Nombre del Alumno", font=self.font_grid_header, fg_color=self.paleta["fondo_card"], text_color=self.paleta["texto_principal"], corner_radius=0).grid(row=0, column=2, rowspan=2, sticky="nsew", padx=1, pady=1)

        col_off = 3
        for t, color in zip(NOMBRES_TRIMESTRES, [self.paleta["trimestre_1"], self.paleta["trimestre_2"], self.paleta["trimestre_3"]]):
            ctk.CTkLabel(self.grid_container, text=t, fg_color=color, text_color=self.paleta["texto_principal"], font=self.font_grid_header).grid(row=0, column=col_off, columnspan=6, sticky="nsew", padx=(1, 3) if t != NOMBRES_TRIMESTRES[-1] else 1, pady=1)
            for j, nom in enumerate(curso_data["nombres_columnas"][t]):
                e = ctk.CTkEntry(self.grid_container, justify=tk.CENTER, width=60, font=self.font_grid_subheader, fg_color=self.paleta["fondo_card"], text_color=self.paleta["texto_subtitulo"], border_width=0, corner_radius=0)
                e.insert(0, nom)
                e.bind("<KeyRelease>", self._marcar_cambios_pendientes)
                e.grid(row=1, column=col_off + j, sticky="nsew", padx=1, pady=1)
                self.widgets_nombres_cols[t].append(e)
            ctk.CTkLabel(self.grid_container, text="Prom", width=60, font=self.font_grid_subheader, fg_color=self.paleta["fondo_card"], text_color=self.paleta["texto_subtitulo"]).grid(row=1, column=col_off+4, sticky="nsew", padx=1, pady=1)
            ctk.CTkLabel(self.grid_container, text="Recup.", width=60, font=self.font_grid_subheader, fg_color=self.paleta["fondo_card"], text_color=self.paleta["texto_subtitulo"]).grid(row=1, column=col_off+5, sticky="nsew", padx=(1, 3) if t != NOMBRES_TRIMESTRES[-1] else 1, pady=1)
            col_off += 6
        
        # PROMEDIOS FINALES
        ctk.CTkLabel(self.grid_container, text="PROMEDIOS FINALES", fg_color=self.paleta["final"], text_color=self.paleta["texto_principal"], font=self.font_grid_header).grid(row=0, column=21, columnspan=4, sticky="nsew", padx=(3, 1), pady=1)
        
        for i, txt in enumerate(["T1", "T2", "T3", "TOTAL"]):
            gap = (3, 1) if i == 0 else 1
            ctk.CTkLabel(self.grid_container, text=txt, width=60, font=self.font_grid_subheader, fg_color=self.paleta["fondo_card"], text_color=self.paleta["texto_subtitulo"]).grid(row=1, column=21+i, sticky="nsew", padx=gap, pady=1)

        # Dibujar las filas de los alumnos
        for i, id_al in enumerate(sorted(curso_data[K_ALUMNOS].keys(), key=int)):
            self.dibujar_fila_alumno(i+2, id_al, curso_data[K_ALUMNOS][id_al], nombre_curso)

    def dibujar_fila_alumno(self, row, id_al, al_data, nombre_curso):
        bg_color = self.paleta["zebra_par"] if row % 2 == 0 else self.paleta["zebra_impar"]
        
        ctk.CTkButton(self.grid_container, text="🗑", fg_color=bg_color, text_color=self.paleta["texto_secundario"], hover_color="#ef4444",
                      width=25, corner_radius=0, font=("Segoe UI Emoji", 14), command=lambda: self.eliminar_entidad("alumno", id_al, nombre_curso)).grid(row=row, column=0, sticky="nsew", padx=1, pady=1)
        
        ctk.CTkLabel(self.grid_container, text=id_al, font=self.font_grid_body, fg_color=bg_color, text_color=self.paleta["texto_principal"]).grid(row=row, column=1, sticky="nsew", padx=1, pady=1)
        
        def register_nav(ent, r, c):
            self.matriz_entradas[(r, c)] = ent
            ent.bind("<Up>", lambda e, rr=r, cc=c: self._navigate_grid(e, rr, cc, "Up"))
            ent.bind("<Down>", lambda e, rr=r, cc=c: self._navigate_grid(e, rr, cc, "Down"))
            ent.bind("<Left>", lambda e, rr=r, cc=c: self._navigate_grid(e, rr, cc, "Left"))
            ent.bind("<Right>", lambda e, rr=r, cc=c: self._navigate_grid(e, rr, cc, "Right"))

        # Create CTkFonts to ensure proper DPI scaling on native tk.Entry
        f_norm = ctk.CTkFont(family=self.font_grid_body[0], size=self.font_grid_body[1])
        f_bold = ctk.CTkFont(family=self.font_grid_body_bold[0], size=self.font_grid_body_bold[1], weight="bold")

        ent_n = tk.Entry(self.grid_container, borderwidth=0, bg=bg_color, font=f_bold, fg=self.paleta["texto_principal"], relief="flat")
        ent_n.insert(0, al_data.get(K_NOMBRE, "")); ent_n.grid(row=row, column=2, sticky="nsew", padx=1, pady=1)
        ent_n.bind("<KeyRelease>", self._marcar_cambios_pendientes)
        self.widgets_nombres_alumnos[id_al] = ent_n
        register_nav(ent_n, row, 2)

        self.widgets_entradas[id_al], self.widgets_resultados[id_al], self.widgets_recuperatorios[id_al] = [], {"trim": [], "fin": []}, []
        c_idx = 3
        for t_idx, t_nom in enumerate(NOMBRES_TRIMESTRES):
            e_dict = {"p": [], "ex": None}
            notas_data = al_data["trimestres"][t_nom]
            for j in range(3):
                e = tk.Entry(self.grid_container, width=6, justify=tk.CENTER, font=f_norm, bg=bg_color, fg=self.paleta["texto_notas"], borderwidth=0, relief="flat", validate='key', validatecommand=self.vcmd)
                val = notas_data["principales"][j]
                if val is not None:
                    e.insert(0, str(int(val)) if isinstance(val, float) and val.is_integer() else str(val))
                e.bind("<KeyRelease>", self._marcar_cambios_pendientes)
                e.grid(row=row, column=c_idx, sticky="nsew", padx=1, pady=1)
                register_nav(e, row, c_idx)
                c_idx += 1; e_dict["p"].append(e)
            
            ex = tk.Entry(self.grid_container, width=6, justify=tk.CENTER, font=f_norm, bg=bg_color, fg=self.paleta["texto_notas"], borderwidth=0, relief="flat", validate='key', validatecommand=self.vcmd)
            val_ex = notas_data[K_EXTRAS][0] if notas_data[K_EXTRAS] else None
            if val_ex is not None:
                ex.insert(0, str(int(val_ex)) if isinstance(val_ex, float) and val_ex.is_integer() else str(val_ex))
            ex.bind("<KeyRelease>", self._marcar_cambios_pendientes)
            ex.grid(row=row, column=c_idx, sticky="nsew", padx=1, pady=1)
            register_nav(ex, row, c_idx)
            c_idx += 1; e_dict["ex"] = ex
            self.widgets_entradas[id_al].append(e_dict)
            
            # Promedio trimestral (NEGRITA solicitada)
            l = ctk.CTkLabel(self.grid_container, text="-", font=self.font_grid_body_bold, fg_color=bg_color, text_color=self.paleta["texto_notas"], anchor="center")
            l.grid(row=row, column=c_idx, sticky="nsew", padx=1, pady=1); c_idx += 1
            
            # --- NUEVO CAMPO RECUPERATORIO (NEGRITA solicitada) ---
            e_recup = tk.Entry(self.grid_container, width=6, justify=tk.CENTER, font=f_bold, bg=bg_color, fg=self.paleta["texto_notas"], borderwidth=0, relief="flat", validate='key', validatecommand=self.vcmd)
            val_recup = notas_data.get(K_RECUPERATORIO)
            if val_recup is not None:
                e_recup.insert(0, str(int(val_recup)) if isinstance(val_recup, float) and val_recup.is_integer() else str(val_recup))
            e_recup.bind("<KeyRelease>", self._marcar_cambios_pendientes)
            gap = (1, 3) if t_idx < 2 else 1
            e_recup.grid(row=row, column=c_idx, sticky="nsew", padx=gap, pady=1)
            register_nav(e_recup, row, c_idx)
            c_idx += 1
            self.widgets_recuperatorios[id_al].append(e_recup)

            self.widgets_resultados[id_al]["trim"].append(l)

        # --- FILAS DE PROMEDIOS FINALES (TODAS NEGRITA solicitada) ---
        for j in range(4):
            gap = (3, 1) if j == 0 else 1
            l_f = ctk.CTkLabel(self.grid_container, text="-", font=self.font_grid_body_bold, fg_color=bg_color, text_color=self.paleta["texto_notas"], anchor="center")
            l_f.grid(row=row, column=21+j, sticky="nsew", padx=gap, pady=1)
            self.widgets_resultados[id_al]["fin"].append(l_f)
            
        # --- CÁLCULO AUTOMÁTICO Y FORMATO DE COLOR AL CARGAR ---
        res_cargados = procesar_calificaciones_alumno(al_data[K_TRIMESTRES])
        self._actualizar_promedios_ui(id_al, res_cargados)

    def _color_por_nota(self, nota: int | float | None) -> str:
        """Retorna el color de la paleta según si la nota aprueba, desaprueba, o es nula."""
        if nota is None:
            return self.paleta["texto_notas"]
        if nota < NOTA_MINIMA_APROBACION:
            return self.paleta["rojo_fuerte"]
        return self.paleta["verde_fg"]

    def _actualizar_promedios_ui(self, id_al, resultados):
        """Actualiza la UI de un alumno con los resultados calculados."""
        # Obtener el color base de la fila (Zebra striping)
        color_base_fila = self.widgets_nombres_alumnos[id_al].cget("bg")
        
        for t_idx in range(len(NOMBRES_TRIMESTRES)):
            recup_widget = self.widgets_recuperatorios[id_al][t_idx]
            prom_redondeado = resultados["promedios_crudos_redondeados"][t_idx]
            is_failing = prom_redondeado is not None and prom_redondeado <= UMBRAL_RECUPERATORIO

            if is_failing:
                # Tono amarillento suave para indicar que se habilitó el recuperatorio
                recup_widget.config(state=tk.NORMAL, bg="#FEF9E7")
            else:
                if recup_widget.get().strip() == "":
                    recup_widget.config(state=tk.DISABLED, disabledbackground=color_base_fila)
                else:
                    recup_widget.config(state=tk.NORMAL, bg=color_base_fila)

            prom_crudo_rnd = resultados["promedios_crudos_redondeados"][t_idx]
            self.widgets_resultados[id_al]["trim"][t_idx].configure(
                text=str(prom_crudo_rnd) if prom_crudo_rnd is not None else "-",
                text_color=self._color_por_nota(prom_crudo_rnd),
            )

            nota_final_rnd = resultados["notas_finales_redondeadas"][t_idx]
            self.widgets_resultados[id_al]["fin"][t_idx].configure(
                text=str(nota_final_rnd) if nota_final_rnd is not None else "-",
                text_color=self._color_por_nota(nota_final_rnd),
            )

        nota_total_rnd = resultados['nota_final_total_redondeada']
        self.widgets_resultados[id_al]["fin"][3].configure(
            text=str(nota_total_rnd) if nota_total_rnd is not None else "-",
            text_color=self._color_por_nota(nota_total_rnd),
        )

    def _navigate_grid(self, event, row, col, direction):
        if direction == "Left":
            if event.widget.index(tk.INSERT) > 0: return
        elif direction == "Right":
            if event.widget.index(tk.INSERT) < len(event.widget.get()): return
        
        while True:
            if direction == "Left": col -= 1
            elif direction == "Right": col += 1
            elif direction == "Up": row -= 1
            elif direction == "Down": row += 1
            
            if row < 0 or row > 2000 or col < 0 or col > 50:
                break
                
            if (row, col) in self.matriz_entradas:
                ent = self.matriz_entradas[(row, col)]
                if ent.cget("state") == tk.NORMAL:
                    ent.focus_set()
                    if hasattr(ent, "_entry"):
                        ent._entry.select_range(0, tk.END)
                    else:
                        ent.select_range(0, tk.END)
                    return "break"

    def agregar_alumno(self, nombre_curso):
        """Agrega un nuevo alumno al curso y recarga la planilla."""
        # Guardar cambios en la UI para no perderlos
        self.guardar_notas_cuadricula(nombre_curso, show_success_message=False)
        
        nombre_colegio = self.colegio_seleccionado
        alumnos = self.datos[K_COLEGIOS][nombre_colegio][K_CURSOS][nombre_curso][K_ALUMNOS]
        nuevo_id = str(max([int(k) for k in alumnos.keys()] + [0]) + 1)
        alumnos[nuevo_id] = {
            K_NOMBRE: "",
            K_TRIMESTRES: crear_trimestres_vacios(),
        }
        self._guardar_datos_con_recuperacion()
        self.mostrar_apartado_curso(nombre_curso)

    def eliminar_entidad(self, tipo, id_ent, nombre_curso=None):
        """Elimina una entidad (colegio, curso o alumno) con confirmación del usuario."""
        if not messagebox.askyesno("Confirmar", f"¿Eliminar permanentemente este {tipo}?"):
            return
        nombre_colegio = self.colegio_seleccionado
        
        if tipo == "colegio":
            del self.datos[K_COLEGIOS][id_ent]
        elif tipo == "curso":
            del self.datos[K_COLEGIOS][nombre_colegio][K_CURSOS][id_ent]
        elif tipo == "alumno":
            # Guardar la grilla antes de borrar para no perder cambios de otros alumnos
            self.guardar_notas_cuadricula(nombre_curso, show_success_message=False)
            
            del self.datos[K_COLEGIOS][nombre_colegio][K_CURSOS][nombre_curso][K_ALUMNOS][id_ent]
            alumnos_restantes = self.datos[K_COLEGIOS][nombre_colegio][K_CURSOS][nombre_curso][K_ALUMNOS]
            self.datos[K_COLEGIOS][nombre_colegio][K_CURSOS][nombre_curso][K_ALUMNOS] = (
                AppPromedios._reordenar_alumnos(alumnos_restantes)
            )

        self._guardar_datos_con_recuperacion()

        # --- Fase 3: Actualizar la interfaz de usuario ---
        if tipo == "colegio":
            self.mostrar_pantalla_colegios()
        elif tipo == "curso":
            self.mostrar_pantalla_cursos(nombre_colegio)
        elif tipo == "alumno":
            self.mostrar_apartado_curso(nombre_curso)

    def guardar_notas_cuadricula(self, nombre_curso, show_success_message=True):
        """Guarda las notas de la cuadrícula, recalcula promedios y persiste."""
        col = self.colegio_seleccionado
        curso_data = self.datos[K_COLEGIOS][col][K_CURSOS][nombre_curso]
        for t_nom in NOMBRES_TRIMESTRES:
            curso_data[K_NOMBRES_COLUMNAS][t_nom] = [w.get() for w in self.widgets_nombres_cols[t_nom]]

        def parsear_nota(entry_widget):
            """Extrae y parsea el valor numérico de un widget Entry."""
            texto = entry_widget.get().replace(',', '.').strip()
            if not texto:
                return None
            try:
                val = float(texto)
                # Si el valor no tiene parte decimal (ej. 8.0), lo convertimos a entero (8)
                if val.is_integer():
                    return int(val)
                return val
            except ValueError:
                return None

        for id_al, al_data in curso_data[K_ALUMNOS].items():
            al_data[K_NOMBRE] = self.widgets_nombres_alumnos[id_al].get()
            widgets_alumno = self.widgets_entradas[id_al]
            for t_idx, t_nom in enumerate(NOMBRES_TRIMESTRES):
                al_data[K_TRIMESTRES][t_nom][K_PRINCIPALES] = [
                    parsear_nota(entry) for entry in widgets_alumno[t_idx]["p"]
                ]
                al_data[K_TRIMESTRES][t_nom][K_EXTRAS] = [parsear_nota(widgets_alumno[t_idx]["ex"])]
                al_data[K_TRIMESTRES][t_nom][K_RECUPERATORIO] = parsear_nota(
                    self.widgets_recuperatorios[id_al][t_idx]
                )
            res = procesar_calificaciones_alumno(al_data[K_TRIMESTRES])
            self._actualizar_promedios_ui(id_al, res)

        if self._guardar_datos_con_recuperacion():
            self.hay_cambios_sin_guardar = False
            if show_success_message:
                messagebox.showinfo("Éxito", "Cambios guardados.")
            return True
        return False

    def _obtener_o_configurar_ruta_datos(self):
        """Obtiene la ruta de datos desde config, búsqueda automática, o configuración manual."""
        # Paso 1: Intentar leer la config guardada
        ruta = gestor_datos.leer_ruta_config()
        if ruta:
            return ruta

        # Paso 2: Búsqueda automática en ubicaciones comunes
        encontrados = gestor_datos.buscar_archivos_datos()
        if len(encontrados) == 1:
            # Solo un archivo encontrado: usarlo directamente
            gestor_datos.escribir_ruta_config(encontrados[0])
            messagebox.showinfo(
                "Datos Encontrados",
                f"Se encontró automáticamente un archivo de datos existente:\n\n"
                f"{encontrados[0]}\n\n"
                f"Se usará esta ubicación."
            )
            return encontrados[0]
        elif len(encontrados) > 1:
            # Múltiples archivos: dejar que el usuario elija
            return self._seleccionar_archivo_encontrado(encontrados)

        # Paso 3: Nada encontrado, configuración manual
        return self._realizar_configuracion_inicial()

    def _seleccionar_archivo_encontrado(self, rutas):
        """Muestra un diálogo para que el usuario elija entre múltiples archivos encontrados."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Archivos de Datos Encontrados")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        seleccion: dict[str, str | None] = {"ruta": None}

        ctk.CTkLabel(
            dialog,
            text="Se encontraron varios archivos de datos.",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            dialog,
            text="Selecciona cuál deseas usar:",
            font=("Segoe UI", 13)
        ).pack(pady=(0, 15))

        radio_var = tk.StringVar(value=rutas[0])

        scroll = ctk.CTkScrollableFrame(dialog, fg_color="transparent")
        scroll.pack(fill=tk.BOTH, expand=True, padx=20)

        for ruta in rutas:
            ctk.CTkRadioButton(
                scroll,
                text=ruta,
                variable=radio_var,
                value=ruta,
                font=("Segoe UI", 12)
            ).pack(anchor="w", pady=5)

        def confirmar():
            seleccion["ruta"] = radio_var.get()
            dialog.destroy()

        def nueva_carpeta():
            dialog.destroy()
            seleccion["ruta"] = "__nueva__"

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Usar Seleccionado", fg_color="#2E86C1",
                      command=confirmar).pack(side=tk.LEFT, padx=10)
        ctk.CTkButton(btn_frame, text="Elegir Otra Carpeta", fg_color="#7D3C98",
                      command=nueva_carpeta).pack(side=tk.LEFT, padx=10)

        dialog.wait_window()

        if seleccion["ruta"] == "__nueva__":
            return self._realizar_configuracion_inicial()
        elif seleccion["ruta"]:
            gestor_datos.escribir_ruta_config(seleccion["ruta"])
            return seleccion["ruta"]
        else:
            return self._realizar_configuracion_inicial()

    def _realizar_configuracion_inicial(self):
        """Solicita al usuario seleccionar una carpeta para los datos."""
        messagebox.showinfo(
            "Configuración Inicial",
            "Seleccioná una carpeta donde se guardarán tus datos.\n\n"
            "Si ya tenés un archivo de datos de otra PC, pegálo\n"
            "en esa carpeta y el programa lo reconocerá automáticamente."
        )
        carpeta = filedialog.askdirectory(title="Selecciona la carpeta para guardar los datos")
        if not carpeta:
            return None
        ruta_archivo = os.path.join(carpeta, "datos_promedios.json")
        gestor_datos.escribir_ruta_config(ruta_archivo)
        return ruta_archivo

    def importar_datos(self):
        """Importa y fusiona datos desde un archivo JSON externo."""
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo de datos a importar",
            filetypes=[
                ("Archivos de datos Promediador", "datos_promedios.json"),
                ("Archivos JSON", "*.json"),
                ("Todos los archivos", "*.*")
            ]
        )
        if not archivo or not isinstance(archivo, str):
            return

        # Verificar que no sea el mismo archivo que ya estamos usando
        if self.ruta_datos and os.path.abspath(archivo) == os.path.abspath(self.ruta_datos):
            messagebox.showwarning(
                "Archivo Duplicado",
                "El archivo seleccionado es el mismo que ya estás usando.\n"
                "Selecciona un archivo diferente."
            )
            return

        # Cargar datos del archivo importado
        datos_importados = gestor_datos.cargar_datos(archivo)
        if not datos_importados.get(K_COLEGIOS):
            messagebox.showinfo(
                "Sin Datos",
                "El archivo seleccionado no contiene datos para importar."
            )
            return

        # Confirmar la importación
        colegios = list(datos_importados[K_COLEGIOS].keys())
        preview = ", ".join(colegios[:5])
        if len(colegios) > 5:
            preview += f" y {len(colegios) - 5} más..."

        confirmar = messagebox.askyesno(
            "Confirmar Importación",
            f"Se encontraron {len(colegios)} institución(es) en el archivo:\n\n"
            f"{preview}\n\n"
            f"Los datos se fusionarán con tus datos actuales.\n"
            f"No se sobrescribirán datos existentes.\n\n"
            f"¿Deseas continuar?"
        )
        if not confirmar:
            return

        # Fusionar
        stats = gestor_datos.fusionar_datos(self.datos, datos_importados)

        # Guardar inmediatamente
        self._guardar_datos_con_recuperacion()

        # Mostrar resultado
        messagebox.showinfo(
            "Importación Exitosa",
            f"¡Datos importados correctamente!\n\n"
            f"• Instituciones nuevas: {stats['colegios_nuevos']}\n"
            f"• Cursos nuevos: {stats['cursos_nuevos']}\n"
            f"• Alumnos nuevos: {stats['alumnos_nuevos']}\n\n"
            f"Los datos ya están guardados."
        )

        # Refrescar la pantalla
        self.mostrar_pantalla_colegios()

    def _guardar_datos_con_recuperacion(self):
        """Intenta guardar los datos y maneja errores ofreciendo recuperación."""
        if not self.ruta_datos:
            return False
        
        try:
            gestor_datos.guardar_datos(self.ruta_datos, self.datos)
            return True
        except FileNotFoundError:
            respuesta = messagebox.askyesno(
                "Ubicación de Datos Perdida",
                "La carpeta donde se guardan los datos no se encuentra.\n\n"
                "¿Deseas seleccionar una nueva ubicación para guardar tus datos?\n\n"
                "(Si eliges 'No', los cambios actuales no se guardarán)."
            )
            if respuesta:
                nueva_ruta = self._realizar_configuracion_inicial()
                if nueva_ruta:
                    self.ruta_datos = nueva_ruta
                    return self._guardar_datos_con_recuperacion()
            messagebox.showwarning("Guardado Cancelado", "No se han guardado.")
            return False
        except (IOError, OSError) as e:
            messagebox.showerror("Error Crítico al Guardar", f"No se pudieron guardar los datos.\n\nError: {e}")
            return False

    @staticmethod
    def _reordenar_alumnos(alumnos_curso: dict) -> dict:
        """Reordena los IDs de los alumnos para que sean consecutivos desde 1."""
        ids_viejos_ordenados = sorted(alumnos_curso.keys(), key=int)
        alumnos_reordenados = {}
        for nuevo_id, viejo_id in enumerate(ids_viejos_ordenados, start=1):
            alumnos_reordenados[str(nuevo_id)] = alumnos_curso[viejo_id]
        return alumnos_reordenados

    def exportar_planilla(self, nombre_curso):
        if self.hay_cambios_sin_guardar:
            messagebox.showwarning("Cambios Pendientes", "Tienes cambios sin guardar. Por favor, guarda la planilla antes de exportar para asegurar que los datos sean correctos.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Exportar Planilla como CSV",
            initialfile=f"Planilla - {nombre_curso}.csv",
            defaultextension=".csv",
            filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )

        if not file_path:
            return

        curso_data = self.datos[K_COLEGIOS][self.colegio_seleccionado][K_CURSOS][nombre_curso]
        success, error_message = exportar_a_csv(curso_data, file_path)

        if success:
            messagebox.showinfo("Exportación Exitosa", f"La planilla ha sido exportada correctamente a:\n{file_path}")
        else:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar la planilla.\n\nError: {error_message}")

    def exportar_planilla_texto(self, nombre_curso):
        if self.hay_cambios_sin_guardar:
            messagebox.showwarning("Cambios Pendientes", "Tienes cambios sin guardar. Por favor, guarda la planilla antes de exportar para asegurar que los datos sean correctos.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Exportar Planilla como Texto",
            initialfile=f"Planilla - {nombre_curso}.txt",
            defaultextension=".txt",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )

        if not file_path:
            return

        curso_data = self.datos[K_COLEGIOS][self.colegio_seleccionado][K_CURSOS][nombre_curso]
        success, error_message = exportar_a_texto(curso_data, file_path, nombre_curso)

        if success:
            messagebox.showinfo("Exportación Exitosa", f"La planilla ha sido exportada como texto correctamente a:\n{file_path}")
        else:
            messagebox.showerror("Error de Exportación", f"No se pudo exportar la planilla a texto.\n\nError: {error_message}")

    def exportar_planilla_pdf(self, nombre_curso):
        if self.hay_cambios_sin_guardar:
            messagebox.showwarning("Cambios sin guardar", "Por favor, guarda la planilla antes de exportarla.")
            return

        file_path = filedialog.asksaveasfilename(
            title="Exportar Planilla a PDF",
            initialfile=f"Planilla - {nombre_curso}.pdf",
            defaultextension=".pdf",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")]
        )

        if not file_path:
            return

        curso_data = self.datos[K_COLEGIOS][self.colegio_seleccionado][K_CURSOS][nombre_curso]
        colegio_sel = str(self.colegio_seleccionado) if self.colegio_seleccionado else ""
        
        # Ejecutar en hilo de fondo para evitar freeze de la UI
        import threading
        
        def tarea_exportacion():
            success, error_message = exportar_a_pdf(curso_data, file_path, nombre_curso, colegio_sel)
            if success:
                self.root.after(0, lambda: messagebox.showinfo("Exportación Exitosa", f"La planilla PDF lista para imprimir se guardó en:\n{file_path}"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error de Exportación", f"No se pudo exportar la planilla a PDF.\n\nError: {error_message}"))
                
        threading.Thread(target=tarea_exportacion, daemon=True).start()

    def accion_volver_desde_planilla(self):
        if self.hay_cambios_sin_guardar:
            respuesta = messagebox.askyesnocancel("Volver", "Tienes cambios sin guardar. ¿Deseas guardarlos antes de volver?")
            if respuesta is True:
                if self.guardar_notas_cuadricula(self.curso_seleccionado):
                    self.mostrar_pantalla_cursos(self.colegio_seleccionado)
            elif respuesta is False:
                self.mostrar_pantalla_cursos(self.colegio_seleccionado)
        else:
            self.mostrar_pantalla_cursos(self.colegio_seleccionado)

    def al_cerrar(self):
        if self.hay_cambios_sin_guardar:
            if self.curso_seleccionado:
                respuesta = messagebox.askyesnocancel("Salir", "Tienes cambios sin guardar en la planilla. ¿Deseas guardarlos antes de salir?")
                if respuesta is True:
                    if self.guardar_notas_cuadricula(self.curso_seleccionado, show_success_message=False):
                        self.root.destroy()
                elif respuesta is False:
                    self.root.destroy()
            else:
                respuesta = messagebox.askyesno("Salir", "Tienes cambios sin guardar que se perderán. ¿Deseas salir de todas formas?")
                if respuesta:
                    self.root.destroy()
        else:
            self.root.destroy()

    def filtrar_busqueda_predictiva(self, texto_ingresado, dropdown_frame):
        """
        Búsqueda predictiva global de alumnos en la base de datos.
        """
        for widget in dropdown_frame.winfo_children():
            widget.destroy()

        if not texto_ingresado:
            return

        texto_lower = texto_ingresado.lower()
        resultados_reales = []
        
        # Búsqueda en los datos reales (construyendo estructura plana al vuelo)
        colegios = self.datos.get(K_COLEGIOS, {})
        for nombre_colegio, colegio_data in colegios.items():
            cursos = colegio_data.get(K_CURSOS, {})
            for nombre_curso, curso_data in cursos.items():
                alumnos = curso_data.get(K_ALUMNOS, {})
                for id_al, al_data in alumnos.items():
                    nombre_alumno = al_data.get(K_NOMBRE, "").strip()
                    
                    # CONTROL DE CAMPOS VACÍOS: Ignorar alumnos sin nombre válido
                    if not nombre_alumno or nombre_alumno == "-":
                        continue
                    
                    # ALGORITMO PREDICTIVO: Coincidencia en minúsculas
                    if (texto_lower in nombre_alumno.lower() or 
                        texto_lower in nombre_curso.lower() or 
                        texto_lower in nombre_colegio.lower()):
                        
                        resultados_reales.append({
                            "id": id_al,
                            "nombre": nombre_alumno,
                            "curso": nombre_curso,
                            "colegio": nombre_colegio
                        })
                        
                        # Limitar resultados para optimización visual (Anti-Lag)
                        if len(resultados_reales) >= 15:
                            break
                if len(resultados_reales) >= 15: break
            if len(resultados_reales) >= 15: break
        
        if not resultados_reales:
            lbl = ctk.CTkLabel(dropdown_frame, text="No se encontraron alumnos.", text_color="#9CA3AF", font=(self.font_body[0], 12))
            lbl.pack(pady=15)
            return

        for res in resultados_reales:
            row_frame = ctk.CTkFrame(dropdown_frame, fg_color="transparent", corner_radius=6, cursor="hand2")
            row_frame.pack(fill=tk.X, padx=5, pady=2)
            
            def on_enter(e, f=row_frame): f.configure(fg_color="#F3F4F6")
            def on_leave(e, f=row_frame): f.configure(fg_color="transparent")
            
            row_frame.bind("<Enter>", on_enter)
            row_frame.bind("<Leave>", on_leave)
            
            lbl_nom = ctk.CTkLabel(row_frame, text=res["nombre"], font=(self.font_body[0], 14, "bold"), text_color="#111827", anchor="w")
            lbl_nom.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(8, 0))
            
            lbl_desc = ctk.CTkLabel(row_frame, text=f'{res["curso"]}  |  {res["colegio"]}', font=(self.font_body[0], 11), text_color="#6B7280", anchor="w")
            lbl_desc.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 8))
            
            # Propagar evento Hover a los hijos para evitar parpadeos (flickering)
            lbl_nom.bind("<Enter>", on_enter)
            lbl_nom.bind("<Leave>", on_leave)
            lbl_desc.bind("<Enter>", on_enter)
            lbl_desc.bind("<Leave>", on_leave)
            
            def click_handler(e, r=res):
                self.navegar_a_planilla_alumno(r["id"], r["colegio"], r["curso"])
                
            row_frame.bind("<Button-1>", click_handler)
            lbl_nom.bind("<Button-1>", click_handler)
            lbl_desc.bind("<Button-1>", click_handler)

    def navegar_a_planilla_alumno(self, alumno_id, colegio, curso):
        """
        Navega a la planilla del alumno seleccionado.
        """
        if hasattr(self, 'search_dropdown') and self.search_dropdown:
            self.search_dropdown.place_forget()
            
        self.colegio_seleccionado = colegio
        self.mostrar_apartado_curso(curso)
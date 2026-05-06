import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import sys
from core import gestor_datos
from core.calculos import procesar_calificaciones_alumno
from core.constants import *
from core.exportador import exportar_a_csv

class AppPromedios:
    def __init__(self, root):
        ctk.set_appearance_mode("light")

        self.root = root
        self.root.title("Gestor Educativo Profesional")
        self.root.geometry("1600x900")

        # --- Fuentes ---
        self.font_title = ("Segoe UI", 34, "bold")
        self.font_card_title = ("Segoe UI", 16, "bold")
        self.font_button = ("Segoe UI", 14, "bold")
        self.font_body = ("Segoe UI", 14)
        self.font_grid_header = ("Segoe UI", 13, "bold")
        self.font_grid_body = ("Segoe UI", 14)

        # --- Paleta de Colores ---
        self.paleta = {
            "fondo_app": "#F4F7F9",      # Un gris muy claro, menos duro que el blanco puro
            "fondo_card": "#FFFFFF",
            "texto_principal": "#2C3E50", # Un azul oscuro, más suave que el negro
            "texto_secundario": "#95A5A6",
            "borde_sutil": "#EAECEE",
            "grid_bg": "#EAECEE",        # Color para las líneas de la grilla

            "azul_fg": "#3498DB", "azul_hover": "#2980B9",
            "verde_fg": "#2ECC71", "verde_hover": "#27AE60",
            "rojo_fuerte": "#E74C3C",

            "card_btn_fg": "#F4F7F9",
            "card_btn_hover": "#EAECEE",
            
            "card_azul_texto": "#3498DB",
            "card_verde_texto": "#27AE60",
            "card_rojo_texto": "#E74C3C",

            "trimestre_1": "#FDEBD0", "trimestre_2": "#D4EFDF", "trimestre_3": "#E8DAEF", "final": "#FCF3CF"
        }
        
        # --- Inicialización de Datos y Configuración ---
        self.root.configure(fg_color=self.paleta["fondo_app"])
        gestor_datos.RUTA_ARCHIVO = gestor_datos.obtener_ruta_base_datos()
        if not gestor_datos.RUTA_ARCHIVO:
            messagebox.showerror("Configuración Requerida", "Se requiere una carpeta de datos para iniciar. La aplicación se cerrará.")
            sys.exit()

        self.datos = gestor_datos.cargar_datos()
        self.frame_actual = None
        self.colegio_seleccionado = None
        self.curso_seleccionado = None
        self.hay_cambios_sin_guardar = False
        self.grid_container = None
        self._resize_timer = None

        # Validación para permitir solo números y puntos en los Entry
        self.vcmd = (self.root.register(self.solo_numeros), '%P')

        # Protocolo de cierre para advertir sobre cambios sin guardar
        self.root.protocol("WM_DELETE_WINDOW", self.al_cerrar)
        self.root.bind('<Configure>', self._on_resize) # Bind resize event

        # Firma fija
        ctk.CTkLabel(
            self.root, 
            text="Software desarrollado por Ignacio Olmedo © 2026", 
            font=("Segoe UI", 12, "italic"), 
            text_color=self.paleta["texto_secundario"]
        ).pack(side=tk.BOTTOM, pady=10)

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
        # Permite un formato de número flotante simple, aceptando tanto punto como coma.
        # Reemplazamos la coma por un punto para una validación unificada.
        P_normalized = P.replace(',', '.')
        parts = P_normalized.split('.')
        if len(parts) > 2:  # Más de un separador decimal
            return False
        # Chequea que todas las partes (antes y después del punto) sean dígitos
        return all(part.isdigit() for part in parts)
        
    def limpiar_pantalla(self):
        if self.frame_actual: self.frame_actual.destroy()

    # --- CRUD COLEGIOS ---
    def mostrar_pantalla_colegios(self):
        self.limpiar_pantalla()
        self.colegio_seleccionado = None
        self.curso_seleccionado = None
        self.grid_container = None
        self.frame_actual = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame_actual.pack(fill=tk.BOTH, expand=True, padx=80, pady=20)

        ctk.CTkLabel(self.frame_actual, text="Mis Instituciones", font=self.font_title, 
                     text_color=self.paleta["texto_principal"]).pack(pady=30)

        for nombre_ant in list(self.datos.get(K_COLEGIOS, {}).keys()):
            # Usamos el nuevo método para crear la tarjeta
            self._crear_tarjeta(
                parent=self.frame_actual,
                nombre_entidad=nombre_ant,
                tipo_entidad="colegio",
                boton_principal_config={
                    "text": "Entrar →",
                    "fg_color": self.paleta["card_btn_fg"],
                    "hover_color": self.paleta["card_btn_hover"],
                    "text_color": self.paleta["card_azul_texto"],
                    "accion": self.renombrar_y_abrir_colegio
                }
            )

        ctk.CTkButton(
            self.frame_actual, text="+ Nueva Institución", 
            fg_color=self.paleta["azul_fg"], hover_color=self.paleta["azul_hover"],
            font=self.font_button, corner_radius=10, height=45,
            command=lambda: self.modal_crear("colegio")
        ).pack(pady=30)

    def _crear_tarjeta(self, parent, nombre_entidad, tipo_entidad, boton_principal_config):
        card = ctk.CTkFrame(parent, fg_color=self.paleta["fondo_card"], border_width=1, border_color=self.paleta["borde_sutil"], corner_radius=16)
        card.pack(fill=tk.X, pady=8, ipady=12, padx=50)
        
        entry_font = self.font_card_title
        ent_nombre = ctk.CTkEntry(card, font=entry_font, fg_color="#F8F9FA", border_width=0, width=400)
        ent_nombre.insert(0, nombre_entidad)
        ent_nombre.pack(side=tk.LEFT, padx=25, ipady=5)
        
        # Botón de acción principal (Entrar / Ver Planilla)
        ctk.CTkButton(
            card, text=boton_principal_config["text"],
            fg_color=boton_principal_config["fg_color"],
            hover_color=boton_principal_config["hover_color"],
            text_color=boton_principal_config["text_color"],
            font=self.font_button, corner_radius=8,
            command=lambda n=nombre_entidad, e=ent_nombre: boton_principal_config["accion"](n, e)
        ).pack(side=tk.RIGHT, padx=10)
        
        # Botón de eliminar (común a ambos)
        ctk.CTkButton(
            card, text="Eliminar",
            fg_color=self.paleta["card_btn_fg"],
            hover_color=self.paleta["card_btn_hover"],
            text_color=self.paleta["card_rojo_texto"],
            corner_radius=8, font=self.font_button,
            command=lambda n=nombre_entidad: self.eliminar_entidad(tipo_entidad, n)
        ).pack(side=tk.RIGHT, padx=10)

    def renombrar_y_abrir_colegio(self, nombre_ant, widget_entry):
        nuevo = widget_entry.get().strip().upper()
        if nuevo and nuevo != nombre_ant:
            if nuevo in self.datos[K_COLEGIOS]:
                messagebox.showerror("Error al Renombrar", f"Ya existe una institución con el nombre '{nuevo}'.\nPor favor, elige un nombre diferente.")
                widget_entry.delete(0, tk.END)
                widget_entry.insert(0, nombre_ant) # Revertir texto en la UI
                return

            self.datos[K_COLEGIOS][nuevo] = self.datos[K_COLEGIOS].pop(nombre_ant)
            gestor_datos.guardar_datos(self.datos)
        self.mostrar_pantalla_cursos(nuevo if nuevo else nombre_ant)

    # --- CRUD CURSOS ---
    def mostrar_pantalla_cursos(self, nombre_colegio):
        self.limpiar_pantalla()
        self.colegio_seleccionado = nombre_colegio
        self.curso_seleccionado = None
        self.grid_container = None
        self.frame_actual = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame_actual.pack(fill=tk.BOTH, expand=True, padx=80, pady=20)

        header = ctk.CTkFrame(self.frame_actual, fg_color="transparent")
        header.pack(fill=tk.X, pady=10)
        
        ctk.CTkButton(
            header, text="← Volver", font=self.font_body, 
            command=self.mostrar_pantalla_colegios,
            fg_color="transparent", text_color=self.paleta["azul_fg"],
            hover_color=self.paleta["card_btn_hover"]
        ).pack(side=tk.LEFT)
        
        ctk.CTkLabel(header, text=f"Cursos en: {nombre_colegio}", font=self.font_title, 
                     text_color=self.paleta["texto_principal"]).pack(side=tk.LEFT, padx=30)

        cursos = self.datos[K_COLEGIOS][nombre_colegio].get(K_CURSOS, {})
        for nombre_curso in list(cursos.keys()):
            self._crear_tarjeta(
                parent=self.frame_actual,
                nombre_entidad=nombre_curso,
                tipo_entidad="curso",
                boton_principal_config={
                    "text": "Ver Planilla",
                    "fg_color": self.paleta["card_btn_fg"],
                    "hover_color": self.paleta["card_btn_hover"],
                    "text_color": self.paleta["card_verde_texto"],
                    "accion": self.renombrar_y_abrir_planilla
                }
            )

        ctk.CTkButton(
            self.frame_actual, text="+ Nuevo Curso",
            fg_color=self.paleta["azul_fg"], hover_color=self.paleta["azul_hover"],
            font=self.font_button, corner_radius=10, height=45,
            command=lambda: self.modal_crear("curso")
        ).pack(pady=30)

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
            gestor_datos.guardar_datos(self.datos)
        self.mostrar_apartado_curso(nuevo if nuevo else nombre_ant)

    # --- MODALES ---
    def modal_crear(self, tipo):
        ventana = ctk.CTkToplevel(self.root)
        ventana.title(f"Añadir {tipo.capitalize()}")
        alto = 350 if tipo == "curso" else 250
        ventana.geometry(f"450x{alto}")
        ventana.configure(fg_color="white")
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
                                    border_color="#ccc", corner_radius=6,
                                    validate='key', validatecommand=self.vcmd)
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

                cant_s = ent_cant.get().strip()
                cant = int(cant_s) if cant_s.isdigit() else 1
                if nom not in self.datos[K_COLEGIOS][col][K_CURSOS]:
                    alumnos = {
                        str(i): {
                            K_NOMBRE: "", 
                            K_TRIMESTRES: {t: {K_PRINCIPALES: [None]*3, K_EXTRAS: [None]} for t in NOMBRES_TRIMESTRES}
                        } for i in range(1, cant + 1)
                    }
                    self.datos[K_COLEGIOS][col][K_CURSOS][nom] = {
                        K_NOMBRES_COLUMNAS: {t: NOMBRES_COLUMNAS_DEFAULT for t in NOMBRES_TRIMESTRES}, 
                        K_ALUMNOS: alumnos
                    }
                    self.mostrar_pantalla_cursos(col)
            
            gestor_datos.guardar_datos(self.datos)
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

        toolbar = ctk.CTkFrame(self.frame_actual, fg_color=self.paleta["fondo_card"], border_width=1, border_color=self.paleta["borde_sutil"], corner_radius=0)
        toolbar.pack(side=tk.TOP, fill=tk.X, ipady=8)
        ctk.CTkButton(toolbar, text="← Volver", command=self.accion_volver_desde_planilla, fg_color="transparent", text_color=self.paleta["azul_fg"], hover_color=self.paleta["card_btn_hover"], font=self.font_body).pack(side=tk.LEFT, padx=20)
        texto_cabecera = f"{self.colegio_seleccionado}  |  {nombre_curso}"
        ctk.CTkLabel(toolbar, text=texto_cabecera, font=self.font_card_title, text_color=self.paleta["texto_principal"]).pack(side=tk.LEFT, padx=10)
        
        ctk.CTkButton(toolbar, text="GUARDAR y CALCULAR", fg_color=self.paleta["verde_fg"], hover_color=self.paleta["verde_hover"], font=self.font_button, corner_radius=8, command=lambda: self.guardar_notas_cuadricula(nombre_curso)).pack(side=tk.RIGHT, padx=30, ipady=5)
        ctk.CTkButton(toolbar, text="Exportar a CSV", fg_color=self.paleta["card_btn_fg"], text_color=self.paleta["texto_secundario"], hover_color=self.paleta["card_btn_hover"], border_width=1, border_color=self.paleta["borde_sutil"], corner_radius=8, font=self.font_button, command=lambda: self.exportar_planilla(nombre_curso)).pack(side=tk.RIGHT, padx=10)
        ctk.CTkButton(toolbar, text="+ Alumno", fg_color=self.paleta["card_btn_fg"], text_color=self.paleta["card_azul_texto"], hover_color=self.paleta["card_btn_hover"], corner_radius=8, font=self.font_button, command=lambda: self.agregar_alumno(nombre_curso)).pack(side=tk.RIGHT, padx=10)

        # Usamos un CTkScrollableFrame para simplificar enormemente el manejo del scroll
        scrollable_frame = ctk.CTkScrollableFrame(self.frame_actual, fg_color=self.paleta["grid_bg"], corner_radius=0)
        scrollable_frame.pack(fill=tk.BOTH, expand=True)

        # El grid_container ahora es el frame interno del CTkScrollableFrame
        self.grid_container = scrollable_frame

        # Hacemos que la columna del nombre del alumno sea la que se expanda
        self.grid_container.grid_columnconfigure(2, weight=1, minsize=250) # Asegura un ancho mínimo de 250px

        curso_data = self.datos[K_COLEGIOS][self.colegio_seleccionado][K_CURSOS][nombre_curso]
        self.widgets_entradas, self.widgets_resultados, self.widgets_nombres_alumnos = {}, {}, {}
        self.widgets_nombres_cols = {t: [] for t in NOMBRES_TRIMESTRES}

        # Headers  
        ctk.CTkLabel(self.grid_container, text="N°", font=self.font_grid_header, fg_color="#E5E7E9", text_color=self.paleta["texto_principal"], corner_radius=0).grid(row=0, column=1, rowspan=2, sticky="nsew", padx=1, pady=1)
        ctk.CTkLabel(self.grid_container, text="Nombre del Alumno", font=self.font_grid_header, fg_color="#E5E7E9", text_color=self.paleta["texto_principal"], corner_radius=0).grid(row=0, column=2, rowspan=2, sticky="nsew", padx=1, pady=1)

        col_off = 3
        for t, color in zip(NOMBRES_TRIMESTRES, [self.paleta["trimestre_1"], self.paleta["trimestre_2"], self.paleta["trimestre_3"]]):
            ctk.CTkLabel(self.grid_container, text=t, fg_color=color, text_color=self.paleta["texto_principal"], font=self.font_grid_header).grid(row=0, column=col_off, columnspan=5, sticky="nsew", padx=1, pady=1)
            for j, nom in enumerate(curso_data["nombres_columnas"][t]):
                e = ctk.CTkEntry(self.grid_container, justify=tk.CENTER, width=60, font=self.font_grid_header, fg_color="#E5E7E9", text_color=self.paleta["texto_principal"], border_width=0, corner_radius=0)
                e.insert(0, nom)
                e.bind("<KeyRelease>", self._marcar_cambios_pendientes)
                e.grid(row=1, column=col_off + j, sticky="nsew", padx=1, pady=1)
                self.widgets_nombres_cols[t].append(e)
            ctk.CTkLabel(self.grid_container, text="Prom", width=60, font=self.font_grid_header, fg_color="#E5E7E9", text_color=self.paleta["texto_principal"]).grid(row=1, column=col_off+4, sticky="nsew", padx=1, pady=1)
            col_off += 5
        
        # PROMEDIOS FINALES: Aplicamos el margen (30, 1) tanto a la cabecera principal como a los subtítulos
        ctk.CTkLabel(self.grid_container, text="PROMEDIOS FINALES", fg_color=self.paleta["final"], text_color=self.paleta["texto_principal"], font=self.font_grid_header).grid(row=0, column=18, columnspan=4, sticky="nsew", padx=(30, 1), pady=1)
        
        for i, txt in enumerate(["T1", "T2", "T3", "TOTAL"]):
            # El gap (30, 1) solo va en el primer elemento (T1) para empujar el resto
            gap = (30, 1) if i == 0 else 1
            ctk.CTkLabel(self.grid_container, text=txt, width=60, font=self.font_grid_header, fg_color="#E5E7E9", text_color=self.paleta["texto_principal"]).grid(row=1, column=18+i, sticky="nsew", padx=gap, pady=1)

        # Dibujar las filas de los alumnos
        for i, id_al in enumerate(sorted(curso_data[K_ALUMNOS].keys(), key=int)):
            self.dibujar_fila_alumno(i+2, id_al, curso_data[K_ALUMNOS][id_al], nombre_curso)

    def dibujar_fila_alumno(self, row, id_al, al_data, nombre_curso):
        ctk.CTkButton(self.grid_container, text="✕", fg_color=self.paleta["fondo_card"], text_color=self.paleta["card_rojo_texto"], hover_color=self.paleta["card_btn_hover"],
                      width=25, corner_radius=4, font=self.font_body, command=lambda: self.eliminar_entidad("alumno", id_al, nombre_curso)).grid(row=row, column=0, sticky="nsew", padx=1, pady=1)
        
        ctk.CTkLabel(self.grid_container, text=id_al, font=self.font_grid_body, fg_color=self.paleta["fondo_card"], text_color=self.paleta["texto_principal"]).grid(row=row, column=1, sticky="nsew", padx=1, pady=1)
        ent_n = ctk.CTkEntry(self.grid_container, border_width=0, fg_color=self.paleta["fondo_card"], font=self.font_grid_body, corner_radius=0)
        ent_n.insert(0, al_data.get(K_NOMBRE, "")); ent_n.grid(row=row, column=2, sticky="nsew", padx=1, pady=1)
        ent_n.bind("<KeyRelease>", self._marcar_cambios_pendientes)
        self.widgets_nombres_alumnos[id_al] = ent_n

        self.widgets_entradas[id_al], self.widgets_resultados[id_al] = [], {"trim": [], "fin": []}
        c_idx = 3
        for t_idx, t_nom in enumerate(NOMBRES_TRIMESTRES):
            e_dict = {"p": [], "ex": None}
            notas_data = al_data["trimestres"][t_nom]
            for j in range(3):
                e = ctk.CTkEntry(self.grid_container, width=60, justify=tk.CENTER, font=self.font_grid_body, fg_color=self.paleta["fondo_card"], border_width=0, corner_radius=0, validate='key', validatecommand=self.vcmd)
                val = notas_data["principales"][j]
                if val is not None: e.insert(0, str(val))
                e.bind("<KeyRelease>", self._marcar_cambios_pendientes)
                e.grid(row=row, column=c_idx, padx=1, pady=1); c_idx += 1; e_dict["p"].append(e)
            
            ex = ctk.CTkEntry(self.grid_container, width=60, justify=tk.CENTER, font=self.font_grid_body, fg_color="#FBFBFB", border_width=0, corner_radius=0, validate='key', validatecommand=self.vcmd)
            val_ex = notas_data[K_EXTRAS][0] if notas_data[K_EXTRAS] else None
            if val_ex is not None: ex.insert(0, str(val_ex))
            ex.bind("<KeyRelease>", self._marcar_cambios_pendientes)
            ex.grid(row=row, column=c_idx, padx=1, pady=1); c_idx += 1; e_dict["ex"] = ex
            self.widgets_entradas[id_al].append(e_dict)
            
            l = ctk.CTkLabel(self.grid_container, text="-", font=self.font_grid_header, fg_color="#FBFBFB", text_color=self.paleta["texto_principal"])
            l.grid(row=row, column=c_idx, sticky="nsew", padx=1, pady=1); c_idx += 1
            self.widgets_resultados[id_al]["trim"].append(l)

        # --- FILAS DE PROMEDIOS FINALES (CORREGIDO PARA ALINEAR CON EL CABECERAS) ---
        for j in range(4):
            # Aplicamos el margen de 30 píxeles a la izquierda solo al primer cuadro (T1)
            # Esto empuja toda la sección hacia la derecha para que coincida con el título
            separacion_seccion = (30, 1) if j == 0 else 1
            
            l_f = ctk.CTkLabel(self.grid_container, text="-", font=self.font_grid_header, fg_color="#FBFBFB", text_color=self.paleta["texto_principal"])
            l_f.grid(row=row, column=18+j, sticky="nsew", padx=separacion_seccion, pady=1)
            self.widgets_resultados[id_al]["fin"].append(l_f)
            
        # --- CÁLCULO AUTOMÁTICO Y FORMATO DE COLOR AL CARGAR ---
        res_cargados = procesar_calificaciones_alumno(al_data[K_TRIMESTRES])
        self._actualizar_promedios_ui(id_al, res_cargados)

    def _actualizar_promedios_ui(self, id_al, resultados):
        # Actualiza los labels de promedio para un alumno específico
        for t_idx, prom_t in enumerate(resultados["trimestres"]):
            val_txt = f"{prom_t:.2f}" if prom_t is not None else "-"
            color = self.paleta["rojo_fuerte"] if (prom_t is not None and prom_t < 6) else (self.paleta["verde_fg"] if prom_t is not None else self.paleta["texto_principal"])
            self.widgets_resultados[id_al]["trim"][t_idx].configure(text=val_txt, text_color=color)
            self.widgets_resultados[id_al]["fin"][t_idx].configure(text=val_txt, text_color=color)
        
        # Color para el promedio final total
        p_final = resultados['final']
        color_f = self.paleta["rojo_fuerte"] if (p_final > 0 and p_final < 6) else (self.paleta["verde_fg"] if p_final > 0 else self.paleta["texto_principal"])
        self.widgets_resultados[id_al]["fin"][3].configure(text=f"{p_final:.2f}" if p_final > 0 else "-", text_color=color_f)

    def agregar_alumno(self, nombre_curso):
        col = self.colegio_seleccionado
        alumnos = self.datos[K_COLEGIOS][col][K_CURSOS][nombre_curso][K_ALUMNOS]
        nuevo_id = str(max([int(k) for k in alumnos.keys()] + [0]) + 1)
        alumnos[nuevo_id] = {K_NOMBRE: "", K_TRIMESTRES: {t: {K_PRINCIPALES: [None]*3, K_EXTRAS: [None]} for t in NOMBRES_TRIMESTRES}}
        gestor_datos.guardar_datos(self.datos); self.mostrar_apartado_curso(nombre_curso)

    def eliminar_entidad(self, tipo, id_ent, nombre_curso=None):
        if not messagebox.askyesno("Confirmar", f"¿Eliminar permanentemente este {tipo}?"): return
        col = self.colegio_seleccionado
        
        # --- Fase 1: Modificar los datos en memoria ---
        if tipo == "colegio":
            del self.datos[K_COLEGIOS][id_ent]
        elif tipo == "curso":
            del self.datos[K_COLEGIOS][col][K_CURSOS][id_ent]
        elif tipo == "alumno":
            del self.datos[K_COLEGIOS][col][K_CURSOS][nombre_curso][K_ALUMNOS][id_ent]
            alumnos_restantes = self.datos[K_COLEGIOS][col][K_CURSOS][nombre_curso][K_ALUMNOS]
            ids_viejos_ordenados = sorted(alumnos_restantes.keys(), key=int)
            alumnos_reordenados = {}
            for nuevo_id, viejo_id in enumerate(ids_viejos_ordenados, start=1):
                alumnos_reordenados[str(nuevo_id)] = alumnos_restantes[viejo_id]
            self.datos[K_COLEGIOS][col][K_CURSOS][nombre_curso][K_ALUMNOS] = alumnos_reordenados

        # --- Fase 2: Persistir los cambios en el disco ---
        gestor_datos.guardar_datos(self.datos)

        # --- Fase 3: Actualizar la interfaz de usuario ---
        if tipo == "colegio":
            self.mostrar_pantalla_colegios()
        elif tipo == "curso":
            self.mostrar_pantalla_cursos(col)
        elif tipo == "alumno":
            self.mostrar_apartado_curso(nombre_curso)

    def guardar_notas_cuadricula(self, nombre_curso):
        col = self.colegio_seleccionado
        curso_data = self.datos[K_COLEGIOS][col][K_CURSOS][nombre_curso]
        for t_nom in NOMBRES_TRIMESTRES:
            curso_data["nombres_columnas"][t_nom] = [w.get() for w in self.widgets_nombres_cols[t_nom]]

        def val_num(e):
            s = e.get().replace(',', '.').strip()
            try: return float(s) if s else None
            except: return None

        for id_al, al_data in curso_data[K_ALUMNOS].items():
            al_data[K_NOMBRE] = self.widgets_nombres_alumnos[id_al].get()
            ui = self.widgets_entradas[id_al]
            for t_idx, t_nom in enumerate(NOMBRES_TRIMESTRES):
                al_data[K_TRIMESTRES][t_nom][K_PRINCIPALES] = [val_num(e) for e in ui[t_idx]["p"]]
                al_data[K_TRIMESTRES][t_nom][K_EXTRAS] = [val_num(ui[t_idx]["ex"])]
            res = procesar_calificaciones_alumno(al_data[K_TRIMESTRES])
            
            # Usamos el nuevo método para actualizar la UI
            self._actualizar_promedios_ui(id_al, res)

        gestor_datos.guardar_datos(self.datos)
        self.hay_cambios_sin_guardar = False
        messagebox.showinfo("Éxito", "Cambios guardados.")

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

    def accion_volver_desde_planilla(self):
        if self.hay_cambios_sin_guardar:
            respuesta = messagebox.askyesnocancel("Volver", "Tienes cambios sin guardar. ¿Deseas guardarlos antes de volver?")
            if respuesta is True: # Sí
                self.guardar_notas_cuadricula(self.curso_seleccionado)
                self.mostrar_pantalla_cursos(self.colegio_seleccionado)
            elif respuesta is False: # No
                self.mostrar_pantalla_cursos(self.colegio_seleccionado)
            # else: Cancelar, no hacer nada
        else:
            self.mostrar_pantalla_cursos(self.colegio_seleccionado)

    def al_cerrar(self):
        if self.hay_cambios_sin_guardar:
            respuesta = messagebox.askyesnocancel("Salir", "Tienes cambios sin guardar. ¿Deseas guardarlos antes de salir?")
            if respuesta is True: # Sí
                self.guardar_notas_cuadricula(self.curso_seleccionado)
                self.root.destroy()
            elif respuesta is False: # No
                self.root.destroy()
            # else: Cancelar, no hacer nada
        else:
            self.root.destroy()
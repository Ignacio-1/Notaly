import tkinter as tk
from tkinter import messagebox, ttk
from core.gestor_datos import cargar_datos, guardar_datos
from core.calculos import procesar_calificaciones_alumno
from core.constants import *

class AppPromedios:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Educativo Profesional")
        self.root.geometry("1450x850")
        
        self.paleta = {
            "fondo_app": "#FDFDFD",
            "barra_superior": "#FFFFFF",
            "texto_principal": "#3C4043",
            "azul_soft": "#E8F0FE",
            "azul_fuerte": "#1A73E8",
            "verde_soft": "#E6F4EA",
            "verde_fuerte": "#1E8E3E",
            "rojo_soft": "#FCE8E6",
            "rojo_fuerte": "#D93025",
            "borde_sutil": "#E0E0E0",
            "t1": "#FFF9C4", "t2": "#E6F4EA", "t3": "#F3E8FD", "nf": "#FEEFC3"
        }
        
        self.root.configure(bg=self.paleta["fondo_app"])
        self.datos = cargar_datos()
        self.frame_actual = None
        self.colegio_seleccionado = None
        self.curso_seleccionado = None
        self.hay_cambios_sin_guardar = False

        # Validación para permitir solo números y puntos
        self.vcmd = (self.root.register(self.solo_numeros), '%P')

        # Protocolo de cierre para advertir sobre cambios sin guardar
        self.root.protocol("WM_DELETE_WINDOW", self.al_cerrar)

        # Firma fija
        tk.Label(self.root, text="Software desarrollado por Ignacio Olmedo © 2026", 
                 font=("Segoe UI", 9, "italic"), bg=self.paleta["fondo_app"], fg="#8A8C8F").pack(side=tk.BOTTOM, pady=5)

        self.mostrar_pantalla_colegios()

    def _marcar_cambios_pendientes(self, event=None):
        self.hay_cambios_sin_guardar = True

    def solo_numeros(self, P):
        if P == "":
            return True
        # Permite un formato de número flotante simple (ej: "123", "123.45")
        parts = P.split('.')
        if len(parts) > 2:  # Más de un punto decimal
            return False
        # Chequea que todas las partes (antes y después del punto) sean dígitos
        return all(part.isdigit() for part in parts)
        
    def limpiar_pantalla(self):
        if self.frame_actual: self.frame_actual.destroy()

    # --- CRUD COLEGIOS ---
    def mostrar_pantalla_colegios(self):
        self.limpiar_pantalla()
        self.colegio_seleccionado = None
        self.frame_actual = tk.Frame(self.root, bg=self.paleta["fondo_app"])
        self.frame_actual.pack(fill=tk.BOTH, expand=True, padx=80, pady=20)

        tk.Label(self.frame_actual, text="Mis Instituciones", font=("Segoe UI", 26, "bold"), 
                 bg=self.paleta["fondo_app"], fg=self.paleta["texto_principal"]).pack(pady=20)

        for nombre_ant in list(self.datos.get(K_COLEGIOS, {}).keys()):
            # Usamos el nuevo método para crear la tarjeta
            self._crear_tarjeta(
                parent=self.frame_actual,
                nombre_entidad=nombre_ant,
                tipo_entidad="colegio",
                boton_principal_config={
                    "text": "Entrar →", 
                    "bg": self.paleta["azul_soft"], 
                    "fg": self.paleta["azul_fuerte"],
                    "accion": self.renombrar_y_abrir_colegio
                }
            )

        tk.Button(self.frame_actual, text="+ Nueva Institución", bg=self.paleta["azul_fuerte"], fg="white",
                  font=("Segoe UI", 11, "bold"), relief=tk.FLAT, pady=12, padx=40,
                  command=lambda: self.modal_crear("colegio")).pack(pady=30)

    def _crear_tarjeta(self, parent, nombre_entidad, tipo_entidad, boton_principal_config):
        card = tk.Frame(parent, bg="white", highlightthickness=1, highlightbackground=self.paleta["borde_sutil"])
        card.pack(fill=tk.X, pady=7, ipady=10, padx=50)
        
        entry_font = ("Segoe UI", 13, "bold") if tipo_entidad == "colegio" else ("Segoe UI", 12, "bold")
        ent_nombre = tk.Entry(card, font=entry_font, bg="#F8F9FA", relief=tk.FLAT, width=30)
        ent_nombre.insert(0, nombre_entidad)
        ent_nombre.pack(side=tk.LEFT, padx=20, ipady=3)
        
        # Botón de acción principal (Entrar / Ver Planilla)
        tk.Button(card, text=boton_principal_config["text"], bg=boton_principal_config["bg"], fg=boton_principal_config["fg"], 
                  font=("Segoe UI", 9, "bold"), relief=tk.FLAT, padx=15,
                  command=lambda n=nombre_entidad, e=ent_nombre: boton_principal_config["accion"](n, e)).pack(side=tk.RIGHT, padx=10)
        
        # Botón de eliminar (común a ambos)
        tk.Button(card, text="Eliminar", bg=self.paleta["rojo_soft"], fg=self.paleta["rojo_fuerte"], 
                  relief=tk.FLAT, command=lambda n=nombre_entidad: self.eliminar_entidad(tipo_entidad, n)).pack(side=tk.RIGHT, padx=10)

    def renombrar_y_abrir_colegio(self, nombre_ant, widget_entry):
        nuevo = widget_entry.get().strip().upper()
        if nuevo and nuevo != nombre_ant:
            if nuevo in self.datos[K_COLEGIOS]:
                messagebox.showerror("Error al Renombrar", f"Ya existe una institución con el nombre '{nuevo}'.\nPor favor, elige un nombre diferente.")
                widget_entry.delete(0, tk.END)
                widget_entry.insert(0, nombre_ant) # Revertir texto en la UI
                return

            self.datos[K_COLEGIOS][nuevo] = self.datos[K_COLEGIOS].pop(nombre_ant)
            guardar_datos(self.datos)
        self.mostrar_pantalla_cursos(nuevo if nuevo else nombre_ant)

    # --- CRUD CURSOS ---
    def mostrar_pantalla_cursos(self, nombre_colegio):
        self.limpiar_pantalla()
        self.colegio_seleccionado = nombre_colegio
        self.frame_actual = tk.Frame(self.root, bg=self.paleta["fondo_app"])
        self.frame_actual.pack(fill=tk.BOTH, expand=True, padx=80, pady=20)

        header = tk.Frame(self.frame_actual, bg=self.paleta["fondo_app"])
        header.pack(fill=tk.X, pady=10)
        
        tk.Button(header, text="← Volver", font=("Segoe UI", 10), command=self.mostrar_pantalla_colegios, 
                  relief=tk.FLAT, bg=self.paleta["fondo_app"], fg=self.paleta["azul_fuerte"]).pack(side=tk.LEFT)
        
        tk.Label(header, text=f"Cursos en: {nombre_colegio}", font=("Segoe UI", 22, "bold"), 
                 bg=self.paleta["fondo_app"], fg=self.paleta["texto_principal"]).pack(side=tk.LEFT, padx=20)

        cursos = self.datos[K_COLEGIOS][nombre_colegio].get(K_CURSOS, {})
        for nombre_curso in list(cursos.keys()):
            self._crear_tarjeta(
                parent=self.frame_actual,
                nombre_entidad=nombre_curso,
                tipo_entidad="curso",
                boton_principal_config={
                    "text": "Ver Planilla",
                    "bg": self.paleta["verde_soft"],
                    "fg": self.paleta["verde_fuerte"],
                    "accion": self.renombrar_y_abrir_planilla
                }
            )

        tk.Button(self.frame_actual, text="+ Nuevo Curso", bg=self.paleta["azul_fuerte"], fg="white",
                  font=("Segoe UI", 11, "bold"), relief=tk.FLAT, pady=12, padx=40,
                  command=lambda: self.modal_crear("curso")).pack(pady=30)

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
            guardar_datos(self.datos)
        self.mostrar_apartado_curso(nuevo if nuevo else nombre_ant)

    # --- MODALES ---
    def modal_crear(self, tipo):
        ventana = tk.Toplevel(self.root)
        ventana.title(f"Añadir {tipo.capitalize()}")
        alto = 350 if tipo == "curso" else 250
        ventana.geometry(f"450x{alto}")
        ventana.configure(bg="white")
        ventana.grab_set()

        tk.Label(ventana, text=f"Nuevo {tipo.capitalize()}", font=("Segoe UI", 14, "bold"), bg="white", fg=self.paleta["azul_fuerte"]).pack(pady=20)
        
        instruccion = "Nombre de la Institución:" if tipo == "colegio" else "Año y División:"
        tk.Label(ventana, text=instruccion, bg="white", font=("Segoe UI", 9)).pack(anchor=tk.W, padx=50)
        ent_nom = tk.Entry(ventana, font=("Segoe UI", 12), highlightthickness=1, highlightbackground="#ccc", relief=tk.FLAT)
        ent_nom.pack(pady=10, padx=50, fill=tk.X, ipady=5)

        ent_cant = None
        if tipo == "curso":
            tk.Label(ventana, text="Cantidad inicial de alumnos:", bg="white", font=("Segoe UI", 9)).pack(anchor=tk.W, padx=50)
            ent_cant = tk.Entry(ventana, font=("Segoe UI", 12), justify=tk.CENTER, highlightthickness=1, 
                                highlightbackground="#ccc", relief=tk.FLAT, validate='key', validatecommand=self.vcmd)
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
            
            guardar_datos(self.datos)
            ventana.destroy()

        tk.Button(ventana, text="Confirmar", bg=self.paleta["azul_fuerte"], fg="white", relief=tk.FLAT, command=confirmar, padx=30, pady=5).pack(pady=20)

    # --- PLANILLA DE NOTAS ---
    def mostrar_apartado_curso(self, nombre_curso):
        self.limpiar_pantalla()
        self.curso_seleccionado = nombre_curso
        self.hay_cambios_sin_guardar = False
        self.frame_actual = tk.Frame(self.root, bg="white")
        self.frame_actual.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(self.frame_actual, bg=self.paleta["barra_superior"], highlightthickness=1, highlightbackground=self.paleta["borde_sutil"])
        toolbar.pack(side=tk.TOP, fill=tk.X, ipady=8)
        tk.Button(toolbar, text="← Volver", command=self.accion_volver_desde_planilla, relief=tk.FLAT).pack(side=tk.LEFT, padx=20)
        texto_cabecera = f"{self.colegio_seleccionado}  |  {nombre_curso}"
        tk.Label(toolbar, text=texto_cabecera, font=("Segoe UI", 14, "bold"), bg="white", fg=self.paleta["texto_principal"]).pack(side=tk.LEFT, padx=10)
       
       

        tk.Button(toolbar, text="+ Alumno", bg=self.paleta["azul_soft"], fg=self.paleta["azul_fuerte"], relief=tk.FLAT, command=lambda: self.agregar_alumno(nombre_curso)).pack(side=tk.LEFT, padx=20)
        tk.Button(toolbar, text="GUARDAR y CALCULAR", bg=self.paleta["verde_fuerte"], fg="white", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, command=lambda: self.guardar_notas_cuadricula(nombre_curso)).pack(side=tk.RIGHT, padx=30, ipady=5)

        container = tk.Frame(self.frame_actual, bg=self.paleta["fondo_app"])
        container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(container, bg=self.paleta["fondo_app"], highlightthickness=0)
        h_scroll = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=canvas.xview)
        v_scroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X); v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.grid_container = tk.Frame(canvas, bg=self.paleta["borde_sutil"])
        canvas.create_window((0,0), window=self.grid_container, anchor="nw")
        self.grid_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        curso_data = self.datos[K_COLEGIOS][self.colegio_seleccionado][K_CURSOS][nombre_curso]
        self.widgets_entradas, self.widgets_resultados, self.widgets_nombres_alumnos = {}, {}, {}
        self.widgets_nombres_cols = {t: [] for t in NOMBRES_TRIMESTRES}

        # Headers  
        tk.Label(self.grid_container, text="N°", width=4, bg="#F1F3F4").grid(row=0, column=1, rowspan=2, sticky="nsew", padx=1, pady=1)
        tk.Label(self.grid_container, text="Nombre del Alumno", width=30, bg="#F1F3F4").grid(row=0, column=2, rowspan=2, sticky="nsew", padx=1, pady=1)

        col_off = 3
        for t, color in zip(NOMBRES_TRIMESTRES, [self.paleta["t1"], self.paleta["t2"], self.paleta["t3"]]):
            tk.Label(self.grid_container, text=t, bg=color, font=("Arial", 10, "bold")).grid(row=0, column=col_off, columnspan=5, sticky="nsew", padx=1, pady=1)
            for j, nom in enumerate(curso_data["nombres_columnas"][t]):
                e = tk.Entry(self.grid_container, justify=tk.CENTER, width=7, relief=tk.FLAT, font=("Arial", 8, "bold"))
                e.insert(0, nom)
                e.bind("<KeyRelease>", self._marcar_cambios_pendientes)
                e.grid(row=1, column=col_off + j, sticky="nsew", padx=1, pady=1)
                self.widgets_nombres_cols[t].append(e)
            tk.Label(self.grid_container, text="Prom", width=6, bg="#E8EAED").grid(row=1, column=col_off+4, sticky="nsew", padx=1, pady=1)
            col_off += 5
        
        # PROMEDIOS FINALES: Aplicamos el margen (30, 1) tanto a la cabecera principal como a los subtítulos
        tk.Label(self.grid_container, text="PROMEDIOS FINALES", bg=self.paleta["nf"], font=("Arial", 10, "bold")).grid(row=0, column=18, columnspan=4, sticky="nsew", padx=(30, 1), pady=1)
        
        for i, txt in enumerate(["T1", "T2", "T3", "TOTAL"]):
            # El gap (30, 1) solo va en el primer elemento (T1) para empujar el resto
            gap = (30, 1) if i == 0 else 1
            tk.Label(self.grid_container, text=txt, width=8, bg="#E8EAED").grid(row=1, column=18+i, sticky="nsew", padx=gap, pady=1)

        # Dibujar las filas de los alumnos
        for i, id_al in enumerate(sorted(curso_data[K_ALUMNOS].keys(), key=int)):
            self.dibujar_fila_alumno(i+2, id_al, curso_data[K_ALUMNOS][id_al], nombre_curso)

    def dibujar_fila_alumno(self, row, id_al, al_data, nombre_curso):
        tk.Button(self.grid_container, text="✕", bg=self.paleta["rojo_soft"], fg=self.paleta["rojo_fuerte"], 
                  relief=tk.FLAT, font=("Arial", 9, "bold"), command=lambda: self.eliminar_entidad("alumno", id_al, nombre_curso)).grid(row=row, column=0, sticky="nsew", padx=1, pady=1)
        
        tk.Label(self.grid_container, text=id_al, bg="white").grid(row=row, column=1, sticky="nsew", padx=1, pady=1)
        ent_n = tk.Entry(self.grid_container, relief=tk.FLAT, bg="white", font=("Segoe UI", 10))
        ent_n.insert(0, al_data.get(K_NOMBRE, "")); ent_n.grid(row=row, column=2, sticky="nsew", padx=1, pady=1)
        ent_n.bind("<KeyRelease>", self._marcar_cambios_pendientes)
        self.widgets_nombres_alumnos[id_al] = ent_n

        self.widgets_entradas[id_al], self.widgets_resultados[id_al] = [], {"trim": [], "fin": []}
        c_idx = 3
        for t_idx, t_nom in enumerate(NOMBRES_TRIMESTRES):
            e_dict = {"p": [], "ex": None}
            notas_data = al_data["trimestres"][t_nom]
            for j in range(3):
                e = tk.Entry(self.grid_container, width=5, justify=tk.CENTER, relief=tk.FLAT, bg="white", validate='key', validatecommand=self.vcmd)
                val = notas_data["principales"][j]
                if val is not None: e.insert(0, str(val))
                e.bind("<KeyRelease>", self._marcar_cambios_pendientes)
                e.grid(row=row, column=c_idx, padx=1, pady=1); c_idx += 1; e_dict["p"].append(e)
            
            ex = tk.Entry(self.grid_container, width=5, justify=tk.CENTER, relief=tk.FLAT, bg="#F8F9FA", validate='key', validatecommand=self.vcmd)
            val_ex = notas_data[K_EXTRAS][0] if notas_data[K_EXTRAS] else None
            if val_ex is not None: ex.insert(0, str(val_ex))
            ex.bind("<KeyRelease>", self._marcar_cambios_pendientes)
            ex.grid(row=row, column=c_idx, padx=1, pady=1); c_idx += 1; e_dict["ex"] = ex
            self.widgets_entradas[id_al].append(e_dict)
            
            l = tk.Label(self.grid_container, text="-", font=("Arial", 9, "bold"), bg="#F8F9FA")
            l.grid(row=row, column=c_idx, sticky="nsew", padx=1, pady=1); c_idx += 1
            self.widgets_resultados[id_al]["trim"].append(l)

        # --- FILAS DE PROMEDIOS FINALES (CORREGIDO PARA ALINEAR CON EL CABECERAS) ---
        for j in range(4):
            # Aplicamos el margen de 30 píxeles a la izquierda solo al primer cuadro (T1)
            # Esto empuja toda la sección hacia la derecha para que coincida con el título
            separacion_seccion = (30, 1) if j == 0 else 1
            
            l_f = tk.Label(self.grid_container, text="-", font=("Arial", 10, "bold"), bg="#F8F9FA")
            l_f.grid(row=row, column=18+j, sticky="nsew", padx=separacion_seccion, pady=1)
            self.widgets_resultados[id_al]["fin"].append(l_f)
            
        # --- CÁLCULO AUTOMÁTICO Y FORMATO DE COLOR AL CARGAR ---
        res_cargados = procesar_calificaciones_alumno(al_data[K_TRIMESTRES])
        self._actualizar_promedios_ui(id_al, res_cargados)

    def _actualizar_promedios_ui(self, id_al, resultados):
        # Actualiza los labels de promedio para un alumno específico
        for t_idx, prom_t in enumerate(resultados["trimestres"]):
            val_txt = f"{prom_t:.2f}" if prom_t is not None else "-"
            color = self.paleta["rojo_fuerte"] if (prom_t is not None and prom_t < 6) else (self.paleta["verde_fuerte"] if prom_t is not None else self.paleta["texto_principal"])
            self.widgets_resultados[id_al]["trim"][t_idx].config(text=val_txt, fg=color)
            self.widgets_resultados[id_al]["fin"][t_idx].config(text=val_txt, fg=color)
        
        # Color para el promedio final total
        p_final = resultados['final']
        color_f = self.paleta["rojo_fuerte"] if (p_final > 0 and p_final < 6) else (self.paleta["verde_fuerte"] if p_final > 0 else self.paleta["texto_principal"])
        self.widgets_resultados[id_al]["fin"][3].config(text=f"{p_final:.2f}" if p_final > 0 else "-", fg=color_f)

    def agregar_alumno(self, nombre_curso):
        col = self.colegio_seleccionado
        alumnos = self.datos[K_COLEGIOS][col][K_CURSOS][nombre_curso][K_ALUMNOS]
        nuevo_id = str(max([int(k) for k in alumnos.keys()] + [0]) + 1)
        alumnos[nuevo_id] = {K_NOMBRE: "", K_TRIMESTRES: {t: {K_PRINCIPALES: [None]*3, K_EXTRAS: [None]} for t in NOMBRES_TRIMESTRES}}
        guardar_datos(self.datos); self.mostrar_apartado_curso(nombre_curso)

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
        guardar_datos(self.datos)

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

        guardar_datos(self.datos)
        self.hay_cambios_sin_guardar = False
        messagebox.showinfo("Éxito", "Cambios guardados.")

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
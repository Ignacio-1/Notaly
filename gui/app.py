import tkinter as tk
from tkinter import simpledialog, messagebox
from core.gestor_datos import cargar_datos, guardar_datos

class AppPromedios:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Promedios Escolares")
        self.root.geometry("700x500")
        
        # Carga los datos del disco local al iniciar
        self.datos = cargar_datos()
        self.frame_actual = None
        
        self.mostrar_pantalla_inicio()

    def limpiar_pantalla(self):
        # Destruye los elementos visuales actuales para dibujar la nueva pantalla
        if self.frame_actual is not None:
            self.frame_actual.destroy()

    def mostrar_pantalla_inicio(self):
        self.limpiar_pantalla()
        self.frame_actual = tk.Frame(self.root)
        self.frame_actual.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(self.frame_actual, text="Cursos Existentes", font=("Arial", 18, "bold")).pack(pady=10)

        # Renderiza botones para cada curso guardado en disco
        for curso in self.datos.get("cursos", {}).keys():
            btn = tk.Button(self.frame_actual, text=curso, font=("Arial", 12),
                            command=lambda c=curso: self.mostrar_apartado_curso(c))
            btn.pack(fill=tk.X, pady=5)

        tk.Button(self.frame_actual, text="+ Crear Nuevo Curso", bg="blue", fg="white", 
                  font=("Arial", 12, "bold"), command=self.flujo_crear_curso).pack(pady=30)

    def flujo_crear_curso(self):
        # Solicitud de datos mediante ventanas emergentes (Dialogs)
        nombre_curso = simpledialog.askstring("Nuevo Curso", "Ingresa el nombre del curso:")
        if not nombre_curso:
            return

        cantidad_str = simpledialog.askstring("Alumnos", "Cantidad de alumnos:")
        if not cantidad_str or not cantidad_str.isdigit():
            messagebox.showerror("Error", "Debes ingresar una cantidad numérica entera válida.")
            return

        cantidad_alumnos = int(cantidad_str)
        
        # Generación de la estructura de datos exigida para el nuevo curso
        estructura_trimestres = {
            "Primer trimestre": {"principales": [None, None, None], "extras": []},
            "Segundo trimestre": {"principales": [None, None, None], "extras": []},
            "Tercer trimestre": {"principales": [None, None, None], "extras": []}
        }

        alumnos_dict = {}
        for i in range(1, cantidad_alumnos + 1):
            alumnos_dict[f"Alumno {i}"] = {"nombre_real": "", "trimestres": estructura_trimestres.copy()}

        # Se inyecta en los datos en memoria y se guarda en el disco local
        self.datos["cursos"][nombre_curso] = {"alumnos": alumnos_dict}
        guardar_datos(self.datos)
        
        # Redirección automática al apartado del nuevo curso
        self.mostrar_apartado_curso(nombre_curso)

    def mostrar_apartado_curso(self, nombre_curso):
        self.limpiar_pantalla()
        self.frame_actual = tk.Frame(self.root)
        self.frame_actual.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(self.frame_actual, text=f"Gestión: {nombre_curso}", font=("Arial", 16, "bold")).pack(pady=10)

        curso_data = self.datos["cursos"][nombre_curso]
        
        # Despliegue del listado de alumnos numerados
        for i, (id_alumno, info) in enumerate(curso_data["alumnos"].items(), start=1):
            frame_alumno = tk.Frame(self.frame_actual)
            frame_alumno.pack(fill=tk.X, pady=2)
            
            nombre_display = info["nombre_real"] if info["nombre_real"] else "[Sin nombre asignado]"
            tk.Label(frame_alumno, text=f"{i}. {id_alumno} - {nombre_display}").pack(side=tk.LEFT)
            
            # Botones de gestión individual (esqueleto)
            tk.Button(frame_alumno, text="Editar/Notas", fg="blue").pack(side=tk.RIGHT, padx=5)
            tk.Button(frame_alumno, text="Eliminar", fg="red").pack(side=tk.RIGHT)

        tk.Button(self.frame_actual, text="Volver al Inicio", command=self.mostrar_pantalla_inicio).pack(pady=20)
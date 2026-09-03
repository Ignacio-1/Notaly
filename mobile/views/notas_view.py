"""
Vista de Planilla de Notas: Cuadrícula responsive interactiva para carga de notas,
cálculo de promedios en tiempo real, recuperatorios y visualización por trimestres.
"""

import flet as ft
from mobile.state import AppState
from mobile.components.grade_editor import GradeEditorDialog
from mobile.components.student_dialog import (
    CreateEntityDialog,
    RenameDialog,
    ConfirmDeleteDialog,
    CustomizeColumnsDialog,
    StudentFormDialog,
)
from mobile.components.export_dialog import ExportDialog
from core.constants import (
    NOMBRES_TRIMESTRES,
    NUM_PRINCIPALES,
    NUM_EXTRAS,
    UMBRAL_RECUPERATORIO,
    NOTA_MINIMA_APROBACION,
)
from core.calculos import procesar_calificaciones_alumno


class NotasView(ft.Container):
    def __init__(self, state: AppState, page: ft.Page, on_navigate: callable):
        super().__init__(expand=True)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = ft.Padding(left=8, right=8, top=6, bottom=12)

        self._build_ui()

    def _color_por_nota(self, nota: int | float | None) -> tuple[str, str]:
        """Retorna (color_fondo, color_texto) según la calificación."""
        if nota is None:
            return ft.Colors.SURFACE_CONTAINER_HIGHEST, ft.Colors.GREY_600
        if nota >= NOTA_MINIMA_APROBACION:
            return "#DCFCE7", "#166534"  # Verde suave / verde oscuro
        return "#FEE2E2", "#991B1B"      # Rojo suave / rojo oscuro

    def _build_ui(self):
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        curso_data = self.state.get_curso_data(colegio, curso)
        alumnos = self.state.get_alumnos(colegio, curso)
        trim_idx = self.state.active_trimestre
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        # Barra superior con navegación y selector de módulo (Notas / Asistencias)
        header_top = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="Volver a Cursos",
                    on_click=lambda e: self._accion_volver(),
                ),
                ft.Column(
                    [
                        ft.Text(f"{curso} - {colegio}", size=16, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text("Planilla de Calificaciones", size=12, color=ft.Colors.SECONDARY),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.SegmentedButton(
                    selected=["notas"],
                    segments=[
                        ft.Segment(value="notas", label=ft.Text("Notas", size=12), icon=ft.Icon(ft.Icons.EDIT_NOTE, size=18)),
                        ft.Segment(value="asistencias", label=ft.Text("Asistencia", size=12), icon=ft.Icon(ft.Icons.CHECKLIST, size=18)),
                    ],
                    on_change=lambda e: self._cambiar_pestana(e.control.selected),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Selector de trimestre (SegmentedButton Material 3)
        tabs_trimestres = ft.Row(
            [
                ft.SegmentedButton(
                    selected=[str(trim_idx)],
                    segments=[
                        ft.Segment(value="0", label=ft.Text("1° Trim", size=12)),
                        ft.Segment(value="1", label=ft.Text("2° Trim", size=12)),
                        ft.Segment(value="2", label=ft.Text("3° Trim", size=12)),
                        ft.Segment(value="3", label=ft.Text("Anual", size=12), icon=ft.Icon(ft.Icons.ANALYTICS, size=16)),
                    ],
                    on_change=self._on_trimestre_change,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # Barra de acciones (Guardar, + Alumno, Columnas, Exportar, Ordenar)
        self.btn_guardar = ft.FilledButton(
            "Guardar",
            icon=ft.Icons.SAVE,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.AMBER_800 if self.state.has_unsaved_changes else ft.Colors.PRIMARY,
                color=ft.Colors.WHITE,
            ),
            on_click=lambda e: self._guardar_notas(),
        )

        actions_bar = ft.Row(
            [
                self.btn_guardar,
                ft.OutlinedButton(
                    "+ Alumno",
                    icon=ft.Icons.PERSON_ADD,
                    on_click=lambda e: self._abrir_modal_agregar_alumno(),
                ),
                ft.IconButton(
                    icon=ft.Icons.TUNE,
                    tooltip="Personalizar Columnas",
                    on_click=lambda e: self._abrir_modal_columnas(),
                ),
                ft.IconButton(
                    icon=ft.Icons.SORT_BY_ALPHA,
                    tooltip="Ordenar Alumnos (A-Z)",
                    on_click=lambda e: self._ordenar_alumnos_az(),
                ),
                ft.IconButton(
                    icon=ft.Icons.SHARE,
                    tooltip="Exportar Planilla (PDF/CSV/TXT)",
                    on_click=lambda e: self._abrir_modal_exportar(),
                ),
            ],
            wrap=True,
            spacing=8,
            alignment=ft.MainAxisAlignment.START,
        )

        # Construcción de la tabla de datos
        tabla_contenido = self._construir_tabla(alumnos, trim_idx, nombres_cols, curso_data)

        self.content = ft.Column(
            controls=[
                header_top,
                tabs_trimestres,
                actions_bar,
                ft.Divider(height=8, color=ft.Colors.TRANSPARENT),
                ft.Container(
                    content=tabla_contenido,
                    expand=True,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=8,
                    padding=4,
                ),
            ],
            expand=True,
            spacing=6,
        )

    def _actualizar_boton_guardar(self):
        if hasattr(self, "btn_guardar"):
            self.btn_guardar.style = ft.ButtonStyle(
                bgcolor=ft.Colors.AMBER_800 if self.state.has_unsaved_changes else ft.Colors.PRIMARY,
                color=ft.Colors.WHITE,
            )

    def _construir_tabla(self, alumnos: dict, trim_idx: int, nombres_cols: list[str], curso_data: dict) -> ft.Control:
        self.alumnos_celdas = {}
        if not alumnos:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.GROUP_OUTLINED, size=60, color=ft.Colors.GREY_400),
                        ft.Text("No hay alumnos en este curso", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                        ft.Text("Toca '+ Alumno' para agregar alumnos a la planilla.", size=13, color=ft.Colors.GREY_500),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
                alignment=ft.Alignment.CENTER,
                padding=40,
            )

        if trim_idx < 3:
            # Vista de un Trimestre Específico (1°, 2° o 3°)
            nombre_trim = NOMBRES_TRIMESTRES[trim_idx]
            columns = [
                ft.DataColumn(ft.Text("N°", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Alumno", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text(nombres_cols[0], weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text(nombres_cols[1], weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text(nombres_cols[2], weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text(nombres_cols[3], weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Prom.", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Recup.", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Final", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("...", weight=ft.FontWeight.BOLD, size=12)),
            ]

            rows = []
            for id_al, al_data in alumnos.items():
                nombre_al = al_data.get("nombre", "Sin nombre")
                trim_data = al_data.get("trimestres", {}).get(nombre_trim, {})
                principales = trim_data.get("principales", [None] * NUM_PRINCIPALES)
                extras = trim_data.get("extras", [None] * NUM_EXTRAS)
                recuperatorio = trim_data.get("recuperatorio")

                calcs = procesar_calificaciones_alumno(al_data.get("trimestres", {}))
                prom_crudo_red = calcs["promedios_crudos_redondeados"][trim_idx]
                nota_final_red = calcs["notas_finales_redondeadas"][trim_idx]

                habilita_recup = prom_crudo_red is not None and prom_crudo_red <= UMBRAL_RECUPERATORIO

                # Celdas interactivas
                cell_p1, ref_p1 = self._crear_celda_nota(nombre_al, nombres_cols[0], principales[0] if len(principales) > 0 else None, id_al, trim_idx, "P", 0)
                cell_p2, ref_p2 = self._crear_celda_nota(nombre_al, nombres_cols[1], principales[1] if len(principales) > 1 else None, id_al, trim_idx, "P", 1)
                cell_p3, ref_p3 = self._crear_celda_nota(nombre_al, nombres_cols[2], principales[2] if len(principales) > 2 else None, id_al, trim_idx, "P", 2)
                cell_ex, ref_ex = self._crear_celda_nota(nombre_al, nombres_cols[3], extras[0] if len(extras) > 0 else None, id_al, trim_idx, "E", 0)
                
                # Celda recuperatorio
                cell_rec, ref_rec = self._crear_celda_nota(
                    nombre_al,
                    "Recuperatorio",
                    recuperatorio,
                    id_al,
                    trim_idx,
                    "R",
                    0,
                    deshabilitado=not habilita_recup and recuperatorio is None,
                )

                # Celdas calculadas
                bg_prom, fg_prom = self._color_por_nota(prom_crudo_red)
                bg_fin, fg_fin = self._color_por_nota(nota_final_red)

                prom_text = ft.Text(str(prom_crudo_red) if prom_crudo_red is not None else "-", weight=ft.FontWeight.BOLD, color=fg_prom, size=13)
                cell_prom_widget = ft.Container(
                    content=prom_text,
                    bgcolor=bg_prom,
                    padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                    border_radius=6,
                    alignment=ft.Alignment.CENTER,
                )

                fin_text = ft.Text(str(nota_final_red) if nota_final_red is not None else "-", weight=ft.FontWeight.BOLD, color=fg_fin, size=14)
                cell_fin_widget = ft.Container(
                    content=fin_text,
                    bgcolor=bg_fin,
                    padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                    border_radius=6,
                    alignment=ft.Alignment.CENTER,
                )

                self.alumnos_celdas[str(id_al)] = {
                    "P0": ref_p1,
                    "P1": ref_p2,
                    "P2": ref_p3,
                    "E0": ref_ex,
                    "R0": ref_rec,
                    "prom_container": cell_prom_widget,
                    "prom_text": prom_text,
                    "fin_container": cell_fin_widget,
                    "fin_text": fin_text,
                    "nombre": nombre_al,
                }

                # Menú acciones de alumno
                menu_alumno = ft.PopupMenuButton(
                    icon=ft.Icons.MORE_HORIZ,
                    items=[
                        ft.PopupMenuItem(
                            icon=ft.Icons.EDIT_OUTLINED,
                            content=ft.Text("Renombrar"),
                            on_click=lambda e, i=id_al, n=nombre_al: self._abrir_modal_renombrar_alumno(i, n),
                        ),
                        ft.PopupMenuItem(
                            icon=ft.Icons.DELETE_OUTLINE,
                            content=ft.Text("Eliminar Alumno"),
                            on_click=lambda e, i=id_al, n=nombre_al: self._abrir_modal_eliminar_alumno(i, n),
                        ),
                    ],
                )

                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(id_al), size=12, color=ft.Colors.GREY_700)),
                            ft.DataCell(ft.Text(nombre_al, size=13, weight=ft.FontWeight.W_500, max_lines=1)),
                            cell_p1,
                            cell_p2,
                            cell_p3,
                            cell_ex,
                            ft.DataCell(cell_prom_widget),
                            cell_rec,
                            ft.DataCell(cell_fin_widget),
                            ft.DataCell(menu_alumno),
                        ]
                    )
                )

        else:
            # Vista de Resumen Anual
            columns = [
                ft.DataColumn(ft.Text("N°", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("Alumno", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("1° Trim", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("2° Trim", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("3° Trim", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("FINAL TOTAL", weight=ft.FontWeight.BOLD, size=13)),
                ft.DataColumn(ft.Text("Condición", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("...", weight=ft.FontWeight.BOLD, size=12)),
            ]

            rows = []
            for id_al, al_data in alumnos.items():
                nombre_al = al_data.get("nombre", "Sin nombre")
                calcs = procesar_calificaciones_alumno(al_data.get("trimestres", {}))
                t1 = calcs["notas_finales_redondeadas"][0]
                t2 = calcs["notas_finales_redondeadas"][1]
                t3 = calcs["notas_finales_redondeadas"][2]
                total = calcs["nota_final_total_redondeada"]

                def make_badge(nota):
                    bg, fg = self._color_por_nota(nota)
                    return ft.Container(
                        content=ft.Text(str(nota) if nota is not None else "-", weight=ft.FontWeight.BOLD, color=fg, size=13),
                        bgcolor=bg,
                        padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                        border_radius=6,
                        alignment=ft.Alignment.CENTER,
                    )

                if total is not None:
                    if total >= NOTA_MINIMA_APROBACION:
                        condicion = ft.Container(
                            content=ft.Text("APROBADO", size=11, weight=ft.FontWeight.BOLD, color="#166534"),
                            bgcolor="#DCFCE7",
                            padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                            border_radius=12,
                        )
                    else:
                        condicion = ft.Container(
                            content=ft.Text("DESAPROBADO", size=11, weight=ft.FontWeight.BOLD, color="#991B1B"),
                            bgcolor="#FEE2E2",
                            padding=ft.Padding(left=8, right=8, top=3, bottom=3),
                            border_radius=12,
                        )
                else:
                    condicion = ft.Text("En curso", size=12, color=ft.Colors.GREY_600)

                menu_alumno = ft.PopupMenuButton(
                    icon=ft.Icons.MORE_HORIZ,
                    items=[
                        ft.PopupMenuItem(
                            icon=ft.Icons.EDIT_OUTLINED,
                            content=ft.Text("Renombrar"),
                            on_click=lambda e, i=id_al, n=nombre_al: self._abrir_modal_renombrar_alumno(i, n),
                        ),
                        ft.PopupMenuItem(
                            icon=ft.Icons.DELETE_OUTLINE,
                            content=ft.Text("Eliminar Alumno"),
                            on_click=lambda e, i=id_al, n=nombre_al: self._abrir_modal_eliminar_alumno(i, n),
                        ),
                    ],
                )

                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(id_al), size=12, color=ft.Colors.GREY_700)),
                            ft.DataCell(ft.Text(nombre_al, size=13, weight=ft.FontWeight.W_500, max_lines=1)),
                            ft.DataCell(make_badge(t1)),
                            ft.DataCell(make_badge(t2)),
                            ft.DataCell(make_badge(t3)),
                            ft.DataCell(make_badge(total)),
                            ft.DataCell(condicion),
                            ft.DataCell(menu_alumno),
                        ]
                    )
                )

        table = ft.DataTable(
            columns=columns,
            rows=rows,
            column_spacing=14,
            heading_row_height=38,
            data_row_min_height=42,
            data_row_max_height=48,
        )

        # Envoltorio con scroll horizontal y vertical
        return ft.ListView(
            controls=[
                ft.Row(
                    controls=[table],
                    scroll=ft.ScrollMode.ADAPTIVE,
                )
            ],
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
        )

    def _actualizar_fila_alumno_ui(self, id_al: str):
        """Actualiza in-place las celdas y cálculos del alumno sin recrear la tabla ni resetear el scroll."""
        id_str = str(id_al)
        if not hasattr(self, "alumnos_celdas") or id_str not in self.alumnos_celdas:
            return

        celdas = self.alumnos_celdas[id_str]
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso)
        al_data = alumnos.get(id_str)
        if not al_data:
            return

        trim_idx = self.state.active_trimestre
        if trim_idx >= 3:
            return

        nombre_trim = NOMBRES_TRIMESTRES[trim_idx]
        trim_data = al_data.get("trimestres", {}).get(nombre_trim, {})
        principales = trim_data.get("principales", [None] * NUM_PRINCIPALES)
        extras = trim_data.get("extras", [None] * NUM_EXTRAS)
        recuperatorio = trim_data.get("recuperatorio")

        calcs = procesar_calificaciones_alumno(al_data.get("trimestres", {}))
        prom_crudo_red = calcs["promedios_crudos_redondeados"][trim_idx]
        nota_final_red = calcs["notas_finales_redondeadas"][trim_idx]
        habilita_recup = prom_crudo_red is not None and prom_crudo_red <= UMBRAL_RECUPERATORIO

        # Actualizar celdas de notas
        notas_map = {
            "P0": principales[0] if len(principales) > 0 else None,
            "P1": principales[1] if len(principales) > 1 else None,
            "P2": principales[2] if len(principales) > 2 else None,
            "E0": extras[0] if len(extras) > 0 else None,
        }
        for key, val in notas_map.items():
            if key in celdas:
                ref = celdas[key]
                ref["valor"] = val
                val_str = "-" if val is None else (str(int(val)) if isinstance(val, float) and val.is_integer() else str(val))
                bg, fg = self._color_por_nota(val)
                ref["text_widget"].value = val_str
                ref["text_widget"].color = fg
                ref["container"].bgcolor = bg

        # Actualizar celda de recuperatorio
        if "R0" in celdas:
            ref_r = celdas["R0"]
            ref_r["valor"] = recuperatorio
            deshabilitado = not habilita_recup and recuperatorio is None
            ref_r["deshabilitado"] = deshabilitado
            if deshabilitado:
                ref_r["text_widget"].value = "-"
                ref_r["text_widget"].color = ft.Colors.GREY_400
                ref_r["container"].bgcolor = ft.Colors.TRANSPARENT
                ref_r["container"].border = None
            else:
                val_str = "-" if recuperatorio is None else (str(int(recuperatorio)) if isinstance(recuperatorio, float) and recuperatorio.is_integer() else str(recuperatorio))
                bg, fg = self._color_por_nota(recuperatorio)
                ref_r["text_widget"].value = val_str
                ref_r["text_widget"].color = fg
                ref_r["container"].bgcolor = bg
                ref_r["container"].border = ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)

        # Actualizar celdas de promedio y final
        bg_prom, fg_prom = self._color_por_nota(prom_crudo_red)
        celdas["prom_text"].value = str(prom_crudo_red) if prom_crudo_red is not None else "-"
        celdas["prom_text"].color = fg_prom
        celdas["prom_container"].bgcolor = bg_prom

        bg_fin, fg_fin = self._color_por_nota(nota_final_red)
        celdas["fin_text"].value = str(nota_final_red) if nota_final_red is not None else "-"
        celdas["fin_text"].color = fg_fin
        celdas["fin_container"].bgcolor = bg_fin

    def _crear_celda_nota(
        self,
        nombre_alumno: str,
        nombre_eval: str,
        valor: float | int | None,
        id_al: str,
        trim_idx: int,
        tipo: str,
        index: int,
        deshabilitado: bool = False,
    ) -> tuple[ft.DataCell, dict]:
        """Crea un DataCell táctil para la celda de nota y retorna su objeto de referencia."""
        val_str = "-" if (valor is None or deshabilitado) else (str(int(valor)) if isinstance(valor, float) and valor.is_integer() else str(valor))
        bg_color, text_color = self._color_por_nota(valor) if not deshabilitado else (ft.Colors.TRANSPARENT, ft.Colors.GREY_400)

        txt_widget = ft.Text(
            val_str,
            weight=ft.FontWeight.BOLD if not deshabilitado else ft.FontWeight.NORMAL,
            size=13,
            color=text_color,
        )
        container = ft.Container(
            content=txt_widget,
            bgcolor=bg_color,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT) if not deshabilitado else None,
            border_radius=6,
            width=42,
            height=32,
            alignment=ft.Alignment.CENTER,
        )

        ref = {
            "container": container,
            "text_widget": txt_widget,
            "valor": valor,
            "deshabilitado": deshabilitado,
        }

        def on_tap(e):
            if ref.get("deshabilitado"):
                return

            def guardar_valor(nuevo_val):
                self.state.set_nota(id_al, trim_idx, tipo, index, nuevo_val)
                # Actualizar in-place sin recargar la lista ni reiniciar el scroll
                self._actualizar_fila_alumno_ui(id_al)
                self._actualizar_boton_guardar()
                self.app_page.update()

            dlg = GradeEditorDialog(
                alumno_nombre=nombre_alumno,
                columna_nombre=nombre_eval,
                valor_actual=ref.get("valor"),
                on_save=guardar_valor,
                page=self.app_page,
            )
            self.app_page.show_dialog(dlg)
            self.app_page.update()

        container.on_click = on_tap
        data_cell = ft.DataCell(container, on_tap=on_tap)
        return data_cell, ref

    def _on_trimestre_change(self, e):
        selected = list(e.control.selected)
        if selected:
            self.state.active_trimestre = int(selected[0])
            self._build_ui()
            self.app_page.update()

    def _cambiar_pestana(self, selected_set):
        if "asistencias" in selected_set:
            if self.state.has_unsaved_changes:
                self._preguntar_guardar_antes_de_salir(destino="asistencias")
            else:
                self.on_navigate("asistencias")

    def _accion_volver(self):
        if self.state.has_unsaved_changes:
            self._preguntar_guardar_antes_de_salir(destino="cursos")
        else:
            self.on_navigate("cursos")

    def _preguntar_guardar_antes_de_salir(self, destino: str):
        def cerrar_dialogo():
            self.app_page.pop_dialog()
            self.app_page.update()

        def guardar_y_salir():
            cerrar_dialogo()
            self.state.save_data()
            self.on_navigate(destino)

        def salir_sin_guardar():
            cerrar_dialogo()
            self.state.load_data()  # Revertir cambios no guardados
            self.on_navigate(destino)

        dlg = ft.AlertDialog(
            title=ft.Text("Cambios sin guardar", weight=ft.FontWeight.BOLD),
            content=ft.Text("Tienes calificaciones modificadas sin guardar.\n¿Deseas guardarlas antes de continuar?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo()),
                ft.TextButton("Descartar", style=ft.ButtonStyle(color=ft.Colors.RED_600), on_click=lambda e: salir_sin_guardar()),
                ft.FilledButton("Guardar y Salir", on_click=lambda e: guardar_y_salir()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            modal=True,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _guardar_notas(self):
        if self.state.save_data():
            self._build_ui()
            self.app_page.update()
            self._mostrar_snackbar("Calificaciones guardadas exitosamente.")
        else:
            self._mostrar_snackbar("Error al guardar calificaciones.", error=True)

    def _abrir_modal_agregar_alumno(self):
        from core.constants import separar_nombre_completo

        def confirmar(apellido: str, nombre: str):
            exito, msg = self.state.add_alumno(apellido, nombre)
            if exito:
                self._build_ui()
                self.app_page.update()
                self._mostrar_snackbar(msg)
                return True
            else:
                self._mostrar_snackbar(msg, error=True)
                return False

        dlg = StudentFormDialog(
            titulo="Agregar Alumno",
            on_confirm=confirmar,
            modo_continuo=True,
            page=self.app_page,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_modal_renombrar_alumno(self, id_al: str, nombre_actual: str):
        from core.constants import separar_nombre_completo
        ap_act, nom_act = separar_nombre_completo(nombre_actual)

        def confirmar(nuevo_apellido: str, nuevo_nombre: str):
            exito, msg = self.state.rename_alumno(id_al, nuevo_apellido, nuevo_nombre)
            if exito:
                self._build_ui()
                self.app_page.update()
                self._mostrar_snackbar(msg)
                return True
            else:
                self._mostrar_snackbar(msg, error=True)
                return False

        dlg = StudentFormDialog(
            titulo=f"Editar Alumno #{id_al}",
            apellido_actual=ap_act,
            nombre_actual=nom_act,
            modo_continuo=False,
            on_confirm=confirmar,
            page=self.app_page,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_modal_eliminar_alumno(self, id_al: str, nombre: str):
        def confirmar():
            exito, msg = self.state.delete_alumno(id_al)
            if exito:
                self._build_ui()
                self.app_page.update()
                self._mostrar_snackbar(msg)
            else:
                self._mostrar_snackbar(msg, error=True)

        dlg = ConfirmDeleteDialog(
            titulo="Eliminar Alumno",
            mensaje=f"¿Estás seguro de que deseas eliminar al alumno '{nombre}' (N° {id_al}) y todas sus notas y asistencias?",
            on_confirm=confirmar,
            page=self.app_page,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_modal_columnas(self):
        trim_idx = self.state.active_trimestre
        nombres_actuales = self.state.get_nombres_columnas(trimestre=trim_idx)

        def guardar_cols(nuevos):
            self.state.set_nombres_columnas(nuevos, trimestre=trim_idx)
            self._build_ui()
            self.app_page.update()
            self._mostrar_snackbar("Nombres de columnas actualizados.")

        dlg = CustomizeColumnsDialog(
            nombres_actuales=nombres_actuales,
            on_save=guardar_cols,
            page=self.app_page,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _ordenar_alumnos_az(self):
        self.state.order_alumnos_alphabetically()
        self._build_ui()
        self.app_page.update()
        self._mostrar_snackbar("Alumnos ordenados alfabéticamente (A-Z).")

    def _abrir_modal_exportar(self):
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        curso_data = self.state.get_curso_data(colegio, curso)

        def resultado_exportacion(exito, detalle):
            if exito:
                self._mostrar_snackbar(f"Exportado correctamente en: {detalle}")
            else:
                self._mostrar_snackbar(f"Error al exportar: {detalle}", error=True)

        dlg = ExportDialog(
            tipo_exportacion="notas",
            colegio_nombre=colegio,
            curso_nombre=curso,
            curso_data=curso_data,
            on_success=resultado_exportacion,
            page=self.app_page,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _mostrar_snackbar(self, mensaje: str, error: bool = False):
        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.ERROR if error else ft.Colors.GREEN_700,
        )
        self.app_page.overlay.append(sb)
        sb.open = True
        self.app_page.update()

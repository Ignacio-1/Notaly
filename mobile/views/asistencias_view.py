"""
Vista de Asistencias: Control táctil diario de asistencia de alumnos,
estadísticas en tiempo real, selector de fechas y exportación.
"""

from datetime import datetime, date, timedelta
import flet as ft
from mobile.state import AppState
from mobile.components.export_dialog import ExportDialog
from core.constants import (
    ESTADO_PRESENTE,
    ESTADO_AUSENTE,
    ESTADO_TARDE,
    ESTADO_JUSTIFICADO,
    ESTADOS_ASISTENCIA,
    INFO_ESTADOS_ASISTENCIA,
)


class AsistenciasView(ft.Container):
    def __init__(self, state: AppState, page: ft.Page, on_navigate: callable):
        super().__init__(expand=True)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = ft.Padding(left=10, right=10, top=6, bottom=12)

        self._build_ui()

    def _formatear_fecha(self, fecha_iso: str) -> str:
        try:
            dt = datetime.strptime(fecha_iso, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return fecha_iso

    def _build_ui(self):
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        curso_data = self.state.get_curso_data(colegio, curso)
        alumnos = self.state.get_alumnos(colegio, curso)
        fecha_actual = self.state.asistencia_fecha
        asistencias_dia = self.state.get_asistencias_dia(fecha_actual, colegio, curso)

        # 1. Barra superior
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
                        ft.Text("Control de Asistencias", size=12, color=ft.Colors.SECONDARY),
                    ],
                    spacing=1,
                    expand=True,
                ),
                ft.SegmentedButton(
                    selected=["asistencias"],
                    segments=[
                        ft.Segment(value="notas", label=ft.Text("Notas", size=12), icon=ft.Icon(ft.Icons.EDIT_NOTE, size=18)),
                        ft.Segment(value="asistencias", label=ft.Text("Asistencia", size=12), icon=ft.Icon(ft.Icons.CHECKLIST, size=18)),
                    ],
                    on_change=lambda e: self._cambiar_pestana(e.control.selected),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # 2. Selector y navegación de Fecha
        fecha_str = self._formatear_fecha(fecha_actual)
        date_bar = ft.Card(
            elevation=1,
            shape=ft.RoundedRectangleBorder(radius=10),
            content=ft.Container(
                padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                content=ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.CHEVRON_LEFT,
                            tooltip="Día Anterior",
                            on_click=lambda e: self._cambiar_dia(-1),
                        ),
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.CALENDAR_MONTH, color=ft.Colors.PRIMARY, size=20),
                                ft.Text(fecha_str, size=15, weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=6,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CHEVRON_RIGHT,
                            tooltip="Día Siguiente",
                            on_click=lambda e: self._cambiar_dia(1),
                        ),
                        ft.TextButton(
                            "Hoy",
                            on_click=lambda e: self._ir_a_hoy(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )

        # 3. Estadísticas del Día
        resumen_dia = self.state.get_resumen_asistencia_dia(fecha_actual, colegio, curso)
        presentes = resumen_dia["presentes"]
        ausentes = resumen_dia["ausentes"]
        tardes = resumen_dia["tardes"]
        justificados = resumen_dia["justificados"]
        porc_dia = resumen_dia.get("porcentaje_asistencia", 0.0)

        def make_kpi(label, val, color_bg, color_fg):
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Text(str(val), weight=ft.FontWeight.BOLD, size=15, color=color_fg),
                        ft.Text(label, size=11, color=color_fg, weight=ft.FontWeight.W_500),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=1,
                ),
                bgcolor=color_bg,
                border_radius=8,
                padding=ft.Padding(left=10, right=10, top=6, bottom=6),
                expand=True,
                alignment=ft.Alignment.CENTER,
            )

        kpi_row = ft.Row(
            [
                make_kpi("Presentes", presentes, "#DCFCE7", "#166534"),
                make_kpi("Ausentes", ausentes, "#FEE2E2", "#991B1B"),
                make_kpi("Tardes", tardes, "#FEF3C7", "#92400E"),
                make_kpi("Justificados", justificados, "#DBEAFE", "#1E40AF"),
                make_kpi("% Asist.", f"{porc_dia}%", "#F3F4F6", "#374151"),
            ],
            spacing=6,
        )

        # 4. Barra de Acciones de Asistencia
        btn_guardar = ft.FilledButton(
            "Guardar",
            icon=ft.Icons.SAVE,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.AMBER_800 if self.state.has_unsaved_asistencias else ft.Colors.PRIMARY,
                color=ft.Colors.WHITE,
            ),
            on_click=lambda e: self._guardar_asistencias(),
        )

        actions_bar = ft.Row(
            [
                btn_guardar,
                ft.OutlinedButton(
                    "Todos Presentes",
                    icon=ft.Icons.DONE_ALL,
                    on_click=lambda e: self._marcar_todos_presentes(),
                ),
                ft.IconButton(
                    icon=ft.Icons.SHARE,
                    tooltip="Exportar Asistencias (PDF/CSV/TXT)",
                    on_click=lambda e: self._abrir_modal_exportar(),
                ),
            ],
            wrap=True,
            spacing=8,
            alignment=ft.MainAxisAlignment.START,
        )

        # 5. Lista de Alumnos para toma de asistencia
        lista_alumnos = self._construir_lista_alumnos(alumnos, asistencias_dia, fecha_actual)

        self.content = ft.Column(
            controls=[
                header_top,
                date_bar,
                kpi_row,
                actions_bar,
                ft.Divider(height=6, color=ft.Colors.TRANSPARENT),
                ft.Container(
                    content=lista_alumnos,
                    expand=True,
                ),
            ],
            expand=True,
            spacing=8,
        )

    def _construir_lista_alumnos(self, alumnos: dict, asistencias_dia: dict, fecha: str) -> ft.Control:
        if not alumnos:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.GROUP_OUTLINED, size=60, color=ft.Colors.GREY_400),
                        ft.Text("No hay alumnos en este curso", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                        ft.Text("Agrega alumnos desde la pestaña 'Notas' para tomar asistencia.", size=13, color=ft.Colors.GREY_500),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=8,
                ),
                alignment=ft.Alignment.CENTER,
                padding=40,
            )

        items = []
        for id_al, al_data in alumnos.items():
            nombre_al = al_data.get("nombre", "Sin nombre")
            estado_actual = asistencias_dia.get(str(id_al))

            # Selector de estado táctil con 4 botones: P, A, T, J
            def make_state_btn(estado_code, label, color_hex, student_id):
                seleccionado = estado_actual == estado_code
                return ft.Container(
                    content=ft.Text(
                        label,
                        weight=ft.FontWeight.BOLD if seleccionado else ft.FontWeight.NORMAL,
                        color=ft.Colors.WHITE if seleccionado else color_hex,
                        size=13,
                    ),
                    bgcolor=color_hex if seleccionado else ft.Colors.TRANSPARENT,
                    border=ft.Border.all(1.5, color_hex),
                    border_radius=8,
                    width=38,
                    height=36,
                    alignment=ft.Alignment.CENTER,
                    on_click=lambda e, st=estado_code, sid=student_id: self._cambiar_estado_alumno(sid, st),
                )

            btn_p = make_state_btn(ESTADO_PRESENTE, "P", "#10B981", str(id_al))
            btn_a = make_state_btn(ESTADO_AUSENTE, "A", "#EF4444", str(id_al))
            btn_t = make_state_btn(ESTADO_TARDE, "T", "#F59E0B", str(id_al))
            btn_j = make_state_btn(ESTADO_JUSTIFICADO, "J", "#3B82F6", str(id_al))

            card = ft.Card(
                elevation=1,
                margin=ft.Margin(bottom=6, left=0, right=0, top=0),
                shape=ft.RoundedRectangleBorder(radius=10),
                content=ft.Container(
                    padding=ft.Padding(left=12, right=10, top=8, bottom=8),
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(str(id_al), size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                                width=24,
                            ),
                            ft.Text(nombre_al, size=14, weight=ft.FontWeight.W_500, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row([btn_p, btn_a, btn_t, btn_j], spacing=4),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ),
            )
            items.append(card)

        return ft.ListView(controls=items, expand=True, spacing=4)

    def _cambiar_estado_alumno(self, id_al: str, estado: str):
        fecha = self.state.asistencia_fecha
        asistencias_actuales = self.state.get_asistencias_dia(fecha)
        nuevo_estado = "" if asistencias_actuales.get(str(id_al)) == estado else estado
        if nuevo_estado:
            self.state.set_asistencia_alumno(fecha, str(id_al), nuevo_estado)
        else:
            from core.constants import K_ASISTENCIAS
            curso_dict = self.state.get_curso_data()
            if curso_dict:
                asistencias = curso_dict.setdefault(K_ASISTENCIAS, {})
                dia_dict = asistencias.setdefault(fecha, {})
                if str(id_al) in dia_dict:
                    del dia_dict[str(id_al)]
                self.state.has_unsaved_asistencias = True
                self.state.notify()
        self._build_ui()
        self.app_page.update()

    def _marcar_todos_presentes(self):
        fecha = self.state.asistencia_fecha
        self.state.set_all_asistencias_dia(fecha, ESTADO_PRESENTE)
        self._build_ui()
        self.app_page.update()
        self._mostrar_snackbar("Todos los alumnos marcados como Presentes.")

    def _cambiar_dia(self, offset_dias: int):
        try:
            dt = datetime.strptime(self.state.asistencia_fecha, "%Y-%m-%d")
            nueva_fecha = dt + timedelta(days=offset_dias)
            self.state.asistencia_fecha = nueva_fecha.strftime("%Y-%m-%d")
            self._build_ui()
            self.app_page.update()
        except Exception:
            pass

    def _ir_a_hoy(self):
        self.state.asistencia_fecha = datetime.now().strftime("%Y-%m-%d")
        self._build_ui()
        self.app_page.update()

    def _cambiar_pestana(self, selected_set):
        if "notas" in selected_set:
            if self.state.has_unsaved_asistencias:
                self._preguntar_guardar_antes_de_salir(destino="notas")
            else:
                self.on_navigate("notas")

    def _accion_volver(self):
        if self.state.has_unsaved_asistencias:
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
            self.state.load_data()  # Revertir cambios
            self.on_navigate(destino)

        dlg = ft.AlertDialog(
            title=ft.Text("Asistencias sin guardar", weight=ft.FontWeight.BOLD),
            content=ft.Text("Tienes asistencias modificadas sin guardar.\n¿Deseas guardarlas antes de continuar?"),
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

    def _guardar_asistencias(self):
        if self.state.save_data():
            self._build_ui()
            self.app_page.update()
            self._mostrar_snackbar("Asistencias guardadas exitosamente.")
        else:
            self._mostrar_snackbar("Error al guardar asistencias.", error=True)

    def _abrir_modal_exportar(self):
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        curso_data = self.state.get_curso_data(colegio, curso)

        def resultado_exportacion(exito, detalle):
            if exito:
                self._mostrar_snackbar(f"Asistencias exportadas en: {detalle}")
            else:
                self._mostrar_snackbar(f"Error al exportar: {detalle}", error=True)

        dlg = ExportDialog(
            tipo_exportacion="asistencias",
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


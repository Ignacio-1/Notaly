"""
Vista de Asistencias: Control táctil diario de asistencia de alumnos,
estadísticas en tiempo real, selector de fechas, tarjetas de alumno con avatar
y dock inferior de marcado rápido (P, A, T, J).
Rediseñada con el sistema de diseño Slate 50 / Indigo 600 según la especificación.
"""

from datetime import datetime, date, timedelta
import flet as ft
from mobile.state import AppState
from mobile.components.export_dialog import ExportDialog
from mobile.components.date_picker_dialog import DatePickerDialog
from mobile.components.ui_header import (
    build_app_header,
    build_module_tabs,
    build_save_status_indicator,
    SaveStatusIndicator,
)
from mobile.theme import (
    BG_PAGE,
    SURFACE_WHITE,
    BORDER_COLOR,
    PRIMARY,
    PRIMARY_LIGHT,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUBTLE,
    WARNING_AMBER,
    ATTENDANCE_P_BG,
    ATTENDANCE_P_TEXT,
    ATTENDANCE_P_SOLID,
    ATTENDANCE_A_BG,
    ATTENDANCE_A_TEXT,
    ATTENDANCE_A_SOLID,
    ATTENDANCE_T_BG,
    ATTENDANCE_T_TEXT,
    ATTENDANCE_T_SOLID,
    ATTENDANCE_J_BG,
    ATTENDANCE_J_TEXT,
    ATTENDANCE_J_SOLID,
    get_avatar_palette,
    extract_initials,
)
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
        super().__init__(expand=True, bgcolor=BG_PAGE)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = 0

        # Alumno activo para marcado por dock inferior
        self.active_student_id: str | None = None

        # Indicador de estado de auto-guardado
        self.save_indicator = SaveStatusIndicator(status=self.state.save_status)
        self.state.on_save_status_change = self._on_save_status_change

        self._build_ui()

    def _on_save_status_change(self, status: str):
        """Notificación reactiva de cambio de estado de auto-guardado."""
        if hasattr(self, "save_indicator") and self.save_indicator:
            self.save_indicator.set_status(status)
            if hasattr(self, "app_page") and self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass

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

        if not self.active_student_id and alumnos:
            self.active_student_id = list(alumnos.keys())[0]

        # 1. Header superior
        header = build_app_header(
            eyebrow=colegio,
            title=curso,
            on_back=self._accion_volver,
            status_indicator=self.save_indicator,
            trailing=ft.IconButton(
                icon=ft.Icons.INSIGHTS,
                tooltip="Estadísticas del Curso",
                icon_color=PRIMARY,
                icon_size=20,
                on_click=lambda _: self._abrir_estadisticas_curso(),
            ),
        )

        # 2. Selector de módulo (Notas / Asistencia)
        module_tabs = ft.Container(
            padding=ft.Padding(left=16, right=16, top=6, bottom=6),
            content=build_module_tabs(active_tab="asistencias", on_change=lambda dest: self._cambiar_pestana([dest])),
        )

        # 3. Selector y navegación de fecha (Barra estilizada)
        fecha_str = self._formatear_fecha(fecha_actual)
        btn_fecha_central = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.CALENDAR_MONTH, color=PRIMARY, size=18),
                    ft.Text(fecha_str, size=14, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=PRIMARY, size=18),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
                tight=True,
            ),
            ink=True,
            border_radius=8,
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            tooltip="Buscar fecha en el calendario",
            on_click=lambda e: self._abrir_selector_fecha(),
        )

        date_bar = ft.Container(
            bgcolor=SURFACE_WHITE,
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=12,
            padding=ft.Padding(left=6, right=6, top=4, bottom=4),
            content=ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_LEFT,
                        icon_size=20,
                        icon_color=TEXT_MUTED,
                        tooltip="Día Anterior",
                        on_click=lambda e: self._cambiar_dia(-1),
                    ),
                    btn_fecha_central,
                    ft.IconButton(
                        icon=ft.Icons.CHEVRON_RIGHT,
                        icon_size=20,
                        icon_color=TEXT_MUTED,
                        tooltip="Día Siguiente",
                        on_click=lambda e: self._cambiar_dia(1),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.EVENT,
                        icon_size=20,
                        icon_color=PRIMARY,
                        tooltip="Elegir Fecha en Calendario",
                        on_click=lambda e: self._abrir_selector_fecha(),
                    ),
                    ft.TextButton(
                        "Hoy",
                        style=ft.ButtonStyle(
                            color=PRIMARY,
                            padding=ft.Padding(left=8, right=8, top=0, bottom=0),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        on_click=lambda e: self._ir_a_hoy(),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

        date_bar_wrapper = ft.Container(
            padding=ft.Padding(left=16, right=16, top=2, bottom=4),
            content=date_bar,
        )

        # 4. Estadísticas del Día (KPIs)
        self.kpi_presentes_text = ft.Text("", weight=ft.FontWeight.BOLD, size=14, color=ATTENDANCE_P_TEXT)
        self.kpi_ausentes_text = ft.Text("", weight=ft.FontWeight.BOLD, size=14, color=ATTENDANCE_A_TEXT)
        self.kpi_tardes_text = ft.Text("", weight=ft.FontWeight.BOLD, size=14, color=ATTENDANCE_T_TEXT)
        self.kpi_justificados_text = ft.Text("", weight=ft.FontWeight.BOLD, size=14, color=ATTENDANCE_J_TEXT)
        self.kpi_porc_text = ft.Text("", weight=ft.FontWeight.BOLD, size=14, color="#374151")

        def make_kpi(label, text_ctrl, color_bg, color_fg):
            return ft.Container(
                content=ft.Column(
                    [
                        text_ctrl,
                        ft.Text(label, size=10, color=color_fg, weight=ft.FontWeight.W_500),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=1,
                ),
                bgcolor=color_bg,
                border_radius=8,
                padding=ft.Padding(left=6, right=6, top=5, bottom=5),
                expand=True,
                alignment=ft.Alignment.CENTER,
            )

        kpi_row = ft.Container(
            padding=ft.Padding(left=16, right=16, top=2, bottom=4),
            content=ft.Row(
                [
                    make_kpi("Presentes", self.kpi_presentes_text, ATTENDANCE_P_BG, ATTENDANCE_P_TEXT),
                    make_kpi("Ausentes", self.kpi_ausentes_text, ATTENDANCE_A_BG, ATTENDANCE_A_TEXT),
                    make_kpi("Tardes", self.kpi_tardes_text, ATTENDANCE_T_BG, ATTENDANCE_T_TEXT),
                    make_kpi("Justificados", self.kpi_justificados_text, ATTENDANCE_J_BG, ATTENDANCE_J_TEXT),
                    make_kpi("% Asist.", self.kpi_porc_text, "#F3F4F6", "#374151"),
                ],
                spacing=6,
            ),
        )
        self._actualizar_kpis_ui(fecha_actual, colegio, curso)

        # 5. Barra de Acciones de Asistencia
        actions_bar = ft.Container(
            padding=ft.Padding(left=16, right=16, top=2, bottom=6),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.OutlinedButton(
                        "Todos Presentes",
                        icon=ft.Icons.DONE_ALL,
                        height=34,
                        style=ft.ButtonStyle(
                            color=PRIMARY,
                            side=ft.BorderSide(1, PRIMARY),
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.Padding(left=10, right=10, top=0, bottom=0),
                        ),
                        on_click=lambda e: self._marcar_todos_presentes(),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.SHARE,
                        icon_size=18,
                        icon_color=TEXT_MUTED,
                        tooltip="Exportar Asistencias (PDF/CSV/TXT)",
                        on_click=lambda e: self._abrir_modal_exportar(),
                    ),
                ],
            ),
        )

        # 6. Lista de Alumnos para toma de asistencia
        lista_alumnos = self._construir_lista_alumnos(alumnos, asistencias_dia, fecha_actual)

        # 7. Dock inferior de marcado rápido (Bottom Dock P, A, T, J)
        marking_dock = self._construir_dock_marcado(alumnos)

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                module_tabs,
                date_bar_wrapper,
                kpi_row,
                actions_bar,
                ft.Container(
                    expand=True,
                    padding=ft.Padding(left=16, right=16, top=4, bottom=6),
                    content=lista_alumnos,
                ),
                marking_dock,
            ],
        )

    def _actualizar_kpis_ui(self, fecha: str | None = None, colegio: str | None = None, curso: str | None = None):
        fecha_act = fecha or self.state.asistencia_fecha
        col = colegio or self.state.selected_colegio or ""
        cur = curso or self.state.selected_curso or ""
        resumen_dia = self.state.get_resumen_asistencia_dia(fecha_act, col, cur)
        self.kpi_presentes_text.value = str(resumen_dia["presentes"])
        self.kpi_ausentes_text.value = str(resumen_dia["ausentes"])
        self.kpi_tardes_text.value = str(resumen_dia["tardes"])
        self.kpi_justificados_text.value = str(resumen_dia["justificados"])
        porc = resumen_dia.get("porcentaje_asistencia", 0.0)
        self.kpi_porc_text.value = f"{porc}%"

    def _actualizar_boton_guardar(self):
        if hasattr(self, "btn_guardar"):
            self.btn_guardar.style = ft.ButtonStyle(
                bgcolor=WARNING_AMBER if self.state.has_unsaved_asistencias else PRIMARY,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(left=12, right=12, top=0, bottom=0),
            )

    def _construir_dock_marcado(self, alumnos: dict) -> ft.Control:
        """Construye la barra flotante anclada al pie con 4 botones grandes para marcado táctil rápido."""
        alumnos_keys = list(alumnos.keys())

        def aplicar_estado_dock(estado_codigo: str):
            if not self.active_student_id and alumnos_keys:
                self.active_student_id = alumnos_keys[0]

            if not self.active_student_id:
                return

            current_id = self.active_student_id
            self._cambiar_estado_alumno(current_id, estado_codigo)

            # Saltar automáticamente al siguiente alumno en la lista
            if current_id in alumnos_keys:
                idx = alumnos_keys.index(current_id)
                next_idx = (idx + 1) % len(alumnos_keys)
                self.active_student_id = alumnos_keys[next_idx]
                self._actualizar_seleccion_tarjetas_ui()
                self.app_page.update()

        dock_buttons = [
            ft.Container(
                expand=True,
                height=44,
                bgcolor=ATTENDANCE_P_BG,
                border=ft.Border.all(1.5, ATTENDANCE_P_SOLID),
                border_radius=10,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda e: aplicar_estado_dock(ESTADO_PRESENTE),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                    tight=True,
                    controls=[
                        ft.Text("P", weight=ft.FontWeight.BOLD, size=15, color=ATTENDANCE_P_TEXT),
                        ft.Text("Presente", weight=ft.FontWeight.W_500, size=11, color=ATTENDANCE_P_TEXT),
                    ],
                ),
            ),
            ft.Container(
                expand=True,
                height=44,
                bgcolor=ATTENDANCE_A_BG,
                border=ft.Border.all(1.5, ATTENDANCE_A_SOLID),
                border_radius=10,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda e: aplicar_estado_dock(ESTADO_AUSENTE),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                    tight=True,
                    controls=[
                        ft.Text("A", weight=ft.FontWeight.BOLD, size=15, color=ATTENDANCE_A_TEXT),
                        ft.Text("Ausente", weight=ft.FontWeight.W_500, size=11, color=ATTENDANCE_A_TEXT),
                    ],
                ),
            ),
            ft.Container(
                expand=True,
                height=44,
                bgcolor=ATTENDANCE_T_BG,
                border=ft.Border.all(1.5, ATTENDANCE_T_SOLID),
                border_radius=10,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda e: aplicar_estado_dock(ESTADO_TARDE),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                    tight=True,
                    controls=[
                        ft.Text("T", weight=ft.FontWeight.BOLD, size=15, color=ATTENDANCE_T_TEXT),
                        ft.Text("Tarde", weight=ft.FontWeight.W_500, size=11, color=ATTENDANCE_T_TEXT),
                    ],
                ),
            ),
            ft.Container(
                expand=True,
                height=44,
                bgcolor=ATTENDANCE_J_BG,
                border=ft.Border.all(1.5, ATTENDANCE_J_SOLID),
                border_radius=10,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda e: aplicar_estado_dock(ESTADO_JUSTIFICADO),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                    tight=True,
                    controls=[
                        ft.Text("J", weight=ft.FontWeight.BOLD, size=15, color=ATTENDANCE_J_TEXT),
                        ft.Text("Justif.", weight=ft.FontWeight.W_500, size=11, color=ATTENDANCE_J_TEXT),
                    ],
                ),
            ),
        ]

        active_nombre = alumnos.get(self.active_student_id, {}).get("nombre", "") if self.active_student_id else ""

        self.dock_label_active = ft.Text(
            f"Alumno #{self.active_student_id}: {active_nombre}" if self.active_student_id else "Marcado rápido",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=PRIMARY,
            no_wrap=True,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        return ft.Container(
            bgcolor=SURFACE_WHITE,
            border=ft.Border.only(top=ft.BorderSide(1, BORDER_COLOR)),
            padding=ft.Padding(left=16, right=16, top=8, bottom=14),
            content=ft.Column(
                tight=True,
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("DOCK DE MARCADO RÁPIDO", size=10, weight=ft.FontWeight.BOLD, color=TEXT_SUBTLE),
                            self.dock_label_active,
                        ],
                    ),
                    ft.Row(spacing=6, controls=dock_buttons),
                ],
            ),
        )

    def _actualizar_seleccion_tarjetas_ui(self):
        """Actualiza el borde de la tarjeta del alumno seleccionado activamente."""
        if hasattr(self, "tarjetas_alumnos"):
            for sid, card_container in self.tarjetas_alumnos.items():
                is_sel = (str(sid) == str(self.active_student_id))
                card_container.border = ft.Border.all(2, PRIMARY if is_sel else BORDER_COLOR)
        if hasattr(self, "dock_label_active") and self.active_student_id:
            alumnos = self.state.get_alumnos()
            nombre = alumnos.get(str(self.active_student_id), {}).get("nombre", "")
            self.dock_label_active.value = f"Alumno #{self.active_student_id}: {nombre}"

    def _construir_lista_alumnos(self, alumnos: dict, asistencias_dia: dict, fecha: str) -> ft.Control:
        self.alumnos_botones = {}
        self.tarjetas_alumnos = {}

        if not alumnos:
            return ft.Container(
                content=ft.Column(
                    [
                        ft.Container(
                            width=56,
                            height=56,
                            bgcolor=PRIMARY_LIGHT,
                            border_radius=16,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.GROUP_OUTLINED, size=28, color=PRIMARY),
                        ),
                        ft.Text("No hay alumnos en este curso", size=15, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                        ft.Text("Agrega alumnos desde la pestaña 'Notas' para tomar asistencia.", size=12, color=TEXT_MUTED),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                ),
                alignment=ft.Alignment.CENTER,
                padding=30,
            )

        items = []
        for idx, (id_al, al_data) in enumerate(alumnos.items()):
            nombre_al = al_data.get("nombre", "Sin nombre")
            estado_actual = asistencias_dia.get(str(id_al))
            bg_avatar, txt_avatar = get_avatar_palette(idx)
            initials = extract_initials(nombre_al)

            # Selector de estado táctil con 4 botones: P, A, T, J
            def make_state_btn(estado_code, label, color_hex, student_id):
                seleccionado = (estado_actual == estado_code)
                txt_widget = ft.Text(
                    label,
                    weight=ft.FontWeight.BOLD if seleccionado else ft.FontWeight.NORMAL,
                    color=ft.Colors.WHITE if seleccionado else color_hex,
                    size=13,
                )
                container = ft.Container(
                    content=txt_widget,
                    bgcolor=color_hex if seleccionado else ft.Colors.TRANSPARENT,
                    border=ft.Border.all(1.5, color_hex),
                    border_radius=8,
                    width=38,
                    height=36,
                    alignment=ft.Alignment.CENTER,
                    on_click=lambda e, st=estado_code, sid=student_id: self._on_btn_click(sid, st),
                )
                return container, txt_widget, color_hex

            btn_p, txt_p, col_p = make_state_btn(ESTADO_PRESENTE, "P", ATTENDANCE_P_SOLID, str(id_al))
            btn_a, txt_a, col_a = make_state_btn(ESTADO_AUSENTE, "A", ATTENDANCE_A_SOLID, str(id_al))
            btn_t, txt_t, col_t = make_state_btn(ESTADO_TARDE, "T", ATTENDANCE_T_SOLID, str(id_al))
            btn_j, txt_j, col_j = make_state_btn(ESTADO_JUSTIFICADO, "J", ATTENDANCE_J_SOLID, str(id_al))

            self.alumnos_botones[str(id_al)] = {
                ESTADO_PRESENTE: (btn_p, txt_p, col_p),
                ESTADO_AUSENTE: (btn_a, txt_a, col_a),
                ESTADO_TARDE: (btn_t, txt_t, col_t),
                ESTADO_JUSTIFICADO: (btn_j, txt_j, col_j),
            }

            is_active_card = (str(id_al) == str(self.active_student_id))

            card_container = ft.Container(
                bgcolor=SURFACE_WHITE,
                border=ft.Border.all(2 if is_active_card else 1, PRIMARY if is_active_card else BORDER_COLOR),
                border_radius=14,
                padding=ft.Padding(left=12, right=10, top=8, bottom=8),
                ink=True,
                on_click=lambda e, sid=str(id_al): self._seleccionar_alumno_activo(sid),
                content=ft.Row(
                    [
                        ft.Container(
                            width=36,
                            height=36,
                            bgcolor=bg_avatar,
                            border_radius=18,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text(initials, size=11, weight=ft.FontWeight.BOLD, color=txt_avatar),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=1,
                            controls=[
                                ft.Text(nombre_al, size=13, weight=ft.FontWeight.BOLD, color=TEXT_MAIN, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(f"N° {id_al}", size=11, color=TEXT_MUTED),
                            ],
                        ),
                        ft.Row([btn_p, btn_a, btn_t, btn_j], spacing=4),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
            self.tarjetas_alumnos[str(id_al)] = card_container
            items.append(card_container)

        return ft.ListView(controls=items, expand=True, spacing=6)

    def _seleccionar_alumno_activo(self, sid: str):
        self.active_student_id = sid
        self._actualizar_seleccion_tarjetas_ui()
        self.app_page.update()

    def _on_btn_click(self, sid: str, estado_code: str):
        self.active_student_id = sid
        self._actualizar_seleccion_tarjetas_ui()
        self._cambiar_estado_alumno(sid, estado_code)

    def _actualizar_botones_alumno_ui(self, id_al: str, estado_seleccionado: str | None):
        """Actualiza visualmente los 4 botones de un alumno in-place sin reconstruir la lista ni resetear el scroll."""
        if not hasattr(self, "alumnos_botones") or id_al not in self.alumnos_botones:
            return
        botones_dict = self.alumnos_botones[id_al]
        for est_code, (btn_c, txt_c, color_hex) in botones_dict.items():
            sel = (estado_seleccionado == est_code)
            btn_c.bgcolor = color_hex if sel else ft.Colors.TRANSPARENT
            txt_c.color = ft.Colors.WHITE if sel else color_hex
            txt_c.weight = ft.FontWeight.BOLD if sel else ft.FontWeight.NORMAL

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

        self._actualizar_botones_alumno_ui(str(id_al), nuevo_estado or None)
        self._actualizar_kpis_ui()
        self._actualizar_boton_guardar()
        self.app_page.update()

    def _marcar_todos_presentes(self):
        fecha = self.state.asistencia_fecha
        self.state.set_all_asistencias_dia(fecha, ESTADO_PRESENTE)
        if hasattr(self, "alumnos_botones"):
            for id_al in self.alumnos_botones:
                self._actualizar_botones_alumno_ui(id_al, ESTADO_PRESENTE)
            self._actualizar_kpis_ui()
            self._actualizar_boton_guardar()
        else:
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

    def _abrir_selector_fecha(self):
        fechas_reg = self.state.get_fechas_asistencias()
        dlg = DatePickerDialog(
            fecha_actual_iso=self.state.asistencia_fecha,
            fechas_con_asistencia=fechas_reg,
            on_date_selected=self._seleccionar_fecha_personalizada,
            page=self.app_page,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _seleccionar_fecha_personalizada(self, nueva_fecha_iso: str):
        self.state.asistencia_fecha = nueva_fecha_iso
        self._build_ui()
        self.app_page.update()

    def _cambiar_pestana(self, selected_set):
        if "notas" in selected_set:
            self.state.flush_auto_save()
            self.on_navigate("notas")

    def _accion_volver(self):
        self.state.flush_auto_save()
        self.on_navigate("cursos")

    def _abrir_estadisticas_curso(self):
        self.state.flush_auto_save()
        self.state.origen_pantalla = "asistencias"
        self.state.estadisticas_nivel = "curso"
        self.on_navigate("estadisticas")


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
            self.state.load_data()
            self.on_navigate(destino)

        dlg = ft.AlertDialog(
            title=ft.Text("Asistencias sin guardar", weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            content=ft.Text("Tienes asistencias modificadas sin guardar.\n¿Deseas guardarlas antes de continuar?", color=TEXT_MUTED),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    style=ft.ButtonStyle(color=TEXT_MUTED, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: cerrar_dialogo(),
                ),
                ft.TextButton(
                    "Descartar",
                    style=ft.ButtonStyle(color=ft.Colors.RED_600, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: salir_sin_guardar(),
                ),
                ft.FilledButton(
                    "Guardar y Salir",
                    style=ft.ButtonStyle(bgcolor=PRIMARY, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=lambda e: guardar_y_salir(),
                ),
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

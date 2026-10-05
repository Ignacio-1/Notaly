"""
Vista de Planilla de Notas: Interfaz táctil móvil responsive basada en tarjetas
expandibles de alumnos, píldoras de trimestres (.grade-pill) y teclado numérico flotante (.key-button).
Cumple con las especificaciones de diseño Slate 50 / Indigo 600 y Material Design 3.
"""

import math
import flet as ft
from mobile.state import AppState
from mobile.components.grade_editor import GradeEditorDialog
from mobile.components.student_dialog import (
    ConfirmDeleteDialog,
    CustomizeColumnsDialog,
    StudentFormDialog,
)
from mobile.components.export_dialog import ExportDialog
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
    PRIMARY_HOVER,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUBTLE,
    WARNING_AMBER,
    GRADE_PASS_BG,
    GRADE_PASS_TEXT,
    GRADE_FAIL_BG,
    GRADE_FAIL_TEXT,
    GRADE_EMPTY_BG,
    GRADE_EMPTY_TEXT,
    get_grade_tone,
    get_avatar_palette,
    extract_initials,
)
from core.constants import (
    NOMBRES_TRIMESTRES,
    NUM_PRINCIPALES,
    NUM_EXTRAS,
    UMBRAL_RECUPERATORIO,
    NOTA_MINIMA_APROBACION,
    separar_nombre_completo,
)
from core.calculos import procesar_calificaciones_alumno


def build_grade_pill(label: str, value: float | int | str | None) -> ft.Container:
    """Construye una píldora visual de calificación para un trimestre (.grade-pill)."""
    if value is None or value == "" or value == "--":
        val_str = "--"
    else:
        try:
            val_str = str(int(math.floor(float(str(value).replace(",", ".")) + 0.5)))
        except (ValueError, TypeError):
            val_str = str(value)
    bg, fg = get_grade_tone(value)
    return ft.Container(
        data="grade-pill",
        bgcolor=bg,
        border_radius=6,
        padding=ft.Padding(left=6, right=6, top=2, bottom=2),
        content=ft.Row(
            spacing=2,
            tight=True,
            controls=[
                ft.Text(f"{label}:", size=10, color=TEXT_MUTED),
                ft.Text(val_str, size=11, weight=ft.FontWeight.BOLD, color=fg),
            ],
        ),
    )


def build_key_button(
    text: str | None = None,
    icon: str | None = None,
    on_click: callable = None,
    is_primary: bool = False,
    expand: bool = True,
    height: int = 42,
) -> ft.Container:
    """Construye un botón táctil para el teclado numérico anclado al pie (.key-button)."""
    if is_primary:
        bg = PRIMARY
        fg = ft.Colors.WHITE
        border = None
    else:
        bg = "#F8FAFC"
        fg = TEXT_MAIN
        border = ft.Border.all(1, BORDER_COLOR)

    if icon:
        content = ft.Icon(icon, size=16, color=TEXT_MUTED if not is_primary else ft.Colors.WHITE)
    else:
        content = ft.Text(text or "", size=14 if len(text or "") <= 2 else 12, weight=ft.FontWeight.BOLD, color=fg)

    return ft.Container(
        data="key-button",
        expand=expand,
        height=height,
        bgcolor=bg,
        border=border,
        border_radius=10,
        alignment=ft.Alignment.CENTER,
        ink=True,
        on_click=on_click,
        content=content,
    )


class NotasView(ft.Container):
    def __init__(self, state: AppState, page: ft.Page, on_navigate: callable):
        super().__init__(expand=True, bgcolor=BG_PAGE)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = 0

        # Estado visual interno
        self.expanded_student_id: str | None = None
        self.active_grade_index: int = 0  # 0 a 4 (P0, P1, P2, E0, R0)
        self.alumnos_celdas: dict = {}
        self.tarjetas_alumnos: dict = {}
        self.name_drafts: dict = {}
        self.pills_alumnos: dict = {}
        self.promedio_anual_labels: dict = {}
        self.slots_controls_by_student: dict = {}
        self.expanded_containers: dict[str, ft.Container] = {}
        self.chevron_icons: dict[str, ft.Icon] = {}
        self.lista_tarjetas_listview: ft.ListView | None = None

        self.paneles_anuales: dict[str, dict] = {}
        self.header_pills_containers: dict[str, ft.Container] = {}
        self.dock_container: ft.Container | None = None

        self.dock_label_active: ft.Text | None = None
        self.dock_badge_trimestre: ft.Text | None = None
        self.top_trimester_tabs: list[ft.Container] = []
        self.local_trim_buttons: dict[str, list[ft.Container]] = {}
        self.btn_guardar: ft.FilledButton | None = None

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

    def _color_por_nota(self, nota: int | float | None) -> tuple[str, str]:
        """Retorna (color_fondo, color_texto) según la calificación."""
        return get_grade_tone(nota)

    def _get_slot_meta(self, slot_idx: int, nombres_cols: list[str]) -> tuple[str, int, str, str]:
        """Retorna (tipo, sub_index, nombre_columna, cell_key)."""
        if slot_idx == 0:
            return "P", 0, nombres_cols[0] if len(nombres_cols) > 0 else "P1", "P0"
        elif slot_idx == 1:
            return "P", 1, nombres_cols[1] if len(nombres_cols) > 1 else "P2", "P1"
        elif slot_idx == 2:
            return "P", 2, nombres_cols[2] if len(nombres_cols) > 2 else "P3", "P2"
        elif slot_idx == 3:
            return "E", 0, nombres_cols[3] if len(nombres_cols) > 3 else "Extra", "E0"
        else:
            return "R", 0, "Recup", "R0"

    def _build_ui(self):
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso)
        alumnos_keys = list(alumnos.keys())

        # Si no hay alumno expandido, seleccionar el alumno en estado o el primero de la lista
        if self.state.selected_alumno_id and str(self.state.selected_alumno_id) in alumnos:
            self.expanded_student_id = str(self.state.selected_alumno_id)
        elif self.expanded_student_id not in alumnos:
            self.expanded_student_id = alumnos_keys[0] if alumnos_keys else None

        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        # 1. Header principal con botón de retroceso y títulos
        header = build_app_header(
            eyebrow=colegio,
            title=curso,
            on_back=self._accion_volver,
            status_indicator=self.save_indicator,
        )

        # 2. Selector de módulo (Notas / Asistencias)
        module_tabs = ft.Container(
            padding=ft.Padding(left=16, right=16, top=6, bottom=4),
            content=build_module_tabs(active_tab="notas", on_change=lambda dest: self._cambiar_pestana([dest])),
        )

        # 3. Selector superior de trimestre (1°, 2°, 3°, Anual)
        self.top_trimester_tabs = []
        labels = ["1° Trim", "2° Trim", "3° Trim", "Anual"]
        for idx, lbl in enumerate(labels):
            is_active = (self.state.active_trimestre == idx)
            self.top_trimester_tabs.append(
                ft.Container(
                    expand=True,
                    height=32,
                    border_radius=8,
                    bgcolor=SURFACE_WHITE if is_active else ft.Colors.TRANSPARENT,
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda e, t_idx=idx: self._seleccionar_trimestre(t_idx),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=4,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.ANALYTICS, size=13, color=PRIMARY if is_active else TEXT_MUTED)
                            if idx == 3
                            else ft.Container(),
                            ft.Text(
                                lbl,
                                size=11,
                                weight=ft.FontWeight.BOLD,
                                color=PRIMARY if is_active else TEXT_MUTED,
                            ),
                        ],
                    ),
                )
            )

        trim_selector_bar = ft.Container(
            padding=ft.Padding(left=16, right=16, top=2, bottom=4),
            content=ft.Container(
                bgcolor="#F1F5F9",
                border_radius=10,
                padding=2,
                content=ft.Row(spacing=2, controls=self.top_trimester_tabs),
            ),
        )

        # 4. Barra de acciones rápidas (+ Alumno, herramientas)
        actions_bar = ft.Container(
            padding=ft.Padding(left=16, right=16, top=2, bottom=6),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.OutlinedButton(
                        "+ Alumno",
                        icon=ft.Icons.PERSON_ADD,
                        height=34,
                        style=ft.ButtonStyle(
                            color=PRIMARY,
                            side=ft.BorderSide(1, PRIMARY),
                            shape=ft.RoundedRectangleBorder(radius=8),
                            padding=ft.Padding(left=10, right=10, top=0, bottom=0),
                        ),
                        on_click=lambda e: self._abrir_modal_agregar_alumno(),
                    ),
                    ft.Row(
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.TUNE,
                                icon_size=18,
                                icon_color=TEXT_MUTED,
                                tooltip="Personalizar Columnas",
                                on_click=lambda e: self._abrir_modal_columnas(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.SORT_BY_ALPHA,
                                icon_size=18,
                                icon_color=TEXT_MUTED,
                                tooltip="Ordenar Alumnos (A-Z)",
                                on_click=lambda e: self._ordenar_alumnos_az(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.SHARE,
                                icon_size=18,
                                icon_color=TEXT_MUTED,
                                tooltip="Exportar Planilla (PDF/CSV/TXT)",
                                on_click=lambda e: self._abrir_modal_exportar(),
                            ),
                        ],
                    ),
                ],
            ),
        )

        # 5. Lista de tarjetas expandibles de alumnos
        lista_tarjetas = self._construir_lista_tarjetas(alumnos, trim_idx, nombres_cols)

        # 6. Teclado Flotante Inferior anclado al pie (Dock Numérico)
        self.dock_container = self._construir_dock_teclado(alumnos, trim_idx, nombres_cols)
        if self.state.active_trimestre == 3:
            self.dock_container.visible = False

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                module_tabs,
                trim_selector_bar,
                actions_bar,
                ft.Container(
                    expand=True,
                    padding=ft.Padding(left=16, right=16, top=2, bottom=4),
                    content=lista_tarjetas,
                ),
                self.dock_container,
            ],
        )

    def _actualizar_boton_guardar(self):
        if self.btn_guardar:
            self.btn_guardar.style = ft.ButtonStyle(
                bgcolor=WARNING_AMBER if self.state.has_unsaved_changes else PRIMARY,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding(left=12, right=12, top=0, bottom=0),
            )

    def _construir_panel_anual_alumno(self, id_str: str, calcs: dict) -> tuple[ft.Container, dict]:
        """Construye el panel informativo de solo lectura para la pestaña 'Anual'."""
        t1 = calcs["notas_finales_redondeadas"][0]
        t2 = calcs["notas_finales_redondeadas"][1]
        t3 = calcs["notas_finales_redondeadas"][2]
        total = calcs["nota_final_total_redondeada"]

        promedios_validos = [t for t in [t1, t2, t3] if t is not None]
        promedio_crudo_total = (sum(promedios_validos) / len(promedios_validos)) if promedios_validos else None

        if promedio_crudo_total is not None:
            if promedio_crudo_total >= 5.50:
                estado_str = "Aprobado"
                estado_bg = GRADE_PASS_BG
                estado_fg = GRADE_PASS_TEXT
                estado_icon = ft.Icons.CHECK_CIRCLE_OUTLINE
            else:
                estado_str = "Desaprobado"
                estado_bg = GRADE_FAIL_BG
                estado_fg = GRADE_FAIL_TEXT
                estado_icon = ft.Icons.CANCEL_OUTLINED
        else:
            estado_str = "--"
            estado_bg = GRADE_EMPTY_BG
            estado_fg = GRADE_EMPTY_TEXT
            estado_icon = ft.Icons.REMOVE_CIRCLE_OUTLINE

        # 1. Bloque T1
        t1_str = str(t1) if t1 is not None else "--"
        bg1, fg1 = get_grade_tone(t1)
        t1_text = ft.Text(t1_str, size=13, weight=ft.FontWeight.BOLD, color=fg1)
        t1_cont = ft.Container(
            bgcolor=bg1,
            border_radius=6,
            padding=ft.Padding(left=8, right=8, top=2, bottom=2),
            alignment=ft.Alignment.CENTER,
            content=t1_text,
        )
        box_t1 = ft.Container(
            expand=True,
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=8,
            padding=ft.Padding(left=6, right=6, top=6, bottom=6),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
                controls=[
                    ft.Text("1° Trim (T1)", size=10, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
                    t1_cont,
                ],
            ),
        )

        # 2. Bloque T2
        t2_str = str(t2) if t2 is not None else "--"
        bg2, fg2 = get_grade_tone(t2)
        t2_text = ft.Text(t2_str, size=13, weight=ft.FontWeight.BOLD, color=fg2)
        t2_cont = ft.Container(
            bgcolor=bg2,
            border_radius=6,
            padding=ft.Padding(left=8, right=8, top=2, bottom=2),
            alignment=ft.Alignment.CENTER,
            content=t2_text,
        )
        box_t2 = ft.Container(
            expand=True,
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=8,
            padding=ft.Padding(left=6, right=6, top=6, bottom=6),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
                controls=[
                    ft.Text("2° Trim (T2)", size=10, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
                    t2_cont,
                ],
            ),
        )

        # 3. Bloque T3
        t3_str = str(t3) if t3 is not None else "--"
        bg3, fg3 = get_grade_tone(t3)
        t3_text = ft.Text(t3_str, size=13, weight=ft.FontWeight.BOLD, color=fg3)
        t3_cont = ft.Container(
            bgcolor=bg3,
            border_radius=6,
            padding=ft.Padding(left=8, right=8, top=2, bottom=2),
            alignment=ft.Alignment.CENTER,
            content=t3_text,
        )
        box_t3 = ft.Container(
            expand=True,
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=8,
            padding=ft.Padding(left=6, right=6, top=6, bottom=6),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=3,
                controls=[
                    ft.Text("3° Trim (T3)", size=10, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
                    t3_cont,
                ],
            ),
        )

        # 4. Fila Resumen Anual (Calificación Anual / Promedio Final y Estado)
        total_str = str(total) if total is not None else "--"
        bg_tot, fg_tot = get_grade_tone(total)
        promedio_anual_text = ft.Text(total_str, size=13, weight=ft.FontWeight.BOLD, color=fg_tot)
        promedio_anual_cont = ft.Container(
            bgcolor=bg_tot,
            border_radius=6,
            padding=ft.Padding(left=8, right=8, top=2, bottom=2),
            alignment=ft.Alignment.CENTER,
            content=promedio_anual_text,
        )

        estado_icon_widget = ft.Icon(estado_icon, size=14, color=estado_fg)
        estado_text_widget = ft.Text(estado_str, size=11, weight=ft.FontWeight.BOLD, color=estado_fg)
        estado_badge = ft.Container(
            bgcolor=estado_bg,
            border_radius=6,
            padding=ft.Padding(left=8, right=8, top=3, bottom=3),
            content=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    estado_icon_widget,
                    estado_text_widget,
                ],
            ),
        )

        resumen_anual_row = ft.Container(
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, BORDER_COLOR),
            border_radius=8,
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=6,
                        tight=True,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("Calificación Anual:", size=11, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
                            promedio_anual_cont,
                        ],
                    ),
                    estado_badge,
                ],
            ),
        )

        panel_container = ft.Container(
            visible=(self.state.active_trimestre == 3),
            padding=ft.Padding(left=12, right=12, top=6, bottom=12),
            border=ft.Border.only(top=ft.BorderSide(1, "#F1F5F9")),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(spacing=6, controls=[box_t1, box_t2, box_t3]),
                    resumen_anual_row,
                ],
            ),
        )

        ref_dict = {
            "container": panel_container,
            "t1_text": t1_text,
            "t1_container": t1_cont,
            "t2_text": t2_text,
            "t2_container": t2_cont,
            "t3_text": t3_text,
            "t3_container": t3_cont,
            "promedio_anual_text": promedio_anual_text,
            "promedio_anual_container": promedio_anual_cont,
            "estado_text": estado_text_widget,
            "estado_badge": estado_badge,
            "estado_icon": estado_icon_widget,
        }

        return panel_container, ref_dict

    def _actualizar_panel_anual_ui(self, id_al: str):
        """Actualiza in-place los datos y estado del panel anual informativo del alumno."""
        id_str = str(id_al)
        if not hasattr(self, "paneles_anuales") or id_str not in self.paneles_anuales:
            return

        ref_anual = self.paneles_anuales[id_str]
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso)
        al_data = alumnos.get(id_str)
        if not al_data:
            return

        trimestres = al_data.get("trimestres", {})
        calcs = procesar_calificaciones_alumno(trimestres)
        t1 = calcs["notas_finales_redondeadas"][0]
        t2 = calcs["notas_finales_redondeadas"][1]
        t3 = calcs["notas_finales_redondeadas"][2]
        total = calcs["nota_final_total_redondeada"]

        promedios_validos = [t for t in [t1, t2, t3] if t is not None]
        promedio_crudo_total = (sum(promedios_validos) / len(promedios_validos)) if promedios_validos else None

        if promedio_crudo_total is not None:
            if promedio_crudo_total >= 5.50:
                estado_str = "Aprobado"
                estado_bg = GRADE_PASS_BG
                estado_fg = GRADE_PASS_TEXT
                estado_icon = ft.Icons.CHECK_CIRCLE_OUTLINE
            else:
                estado_str = "Desaprobado"
                estado_bg = GRADE_FAIL_BG
                estado_fg = GRADE_FAIL_TEXT
                estado_icon = ft.Icons.CANCEL_OUTLINED
        else:
            estado_str = "--"
            estado_bg = GRADE_EMPTY_BG
            estado_fg = GRADE_EMPTY_TEXT
            estado_icon = ft.Icons.REMOVE_CIRCLE_OUTLINE

        # Actualizar T1
        t1_str = str(t1) if t1 is not None else "--"
        bg1, fg1 = get_grade_tone(t1)
        ref_anual["t1_text"].value = t1_str
        ref_anual["t1_text"].color = fg1
        ref_anual["t1_container"].bgcolor = bg1

        # Actualizar T2
        t2_str = str(t2) if t2 is not None else "--"
        bg2, fg2 = get_grade_tone(t2)
        ref_anual["t2_text"].value = t2_str
        ref_anual["t2_text"].color = fg2
        ref_anual["t2_container"].bgcolor = bg2

        # Actualizar T3
        t3_str = str(t3) if t3 is not None else "--"
        bg3, fg3 = get_grade_tone(t3)
        ref_anual["t3_text"].value = t3_str
        ref_anual["t3_text"].color = fg3
        ref_anual["t3_container"].bgcolor = bg3

        # Actualizar Promedio Final / Calificación Anual
        total_str = str(total) if total is not None else "--"
        bg_tot, fg_tot = get_grade_tone(total)
        ref_anual["promedio_anual_text"].value = total_str
        ref_anual["promedio_anual_text"].color = fg_tot
        ref_anual["promedio_anual_container"].bgcolor = bg_tot

        # Actualizar Estado
        ref_anual["estado_text"].value = estado_str
        ref_anual["estado_text"].color = estado_fg
        ref_anual["estado_badge"].bgcolor = estado_bg
        if "estado_icon" in ref_anual and ref_anual["estado_icon"]:
            ref_anual["estado_icon"].name = estado_icon
            ref_anual["estado_icon"].color = estado_fg

    def _seleccionar_trimestre(self, trim_idx: int):
        self.state.active_trimestre = trim_idx
        self.active_grade_index = 0

        # Si no tenemos tarjetas montadas, construir UI
        if not hasattr(self, "tarjetas_alumnos") or not self.tarjetas_alumnos:
            self._build_ui()
            self.app_page.update()
            return

        # 1. Actualización quirúrgica in-place de las pestañas superiores
        if hasattr(self, "top_trimester_tabs"):
            for idx, tab in enumerate(self.top_trimester_tabs):
                is_act = (idx == trim_idx)
                tab.bgcolor = SURFACE_WHITE if is_act else ft.Colors.TRANSPARENT
                if hasattr(tab, "content") and hasattr(tab.content, "controls"):
                    controls = tab.content.controls
                    if len(controls) > 0 and isinstance(controls[0], ft.Icon):
                        controls[0].color = PRIMARY if is_act else TEXT_MUTED
                    if len(controls) > 1 and isinstance(controls[1], ft.Text):
                        controls[1].color = PRIMARY if is_act else TEXT_MUTED

        # Caso A: Conmutar a pestaña 'Anual' (vista informativa de solo lectura)
        if trim_idx >= 3:
            # Ocultar el dock numérico inferior (dock_container.visible = False)
            if hasattr(self, "dock_container") and self.dock_container:
                self.dock_container.visible = False

            # Conmutar cada tarjeta a vista anual informativa de solo lectura
            if hasattr(self, "tarjetas_alumnos"):
                for sid in self.tarjetas_alumnos:
                    if sid in self.paneles_anuales:
                        self.paneles_anuales[sid]["container"].visible = True
                    if sid in self.expanded_containers:
                        self.expanded_containers[sid].visible = False
                    if sid in self.chevron_icons:
                        self.chevron_icons[sid].visible = False
                    if sid in self.header_pills_containers:
                        self.header_pills_containers[sid].visible = False

                    self.tarjetas_alumnos[sid].border = ft.Border.all(1.5, BORDER_COLOR)
                    self.tarjetas_alumnos[sid].shadow = ft.BoxShadow(spread_radius=0, blur_radius=8, color=ft.Colors.TRANSPARENT)
                    self._actualizar_panel_anual_ui(sid)

            self.app_page.update()
            return

        # Caso B: Regreso a Trimestres (T1, T2, T3) (restablecer edición normal y dock reactivo)
        if hasattr(self, "dock_container") and self.dock_container:
            self.dock_container.visible = True

        if hasattr(self, "tarjetas_alumnos"):
            for sid in self.tarjetas_alumnos:
                if sid in self.paneles_anuales:
                    self.paneles_anuales[sid]["container"].visible = False
                if sid in self.header_pills_containers:
                    self.header_pills_containers[sid].visible = True
                if sid in self.chevron_icons:
                    self.chevron_icons[sid].visible = True

                is_exp = (str(self.expanded_student_id) == str(sid))
                if sid in self.expanded_containers:
                    self.expanded_containers[sid].visible = is_exp
                if sid in self.chevron_icons:
                    self.chevron_icons[sid].name = ft.Icons.EXPAND_LESS if is_exp else ft.Icons.EXPAND_MORE
                    self.chevron_icons[sid].color = PRIMARY if is_exp else TEXT_MUTED

                self.tarjetas_alumnos[sid].border = ft.Border.all(1.5, PRIMARY if is_exp else BORDER_COLOR)
                self.tarjetas_alumnos[sid].shadow = ft.BoxShadow(spread_radius=0, blur_radius=8, color="#0F172A0D" if is_exp else ft.Colors.TRANSPARENT)

        # 2. Actualización quirúrgica in-place de botones de trimestre locales en cada tarjeta
        if hasattr(self, "local_trim_buttons"):
            for sid, btns in self.local_trim_buttons.items():
                for t_idx, btn in enumerate(btns):
                    is_sel = (t_idx == trim_idx)
                    btn.bgcolor = SURFACE_WHITE if is_sel else ft.Colors.TRANSPARENT
                    if hasattr(btn, "content") and isinstance(btn.content, ft.Text):
                        btn.content.color = PRIMARY if is_sel else TEXT_MUTED

        # 3. Actualizar metadatos y etiquetas de columnas para los 5 slots por alumno
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        if hasattr(self, "slots_controls_by_student"):
            for sid, slots_map in self.slots_controls_by_student.items():
                for s_idx in range(5):
                    tipo, sub_i, col_name, cell_key = self._get_slot_meta(s_idx, nombres_cols)
                    if cell_key in slots_map:
                        ref = slots_map[cell_key]
                        ref["tipo"] = tipo
                        ref["sub_idx"] = sub_i
                        ref["col_name"] = col_name
                        if "label_widget" in ref and ref["label_widget"] is not None:
                            ref["label_widget"].value = col_name

        # 4. Actualizar las filas de calificaciones y cálculos de todos los alumnos
        if hasattr(self, "tarjetas_alumnos"):
            for sid in self.tarjetas_alumnos:
                self._actualizar_fila_alumno_ui(sid)

        # 5. Resaltar slots activos en el alumno expandido (si hay uno)
        if self.expanded_student_id:
            self._actualizar_slots_ui(self.expanded_student_id)

        # 6. Actualizar labels y badge del dock flotante inferior
        self._actualizar_dock_labels()

        # 7. Un solo update de la página sin tocar la estructura del ft.ListView -> SCROLL PRESERVADO
        self.app_page.update()

    def _construir_lista_tarjetas(self, alumnos: dict, trim_idx: int, nombres_cols: list[str]) -> ft.Control:
        self.alumnos_celdas = {}
        self.tarjetas_alumnos = {}
        self.pills_alumnos = {}
        self.promedio_anual_labels = {}
        self.slots_controls_by_student = {}
        self.expanded_containers = {}
        self.chevron_icons = {}
        self.local_trim_buttons = {}
        self.paneles_anuales = {}
        self.header_pills_containers = {}

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
                        ft.Text("Toca '+ Alumno' para cargar los estudiantes a la planilla.", size=12, color=TEXT_MUTED),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                ),
                alignment=ft.Alignment.CENTER,
                padding=30,
            )

        student_cards = []
        es_modo_anual = (self.state.active_trimestre == 3)

        for id_al, al_data in alumnos.items():
            id_str = str(id_al)
            nombre_al = al_data.get("nombre", "Sin nombre")
            ap_act, nom_act = separar_nombre_completo(nombre_al)

            # Inicializar drafts de edición de nombre
            if id_str not in self.name_drafts:
                self.name_drafts[id_str] = {"apellido": ap_act, "nombre": nom_act}

            trimestres = al_data.get("trimestres", {})
            calcs = procesar_calificaciones_alumno(trimestres)
            t1 = calcs["notas_finales_redondeadas"][0]
            t2 = calcs["notas_finales_redondeadas"][1]
            t3 = calcs["notas_finales_redondeadas"][2]
            total = calcs["nota_final_total_redondeada"]
            prom_crudo_red = calcs["promedios_crudos_redondeados"][trim_idx] if trim_idx < 3 else None
            nota_final_red = calcs["notas_finales_redondeadas"][trim_idx] if trim_idx < 3 else None

            # Panel anual informativo de solo lectura
            panel_anual, ref_anual = self._construir_panel_anual_alumno(id_str, calcs)
            self.paneles_anuales[id_str] = ref_anual

            # Píldoras de trimestres (.grade-pill)
            pill1 = build_grade_pill("1ºT", t1)
            pill2 = build_grade_pill("2ºT", t2)
            pill3 = build_grade_pill("3ºT", t3)
            self.pills_alumnos[id_str] = [pill1, pill2, pill3]

            is_open = (str(self.expanded_student_id) == id_str)

            # Avatar y colores
            num_id = int(id_str) if id_str.isdigit() else 0
            avatar_bg, avatar_fg = get_avatar_palette(num_id)
            iniciales = extract_initials(nombre_al)

            prom_anual_txt = ft.Text(
                f"Promedio anual: {total if total is not None else '--'}",
                size=11,
                color=TEXT_MUTED,
            )
            self.promedio_anual_labels[id_str] = prom_anual_txt

            # Celdas calculadas del trimestre activo
            bg_prom, fg_prom = self._color_por_nota(prom_crudo_red)
            prom_text = ft.Text(str(prom_crudo_red) if prom_crudo_red is not None else "-", weight=ft.FontWeight.BOLD, color=fg_prom, size=13)
            prom_container = ft.Container(
                content=prom_text,
                bgcolor=bg_prom,
                padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                border_radius=6,
                alignment=ft.Alignment.CENTER,
            )

            bg_fin, fg_fin = self._color_por_nota(nota_final_red)
            fin_text = ft.Text(str(nota_final_red) if nota_final_red is not None else "-", weight=ft.FontWeight.BOLD, color=fg_fin, size=13)
            fin_container = ft.Container(
                content=fin_text,
                bgcolor=bg_fin,
                padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                border_radius=6,
                alignment=ft.Alignment.CENTER,
            )

            # Construir slots de notas (5 slots: P0, P1, P2, E0, R0)
            slots_map = {}
            slots_widgets = []
            nombre_trim = NOMBRES_TRIMESTRES[trim_idx] if trim_idx < 3 else NOMBRES_TRIMESTRES[0]
            trim_data = trimestres.get(nombre_trim, {})
            principales = trim_data.get("principales", [None] * NUM_PRINCIPALES)
            extras = trim_data.get("extras", [None] * NUM_EXTRAS)
            recuperatorio = trim_data.get("recuperatorio")

            raw_valores = [
                principales[0] if len(principales) > 0 else None,
                principales[1] if len(principales) > 1 else None,
                principales[2] if len(principales) > 2 else None,
                extras[0] if len(extras) > 0 else None,
                recuperatorio,
            ]

            # Regla de corte: promedio < 5.50 habilita recuperación. Si >= 5.50 o no hay notas, bloqueado.
            prom_crudo_sin_red = calcs["promedios_crudos_sin_redondear"][trim_idx] if trim_idx < 3 else None
            habilita_recup = prom_crudo_sin_red is not None and prom_crudo_sin_red < 5.50

            for s_idx in range(5):
                tipo, sub_i, col_name, cell_key = self._get_slot_meta(s_idx, nombres_cols)
                val_actual = raw_valores[s_idx]
                is_active_slot = (self.active_grade_index == s_idx and is_open)
                deshabilitado = (s_idx == 4 and not habilita_recup)

                cell_widget, ref_dict = self._crear_slot_control(
                    id_al=id_str,
                    nombre_alumno=nombre_al,
                    col_name=col_name,
                    val_actual=val_actual,
                    trim_idx=trim_idx,
                    tipo=tipo,
                    sub_idx=sub_i,
                    slot_index=s_idx,
                    is_active=is_active_slot,
                    deshabilitado=deshabilitado,
                )

                slots_map[cell_key] = ref_dict
                slots_widgets.append(cell_widget)

            # Registrar referencias para tests y actualizaciones in-place
            self.alumnos_celdas[id_str] = {
                "P0": slots_map["P0"],
                "P1": slots_map["P1"],
                "P2": slots_map["P2"],
                "E0": slots_map["E0"],
                "R0": slots_map["R0"],
                "prom_container": prom_container,
                "prom_text": prom_text,
                "fin_container": fin_container,
                "fin_text": fin_text,
                "nombre": nombre_al,
                "pills": [pill1, pill2, pill3],
                "prom_anual_text": prom_anual_txt,
                "panel_anual": panel_anual,
                "anual_t1": ref_anual["t1_text"],
                "anual_t2": ref_anual["t2_text"],
                "anual_t3": ref_anual["t3_text"],
                "anual_promedio": ref_anual["promedio_anual_text"],
                "anual_estado": ref_anual["estado_text"],
                "anual_badge": ref_anual["estado_badge"],
            }
            self.slots_controls_by_student[id_str] = slots_map

            # Contenido expandido de la tarjeta (siempre construido, controlado por visibilidad para no destruir el ListView)
            # 1. Selector local de trimestre para el alumno
            trim_buttons = []
            for t in [1, 2, 3]:
                t_idx_btn = t - 1
                is_sel_t = (trim_idx == t_idx_btn)
                trim_buttons.append(
                    ft.Container(
                        expand=True,
                        height=32,
                        border_radius=8,
                        bgcolor=SURFACE_WHITE if is_sel_t else ft.Colors.TRANSPARENT,
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                        on_click=lambda _, val=t_idx_btn: self._seleccionar_trimestre(val),
                        content=ft.Text(
                            f"Trimestre {t}",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=PRIMARY if is_sel_t else TEXT_MUTED,
                        ),
                    )
                )
            self.local_trim_buttons[id_str] = trim_buttons

            selector_trim_local = ft.Container(
                bgcolor="#F1F5F9",
                border_radius=10,
                padding=2,
                content=ft.Row(spacing=2, controls=trim_buttons),
            )

            # 2. Formulario compacto de edición rápida de nombres
            txt_edit_apellido = ft.TextField(
                label="Apellido",
                value=self.name_drafts[id_str]["apellido"],
                dense=True,
                border_radius=8,
                text_size=12,
                on_change=lambda e, sid=id_str: self._actualizar_draft_nombre(sid, "apellido", e.control.value),
            )
            txt_edit_nombre = ft.TextField(
                label="Nombre",
                value=self.name_drafts[id_str]["nombre"],
                dense=True,
                border_radius=8,
                text_size=12,
                on_change=lambda e, sid=id_str: self._actualizar_draft_nombre(sid, "nombre", e.control.value),
            )

            edicion_alumno_row = ft.Column(
                spacing=6,
                controls=[
                    ft.Text("Editar datos del alumno", size=12, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                    ft.Row(spacing=8, controls=[ft.Container(expand=True, content=txt_edit_apellido), ft.Container(expand=True, content=txt_edit_nombre)]),
                ],
            )

            # 3. Fila de cálculos del trimestre actual
            resumen_trimestre_row = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Text("Promedio Trimestre:", size=11, color=TEXT_MUTED),
                            prom_container,
                        ],
                    ),
                    ft.Row(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Text("Nota Final:", size=11, color=TEXT_MUTED),
                            fin_container,
                        ],
                    ),
                ],
            )

            expanded_content = ft.Container(
                visible=(is_open and not es_modo_anual),
                padding=ft.Padding(left=12, right=12, top=10, bottom=12),
                border=ft.Border.only(top=ft.BorderSide(1, "#F1F5F9")),
                content=ft.Column(
                    spacing=12,
                    controls=[
                        edicion_alumno_row,
                        selector_trim_local,
                        ft.Row(spacing=6, controls=slots_widgets),
                        resumen_trimestre_row,
                    ],
                ),
            )
            self.expanded_containers[id_str] = expanded_content

            chevron_icon = ft.Icon(
                ft.Icons.EXPAND_LESS if is_open else ft.Icons.EXPAND_MORE,
                size=18,
                color=PRIMARY if is_open else TEXT_MUTED,
                visible=(not es_modo_anual),
            )
            self.chevron_icons[id_str] = chevron_icon

            header_pills_cont = ft.Container(
                visible=(not es_modo_anual),
                content=ft.Row(spacing=4, tight=True, controls=[pill1, pill2, pill3]),
            )
            self.header_pills_containers[id_str] = header_pills_cont

            # Tarjeta completa
            card_container = ft.Container(
                bgcolor=SURFACE_WHITE,
                border_radius=16,
                border=ft.Border.all(1.5, PRIMARY if (is_open and not es_modo_anual) else BORDER_COLOR),
                shadow=ft.BoxShadow(spread_radius=0, blur_radius=8, color="#0F172A0D" if (is_open and not es_modo_anual) else ft.Colors.TRANSPARENT),
                content=ft.Column(
                    spacing=0,
                    controls=[
                        # Cabecera colapsable / expandible
                        ft.Container(
                            padding=12,
                            ink=(not es_modo_anual),
                            on_click=lambda _, sid=id_str: self._toggle_expand_alumno(sid),
                            content=ft.Row(
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Container(
                                        width=40,
                                        height=40,
                                        bgcolor=avatar_bg,
                                        border_radius=20,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Text(iniciales, size=12, weight=ft.FontWeight.BOLD, color=avatar_fg),
                                    ),
                                    ft.Column(
                                        expand=True,
                                        spacing=1,
                                        controls=[
                                            ft.Text(f"#{id_str} {nombre_al}", size=13, weight=ft.FontWeight.BOLD, color=TEXT_MAIN, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                            prom_anual_txt,
                                        ],
                                    ),
                                    header_pills_cont,
                                    chevron_icon,
                                    ft.PopupMenuButton(
                                        icon=ft.Icons.MORE_VERT,
                                        icon_size=18,
                                        icon_color=TEXT_MUTED,
                                        items=[
                                            ft.PopupMenuItem(
                                                icon=ft.Icons.EDIT_OUTLINED,
                                                content=ft.Text("Renombrar"),
                                                on_click=lambda e, i=id_str, n=nombre_al: self._abrir_modal_renombrar_alumno(i, n),
                                            ),
                                            ft.PopupMenuItem(
                                                icon=ft.Icons.DELETE_OUTLINE,
                                                content=ft.Text("Eliminar Alumno"),
                                                on_click=lambda e, i=id_str, n=nombre_al: self._abrir_modal_eliminar_alumno(i, n),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        panel_anual,
                        expanded_content,
                    ],
                ),
            )

            self.tarjetas_alumnos[id_str] = card_container
            student_cards.append(card_container)

        self.lista_tarjetas_listview = ft.ListView(
            spacing=10,
            controls=student_cards,
            expand=True,
        )
        return self.lista_tarjetas_listview

    def _crear_slot_control(
        self,
        id_al: str,
        nombre_alumno: str,
        col_name: str,
        val_actual: float | int | None,
        trim_idx: int,
        tipo: str,
        sub_idx: int,
        slot_index: int,
        is_active: bool,
        deshabilitado: bool = False,
    ) -> tuple[ft.Control, dict]:
        """Crea el slot visual de nota interactivo para un alumno."""
        if val_actual is None or deshabilitado:
            val_str = "-"
        else:
            try:
                val_str = str(int(math.floor(float(str(val_actual).replace(",", ".")) + 0.5)))
            except (ValueError, TypeError):
                val_str = str(val_actual)
        bg_color, text_color = self._color_por_nota(val_actual) if not deshabilitado else (ft.Colors.TRANSPARENT, TEXT_SUBTLE)

        txt_widget = ft.Text(
            val_str,
            size=14 if not deshabilitado else 12,
            weight=ft.FontWeight.BOLD if not deshabilitado else ft.FontWeight.NORMAL,
            color=PRIMARY if (is_active and not deshabilitado) else text_color,
        )

        container = ft.Container(
            height=44,
            border_radius=10,
            border=ft.Border.all(2 if is_active else 1, PRIMARY if is_active else BORDER_COLOR),
            bgcolor=PRIMARY_LIGHT if is_active else bg_color,
            alignment=ft.Alignment.CENTER,
            ink=not deshabilitado,
            content=txt_widget,
        )

        label_text_widget = ft.Text(col_name, size=9, weight=ft.FontWeight.W_500, color=PRIMARY if is_active else TEXT_MUTED)

        ref_dict = {
            "container": container,
            "text_widget": txt_widget,
            "label_widget": label_text_widget,
            "valor": val_actual,
            "deshabilitado": deshabilitado,
            "slot_index": slot_index,
            "tipo": tipo,
            "sub_idx": sub_idx,
            "col_name": col_name,
        }

        def on_slot_click(e):
            if ref_dict.get("deshabilitado"):
                return
            self.expanded_student_id = id_al
            self.active_grade_index = slot_index
            self._actualizar_dock_labels()
            self._actualizar_slots_ui(id_al)

            # Abrir también GradeEditorDialog para soporte táctil fino y compatibilidad con tests
            def guardar_desde_dialogo(nuevo_val):
                curr_trim = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
                self.state.set_nota(id_al, curr_trim, ref_dict["tipo"], ref_dict["sub_idx"], nuevo_val)
                self._actualizar_fila_alumno_ui(id_al)
                self._actualizar_boton_guardar()
                self._actualizar_dock_labels()
                self.app_page.update()

            dlg = GradeEditorDialog(
                alumno_nombre=nombre_alumno,
                columna_nombre=ref_dict.get("col_name", col_name),
                valor_actual=ref_dict.get("valor"),
                on_save=guardar_desde_dialogo,
                page=self.app_page,
            )
            self.app_page.show_dialog(dlg)
            self.app_page.update()

        container.on_click = on_slot_click

        column_widget = ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=3,
            controls=[
                container,
                label_text_widget,
            ],
        )

        return column_widget, ref_dict

    def _construir_dock_teclado(self, alumnos: dict, trim_idx: int, nombres_cols: list[str]) -> ft.Control:
        """Construye el dock flotante inferior con el teclado numérico anclado al pie (.key-button)."""
        active_nombre = ""
        active_id = self.expanded_student_id
        if active_id and active_id in alumnos:
            active_nombre = alumnos[active_id].get("nombre", "")

        _, _, slot_col_name, _ = self._get_slot_meta(self.active_grade_index, nombres_cols)
        nombre_corto = active_nombre.split(",")[0].strip() if active_nombre else ""

        self.dock_label_active = ft.Text(
            f"Ingresar {slot_col_name} · #{active_id} {nombre_corto}" if active_id else "Selecciona un alumno para calificar",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=TEXT_MAIN,
            no_wrap=True,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        self.dock_badge_trimestre = ft.Text(
            f"T{trim_idx + 1}" if trim_idx < 3 else "Anual",
            size=11,
            weight=ft.FontWeight.BOLD,
            color=PRIMARY,
        )

        # Fila 1 de números: [1] a [5]
        numpad_row1_controls = []
        for n in range(1, 6):
            btn = build_key_button(
                text=str(n),
                on_click=lambda e, val=n: self._aplicar_nota_dock(val),
            )
            numpad_row1_controls.append(btn)

        # Fila 2 de números: [6] a [10] + [⌫] + [Sig.]
        numpad_row2_controls = []
        for n in range(6, 11):
            btn = build_key_button(
                text=str(n),
                on_click=lambda e, val=n: self._aplicar_nota_dock(val),
            )
            numpad_row2_controls.append(btn)

        btn_clear = build_key_button(
            icon=ft.Icons.BACKSPACE_OUTLINED,
            on_click=lambda e: self._limpiar_nota_dock(),
        )
        numpad_row2_controls.append(btn_clear)

        btn_sig = build_key_button(
            text="Sig.",
            is_primary=True,
            on_click=lambda e: self._avanzar_slot_dock(),
        )
        numpad_row2_controls.append(btn_sig)

        return ft.Container(
            bgcolor=SURFACE_WHITE,
            border=ft.Border.only(top=ft.BorderSide(1, BORDER_COLOR)),
            padding=ft.Padding(left=16, right=16, top=10, bottom=16),
            shadow=ft.BoxShadow(blur_radius=16, color="#0F172A14", offset=ft.Offset(0, -4)),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            self.dock_label_active,
                            ft.Container(
                                bgcolor=PRIMARY_LIGHT,
                                border_radius=6,
                                padding=ft.Padding(left=8, right=8, top=2, bottom=2),
                                content=self.dock_badge_trimestre,
                            ),
                        ],
                    ),
                    ft.Row(spacing=6, controls=numpad_row1_controls),
                    ft.Row(spacing=6, controls=numpad_row2_controls),
                ],
            ),
        )

    def _aplicar_nota_dock(self, valor: float | int):
        """Aplica la nota seleccionada en el dock inferior al slot activo del alumno expandido."""
        if self.state.active_trimestre >= 3 or not self.expanded_student_id:
            return

        id_al = self.expanded_student_id
        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        val_int = int(math.floor(float(valor) + 0.5))
        tipo, sub_idx, _, _ = self._get_slot_meta(self.active_grade_index, nombres_cols)
        self.state.set_nota(id_al, trim_idx, tipo, sub_idx, val_int)

        self._actualizar_fila_alumno_ui(id_al)
        self._actualizar_boton_guardar()

        # Avanzar automáticamente al siguiente slot
        if self.active_grade_index < 4:
            self.active_grade_index += 1
        else:
            # Si completó los 5 slots, pasar al siguiente alumno
            alumnos_keys = list(self.state.get_alumnos(colegio, curso).keys())
            if id_al in alumnos_keys:
                idx = alumnos_keys.index(id_al)
                next_idx = (idx + 1) % len(alumnos_keys)
                self._toggle_expand_alumno(alumnos_keys[next_idx])
                return

        self._actualizar_dock_labels()
        self._actualizar_slots_ui(id_al)
        self.app_page.update()

    def _limpiar_nota_dock(self):
        """Borra la nota del slot activo del alumno expandido."""
        if self.state.active_trimestre >= 3 or not self.expanded_student_id:
            return

        id_al = self.expanded_student_id
        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        tipo, sub_idx, _, _ = self._get_slot_meta(self.active_grade_index, nombres_cols)
        self.state.set_nota(id_al, trim_idx, tipo, sub_idx, None)

        self._actualizar_fila_alumno_ui(id_al)
        self._actualizar_boton_guardar()
        self._actualizar_dock_labels()
        self.app_page.update()

    def _avanzar_slot_dock(self):
        """Avanza al siguiente slot o al siguiente alumno."""
        if self.state.active_trimestre >= 3:
            return

        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos_keys = list(self.state.get_alumnos(colegio, curso).keys())

        if self.active_grade_index < 4:
            self.active_grade_index += 1
            if self.expanded_student_id:
                self._actualizar_slots_ui(self.expanded_student_id)
            self._actualizar_dock_labels()
            self.app_page.update()
        elif alumnos_keys and self.expanded_student_id in alumnos_keys:
            idx = alumnos_keys.index(self.expanded_student_id)
            next_idx = (idx + 1) % len(alumnos_keys)
            self._toggle_expand_alumno(alumnos_keys[next_idx])

    def _actualizar_dock_labels(self):
        """Actualiza el texto y badge del dock flotante inferior."""
        if not self.dock_label_active:
            return

        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso)
        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        nombres_cols = self.state.get_nombres_columnas(colegio, curso, trim_idx)

        active_id = self.expanded_student_id
        active_nombre = alumnos.get(active_id, {}).get("nombre", "") if active_id else ""
        nombre_corto = active_nombre.split(",")[0].strip() if active_nombre else ""
        _, _, slot_col_name, _ = self._get_slot_meta(self.active_grade_index, nombres_cols)

        if active_id:
            self.dock_label_active.value = f"Ingresar {slot_col_name} · #{active_id} {nombre_corto}"
        else:
            self.dock_label_active.value = "Selecciona un alumno para calificar"

        if self.dock_badge_trimestre:
            self.dock_badge_trimestre.value = f"T{trim_idx + 1}" if trim_idx < 3 else "Anual"

    def _actualizar_slots_ui(self, id_al: str):
        """Actualiza los bordes y resaltados de los slots activos del alumno expandido."""
        if id_al not in self.slots_controls_by_student:
            return

        slots_dict = self.slots_controls_by_student[id_al]
        for key, ref in slots_dict.items():
            s_idx = ref.get("slot_index", 0)
            is_active = (s_idx == self.active_grade_index and str(self.expanded_student_id) == str(id_al))
            val = ref.get("valor")
            desh = ref.get("deshabilitado", False)

            bg, fg = self._color_por_nota(val) if not desh else (ft.Colors.TRANSPARENT, TEXT_SUBTLE)
            ref["container"].border = ft.Border.all(2 if is_active else 1, PRIMARY if is_active else BORDER_COLOR)
            ref["container"].bgcolor = PRIMARY_LIGHT if is_active else bg
            ref["text_widget"].color = PRIMARY if (is_active and not desh) else fg
            if "label_widget" in ref and ref["label_widget"] is not None:
                ref["label_widget"].color = PRIMARY if is_active else TEXT_MUTED

    def _actualizar_fila_alumno_ui(self, id_al: str):
        """Actualiza in-place las celdas, cálculos, píldoras y promedios del alumno sin recargar la lista."""
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

        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
        nombre_trim = NOMBRES_TRIMESTRES[trim_idx]
        trim_data = al_data.get("trimestres", {}).get(nombre_trim, {})
        principales = trim_data.get("principales", [None] * NUM_PRINCIPALES)
        extras = trim_data.get("extras", [None] * NUM_EXTRAS)
        recuperatorio = trim_data.get("recuperatorio")

        calcs = procesar_calificaciones_alumno(al_data.get("trimestres", {}))
        prom_crudo_red = calcs["promedios_crudos_redondeados"][trim_idx]
        nota_final_red = calcs["notas_finales_redondeadas"][trim_idx]
        prom_crudo_sin_red = calcs["promedios_crudos_sin_redondear"][trim_idx]
        habilita_recup = prom_crudo_sin_red is not None and prom_crudo_sin_red < 5.50

        # Actualizar celdas de notas individuales
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
                if val is None:
                    val_str = "-"
                else:
                    try:
                        val_str = str(int(math.floor(float(str(val).replace(",", ".")) + 0.5)))
                    except (ValueError, TypeError):
                        val_str = str(val)
                bg, fg = self._color_por_nota(val)
                ref["text_widget"].value = val_str
                ref["text_widget"].color = fg
                ref["container"].bgcolor = bg

        if "R0" in celdas:
            ref_r = celdas["R0"]
            ref_r["valor"] = recuperatorio
            deshabilitado = not habilita_recup
            ref_r["deshabilitado"] = deshabilitado
            ref_r["container"].ink = not deshabilitado
            if deshabilitado:
                ref_r["text_widget"].value = "-"
                ref_r["text_widget"].color = TEXT_SUBTLE
                ref_r["container"].bgcolor = ft.Colors.TRANSPARENT
                ref_r["container"].border = ft.Border.all(1, BORDER_COLOR)
            else:
                if recuperatorio is None:
                    val_str = "-"
                else:
                    try:
                        val_str = str(int(math.floor(float(str(recuperatorio).replace(",", ".")) + 0.5)))
                    except (ValueError, TypeError):
                        val_str = str(recuperatorio)
                bg, fg = self._color_por_nota(recuperatorio)
                ref_r["text_widget"].value = val_str
                ref_r["text_widget"].color = fg
                ref_r["container"].bgcolor = bg
                ref_r["container"].border = ft.Border.all(1, BORDER_COLOR)

        # Actualizar promedios y final del trimestre
        bg_prom, fg_prom = self._color_por_nota(prom_crudo_red)
        celdas["prom_text"].value = str(prom_crudo_red) if prom_crudo_red is not None else "-"
        celdas["prom_text"].color = fg_prom
        celdas["prom_container"].bgcolor = bg_prom

        bg_fin, fg_fin = self._color_por_nota(nota_final_red)
        celdas["fin_text"].value = str(nota_final_red) if nota_final_red is not None else "-"
        celdas["fin_text"].color = fg_fin
        celdas["fin_container"].bgcolor = bg_fin

        # Actualizar píldoras de trimestres (.grade-pill)
        if id_str in self.pills_alumnos:
            pills = self.pills_alumnos[id_str]
            for i, p_ctrl in enumerate(pills):
                t_val = calcs["notas_finales_redondeadas"][i]
                if t_val is None:
                    t_str = "--"
                else:
                    try:
                        t_str = str(int(math.floor(float(str(t_val).replace(",", ".")) + 0.5)))
                    except (ValueError, TypeError):
                        t_str = str(t_val)
                bg_p, fg_p = self._color_por_nota(t_val)
                p_ctrl.bgcolor = bg_p
                # Actualizar el texto del contenido
                if hasattr(p_ctrl, "content") and hasattr(p_ctrl.content, "controls") and len(p_ctrl.content.controls) > 1:
                    p_ctrl.content.controls[1].value = t_str
                    p_ctrl.content.controls[1].color = fg_p

        # Actualizar promedio anual
        total = calcs["nota_final_total_redondeada"]
        if id_str in self.promedio_anual_labels:
            self.promedio_anual_labels[id_str].value = f"Promedio anual: {total if total is not None else '--'}"

        # Actualizar panel anual informativo de solo lectura
        self._actualizar_panel_anual_ui(id_str)

        # In-place update estricto: actualiza únicamente la tarjeta del alumno sin re-renderizados generales
        if hasattr(self, "tarjetas_alumnos") and id_str in self.tarjetas_alumnos:
            card = self.tarjetas_alumnos[id_str]
            try:
                card.update()
            except Exception:
                pass

    def _toggle_expand_alumno(self, sid: str):
        """Expande o colapsa la tarjeta de un alumno in-place conservando la posición de scroll."""
        if self.state.active_trimestre >= 3:
            # En modo Anual la vista es puramente informativa de solo lectura sin edición
            return

        prev_id = self.expanded_student_id
        sid_str = str(sid)

        # Si el control no está en los diccionarios, recurrir a _build_ui
        if sid_str not in self.expanded_containers or sid_str not in self.tarjetas_alumnos:
            if self.expanded_student_id == sid_str:
                self.expanded_student_id = None
            else:
                self.expanded_student_id = sid_str
                self.active_grade_index = 0
            self._build_ui()
            self.app_page.update()
            return

        if prev_id == sid_str:
            # Colapsar el alumno actual
            self.expanded_student_id = None
            self.expanded_containers[sid_str].visible = False
            self.tarjetas_alumnos[sid_str].border = ft.Border.all(1.5, BORDER_COLOR)
            self.tarjetas_alumnos[sid_str].shadow = ft.BoxShadow(spread_radius=0, blur_radius=8, color=ft.Colors.TRANSPARENT)
            if sid_str in self.chevron_icons:
                self.chevron_icons[sid_str].name = ft.Icons.EXPAND_MORE
                self.chevron_icons[sid_str].color = TEXT_MUTED
        else:
            # Colapsar el alumno previo si existe
            if prev_id and str(prev_id) in self.expanded_containers:
                prev_str = str(prev_id)
                self.expanded_containers[prev_str].visible = False
                if prev_str in self.tarjetas_alumnos:
                    self.tarjetas_alumnos[prev_str].border = ft.Border.all(1.5, BORDER_COLOR)
                    self.tarjetas_alumnos[prev_str].shadow = ft.BoxShadow(spread_radius=0, blur_radius=8, color=ft.Colors.TRANSPARENT)
                if prev_str in self.chevron_icons:
                    self.chevron_icons[prev_str].name = ft.Icons.EXPAND_MORE
                    self.chevron_icons[prev_str].color = TEXT_MUTED

            # Expandir el nuevo alumno
            self.expanded_student_id = sid_str
            self.active_grade_index = 0
            self.expanded_containers[sid_str].visible = True
            self.tarjetas_alumnos[sid_str].border = ft.Border.all(1.5, PRIMARY)
            self.tarjetas_alumnos[sid_str].shadow = ft.BoxShadow(spread_radius=0, blur_radius=8, color="#0F172A0D")
            if sid_str in self.chevron_icons:
                self.chevron_icons[sid_str].name = ft.Icons.EXPAND_LESS
                self.chevron_icons[sid_str].color = PRIMARY
            self._actualizar_slots_ui(sid_str)

        self._actualizar_dock_labels()
        self.app_page.update()

    def _actualizar_draft_nombre(self, sid: str, campo: str, valor: str):
        if sid not in self.name_drafts:
            self.name_drafts[sid] = {"apellido": "", "nombre": ""}
        self.name_drafts[sid][campo] = valor

        # Auto-guardado reactivo con debounce de 600 ms para inputs de texto
        ap = self.name_drafts[sid].get("apellido", "").strip()
        nom = self.name_drafts[sid].get("nombre", "").strip()
        if ap or nom:
            self.state.rename_alumno(sid, ap, nom, auto_save=True)

    def _cambiar_pestana(self, selected_set):
        if "asistencias" in selected_set:
            self.state.flush_auto_save()
            self.on_navigate("asistencias")

    def _accion_volver(self, e=None):
        self.state.flush_auto_save()
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
            self.state.load_data()
            self.on_navigate(destino)

        dlg = ft.AlertDialog(
            title=ft.Text("Cambios sin guardar", weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
            content=ft.Text("Tienes calificaciones modificadas sin guardar.\n¿Deseas guardarlas antes de continuar?", color=TEXT_MUTED),
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

    def _guardar_notas(self):
        if self.state.save_data():
            self._build_ui()
            self.app_page.update()
            self._mostrar_snackbar("Calificaciones guardadas exitosamente.")
        else:
            self._mostrar_snackbar("Error al guardar calificaciones.", error=True)

    def _abrir_modal_agregar_alumno(self):
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
        trim_idx = self.state.active_trimestre if 0 <= self.state.active_trimestre < 3 else 0
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


# Alias para compatibilidad de nomenclatura
PlanillaView = NotasView

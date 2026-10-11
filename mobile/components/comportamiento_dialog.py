"""
Diálogo modal para calificación y registro de comportamiento de alumnos en Notaly.
Permite seleccionar comportamientos clasificados en Positivo, Regular y Negativo,
desplegando subtipos específicos (Meritoria, Ejemplar, Regular, Inadecuado, Grave)
y campo de observación opcional sin placeholder.
Opera con autoguardado reactivo al instante y en segundo plano sin botones manuales de guardado.
"""

from datetime import datetime
from typing import Callable
import flet as ft

from mobile.theme import (
    PRIMARY,
    PRIMARY_LIGHT,
    PRIMARY_HOVER,
    TEXT_MAIN,
    TEXT_MUTED,
    BORDER_COLOR,
    BORDER_ACTIVE,
    BG_PAGE,
    SURFACE_WHITE,
    LIGHT_TOKENS,
    DARK_TOKENS,
    ThemeTokens,
    get_tokens,
    get_avatar_palette,
    extract_initials,
)
from core.constants import (
    K_COMPORTAMIENTOS,
    K_FECHA,
    K_TIPO,
    K_SUBTIPO,
    K_OBSERVACION,
    COMPORTAMIENTO_POSITIVO,
    COMPORTAMIENTO_REGULAR,
    COMPORTAMIENTO_NEGATIVO,
    SUBTIPO_MERITORIA,
    SUBTIPO_EJEMPLAR,
    SUBTIPO_REGULAR,
    SUBTIPO_INADECUADO,
    SUBTIPO_GRAVE,
    FORMATO_FECHA,
    formatear_fecha,
)
from mobile.state import AppState

COLOR_POS_BG = "#DCFCE7"
COLOR_POS_TEXT = "#166534"
COLOR_POS_SOLID = "#10B981"

COLOR_REG_BG = "#FEF3C7"
COLOR_REG_TEXT = "#B45309"
COLOR_REG_SOLID = "#F59E0B"

COLOR_NEG_BG = "#FEE2E2"
COLOR_NEG_TEXT = "#991B1B"
COLOR_NEG_SOLID = "#EF4444"


def get_comportamiento_style(tipo: str, tokens: ThemeTokens | None = None) -> tuple[str, str, str]:
    """Retorna (bgcolor_suave, text_color, solid_color) según el tipo de comportamiento."""
    t = str(tipo or "").lower().strip()
    if tokens:
        if t == COMPORTAMIENTO_POSITIVO:
            return tokens.attendance_p_bg, tokens.attendance_p_text, tokens.attendance_p_solid
        elif t == COMPORTAMIENTO_REGULAR:
            return tokens.attendance_t_bg, tokens.attendance_t_text, tokens.attendance_t_solid
        elif t == COMPORTAMIENTO_NEGATIVO:
            return tokens.attendance_a_bg, tokens.attendance_a_text, tokens.attendance_a_solid
        return tokens.bg_page, tokens.text_muted, tokens.border_color
    if t == COMPORTAMIENTO_POSITIVO:
        return COLOR_POS_BG, COLOR_POS_TEXT, COLOR_POS_SOLID
    elif t == COMPORTAMIENTO_REGULAR:
        return COLOR_REG_BG, COLOR_REG_TEXT, COLOR_REG_SOLID
    elif t == COMPORTAMIENTO_NEGATIVO:
        return COLOR_NEG_BG, COLOR_NEG_TEXT, COLOR_NEG_SOLID
    return "#F1F5F9", TEXT_MUTED, "#94A3B8"


class ComportamientoDialog(ft.AlertDialog):
    """
    Diálogo modal de registro y calificación de comportamiento para un alumno.
    Cumple con el principio de cero botones manuales de guardado y preservación de scroll.
    """

    def __init__(
        self,
        state: AppState,
        id_alumno: str,
        nombre_alumno: str,
        colegio: str | None = None,
        curso: str | None = None,
        on_close: Callable[[], None] | None = None,
        page: ft.Page | None = None,
        tokens: ThemeTokens | None = None,
    ):
        self.state = state
        self.id_alumno = str(id_alumno)
        self.nombre_alumno = nombre_alumno
        self.colegio = colegio or self.state.selected_colegio or ""
        self.curso = curso or self.state.selected_curso or ""
        self.on_close_cb = on_close
        self.app_page = page
        self.tokens = tokens or getattr(state, "tokens", None) or get_tokens("dark" if getattr(page, "theme_mode", None) == ft.ThemeMode.DARK else "light")
        tok = self.tokens

        # Fecha de observación activa (por defecto hoy)
        self.fecha_activa = datetime.now().strftime(FORMATO_FECHA)

        # Estado local de la selección actual
        self.tipo_seleccionado: str | None = None
        self.subtipo_seleccionado: str | None = None
        self.obs_activa_id: str | None = None

        # Contenedores reactivos
        self.subtipos_container = ft.Container(visible=False)
        self.observacion_input_container = ft.Container(visible=False)
        self.micro_status_text = ft.Text(
            "",
            size=11,
            color=COLOR_POS_SOLID,
            weight=ft.FontWeight.W_500,
            visible=False,
        )
        self.historial_container = ft.Column(spacing=6)

        # Campo de texto opcional SIN placeholder
        self.txt_observacion = ft.TextField(
            label="Observación (opcional)",
            hint_text="",  # Sin placeholder de ejemplo
            multiline=True,
            min_lines=2,
            max_lines=4,
            dense=True,
            border_radius=10,
            bgcolor=tok.bg_page,
            border_color=tok.border_color,
            focused_border_color=tok.primary,
            text_size=12,
            color=tok.text_main,
            on_change=self._al_cambiar_observacion_texto,
        )

        # Botones de categoría principal
        self.btn_positivo = self._crear_boton_categoria("Positivo", COMPORTAMIENTO_POSITIVO, COLOR_POS_SOLID)
        self.btn_regular = self._crear_boton_categoria("Regular", COMPORTAMIENTO_REGULAR, COLOR_REG_SOLID)
        self.btn_negativo = self._crear_boton_categoria("Negativo", COMPORTAMIENTO_NEGATIVO, COLOR_NEG_SOLID)

        # Construir contenido del modal
        dialog_content = self._construir_contenido()

        super().__init__(
            modal=True,
            bgcolor=tok.surface,
            content=dialog_content,
            actions=[],  # Cero botones de guardar manuales en actions
            actions_alignment=ft.MainAxisAlignment.END,
            content_padding=ft.Padding(left=16, right=16, top=16, bottom=16),
            shape=ft.RoundedRectangleBorder(radius=16),
        )

        # Cargar historial previo
        self._refrescar_historial_ui()

    def _crear_boton_categoria(self, label: str, tipo: str, color_solido: str) -> ft.Container:
        """Crea un botón estilizado para seleccionar la categoría de comportamiento."""
        tok = self.tokens
        return ft.Container(
            expand=True,
            height=40,
            border_radius=10,
            bgcolor=tok.surface_variant,
            border=ft.Border.all(1.5, tok.border_color),
            alignment=ft.Alignment.CENTER,
            ink=True,
            on_click=lambda _: self._seleccionar_categoria(tipo),
            content=ft.Text(
                label,
                size=12,
                weight=ft.FontWeight.BOLD,
                color=tok.text_main,
            ),
        )

    def _construir_contenido(self) -> ft.Container:
        """Construye el layout desplazable del diálogo."""
        tok = self.tokens
        num_id = int(self.id_alumno) if self.id_alumno.isdigit() else 0
        avatar_bg, avatar_fg = get_avatar_palette(num_id, is_dark=(tok == DARK_TOKENS))
        iniciales = extract_initials(self.nombre_alumno)

        # 1. Cabecera con avatar, alumno y botón de cierre
        header = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    tight=True,
                    controls=[
                        ft.Container(
                            width=38,
                            height=38,
                            bgcolor=avatar_bg,
                            border_radius=19,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text(iniciales, size=12, weight=ft.FontWeight.BOLD, color=avatar_fg),
                        ),
                        ft.Column(
                            spacing=1,
                            tight=True,
                            controls=[
                                ft.Text(
                                    f"#{self.id_alumno} {self.nombre_alumno}",
                                    size=14,
                                    weight=ft.FontWeight.BOLD,
                                    color=tok.text_main,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    f"Comportamiento · {self.fecha_activa}",
                                    size=11,
                                    color=tok.text_muted,
                                ),
                            ],
                        ),
                    ],
                ),
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=tok.text_muted,
                    icon_size=20,
                    tooltip="Cerrar",
                    on_click=lambda _: self._cerrar_dialogo(),
                ),
            ],
        )

        # 2. Selector de categoría principal (Positivo / Regular / Negativo)
        categorias_row = ft.Row(
            spacing=8,
            controls=[
                self.btn_positivo,
                self.btn_regular,
                self.btn_negativo,
            ],
        )

        # 3. Contenedor de observación opcional
        self.observacion_input_container.content = ft.Column(
            spacing=4,
            tight=True,
            controls=[
                self.txt_observacion,
                self.micro_status_text,
            ],
        )

        # 4. Sección de Historial
        seccion_historial = ft.Column(
            spacing=8,
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            "Historial de observaciones",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=tok.text_main,
                        ),
                        ft.Icon(ft.Icons.HISTORY, size=16, color=tok.text_muted),
                    ],
                ),
                self.historial_container,
            ],
        )

        scroll_content = ft.Column(
            spacing=14,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                header,
                ft.Divider(height=1, color=tok.border_color),
                ft.Text("Calificar comportamiento:", size=12, weight=ft.FontWeight.BOLD, color=tok.text_main),
                categorias_row,
                self.subtipos_container,
                self.observacion_input_container,
                ft.Divider(height=1, color=tok.border_color),
                seccion_historial,
            ],
        )


        return ft.Container(
            content=scroll_content,
            width=360,
            height=480,
            padding=0,
        )

    def _actualizar_estilo_botones_categoria(self):
        """Actualiza el aspecto visual de los 3 botones principales según la selección."""
        categorias = [
            (self.btn_positivo, COMPORTAMIENTO_POSITIVO, COLOR_POS_SOLID, COLOR_POS_BG, COLOR_POS_TEXT),
            (self.btn_regular, COMPORTAMIENTO_REGULAR, COLOR_REG_SOLID, COLOR_REG_BG, COLOR_REG_TEXT),
            (self.btn_negativo, COMPORTAMIENTO_NEGATIVO, COLOR_NEG_SOLID, COLOR_NEG_BG, COLOR_NEG_TEXT),
        ]

        for btn, tipo, solid, bg_suave, text_col in categorias:
            is_sel = (self.tipo_seleccionado == tipo)
            btn.bgcolor = bg_suave if is_sel else "#F8FAFC"
            btn.border = ft.Border.all(2 if is_sel else 1.5, solid if is_sel else BORDER_COLOR)
            if hasattr(btn, "content") and isinstance(btn.content, ft.Text):
                btn.content.color = text_col if is_sel else TEXT_MAIN
                btn.content.weight = ft.FontWeight.BOLD if is_sel else ft.FontWeight.W_500

    def _seleccionar_categoria(self, tipo: str):
        """Maneja la pulsación de una de las tres categorías principales."""
        self.tipo_seleccionado = tipo
        self._actualizar_estilo_botones_categoria()

        if tipo == COMPORTAMIENTO_REGULAR:
            # Para Regular: selección directa de subtipo "Regular"
            self.subtipo_seleccionado = SUBTIPO_REGULAR
            self.subtipos_container.visible = False

            # Auto-guardado inmediato del registro
            self._guardar_observacion_inmediata(COMPORTAMIENTO_REGULAR, SUBTIPO_REGULAR)

            # Mostrar campo de texto opcional
            self.observacion_input_container.visible = True

        elif tipo == COMPORTAMIENTO_POSITIVO:
            # Mostrar seleccionables: Meritoria / Ejemplar
            self.subtipo_seleccionado = None
            self.subtipos_container.visible = True
            self.subtipos_container.content = self._construir_subtipos_row(
                [SUBTIPO_MERITORIA, SUBTIPO_EJEMPLAR],
                COLOR_POS_SOLID,
                COLOR_POS_BG,
                COLOR_POS_TEXT,
            )
            # Ocultar input hasta que se elija subtipo
            self.observacion_input_container.visible = False

        elif tipo == COMPORTAMIENTO_NEGATIVO:
            # Mostrar seleccionables: Inadecuado / Grave
            self.subtipo_seleccionado = None
            self.subtipos_container.visible = True
            self.subtipos_container.content = self._construir_subtipos_row(
                [SUBTIPO_INADECUADO, SUBTIPO_GRAVE],
                COLOR_NEG_SOLID,
                COLOR_NEG_BG,
                COLOR_NEG_TEXT,
            )
            # Ocultar input hasta que se elija subtipo
            self.observacion_input_container.visible = False

        self._actualizar_dialogo()

    def _construir_subtipos_row(
        self,
        subtipos: list[str],
        color_solido: str,
        bg_suave: str,
        text_col: str,
    ) -> ft.Container:
        """Construye la fila de botones de subtipos seleccionables."""
        tok = self.tokens
        botones = []
        for st in subtipos:
            is_sel = (self.subtipo_seleccionado == st)
            btn = ft.Container(
                expand=True,
                height=36,
                border_radius=8,
                bgcolor=bg_suave if is_sel else tok.surface_variant,
                border=ft.Border.all(1.5, color_solido if is_sel else tok.border_color),
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda _, val=st: self._seleccionar_subtipo(val),
                content=ft.Text(
                    val_label := st,
                    size=12,
                    weight=ft.FontWeight.BOLD if is_sel else ft.FontWeight.W_500,
                    color=text_col if is_sel else tok.text_main,
                ),
            )
            botones.append(btn)

        return ft.Container(
            padding=ft.Padding(left=0, right=0, top=2, bottom=4),
            content=ft.Row(spacing=8, controls=botones),
        )

    def _seleccionar_subtipo(self, subtipo: str):
        """Maneja la selección de un subtipo específico (Meritoria, Ejemplar, Inadecuado, Grave)."""
        self.subtipo_seleccionado = subtipo

        # Re-renderizar subtipos para marcar el activo
        if self.tipo_seleccionado == COMPORTAMIENTO_POSITIVO:
            self.subtipos_container.content = self._construir_subtipos_row(
                [SUBTIPO_MERITORIA, SUBTIPO_EJEMPLAR],
                COLOR_POS_SOLID,
                COLOR_POS_BG,
                COLOR_POS_TEXT,
            )
        elif self.tipo_seleccionado == COMPORTAMIENTO_NEGATIVO:
            self.subtipos_container.content = self._construir_subtipos_row(
                [SUBTIPO_INADECUADO, SUBTIPO_GRAVE],
                COLOR_NEG_SOLID,
                COLOR_NEG_BG,
                COLOR_NEG_TEXT,
            )

        # Auto-guardado inmediato de la opción seleccionada
        self._guardar_observacion_inmediata(self.tipo_seleccionado, subtipo)

        # Desplegar campo de texto opcional
        self.observacion_input_container.visible = True
        self._actualizar_dialogo()

    def _guardar_observacion_inmediata(self, tipo: str, subtipo: str):
        """Crea o actualiza la observación inmediatamente con autoguardado en background."""
        if self.obs_activa_id:
            # Actualizar la observación que se está editando en la sesión
            self.state.update_comportamiento_alumno(
                id_al=self.id_alumno,
                comp_id=self.obs_activa_id,
                tipo=tipo,
                subtipo=subtipo,
                fecha=self.fecha_activa,
                colegio=self.colegio,
                curso=self.curso,
                auto_save=True,
            )
        else:
            # Crear nueva observación
            ok, _, nueva_obs = self.state.add_comportamiento_alumno(
                id_al=self.id_alumno,
                tipo=tipo,
                subtipo=subtipo,
                observacion=self.txt_observacion.value or "",
                fecha=self.fecha_activa,
                colegio=self.colegio,
                curso=self.curso,
                auto_save=True,
            )
            if ok and "id" in nueva_obs:
                self.obs_activa_id = nueva_obs["id"]

        self._mostrar_micro_status("✓ Guardado automático")
        self._refrescar_historial_ui()

    def _al_cambiar_observacion_texto(self, e):
        """Evento on_change del campo de texto libre: autoguarda con debounce."""
        nuevo_texto = (e.control.value or "").strip()
        if self.obs_activa_id:
            self.state.update_comportamiento_alumno(
                id_al=self.id_alumno,
                comp_id=self.obs_activa_id,
                observacion=nuevo_texto,
                colegio=self.colegio,
                curso=self.curso,
                auto_save=True,
            )
            self._mostrar_micro_status("✓ Guardando...")
            self._refrescar_historial_ui()

    def _mostrar_micro_status(self, mensaje: str):
        """Muestra una micro-notificación discreta de persistencia."""
        self.micro_status_text.value = mensaje
        self.micro_status_text.visible = True
        self._actualizar_dialogo()

    def _refrescar_historial_ui(self):
        """Actualiza la lista visual del historial de observaciones del alumno."""
        tok = self.tokens
        observaciones = self.state.get_comportamientos_alumno(
            id_al=self.id_alumno,
            colegio=self.colegio,
            curso=self.curso,
        )

        self.historial_container.controls.clear()

        if not observaciones:
            self.historial_container.controls.append(
                ft.Container(
                    padding=10,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "No hay observaciones registradas aún.",
                        size=11,
                        color=TEXT_MUTED,
                        italic=True,
                    ),
                )
            )
            return

        for obs in observaciones:
            c_id = obs.get("id")
            tipo = obs.get(K_TIPO, "")
            subtipo = obs.get(K_SUBTIPO, "")
            fecha = obs.get(K_FECHA, "")
            texto = obs.get(K_OBSERVACION, "").strip()

            bg_c, text_c, solid_c = get_comportamiento_style(tipo)

            # Badge de subtipo
            badge = ft.Container(
                bgcolor=bg_c,
                border_radius=6,
                padding=ft.Padding(left=6, right=6, top=2, bottom=2),
                content=ft.Text(
                    subtipo or tipo.capitalize(),
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=text_c,
                ),
            )

            fila_header = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=6,
                        tight=True,
                        controls=[
                            badge,
                            ft.Text(formatear_fecha(fecha), size=11, color=tok.text_muted),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=16,
                        icon_color=tok.text_muted,
                        tooltip="Eliminar observación",
                        on_click=lambda _, comp_id=c_id: self._eliminar_observacion(comp_id),
                    ),
                ],
            )

            controles_tarjeta = [fila_header]
            # Si el profesor añadió texto opcional, mostrarlo; si no, solo se muestra la opción
            if texto:
                controles_tarjeta.append(
                    ft.Text(texto, size=11, color=tok.text_main)
                )

            tarjeta_obs = ft.Container(
                bgcolor=tok.surface_variant,
                border=ft.Border.all(1, tok.border_color),
                border_radius=8,
                padding=ft.Padding(left=10, right=6, top=6, bottom=6),
                content=ft.Column(spacing=4, tight=True, controls=controles_tarjeta),
            )

            self.historial_container.controls.append(tarjeta_obs)

    def _eliminar_observacion(self, comp_id: str):
        """Elimina una observación y actualiza el historial in-place."""
        self.state.delete_comportamiento_alumno(
            id_al=self.id_alumno,
            comp_id=comp_id,
            colegio=self.colegio,
            curso=self.curso,
            auto_save=True,
        )
        if self.obs_activa_id == comp_id:
            self.obs_activa_id = None
            self.txt_observacion.value = ""

        self._refrescar_historial_ui()
        self._actualizar_dialogo()

    def _cerrar_dialogo(self):
        """Cierra el diálogo modal asegurando el vaciado de búfer en almacenamiento local."""
        self.state.flush_auto_save()
        if self.app_page:
            try:
                self.app_page.pop_dialog()
            except Exception:
                pass
        if self.on_close_cb:
            self.on_close_cb()

    def _actualizar_dialogo(self):
        """Ejecuta un update reactivo seguro del diálogo si está montado."""
        if self.app_page:
            try:
                self.app_page.update()
                return
            except Exception:
                pass
        try:
            self.update()
        except Exception:
            pass

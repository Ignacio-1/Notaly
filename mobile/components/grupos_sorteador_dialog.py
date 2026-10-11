"""
Componentes modales para la generación y gestión de Trabajos en Grupo:
- SorteadorGruposDialog: Asistente interactivo con balanceo automático, previsualización en vivo y temas.
- ReasignarAlumnoDialog: Modal ágil para reubicar alumnos entre grupos de forma manual.
"""

from typing import Callable, Any
import flet as ft
from mobile.state import AppState
from mobile.theme import (
    PRIMARY,
    SURFACE_WHITE,
    BORDER_COLOR,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUBTLE,
)
from core.grupos import (
    distribuir_alumnos_en_grupos,
    calcular_previsualizacion_grupos,
    asignar_temas_a_grupos,
)


class SorteadorGruposDialog(ft.AlertDialog):
    """Diálogo modal para configurar y sortear grupos de trabajo con o sin temas."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page,
        on_created: Callable[[dict], Any],
    ):
        self.app_state = state
        self.app_page = page
        self.on_created = on_created

        colegio = state.selected_colegio or ""
        curso = state.selected_curso or ""
        self.alumnos_dict = state.get_alumnos(colegio, curso)
        self.total_alumnos = len(self.alumnos_dict)

        # Estado del formulario
        self.modo = "por_grupos"  # "por_grupos" | "por_integrantes"
        self.valor = 4 if self.total_alumnos >= 4 else max(1, self.total_alumnos)
        self.sortear_temas = False
        self.temas_lista: list[str] = []

        trabajos_existentes = state.get_trabajos_grupo_curso(colegio, curso)
        num_nuevo = len(trabajos_existentes) + 1
        self.tf_titulo = ft.TextField(
            label="Título del Trabajo",
            value=f"Trabajo Práctico N° {num_nuevo}",
            border_radius=8,
            border_color=BORDER_COLOR,
            text_size=13,
            color=TEXT_MAIN,
            expand=True,
        )

        self.tf_valor = ft.TextField(
            value=str(self.valor),
            width=55,
            height=38,
            text_align=ft.TextAlign.CENTER,
            text_size=14,
            border_radius=8,
            border_color=BORDER_COLOR,
            input_filter=ft.NumbersOnlyInputFilter(),
            on_change=self._on_valor_text_change,
        )

        self.preview_text = ft.Text(
            size=12,
            weight=ft.FontWeight.W_500,
            color="#1E293B",
        )

        self.tf_nuevo_tema = ft.TextField(
            hint_text="Escribir tema o consigna...",
            text_size=12,
            border_radius=8,
            border_color=BORDER_COLOR,
            expand=True,
            on_submit=lambda _: self._agregar_tema(),
        )

        self.temas_wrap = ft.Row(wrap=True, spacing=6, run_spacing=6)

        super().__init__(
            modal=True,
            title=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.CASINO, color=PRIMARY, size=24),
                    ft.Column(
                        spacing=1,
                        controls=[
                            ft.Text("Sortear Grupos de Trabajo", size=16, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                            ft.Text(f"{curso} • {self.total_alumnos} alumnos", size=12, color=TEXT_MUTED),
                        ],
                    ),
                ],
            ),
            content=self._build_content(),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self._cerrar()),
                ft.FilledButton(
                    "¡Sortear y Crear!",
                    style=ft.ButtonStyle(
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=lambda _: self._ejecutar_sorteo(),
                ) if self.total_alumnos > 0 else ft.Container(),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._actualizar_preview()

    def _actualizar_preview(self):
        prev = calcular_previsualizacion_grupos(self.total_alumnos, self.modo, self.valor)
        self.preview_text.value = f"💡 {prev['resumen']}"

    def _on_valor_text_change(self, e):
        val_str = self.tf_valor.value or ""
        if val_str.isdigit() and int(val_str) > 0:
            self.valor = int(val_str)
            self._actualizar_preview()
            if self.app_page:
                self.app_page.update()

    def _ajustar_valor(self, delta: int):
        nuevo = max(1, self.valor + delta)
        if self.modo == "por_grupos":
            nuevo = min(nuevo, max(1, self.total_alumnos))
        self.valor = nuevo
        self.tf_valor.value = str(self.valor)
        self._actualizar_preview()
        if self.app_page:
            self.app_page.update()

    def _cambiar_modo(self, nuevo_modo: str):
        self.modo = nuevo_modo
        # Ajustar valores sugeridos según modo
        if self.modo == "por_grupos":
            self.valor = min(4, max(1, self.total_alumnos))
        else:
            self.valor = 4 if self.total_alumnos >= 4 else max(1, self.total_alumnos)
        self.tf_valor.value = str(self.valor)
        self._actualizar_preview()
        self.content = self._build_content()
        if self.app_page:
            self.app_page.update()

    def _toggle_temas(self, e):
        self.sortear_temas = e.control.value
        self.content = self._build_content()
        if self.app_page:
            self.app_page.update()

    def _agregar_tema(self):
        val = (self.tf_nuevo_tema.value or "").strip()
        if val and val not in self.temas_lista:
            self.temas_lista.append(val)
            self.tf_nuevo_tema.value = ""
            self._refrescar_chips_temas()
            if self.app_page:
                self.app_page.update()

    def _eliminar_tema(self, tema: str):
        if tema in self.temas_lista:
            self.temas_lista.remove(tema)
            self._refrescar_chips_temas()
            if self.app_page:
                self.app_page.update()

    def _refrescar_chips_temas(self):
        chips = []
        for t in self.temas_lista:
            chips.append(
                ft.Container(
                    bgcolor="#F1F5F9",
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=16,
                    padding=ft.Padding(left=10, right=6, top=3, bottom=3),
                    content=ft.Row(
                        spacing=4,
                        tight=True,
                        controls=[
                            ft.Text(t, size=11, color=TEXT_MAIN),
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_size=13,
                                icon_color=TEXT_MUTED,
                                tooltip="Eliminar",
                                on_click=lambda _, item=t: self._eliminar_tema(item),
                            ),
                        ],
                    ),
                )
            )
        self.temas_wrap.controls = chips

    def _build_content(self) -> ft.Container:
        if self.total_alumnos == 0:
            return ft.Container(
                width=340,
                padding=12,
                content=ft.Column(
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                    controls=[
                        ft.Icon(ft.Icons.PERSON_OFF, size=36, color=TEXT_MUTED),
                        ft.Text(
                            "Este curso no tiene alumnos cargados.",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_MAIN,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Carga primero a los alumnos en la pestaña de Notas para poder realizar el sorteo.",
                            size=12,
                            color=TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            )

        is_por_grupos = (self.modo == "por_grupos")

        # Selector de modo compacto
        modo_tabs = ft.Container(
            bgcolor="#F1F5F9",
            border_radius=8,
            padding=3,
            content=ft.Row(
                spacing=4,
                controls=[
                    ft.Container(
                        expand=True,
                        height=32,
                        border_radius=6,
                        bgcolor=SURFACE_WHITE if is_por_grupos else ft.Colors.TRANSPARENT,
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                        on_click=lambda _: self._cambiar_modo("por_grupos"),
                        content=ft.Text(
                            "N° de Grupos",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=PRIMARY if is_por_grupos else TEXT_MUTED,
                        ),
                    ),
                    ft.Container(
                        expand=True,
                        height=32,
                        border_radius=6,
                        bgcolor=SURFACE_WHITE if not is_por_grupos else ft.Colors.TRANSPARENT,
                        alignment=ft.Alignment.CENTER,
                        ink=True,
                        on_click=lambda _: self._cambiar_modo("por_integrantes"),
                        content=ft.Text(
                            "Alumnos x Grupo",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=PRIMARY if not is_por_grupos else TEXT_MUTED,
                        ),
                    ),
                ],
            ),
        )

        # Control numérico
        stepper_label = "Cantidad de grupos a formar:" if is_por_grupos else "Alumnos por grupo deseados:"
        stepper_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(stepper_label, size=12, color=TEXT_MAIN, weight=ft.FontWeight.W_500),
                ft.Row(
                    spacing=4,
                    tight=True,
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.REMOVE,
                            icon_size=16,
                            icon_color=TEXT_MAIN,
                            on_click=lambda _: self._ajustar_valor(-1),
                        ),
                        self.tf_valor,
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            icon_size=16,
                            icon_color=TEXT_MAIN,
                            on_click=lambda _: self._ajustar_valor(1),
                        ),
                    ],
                ),
            ],
        )

        # Previsualización dinámica en caja Slate
        caja_preview = ft.Container(
            bgcolor="#F8FAFC",
            border=ft.Border.all(1, "#E2E8F0"),
            border_radius=8,
            padding=ft.Padding(left=10, right=10, top=8, bottom=8),
            content=self.preview_text,
        )

        # Sección de temas
        switch_temas = ft.Switch(
            label="Sortear con temas",
            value=self.sortear_temas,
            active_color=PRIMARY,
            on_change=self._toggle_temas,
        )

        seccion_temas_controls = [switch_temas]
        if self.sortear_temas:
            self._refrescar_chips_temas()
            seccion_temas_controls.extend([
                ft.Row(
                    spacing=6,
                    controls=[
                        self.tf_nuevo_tema,
                        ft.IconButton(
                            icon=ft.Icons.ADD_CIRCLE,
                            icon_color=PRIMARY,
                            icon_size=24,
                            tooltip="Añadir tema",
                            on_click=lambda _: self._agregar_tema(),
                        ),
                    ],
                ),
                ft.Text(
                    f"{len(self.temas_lista)} temas añadidos" if self.temas_lista else "Sin temas cargados aún.",
                    size=11,
                    color=TEXT_MUTED,
                ),
                self.temas_wrap,
            ])

        return ft.Container(
            width=340,
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[
                    self.tf_titulo,
                    modo_tabs,
                    stepper_row,
                    caja_preview,
                    ft.Divider(height=8, color=BORDER_COLOR),
                    *seccion_temas_controls,
                ],
            ),
        )

    def _cerrar(self):
        if self.app_page:
            self.app_page.pop_dialog()
            self.app_page.update()

    def _ejecutar_sorteo(self):
        if self.total_alumnos == 0:
            self._cerrar()
            return

        alumnos_ids = list(self.alumnos_dict.keys())
        grupos_generados = distribuir_alumnos_en_grupos(
            alumnos_ids=alumnos_ids,
            modo=self.modo,
            valor=self.valor,
            mezclar=True,
        )

        cant_grupos = len(grupos_generados)
        temas_asignados = (
            asignar_temas_a_grupos(cant_grupos, self.temas_lista, mezclar=True)
            if self.sortear_temas and self.temas_lista
            else ["" for _ in range(cant_grupos)]
        )

        grupos_data = []
        for i, integrantes in enumerate(grupos_generados):
            g_id = str(i + 1)
            tema_asignado = temas_asignados[i] if i < len(temas_asignados) else ""
            grupos_data.append({
                "id": g_id,
                "nombre": f"Grupo {g_id}",
                "integrantes": integrantes,
                "tema": tema_asignado,
                "nota": None,
                "observacion": "",
            })

        titulo = (self.tf_titulo.value or "Trabajo Grupal").strip()
        ok, msg, nuevo_trabajo = self.app_state.create_trabajo_grupo(
            titulo=titulo,
            grupos_data=grupos_data,
            temas=self.temas_lista if self.sortear_temas else [],
            con_temas=self.sortear_temas,
        )

        self._cerrar()
        if ok and nuevo_trabajo and self.on_created:
            self.on_created(nuevo_trabajo)


class ReasignarAlumnoDialog(ft.AlertDialog):
    """Diálogo para transferir un alumno a otro grupo o retirarlo."""

    def __init__(
        self,
        state: AppState,
        page: ft.Page,
        trabajo_id: str,
        alumno_id: str,
        alumno_nombre: str,
        grupo_origen_id: str,
        grupos: list[dict],
        on_moved: Callable[[], Any],
    ):
        self.app_state = state
        self.app_page = page
        self.trabajo_id = trabajo_id
        self.alumno_id = alumno_id
        self.grupo_origen_id = grupo_origen_id
        self.on_moved = on_moved

        opciones = []
        for g in grupos:
            gid = str(g.get("id"))
            gnom = g.get("nombre") or f"Grupo {gid}"
            if gid != grupo_origen_id:
                opciones.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.GROUP_ADD, color=PRIMARY, size=20),
                        title=ft.Text(f"Mover a {gnom}", size=13, weight=ft.FontWeight.W_500, color=TEXT_MAIN),
                        on_click=lambda _, target_id=gid: self._ejecutar_movimiento(target_id),
                    )
                )

        # Opción para dejar sin grupo
        opciones.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.PERSON_REMOVE, color="#EF4444", size=20),
                title=ft.Text("Retirar de grupos (dejar sin grupo)", size=13, color="#EF4444"),
                on_click=lambda _: self._ejecutar_movimiento("none"),
            )
        )

        super().__init__(
            modal=True,
            title=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.SWAP_HORIZ, color=PRIMARY, size=22),
                    ft.Column(
                        spacing=1,
                        controls=[
                            ft.Text("Reasignar Alumno", size=15, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                            ft.Text(alumno_nombre, size=12, color=TEXT_MUTED),
                        ],
                    ),
                ],
            ),
            content=ft.Container(
                width=320,
                content=ft.Column(
                    tight=True,
                    spacing=2,
                    controls=opciones,
                ),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: self._cerrar()),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

    def _cerrar(self):
        if self.app_page:
            self.app_page.pop_dialog()
            self.app_page.update()

    def _ejecutar_movimiento(self, target_gid: str):
        self.app_state.mover_alumno_grupo(
            trabajo_id=self.trabajo_id,
            alumno_id=self.alumno_id,
            grupo_destino_id=target_gid,
        )
        self._cerrar()
        if self.on_moved:
            self.on_moved()

"""
Vista de Trabajos en Grupo y Sorteador para Notaly Mobile.
Diseñada con Material Design 3, paleta Slate 50 / Indigo 600 y componentes reactivos in-place.
Permite gestionar múltiples trabajos grupales, sortear alumnos, asignar temas y calificar
con aislamiento estricto respecto a las notas individuales.
"""

from typing import Callable, Any
import flet as ft
from mobile.state import AppState
from mobile.components.ui_header import (
    build_app_header,
    build_module_tabs,
    build_save_status_indicator,
    SaveStatusIndicator,
)
from mobile.components.grupos_sorteador_dialog import (
    SorteadorGruposDialog,
    ReasignarAlumnoDialog,
)
from mobile.components.calificar_grupo_dialog import CalificarGrupoDialog
from mobile.theme import (
    BG_PAGE,
    SURFACE_WHITE,
    BORDER_COLOR,
    PRIMARY,
    PRIMARY_LIGHT,
    TEXT_MAIN,
    TEXT_MUTED,
    TEXT_SUBTLE,
    get_grade_tone,
    get_avatar_palette,
    extract_initials,
)
from core.grupos import formatear_resumen_grupos_texto


class GruposView(ft.Container):
    """Vista principal para la administración de grupos dentro de un curso."""

    def __init__(self, state: AppState, page: ft.Page, on_navigate: Callable[[str], Any]):
        super().__init__(expand=True, bgcolor=BG_PAGE)
        self.state = state
        self.app_page = page
        self.on_navigate = on_navigate
        self.padding = 0

        self.save_indicator = SaveStatusIndicator(status=self.state.save_status)
        self.state.on_save_status_change = self._on_save_status_change

        self.active_trabajo_id: str | None = None
        self.body_container = ft.Container(expand=True)
        self.lista_grupos_listview: ft.ListView | None = None

        self._build_ui()

    def _on_save_status_change(self, status: str):
        if hasattr(self, "save_indicator") and self.save_indicator:
            self.save_indicator.set_status(status)
            if hasattr(self, "app_page") and self.app_page:
                try:
                    self.app_page.update()
                except Exception:
                    pass

    def _build_ui(self):
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""

        # 1. Header principal
        header = build_app_header(
            eyebrow=colegio,
            title=curso,
            on_back=lambda: self.on_navigate("cursos"),
            status_indicator=self.save_indicator,
            trailing=ft.Row(
                spacing=4,
                tight=True,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.COPY_ALL,
                        tooltip="Copiar lista de grupos",
                        icon_color=PRIMARY,
                        icon_size=20,
                        on_click=lambda _: self._copiar_al_portapapeles(),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CASINO,
                        tooltip="Sortear nuevos grupos",
                        icon_color=PRIMARY,
                        icon_size=20,
                        on_click=lambda _: self._abrir_sorteador(),
                    ),
                ],
            ),
        )

        # 2. Selector tri-modular (Notas / Asistencia / Grupos)
        module_tabs = ft.Container(
            padding=ft.Padding(left=16, right=16, top=6, bottom=4),
            content=build_module_tabs(active_tab="grupos", on_change=lambda dest: self.on_navigate(dest)),
        )

        self._actualizar_contenido_body()

        self.content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                module_tabs,
                self.body_container,
            ],
        )

    def _actualizar_contenido_body(self):
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        trabajos = self.state.get_trabajos_grupo_curso(colegio, curso)

        if not trabajos:
            self.active_trabajo_id = None
            self.body_container.content = self._build_empty_state()
            return

        # Si el trabajo activo no existe o es None, seleccionar el último
        ids_existentes = [str(t.get("id")) for t in trabajos if isinstance(t, dict)]
        if not self.active_trabajo_id or self.active_trabajo_id not in ids_existentes:
            self.active_trabajo_id = ids_existentes[-1]

        trabajo_actual = self.state.get_trabajo_grupo(self.active_trabajo_id, colegio, curso)
        if not trabajo_actual:
            self.body_container.content = self._build_empty_state()
            return

        # Selector horizontal de trabajos prácticos si hay más de 1 o para añadir nuevos
        selector_trabajos = self._build_selector_trabajos(trabajos)

        # Barra de detalle y acciones del trabajo activo
        barra_acciones = self._build_barra_trabajo_activo(trabajo_actual)

        # Lista de tarjetas de grupo con ListView para scroll suave
        self.lista_grupos_listview = ft.ListView(
            expand=True,
            spacing=10,
            padding=ft.Padding(left=16, right=16, top=4, bottom=20),
            controls=self._build_tarjetas_grupos(trabajo_actual),
        )

        self.body_container.content = ft.Column(
            expand=True,
            spacing=4,
            controls=[
                selector_trabajos,
                barra_acciones,
                self.lista_grupos_listview,
            ],
        )

    def _build_selector_trabajos(self, trabajos: list[dict]) -> ft.Container:
        chips = []
        for t in trabajos:
            t_id = str(t.get("id"))
            is_active = (t_id == self.active_trabajo_id)
            tit = t.get("titulo") or "Trabajo Grupal"
            chips.append(
                ft.Container(
                    height=32,
                    padding=ft.Padding(left=12, right=12, top=4, bottom=4),
                    border_radius=16,
                    bgcolor=PRIMARY if is_active else "#F1F5F9",
                    border=ft.Border.all(1, PRIMARY if is_active else BORDER_COLOR),
                    alignment=ft.Alignment.CENTER,
                    ink=True,
                    on_click=lambda _, tid=t_id: self._seleccionar_trabajo(tid),
                    content=ft.Text(
                        tit,
                        size=11,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                        color=ft.Colors.WHITE if is_active else TEXT_MAIN,
                    ),
                )
            )

        # Botón para añadir nuevo trabajo
        chips.append(
            ft.Container(
                height=32,
                padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                border_radius=16,
                bgcolor="#EFF6FF",
                border=ft.Border.all(1, "#BFDBFE"),
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda _: self._abrir_sorteador(),
                content=ft.Row(
                    spacing=2,
                    tight=True,
                    controls=[
                        ft.Icon(ft.Icons.ADD, size=14, color=PRIMARY),
                        ft.Text("Nuevo Trabajo", size=11, weight=ft.FontWeight.BOLD, color=PRIMARY),
                    ],
                ),
            )
        )

        return ft.Container(
            padding=ft.Padding(left=16, right=16, top=2, bottom=4),
            content=ft.Row(
                scroll=ft.ScrollMode.ADAPTIVE,
                spacing=6,
                controls=chips,
            ),
        )

    def _build_barra_trabajo_activo(self, trabajo: dict) -> ft.Container:
        grupos = trabajo.get("grupos") or []
        cant_grupos = len(grupos)
        cant_alumnos = sum(len(g.get("integrantes") or []) for g in grupos if isinstance(g, dict))

        return ft.Container(
            padding=ft.Padding(left=16, right=16, top=4, bottom=6),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=6,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.GROUPS, size=16, color=PRIMARY),
                            ft.Text(
                                f"{cant_grupos} grupos • {cant_alumnos} integrantes",
                                size=12,
                                weight=ft.FontWeight.W_500,
                                color=TEXT_MUTED,
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=4,
                        tight=True,
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.ADD_CARD,
                                tooltip="Agregar grupo manual",
                                icon_size=18,
                                icon_color=PRIMARY,
                                on_click=lambda _: self._agregar_grupo_manual(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Eliminar este trabajo",
                                icon_size=18,
                                icon_color="#EF4444",
                                on_click=lambda _: self._confirmar_eliminar_trabajo(),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _build_tarjetas_grupos(self, trabajo: dict) -> list[ft.Control]:
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos_dict = self.state.get_alumnos(colegio, curso)
        grupos = trabajo.get("grupos") or []
        trabajo_id = str(trabajo.get("id"))

        tarjetas = []
        for g in grupos:
            if not isinstance(g, dict):
                continue
            gid = str(g.get("id"))
            gnom = g.get("nombre") or f"Grupo {gid}"
            tema = (g.get("tema") or "").strip()
            nota = g.get("nota")
            obs = (g.get("observacion") or "").strip()
            integrantes = g.get("integrantes") or []

            # 1. Píldora de Calificación
            if nota is not None and str(nota).strip() != "":
                bg_tone, fg_tone = get_grade_tone(nota)
                nota_widget = ft.Container(
                    bgcolor=bg_tone,
                    border=ft.Border.all(1, fg_tone),
                    border_radius=8,
                    padding=ft.Padding(left=8, right=8, top=2, bottom=2),
                    ink=True,
                    on_click=lambda _, grp=g: self._abrir_calificar_grupo(trabajo_id, grp),
                    content=ft.Row(
                        spacing=3,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.STAR, size=13, color=fg_tone),
                            ft.Text(f"Nota: {nota}", size=11, weight=ft.FontWeight.BOLD, color=fg_tone),
                        ],
                    ),
                )
            else:
                nota_widget = ft.Container(
                    bgcolor="#F8FAFC",
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=8,
                    padding=ft.Padding(left=8, right=8, top=2, bottom=2),
                    ink=True,
                    on_click=lambda _, grp=g: self._abrir_calificar_grupo(trabajo_id, grp),
                    content=ft.Row(
                        spacing=3,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.GRADE, size=13, color=TEXT_MUTED),
                            ft.Text("+ Calificar", size=11, weight=ft.FontWeight.W_500, color=TEXT_MUTED),
                        ],
                    ),
                )

            # 2. Píldora de Tema
            if tema:
                tema_widget = ft.Container(
                    bgcolor="#EEF2FF",
                    border=ft.Border.all(1, "#C7D2FE"),
                    border_radius=6,
                    padding=ft.Padding(left=6, right=6, top=1, bottom=1),
                    ink=True,
                    on_click=lambda _, grp=g: self._editar_tema_grupo(trabajo_id, grp),
                    content=ft.Row(
                        spacing=3,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.MENU_BOOK, size=12, color=PRIMARY),
                            ft.Text(tema, size=10, weight=ft.FontWeight.BOLD, color=PRIMARY),
                        ],
                    ),
                )
            else:
                tema_widget = ft.Container(
                    bgcolor="#F8FAFC",
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=6,
                    padding=ft.Padding(left=6, right=6, top=1, bottom=1),
                    ink=True,
                    on_click=lambda _, grp=g: self._editar_tema_grupo(trabajo_id, grp),
                    content=ft.Row(
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Icon(ft.Icons.ADD, size=11, color=TEXT_MUTED),
                            ft.Text("Tema", size=10, color=TEXT_MUTED),
                        ],
                    ),
                )

            # 3. Lista de alumnos integrantes
            filas_alumnos = []
            if not integrantes:
                filas_alumnos.append(
                    ft.Text("Sin alumnos asignados a este grupo.", size=12, color=TEXT_MUTED, italic=True)
                )
            else:
                for al_id in integrantes:
                    al_data = alumnos_dict.get(str(al_id), {})
                    nom_al = al_data.get("nombre") or f"Alumno #{al_id}"
                    bg_av, fg_av = get_avatar_palette(str(al_id))
                    initials = extract_initials(nom_al)

                    filas_alumnos.append(
                        ft.Container(
                            padding=ft.Padding(left=4, right=4, top=3, bottom=3),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        tight=True,
                                        controls=[
                                            ft.Container(
                                                width=26,
                                                height=26,
                                                border_radius=13,
                                                bgcolor=bg_av,
                                                alignment=ft.Alignment.CENTER,
                                                content=ft.Text(
                                                    initials,
                                                    size=10,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=fg_av,
                                                ),
                                            ),
                                            ft.Text(nom_al, size=12, weight=ft.FontWeight.W_500, color=TEXT_MAIN),
                                        ],
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.SWAP_HORIZ,
                                        icon_size=16,
                                        icon_color=TEXT_MUTED,
                                        tooltip="Reasignar a otro grupo",
                                        on_click=lambda _, a_id=str(al_id), a_nom=nom_al, o_gid=gid: self._abrir_reasignar_alumno(
                                            trabajo_id, a_id, a_nom, o_gid, grupos
                                        ),
                                    ),
                                ],
                            ),
                        )
                    )

            # 4. Sección de observación
            obs_controls = []
            if obs:
                obs_controls.append(
                    ft.Container(
                        bgcolor="#F8FAFC",
                        border=ft.Border.all(1, "#E2E8F0"),
                        border_radius=6,
                        padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                        content=ft.Row(
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Icon(ft.Icons.RATE_REVIEW_OUTLINED, size=14, color=TEXT_MUTED),
                                ft.Text(obs, size=11, color=TEXT_MAIN, expand=True),
                            ],
                        ),
                    )
                )

            # 5. Tarjeta completa
            tarjetas.append(
                ft.Container(
                    bgcolor=SURFACE_WHITE,
                    border=ft.Border.all(1, BORDER_COLOR),
                    border_radius=12,
                    padding=12,
                    content=ft.Column(
                        spacing=8,
                        tight=True,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        tight=True,
                                        controls=[
                                            ft.Icon(ft.Icons.GROUP, size=16, color=PRIMARY),
                                            ft.Text(gnom, size=14, weight=ft.FontWeight.BOLD, color=TEXT_MAIN),
                                            tema_widget,
                                        ],
                                    ),
                                    nota_widget,
                                ],
                            ),
                            ft.Divider(height=1, color=BORDER_COLOR),
                            ft.Column(spacing=2, controls=filas_alumnos),
                            *obs_controls,
                        ],
                    ),
                )
            )

        return tarjetas

    def _build_empty_state(self) -> ft.Container:
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        alumnos = self.state.get_alumnos(colegio, curso)
        cant_alumnos = len(alumnos)

        return ft.Container(
            expand=True,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding(left=24, right=24, top=16, bottom=16),
            content=ft.Container(
                bgcolor=SURFACE_WHITE,
                border=ft.Border.all(1, BORDER_COLOR),
                border_radius=16,
                padding=24,
                width=360,
                content=ft.Column(
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                    controls=[
                        ft.Container(
                            width=64,
                            height=64,
                            border_radius=32,
                            bgcolor="#EEF2FF",
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.GROUPS_OUTLINED, size=34, color=PRIMARY),
                        ),
                        ft.Text(
                            "Aún no hay grupos creados",
                            size=17,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_MAIN,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Organiza a los alumnos en equipos para trabajos prácticos, exposiciones y debates con sorteo automático y asignación de temas.",
                            size=12,
                            color=TEXT_MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(
                            bgcolor="#F1F5F9",
                            border_radius=12,
                            padding=ft.Padding(left=10, right=10, top=4, bottom=4),
                            content=ft.Text(
                                f"{cant_alumnos} alumnos listos en el curso"
                                if cant_alumnos > 0
                                else "Sin alumnos cargados en el curso",
                                size=11,
                                weight=ft.FontWeight.W_500,
                                color=PRIMARY if cant_alumnos > 0 else "#EF4444",
                            ),
                        ),
                        ft.FilledButton(
                            "Crear y Sortear Grupos",
                            icon=ft.Icons.CASINO,
                            style=ft.ButtonStyle(
                                bgcolor=PRIMARY,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                            on_click=lambda _: self._abrir_sorteador(),
                        ),
                    ],
                ),
            ),
        )

    def _seleccionar_trabajo(self, trabajo_id: str):
        self.active_trabajo_id = trabajo_id
        self._actualizar_contenido_body()
        if self.app_page:
            self.app_page.update()

    def _abrir_sorteador(self):
        def on_created(nuevo_trabajo: dict):
            self.active_trabajo_id = str(nuevo_trabajo.get("id"))
            self._actualizar_contenido_body()
            if self.app_page:
                self.app_page.update()

        dlg = SorteadorGruposDialog(self.state, self.app_page, on_created=on_created)
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_calificar_grupo(self, trabajo_id: str, grupo: dict):
        def on_saved():
            self._actualizar_contenido_body()
            if self.app_page:
                self.app_page.update()

        dlg = CalificarGrupoDialog(self.state, self.app_page, trabajo_id, grupo, on_saved=on_saved)
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _abrir_reasignar_alumno(
        self,
        trabajo_id: str,
        alumno_id: str,
        alumno_nombre: str,
        grupo_origen_id: str,
        grupos: list[dict],
    ):
        def on_moved():
            self._actualizar_contenido_body()
            if self.app_page:
                self.app_page.update()

        dlg = ReasignarAlumnoDialog(
            state=self.state,
            page=self.app_page,
            trabajo_id=trabajo_id,
            alumno_id=alumno_id,
            alumno_nombre=alumno_nombre,
            grupo_origen_id=grupo_origen_id,
            grupos=grupos,
            on_moved=on_moved,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _editar_tema_grupo(self, trabajo_id: str, grupo: dict):
        tf_tema = ft.TextField(
            label="Tema asignado",
            value=grupo.get("tema") or "",
            border_radius=8,
            border_color=BORDER_COLOR,
            text_size=13,
            color=TEXT_MAIN,
        )

        def guardar_tema(_):
            self.state.update_grupo_trabajo(
                trabajo_id=trabajo_id,
                grupo_id=str(grupo.get("id")),
                tema=tf_tema.value or "",
            )
            self.app_page.pop_dialog()
            self._actualizar_contenido_body()
            self.app_page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Tema de {grupo.get('nombre')}", size=15, weight=ft.FontWeight.BOLD),
            content=ft.Container(width=300, content=tf_tema),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: (self.app_page.pop_dialog(), self.app_page.update())),
                ft.FilledButton("Guardar", style=ft.ButtonStyle(bgcolor=PRIMARY), on_click=guardar_tema),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _agregar_grupo_manual(self):
        if not self.active_trabajo_id:
            return
        ok, msg, _ = self.state.add_grupo_a_trabajo(self.active_trabajo_id)
        if ok:
            self._actualizar_contenido_body()
            if self.app_page:
                self.app_page.update()

    def _confirmar_eliminar_trabajo(self):
        if not self.active_trabajo_id:
            return

        def eliminar(_):
            self.state.delete_trabajo_grupo(self.active_trabajo_id)
            self.app_page.pop_dialog()
            self.active_trabajo_id = None
            self._actualizar_contenido_body()
            self.app_page.update()

        dlg = ft.AlertDialog(
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#EF4444", size=24),
                    ft.Text("Eliminar Trabajo", size=16, weight=ft.FontWeight.BOLD),
                ],
            ),
            content=ft.Text("¿Estás seguro de que deseas eliminar este trabajo en grupo? Esta acción no se puede deshacer.", size=13),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: (self.app_page.pop_dialog(), self.app_page.update())),
                ft.FilledButton("Eliminar", style=ft.ButtonStyle(bgcolor="#EF4444", color=ft.Colors.WHITE), on_click=eliminar),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.app_page.show_dialog(dlg)
        self.app_page.update()

    def _mostrar_snackbar(self, mensaje: str, error: bool = False):
        if not self.app_page:
            return
        if hasattr(self.app_page, "show_snack_bar") and callable(self.app_page.show_snack_bar):
            self.app_page.show_snack_bar(ft.SnackBar(ft.Text(mensaje)))
            return

        sb = ft.SnackBar(
            content=ft.Text(mensaje, color=ft.Colors.WHITE),
            bgcolor=ft.Colors.ERROR if error else ft.Colors.GREEN_700,
        )
        if hasattr(self.app_page, "overlay") and hasattr(self.app_page.overlay, "append"):
            self.app_page.overlay.append(sb)
            sb.open = True
            self.app_page.update()

    def _copiar_texto_al_portapapeles(self, texto: str) -> bool:
        copiado = False

        # 1. Servicio oficial de portapapeles Flet (Android, Desktop, Web)
        try:
            if self.app_page and hasattr(ft, "Clipboard"):
                cb = getattr(self.app_page, "_clipboard_service", None)
                if not cb:
                    cb = ft.Clipboard()
                    if hasattr(self.app_page, "services") and isinstance(self.app_page.services, list):
                        self.app_page.services.append(cb)
                    self.app_page._clipboard_service = cb
                if hasattr(self.app_page, "run_task"):
                    self.app_page.run_task(cb.set, texto)
                    copiado = True
        except Exception:
            pass

        # 2. Soporte para mocks en pruebas unitarias o clientes con set_clipboard
        if self.app_page and hasattr(self.app_page, "set_clipboard") and callable(self.app_page.set_clipboard):
            self.app_page.set_clipboard(texto)
            copiado = True

        return copiado

    def _copiar_al_portapapeles(self):
        colegio = self.state.selected_colegio or ""
        curso = self.state.selected_curso or ""
        trabajo = self.state.get_trabajo_grupo(self.active_trabajo_id, colegio, curso)
        if not trabajo:
            self._mostrar_snackbar("No hay ningún trabajo en grupo seleccionado.", error=True)
            return

        alumnos_dict = self.state.get_alumnos(colegio, curso)
        alumnos_nombres = {
            str(k): v.get("nombre") or f"Alumno #{k}"
            for k, v in alumnos_dict.items()
        }

        texto = formatear_resumen_grupos_texto(
            trabajo_titulo=trabajo.get("titulo") or "Trabajo Grupal",
            grupos=trabajo.get("grupos") or [],
            alumnos_nombres=alumnos_nombres,
        )

        copiado = self._copiar_texto_al_portapapeles(texto)
        if copiado:
            self._mostrar_snackbar("📋 Formación de grupos copiada al portapapeles.")
        else:
            self._mostrar_snackbar("Error al copiar al portapapeles.", error=True)


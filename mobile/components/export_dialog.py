"""
Hoja modal editorial de exportación de planillas de Notas o Asistencias (SPEC-028).

Migra `ExportDialog` a `NotalySheet` adaptativo sin altura fija ni grupos de radio
M3, utilizando filas seleccionables `EditorialRadioList` (`NotalyListRow`), aviso
completo con tríada `warn_*`, colapso de selectores de fechas cuando "Todas las
fechas" está activo y paleta dual completa (RF-05, RF-07, RF-21, RF-23).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

import flet as ft

from core import gestor_planillas
from core.calculos import (
    obtener_estadisticas_asistencia_curso,
    ordenar_fechas_cronologicamente,
)
from core.constants import (
    K_ALUMNOS,
    K_ASISTENCIAS,
    K_PERIODOS_INTENSIFICACION,
    K_REGIMEN,
    REGIMEN_CUATRIMESTRAL,
    REGIMEN_TRIMESTRAL,
    normalizar_regimen,
    obtener_etiqueta_periodo_por_indice,
)
from core.intensificacion import tiene_datos_intensificacion_curso
from core.exportador import (
    exportar_a_csv,
    exportar_a_pdf,
    exportar_a_texto,
    exportar_asistencias_a_csv,
    exportar_asistencias_a_pdf,
    exportar_asistencias_a_texto,
    exportar_estadisticas_asistencia_a_pdf,
    generar_texto_notas_whatsapp,
)
from mobile.components.ledger_primitives import EditorialRadioList
from mobile.components.notaly_sheet import NotalySheet, sheet_action_button
from mobile.components.share_helper import compartir_archivo
from mobile.theme import (
    RADIUS_SM,
    SPACE_MD,
    SPACE_SM,
    ThemeTokens,
    resolve_tokens,
)

logger = logging.getLogger(__name__)


class ExportDialog(NotalySheet):
    """Hoja modal adaptativa para seleccionar formato y exportar planillas."""

    def __init__(
        self,
        tipo_exportacion: str = "notas",
        colegio_nombre: str = "",
        curso_nombre: str = "",
        curso_data: dict | None = None,
        on_success: Callable[..., Any] | None = None,
        page: ft.Page | None = None,
        periodo_activo: int = 0,
        tokens: ThemeTokens | None = None,
        **kwargs: Any,
    ) -> None:
        self.tipo_exportacion = tipo_exportacion
        self.colegio_nombre = colegio_nombre
        self.curso_nombre = curso_nombre
        self.curso_data = curso_data or {}
        self.on_success = on_success or kwargs.get("on_exportar")
        self.app_page = page
        self.state = kwargs.get("state")
        self.tokens = resolve_tokens(tokens=tokens, page=page, state=self.state)
        tok = self.tokens
        self.periodo_activo = int(periodo_activo) if str(periodo_activo).isdigit() else 0
        self._user_on_dismiss = kwargs.get("on_dismiss")
        if self.state is not None and hasattr(self.state, "get_regimen_colegio"):
            self.regimen = normalizar_regimen(
                self.state.get_regimen_colegio(self.colegio_nombre)
            )
        else:
            self.regimen = normalizar_regimen(
                kwargs.get("regimen", self.curso_data.get(K_REGIMEN))
            )

        opciones_formato: list[tuple[str, str, str | None]] = [
            ("pdf", "Documento PDF (.pdf)", "Lista formateada para impresión"),
            ("csv", "Hoja de cálculo (.csv)", "Compatible con Excel / LibreOffice"),
            ("txt", "Texto plano (.txt)", "Lectura universal compacta"),
        ]
        if tipo_exportacion == "notas":
            opciones_formato.append(
                ("whatsapp", "Texto para WhatsApp", "Resumen listo para compartir")
            )

        self.formato_selector = EditorialRadioList(
            options=opciones_formato,
            value="pdf",
            on_change=self._al_cambiar_formato,
            tokens=tok,
        )

        # --- Selector de tipo de reporte para asistencias ---
        if tipo_exportacion == "asistencias":
            self.tipo_reporte_asistencias = EditorialRadioList(
                options=[
                    ("detallada", "Planilla detallada con fechas", None),
                    ("estadistica", "Resumen estadístico (KPIs y nómina)", None),
                ],
                value="detallada",
                on_change=self._al_cambiar_tipo_reporte_asistencias,
                tokens=tok,
            )
        else:
            self.tipo_reporte_asistencias = None

        # --- Controles específicos de PDF ---
        label_recomendado = (
            "Por páginas (15 por hoja)"
            if tipo_exportacion == "notas"
            else "Por páginas (10 por hoja)"
        )
        self.modo_pdf_selector = EditorialRadioList(
            options=[
                ("paginado", label_recomendado, "Lectura óptima recomendada"),
                ("una_pagina", "Una sola página", "Ajuste compacto continuo"),
            ],
            value="paginado",
            on_change=self._al_cambiar_modo_pdf,
            tokens=tok,
        )

        self.banner_advertencia = ft.Container(
            visible=False,
            bgcolor=tok.warn_bg,
            border=ft.Border.all(1, tok.warn_border),
            border_radius=RADIUS_SM,
            padding=SPACE_SM,
            content=ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        icon=ft.Icons.WARNING_AMBER_ROUNDED,
                        size=18,
                        color=tok.warn_fg,
                    ),
                    ft.Text(
                        "En listas largas el texto puede reducirse para caber en una sola hoja.",
                        size=12,
                        color=tok.warn_fg,
                        expand=True,
                    ),
                ],
            ),
        )

        self.modo_pdf_header = ft.Text(
            "Modo de paginación PDF",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=tok.text_secondary,
        )

        pdf_controls: list[ft.Control] = []
        if self.tipo_reporte_asistencias is not None:
            pdf_controls.extend(
                [
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    ft.Text(
                        "Tipo de reporte",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_secondary,
                    ),
                    self.tipo_reporte_asistencias,
                ]
            )

        pdf_controls.extend(
            [
                ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                self.modo_pdf_header,
                self.modo_pdf_selector,
                self.banner_advertencia,
            ]
        )

        if tipo_exportacion == "asistencias":
            fechas_raw = list(self.curso_data.get(K_ASISTENCIAS, {}).keys())
            fechas_ordenadas = ordenar_fechas_cronologicamente(fechas_raw)

            self.chk_todas_fechas = ft.Checkbox(
                label="Todas las fechas",
                value=True,
                active_color=tok.accent_primary,
                check_color=tok.accent_on_primary,
                on_change=self._al_cambiar_todas_fechas,
            )

            opciones_fechas = [ft.dropdown.Option(f) for f in fechas_ordenadas]
            val_desde = fechas_ordenadas[0] if fechas_ordenadas else None
            val_hasta = fechas_ordenadas[-1] if fechas_ordenadas else None

            self.dd_desde = ft.Dropdown(
                label="Desde",
                options=opciones_fechas,
                value=val_desde,
                disabled=True,
                expand=True,
                border_radius=RADIUS_SM,
                border_color=tok.border_hairline,
                focused_border_color=tok.accent_primary,
                color=tok.text_primary,
                content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=4),
            )
            self.dd_hasta = ft.Dropdown(
                label="Hasta",
                options=opciones_fechas,
                value=val_hasta,
                disabled=True,
                expand=True,
                border_radius=RADIUS_SM,
                border_color=tok.border_hairline,
                focused_border_color=tok.accent_primary,
                color=tok.text_primary,
                content_padding=ft.Padding.symmetric(horizontal=SPACE_SM, vertical=4),
            )

            self.fechas_row = ft.Row(
                [self.dd_desde, self.dd_hasta],
                spacing=SPACE_SM,
                visible=False,
            )
            pdf_controls.extend(
                [
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    ft.Text(
                        "Rango de fechas",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_secondary,
                    ),
                    self.chk_todas_fechas,
                    self.fechas_row,
                ]
            )
        else:
            self.chk_todas_fechas = None
            self.dd_desde = None
            self.dd_hasta = None
            self.fechas_row = None

        # --- Anexo opcional de Período de Intensificación (solo PDF de Notas si hay datos) ---
        self.chk_incluir_intensificacion: ft.Checkbox | None = None
        self.intensif_periodos_container: ft.Container | None = None
        self.intensif_periodos_checks: dict[str, ft.Checkbox] = {}
        if tipo_exportacion == "notas" and tiene_datos_intensificacion_curso(self.curso_data):
            periodos_int = [
                p
                for p in (self.curso_data.get(K_PERIODOS_INTENSIFICACION, []) or [])
                if isinstance(p, dict)
            ]
            self.chk_incluir_intensificacion = ft.Checkbox(
                label="Añadir período de intensificación",
                value=False,
                active_color=tok.accent_primary,
                check_color=tok.accent_on_primary,
                on_change=self._al_cambiar_incluir_intensificacion,
            )
            checks_ctrl: list[ft.Control] = []
            for per in periodos_int:
                pid = str(per.get("id", ""))
                pnom = str(per.get("nombre") or "Período")
                chk_p = ft.Checkbox(
                    label=pnom,
                    value=True,
                    active_color=tok.accent_primary,
                    check_color=tok.accent_on_primary,
                )
                self.intensif_periodos_checks[pid] = chk_p
                checks_ctrl.append(chk_p)

            self.intensif_periodos_container = ft.Container(
                visible=False,
                padding=ft.Padding(left=SPACE_MD, top=0, right=0, bottom=0),
                content=ft.Column(checks_ctrl, spacing=2, tight=True),
            )
            pdf_controls.extend(
                [
                    ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                    ft.Text(
                        "Anexo de Intensificación",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=tok.text_secondary,
                    ),
                    self.chk_incluir_intensificacion,
                    self.intensif_periodos_container,
                ]
            )

        self.pdf_opciones_container = ft.Container(
            visible=True,
            content=ft.Column(pdf_controls, spacing=SPACE_SM, tight=True),
            padding=ft.Padding(top=4, bottom=4, left=0, right=0),
        )

        self.periodo_container: ft.Container | None = None
        if tipo_exportacion == "notas":
            if self.regimen == REGIMEN_CUATRIMESTRAL:
                opciones_per = [
                    ("0", "1° Cuatrimestre", None),
                    ("1", "2° Cuatrimestre", None),
                    ("3", "Resumen Anual", None),
                ]
                periodo_val_inicial = (
                    "0"
                    if self.periodo_activo == 2
                    else str(min(3, max(0, self.periodo_activo)))
                )
            else:
                opciones_per = [
                    ("0", "1° Trimestre", None),
                    ("1", "2° Trimestre", None),
                    ("2", "3° Trimestre", None),
                    ("3", "Resumen Anual", None),
                ]
                periodo_val_inicial = str(min(3, max(0, self.periodo_activo)))
            self.periodo_selector = EditorialRadioList(
                options=opciones_per,
                value=periodo_val_inicial,
                tokens=tok,
            )
            self.periodo_container = ft.Container(
                visible=False,
                content=ft.Column(
                    [
                        ft.Divider(height=1, thickness=1, color=tok.border_hairline),
                        ft.Text(
                            "Período a copiar",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=tok.text_secondary,
                        ),
                        self.periodo_selector,
                    ],
                    spacing=SPACE_SM,
                    tight=True,
                ),
                padding=ft.Padding(top=4, bottom=4, left=0, right=0),
            )

        context_box = ft.Container(
            bgcolor=tok.surface_subtle,
            border=ft.Border.all(1, tok.border_hairline),
            border_radius=RADIUS_SM,
            padding=SPACE_MD,
            content=ft.Row(
                spacing=SPACE_SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(
                        icon=ft.Icons.CLASS_OUTLINED,
                        size=20,
                        color=tok.accent_primary,
                    ),
                    ft.Column(
                        spacing=2,
                        tight=True,
                        expand=True,
                        controls=[
                            ft.Text(
                                colegio_nombre,
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color=tok.text_primary,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                curso_nombre,
                                size=12,
                                color=tok.text_secondary,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                ],
            ),
        )

        body_controls: list[ft.Control] = [
            context_box,
            ft.Text(
                "Formato de exportación",
                size=12,
                weight=ft.FontWeight.BOLD,
                color=tok.text_secondary,
            ),
            self.formato_selector,
            self.pdf_opciones_container,
        ]
        if self.periodo_container:
            body_controls.append(self.periodo_container)

        self.btn_exportar = sheet_action_button(
            "Generar y Exportar",
            lambda _e: self._exportar(),
            tokens=tok,
            primary=True,
            icon=ft.Icons.DOWNLOAD,
            expand=True,
        )
        btn_cancelar = sheet_action_button(
            "Cancelar",
            lambda _e: self._cerrar(),
            tokens=tok,
            primary=False,
            expand=True,
        )

        titulo_str = (
            "Exportar Planilla de Notas"
            if tipo_exportacion == "notas"
            else "Exportar Asistencias"
        )

        super().__init__(
            page=page,
            title=titulo_str,
            body=body_controls,
            actions=[btn_cancelar, self.btn_exportar],
            tokens=tok,
            state=self.state,
            on_dismiss=self._on_internal_dismiss,
        )
        # Alias esperado por tests responsivos y de exportación
        self.content_col = self.body_column

    def _safe_update(self) -> None:
        try:
            if self.page is not None:
                self.update()
        except Exception:
            pass

    def _on_internal_dismiss(self, e: Any = None) -> None:
        if callable(self._user_on_dismiss):
            self._user_on_dismiss(e)

    def _al_cambiar_tipo_reporte_asistencias(self, _e: Any) -> None:
        es_est = bool(
            self.tipo_reporte_asistencias
            and self.tipo_reporte_asistencias.value == "estadistica"
        )
        if self.modo_pdf_header:
            self.modo_pdf_header.visible = not es_est
        if self.modo_pdf_selector:
            self.modo_pdf_selector.visible = not es_est
        if self.banner_advertencia:
            self.banner_advertencia.visible = (not es_est) and (
                self.modo_pdf_selector.value == "una_pagina"
            )
        self._safe_update()

    def _al_cambiar_modo_pdf(self, _e: Any) -> None:
        self.banner_advertencia.visible = self.modo_pdf_selector.value == "una_pagina"
        self._safe_update()

    def _al_cambiar_incluir_intensificacion(self, _e: Any) -> None:
        if self.intensif_periodos_container is not None and self.chk_incluir_intensificacion is not None:
            self.intensif_periodos_container.visible = bool(self.chk_incluir_intensificacion.value)
        self._safe_update()

    def _al_cambiar_todas_fechas(self, _e: Any) -> None:
        todas = bool(self.chk_todas_fechas.value)
        if self.dd_desde:
            self.dd_desde.disabled = todas
        if self.dd_hasta:
            self.dd_hasta.disabled = todas
        if self.fechas_row is not None:
            self.fechas_row.visible = not todas
        self._safe_update()

    def _al_cambiar_formato(self, _e: Any) -> None:
        formato = self.formato_selector.value
        es_wa = formato == "whatsapp"
        es_pdf = formato == "pdf"

        if self.periodo_container:
            self.periodo_container.visible = es_wa
        self.pdf_opciones_container.visible = es_pdf

        if es_wa:
            if isinstance(self.btn_exportar.content, ft.Text):
                self.btn_exportar.content.value = "Copiar al Portapapeles"
            self.btn_exportar.icon = ft.Icons.COPY_ALL
        else:
            if isinstance(self.btn_exportar.content, ft.Text):
                self.btn_exportar.content.value = "Generar y Exportar"
            self.btn_exportar.icon = ft.Icons.DOWNLOAD
        self._safe_update()

    def _cerrar(self) -> None:
        self.close()
        self._on_internal_dismiss(None)

    def _obtener_carpeta_exportacion(self) -> Path:
        return gestor_planillas.obtener_directorio_exportaciones()

    def _intentar_compartir(self, ruta_str: str, nombre_archivo: str) -> None:
        if self.app_page:
            compartir_archivo(
                self.app_page,
                ruta_str,
                texto=f"Reporte de {self.curso_nombre}: {nombre_archivo}",
            )

    def _copiar_texto_al_portapapeles(self, texto: str) -> bool:
        copiado = False
        try:
            if self.app_page and hasattr(ft, "Clipboard"):
                cb = getattr(self.app_page, "_clipboard_service", None)
                if not cb:
                    cb = ft.Clipboard()
                    if hasattr(self.app_page, "services") and isinstance(
                        self.app_page.services, list
                    ):
                        self.app_page.services.append(cb)
                    self.app_page._clipboard_service = cb
                if hasattr(self.app_page, "run_task"):
                    self.app_page.run_task(cb.set, texto)
                    copiado = True
        except Exception:
            pass

        if (
            self.app_page
            and hasattr(self.app_page, "set_clipboard")
            and callable(self.app_page.set_clipboard)
        ):
            self.app_page.set_clipboard(texto)
            copiado = True

        return copiado

    def _exportar(self) -> None:
        alumnos = self.curso_data.get(K_ALUMNOS, {})
        if not alumnos:
            self._cerrar()
            if self.on_success:
                self.on_success(False, "El curso no tiene alumnos registrados.")
            return

        formato = self.formato_selector.value or "pdf"
        if formato == "whatsapp":
            try:
                periodo_val = (
                    self.periodo_selector.value
                    if hasattr(self, "periodo_selector") and self.periodo_selector
                    else "0"
                )
                try:
                    p_num = int(str(periodo_val))
                    nombre_periodo = obtener_etiqueta_periodo_por_indice(p_num, self.regimen)
                except (ValueError, TypeError):
                    nombre_periodo = "el período seleccionado"

                kwargs_reg = (
                    {"regimen": self.regimen}
                    if self.regimen != REGIMEN_TRIMESTRAL
                    else {}
                )
                texto = generar_texto_notas_whatsapp(
                    curso_data=self.curso_data,
                    periodo=periodo_val,
                    nombre_curso=self.curso_nombre,
                    nombre_colegio=self.colegio_nombre,
                    **kwargs_reg,
                )

                copiado = self._copiar_texto_al_portapapeles(texto)
                self._cerrar()

                if self.on_success:
                    if copiado:
                        self.on_success(True, "portapapeles", nombre_periodo)
                    else:
                        self.on_success(
                            False, "No se pudo acceder al servicio de portapapeles."
                        )
            except Exception as exc:
                self._cerrar()
                if self.on_success:
                    self.on_success(False, str(exc))
            return

        try:
            carpeta_destino = self._obtener_carpeta_exportacion()
            carpeta_destino.mkdir(parents=True, exist_ok=True)

            tipo_registro = self.tipo_exportacion
            if (
                self.tipo_exportacion == "asistencias"
                and formato == "pdf"
                and self.tipo_reporte_asistencias
                and self.tipo_reporte_asistencias.value == "estadistica"
            ):
                tipo_registro = "estadisticas_asistencia"

            nombre_archivo = gestor_planillas.generar_nombre_planilla(
                curso=self.curso_nombre,
                tipo=tipo_registro,
                formato=formato,
                directorio=carpeta_destino,
                colegio=self.colegio_nombre,
            )
            ruta_archivo = carpeta_destino / nombre_archivo
            ruta_str = str(ruta_archivo)

            exito = False
            error_msg = None
            es_paginado = self.modo_pdf_selector.value == "paginado"

            kwargs_reg = (
                {"regimen": self.regimen}
                if self.regimen != REGIMEN_TRIMESTRAL
                else {}
            )
            if self.tipo_exportacion == "notas":
                if formato == "pdf":
                    titulo_pdf = f"{self.colegio_nombre} - {self.curso_nombre}"
                    periodos_anexo: list[str] | None = None
                    if (
                        self.chk_incluir_intensificacion is not None
                        and self.chk_incluir_intensificacion.value
                    ):
                        periodos_anexo = [
                            pid
                            for pid, chk in self.intensif_periodos_checks.items()
                            if chk.value
                        ] or None
                    exito, error_msg = exportar_a_pdf(
                        self.curso_data,
                        ruta_str,
                        titulo_pdf,
                        nombre_colegio=self.colegio_nombre,
                        paginado=es_paginado,
                        periodos_intensificacion_ids=periodos_anexo,
                        **kwargs_reg,
                    )
                elif formato == "csv":
                    exito, error_msg = exportar_a_csv(
                        self.curso_data, ruta_str, **kwargs_reg
                    )
                elif formato == "txt":
                    titulo_txt = f"{self.colegio_nombre} - {self.curso_nombre}"
                    exito, error_msg = exportar_a_texto(
                        self.curso_data, ruta_str, titulo_txt, **kwargs_reg
                    )
            else:
                if formato == "pdf":
                    fecha_desde = None
                    fecha_hasta = None
                    if self.chk_todas_fechas and not self.chk_todas_fechas.value:
                        fecha_desde = self.dd_desde.value if self.dd_desde else None
                        fecha_hasta = self.dd_hasta.value if self.dd_hasta else None

                        if fecha_desde and fecha_hasta:
                            fechas_norm = ordenar_fechas_cronologicamente(
                                [fecha_desde, fecha_hasta]
                            )
                            fecha_desde, fecha_hasta = fechas_norm[0], fechas_norm[-1]

                    if (
                        self.tipo_reporte_asistencias
                        and self.tipo_reporte_asistencias.value == "estadistica"
                    ):
                        rango_str = "Todas las fechas"
                        if fecha_desde and fecha_hasta:
                            rango_str = f"Desde: {fecha_desde} | Hasta: {fecha_hasta}"
                        datos_stats = obtener_estadisticas_asistencia_curso(
                            self.curso_data,
                            fecha_desde=fecha_desde,
                            fecha_hasta=fecha_hasta,
                        )
                        exito, error_msg = exportar_estadisticas_asistencia_a_pdf(
                            datos_estadisticas=datos_stats,
                            file_path=ruta_str,
                            nombre_colegio=self.colegio_nombre,
                            nombre_curso=self.curso_nombre,
                            rango_fechas_str=rango_str,
                            **kwargs_reg,
                        )
                    else:
                        titulo_pdf = (
                            f"Asistencias - {self.colegio_nombre} - {self.curso_nombre}"
                        )
                        exito, error_msg = exportar_asistencias_a_pdf(
                            self.curso_data,
                            ruta_str,
                            titulo_pdf,
                            nombre_colegio=self.colegio_nombre,
                            paginado=es_paginado,
                            fecha_desde=fecha_desde,
                            fecha_hasta=fecha_hasta,
                            **kwargs_reg,
                        )
                elif formato == "csv":
                    exito, error_msg = exportar_asistencias_a_csv(
                        self.curso_data, ruta_str
                    )
                elif formato == "txt":
                    titulo_txt = (
                        f"Asistencias - {self.colegio_nombre} - {self.curso_nombre}"
                    )
                    exito, error_msg = exportar_asistencias_a_texto(
                        self.curso_data, ruta_str, titulo_txt
                    )

            if not exito:
                raise RuntimeError(error_msg or "Error durante la generación del archivo")

            gestor_planillas.registrar_exportacion(
                ruta_archivo=ruta_archivo,
                colegio=self.colegio_nombre,
                curso=self.curso_nombre,
                tipo=tipo_registro,
                formato=formato,
                directorio=carpeta_destino,
            )
            if hasattr(self, "state") and self.state and hasattr(self.state, "notify"):
                try:
                    self.state.notify()
                except Exception:
                    pass

            self._cerrar()
            self._intentar_compartir(ruta_str, nombre_archivo)

            if self.on_success:
                self.on_success(True, ruta_str)

        except Exception as exc:
            self._cerrar()
            if self.on_success:
                self.on_success(False, str(exc))

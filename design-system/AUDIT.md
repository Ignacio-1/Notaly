# Auditoría Técnica de UI/UX y Sistema de Diseño — Notaly Mobile (`com.notaly.app.notaly`)

**Fecha de auditoría:** 2026-11-16  
**Dispositivo auditado:** Android Emulator `emulator-5554` (`Medium_Phone_API_37.0`, Android 17 / `sdk_gphone64_x86_64`, resolución física `1080×2400 px`)  
**Paquete ejecutado:** `com.notaly.app.notaly` (Flet + Material 3)  
**Alcance:** Inspección en vivo vía `mobile-mcp` (capturas de pantalla reales y extracción del árbol de accesibilidad/elementos) en estados **vacíos**, **con datos**, **Modo Claro** y **Modo Oscuro**, cruzada con la implementación fuente en `mobile/`.

---

## 1. Resumen Ejecutivo y Hallazgos Transversales

La aplicación móvil cuenta con una base de tokens semánticos en [`mobile/theme.py`](../mobile/theme.py) (`LIGHT_TOKENS` y `DARK_TOKENS`), pero su ejecución visual y arquitectónica presenta **fricciones estructurales severas** que afectan la legibilidad, la densidad de información, el contraste WCAG AA, la navegación y la consistencia del sistema de diseño:

1. **Doble cabecera persistente y pérdida de viewport vertical:** El `AppBar` global ([`mobile/main.py`](../mobile/main.py#L398-L420)) convive siempre con `build_app_header` ([`mobile/components/ui_header.py`](../mobile/components/ui_header.py#L67-L138)). En `ColegiosView` y `PlanillasView` se duplica la iconografía escolar (`ft.Icons.SCHOOL`) y en `NotasView` se apilan **5 barras superiores** (~650 px / ~27 % de la pantalla) antes de mostrar el primer alumno.
2. **Fallas críticas de contraste en Modo Oscuro y estados semánticos (WCAG AA):**
   - Los `FilledButton` primarios usan `bgcolor=tok.primary` (`#818CF8` en Dark Mode) con `color=ft.Colors.WHITE` hardcodeado → ratio **2.98:1** (falla 4.5:1).
   - En `GlobalSearchBar` ([`mobile/components/global_search.py`](../mobile/components/global_search.py#L243-L247)), los resultados usan `TEXT_MAIN` (`#0F172A`) y `BG_PAGE` (`#F8FAFC`) hardcodeados → texto casi ilegible sobre fondo `#2B2930` en Modo Oscuro.
   - En `AsistenciasView`, los botones rellenos `T` (`#F59E0B` con texto blanco → **2.15:1**) y `P` (`#10B981` con texto blanco → **2.54:1**) incumplen WCAG AA.
3. **Bugs visuales y de interacción detectados en dispositivo real:**
   - `GlobalSearchBar` con `full_screen=False` dentro de `AppBar.title` abre el overlay desplazado a `x=135 px` (`945 px` de ancho), dejando una franja lateral izquierda recortada de la pantalla anterior.
   - Incompatibilidad Flet 0.86+ en [`mobile/views/notas_view.py`](../mobile/views/notas_view.py#L668): mutar `.name` en lugar de `.icon` en `ft.Icon` deja los íconos de estado anual (`Aprobado`/`Desaprobado`) congelados en `⊖` y los chevrons de tarjetas invertidos (`^` colapsado / `v` expandido).
   - `header_pills_containers` ([`mobile/views/notas_view.py`](../mobile/views/notas_view.py#L156)) nunca se puebla, dejando las tarjetas colapsadas sin resumen visual de notas.
   - El caché `_curso_views` en [`mobile/main.py`](../mobile/main.py#L239-L249) provoca desincronización entre pestañas (agregar alumnos en `Notas` deja `Asistencia` mostrando estado vacío), y `navigate()` ([`mobile/main.py`](../mobile/main.py#L227-L230)) sobrescribe `state.selected_colegio` al navegar hacia otro colegio si existe un frame `"cursos"` previo en el historial.
4. **Abuso de `ft.AlertDialog` genérico con alturas fijas desproporcionadas:** Múltiples modales (`LocalBackupDialog`, `PlanillasCursoDialog`, `PlanificacionesInstitucionDialog`, `PlanificacionCursoDialog`, `SorteadorGruposDialog`, `ComportamientoDialog` y el selector de contexto de `EstadisticasView`) fijan alturas estáticas (`380–520 dp` o columnas expandidas) generando grandes espacios vacíos blancos/lavanda, y varios formularios carecen de `scroll=ft.ScrollMode.AUTO` cuando aparece el teclado virtual.

---

## 2. Mapa de Vistas, Pestañas, Modales y Estados Auditados

| Pantalla / Modal | Estados Verificados en Emulador | Archivo Fuente Principal |
|---|---|---|
| **Inicio — Colegios** (`ColegiosView`) | Con datos (simple y con dirección/horario), Modo Claro/Oscuro, menú contextual | [`mobile/views/colegios_view.py`](../mobile/views/colegios_view.py) |
| **Barra Global + Búsqueda** (`AppBar` + `GlobalSearchBar`) | Reposo, abierta vacía, resultados con coincidencia (Claro y Oscuro), menú overflow, Acerca de | [`mobile/main.py`](../mobile/main.py), [`mobile/components/global_search.py`](../mobile/components/global_search.py) |
| **Copia de Seguridad** (`LocalBackupDialog`) | Con copia automática diaria detectada | [`mobile/components/local_backup_dialog.py`](../mobile/components/local_backup_dialog.py) |
| **Cursos de Institución** (`CursosView`) | Vacío (0 cursos), con datos + horario, menú contextual | [`mobile/views/cursos_view.py`](../mobile/views/cursos_view.py) |
| **Planificaciones** (`PlanificacionesInstitucionDialog` & `PlanificacionCursoDialog`) | Institución sin clases planificadas, calendario mensual | [`mobile/components/planificaciones_institucion_dialog.py`](../mobile/components/planificaciones_institucion_dialog.py), [`mobile/components/planificacion_dialog.py`](../mobile/components/planificacion_dialog.py) |
| **Planilla de Notas** (`NotasView`) | Vacío (0 alumnos), alumnos sin nombre, con notas aprobadas/desaprobadas, dock numérico abierto, pestaña Anual | [`mobile/views/notas_view.py`](../mobile/views/notas_view.py) |
| **Modales de Notas y Alumnos** | `ColegioFormDialog`, `CreateCursoDialog`, `StudentFormDialog`, `CustomizeColumnsDialog`, `ComportamientoDialog` (vacío y con registro), `ConfirmDeleteDialog`, `PlanillasCursoDialog` (vacío y con PDF), `ExportDialog` | [`mobile/components/student_dialog.py`](../mobile/components/student_dialog.py), [`mobile/components/comportamiento_dialog.py`](../mobile/components/comportamiento_dialog.py), [`mobile/components/planillas_curso_dialog.py`](../mobile/components/planillas_curso_dialog.py), [`mobile/components/export_dialog.py`](../mobile/components/export_dialog.py) |
| **Asistencias** (`AsistenciasView` & `DatePickerDialog`) | Vacío (0 alumnos), sin marcas, con marcas P/A/T, selector de fecha | [`mobile/views/asistencias_view.py`](../mobile/views/asistencias_view.py), [`mobile/components/date_picker_dialog.py`](../mobile/components/date_picker_dialog.py) |
| **Grupos** (`GruposView` & modales) | Vacío, con grupos creados y calificados, `SorteadorGruposDialog` (con/sin temas), `CalificarGrupoDialog`, `ReasignarAlumnoDialog` | [`mobile/views/grupos_view.py`](../mobile/views/grupos_view.py), [`mobile/components/grupos_sorteador_dialog.py`](../mobile/components/grupos_sorteador_dialog.py), [`mobile/components/calificar_grupo_dialog.py`](../mobile/components/calificar_grupo_dialog.py) |
| **Planillas Exportadas** (`PlanillasView`) | Vacío, árbol expandido (Colegio → Curso → Archivo), modal eliminar planilla | [`mobile/views/planillas_view.py`](../mobile/views/planillas_view.py) |
| **Estadísticas** (`EstadisticasView` & modales) | Nivel Institucional (sin notas/registros/clases), Nivel Curso (con notas, donut e histograma), secciones Calificaciones/Comportamiento/Asistencias, modal Contexto, `ExportEstadisticasDialog` | [`mobile/views/estadisticas_view.py`](../mobile/views/estadisticas_view.py), [`mobile/components/export_estadisticas_dialog.py`](../mobile/components/export_estadisticas_dialog.py) |

---

## 3. Análisis Detallado por Pantalla y Componente

### 3.1 Shell Global: AppBar, Footer y Búsqueda (`mobile/main.py`, `ui_header.py`, `footer.py`, `global_search.py`)

**Evidencia del árbol y captura:**
- `AppBar` ([`mobile/main.py:398-420`](../mobile/main.py#L398-L420)): `@e3 View at=142,81 size=518x111` (SearchBar), `@e7 Button` (Modo Oscuro), `@e9 Button` (Copia de Seguridad), `@e10 Button label="Show menu"`.
- Debajo inmediato en `ColegiosView`: `@e11 "GESTIÓN DOCENTE"`, `@e12 "Notaly"`.
- Overlay de `GlobalSearchBar`: `@e4 View label="Volver" at=135,81 size=945x147`.
- `AppFooter` ([`mobile/components/footer.py:16-62`](../mobile/components/footer.py#L16-L62)): `@e18..@e20` en `y=2127, size=360x210`.

**Hallazgos:**
1. **Jerarquía visual:**
   - **Doble cabecera redundante:** El `AppBar` muestra un ícono de birrete (`ft.Icons.SCHOOL`) a la izquierda y, 60 px más abajo, `build_app_header("Gestión Docente", "Notaly")` ([`mobile/views/colegios_view.py:50`](../mobile/views/colegios_view.py#L50)) vuelve a renderizar otro ícono de birrete dentro de un cuadrado índigo. La pantalla principal no necesita dos encabezados apilados.
   - **Acción duplicada en AppBar:** El conmutador de tema (`Modo Oscuro`/`Modo Claro`) aparece simultáneamente como `IconButton` directo (`theme_button`, línea 348) y como primera opción dentro del `PopupMenuButton` (`theme_menu_item`, línea 355).
2. **Espaciado y geometría:**
   - **`GlobalSearchBar` desplazada (`x=135 px`):** Al usar `full_screen=False` ([`mobile/components/global_search.py:64`](../mobile/components/global_search.py#L64)) dentro de `AppBar.title`, Material 3 ancla el `SearchView` al ancho y posición del título (`x=135..1080`), dejando una columna izquierda transparente de `135 px` donde se asoman recortes del contenido inferior (`"Cole..."`, `"1 insti"`, `"P"`).
   - **Barra de búsqueda estrangulada:** Entre el ícono `leading` y los 3 botones de acción derechos, la caja de búsqueda queda comprimida a `518 px` (~190 dp) recortando el hint `"Buscar alumno, curso..."`.
   - **Teclado/barra flotante de Gboard en diálogos:** En vistas con `EditText` enfocado, la píldora flotante del teclado en emulador solapa visualmente el `NavigationBar` inferior.
3. **Contraste:**
   - **Fallo crítico en Dark Mode (`GlobalSearchBar`):** En [`mobile/components/global_search.py:113-116, 207-247`](../mobile/components/global_search.py#L207-L247), los `ListTile` usan `TEXT_MAIN` (`#0F172A`), `TEXT_MUTED`, `BG_PAGE` (`#F8FAFC`), `BORDER_COLOR` y `ft.Colors.GREY_500/600` estáticos en vez de `self.app_state.tokens`. En captura real Dark Mode, `"PRUEBA 1"` se renderiza en azul casi negro sobre fondo `#2B2930` (contraste < 1.5:1, ilegible).
   - **Eyebrow con bajo contraste en Dark Mode:** `tok.text_subtle` (`#64748B`) sobre `tok.surface` (`#1E293B`) da **3.07:1**, insuficiente para texto de `11 px`.
4. **Densidad y accesibilidad:**
   - Los `IconButton` en `ui_header.py` y `main.py` envuelven su `Button` separado de su `View label="..."` en el árbol de accesibilidad (`@e6 View label="Modo Oscuro"` y `@e7 Button` sin label).
5. **Componentes genéricos M3 a reemplazar:**
   - `ft.SearchBar` (`full_screen=False`) → reemplazar por una página/modal de búsqueda a pantalla completa (`100%` ancho) o trigger táctil limpio desacoplado de un `AppBar` sobrecargado.
   - `ft.PopupMenuButton` genérico (surface tint lavanda M3 `#ECE6F0`) → reemplazar por un **Bottom Sheet** estilizado con tokens propios (`tok.surface`, bordes y tipografía consistente).

---

### 3.2 Colegios (`mobile/views/colegios_view.py`)

**Evidencia del árbol y captura:**
- `@e13 View label="Colegios\n1 instituciones registradas"`
- `@e14 Button label="+ Colegio" at=755,423 size=283x94`
- `@e15 View label="P1\nPRUEBA 1\n1 curso registrados"`
- `@e16 Button` (sin label de accesibilidad; botón de Insights) y `@e17 Button label="Show menu"`.

**Hallazgos:**
1. **Jerarquía visual:**
   - Cada tarjeta expone un ícono de `INSIGHTS` suelto junto al menú `⋮`, aunque `Estadísticas` ya es la primera opción dentro del `PopupMenuButton` ([`colegios_view.py:196-200`](../mobile/views/colegios_view.py#L196-L200)). Visualmente, el ícono de línea sin etiqueta compite con la acción primaria (tocar la tarjeta para abrir cursos).
2. **Espaciado:**
   - El padding superior (`top=12`) más la doble cabecera empujan el título `"Colegios"` hasta `y=415 px`.
   - El `FilledButton("+ Colegio")` mide `94 px` (~36 dp) de alto (`height=36`, línea 79), por debajo del mínimo táctil recomendado de 44–48 dp.
3. **Contraste:**
   - En Modo Oscuro, `+ Colegio` usa `bgcolor=tok.primary` (`#818CF8`) con `color=ft.Colors.WHITE` (líneas 75–76) → **2.98:1** (no cumple WCAG AA). Este patrón se repite en **todos los `FilledButton` primarios de la app**.
4. **Densidad de datos y textos:**
   - Errores gramaticales visibles en producción: `"1 instituciones registradas"` (línea 69) y `"1 curso registrados"` (línea 126, solo pluraliza `curso` pero deja `registrados` en plural).
   - La tarjeta con dirección y horario (`Audit Demo`) crece de `194 px` a `267 px` verticalmente y alinea los metadatos debajo del subtítulo sin separación visual ni chips.
5. **Componentes genéricos M3 a reemplazar:**
   - `ft.FilledButton` estándar con borde de `10 px` sin escala de tipografía/contraste adaptativa para Dark Mode.
   - `ft.PopupMenuButton` de tarjeta → unificar acciones secundarias de tarjeta en un Bottom Sheet contextual o menú con superficie tokenizada.

---

### 3.3 Cursos (`mobile/views/cursos_view.py`)

**Evidencia del árbol y captura:**
- `@e15 View label="Mis cursos\n1 activos · Ciclo lectivo"`
- `@e16 Button label="Planificaciones" at=42,570 size=488x94`
- `@e17 Button label="+ Curso" at=551,570 size=487x94`
- `@e18 View label="3A\nPlanilla y gestión integral\n3 estudiantes\nCiclo Lectivo Activo"`
- Estado vacío: `@e18 View label="No hay cursos registrados\nToca '+ Curso' para agregar el primer curso a este colegio."`

**Hallazgos:**
1. **Jerarquía visual:**
   - En el estado vacío (`0 cursos`), el botón `OutlinedButton("Planificaciones")` sigue apareciendo al 50 % de ancho con el mismo peso estructural que `+ Curso`, cuando no existen cursos que planificar.
   - El subtítulo fijo `"Planilla y gestión integral"` (línea 149) en **todas** las tarjetas no aporta información real (texto relleno repetitivo).
2. **Espaciado:**
   - Botones de cabecera (`Planificaciones` y `+ Curso`) con `height=36` (`94 px`) por debajo del mínimo táctil de 44–48 dp.
   - En el pie de tarjeta, `"0 estudiantes"` / `"3 estudiantes"` y `"Ciclo Lectivo Activo"` quedan separados por un `Divider` que ocupa espacio vertical innecesario cuando `"Ciclo Lectivo Activo"` también es texto estático sin valor operativo cuando `num_clases == 0` (líneas 219–223).
3. **Contraste:**
   - Mismo fallo de `FilledButton` en Modo Oscuro para `+ Curso` (`#FFFFFF` sobre `#818CF8`, **2.98:1**).
4. **Densidad y microcopy:**
   - Error gramatical visible cuando hay 1 curso: `"1 activos · Ciclo lectivo"` (línea 50).
   - Redundancia: el botón de calendario en la tarjeta (`@e19`) abre exactamente lo mismo que la primera opción del menú `⋮` (`"Planificación de Clases"`), mientras el menú además oculta `"Estadísticas"` sin indicador visual directo.
5. **Componentes genéricos M3 a reemplazar:**
   - `PopupMenuButton` con 6 ítems (`Planificación de Clases`, `Estadísticas`, `Planilla de Notas`, `Asistencias`, `Renombrar`, `Eliminar`) sin jerarquía destructiva visual en `"Eliminar"`.

---

### 3.4 Notas (`mobile/views/notas_view.py`)

**Evidencia del árbol y captura:**
- Subcabeceras apiladas: `AppBar` (`y=74..192`) + `build_app_header` (`y=242..358`) + `build_module_tabs` (`y=407..525`) + `trim_selector_bar` (`y=554..638`) + `actions_bar` (`y=659..785`).
- `@e28 Button label="+ Alumno"` muestra visualmente `[👤+  + Alumno]` (doble `+`).
- `@e29..@e32 Button` (4 botones de herramientas sin etiqueta accesible en árbol).
- Tarjeta expandida: `@e35..@e37` (`Trimestre 1`, `Trimestre 2`, `Trimestre 3`) dentro de la tarjeta justo debajo de `@e24..@e26` (`1° Trim`, `2° Trim`, `3° Trim`).
- Dock numérico: `@e51..@e62`, con `@e61 View` (retroceso) sin `label`.

**Hallazgos:**
1. **Jerarquía visual y redundancia crítica:**
   - **Doble selector de trimestres simultáneo:** La barra global `1° Trim | 2° Trim | 3° Trim | Anual` (`L257-297`) y la barra interna dentro de la tarjeta expandida `Trimestre 1 | Trimestre 2 | Trimestre 3` (`L964-992`) hacen exactamente lo mismo (`self._seleccionar_trimestre`), duplicando controles en pantalla y robando altura útil.
   - **5 barras apiladas arriba** reducen el área útil de tarjetas a ~65 % de la altura total (y < 40 % cuando se abre el dock numérico).
   - En la pestaña `Anual`, la barra de acciones (`+ Alumno`, personalizar columnas, ordenar A–Z) sigue visible y activa a pesar de ser un modo de solo lectura.
2. **Bugs visuales reales observados en captura:**
   - **Chevrons invertidos:** Al expandir `#2` y colapsar `#1`, `#1` conserva el ícono `^` (`EXPAND_LESS`) y `#2` muestra `v` (`EXPAND_MORE`) porque [`notas_view.py:737, 1670, 1681, 1692`](../mobile/views/notas_view.py#L1670-L1693) asigna `.name = ...` en vez de `.icon = ...` (incompatible con Flet 0.86+).
   - **Íconos congelados en `Anual`:** En [`notas_view.py:668`](../mobile/views/notas_view.py#L668), `ref_anual["estado_icon"].name = estado_icon` falla silenciosamente por la misma causa, dejando `⊖` (`REMOVE_CIRCLE_OUTLINE`) tanto en la insignia verde `Aprobado` como en la roja `Desaprobado`.
   - **Tarjetas colapsadas vacías:** `header_pills_containers` ([`notas_view.py:156, 796`](../mobile/views/notas_view.py#L156)) no se construye ni se monta en la cabecera de la tarjeta. Cuando un alumno está colapsado, el docente no ve sus promedios (`1ºT`, `2ºT`, `3ºT`) sin abrir tarjeta por tarjeta.
3. **Espaciado:**
   - En el dock numérico inferior, la fila 2 (`6 7 8 9 10 [⌫] [Sig.]`) termina prácticamente pegada al indicador de gestos del sistema Android (`bottom` insuficiente en el contenedor del dock).
   - En el panel `Anual`, los 3 bloques (`1° Trim (T1)`, `2° Trim (T2)`, `3° Trim (T3)`) y `resumen_anual_row` tienen `bgcolor=tok.surface_variant` (`#F1F5F9`) mientras las píldoras vacías `--` usan `grade_empty_bg` (`#F1F5F9`), fundiéndose por completo sin borde ni contraste.
4. **Contraste y densidad:**
   - Cuando un alumno no tiene nombre cargado, se muestra `?` en el avatar y `#1 ` (con espacio final) en `NotasView`, mientras `AsistenciasView` lo muestra como `N° 1` — nomenclatura inconsistente entre pestañas.
   - El casillero `Recup` deshabilitado renderiza el guion `-` con opacidad/contraste muy bajo (`#CBD5E1` / `text_subtle` sobre `#F8FAFC`).
   - El botón `+ Alumno` duplica el signo `+` (ícono `PERSON_ADD` ya incluye `+` + texto `"+ Alumno"`).
5. **Componentes genéricos M3 a reemplazar:**
   - Barra de 4 `IconButton` sin etiquetas (`Tune`, `Sort`, `Planillas`, `Exportar`) → reemplazar por botones con descriptor o menú contextual / action sheet claro para evitar iconografía ambigua (`TUNE` vs `FOLDER_SHARED_OUTLINED`).
   - `SegmentedButton`-like pills caseras repetidas (`module_tabs` + `trim_selector_bar` + `local_trim_buttons`) → consolidar jerarquía de navegación con un único selector de período.

---

### 3.5 Asistencias (`mobile/views/asistencias_view.py`)

**Evidencia del árbol y captura:**
- Barra de fecha (`y=562..688`): `<`, `📅 16-11-2026 ▼`, `>`, `📅` (`Elegir Fecha en Calendario`), `Hoy`.
- Fila de 5 KPIs (`y=730..822`): `Presentes`, `Ausentes`, `Tardes`, `Justificados`, `% Asist.`.
- Tarjetas de alumno (`y=1003..1470`): avatar + nombre/N° + 4 botones (`P`, `A`, `T`, `J`).

**Hallazgos:**
1. **Jerarquía visual y redundancia:**
   - **Disparador de calendario duplicado:** En `date_bar` ([`asistencias_view.py:121-167`](../mobile/views/asistencias_view.py#L121-L167)), el pill central `📅 16-11-2026 ▼` y el `IconButton(ft.Icons.EVENT)` justo a la derecha abren exactamente el mismo modal `DatePickerDialog`.
   - **Borde de selección "fantasma":** Al tocar un botón (`P`/`A`/`T`/`J`) o una tarjeta, ésta recibe un borde índigo de `2 px` (`is_active_card`, línea 540), remanente del antiguo dock de marcado inferior que fue eliminado (`self.marking_dock = None`, línea 273). En pantalla confunde al usuario haciéndole creer que la última fila está "seleccionada" o tiene foco especial.
   - **Bug de sincronización entre pestañas:** Al agregar alumnos en `NotasView` y cambiar a `Asistencia`, `AsistenciasView` permanece en estado vacío (`"No hay alumnos en este curso"`) porque [`mobile/main.py:242-245`](../mobile/main.py#L242-L245) cachea la instancia en `_curso_views["asistencias"]` sin refrescarla.
2. **Espaciado y densidad:**
   - **5 KPIs comprimidos en una fila:** `"Justificados"` en `10 px` ocupa casi el 100 % de su columna, y `"% Asist."` usa `bgcolor=tok.surface` sin borde, pareciendo texto suelto sobre `bg_page` en contraste con las otras 4 cajas tintadas.
   - **Botones `P/A/T/J` pequeños y estrechamiento del nombre:** Cada botón mide `38×36 dp` (`99×95 px`, por debajo de `48 dp` táctil recomendado) y los 4 botones consumen ~`450 px` horizontales, truncando nombres como `"GomezAna SofiaMa..."`.
3. **Contraste (WCAG AA):**
   - **Fallo crítico en botón `T` (Tarde):** Texto blanco sobre `#F59E0B` (Amber 500) = **2.15:1**; estado inactivo `#F59E0B` sobre blanco = **2.15:1**.
   - **Fallo crítico en botón `P` (Presente):** Texto blanco sobre `#10B981` (Emerald 500) = **2.54:1**; estado inactivo `#10B981` sobre blanco = **2.54:1**.
   - En ambos casos, tanto el borde/texto sin marcar como el botón relleno son ilegibles bajo estándares WCAG AA (4.5:1 para texto normal de 13 px).
4. **Componentes a reemplazar:**
   - Reemplazar las 4 cajas cuadradas `P/A/T/J` con borde fino de bajo contraste por un **Segmented Control táctil** de estado con fondos tintados suaves (`attendance_*_bg` + `attendance_*_text` de alto contraste, > 7:1) o estado único expandible / menú compacto en pantallas estrechas.

---

### 3.6 Trabajos en Grupo (`mobile/views/grupos_view.py`)

**Evidencia del árbol y captura:**
- Estado vacío (`y=1329..1809`): tarjeta centrada con `"Aún no hay grupos creados"` y `"3 alumnos listos en el curso"`.
- Estado con datos (`y=546..1811`): chips de trabajos (`Trabajo Práctico N° 1`, `+ Nuevo Trabajo`), barra `3 grupos • 3 integrantes` + 2 botones de ícono, y tarjetas por grupo con `+ Tema`, `+ Calificar` / `Nota: 9`, y botón de swap por alumno.

**Hallazgos:**
1. **Jerarquía visual:**
   - En estado vacío, los botones de cabecera (`Copiar lista de grupos` y `Sortear nuevos grupos`, líneas 75–88) siguen activos aunque no haya nada que copiar (`COPY_ALL`), generando acciones muertas.
   - En estado con datos, conviven demasiados puntos de entrada para crear/agregar (`CASINO` en header, `+ Nuevo Trabajo` chip, `ADD_CARD` en barra de trabajo).
2. **Espaciado:**
   - Los chips interactivos `+ Tema` (`padding top=1, bottom=1`, línea 324) y `+ Calificar` (`padding top=2, bottom=2`, línea 288) miden apenas `42–53 px` (~16–20 dp) de altura real en pantalla, resultando blancos táctiles muy pequeños y propensos a errores de toque.
3. **Contraste y densidad:**
   - `GruposView` es visualmente más limpia que `NotasView`, pero el botón de reasignar (`SWAP_HORIZ`, `icon_size=16`) en gris sutil (`tok.text_muted`) se percibe poco accionable.
4. **Componentes a reemplazar:**
   - Reemplazar las micro-píldoras `+ Tema` / `+ Calificar` por pills/botones táctiles de altura ≥ `36–40 dp` con área táctil mínima de `44 dp`.

---

### 3.7 Planillas Exportadas (`mobile/views/planillas_view.py`)

**Evidencia del árbol y captura:**
- Chips de filtro (`y=404..486`): `Todas`, `Notas`, `Asistencias`, `Estadísticas` (recortado en `x=1038`).
- Árbol con datos: `Audit Demo` (`1 archivo`) → `Curso: 1A` (`1 archivo(s)`) → tarjeta gris `Planilla 1A - 16-11-2026.pdf` con `Compartir`, `Abrir`, `Eliminar`.

**Hallazgos:**
1. **Jerarquía visual y densidad:**
   - **Anidamiento excesivo ("caja dentro de caja dentro de caja"):** En móviles de `360–390 dp`, el acordeón de Institución (`col_header`) + contenedor con margen izquierdo `12 px` (`cur_box`) + tarjeta interna `surface_variant` crea 3 niveles de bordes/fondos que desperdician ancho horizontal y saturan la vista.
   - **Inconsistencia gramatical:** Nivel institución dice `"1 archivo"` (línea 242) y nivel curso justo debajo dice `"1 archivo(s)"` (línea 275).
2. **Espaciado y scroll:**
   - El chip `"Estadísticas"` en la barra horizontal queda recortado a la derecha (`"Estadística"`) sin gradiente o pista visual de scroll horizontal.
3. **Contraste:**
   - El modal de confirmación de borrado (`_confirmar_eliminar`, [`planillas_view.py:447-474`](../mobile/views/planillas_view.py#L447-L474)) omite `bgcolor=tok.surface`, renderizando el fondo lavanda genérico M3 (`#ECE6F0`) inconsistente con `ConfirmDeleteDialog` (`tok.surface` blanco puro).
4. **Componentes a reemplazar:**
   - Sustituir el acordeón de 3 cajas anidadas por **headers de sección planos/colapsables** con lista limpia de archivos y acciones en fila o swipe/sheet.

---

### 3.8 Estadísticas (`mobile/views/estadisticas_view.py`)

**Evidencia del árbol y captura:**
- `@e17 View label="CONTEXTO ANALÍTICO\nColegio: PRUEBA 1 · Ámbito: Institucional\nCambiar"` (visualmente truncado: `"Colegio: PRUEBA 1 · Ámbito: Instit..."`).
- Pestañas de sección (`y=651..740`): `Calificaciones`, `Comportamiento`, `Asistencias`.
- Pills de período (`y=795..882`): `1° Trimestre`, `2° Trimestre`, `3° Trimestre`, `Resumen Anual` (cortado: `"Resume"`).
- Grid KPI 2×2 (`y=945..1397`), Donut (`y=1439..1964`), Histograma (`y=2006+`).

**Hallazgos:**
1. **Jerarquía visual y redundancia de datos:**
   - **Duplicación exacta KPI vs Donut:** En `Calificaciones`, el grid superior muestra `Aprobados (1 / 33.3%)`, `Desaprobados (1 / 33.3%)`, `Sin Calificar (1 / 33.3%)` y `Promedio (6.00)`. Inmediatamente debajo, la tarjeta `Distribución General` repite exactamente los mismos 3 valores (`Aprobados 1 (33.3%)`, `Desaprobados 1 (33.3%)`, `Sin Calificar 1 (33.3%)`).
   - **Inconsistencia visual en el grid 2×2:** En `Calificaciones` ([`estadisticas_view.py:857-872`](../mobile/views/estadisticas_view.py#L857-L872)), `Aprobados` y `Desaprobados` tienen bordes de `1 px` de color intenso (`grade_pass_text` / `grade_fail_text`), mientras `Sin Calificar` y `Promedio` tienen borde neutro sutil (`tok.border_color`). En `Comportamiento` (3 tarjetas) todas tienen borde de color, y en `Asistencias` ninguna tiene borde destacado salvo el fondo de `primary_light`.
2. **Espaciado y truncamiento:**
   - **Botón `Comportamiento` pegado al borde:** En `_build_seccion_selector` (líneas 740–763), la palabra `"Comportamiento"` junto con el ícono toca el borde derecho de su pestaña (`1/3` del ancho).
   - **Pills de período cortadas:** `"Resumen Anual"` aparece cortado a la mitad (`"Resume"`) en el borde derecho sin indicador de scroll; usar etiquetas más cortas (`1° Trim`, `2° Trim`, `3° Trim`, `Anual`) evitaría el scroll horizontal por completo.
   - **Tarjeta de contexto truncada:** Incluso con un nombre corto como `"PRUEBA 1"`, `"Ámbito: Institucional"` se trunca a `"Ámbito: Instit..."` porque el subtítulo usa 1 sola línea junto al botón `Cambiar`.
   - **Filtros de Asistencia sobredimensionados:** En la sección `Asistencias` ([`estadisticas_view.py:2055-2074`](../mobile/views/estadisticas_view.py#L2055-L2074)), cuando `"Todas las fechas"` está marcado, los dos `ft.Dropdown` deshabilitados (`Desde` y `Hasta`) ocupan `147 px` (~56 dp) de altura gris inútil.
   - **Modal de contexto gigante y vacío:** El diálogo `"Seleccionar Institución y Curso"` ([`estadisticas_view.py:641-665`](../mobile/views/estadisticas_view.py#L641-L665)) omite `bgcolor=tok.surface` y coloca una `Column` no ajustada (`tight=False`) dentro de un `Container` sin altura acotada, estirando el diálogo desde `y=189` hasta `y=2211` con casi **80 % de espacio vacío lavanda**.
3. **Contraste:**
   - En el histograma (`Calidad del Rendimiento`), las etiquetas `0` sobre barras vacías en `#94A3B8` sobre fondo blanco tienen contraste ~**2.68:1**.
4. **Componentes genéricos M3 a reemplazar:**
   - Modal selector de contexto → reemplazar por un **Bottom Sheet** compacto con altura adaptable al contenido.
   - `ft.Dropdown` deshabilitados para `Desde`/`Hasta` → ocultar o colapsar cuando `Todas las fechas` está activo, y reemplazar por chips/selectores de fecha del sistema de diseño.

---

### 3.9 Auditoría Consolidada de Diálogos Modales

| Modal / Archivo | Problemas Críticos Detectados (Evidencia Real + Código) |
|---|---|
| **`ColegioFormDialog`, `CreateCursoDialog`, `CustomizeColumnsDialog`** ([`student_dialog.py`](../mobile/components/student_dialog.py#L320-L792)) | Sin `scroll=ft.ScrollMode.AUTO` (incumple `flet-mobile/SKILL.md` ante teclado Gboard); anchos fijos (`320–340`); `EditText` sin etiqueta accesible en árbol; todos usan `ft.Icons.SCHOOL` genérico vía `logo_dialog_title`. |
| **`StudentFormDialog`** ([`student_dialog.py:41-177`](../mobile/components/student_dialog.py#L41-L177)) | 3 botones en `AlertDialog.actions` (`Listo / Cerrar`, `Guardar y salir`, `Siguiente Alumno ➔`) colapsan en **3 filas apiladas verticales** a la derecha (escalera antiestética); el texto de ayuda dice `'Siguiente'` pero el botón dice `'Siguiente Alumno ➔'`; falta scroll interno. |
| **`LocalBackupDialog`** ([`local_backup_dialog.py`](../mobile/components/local_backup_dialog.py)) | `height=480` fijo (`L115`) deja ~150 px de vacío blanco; `self.tab_selector` (`SegmentedButton`, `L81-98`) es código muerto sin montar; botón `"Seleccionar archivo de copia (.json)"` (`height=40`, `L439`) envuelve su texto en **2 líneas chocando con los bordes**; muestra el nombre técnico crudo `"copia de seguridad automatica notaly.json"` truncado. |
| **`PlanificacionesInstitucionDialog`** ([`planificaciones_institucion_dialog.py`](../mobile/components/planificaciones_institucion_dialog.py)) | `height=min(max_dialog_h, 380)` (`L111`) deja ~200 dp de vacío cuando hay un curso sin clases. |
| **`PlanificacionCursoDialog`** ([`planificacion_dialog.py`](../mobile/components/planificacion_dialog.py)) | `height=max_h` (`L207`) fija ~520 dp creando vacío cuando la lista está vacía; celdas del calendario de `36 dp` (94 px, por debajo de 48 dp). |
| **`DatePickerDialog`** ([`date_picker_dialog.py`](../mobile/components/date_picker_dialog.py)) | Hardcodea constantes claras (`PRIMARY`, `ATTENDANCE_P_BG`, `TEXT_MAIN`, `L206-208`) rompiendo Dark Mode; sin `scroll=ft.ScrollMode.AUTO`; usa `ft.Chip` genérico de Material para `Hoy`/`Ayer`. |
| **`ExportDialog`** ([`export_dialog.py`](../mobile/components/export_dialog.py)) | `ft.RadioGroup` genérico ocupa 4 filas altas; metadata de contexto en texto plano (`Colegio:` / `Curso:`) inconsistente con la tarjeta de `ExportEstadisticasDialog`; usa `ft.Icons.SCHOOL`; `height=min(480, calc_max_h)` deja espacio sobrante. |
| **`ExportEstadisticasDialog`** ([`export_estadisticas_dialog.py`](../mobile/components/export_estadisticas_dialog.py)) | **`info_card` (`L137-147`) se encoge al ~70 % del ancho del diálogo** dejando un hueco vacío a la derecha; usa emojis (`🏫`, `📚`, `🗓️`, `📄`) en lugar de íconos vectoriales consistentes. |
| **`SorteadorGruposDialog`** ([`grupos_sorteador_dialog.py`](../mobile/components/grupos_sorteador_dialog.py)) | **`caja_preview` (`L331-337`) no abarca el 100 % del ancho**; error `"1 alumnos"` (`L144`); `height=calc_max_h` (`L382`) deja ~450 px vacíos; `ft.Switch` genérico; `_refrescar_chips_temas` (`L199-224`) hardcodea `#F1F5F9` y `TEXT_MAIN` (roto en Dark Mode). |
| **`CalificarGrupoDialog`** ([`calificar_grupo_dialog.py`](../mobile/components/calificar_grupo_dialog.py)) | Error `"1 integrantes"` (`L90`); hardcodea `TEXT_MUTED` (`L192`) y `PRIMARY` (`L207`); banner azul `#EFF6FF` hardcodeado en modo claro. |
| **`ComportamientoDialog`** ([`comportamiento_dialog.py`](../mobile/components/comportamiento_dialog.py)) | `_actualizar_estilo_botones_categoria` (`L312-326`) hardcodea `#F8FAFC`, `BORDER_COLOR`, `TEXT_MAIN` y tonos claros `COLOR_POS_BG` etc., rompiendo Dark Mode al seleccionar categorías; `height=480` fijo (`L308`) genera vacío blanco inferior. |
| **`PlanillasCursoDialog`** ([`planillas_curso_dialog.py`](../mobile/components/planillas_curso_dialog.py)) | `height=max_h` (`L79`, hasta 500 dp) genera un bloque blanco enorme tanto vacío como con 1 solo archivo. |
| **`GradeEditorDialog`** ([`grade_editor.py`](../mobile/components/grade_editor.py)) | 3 acciones en `AlertDialog` con riesgo de apilado en pantallas estrechas; título con `ft.Icons.SCHOOL`; sin `scroll=ft.ScrollMode.AUTO`. |

---

## 4. Componentes Genéricos de Material Design a Reemplazar

Para evolucionar de una interfaz genérica de Material 3 hacia un sistema de diseño propio de Notaly (cohesivo, táctil y libre de tintes lavanda por defecto):

| Componente M3 Actual | Dónde se Usa | Problema Visual / UX | Reemplazo Recomendado en Sistema de Diseño |
|---|---|---|---|
| **`ft.AlertDialog` sin altura adaptativa ni scroll estándar** | Todos los modales (14 clases) | Tinte lavanda M3 cuando falta `bgcolor`; botones en escalera vertical cuando hay >2 acciones; grandes huecos vacíos por `height` fijo. | **`NotalyDialog` / `NotalyBottomSheet`**: contenedor con `bgcolor=tok.surface`, `border_radius=20`, ancho fluido `min(w-32, 400)`, contenido con `tight=True` + `max_height` adaptativo y fila de acciones controlada (`Row` / `Column` explícita). Preferir **Bottom Sheet** para selectores (`Seleccionar Institución y Curso`, `Exportar`, `Reasignar Alumno`, menús de tarjeta). |
| **`ft.SearchBar(full_screen=False)` en `AppBar.title`** | `GlobalSearchBar` ([`global_search.py`](../mobile/components/global_search.py)) | Anclaje desplazado a `x=135 px` con recorte de pantalla detrás; barra angosta que trunca placeholder; surface tint M3. | **Trigger compacto en cabecera unificada + Overlay/Vista de búsqueda a ancho completo (`100%`)** con fondo `tok.surface` / `tok.bg_page`. |
| **`ft.PopupMenuButton` estándar** | `AppBar`, `ColegiosView`, `CursosView` | Apariencia genérica gris/lavanda M3 sin separación semántica para acciones destructivas (`Eliminar`). | **Action Sheet / Modal Bottom Sheet** con ítems táctiles de `48 dp`, íconos alineados y fila destructiva en `tok.danger`. |
| **`ft.Dropdown` deshabilitado** | `EstadisticasView` y `ExportDialog` (`Desde`/`Hasta`) | Ocupa `147 px` de altura cuando está deshabilitado; apariencia pesada de formulario web/M3. | **Chips de rango colapsables** que solo despliegan selectores interactivos cuando el usuario desactiva `"Todas las fechas"`. |
| **`ft.Radio` / `ft.RadioGroup` vertical** | `ExportDialog` | Lista plana genérica de radios con alta huella vertical y poca diferenciación por formato (PDF, CSV, TXT, WhatsApp). | **Tarjetas seleccionables compactas (`SelectableOptionCard`)** con ícono de formato, descripción corta de 1 línea y borde activo `tok.primary`. |
| **`ft.Chip` y `ft.Switch` sin estilo de marca** | `DatePickerDialog`, `SorteadorGruposDialog` | Colores de superficie M3 genéricos que desentonan con los chips custom de `PlanillasView` y `EstadisticasView`. | **Primitivas `NotalyChip` y `NotalyToggleRow`** unificadas bajo `ThemeTokens`. |
| **`ft.NavigationBar` con estilo por defecto** | `AppFooter` ([`footer.py`](../mobile/components/footer.py)) | Tinte de elevación M3 y ausencia de borde superior sutil (`1 px tok.border_color`) que lo separe del fondo en Light/Dark mode. | Mantener `ft.NavigationBar` por compatibilidad de insets Android (`80 dp` según `flet-mobile/SKILL.md`), pero envolver/estilizar con divisor superior `tok.border_color`, `elevation=0` y tokens exactos de icono/etiqueta. |

---

## 5. Auditoría Específica de Modo Oscuro

Esta sección consolida la inspección en vivo sobre el dataset real en **Modo Oscuro** (`MEDIA DE LA REDUCCION`, `Colegio 1`, `MARIANO GOMEZ`, `MEDIA DE LULES`, `REINA DE LA ESPERANZA`, curso `2DO A` con 29 alumnos y registros de notas/asistencias del `12-10-2026` y `16-11-2026`) cruzada con [`mobile/theme.py`](../mobile/theme.py#L108-L143), `mobile/components/` y `mobile/views/`.

### 5.1 Cobertura Verificada en Modo Oscuro

| Pantalla / Modal Inspeccionado | Estado Verificado en Emulador (Dark Mode) | Archivo Fuente Cruzado |
|---|---|---|
| **`ColegiosView`** | Lista con 5 instituciones (`Colegio 1`..`REINA DE LA ESPERANZA`) | [`mobile/views/colegios_view.py`](../mobile/views/colegios_view.py) |
| **`LocalBackupDialog`** | Respaldo automático detectado (`5 inst / 220 alum / 232.9 KB`) | [`mobile/components/local_backup_dialog.py`](../mobile/components/local_backup_dialog.py) |
| **`CursosView`** | `MEDIA DE LA REDUCCION` con `2DO A` (29 est.) y `2DO B` (27 est.) | [`mobile/views/cursos_view.py`](../mobile/views/cursos_view.py) |
| **`PlanificacionCursoDialog`** | Calendario mensual en `#1E293B` | [`mobile/components/planificacion_dialog.py`](../mobile/components/planificacion_dialog.py) |
| **`NotasView`** | `2DO A` en `1° Trim` (notas `10`, `7`, `4`, `8`), dock numérico abierto, `2° Trim` vacío, `Anual` (`Aprobado`/`Desaprobado`) | [`mobile/views/notas_view.py`](../mobile/views/notas_view.py) |
| **`ComportamientoDialog`** | Estado inicial y tras pulsar categoría `Positivo` | [`mobile/components/comportamiento_dialog.py`](../mobile/components/comportamiento_dialog.py) |
| **`ExportDialog`** | Opciones PDF y selección de `"Una sola página"` con banner de advertencia | [`mobile/components/export_dialog.py`](../mobile/components/export_dialog.py) |
| **`AsistenciasView` & `DatePickerDialog`** | Fecha `16-11-2026` vacía, fecha `12-10-2026` con marcas `P/A/T` y 5 KPIs, calendario `Noviembre 2026` y `Octubre 2026` | [`mobile/views/asistencias_view.py`](../mobile/views/asistencias_view.py), [`mobile/components/date_picker_dialog.py`](../mobile/components/date_picker_dialog.py) |
| **`GruposView` & `SorteadorGruposDialog`** | Vista vacía/con datos y modal con `Sortear con temas` activado | [`mobile/views/grupos_view.py`](../mobile/views/grupos_view.py), [`mobile/components/grupos_sorteador_dialog.py`](../mobile/components/grupos_sorteador_dialog.py) |
| **`PlanillasView`** | Estado vacío sin archivos exportados | [`mobile/views/planillas_view.py`](../mobile/views/planillas_view.py) |
| **`EstadisticasView` & `ExportEstadisticasDialog`** | `2DO A` en `Calificaciones` (KPIs, donut e histograma), `Comportamiento`, `Asistencias`, modal `Seleccionar Institución y Curso` y `Exportar Estadísticas` | [`mobile/views/estadisticas_view.py`](../mobile/views/estadisticas_view.py), [`mobile/components/export_estadisticas_dialog.py`](../mobile/components/export_estadisticas_dialog.py) |
| **`GlobalSearchBar`** | Resultados de búsqueda abiertos en Modo Oscuro (`PRUEBA 1`) | [`mobile/components/global_search.py`](../mobile/components/global_search.py) |

---

### 5.2 Auditoría de Tokens `DARK_TOKENS` y Contraste (WCAG AA)

En [`mobile/theme.py`](../mobile/theme.py#L108-L143), `DARK_TOKENS` define correctamente la superficie base (`bg_page="#0F172A"`, `surface="#1E293B"`, `surface_variant="#334155"`, `text_main="#F8FAFC"`), pero varios pares texto/fondo y el uso sistemático de `ft.Colors.WHITE` sobre rellenos pastel/luminosos producen **fallos severos de contraste (< 4.5:1)**:

| Elemento / Par Cromático | Primer Plano (Fg) | Fondo (Bg) | Ratio | Estado WCAG AA | Dónde Impacta (Evidencia + Código) |
|---|---|---|---|---|---|
| **Botón `T` (Tarde) activo** | `#FFFFFF` | `#FBBF24` (`attendance_t_solid`) | **1.67:1** | Falla crítico | `AsistenciasView` en fecha `12-10-2026` ([`asistencias_view.py:509, 591`](../mobile/views/asistencias_view.py#L509)) |
| **Botón `P` (Presente) activo** | `#FFFFFF` | `#34D399` (`attendance_p_solid`) | **1.92:1** | Falla crítico | `AsistenciasView` en fecha `12-10-2026` ([`asistencias_view.py:509, 591`](../mobile/views/asistencias_view.py#L509)) |
| **Botón `J` (Justificado) activo** | `#FFFFFF` | `#60A5FA` (`attendance_j_solid`) | **2.50:1** | Falla crítico | `AsistenciasView` ([`asistencias_view.py:509, 591`](../mobile/views/asistencias_view.py#L509)) |
| **Botón `A` (Ausente) activo** | `#FFFFFF` | `#F87171` (`attendance_a_solid`) | **2.76:1** | Falla crítico | `AsistenciasView` en fecha `12-10-2026` ([`asistencias_view.py:509, 591`](../mobile/views/asistencias_view.py#L509)) |
| **`FilledButton` / pills primarias** | `#FFFFFF` (`ft.Colors.WHITE`) | `#818CF8` (`DARK_TOKENS.primary`) | **2.98:1** | Falla | `+ Colegio`, `+ Curso`, `+ Alumno`, `Sig.` en dock, `1° Trimestre`, `Rangos`, `Restaurar`, `Listo`, `Crear y Sortear Grupos`, `Exportar PDF` ([`notas_view.py:108, 116, 396, 1845`](../mobile/views/notas_view.py#L108), [`asistencias_view.py:309, 726`](../mobile/views/asistencias_view.py#L309), [`estadisticas_view.py:809, 1014, 2560`](../mobile/views/estadisticas_view.py#L809), [`student_dialog.py:151, 163, 288, 410, 548, 649, 710, 783`](../mobile/components/student_dialog.py#L151)). Nota: el `Checkbox` en `ExportEstadisticasDialog` sí usa tilde `#0F172A` sobre `#818CF8`, evidenciando inconsistencia interna. |
| **Eyebrows y texto sutil sobre tarjeta** | `#64748B` (`text_subtle`) | `#1E293B` (`surface`) | **3.07:1** | Falla | `GESTIÓN DOCENTE`, `INSTITUCIÓN`, `CONTEXTO ANALÍTICO`, `RENDIMIENTO DE CURSO · MEDIA DE LA REDUC...`, guion `-` en `Recup` y `"Excluye sin calificar"` |
| **`text_subtle` sobre fondo base** | `#64748B` (`text_subtle`) | `#0F172A` (`bg_page`) | **3.76:1** | Falla | Cabeceras contextuales y pies sobre fondo principal |
| **Notas desaprobadas / Ausentes** | `#F87171` (`grade_fail_text` / `attendance_a_text`) | `#7F1D1D` (`grade_fail_bg` / `attendance_a_bg`) | **3.62:1** | Falla | Notas `4` y `Desaprobado` en `NotasView`, KPI `Desaprobados` (`6 / 20.7%`) y `Negativo` (`0.0%`) en `EstadisticasView`, KPI `Ausentes` en `AsistenciasView` (contrastado frente a `#4ADE80` sobre `#064E3B`, que logra **~7.32:1**) |
| **Celdas vacías / KPI neutrales** | `#94A3B8` (`grade_empty_text`) | `#334155` (`grade_empty_bg` / `surface_variant`) | **4.05:1** | Falla | KPI `Sin Calificar`, subtítulos `Matriculados`/`Dictadas`/`Registros P+A+T+J`, etiquetas `1° Trim (T1)` / `Calificación Anual:`, y valores vacíos de `2° Trim`. Además, `grade_empty_bg` y `surface_variant` usan exactamente `#334155`, volviendo invisibles las píldoras `--` en `Anual`. |
| **KPI Justificados** | `#60A5FA` (`attendance_j_text`) | `#1E3A8A` (`attendance_j_bg`) | **4.46:1** | Límite / Falla en 10 px | KPI `Justificados` en `AsistenciasView` (además la etiqueta de `10 px` toca los bordes laterales de su caja) |
| **Días del `DatePickerDialog`** | `#0F172A` (`TEXT_MAIN` claro) | `#1E293B` (`surface`) | **1.22:1** | Roto / Ilegible | Números de día 1–30 en `Noviembre 2026` y `Octubre 2026` ([`date_picker_dialog.py:206-208`](../mobile/components/date_picker_dialog.py#L206-L208)) |

---

### 5.3 Colores Claros Hardcodeados, Sombras Invisibles y Modales sin Fondo Tokenizado

La inspección estática y en emulador identificó los siguientes puntos donde la UI rompe el Modo Oscuro por importar las constantes de compatibilidad de `LIGHT_TOKENS` (`PRIMARY`, `TEXT_MAIN`, `TEXT_MUTED`, `BORDER_COLOR`, `BG_PAGE`, `ATTENDANCE_P_*`) o definir colores literales:

1. **`DatePickerDialog`** ([`mobile/components/date_picker_dialog.py:170, 206-208`](../mobile/components/date_picker_dialog.py#L206-L208)): Pinta días sin asistencia con `TEXT_MAIN` (`#0F172A`) sobre `surface` (`#1E293B`, **1.22:1**), día seleccionado con `PRIMARY` claro (`#4F46E5`) en vez de `#818CF8`, días con asistencia usando `ATTENDANCE_P_BG` (`#DCFCE7` claro) / `ATTENDANCE_P_TEXT` y encabezado con `ft.Colors.SECONDARY`.
2. **`ComportamientoDialog`** ([`mobile/components/comportamiento_dialog.py:49-59, 123, 312-326, 506`](../mobile/components/comportamiento_dialog.py#L312-L326)): Define constantes claras (`COLOR_POS_BG="#DCFCE7"`, `COLOR_POS_TEXT="#166534"`, `COLOR_POS_SOLID="#10B981"`, `COLOR_REG_BG="#FEF3C7"`, `COLOR_REG_TEXT="#B45309"`, `COLOR_NEG_BG="#FEE2E2"`, `COLOR_NEG_TEXT="#991B1B"`). Al tocar `Positivo` en vivo, `_actualizar_estilo_botones_categoria` convierte los botones no seleccionados (`Regular` y `Negativo`) a fondo blanco `#F8FAFC` con texto `#0F172A` y borde `#E2E8F0`, y el activo a pastel claro `#DCFCE7` sobre el diálogo oscuro `#1E293B`.
3. **`GlobalSearchBar`** ([`mobile/components/global_search.py:72, 79, 89-100, 113-116, 207-247`](../mobile/components/global_search.py#L207-L247)): Hardcodea `TEXT_MAIN` (`#0F172A`), `TEXT_MUTED`, `BG_PAGE` (`#F8FAFC`), `BORDER_COLOR`, `PRIMARY`, `ft.Colors.GREY_500/600` y tonos `#0369A1`/`#6D28D9`. Los resultados en Modo Oscuro muestran títulos casi negros sobre fondo `#2B2930` y recuadros de ícono blancos.
4. **`SorteadorGruposDialog`** ([`mobile/components/grupos_sorteador_dialog.py:204-216, 236-247, 343, 357, 367, 392, 489-490`](../mobile/components/grupos_sorteador_dialog.py#L204-L247)): Al activar `Sortear con temas`, muestra un `Divider` blanco-gris brillante (`BORDER_COLOR` = `#E2E8F0`) atravesando el diálogo oscuro, un botón `+` en `PRIMARY` claro (`#4F46E5`) sobre fondo oscuro, `"Sin temas cargados aún."` en `TEXT_MUTED` (`#64748B`, **3.07:1**), y chips de temas con `bgcolor="#F1F5F9"`, `TEXT_MAIN` y `#EF4444`.
5. **`CalificarGrupoDialog`** ([`mobile/components/calificar_grupo_dialog.py:120, 158-170, 192, 207`](../mobile/components/calificar_grupo_dialog.py#L120)): Usa la comparación frágil `is_dark = (tok == DARK_TOKENS)` para el banner azul (`#EFF6FF`), mientras `L192` (`TEXT_MUTED`) y `L207` (`PRIMARY`) siguen hardcodeados en claro.
6. **`LocalBackupDialog` y `ExportDialog`** ([`mobile/components/local_backup_dialog.py:205, 210`](../mobile/components/local_backup_dialog.py#L205-L210), [`mobile/components/export_dialog.py:130, 135`](../mobile/components/export_dialog.py#L130-L135)): La insignia `"Al día (hoy)"` usa `ft.Colors.GREEN_600` sobre verde al 12 % encima de `#334155` (bajo contraste); `ExportDialog` hardcodea `ft.Colors.AMBER_400` / `ft.Colors.AMBER_600`.
7. **`EstadisticasView` y `PlanillasView`** ([`mobile/views/estadisticas_view.py:36-49, 1085-1100, 1348, 1480, 1503, 1526, 2192-2258, 2325-2357, 2500-2508`](../mobile/views/estadisticas_view.py#L36-L49), [`mobile/views/planillas_view.py:324-336`](../mobile/views/planillas_view.py#L324-L336)): Fijan colores literales de donut/histograma (`#10B981`, `#EF4444`, `#F59E0B`, `#34D399`, `#94A3B8`, `#CBD5E1`), badge `< 75%` en `#EF4444` con blanco, e íconos `"#6366F1"` / `"#10B981"` en `PlanillasView`.
8. **Sombras invisibles en `NotasView`** ([`mobile/views/notas_view.py:715, 741, 1100, 1314, 1668, 1679, 1690`](../mobile/views/notas_view.py#L715)): `ft.BoxShadow` utiliza `#0F172A0D` y `#0F172A14` — literalmente el mismo tono `#0F172A` de `DARK_TOKENS.bg_page`, eliminando toda separación por elevación en Modo Oscuro.
9. **`AlertDialog` que omiten `bgcolor=tok.surface`:** Cinco diálogos siguen usando superficie genérica M3 oscura (`#2B2930`): [`planillas_curso_dialog.py:272`](../mobile/components/planillas_curso_dialog.py#L272), [`main.py:470`](../mobile/main.py#L470) (primer inicio), [`asistencias_view.py:710`](../mobile/views/asistencias_view.py#L710), [`estadisticas_view.py:641`](../mobile/views/estadisticas_view.py#L641) (`Seleccionar Institución y Curso` con botón `"Cerrar"` aislado en la parte inferior) y [`planillas_view.py:447`](../mobile/views/planillas_view.py#L447).

---

### 5.4 Fricciones Visuales y de Densidad Detectadas con Datos Reales en Modo Oscuro

- **Pérdida de color semántico en celda enfocada (`NotasView`):** Al tocar una nota cargada (`P1 = 10` con dock abierto), la celda adopta `bgcolor=tok.primary_light` (`#1E1B4B`) y texto `#F8FAFC`, borrando visualmente el estado aprobado/desaprobado durante la edición.
- **Filas inferiores tapadas por la barra de gestos:** En `2DO A`, las últimas filas visibles en pantalla (`NotasView` `#5 Carrizo...` y `AsistenciasView` `#9 Delgado...`) quedan parcialmente cubiertas por el área de gestos inferior / barra de navegación.
- **Truncamiento de curso en `CONTEXTO ANALÍTICO` (`EstadisticasView`):** Con nombres reales (`Colegio: MEDIA DE LA REDUCCION...`), el título largo del colegio expulsa por completo el curso seleccionado (`2DO A`) de la tarjeta de contexto. Además, en la sección `Comportamiento`, la pestaña `"Comportamiento"` roza su borde derecho y la fila de filtros `Todos (0) · Positivo (0) · Regular (0) · Negativo (0)` llega al límite del ancho disponible sin margen para cifras de dos dígitos.
- **Recorte en histograma (`Calidad del Rendimiento`) y en `ExportDialog`:** En el histograma scrolleado de `2DO A`, las etiquetas inferiores de la barra `6-7` (`19` / `65.5%`) quedan recortadas contra el borde inferior del contenedor/footer; y en `ExportDialog`, elegir `"Una sola página"` deja visible solo el borde superior (`~6 px` ámbar) de `banner_advertencia` debajo del límite `height=min(480, calc_max_h)`.
- **Persistencia visual en `ExportEstadisticasDialog` en Dark Mode:** Confirmado también en Modo Oscuro que `info_card` se encoge al ~70 % del ancho del modal y mantiene emojis (`🏫`, `📚`, `📅`, `📄`) junto a un botón primario `"Exportar PDF"` de bajo contraste (**2.98:1**).

---

## 6. Backlog Priorizado para Diseño y Remediación (Sin Código Todavía)

### Prioridad P0 — Bloqueantes de Contraste, Legibilidad y Funcionalidad Visual
1. **Corregir tokens Dark Mode en botones primarios, estados y `text_subtle`:** Introducir `on_primary` (`#0F172A` sobre `#818CF8`, o ajustar `DARK_TOKENS.primary` para cumplir ≥ 4.5:1 con blanco), elevar `DARK_TOKENS.text_subtle` (`#64748B` → `>= 4.5:1` sobre `#1E293B`/`#0F172A`), aclarar `grade_fail_text`/`attendance_a_text` sobre `#7F1D1D` (**3.62:1** → ≥ 4.5:1), aclarar `grade_empty_text` sobre `#334155` (**4.05:1** → ≥ 4.5:1), diferenciar `grade_empty_bg` de `surface_variant`, y ajustar `attendance_j_text` sobre `#1E3A8A` (**4.46:1**).
2. **Corregir contraste en botones `P/A/T/J` de `AsistenciasView` (Claro y Oscuro):** Reemplazar `ft.Colors.WHITE` sobre rellenos sólidos (`1.67:1`–`2.76:1` en Dark Mode; `2.15:1`–`2.54:1` en Light Mode) por pares semánticos oscuros/claros de alto contraste o texto `#0F172A` sobre `attendance_*_solid` en Dark Mode.
3. **Eliminar colores claros hardcodeados fuera de `ThemeTokens`:** Refactorizar `DatePickerDialog` (días `#0F172A` en **1.22:1**), `ComportamientoDialog` (`#F8FAFC`/`#DCFCE7` en `_actualizar_estilo_botones_categoria`), `GlobalSearchBar`, `SorteadorGruposDialog` (`BORDER_COLOR`, `#F1F5F9`, `PRIMARY`, `TEXT_MUTED`), `CalificarGrupoDialog`, `LocalBackupDialog`, `ExportDialog`, `PlanillasView` y `EstadisticasView` para consumir exclusivamente `tok.*`, y añadir `bgcolor=tok.surface` a los 5 `AlertDialog` restantes.
4. **Corregir incompatibilidad `.name` → `.icon` en `NotasView`:** Solucionar chevrons invertidos y estado anual congelado en `⊖`.
5. **Corregir `GlobalSearchBar` (`x=135 px` gutter):** Pasar a búsqueda a pantalla completa / modal de ancho `100%`.

### Prioridad P1 — Jerarquía Visual, Espaciado y Consistencia del Layout
6. **Eliminar la doble cabecera superior:** Consolidar `AppBar` + `build_app_header` en un único sistema de cabecera contextual (en `ColegiosView` un header limpio con búsqueda + acciones sin repetir birrete; en subvistas, volver + título + acciones sin apilar una barra de búsqueda global encima).
7. **Compactar cabeceras de `NotasView` y preservar semántica en celda activa:** Unificar los selectores de trimestre (eliminar el selector duplicado dentro de la tarjeta o el superior), poblar píldoras resumen (`header_pills_containers`), mantener un borde/acento sin perder color de aprobado/desaprobado al enfocar celda, y sustituir `BoxShadow("#0F172A0D")` por borde/elevación perceptible en Modo Oscuro.
8. **Ajustar alturas de diálogos al contenido y evitar recortes:** Reemplazar `height=380/480/500/520` fijos por `tight=True` con altura máxima adaptativa y `scroll=ft.ScrollMode.AUTO` (incluyendo `ExportDialog` para que `banner_advertencia` sea visible al elegir `"Una sola página"`), más padding inferior en listas de `NotasView`/`AsistenciasView` e histograma de `EstadisticasView`.
9. **Corregir anchos internos de tarjetas y truncamiento con datos reales:** Expandir `info_card` en `ExportEstadisticasDialog` y `caja_preview` en `SorteadorGruposDialog` al 100 %, resolver la escalera de 3 botones en `StudentFormDialog`, y mostrar colegio + curso completo en `CONTEXTO ANALÍTICO` de `EstadisticasView`.
10. **Aplanar la jerarquía de `PlanillasView`:** Reducir de 3 contenedores anidados a 2 niveles limpios y acortar/desbordar limpiamente el chip `Estadísticas` y las pestañas/filtros de `EstadisticasView`.

### Prioridad P2 — Microcopy, Densidad, Accesibilidad y Pulido
11. **Corregir pluralización y textos:** `"1 institución registrada"`, `"1 curso registrado"`, `"1 activo"`, `"1 alumno"`, `"1 integrante"`, `"1 archivo"` en todas las vistas.
12. **Eliminar duplicidad de acciones:** Quitar `+` doble en `"+ Alumno"`, quitar el segundo ícono de calendario en `AsistenciasView`, ocultar `"Planificaciones"` cuando hay 0 cursos o `COPY_ALL` cuando hay 0 grupos, y quitar el borde de selección fantasma en `AsistenciasView`.
13. **Estandarizar etiquetas de accesibilidad y áreas táctiles ≥ 44–48 dp:** Añadir `semantics_label` / `tooltip` accesible a los `IconButton` de barras de herramientas y backspace del dock; ampliar altura de botones `P/A/T/J`, `+ Curso`, `+ Colegio`, `+ Tema` y `+ Calificar`.
14. **Resolver defectos de navegación/caché de estado detectados en pruebas:** Invalidar/refrescar `_curso_views` al volver entre `Notas`/`Asistencia`/`Grupos` y validar coincidencia de contexto en `navigate()` antes de hacer `pop_history()`.

# Notaly Mobile — Sistema de Diseño **"Crisp Editorial Ledger"** (`MASTER.md`)

**Versión del Sistema:** `2.0-editorial`  
**Paquete de Producción:** `com.notaly.app.notaly` (Android / iOS · `build_version = "2.0.0"`)  
**Runtime Verificado:** Python `3.13.9` · Flet `0.86.5` (Flutter `3.44.8` en CI)  
**Base de Evidencia:** Hallazgos de [`design-system/AUDIT.md`](./AUDIT.md) + auditoría integral de infraestructura, vistas y diálogos de `mobile/`.  
**Dirección Estética:** **Crisp Editorial Ledger** — interfaz docente editorial, sobria y de alta legibilidad basada en listas estructuradas con divisores finos, **cero píldoras**, radios de borde mínimos (`0–8px`), un único punto focal dominante por sección y cero *"AI slop"*.

---

## 1. Auto-Auditoría Obligatoria de Infraestructura e Invariantes

### 1.1 Inventario Activo de `.agents/` y Arnés de Ingeniería

La auditoría directa del árbol `.agents/` y los archivos raíz de gobernanza confirma la presencia de una metodología **Spec-Driven Development (SDD)** estricta:

| Categoría | Elementos Activos Inspeccionados | Directivas y Restricciones Relevantes para el Rediseño |
|---|---|---|
| **Constitución y Estado** | [`docs/constitution.md`](../docs/constitution.md), [`plan.md`](../plan.md), [`memory.md`](../memory.md) | 9 principios innegociables: desacoplamiento `core/` vs UI; puerta `pytest` en verde; preservación de scroll e *in-place updates*; notas enteras `1–10` con corte `< 5.50`; autoguardado con debounce sin botones manuales; sintaxis Flet `0.86+`; blindaje absoluto de `.github/workflows/build-apk.yml`; fechas `dd-mm-aaaa` y horas `hh:mm`; flujo SDD obligatorio previo a código. |
| **Agentes (`.agents/agents/`)** | [`coordinator.md`](../.agents/agents/coordinator.md), [`desarrollador_notaly.md`](../.agents/agents/desarrollador_notaly.md), [`planner.md`](../.agents/agents/planner.md), [`implementer.md`](../.agents/agents/implementer.md), [`reviewer.md`](../.agents/agents/reviewer.md) | `@coordinator` orquesta el flujo SDD; `@planner` redacta `spec.md` (EARS), `plan.md` y `tasks.md`; `@implementer` ejecuta una sola tarea TDD a la vez (prohibido editar `.agents/specs/**` o `.github/workflows/**`); `@reviewer` audita en solo lectura y emite `VEREDICTO: APROBADO` o `CAMBIOS NECESARIOS`. Todo código de dominio, comentarios y documentación debe redactarse en español. |
| **Comandos (`.agents/commands/`)** | [`sdd-spec.md`](../.agents/commands/sdd-spec.md), [`sdd-plan.md`](../.agents/commands/sdd-plan.md), [`sdd-tasks.md`](../.agents/commands/sdd-tasks.md) *(vacío, 0 bytes)*, [`sdd-implement.md`](../.agents/commands/sdd-implement.md), [`sdd-validate.md`](../.agents/commands/sdd-validate.md) | Flujo secuencial `/sdd-spec` → `/sdd-plan` → `/sdd-implement` → `/sdd-validate`. |
| **Skill `flet-mobile`** | [`.agents/skills/flet-mobile/SKILL.md`](../.agents/skills/flet-mobile/SKILL.md) | Prohibido reasignar `list_view.controls = [...]` ante eventos locales de tarjeta/trimestre/dock. Exige `ft.Alignment.CENTER`, `ft.Padding(...)`, `ft.Border.all(...)`; prohibido pasar `icon_size` a `ft.FilledButton`/`ft.Button`; servicios `FilePicker`/`Clipboard`/`Share` en `page.services`; `page.overlay` mutado *in-place*; apertura de archivos móviles vía [`share_helper.py`](../mobile/components/share_helper.py) (sin `xdg-open`); prohibido importar `tkinter`/`customtkinter`/`ctypes`; gráficos nativos (`flet.canvas`, sin matplotlib); PDFs vía `core/exportador.py` + `fpdf2` + `io.BytesIO()`; validación intermedia con `venv\Scripts\pytest.exe --ignore=tests/e2e` (sin ejecutar E2E en emulador autónomamente). |
| **Skill `proteccion-app-playstore`** | [`.agents/skills/proteccion-app-playstore/SKILL.md`](../.agents/skills/proteccion-app-playstore/SKILL.md) | Ofuscación en staging (`scripts/obfuscate_pipeline.py`) preservando código fuente legible; prohibido `MANAGE_EXTERNAL_STORAGE` y rutas cableadas a `/sdcard/Download`; uso exclusivo de almacenamiento privado de app + SAF `FilePicker`; anti-tampering `com.notaly.app`; artefactos `.aab` + `.apk` sin `.jks` en Git (`*.jks` excluido en [`.gitignore`](../.gitignore)). |
| **Skill `ui-ux-pro-max`** | [`.agents/skills/ui-ux-pro-max/SKILL.md`](../.agents/skills/ui-ux-pro-max/SKILL.md) (+ `data/` y `scripts/`) | Guías de contraste dual (`>= 4.5:1` claro y oscuro), objetivos táctiles (`>= 48dp` Android / `>= 44pt` iOS), espaciado `4/8dp`, prohibición de emojis como íconos estructurales (solo íconos vectoriales consistentes), *safe areas* y rendimiento de `ListView`. |
| **Specs Históricas (`.agents/specs/`)** | `005` a `027` + `autoguardado.md`, `feature_1_busqueda_movil_global.md`, `referencia_ui_flet.py`, `remake_ui_mobile.md` | Documentan la evolución actual hasta `SPEC-027` (475 tests internos + 34 tests E2E en verde registrados en [`memory.md`](../memory.md)). |
| **Carpetas inexistentes en `.agents/`** | `rules/` y `workflows/` no existen bajo `.agents/` | Las reglas viven en `docs/constitution.md` y `.agents/skills/`; el único workflow activo reside en `.github/workflows/build-apk.yml`. |

### 1.2 Entry Point Móvil, Empaquetado APK/AAB y Ruta Exacta de `assets/`

La inspección cruzada de [`pyproject.toml`](../pyproject.toml), [`.github/workflows/build-apk.yml`](../.github/workflows/build-apk.yml), [`mobile_app.py`](../mobile_app.py), [`mobile/main.py`](../mobile/main.py), [`scripts/obfuscate_pipeline.py`](../scripts/obfuscate_pipeline.py) y el código fuente del empaquetador `flet_cli.commands.build_base` (Flet `0.86.5`) confirma:

1. **Entry point oficial de compilación:** **`mobile_app.py`** en la raíz del repositorio.
   - [`pyproject.toml`](../pyproject.toml#L18-L28): `project_name = "notaly"`, `product_name = "Notaly"`, `org_name = "com.notaly.app"`, `module_name = "mobile_app"`, `build_version = "2.0.0"`, `[tool.flet.app] path = "."`, `module = "mobile_app"`.
   - [`.github/workflows/build-apk.yml`](../.github/workflows/build-apk.yml#L104-L138): ejecuta `flet build aab . --module-name mobile_app ...` y `flet build apk . --module-name mobile_app ...`.
   - [`mobile_app.py`](../mobile_app.py): inserta la raíz en `sys.path`, importa `main` desde `mobile.main` y ejecuta `flet.app.run(main)` (cuyo argumento por defecto en Flet `0.86.5` es `assets_dir="assets"`).
2. **Ruta exacta de `assets/` empaquetada por APK/AAB:** **`./assets/` (carpeta raíz del repositorio)**.
   - En `flet_cli.commands.build_base` (`L855-858`, `L1810`, `L2249-2250`), `package_app_path` se resuelve como `Path(python_app_path) / "."` (la raíz `.`) y `assets_path` como `package_app_path / "assets"`.
   - Actualmente existen dos carpetas de recursos:
     - **`./assets/`** (EMPAQUETADA EN BUILD): contiene `app_icon.png`, `icon.png`, `splash.png`.
     - **`./mobile/assets/`** (NO empaquetada por `flet build`): contiene duplicados `icon.png`, `splash.png`. Solo se resuelve si alguien ejecuta `python mobile/main.py` directamente desde consola porque [`mobile/main.py:524`](../mobile/main.py#L524) llama a `ft.app(target=main, assets_dir="assets")` (relativo al directorio del script).
   - **Directiva de fuentes y recursos:** Toda fuente `.ttf` nueva del sistema de diseño DEBE ubicarse en **`assets/fonts/`** (bajo la raíz `./assets/`), y el fallback `__main__` de `mobile/main.py` deberá apuntar a la carpeta raíz `assets/` (o ejecutarse vía `mobile_app.py`) para garantizar paridad en desarrollo y en APK/AAB.
3. **Pipeline de protección y compilación (intocable):**
   - `scripts/obfuscate_pipeline.py` procesa únicamente `TARGET_DIRS = ["core", "mobile"]` y `TARGET_FILES = ["mobile_app.py"]` usando `python_minifier` (`rename_globals=False`, `rename_locals=True`) y `compileall(..., optimize=2)`. No modifica `assets/`.
   - `[tool.flet.android.permission]` declara únicamente `READ_EXTERNAL_STORAGE` y `WRITE_EXTERNAL_STORAGE`.

### 1.3 Inventario Real de Estructura (`core/` y `mobile/`)

- **`core/` (INTACTO — 6 módulos + `__init__.py`):**
  `constants.py`, `calculos.py`, `gestor_datos.py`, `gestor_planillas.py`, `grupos.py`, `exportador.py`.
- **`mobile/` (Superficie de UI móvil):**
  - Núcleo de app: `main.py` (524 líneas), `state.py` (2241 líneas), `theme.py` (246 líneas).
  - **7 vistas (`mobile/views/`):** `colegios_view.py`, `cursos_view.py`, `notas_view.py`, `asistencias_view.py`, `grupos_view.py`, `estadisticas_view.py`, `planillas_view.py`.
  - **16 archivos en `mobile/components/` (19 clases `ft.AlertDialog` + componentes shell):**
    - Shell y utilidades: `footer.py` (`AppFooter`), `ui_header.py` (`SaveStatusIndicator`, `build_app_header`, `build_module_tabs`), `global_search.py` (`GlobalSearchBar`), `share_helper.py`.
    - Modales dedicados: `grade_editor.py` (`GradeEditorDialog`), `date_picker_dialog.py` (`DatePickerDialog`), `export_dialog.py` (`ExportDialog`), `export_estadisticas_dialog.py` (`ExportEstadisticasDialog`), `local_backup_dialog.py` (`LocalBackupDialog`), `planificacion_dialog.py` (`PlanificacionCursoDialog`), `planificaciones_institucion_dialog.py` (`PlanificacionesInstitucionDialog`), `planillas_curso_dialog.py` (`PlanillasCursoDialog`), `comportamiento_dialog.py` (`ComportamientoDialog`), `grupos_sorteador_dialog.py` (`SorteadorGruposDialog`, `ReasignarAlumnoDialog`), `calificar_grupo_dialog.py` (`CalificarGrupoDialog`), `student_dialog.py` (`StudentFormDialog`, `CreateEntityDialog`, `ColegioFormDialog`, `CreateCursoDialog`, `RenameDialog`, `ConfirmDeleteDialog`, `CustomizeColumnsDialog`).
    - Modales `ft.AlertDialog` inline adicionales: `Acerca de` y `Primer inicio / Restaurar copia` (`mobile/main.py`), `Asistencias sin guardar` (`asistencias_view.py`), `Cambios sin guardar` (`notas_view.py`), `Editar tema` y `Eliminar trabajo` (`grupos_view.py`), `¿Eliminar planilla?` (`planillas_view.py`), `¿Eliminar archivo?` (`planillas_curso_dialog.py`), `Seleccionar Institución y Curso` (`estadisticas_view.py`).

### 1.4 Reglas Inviolables de Retrocompatibilidad y Límites del Rediseño

1. **Prohibido tocar `core/`:** Ningún cambio en fórmulas (`redondeo_especial`, umbral `< 5.50`), constantes/claves JSON (`K_*`), I/O atómico (`_escribir_archivo_seguro`), búsqueda pura o exportación PDF/CSV/TXT.
2. **Prohibido alterar rutas locales, esquemas JSON, cifrado o migración v2.0.0:**
   - Rutas preservadas: `_get_config_dir()` (`FLET_APP_STORAGE_DATA / "Promediador"` en Android, `%APPDATA%\Promediador`, `~/.config/Promediador`), `datos_promedios.json`, `config_path.json`, `preferencias.json` (clave `"tema": "light" | "dark"` y `"auto_backup"`), `exports_index.json`, `copia de seguridad automatica notaly.json` y `.bak`.
   - `iniciador.py` (DRM Desktop Ed25519/Fernet) y `gui/*` (CustomTkinter Desktop) quedan completamente fuera de alcance.
   - `.github/workflows/build-apk.yml` es intocable.
3. **Alcance exclusivo del rediseño:**
   - `assets/fonts/` (paquete tipográfico offline `.ttf`).
   - `mobile/theme.py` (nuevos tokens editoriales duales + puente retrocompatible de propiedades/funciones para no romper suites existentes hasta su migración SDD).
   - `mobile/components/` (primitivos propios del sistema y migración de modales).
   - `mobile/views/` (las 7 vistas editoriales).
   - `mobile/main.py` (shell de cabecera única, registro `page.fonts`, `page.theme`/`dark_theme`, corrección de `navigate()` y `_curso_views`).
   - Enlace visual/navegación en `mobile/state.py` (corrección de preservación de `selected_colegio` en `pop_history()` y enlace visual de tema/contexto sin tocar métodos ni formatos de persistencia).
4. **Restricciones AST de Android ([`tests/test_android_compat.py`](../tests/test_android_compat.py)):** Prohibido en `mobile/` importar `tkinter`, `customtkinter`, `ctypes`; prohibido acceder directamente a `page.window.*`; prohibido usar `_MEIPASS` o rutas literales `C:\`.

---

## 2. Principios de Diseño — *"Crisp Editorial Ledger"*

La interfaz de Notaly adopta la estética de un **libro de actas docente contemporáneo**: alta legibilidad de aula (uso rápido con una mano, luz natural intensa o penumbra nocturna), jerarquía tipográfica nítida y estructura tabular disciplinada.

| Principio | Regla Operativa | Qué Elimina del Diseño Anterior |
|---|---|---|
| **1. Listas estructuradas sobre tarjetas pesadas** | Las entidades (colegios, cursos, alumnos, grupos, reportes) se presentan como **filas continuas de ancho completo (`0px` de radio)** dentro de secciones limpias delimitadas por divisores horizontales `1px border_hairline`. | Elimina tarjetas flotantes con bordes `16px`, sombras difusas invisibles en Dark Mode y el anidamiento de 3 cajas visto en `PlanillasView`. |
| **2. Cero píldoras (`0 pills`)** | Todo selector, filtro, celda numérica, badge de estado y botón usa geometría rectangular estricta (`border_radius <= 4px`), o pestañas planas con **subrayado inferior de `2px`**. | Elimina `ft.Chip`, cápsulas de `12–32px`, botones de `10–18px`, avatares circulares y micro-etiquetas ovaladas. |
| **3. Un punto focal dominante por sección** | Cada pantalla destaca **un único dato o acción rectora** mediante escala tipográfica tabular (`17–26sp` Bold `LedgerMono`), filete lateral semántico de `3px` o un único CTA rectangular `accent_primary` (`48dp`). | Elimina la competencia visual entre múltiples íconos sin etiqueta, cabeceras duplicadas y tarjetas donde todo tiene el mismo peso. |
| **4. Sobriedad editorial (cero *"AI slop"*)** | Paleta papel alabastro / grafito pizarra con acento Tinta Prusiana / Azul Pizarra Luminoso. Cero emojis estructurales, cero gradientes, cero neón/púrpura/índigo. | Elimina `#4F46E5`/`#818CF8`, tintes lavanda M3 (`#ECE6F0`/`#2B2930`), emojis `🏫📚🗓️📄💡` y subtítulos de relleno. |

---

## 3. Tokens de Color Duales Calibrados (Android e iOS)

Prohibido usar `#000000` o `#FFFFFF` como fondo base del lienzo, paletas púrpura/índigo, o colores literales fuera de `mobile/theme.py`.

### 3.1 Superficies, Tipografía y Acentos

| Token Canónico | Modo Claro (*"Warm Alabaster Ledger"*) | Modo Oscuro (*"Deep Graphite Slate"*) | Uso Obligatorio y Regla de Contraste |
|---|---|---|---|
| `bg_canvas` | `#F6F5F1` | `#111315` | Fondo base de `page.bgcolor` y vistas; separación sutil respecto a listas. |
| `surface_primary` | `#FCFBF9` | `#181B1F` | Fondo de secciones de lista, `NotalyTopHeader`, `NotalySheet`, `AppFooter` y dock numérico. |
| `surface_subtle` | `#ECEAE2` | `#20242A` | Fondo de celdas vacías sobre `surface_primary`, encabezados secundarios de sección o bloques informativos. |
| `surface_elevated` | `#FFFFFF` | `#262B32` | Celdas vacías anidadas dentro de `surface_subtle` (ej. valores `--` en panel Anual o botones numéricos del dock). |
| `text_primary` | `#18181B` | `#F1F3F5` | Títulos, nombres de colegios/cursos/alumnos, cifras KPI, valores de inputs. Ratio: **14.71–17.72:1** (Claro) / **12.81–16.74:1** (Oscuro). |
| `text_secondary` | `#52525B` | `#A1A8B3` | Subtítulos, eyebrows (`11sp`), fechas, metadatos con `·`, etiquetas de pestañas inactivas, botones `Outlined`/neutros. Ratio: **6.42–7.47:1** (Claro) / **6.51–7.77:1** (Oscuro). |
| `text_muted` | `#71717A` | `#757D8A` | **Uso estrictamente restringido:** placeholders de `TextField`, guiones `-` de celdas `Recup` deshabilitadas o íconos meramente decorativos. *(Ratio `4.01–4.67:1` en Claro y `3.75–4.48:1` en Oscuro; **PROHIBIDO** usarlo en eyebrows de `11sp` o metadata crítica, donde debe usarse `text_secondary`)*. |
| `border_hairline` | `#DCD8CE` | `#2D333B` | Divisores horizontales de `1px`, bordes de filas/inputs/celdas neutras y líneas base de tablas. |
| `accent_primary` | `#1B3B5A` *(Tinta Prusiana)* | `#7FB3D5` *(Azul Pizarra Luminoso)* | Único CTA primario de sección, borde de foco activo (`2px`), indicador de `UnderlineTabBar`, ícono activo de navegación. Ratio sobre `surface_primary`: **11.16:1** (Claro) / **7.66:1** (Oscuro). |
| `accent_on_primary` | `#FCFBF9` | `#0D1B2A` | Texto e ícono **obligatorio** sobre botones o celdas rellenas con `accent_primary`. Ratio: **11.16:1** (Claro) / **7.71:1** (Oscuro) — *corrige el fallo `2.98:1` de `AUDIT.md`*. |
| `accent_subtle` | `#E4ECF4` | `#1B2A38` | Fondo de monogramas institucionales, indicador activo de `NavigationBar`, resaltado suave interactivo. Ratio de `accent_primary` encima: **9.67:1** (Claro) / **6.49:1** (Oscuro). |
| `accent_hover` | `#132B42` | `#9CC5E0` | Estado *pressed* / *hover* sobre `accent_primary`. |

### 3.2 Estados Semánticos Calibrados (WCAG AA+ >= 4.5:1)

Cada estado semántico se define por una **tríada indivisible (`bg`, `fg`, `border`)**. Queda prohibido combinar `fg` claro con `bg` oscuro o usar `ft.Colors.WHITE` sobre fondos semánticos.

| Estado Semántico | Claro (`bg` / `fg` / `border`) | Ratio Claro (`fg` / `bg`) | Oscuro (`bg` / `fg` / `border`) | Ratio Oscuro (`fg` / `bg`) | Aplicación en Notaly |
|---|---|---|---|---|---|
| **Aprobado / Presente (`P`) / Positivo** | `#E6F4EA` / `#135E3D` / `#B7DFC5` | **6.86:1** *(AAA cercano)* | `#142E24` / `#6EE7B7` / `#234E3D` | **9.53:1** *(AAA)* | Notas `>= 6`, promedio `>= 5.50`, estado `P`, comportamiento `Positivo`, indicador `Guardado`. |
| **En Riesgo / Tardanza (`T`) / Regular** | `#FEF3C7` / `#92400E` / `#FDE68A` | **6.37:1** *(AA+)* | `#332512` / `#FCD34D` / `#573E1C` | **10.30:1** *(AAA)* | Estado `T` (Tarde), comportamiento `Regular`, advertencias (PDF 1 pág., `Guardando...`), alumnos en umbral de riesgo (`6` límite o asistencia `75–80%`). |
| **Desaprobado / Ausente (`A`) / Negativo** | `#FEE2E2` / `#991B1B` / `#FECACA` | **6.80:1** *(AA+)* | `#35181B` / `#FCA5A5` / `#5C262C` | **8.53:1** *(AAA)* | Notas `< 6`, promedio `< 5.50`, estado `A` (Ausente), alerta `< 75%`, comportamiento `Negativo`, acciones destructivas (`Eliminar`). |
| **Justificado (`J`) / Informativo** | `#E4ECF4` / `#1B3B5A` / `#C2D4E6` | **9.67:1** *(AAA)* | `#1A2838` / `#93C5FD` / `#2B425C` | **8.29:1** *(AAA)* | Estado `J` (Justificado), avisos informativos (ej. aislamiento de nota grupal en `CalificarGrupoDialog`). |
| **Vacío / Pendiente (`--` / `-`)** | `#ECEAE2` / `#52525B` / `#DCD8CE` | **6.42:1** *(AA+)* | `#262B32` / `#A1A8B3` / `#2D333B` | **5.71:1** *(AA+)* | Celdas sin nota `--`, `Sin Calificar` (en Anual sobre `surface_subtle` `#20242A`, `surface_elevated` `#262B32` garantiza separación visible). |

### 3.3 Paleta de Gráficos Vectoriales y Monogramas Editoriales

- **Donut y Histograma (`EstadisticasView`):** Prohibido el uso de constantes hardcoded (`#10B981`, `#EF4444`, `#F59E0B`, `#34D399`, `#CBD5E1`, `#6366F1`). Los segmentos de `flet.canvas` e histogramas consumen tokens del tema activo:
  - Aprobado / Presente / Positivo / Rango `8–10`: `pass_fg` (`#135E3D` claro / `#6EE7B7` oscuro).
  - Rango `6–7` (Bueno): `pass_border` reforzado (`#2E7D5B` claro / `#34D399` oscuro).
  - Rango `4–5` / Tarde / Regular: `warn_fg` (`#92400E` claro / `#FCD34D` oscuro).
  - Rango `1–3` / Desaprobado / Ausente / Negativo: `fail_fg` (`#991B1B` claro / `#FCA5A5` oscuro).
  - Justificado: `justif_fg` (`#1B3B5A` claro / `#93C5FD` oscuro).
  - Sin calificar / Barra vacía: `border_hairline` para trazo/barra base, `text_secondary` para etiquetas `0`.
- **Monogramas Editoriales de Entidad (`get_avatar_palette`, `radius=4px`):** Reemplazan los avatares circulares púrpura/rosa neon por 5 tonos editoriales sobrios (Prusiano `#E4ECF4/#1B3B5A`, Salvia `#E6F4EA/#135E3D`, Ocre `#FEF3C7/#92400E`, Terracota `#F5E8E4/#8C2D19`, Grafito `#ECEAE2/#3F3F46` en claro; y sus pares oscuros `#1B2A38/#93C5FD`, `#142E24/#6EE7B7`, `#332512/#FCD34D`, `#361E1A/#FDBA74`, `#20242A/#CBD5E1` — todos `>= 6.0:1`).

### 3.4 Puente Retrocompatible en `mobile/theme.py`

Para mantener compatibilidad con los 475 tests unitarios existentes durante la transición SDD (`tests/test_tema_preferencias.py`, `tests/ui/*`), `ThemeTokens` incorporará los tokens canónicos de *"Crisp Editorial Ledger"* junto con propiedades/campos alias retrocompatibles:
- `bg_page` ↔ `bg_canvas` | `surface` ↔ `surface_primary` | `surface_variant` ↔ `surface_subtle` | `border_color` ↔ `border_hairline`
- `primary` ↔ `accent_primary` | `on_primary` ↔ `accent_on_primary` | `primary_light` ↔ `accent_subtle` | `primary_hover` ↔ `accent_hover`
- `text_main` ↔ `text_primary` | `text_muted` ↔ `text_secondary` | `text_subtle` ↔ `text_muted`
- `grade_pass_border`, `grade_fail_border`, `grade_empty_border`, `attendance_*_border`, `attendance_*_solid` (donde `solid` en el nuevo sistema apunta al trazo/acento semántico de alto contraste, **nunca** con `ft.Colors.WHITE` encima).

---

## 4. Punto Fuerte y Jerarquía Visual por Sección (Inventario Completo)

Cada vista de Notaly se organiza en torno a **un punto focal dominante único**, garantizando escaneo inmediato y acceso en un toque sin sobrecarga visual:

| Vista (`mobile/views/`) | Punto Focal Dominante (Preside la Vista) | Mecanismo de Realce Editorial | Estructura de Lista y Subordinación | Remediación Específica de `AUDIT.md` |
|---|---|---|---|---|
| **`colegios_view.py`** | **Nombre de Institución + Conteo tabular (`cursos · alumnos`)** y botón primario **`+ Colegio`**. | Nombre en `16sp` SemiBold `text_primary`; resumen derecho en `13sp` Medium `LedgerMono` (`text_secondary`); CTA único rectangular `accent_primary` (`48dp` alto, `radius=4`). | Filas planas de ancho completo (`NotalyListRow`) con monograma cuadrado `40×40dp` (`radius=4`), dirección/horarios en 1 línea compacta con `·` y menú `⋮` (`48×48dp`) hacia `NotalySheet`. | Elimina doble cabecera (`AppBar` + `build_app_header` con doble birrete); elimina ícono `INSIGHTS` redundante fuera del sheet; corrige pluralización (`1 institución registrada`, `1 curso registrado`); botón `+ Colegio` sube de `36dp` a `48dp`. |
| **`cursos_view.py`** | **Acceso directo a Planilla del curso** (fila primaria completa) y diferenciación clara hacia **Planificaciones**. | Título de curso `16sp` SemiBold + conteo tabular `N alum.` en `14sp` `LedgerMono` a la derecha + chevron `>`. Botón secundario **`Planificaciones`** (`48dp` alto, `1px border_hairline`, fondo `surface_primary`) junto al CTA **`+ Curso`** (`48dp`, `accent_primary`). | Filas limpias sin subtítulos de relleno. Línea secundaria real: `horario · N clases planificadas` (o solo `horario` si `num_clases == 0`). Menú `⋮` abre `NotalySheet` con acciones directas (`Planilla de Notas`, `Asistencias`, `Grupos`, `Planificaciones`, `Estadísticas`, `Renombrar`, `Eliminar` en `fail_fg`). | Oculta el botón `"Planificaciones"` cuando hay `0 cursos`; elimina textos estáticos `"Planilla y gestión integral"` y `"Ciclo Lectivo Activo"`; corrige `"1 curso activo"`; elimina botón calendario duplicado de tarjeta; sube botones a `48dp`. |
| **`notas_view.py`** | **Columna/celda de Promedio / Nota Final** (`GradeCell` dominante) + **filete lateral semántico de `3px`**. | Celda final derecha en **`17sp` Bold `LedgerMono`** (`48×40dp`, `radius=4`, par semántico `pass`/`fail`/`empty`) acompañada por filete vertical izquierdo de `3px` (`pass_fg`/`fail_fg`/`border_hairline`). | Lista de `NotalyListRow`: en fila **colapsada**, nombre (`#N Apellido, Nombre`) + resumen tabular continuo separado por `·` (`1°T 8 · 2°T 7 · 3°T --`); al **expandir**, slots `P1/P2/P3/Extra/Recup` (`14sp` `LedgerMono`, subordinados frente al `17sp` final) y fila compacta de `Comportamiento`. | Reduce 5 barras apiladas a 2 niveles fijos (`NotalyTopHeader` + `UnderlineTabBar` de módulos; selector de período `1° Trim \| 2° Trim \| 3° Trim \| Anual` y acciones integradas); elimina selector duplicado `Trimestre 1/2/3` dentro de la tarjeta; puebla resumen colapsado; corrige `.name` → `.icon`; conserva color semántico en celda activa usando solo borde `2px accent_primary`; oculta herramientas de edición en `Anual`; quita doble `+` de `+ Alumno`; unifica `#N Sin nombre`; eleva `surface_elevated` en celdas vacías de `Anual`. |
| **`asistencias_view.py`** | **Cabecera de fecha navegable (`48×48dp`)** + **selector rectangular `P / A / T / J` con estado único iluminado**. | Selector de fecha central con fecha tabular `dd-mm-aaaa` (`15sp` Bold `LedgerMono`) flanqueada por botones `48×48dp` (`<`, `>`, `Hoy`). En cada fila, `AttendanceCellGroup` (`44dp` alto, `radius=4`) resalta **únicamente la opción activa** en su par semántico (`>= 6.37:1`); las 3 inactivas permanecen neutras (`surface_primary`, `1px border_hairline`, `text_secondary`). | Filete lateral `3px` reflejando la marca del alumno (`P`/`A`/`T`/`J` o neutro); banda de resumen superior compacta de 2 líneas o 4+1 tabular (`P · A · T · J` + `% Asist.` en `16sp` Bold `LedgerMono`); CTA rectangular **`Todos Presentes`** (`48dp` alto). | Elimina segundo botón de calendario `EVENT`; elimina borde índigo "fantasma" de `is_active_card`; corrige fallos críticos de contraste (`1.67:1`–`2.76:1` → `6.37:1`–`10.30:1`); libera ancho horizontal para evitar truncar nombres; corrige desincronización de `_curso_views["asistencias"]`. |
| **`grupos_view.py`** | **Botón destacado `Sortear Grupos`** (`48dp`) + **Nota Grupal tabular dominante** sobre integrantes. | CTA rectangular **`Sortear Grupos`** (`48dp` alto, `accent_primary`) en zona superior accesible; en cada bloque de grupo (`NotalyListSection`), cabecera con título + tema rectangular editable (`44dp` hit area) y **`GradeCell` dominante (`17sp` Bold `LedgerMono`)** + filete lateral `3px` si calificado. | Selector de trabajos prácticos con `UnderlineTabBar` horizontal (cero chips ovalados); lista plana de integrantes con botón táctil `Reasignar` (`44–48dp`, `text_secondary` visible) y observación editorial en `surface_subtle`. | Elimina múltiples puntos de entrada redundantes (`CASINO`, `+ Nuevo Trabajo`, `ADD_CARD`); reemplaza micro-píldoras `+ Tema` y `+ Calificar` (`16–20dp`) por controles rectangulares `>= 44dp`; deshabilita/oculta `Copiar lista` en estado vacío. |
| **`estadisticas_view.py`** | **Bloque superior de KPIs críticos (`24–26sp` tabular)** + **Lista priorizada de Alumnos en Riesgo (`3px` lateral)**. | Banda superior con 3 KPIs críticos sin redundancia: **Promedio General**, **% Aprobación** y **En Riesgo** (desaprobados o asistencia `< 75%`) en `24–26sp` Bold `LedgerMono`. Debajo inmediato: lista priorizada de alumnos en riesgo con **filete lateral `3px` (`fail_fg` / `warn_fg`)** y valor tabular derecho; luego Donut e Histograma. | Cabecera de contexto de 2 líneas libres (sin truncar `Colegio` ni `Curso`) con botón `Cambiar` (`48dp`) que abre `NotalySheet`; `UnderlineTabBar` para `Calificaciones \| Comportamiento \| Asistencias` y períodos cortos `1° Trim \| 2° Trim \| 3° Trim \| Anual`. | Elimina duplicación exacta entre grid KPI 2×2 y Donut; unifica bordes KPI inconsistentes; elimina truncamientos (`"Resume"`, `"Comportamiento"`, `"Instit..."`); reemplaza modal vacío lavanda de contexto por `NotalySheet`; colapsa dropdowns de fecha cuando `"Todas las fechas"` está activo; tokeniza colores de Donut/Histograma; asegura `bottom >= 88dp` para no recortar etiquetas inferiores. |
| **`planillas_view.py`** | **Lista de reportes disponibles y exportados con acción rectangular directa (`48dp`) a la derecha**. | Lista plana de 2 niveles máximo (`NotalyListSection` por institución colapsable → `NotalyListRow` por reporte/archivo). Cada fila reserva a la derecha una **acción rectangular de `48dp` de alto (`radius=4`)**: `Generar` / `Exportar` (para reportes disponibles de curso/institución) o `Abrir` (para planillas exportadas, con `Compartir`/`Eliminar` en menú `⋮` / `NotalySheet`). | Filtros planos en `UnderlineTabBar` (`Todas \| Notas \| Asist. \| Stats`) sin recorte horizontal; subtítulo tabular en `LedgerMono` (`Tipo · dd-mm-aaaa hh:mm · KB`). | Aplana el árbol de 3 cajas anidadas a 2 niveles planos; corrige `"1 archivo(s)"` → `"1 archivo"` / `"N archivos"`; agrega `bgcolor=tok.surface_primary` al modal de eliminación (o usa `NotalySheet`); elimina hex hardcoded `#6366F1` y `#10B981`. |

---

## 5. Geometría Arquitectónica y Formato de Lista

### 5.1 Escala Estricta de Radios de Borde (`border_radius`)

| Categoría de Control | Radio Permitido | Regla Estricta |
|---|---|---|
| **Filas de lista, divisores, headers, tab bars** | **`0px`** | `NotalyListRow`, divisores `1px border_hairline`, `NotalyTopHeader`, `UnderlineTabBar`. |
| **Botones, inputs, celdas, selectores, monogramas** | **`4px` máximo** | `FilledButton` / CTA rectangular, `OutlinedButton`, `TextField`, `GradeCell`, `AttendanceCellGroup`, teclas del dock numérico, monogramas de iniciales (`40×40dp`), badges rectangulares de estado. |
| **Contenedores de sección / bloques gráficos** | **`6px` máximo** | `NotalyListSection` (cuando lleve marco externo), contenedor de Donut / Histograma / Resumen KPI. |
| **Bottom Sheets (`NotalySheet`)** | **`8px` solo arriba** | `ft.BorderRadius.only(top_left=8, top_right=8, bottom_left=0, bottom_right=0)`. Diálogos de confirmación compactos: `6px` máximo. |
| **PROHIBIDO** | **`>= 12px` / `999px`** | Prohibidas cápsulas, óvalos, avatares circulares (`radius=18/20/32`), `ft.Chip` y botones `radius=10/16/18`. |

### 5.2 Ritmo Espacial (`4dp / 8dp`) y Reglas de Lista

- **Escala de espaciado:** `SPACE_XS = 4`, `SPACE_SM = 8`, `SPACE_MD = 12`, `SPACE_LG = 16`, `SPACE_XL = 24`, `SPACE_XXL = 32`.
- **Layout centrado en listas:**
  - Cero tarjetas dentro de tarjetas. Una sección agrupa filas separadas por un único divisor inferior `ft.Border.only(bottom=ft.BorderSide(1, tok.border_hairline))`.
  - Margen horizontal interno de fila: `16dp` (o `12dp` en pantallas `< 360dp`); padding vertical `12dp`; altura mínima de fila: `56dp` (1 línea) o `68dp` (2 líneas).
  - Filete semántico lateral: contenedor/borde izquierdo de `3px` de ancho (`ft.Border.only(left=ft.BorderSide(3, estado_fg))`), reservado únicamente para comunicar estado académico/asistencia o foco de riesgo.
- **Filtros y resúmenes sin píldoras:**
  - **Filtros / Períodos / Módulos:** `UnderlineTabBar` plana (`height=44–48dp`), texto `13sp`, indicador inferior de `2px` en `accent_primary`.
  - **Resúmenes colapsados (ej. `NotasView`):** texto tabular continuo separado por puntos medios (`·`) en `LedgerMono` `12sp`, p. ej. `1°T 8 · 2°T 7 · 3°T --`, aplicando el color semántico (`pass_fg` / `fail_fg` / `text_secondary`) únicamente sobre los dígitos, sin fondo ni borde de cápsula.

---

## 6. Tipografía Offline y Alineación Numérica

### 6.1 Fuentes Seleccionadas (Licencia Abierta SIL OFL-1.1)

| Rol Tipográfico | Familia | Pesos Empaquetados (`.ttf`) | Ruta en Repo y APK/AAB | Alias `page.fonts` |
|---|---|---|---|---|
| **Editorial UI / Prosa** | **Plus Jakarta Sans** *(alternativa aceptada: Inter)* | `Regular` (400), `Medium` (500), `SemiBold` (600), `Bold` (700) | `assets/fonts/PlusJakartaSans-*.ttf` | `"LedgerSans"` |
| **Numérica Tabular** | **JetBrains Mono** | `Regular` (400), `Medium` (500), `Bold` (700) | `assets/fonts/JetBrainsMono-*.ttf` | `"LedgerMono"` |

- **Registro en `mobile/main.py` (antes de construir controles):**
  ```python
  page.fonts = {
      "LedgerSans": "fonts/PlusJakartaSans-Regular.ttf",
      "LedgerSans-Medium": "fonts/PlusJakartaSans-Medium.ttf",
      "LedgerSans-SemiBold": "fonts/PlusJakartaSans-SemiBold.ttf",
      "LedgerSans-Bold": "fonts/PlusJakartaSans-Bold.ttf",
      "LedgerMono": "fonts/JetBrainsMono-Regular.ttf",
      "LedgerMono-Medium": "fonts/JetBrainsMono-Medium.ttf",
      "LedgerMono-Bold": "fonts/JetBrainsMono-Bold.ttf",
  }
  ```
  *(Nota: verificar en runtime si Flet mapea pesos desde un archivo variable o fuentes estáticas por familia; registrar variantes estáticas o un `.ttf` variable bajo `"LedgerSans"` y `"LedgerMono"` con `ft.Theme(font_family="LedgerSans")` garantiza renderizado 100% offline en Android e iOS sin acceso a CDN ni Google Fonts).*

### 6.2 Alineación Numérica en Flet `0.86.5` (Nota Crítica de Compatibilidad)

La verificación directa sobre `flet==0.86.5` en el entorno del proyecto confirmó que **`ft.FontFeature` no existe** (`hasattr(ft, "FontFeature") == False`) y tanto `ft.Text(..., font_features=...)` como `ft.TextStyle(..., font_features=...)` lanzan **`TypeError` en tiempo de ejecución**.

Para cumplir el requisito de alineación tabular estricta en promedios, notas, fechas y porcentajes **sin romper Flet `0.86.5`**:
1. Todos los controles numéricos, fechas (`dd-mm-aaaa`), porcentajes (`85.5%`), notas (`1`–`10`), KPIs e IDs (`#12`) DEBEN renderizarse con **`font_family="LedgerMono"`** (`JetBrains Mono`), cuyo ancho de avance es nativamente monoespaciado/tabular en todos los dígitos y símbolos (`0–9`, `.`, `-`, `%`, `/`).
2. Centralizar un helper `tabular_text(value, ...)` en `mobile/theme.py` que fije `font_family="LedgerMono"` y únicamente adjunte `font_features=[ft.FontFeature.tabular_figures()]` bajo guardia defensiva `if hasattr(ft, "FontFeature")` para compatibilidad futura si Flet lo expone en versiones posteriores.

### 6.3 Escala Tipográfica Editorial

| Token Tipográfico | Familia | Tamaño (`sp`) | Peso | Uso |
|---|---|---|---|---|
| `display_kpi` | `LedgerMono` | `24–26` | `BOLD` | KPIs críticos superiores en `EstadisticasView`. |
| `grade_dominant` | `LedgerMono` | `17` | `BOLD` | Promedio / Nota Final en `NotasView` y Nota Grupal en `GruposView`. |
| `title_header` | `LedgerSans` | `18` | `BOLD` | Título único de `NotalyTopHeader`. |
| `title_row` | `LedgerSans` | `15–16` | `W_600` (`SemiBold`) | Nombres de instituciones, cursos, alumnos y títulos de sección. |
| `body_primary` | `LedgerSans` | `14` | `W_500` / `NORMAL` | Cuerpo de texto, opciones de sheets, inputs, CTAs. |
| `numeric_cell` | `LedgerMono` | `14` | `BOLD` | Celdas `P1/P2/P3/Extra/Recup`, teclas de dock, botones `P/A/T/J`. |
| `meta_tabular` | `LedgerMono` / `LedgerSans` | `12–13` | `W_500` / `NORMAL` | Fechas, porcentajes, resúmenes `1°T 8 · 2°T 7`, subtítulos de fila (`text_secondary`). |
| `eyebrow_label` | `LedgerSans` | `11` | `BOLD` (UPPERCASE) | Etiquetas de sección y rótulos de columna (`color=tok.text_secondary` obligatorio para contraste `>= 6.4:1`). |

---

## 7. Consolidación de Cabeceras, Búsqueda Global y Primitivos Custom (`mobile/components/`)

### 7.1 Eliminación de Doble Cabecera (`NotalyTopHeader`)

Se elimina por completo la convivencia de `page.appbar` + `build_app_header`. Toda la navegación superior se consolida en un único componente **`NotalyTopHeader`** (`height=56dp` dentro de `ft.SafeArea(avoid_intrusions_top=True, avoid_intrusions_bottom=False)`, fondo `surface_primary`, borde inferior `1px border_hairline`):

- **Variante Raíz (`ColegiosView`, `PlanillasView`, `EstadisticasView`):**
  - Izquierda: Wordmark/título en `18sp` Bold (`"Notaly"`, `"Planillas"`, `"Estadísticas"` — sin doble birrete).
  - Derecha (máx. 3 botones táctiles `48×48dp` sin etiquetas duplicadas): `Buscar` (`Icons.SEARCH`), `Tema` (`Icons.DARK_MODE_OUTLINED` / `Icons.LIGHT_MODE_OUTLINED`), `Más` (`Icons.MORE_VERT` → abre `NotalySheet` con *Copia de Seguridad* y *Acerca de*).
- **Variante Subvista (`CursosView`, `NotasView`, `AsistenciasView`, `GruposView`):**
  - Izquierda: `IconButton` `Volver` (`48×48dp`, `tooltip="Volver"`).
  - Centro (`expand=True`): Título de 1 sola línea (`max_lines=1`, `ELLIPSIS`), p. ej. `"3° A · Colegio X"` (evita apilar eyebrow + título cuando comprime viewport).
  - Derecha: Micro-texto discreto de autoguardado (`"Guardado"` / `"Guardando..."`, `11sp` en `pass_fg`/`warn_fg`, sin píldora) + máx. 1–2 acciones `48×48dp` (`Planificación` / `Herramientas`).
- **En el bloque Curso (`Notas`, `Asistencia`, `Grupos`):** Máximo **2 niveles fijos** arriba del área desplazable:
  1. `NotalyTopHeader` (56dp + safe area).
  2. `UnderlineTabBar` de módulos (`Notas | Asistencia | Grupos`, 44dp).
  *El selector de período (`1° Trim | 2° Trim | 3° Trim | Anual`) y las acciones del curso se integran limpiamente al inicio del scroll o mediante fila compacta de 1 nivel, reduciendo de ~650px (5 barras) a ~100dp fijos.*

### 7.2 Rediseño de Búsqueda Global (`GlobalSearchOverlay`)

Reemplaza a `ft.SearchBar(full_screen=False)` en `AppBar.title` (causante del desplazamiento `x=135px` / `945px` ancho y texto ilegible `#0F172A` sobre `#2B2930`):
- **Disparador:** `IconButton` `48×48dp` en `NotalyTopHeader` (y opcionalmente un campo trigger rectangular ancho completo al tope de `ColegiosView` en estado de lista extensa).
- **Overlay de Pantalla Completa (`100%` ancho × `100%` alto):** Contenedor o ruta overlay dentro de `ft.SafeArea` con fondo `tok.bg_canvas`, cabecera de búsqueda de `56dp` (`bg=tok.surface_primary`, borde inferior `1px border_hairline`, botón `Volver` `48×48dp`, `TextField` sin borde externo con `autofocus=True` y botón `Limpiar` `48×48dp`).
- **Resultados:** Lista de `NotalyListRow` (`bg=tok.surface_primary`, divisor `1px border_hairline`) con monograma `4px` (`accent_subtle` para Colegios, `justif` para Cursos, `pass`/`neutral` para Alumnos) y tipografía 100% tokenizada (`text_primary` / `text_secondary`), funcionando idénticamente en Modo Claro y Oscuro.

### 7.3 Primitivos Custom Obligatorios en `mobile/components/`

1. **`NotalySheet` (`mobile/components/notaly_sheet.py`):**
   - Basado en `ft.BottomSheet` (`bgcolor=tok.surface_primary`, `use_safe_area=True`, `scrollable=True`, `shape=ft.RoundedRectangleBorder(radius=ft.BorderRadius.only(top_left=8, top_right=8))`).
   - Tirador superior centrado (`32×3dp`, `tok.border_hairline`), cabecera con título (`16sp` Bold) y botón cerrar (`48×48dp`).
   - Cuerpo con `ft.Column(tight=True, scroll=ft.ScrollMode.AUTO)` y restricción adaptativa `max_height = 0.85 * page_height` (nunca altura fija estática).
   - Barra inferior de acciones controlada (`Row` con máx. 2 botones `height=48dp`, `radius=4`, o CTA único de ancho completo + acción destructiva/secundaria separada), erradicando la escalera vertical de botones.
2. **`NotalyListSection`:**
   - Contenedor editorial para agrupar filas relacionadas (`bgcolor=tok.surface_primary`, `border=ft.Border.all(1, tok.border_hairline)`, `border_radius=6` en secciones agrupadas o `0` de borde a borde), con cabecera opcional (`eyebrow` en `text_secondary` + acción derecha).
3. **`NotalyListRow`:**
   - Fila rectangular (`border_radius=0`, `min_height=56dp`, `padding=ft.Padding(16, 12, 16, 12)`), divisor inferior `1px tok.border_hairline` (omitido en última fila de sección), soporte de `stripe_color` (`3px` borde izquierdo semántico), bloque central `expand=True` con `max_lines=1`/`ELLIPSIS`, resumen tabular continuo opcional con `·` y slot derecho alineado.
4. **`UnderlineTabBar`:**
   - Fila plana (`height=44–48dp`, `bgcolor=tok.surface_primary`, borde inferior base `1px tok.border_hairline`).
   - Cada pestaña es un `Container(expand=True, alignment=CENTER, ink=True)` con texto `13sp` (`W_600` y `tok.accent_primary` si activo; `W_500` y `tok.text_secondary` si inactivo) y `ft.Border.only(bottom=ft.BorderSide(2, tok.accent_primary))` únicamente en la pestaña activa.
5. **`AttendanceCellGroup`:**
   - Fila de 4 botones rectangulares (`P`, `A`, `T`, `J`), `border_radius=4`, altura `44dp` (área táctil efectiva `44–48dp`), separación `4dp`.
   - **Estado activo:** `bgcolor=sem_bg`, `border=1.5px sem_border` (o `sem_fg` sutil), `text_color=sem_fg`, `weight=BOLD` (`LedgerMono`).
   - **Estados inactivos:** `bgcolor=tok.surface_primary`, `border=1px tok.border_hairline`, `text_color=tok.text_secondary`, `weight=NORMAL` — evita ruido visual y garantiza contraste `>= 6.37:1` en activo y `>= 6.5:1` en inactivo.
6. **`GradeCell`:**
   - Celda rectangular (`border_radius=4`, tamaño dominante `48×40dp` / `17sp` Bold `LedgerMono` para nota final o promedio; `expand=True, height=44dp` / `14sp` Bold para slots de carga).
   - **Preservación semántica en foco:** Cuando `is_active=True` (editando con dock), **conserva `bgcolor` y `text_color` del valor actual** (aprobado/desaprobado/vacío) y aplica únicamente `border=ft.Border.all(2, tok.accent_primary)`.
   - **Estado deshabilitado (`Recup` bloqueado):** `bgcolor=tok.bg_canvas`, `border=1px tok.border_hairline`, texto `"-"` en `tok.text_muted`, `ink=False`.
7. **`EmptyStateView`:**
   - Contenedor centrado con padding `24–32dp`, ícono vectorial `32dp` en `tok.text_secondary` dentro de recuadro `56×56dp` (`radius=4`, `tok.surface_subtle`, borde `1px tok.border_hairline`), título `16sp` SemiBold, descripción `13sp` `tok.text_secondary` y máximo 1 CTA rectangular `48dp`.

### 7.4 Plan de Remediación de los 19 Diálogos y Modales Existentes

| Grupo de Modales | Componente Destino | Correcciones Obligatorias respecto a `AUDIT.md` |
|---|---|---|
| **Menús contextuales de tarjetas y cabecera** (`ColegiosView`, `CursosView`, `NotalyTopHeader`, menú herramientas `NotasView`) | **`NotalySheet`** (Action Sheet) | Reemplazar `ft.PopupMenuButton` lavanda M3; ítems táctiles de `48dp` de alto con ícono alineado y acción `Eliminar` en `tok.fail_fg`. |
| **Selectores e inspectores de lista** (`Selector Institución y Curso` en `EstadisticasView`, `PlanillasCursoDialog`, `PlanificacionesInstitucionDialog`, `PlanificacionCursoDialog`, `LocalBackupDialog`, `ExportDialog`, `ExportEstadisticasDialog`, `ReasignarAlumnoDialog`) | **`NotalySheet`** (altura adaptable `<= 0.85 * h`, `ScrollMode.AUTO`) | Eliminar `height=380/480/500/520` fijos; añadir `bgcolor=tok.surface_primary`; expandir `info_card` al 100% en `ExportEstadisticasDialog` reemplazando emojis `🏫📚🗓️📄` por íconos vectoriales; eliminar `self.tab_selector` muerto y nombre técnico truncado en `LocalBackupDialog`; botones `48dp`; reemplazar `ft.RadioGroup` por filas `NotalyListRow` seleccionables; mostrar siempre `banner_advertencia` en `ExportDialog` al activar "Una sola página". |
| **Formularios con teclado virtual** (`StudentFormDialog`, `ColegioFormDialog`, `CreateCursoDialog`, `CreateEntityDialog`, `RenameDialog`, `CustomizeColumnsDialog`, `SorteadorGruposDialog`, `ComportamientoDialog`, `CalificarGrupoDialog`, `DatePickerDialog`, `GradeEditorDialog`) | **`NotalySheet`** (formularios largos/calendario/comportamiento/sorteador) o **Diálogo Editorial Compacto** (`tight=True`, `ScrollMode.AUTO`, `radius=6`, `bgcolor=tok.surface_primary`) | En `StudentFormDialog`: máximo 2 acciones por fila (`Siguiente` primario `48dp` + `Guardar y salir` secundario + cerrar `×` en header o enlace eliminar), unificar texto `'Siguiente'`; agregar `ScrollMode.AUTO` a todos; en `DatePickerDialog` y `ComportamientoDialog` eliminar constantes claras (`TEXT_MAIN`, `PRIMARY`, `COLOR_POS_BG`, etc.) y reemplazar `ft.Chip` por botones rectangulares `44dp` (`radius=4`); en `SorteadorGruposDialog` expandir `caja_preview` al 100%, corregir `"1 alumno"`, tokenizar chips de temas y `Switch`, eliminar `BORDER_COLOR`/`#F1F5F9`; en `CalificarGrupoDialog` corregir `"1 integrante"`, eliminar `TEXT_MUTED`/`PRIMARY`/`#EFF6FF` e `is_dark == DARK_TOKENS`; en `GradeEditorDialog` quitar `ft.Icons.SCHOOL`. |
| **Confirmaciones destructivas y sistema** (`ConfirmDeleteDialog`, `Acerca de`, `Primer inicio`, `Cambios sin guardar`, `¿Eliminar planilla/archivo/trabajo?`) | **Diálogo Editorial Compacto** (`bgcolor=tok.surface_primary`, `radius=6`, máx. ancho `min(w-32, 380)`) | Añadir `bgcolor=tok.surface_primary` faltante a los 5 diálogos detectados (`planillas_curso_dialog.py:272`, `main.py:470`, `asistencias_view.py:710`, `estadisticas_view.py:641`, `planillas_view.py:447`); botones `height=48dp`, `radius=4`, `accent_on_primary` / `fail_fg` contrastados. |

---

## 8. Responsividad Multi-Dispositivo (Android e iOS) y Remediación de Bugs Flet 0.86+

### 8.1 Safe Areas, Teclado Virtual y Barra Inferior

1. **Inmersión segura (`ft.SafeArea`):**
   - `NotalyTopHeader` usa `ft.SafeArea(avoid_intrusions_top=True, avoid_intrusions_bottom=False)` para librar *status bar*, *notch* y *Dynamic Island* (iOS).
   - Docks inferiores (`NotasView`), `NotalySheet` y contenedores sin footer usan `ft.SafeArea(avoid_intrusions_top=False, avoid_intrusions_bottom=True, maintain_bottom_view_padding=True)` para respetar la barra de gestos Android y el *Home Indicator* de iOS.
2. **Barra inferior (`AppFooter`):** Mantener `ft.NavigationBar` con `height=None` (estándar M3 `80dp` para absorber `viewPadding.bottom`), `label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW`, `elevation=0`, `bgcolor=tok.surface_primary`, `indicator_color=tok.accent_subtle` y borde superior `1px tok.border_hairline`. Todas las vistas con footer (`Colegios`, `Cursos`, `Planillas`, `Estadísticas`) reservan `bottom >= 88dp` en su `ListView.padding`.
3. **Teclado virtual y Dock numérico (`NotasView`):**
   - Al abrir cualquier modal o `NotalySheet` desde `NotasView`, ocultar inmediatamente `dock_container.visible = False` y restaurarlo en `on_dismiss` (solo si `active_trimestre < 3`).
   - Cuando `dock_container.visible = True`, incrementar el `padding.bottom` del `ListView` (`>= 176dp`) para que la última fila de alumno sea desplazable por encima del teclado numérico y la barra de gestos.
   - En formularios con `TextField`, `ScrollMode.AUTO` en `NotalySheet` asegura visibilidad activa del campo enfocado sobre Gboard / teclado iOS.

### 8.2 Breakpoints Responsivos (Portrait y Landscape)

| Clase de Dispositivo (`page.width`) | Gutters Laterales | Comportamiento de Layout y Componentes |
|---|---|---|
| **Compacto (`< 360dp`)** *(ej. `320–359dp`)* | `12dp` | `UnderlineTabBar` con rótulos breves (`1°T \| 2°T \| 3°T \| Anual`; `Todas \| Notas \| Asist. \| Stats`). En `AsistenciasView`, `AttendanceCellGroup` usa botones `36×44dp` (`gap=4dp`) o modo apilado compacto garantizando `>= 140dp` libres al nombre del alumno. Botones secundarios de cabecera agrupados en `NotalySheet`. |
| **Estándar (`360dp – 430dp`)** *(Pixel, Galaxy, iPhone)* | `16dp` | `AttendanceCellGroup` `40×44dp` (`gap=4dp`); 5 slots de notas en una fila (`expand=True`, `44dp` alto); acciones de fila alineadas en `48dp`. |
| **Tablet / Horizontal (`>= 600dp`)** | `24dp` (`max_width=720dp` centrado) | El cuerpo principal de listas y estadísticas se centra en un lienzo editorial máximo de `720dp` para preservar longitud de lectura óptima; KPIs críticos en 3 columnas horizontales; `NotalySheet` acotado a `max_width=480dp`. |

### 8.3 Corrección Explícita de Todos los Bugs Documentados en `AUDIT.md` y Flet 0.86+

| # | Bug Verificado en Código y Emulador | Ubicación Exacta | Solución Obligatoria en Implementación |
|---|---|---|---|
| **B1** | Incompatibilidad Flet `0.86+`: mutar `.name` en lugar de `.icon` en `ft.Icon` congela íconos de estado anual en `⊖`, invierte chevrons (`^`/`v`) y rompe actualización de `SaveStatusIndicator`. | [`mobile/views/notas_view.py#L668`](../mobile/views/notas_view.py#L668), [`L737`](../mobile/views/notas_view.py#L737), [`L1670-L1693`](../mobile/views/notas_view.py#L1670-L1693); [`mobile/components/ui_header.py#L48-L55`](../mobile/components/ui_header.py#L48-L55) | Sustituir toda asignación `.name = ...` sobre instancias de `ft.Icon` por `.icon = ...` y llamar a `.update()` del control afectado. |
| **B2** | `header_pills_containers` declarada pero nunca poblada en `NotasView`: filas colapsadas no muestran resumen por trimestre. | [`mobile/views/notas_view.py#L156`](../mobile/views/notas_view.py#L156), [`L796`](../mobile/views/notas_view.py#L796) | Poblar en cada fila un resumen tabular continuo separado por `·` (`1°T 8 · 2°T 7 · 3°T --`, en `LedgerMono` `12sp`, sin píldoras!) y actualizarlo *in-place* en `_actualizar_fila_alumno_ui` (ocultándolo únicamente en modo `Anual`). |
| **B3** | Desincronización de caché `_curso_views`: agregar/editar alumnos en `NotasView` deja `AsistenciasView` / `GruposView` mostrando datos desactualizados o estado vacío. | [`mobile/main.py#L102-L103`](../mobile/main.py#L102-L103), [`L238-L250`](../mobile/main.py#L238-L250) | Mantener un marcador de versión/invalidación por curso (o invalidar las otras pestañas cacheadas de `_curso_views` cuando `NotasView` modifica el padrón de alumnos, y refrescar los datos *in-place* al reactivar una vista cacheada en `navigate()`). |
| **B4** | `navigate()` sobrescribe `state.selected_colegio` al navegar a otro colegio si existe un frame `"cursos"` previo en el tope del historial, y `pop_history()` debe conservar contexto válido. | [`mobile/main.py#L226-L231`](../mobile/main.py#L226-L231); [`mobile/state.py#L321-L368`](../mobile/state.py#L321-L368) | En `navigate()`, solo consumir `peek_history()` cuando `screen == view_name` **y además** coincidan `(selected_colegio, selected_curso)` (o restringir `pop_history()` estrictamente al flujo `back`). Al entrar a un nuevo colegio (`_abrir_colegio`), preservar el nuevo `selected_colegio` sin restaurar frames obsoletos de otro colegio. |
| **B5** | `GlobalSearchBar` con `full_screen=False` en `AppBar.title` abre desplazado a `x=135px` con texto ilegible en Dark Mode. | [`mobile/components/global_search.py#L64`](../mobile/components/global_search.py#L64), [`L207-L247`](../mobile/components/global_search.py#L207-L247) | Migrar a `GlobalSearchOverlay` de ancho `100%` y superficie tokenizada `tok.*`. |
| **B6** | Contraste `< 4.5:1` en Dark/Light Mode (`FilledButton` `2.98:1`, `T`/`P` `1.67–2.54:1`, `text_subtle` `3.07:1`, `grade_fail` `3.62:1`, `grade_empty` `4.05:1`, `DatePickerDialog` `1.22:1`, 5 `AlertDialog` sin `bgcolor=tok.surface`, `BoxShadow("#0F172A0D")` invisible). | [`mobile/theme.py`](../mobile/theme.py), [`mobile/components/`](../mobile/components/), [`mobile/views/`](../mobile/views/) | Aplicar la tabla completa de la Sección 3, erradicar toda constante clara importada (`PRIMARY`, `TEXT_MAIN`, `BG_PAGE`, etc.) y `ft.Colors.WHITE` en controles, y asignar `bgcolor=tok.surface_primary` en el 100% de sheets y diálogos. |
| **B7** | Redundancias, acciones muertas y errores gramaticales. | Múltiples vistas y modales | Corregir `"1 institución registrada"`, `"1 curso registrado"`, `"1 curso activo"`, `"1 alumno"`, `"1 integrante"`, `"1 archivo"`; quitar `+` doble en `+ Alumno`; quitar segundo botón de calendario en `AsistenciasView`; ocultar acciones vacías (`Planificaciones` con 0 cursos, `Copiar` con 0 grupos). |

---

## 9. Lista Negra Anti-"AI Slop" y Puerta de Aprobación SDD

### 9.1 Elementos Terminantemente Prohibidos en `mobile/`

1. **Cero degradados decorativos:** Prohibido `ft.LinearGradient`, `ft.RadialGradient` o fondos con transiciones ornamentales.
2. **Cero colores neón, púrpura o índigo:** Prohibido `#4F46E5`, `#818CF8`, `#6366F1`, `#6D28D9`, `#2E1065` o semillas `color_scheme_seed` fuera de `accent_primary` (`#1B3B5A` / `#7FB3D5`).
3. **Cero `ft.Card` por defecto:** Prohibido usar `ft.Card` con elevación material o superficie tintada lavanda; usar `NotalyListSection` y `NotalyListRow`.
4. **Cero píldoras, cápsulas o `ft.Chip`:** Prohibido `ft.Chip`, contenedores ovalados y cualquier `border_radius >= 12` o `999`.
5. **Cero radios excesivos:** Prohibido `border_radius > 8px` en cualquier control de la aplicación (y máximo `4px` en botones/celdas/inputs, `6px` en secciones, `8px` solo en bordes superiores de `NotalySheet`).
6. **Cero sombras difusas:** Prohibido `ft.BoxShadow` con `blur_radius > 8` o tintes oscuros invisibles (`#0F172A0D`). La separación visual se construye por contraste de superficie (`bg_canvas` vs `surface_primary`) y divisores `1px border_hairline`.
7. **Cero alturas fijas en contenedores dinámicos:** Prohibido `height=380/480/500/520` en modales/diálogos o `height=64` en `ft.NavigationBar`.
8. **Cero emojis como íconos de UI:** Prohibido `🏫`, `📚`, `🗓️`, `📄`, `💡`, `📋` dentro de controles visuales; usar exclusivamente íconos vectoriales de `ft.Icons.*` (pueden conservarse emojis únicamente dentro del texto plano exportado a WhatsApp por `core/exportador.py`).
9. **Cero colores hardcodeados fuera de `mobile/theme.py`:** Prohibido `ft.Colors.WHITE`, `ft.Colors.RED_600`, `ft.Colors.GREY_500`, `ft.Colors.AMBER_*`, `ft.Colors.SECONDARY` o hex literales dentro de `mobile/views/`, `mobile/components/` o `mobile/main.py`.

### 9.2 Checklist Pre-Implementación (SDD)

Antes de modificar cualquier archivo `.py`:
- [ ] Crear carpeta `.agents/specs/028-redisenio-crisp-editorial-ledger/` con `spec.md` (requisitos EARS), `plan.md` y `tasks.md` atómicos aprobados por el usuario.
- [ ] Descargar y verificar licencia OFL-1.1 de `Plus Jakarta Sans` y `JetBrains Mono` en `./assets/fonts/`.
- [ ] Confirmar que `core/`, `.github/workflows/build-apk.yml`, `iniciador.py` y `gui/` permanecen con `0` líneas modificadas.
- [ ] Validar cada tarea atómica con `venv\Scripts\pytest.exe --ignore=tests/e2e` en verde al 100%, conservando intactos todos los tests de compatibilidad Android y preservación de scroll.

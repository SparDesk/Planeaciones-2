from __future__ import annotations

"""
Módulo de integración con la SDK oficial de Google GenAI (Gemini)
para la generación automatizada de planeaciones didácticas bajo el modelo NEM (SEP).
"""

import os
import time
import socket
import requests
import streamlit as st
from typing import Dict, Any, Tuple, Union, List, Optional
from google import genai
from google.genai import types
try:
    import httpx
except ImportError:
    httpx = None
try:
    from nem_data import METODOLOGIAS_SOCIOCRITICAS, parsear_metodologia_lista, formatear_metodologia_str
except ImportError:
    METODOLOGIAS_SOCIOCRITICAS = {}
    def parsear_metodologia_lista(m):
        return [str(m)] if m else ["Aprendizaje Basado en Proyectos Comunitarios"]
    def formatear_metodologia_str(m):
        return str(m or "Aprendizaje Basado en Proyectos Comunitarios")

try:
    from cuadernillo_kempis import (
        detectar_relevancia_kempis,
        formatear_kempis_para_prompt,
        obtener_recursos_kempis_por_semana,
        obtener_proyecto_semana,
        obtener_anexos_por_semana_y_dia,
        CATALOGO_PROYECTOS_SEP_37_SEMANAS
    )
except ImportError:
    detectar_relevancia_kempis = lambda *args, **kwargs: True
    formatear_kempis_para_prompt = lambda *args, **kwargs: ""
    obtener_recursos_kempis_por_semana = lambda *args, **kwargs: None
    obtener_proyecto_semana = lambda *args, **kwargs: {}
    obtener_anexos_por_semana_y_dia = lambda *args, **kwargs: []
    CATALOGO_PROYECTOS_SEP_37_SEMANAS = {}

try:
    from file_processor import busqueda_cruzada_archivos_plataforma
except ImportError:
    busqueda_cruzada_archivos_plataforma = None

DEFAULT_MODEL = "gemini-3.8-flash"

AVAILABLE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.8-pro",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

def verificar_conexion_internet(host: str = "www.google.com", port: int = 80, timeout: float = 3.0) -> bool:
    """
    Verifica si existe una conexión activa a internet antes de iniciar la generación de la planeación.
    Utiliza socket para una comprobación rápida a nivel TCP y requests como mecanismo de respaldo
    para validar la conectividad hacia la web y APIs externas.

    Parámetros:
        host (str): Servidor contra el cual comprobar conectividad socket (por defecto: 'www.google.com').
        port (int): Puerto de conexión TCP (por defecto: 80).
        timeout (float): Tiempo máximo de espera en segundos (por defecto: 3.0).

    Retorna:
        bool: True si hay conexión a internet activa, False si no hay red o expira el tiempo de espera.
    """
    # 1. Comprobación rápida vía socket TCP
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, socket.gaierror, socket.error, OSError, PermissionError):
        pass

    # 2. Respaldo mediante requests HTTP/HTTPS
    try:
        resp = requests.head("https://www.google.com", timeout=timeout)
        if resp.status_code < 500:
            return True
    except Exception:
        pass

    try:
        resp = requests.get("https://www.google.com", timeout=timeout)
        return resp.status_code < 500
    except Exception:
        return False

def get_client(api_key: str = None) -> genai.Client:
    """Crea e inicializa el cliente oficial de Google GenAI."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("No se proporcionó una GEMINI_API_KEY válida. Ingrésala en la barra lateral o en las variables de entorno.")
    return genai.Client(api_key=key)

def build_system_instruction() -> str:
    """Instrucción de sistema para el rol de Especialista Pedagógico SEP."""
    return """Eres el Especialista Principal en Pedagogía Curricular y Didáctica de la Secretaría de Educación Pública (SEP) de México, experto consumado en el Plan de Estudio 2022 y el modelo de la Nueva Escuela Mexicana (NEM).

Tu misión es diseñar planeaciones didácticas auténticas, contextualizadas, profundas y rigurosamente estructuradas para el trabajo docente en educación primaria (Fases 3, 4 y 5), con especialización en 6° de Primaria (Fase 5).

REGLAS PEDAGÓGICAS INQUEBRANTABLES:
1. Lenguaje docente mexicano formal, constructivo, inclusivo y orientado a la comunidad.
2. ARTICULACIÓN DINÁMICA Y FLEXIBLE DE CAMPOS FORMATIVOS:
   - Articula de manera interdisciplinaria y contextualizada los Campos Formativos seleccionados por el docente (pudiendo ser uno, varios o los 4 campos simultáneamente).
   - Cuando se selecciona un solo campo formativo, profundiza exhaustivamente en sus contenidos, PDA y secuencia didáctica específica sin forzar contenidos ajenos.
   - Cuando se seleccionan múltiples o todos los campos, intégralos armónicamente a través del proyecto interdisciplinario o indagación comunitaria.
3. INTEGRACIÓN DIRECTA DE LAS PROBLEMÁTICAS DEL PROGRAMA ANALÍTICO (CICLO 2026-2027):
   - Atender y resolver transversalmente en las actividades diarias y de inicio:
     * Comprensión lectora profunda e inferencial.
     * Velocidad y fluidez lectora (lectura cronometrada en voz alta, dicción, modulación).
     * Ortografía y redacción autónoma (reglas de acentuación, signos de puntuación, grafías de uso dudoso).
     * Asuntos comunitarios (promoción de la lectura en familias/comunidad, acceso y uso crítico/ético/pedagógico de tecnologías digitales y recursos).
4. CALENDARIO ESCOLAR OFICIAL SEP (37 SEMANAS LECTIVAS / 185 DÍAS):
   - La dosificación y temporalidad corresponden estrictamente a las 37 semanas lectivas oficiales del Ciclo Escolar 2026-2027.
   - Sitúa el nivel de complejidad y avance curricular de acuerdo a la semana seleccionada de las 37 semanas oficiales.
5. ATENCIÓN AL GRUPO Y DUA (26 ALUMNOS - ESTILOS KINESTÉSICO Y VISUAL):
   - Cada sesión didáctica DEBE estructurarse explícitamente en tres momentos (Inicio, Desarrollo y Cierre) e incorporar obligatoriamente:
     * Estímulos KINESTÉSICOS vivenciales (manipulación de materiales concretos, estaciones de aprendizaje activas, dramatización, proyectos por equipos).
     * Recursos VISUALES estructurados (organizadores gráficos, mapas conceptuales, esquemas ilustrados con códigos de color, infografías).
6. ACTIVIDADES DE INICIO DEL DÍA (RUTINA MATUTINA PERMANENTE):
   - Dictado reflexivo y ortográfico (5 palabras/enunciados con reto ortográfico explícito).
   - Velocidad y fluidez lectora (1 minuto cronometrado con modulación y registro).
   - Cálculo mental contextualizado (5 operaciones contextualizadas al grado y semana).
   - Problema matemático razonado (enunciado vinculado a la comunidad, datos, operaciones y resultado interpretado).
7. Vinculación estricta con los Libros de Texto Gratuitos (LTG) de la SEP:
   - Cita explícitamente sugerencias de páginas de los libros: Proyectos de Aula / Escolares / Comunitarios, Nuestros Saberes y Múltiples Lenguajes.
8. Evaluación formativa real: Evitar generalidades; describe criterios observables y diseña un instrumento concreto (como rúbrica analítica o lista de cotejo con indicadores claros de logro).
9. Ajustes razonables / Inclusión: Estrategias de atención a la diversidad (DUA) y barreras para el aprendizaje y la participación (BAP).
10. ARTICULACIÓN METODOLÓGICA FLEXIBLE Y USO OBLIGATORIO DEL PROGRAMA ANALÍTICO:
    - Respeta y aplica rigurosamente la(s) metodología(s) sociocrítica(s) seleccionada(s) por el docente (Aprendizaje Basado en Proyectos Comunitarios, STEAM, ABPr, Aprendizaje Servicio de forma individual o combinada).
    - Cita con precisión las fases y momentos oficiales correspondientes a cada metodología activa en el desarrollo de las sesiones, vinculándolas a los campos formativos delimitados por el docente en el Programa Analítico.
11. BÚSQUEDA CRUZADA EN ARCHIVOS Y COHERENCIA CURRICULAR ESTRICTA:
    - Realiza una lectura y búsqueda cruzada en todos los archivos de la plataforma (cuadernillos de 37 semanas, libros de texto SEP, guías CTE y anexos imprimibles) para alinear las actividades, recursos didácticos y consignas de acuerdo con lo solicitado por el docente.
    - PROHIBICIÓN ESTRICTA DE ALUCINACIÓN: Queda terminantemente prohibido inventar asignaturas tradicionales independientes del plan anterior (como materias aisladas de Español, Matemáticas, Ciencias Naturales, Geografía o Historia por separado) o contenidos externos ajenos al Plan de Estudio 2022 de la NEM. Toda la planeación debe mantener una trazabilidad directa con las 4 problematizaciones oficiales y la ficha técnica institucional (Primaria Revolución Social de 1910, 26 alumnos, estilos Kinestésico y Visual, DUA).
"""

def generate_planeacion(
    datos_escuela: Dict[str, Any],
    campos_formativos: list,
    metodologia: Union[str, list],
    ejes_articuladores: list,
    contenidos_pda: list,
    directrices_docente: str,
    contexto_archivos: str = "",
    libros_seleccionados: list = None,
    guia_cte: str = None,
    programa_sintetico: str = None,
    dias_seleccionados: list = None,
    semana_seleccionada: Union[int, str] = None,
    fase_seleccionada: str = None,
    fallback_programa_sintetico: bool = False,
    num_sesiones: int = 5,
    api_key: str = None,
    modelo: str = DEFAULT_MODEL,
    busqueda_web: bool = False,
    contexto_url: str = "",
    dossier_busqueda: Optional[Dict[str, Any]] = None,
    archivo_base_estricta: str = None,
    contenido_base_estricta: str = None,
    modo_base_estricta: bool = False,
    **kwargs
) -> Tuple[str, str]:
    """
    Envía la solicitud a Gemini usando la SDK oficial de Google GenAI y retorna el texto generado,
    articulando dinámicamente Libros de Texto SEP, Guía del CTE, Programa Sintético, Programa Analítico y búsqueda cruzada en archivos.
    
    Parámetros obligatorios enriquecidos:
        libros_seleccionados: Lista o texto de libros de texto SEP seleccionados.
        guia_cte: Guía u orientaciones de Consejo Técnico Escolar seleccionadas.
        programa_sintetico: Texto extraído o directrices del Programa Sintético de la NEM.
        dias_seleccionados: Lista de días de la semana a planear seleccionados por el usuario.
        semana_seleccionada: Número de semana (1 a 37) del calendario escolar oficial SEP.
        fase_seleccionada: Fase oficial de la Nueva Escuela Mexicana (ej. 'Fase 5' o '5').
        fallback_programa_sintetico: Booleano que indica si se debe usar la directriz de fallback si no hay archivo oficial.
        contexto_url: Texto extraído de una URL de referencia pedagógica mediante web scraping.
        dossier_busqueda: Diccionario con la búsqueda cruzada en archivos de la plataforma.
    """
    # Verificación preventiva de conectividad a internet
    if not verificar_conexion_internet():
        raise ConnectionError("No hay conexión a internet. Por favor, revisa tu red e inténtalo de nuevo.")

    client = get_client(api_key)

    # Compatibilidad con posibles alias vía kwargs
    if libros_seleccionados is None:
        libros_seleccionados = kwargs.get("libros", [])

    if guia_cte is None:
        guia_cte = kwargs.get("guia_cte_seleccionada", "Orientaciones CTE - 5ª Sesión Ordinaria (Febrero 2026)")

    guia_cte_detalle = kwargs.get("guia_cte_detalle", None)

    if not contexto_url:
        contexto_url = kwargs.get("contexto_url", "")

    # Declaración e inicialización preventiva de directriz_contexto_url_txt
    directriz_contexto_url_txt = kwargs.get("directriz_contexto_url_txt", "") or ""

    # 1. REGLA DE DÍAS SELECCIONADOS
    if dias_seleccionados is None:
        dias_seleccionados = kwargs.get("dias_seleccionados") or kwargs.get("dias_planeados") or datos_escuela.get("dias_seleccionados") or datos_escuela.get("dias_planeados") or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    if not dias_seleccionados:
        dias_seleccionados = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    num_sesiones = len(dias_seleccionados)

    # 2. REGLA DE TEMPORALIDAD DINÁMICA (37 SEMANAS OFICIALES SEP Y CALENDARIO 2026-2027)
    if semana_seleccionada is None:
        semana_seleccionada = (
            kwargs.get("semana_seleccionada") or
            kwargs.get("semana") or
            datos_escuela.get("semana_seleccionada") or
            datos_escuela.get("semana")
        )
        if not semana_seleccionada and datos_escuela.get("periodo"):
            import re
            m = re.search(r'\d+', str(datos_escuela.get("periodo")))
            if m:
                semana_seleccionada = int(m.group())
        if not semana_seleccionada:
            semana_seleccionada = 1
    try:
        semana_seleccionada = int(semana_seleccionada)
        semana_seleccionada = max(1, min(37, semana_seleccionada))
    except (ValueError, TypeError):
        semana_seleccionada = 1

    mes_seleccionado = (
        kwargs.get("mes_seleccionado") or
        kwargs.get("mes") or
        datos_escuela.get("mes_seleccionado") or
        datos_escuela.get("mes") or
        "Octubre"
    )
    año_seleccionado = kwargs.get("año_seleccionado") or datos_escuela.get("año", 2026)
    proyecto_info = obtener_proyecto_semana(semana_seleccionada, mes=mes_seleccionado)

    # 3. FASE CURRICULAR (NEM)
    fase_correspondiente = datos_escuela.get('fase', 'Fase 5')
    if fase_seleccionada is None:
        fase_seleccionada = kwargs.get("fase_seleccionada") or fase_correspondiente
    fase_limpia = str(fase_seleccionada).replace("Fase", "").strip() or "5"

    grado_seleccionado = datos_escuela.get('grado', '6° de Primaria')

    # 3.1 BÚSQUEDA GLOBAL Y CRUZADA EN ARCHIVOS DE LA PLATAFORMA (CUADERNILLOS, LIBROS, GUÍAS Y ANEXOS)
    if dossier_busqueda is None:
        dossier_busqueda = kwargs.get("dossier_busqueda")
    if dossier_busqueda is None and busqueda_cruzada_archivos_plataforma:
        try:
            dossier_busqueda = busqueda_cruzada_archivos_plataforma(
                semana=semana_seleccionada,
                grado=grado_seleccionado,
                campos_formativos=campos_formativos,
                dias_seleccionados=dias_seleccionados,
                directrices_docente=directrices_docente,
                archivos_procesados=kwargs.get("archivos_procesados"),
                mes=mes_seleccionado,
                año=año_seleccionado,
                libros_seleccionados=libros_seleccionados,
                guia_cte=guia_cte
            )
        except Exception:
            dossier_busqueda = None

    # 3.2 ARTICULACIÓN DINÁMICA DE CAMPOS FORMATIVOS Y PROGRAMA ANALÍTICO
    campos_4_obligatorios = [
        "Lenguajes",
        "Saberes y Pensamiento Científico",
        "Ética, Naturaleza y Sociedades",
        "De lo Humano y lo Comunitario"
    ]
    # Determinar los campos objetivo a partir de los seleccionados por el docente
    campos_objetivo = [c for c in campos_formativos if c in campos_4_obligatorios] if campos_formativos else campos_4_obligatorios
    campos_en_pda = set()
    for item in (contenidos_pda or []):
        c_raw = (item.get("campo") or "").strip().lower()
        for c_ob in campos_objetivo:
            if c_ob.lower() in c_raw or c_raw in c_ob.lower():
                campos_en_pda.add(c_ob)

    if len(campos_en_pda) < len(campos_objetivo) and dossier_busqueda and "pda_4campos" in dossier_busqueda:
        contenidos_pda_completos = list(contenidos_pda or [])
        for item_d in dossier_busqueda["pda_4campos"]:
            if item_d["campo"] in campos_objetivo and item_d["campo"] not in campos_en_pda:
                contenidos_pda_completos.append({
                    "campo": item_d["campo"],
                    "contenido": item_d["contenido"],
                    "pda": item_d["pda"]
                })
                campos_en_pda.add(item_d["campo"])
        contenidos_pda = contenidos_pda_completos

    # ----------------------------------------------------
    # CONFIGURACIÓN DE BASE ESTRICTA (PROGRAMA ANALÍTICO / SINTÉTICO SUBIDO)
    # PRIORIDAD ABSOLUTA: Uso exclusivo del documento seleccionado por el usuario
    # ----------------------------------------------------
    archivo_base_estricta = archivo_base_estricta or kwargs.get("archivo_base_estricta") or kwargs.get("nombre_archivo_base_estricta")
    contenido_base_estricta = contenido_base_estricta or kwargs.get("contenido_base_estricta") or kwargs.get("texto_base_estricta")
    modo_base_estricta = modo_base_estricta or kwargs.get("modo_base_estricta", False)
    if archivo_base_estricta and not modo_base_estricta:
        modo_base_estricta = True

    directriz_base_estricta_txt = ""
    if modo_base_estricta and archivo_base_estricta and contenido_base_estricta and str(contenido_base_estricta).strip():
        directriz_base_estricta_txt = f"""
================================================================================
🔒 DIRECTRIZ SUPREMA DE PRIORIDAD ABSOLUTA - BASE ESTRICTA OBLIGATORIA DEL DOCENTE
================================================================================
DOCUMENTO RECTOR SELECCIONADO POR EL USUARIO: "{archivo_base_estricta}"
EL DOCENTE HA MARCADO ESTE ARCHIVO SUBIDO COMO LA FUENTE ESTRICTA, EXCLUSIVA Y
OBLIGATORIA PARA REGIR LA TOTALIDAD DE ESTA PLANEACIÓN DIDÁCTICA.

* INSTRUCCIONES INELUDIBLES DE MÁXIMA PRIORIDAD Y FIDELIDAD:
1. CONTENIDOS Y PROCESOS DE DESARROLLO DE APRENDIZAJE (PDA):
   Debes extraer y aplicar EXCLUSIVAMENTE los Contenidos y PDA presentes en este archivo cargado ("{archivo_base_estricta}").
   Respeta rigurosamente su redacción, alcance y formulación original sin alteraciones.
2. PROBLEMÁTICAS Y CONTEXTUALIZACIÓN COMUNITARIA:
   Si el archivo corresponde al Programa Analítico o al diagnóstico local de la escuela, adopta de forma ESTRICTA y PRIORITARIA las problemáticas comunitarias, rezagos formativos y acuerdos escolares expuestos en él.
3. CAMPOS FORMATIVOS Y EJES ARTICULADORES:
   Los campos formativos ({', '.join(campos_formativos)}) y los ejes articuladores ({', '.join(ejes_articuladores)}) deben fundamentarse directa e inequívocamente en lo establecido en este documento.
4. PROHIBICIÓN TERMINANTE DE PLANTILLAS GENÉRICAS O EXTERNAS:
   QUEDA TOTALMENTE PROHIBIDO recurrir a plantillas genéricas, contenidos predeterminados estándar de internet o formulaciones ajenas a este documento.
   Cada momento de la secuencia didáctica (Inicio, Rutina Matutina, Desarrollo y Cierre), las rutinas diarias de ortografía y cálculo mental, así como los criterios del instrumento de evaluación formativa, DEBEN EMANAR ESTRICTAMENTE DE ESTE ARCHIVO.

--- CONTENIDO EXTRAÍDO DEL ARCHIVO SELECCIONADO COMO BASE ESTRICTA ---
{str(contenido_base_estricta).strip()}
================================================================================
"""
        programa_sintetico = contenido_base_estricta
        fallback_programa_sintetico = False

    # 4. PROGRAMA SINTÉTICO Y FUNCIÓN DE RESPALDO (WEB SCRAPING SEP CON PARÁMETROS DINÁMICOS)
    if programa_sintetico is None:
        programa_sintetico = kwargs.get("programa_sintetico_destacado", "")

    fallback_programa_sintetico = fallback_programa_sintetico or kwargs.get("fallback_programa_sintetico", False)
    if not (modo_base_estricta and archivo_base_estricta and contenido_base_estricta) and not programa_sintetico and not fallback_programa_sintetico:
        try:
            from conaliteg_scraper import buscar_programa_sintetico_sep
            dia_ref = dias_seleccionados[0] if dias_seleccionados else "Lunes"
            resumen_sep, exito_scraping = buscar_programa_sintetico_sep(
                fase_seleccionada=fase_seleccionada,
                semana=semana_seleccionada,
                mes=mes_seleccionado,
                dia=dia_ref,
                proyecto=proyecto_info.get("titulo_proyecto", "")
            )
            if exito_scraping and resumen_sep:
                programa_sintetico = resumen_sep
            else:
                fallback_programa_sintetico = True
        except Exception:
            fallback_programa_sintetico = True

    if modo_base_estricta and archivo_base_estricta and contenido_base_estricta:
        directriz_programa_sintetico_txt = f"""=== BASE ESTRICTA RECTORA DEL DOCENTE: "{archivo_base_estricta}" ===
El documento '{archivo_base_estricta}' funge como la fuente oficial con Prioridad Absoluta. Queda prohibido el uso de plantillas externas genéricas."""
    elif fallback_programa_sintetico or not programa_sintetico or not str(programa_sintetico).strip():
        directriz_programa_sintetico_txt = f"""=== PROGRAMA SINTÉTICO Y LINEAMIENTOS CURRICULARES (SEP - NEM) ===
Como no se proporcionó un documento oficial, utiliza tu conocimiento interno y capacidad de búsqueda para acceder a los lineamientos oficiales de la Nueva Escuela Mexicana (SEP) para la Fase {fase_limpia}, Semana {semana_seleccionada} de 37 y el mes de {mes_seleccionado} ({año_seleccionado}).
* REGLA DE FIDELIDAD CURRICULAR: Fundamenta los Contenidos sintéticos y Procesos de Desarrollo de Aprendizaje (PDA) oficiales en el currículo nacional vigente de la Nueva Escuela Mexicana para la Fase {fase_limpia}, articulando de forma contextualizada la Semana {semana_seleccionada} y los días {', '.join(dias_seleccionados)}."""
    else:
        directriz_programa_sintetico_txt = f"""=== BASE DE DATOS PRINCIPAL Y OFICIAL: PROGRAMA SINTÉTICO FASE 5 (6° DE PRIMARIA - SEP) ===
DOCUMENTO OFICIAL CARGADO: "Programa_Sintetico_Fase_5.pdf"
* DIRECTRIZ MANDATORIA DE MÁXIMA PRIORIDAD Y FIDELIDAD CURRICULAR:
Utiliza este documento oficial cargado como la BASE DE DATOS PRINCIPAL Y OFICIAL para tu análisis pedagógico y la planeación didáctica de 6° de Primaria.
Debes extraer rigurosamente y sin excepción de este documento:
1. CONTENIDOS SINTÉTICOS: Los contenidos oficiales de la Fase 5 correspondientes específicamente a 6° de Primaria.
2. PROCESOS DE DESARROLLO DE APRENDIZAJE (PDA): Los PDA oficiales específicos de 6° de Primaria exactamente con la redacción y alcance del documento.
3. CAMPOS FORMATIVOS: Articulación en los 4 Campos Formativos (Lenguajes, Saberes y Pensamiento Científico, Ética, Naturaleza y Sociedades, De lo Humano y lo Comunitario).
4. EJES ARTICULADORES: Vinculación con los 7 Ejes Articuladores de la Nueva Escuela Mexicana.
PROHIBICIÓN ESTRICTA: Queda terminantemente prohibido inventar, distorsionar o sustituir los Contenidos y PDA por versiones genéricas. Cada momento de la secuencia didáctica (Inicio, Desarrollo y Cierre) y las actividades de inicio del día deben derivarse de forma estricta de esta base curricular oficial.

--- TEXTO EXTRAÍDO DEL DOCUMENTO OFICIAL ---
{str(programa_sintetico).strip()}"""

    # Mapeo de fechas del calendario 2026 si están disponibles
    dias_fechas = datos_escuela.get("dias_fechas", {}) if isinstance(datos_escuela, dict) else {}
    fechas_txt = ""
    if dias_fechas:
        lineas_f = [f"  * {d}: {dias_fechas.get(d, d)}" for d in dias_seleccionados if d in dias_fechas]
        if lineas_f:
            fechas_txt = "\n- Fechas exactas del Calendario 2026 asignadas a cada día:\n" + "\n".join(lineas_f)

    # Detalle y fases de la(s) metodología(s) seleccionada(s)
    metodologias_lista = parsear_metodologia_lista(metodologia)
    metodologia_str = formatear_metodologia_str(metodologia)

    fases_metodologicas_items = []
    for m in metodologias_lista:
        info_m = METODOLOGIAS_SOCIOCRITICAS.get(m, {})
        desc_m = info_m.get("descripcion", "")
        fases_m = info_m.get("fases_oficiales", [])
        bloque = f"- **Metodología: {m}**"
        if desc_m:
            bloque += f"\n  *Enfoque:* {desc_m}"
        if fases_m:
            bloque += "\n  *Fases y Momentos Oficiales SEP:*\n" + "\n".join(f"    • {f}" for f in fases_m)
        fases_metodologicas_items.append(bloque)
    fases_metodologicas = "\n\n".join(fases_metodologicas_items)

    # Formateo de Contenidos y PDA
    articulacion_txt = ""
    for idx, item in enumerate(contenidos_pda, 1):
        articulacion_txt += f"\n- Contenido {idx}: {item.get('contenido', '')}\n  PDA {idx}: {item.get('pda', '')}"

    if isinstance(libros_seleccionados, (list, tuple, set)):
        libros_txt = ", ".join(str(x) for x in libros_seleccionados) if libros_seleccionados else "Proyectos de Aula, Proyectos Escolares, Proyectos Comunitarios, Nuestros Saberes, Múltiples Lenguajes"
    else:
        libros_txt = str(libros_seleccionados or "Proyectos de Aula, Proyectos Escolares, Proyectos Comunitarios, Nuestros Saberes, Múltiples Lenguajes")

    cte_nombre = str(guia_cte or "Orientaciones CTE - 5ª Sesión Ordinaria (Febrero 2026)")
    cte_enfoque = guia_cte_detalle.get("enfoque", "Evaluación formativa y proyectos comunitarios") if isinstance(guia_cte_detalle, dict) else "Evaluación formativa y proyectos comunitarios"
    cte_directrices = guia_cte_detalle.get("directrices", "Priorizar la evaluación dialógica y atención a BAP.") if isinstance(guia_cte_detalle, dict) else "Priorizar la evaluación dialógica y atención a BAP."

    busqueda_web = busqueda_web or kwargs.get("busqueda_web", False)
    directriz_busqueda_web_txt = ""
    if busqueda_web:
        directriz_busqueda_web_txt = f"""
=== BÚSQUEDA WEB EN TIEMPO REAL CON FILTRADO DINÁMICO POR FECHA, DÍA Y MES (GOOGLE SEARCH GROUNDING) ===
Antes de estructurar la secuencia didáctica, utiliza tu herramienta de búsqueda en internet aplicando de forma obligatoria los siguientes parámetros dinámicos de fecha del ciclo escolar 2026-2027:
- Semana Oficial de la SEP: Semana {semana_seleccionada} de 37 lectivas.
- Mes correspondiente al Calendario 2026-2027: {mes_seleccionado} {año_seleccionado}.
- Días de la semana seleccionados a planear: {', '.join(dias_seleccionados)}.
- Proyecto integrador vinculado: {proyecto_info.get('titulo_proyecto', '')}.

DIRECTRICES DE BÚSQUEDA CONTEXTUAL OBLIGATORIA:
1. Realiza búsquedas específicas cruzando cada día específico seleccionado ({', '.join(dias_seleccionados)}) con los momentos del proyecto y los anexos de la Semana {semana_seleccionada} ({mes_seleccionado} {año_seleccionado}).
2. PROHIBICIÓN ESTRICTA: Queda terminantemente prohibido utilizar consultas estáticas o valores fijos que fuercen siempre la misma semana o un único bloque predeterminado.
3. Incorpora dinámicamente en las actividades de Inicio, Desarrollo y Cierre de cada día los hallazgos recientes, dinámicas interactivas y fichas de trabajo encontradas para esa fecha y semana exactas.
"""

    # Detección e integración del proyecto y anexos didácticos
    vincular_kempis = kwargs.get("vincular_cuadernillo_kempis", True)
    directriz_kempis_txt = ""
    if vincular_kempis:
        directriz_kempis_txt = formatear_kempis_para_prompt(
            semana=semana_seleccionada,
            campos_formativos=campos_formativos,
            dias_seleccionados=dias_seleccionados,
            mes=mes_seleccionado,
            año=año_seleccionado
        )

    # DIRECTRIZ DE CONTEXTO WEB / URL DE REFERENCIA (ASEGURADA E INICIALIZADA)
    if not directriz_contexto_url_txt and contexto_url and str(contexto_url).strip():
        directriz_contexto_url_txt = f"""
=== CONTENIDO Y CONTEXTO PEDAGÓGICO EXTRAÍDO DE URL DE REFERENCIA ===
El docente ha proporcionado la siguiente fuente de información web de referencia pedagógica para enriquecer la planeación didáctica:
{str(contexto_url).strip()}
* DIRECTRIZ DE INTEGRACIÓN WEB: Incorpora pertinentemente las ideas clave, enfoques o dinámicas de esta fuente dentro del plano didáctico sin perder la alineación oficial NEM.
"""

    dossier_busqueda_txt = dossier_busqueda.get("dossier_prompt", "") if dossier_busqueda else ""

    guias_problematicas_campos = {
        "Lenguajes": """1. Lenguajes:
   - Comprensión lectora profunda: Identificación de ideas clave, inferencias complejas y análisis crítico de textos informativos y argumentativos.
   - Velocidad y fluidez lectora: Cronometrado de lectura en voz alta (1 minuto), entonación, dicción clara y ritmo fluido.
   - Ortografía y producción escrita: Aplicación sistemática de reglas de acentuación (agudas, graves, esdrújulas), signos de puntuación y grafías dudosas (b/v, c/s/z, g/j, h) en redacciones originales.""",
        "Saberes y Pensamiento Científico": """2. Saberes y Pensamiento Científico:
   - Lectura reflexiva de textos informativos científicos, tablas, datos experimentales y gráficas.
   - Cálculo mental contextualizado y problemas matemáticos razonados vinculados a la vida comunitaria y escolar de Durango (proporcionalidad, porcentajes, medidas).
   - Registro y redacción rigurosa de hipótesis, procedimientos de indagación y conclusiones fundamentadas.""",
        "Ética, Naturaleza y Sociedades": """3. Ética, Naturaleza y Sociedades:
   - Comprensión lectora crítica de dilemas éticos, normatividad ciudadana, derechos humanos y memoria histórica (incluyendo la Revolución Social de 1910 y los ideales de justicia social).
   - Diálogo deliberativo, posturas argumentativas fundadas y redacción con ortografía cuidada de compromisos ciudadanos.""",
        "De lo Humano y lo Comunitario": """4. De lo Humano y lo Comunitario:
   - Asuntos comunitarios: Estrategias vivenciales para involucrar a las familias y personas de la comunidad de Durango en el fomento y gusto por la lectura.
   - Acceso y uso crítico de tecnologías: Incorporar el uso ético, colaborativo y pedagógico de dispositivos digitales, fuentes de internet y recursos tecnológicos para la resolución de problemáticas locales.
   - Trabajo colaborativo, autoconocimiento, autorregulación y empatía grupal."""
    }

    campos_para_guia = [c for c in campos_formativos if c in guias_problematicas_campos] if campos_formativos else list(guias_problematicas_campos.keys())
    detalles_campos_articulados = "\n".join(guias_problematicas_campos[c] for c in campos_para_guia)

    prompt = f"""{build_system_instruction()}
{directriz_base_estricta_txt}
Elabora la planeación didáctica completa, oficial y lista para aplicar, bajo las siguientes especificaciones:

=== DATOS GENERALES DE LA INSTITUCIÓN ===
- Escuela: {datos_escuela.get('nombre_escuela', 'Escuela Primaria “Revolución Social de 1910”')}
- CCT: {datos_escuela.get('cct', '10EPR0361N')}
- Zona Escolar y Sector: {datos_escuela.get('zona_escolar', 'Zona 49')}, {datos_escuela.get('sector', 'Sector 02')} ({datos_escuela.get('entidad', 'Durango')})
- Docente Titular: {datos_escuela.get('docente', 'Maestra Aday Domínguez Domínguez')}
- Director de la Escuela: {datos_escuela.get('director', 'Guillermo Gerardo Borjas Díaz')}
- Grado y Fase: {datos_escuela.get('grado', '6° de Primaria')} ({fase_correspondiente}) Grupo '{datos_escuela.get('grupo', 'A')}'
- Temporalidad: {datos_escuela.get('periodo', f'Semana {semana_seleccionada}')} ({num_sesiones} sesiones didácticas programadas: {', '.join(dias_seleccionados)})
- Ciclo Escolar: {datos_escuela.get('ciclo_escolar', '2026-2027')}
- Turno: {datos_escuela.get('turno', 'Matutino')}

=== CONTEXTO DEL ENTORNO, DIAGNÓSTICO Y ESTILOS DE APRENDIZAJE DEL GRUPO (OBLIGATORIO) ===
- Diagnóstico Grupal: Grupo de 6° Grado Grupo “A” integrado por 26 alumnos.
- Estilos de Aprendizaje Predominantes: KINESTÉSICO (actividades vivenciales, manipulación de material concreto, proyectos prácticos, dinámicas activas y estaciones de aprendizaje) y VISUAL (organizadores gráficos, mapas conceptuales, esquemas con colores, diagramas e infografías ilustradas).
- Contexto Escolar y Comunitario: Entorno urbano en Durango con familias trabajadoras, profesionistas y personas jubiladas con fuerte sentido de pertenencia comunitaria.
- REGLA PEDAGÓGICA (DUA Y ESTILOS DE APRENDIZAJE):
  Es OBLIGATORIO que cada sesión didáctica integre estímulos VISUALES estructurados y dinámicas KINESTÉSICAS vivenciales, fundamentando la dosificación y las secuencias en el perfil de estos 26 alumnos.

=== PROBLEMÁTICAS IDENTIFICADAS DEL PROGRAMA ANALÍTICO (EJES DE TRABAJO PRIORITARIOS) ===
1. Comprensión Lectora: Fortalecer el análisis inferencial, extracción de ideas clave, juicio crítico y comprensión profunda de textos informativos y argumentativos.
2. Velocidad y Fluidez Lectora: Desarrollar entonación, ritmo, dicción y fluidez en lectura en voz alta.
3. Ortografía y Redacción: Consolidar reglas de acentuación, signos de puntuación, grafías dudosas y redacción de textos argumentativos e informativos propios.
4. Asuntos Comunitarios y Tecnologías: Promover la lectura en familias y comunidad, así como el acceso equitativo y uso crítico, ético y pedagógico de tecnologías digitales y recursos de información.
- REGLA DE FUNDAMENTACIÓN DEL MOTOR DE IA:
  Fundamenta el plano didáctico, las rutinas de inicio (dictado ortográfico, cálculo mental), las preguntas detonadoras y los productos en la atención y resolución de estas 4 problemáticas oficiales del Programa Analítico.

=== DIRECTRIZ MANDATORIA DE ARTICULACIÓN DE CAMPOS FORMATIVOS Y PROGRAMA ANALÍTICO ===
Debes cruzar e incorporar de manera contextualizada las problemáticas prioritarias del Programa Analítico a lo largo de los Campos Formativos seleccionados por el docente ({', '.join(campos_para_guia)}):
{detalles_campos_articulados}
REGLA DE SELECCIÓN FLEXIBLE: Concéntrate rigurosamente en los campos formativos elegidos ({', '.join(campos_para_guia)}). No obligues a la inclusión de contenidos de campos no seleccionados, permitiendo planeaciones unidisciplinares, interdisciplinares o integrales según la delimitación docente.

=== TEMPORALIDAD Y CALENDARIO ESCOLAR OFICIAL SEP (37 SEMANAS LECTIVAS) ===
- Semana seleccionada: Semana {semana_seleccionada} de las 37 semanas lectivas del calendario escolar oficial de la SEP (Ciclo Escolar 2026-2027)
- Mes oficial del Calendario 2026-2027: {mes_seleccionado} {año_seleccionado}
- Proyecto Integrador Asignado: {proyecto_info.get('titulo_proyecto', '')}
REGLA DE TEMPORALIDAD Y DOSIFICACIÓN ANUAL (37 SEMANAS OFICIALES DE LA SEP):
Ajusta la profundidad, alcance y progresión de los Contenidos y los PDA para que correspondan con total fidelidad pedagógica a la Semana {semana_seleccionada} de las 37 semanas lectivas oficiales de la SEP y al mes de {mes_seleccionado} {año_seleccionado}. Modula la exigencia y complejidad de las secuencias didácticas y la evaluación formativa considerando el avance anual esperado dentro de las 37 semanas lectivas del ciclo escolar 2026-2027.

=== DÍAS DE LA SEMANA A PLANEAR Y CALENDARIO INTERACTIVO 2026 (OBLIGATORIO) ===
- Días de la semana a planear seleccionados en las pestañas: {dias_seleccionados}
{fechas_txt}
REGLA DE CRUCE CONTEXTUAL POR DÍA DE LA SEMANA:
Para cada día específico seleccionado en las pestañas ({', '.join(dias_seleccionados)}), debes cruzar de forma obligatoria:
1) El día de la semana (Lunes, Martes, Miércoles, Jueves, Viernes) con su fecha oficial del año 2026.
2) La fase metodológica del Proyecto '{proyecto_info.get('titulo_proyecto', '')}' que corresponde a ese día.
3) El Anexo imprimible y ficha de trabajo específica correspondiente a ese día de la Semana {semana_seleccionada}.
4) Las actividades de Inicio, Desarrollo y Cierre citando expresamente el material y el anexo del día.
REGLA ESTRICTA ADICIONAL: TIENES ESTRICTAMENTE PROHIBIDO mencionar, planear o incluir tablas para cualquier otro día de la semana que no figure en {dias_seleccionados}.

=== CONFIGURACIÓN CURRICULAR (SEP - NEM) ===
- Campos Formativos seleccionados: {', '.join(campos_formativos)}
- Metodología(s) Sociocrítica(s) Oficial(es): {metodologia_str}
  Fases y momentos metodológicos a articular y seguir estrictamente:
{fases_metodologicas}
- Ejes Articuladores: {', '.join(ejes_articuladores)}

=== RECURSOS SEP Y ARTICULACIÓN METODOLÓGICA (NEM) ===
- Metodología(s) y Enfoque Pedagógico:
  * Metodología(s) activa(s) seleccionada(s): {metodologia_str}
  * REQUISITO DE ARTICULACIÓN METODOLÓGICA FLEXIBLE (NEM):
    - Si se seleccionó UNA sola metodología ({metodologia_str}): Estructura toda la secuencia didáctica siguiendo rigurosamente sus fases y momentos específicos (ej. 11 momentos de Proyectos Comunitarios, 5 fases STEAM, 6 momentos ABPr, o 5 etapas Aprendizaje Servicio).
    - Si se seleccionaron MÚLTIPLES metodologías ({metodologia_str}): Articúlalas flexiblemente a lo largo de las sesiones del plano didáctico, asignando cada metodología al campo formativo o momento correspondiente (ej. Indagación STEAM para saberes científicos y matemáticos; Proyectos Comunitarios para lenguajes; ABPr para dilemas éticos; Aprendizaje Servicio para proyectos solidarios). Cita explícitamente en el desarrollo de cada sesión las fases o momentos metodológicos específicos puestos en práctica.
- Libros a utilizar: {libros_seleccionados}
  * Títulos de los libros de texto seleccionados: {libros_txt}
  * REQUISITO PEDAGÓGICO: En la secuencia didáctica, cita expresamente sugerencias de páginas y dinámicas concretas de estos libros para consulta y trabajo de los alumnos.

- Tomar en cuenta la guía: {guia_cte}
  * Guía y Orientaciones CTE seleccionadas: {cte_nombre}
  * Enfoque pedagógico del mes: {cte_enfoque}
  * Directrices CTE aplicadas: {cte_directrices}
  * REQUISITO CTE: Articula estas directrices en el plano didáctico, la evaluación formativa y los ajustes razonables.


{directriz_programa_sintetico_txt}

{dossier_busqueda_txt}

=== ARTICULACIÓN CURRICULAR (CONTENIDOS Y PDA PRIORIZADOS) ===
{articulacion_txt}

=== DIRECTRICES DEL PLAN ANALÍTICO Y NOTAS DEL DOCENTE ===
{directrices_docente if directrices_docente.strip() else 'Atender los problemas comunitarios de rezago lector, redacción autónoma, cálculo mental y convivencia pacífica.'}
{directriz_busqueda_web_txt}
=== TEXTOS Y ARCHIVOS DE REFERENCIA ADICIONALES APORTADOS ===
{contexto_archivos}
{directriz_contexto_url_txt}
{directriz_kempis_txt}
ESTRUCTURA DE RESPUESTA EXIGIDA (Usa Markdown profesional, encabezados claros y tablas):

# I. DATOS DE IDENTIFICACIÓN Y DOSIFICADOR GENERAL DEL PROYECTO
- Nombre sugerido para el Proyecto Integrador (atractivo y motivante para las y los alumnos).
- Propósito general del proyecto (articulando transversalmente las problemáticas del Programa Analítico).
- Escenario (Aula, Escolar o Comunitario).
- Metodología(s) sociocrítica(s) articulada(s) y justificación pedagógica integradora.
- Ejes articuladores en acción.
- Temporalidad: Semana {semana_seleccionada} de 37 del calendario escolar oficial de la SEP ({num_sesiones} sesiones didácticas).

# II. ARTICULACIÓN CURRICULAR TRANSVERSAL (TABLA NEM - CAMPOS FORMATIVOS)
Articula transversalmente los Contenidos y PDA de los Campos Formativos seleccionados ({', '.join(campos_para_guia)}) {f"extraídos obligatoriamente y sin alteración del documento de Base Estricta '{archivo_base_estricta}' subido por el usuario" if (modo_base_estricta and archivo_base_estricta) else "extraídos obligatoriamente del Programa Analítico y la búsqueda cruzada en archivos"}.
Es OBLIGATORIO que la tabla contenga al menos una fila para cada Campo Formativo seleccionado ({', '.join(campos_para_guia)}), atendiendo y cruzando las problemáticas prioritarias sin omitir ningún campo ni inventar asignaturas tradicionales independientes ni utilizar plantillas genéricas.
Genera una tabla con:
| Campo Formativo | Contenido Sintético | Procesos de Desarrollo de Aprendizaje (PDA) | Vinculación con Libros SEP (LTG) | Problemática Analítica Atendida |

# III. ACTIVIDADES DE INICIO DEL DÍA (RUTINA MATUTINA - {num_sesiones} SESIONES)
Genera la rutina matutina ÚNICAMENTE para los siguientes días: {dias_seleccionados}. Cada día debe atender directamente las problemáticas de ortografía, velocidad lectora y cálculo mental (articulando los retos ortográficos, múltiplos del gramo, IVA o conmemoraciones del Cuadernillo Profa Kempis cuando corresponda):
Para cada día en {dias_seleccionados}:
- Sesión N ([Día de la semana]):
  * Dictado Ortográfico: 5 palabras u oraciones con dificultad ortográfica explícita (acentuación, grafías b/v, c/s/z, g/j, h o signos).
  * Velocidad y Fluidez Lectora: Ejercicio guiado de lectura en voz alta (1 minuto cronometrado o lectura en atril) con registro de fluidez, modulación y comprensión rápida.
  * Cálculo Mental Contextualizado: 5 operaciones mentales acordes al grado y dosificación de la Semana {semana_seleccionada} de 37.
  * Problema Matemático Razonado: Situación problemática contextualizada en la comunidad escolar de Durango con enunciado, datos, operaciones y resultado interpretado.

# IV. SECUENCIA DIDÁCTICA DETALLADA (PLANO DIDÁCTICO POR SESIONES: {', '.join(dias_seleccionados)})
Genera la secuencia didáctica ÚNICAMENTE para estos días: {dias_seleccionados}. Distribuye los momentos (Inicio, Desarrollo, Cierre) respetando estos días exactos. No inventes días adicionales.
Es OBLIGATORIO alinear cada sesión con el Anexo Didáctico específico de la plataforma, los libros SEP correspondientes y las consignas del dossier de búsqueda cruzada.
Estructura la Secuencia Didáctica separando claramente cada día. Desarrolla detalladamente exactamente una sesión por cada día en {dias_seleccionados} (total: {num_sesiones} sesiones):
### Sesión N: [Día de la semana] [Fecha oficial 2026] - [Nombre de la Sesión / Momento del Proyecto: {proyecto_info.get('titulo_proyecto', '')}]
- **Tiempo estimado:** (ej. 90 minutos)
- **Inicio (15-20 min):** Preguntas detonadoras, recuperación de conocimientos previos y activación del interés.
- **Desarrollo (50-60 min):**
  * Actividades con estímulos KINESTÉSICOS vivenciales (manipulación de material concreto, dinámicas activas, dramatización, estaciones de trabajo colaborativo para los 26 alumnos).
  * Actividades con recursos VISUALES estructurados (elaboración de organizadores gráficos, esquemas ilustrados, infografías a color).
  * Articulación transversal de los 4 Campos Formativos y consulta de páginas sugeridas de libros SEP (Proyectos, Nuestros Saberes, Múltiples Lenguajes).
  * Cruce obligatorio con el Anexo específico de la Semana {semana_seleccionada} asignado a este día.
- **Cierre (15-20 min):** Socialización comunitaria, síntesis, conclusiones colectivas y metacognición.
- **Recursos didácticos y materiales:** Materiales vivenciales, cuadernos, libros SEP, recursos del aula y cita explícita del Anexo correspondiente a este día.
- **Evidencia / Producto de la sesión:** Qué registrará o elaborará el estudiante a partir del anexo del día.


# V. INSTRUMENTO DE EVALUACIÓN FORMATIVA
### Rúbrica Analítica de Desempeño ({fase_correspondiente} - {grado_seleccionado})
Diseña una tabla de Rúbrica Analítica con indicadores observables que evalúen:
1) Comprensión lectora e inferencias.
2) Velocidad y fluidez lectora.
3) Ortografía y redacción autónoma.
4) Participación comunitaria y uso crítico de tecnologías.
5) Desempeño vivencial kinestésico y visual de los 26 alumnos.
| Criterio / Indicador de Logro | Nivel Sobresaliente | Nivel Satisfactorio | Nivel Básico | Requiere Apoyo |

# VI. AJUSTES RAZONABLES Y ATENCIÓN A LA DIVERSIDAD (BAP - DUA)
Estrategias concretas para los 26 alumnos del grupo, atendiendo de manera prioritaria a los estilos KINESTÉSICO y VISUAL, la nivelación en fluidez lectora/ortografía y el acceso equitativo a tecnologías y recursos.

# VII. OBSERVACIONES GENERALES Y ESPACIO DE SEGUIMIENTO
Reflexiones docentes para el diario de clase y vinculación con los compromisos del Programa Analítico oficial (Ciclo 2026-2027).
"""

    # Configuración de búsqueda web (Google Search Grounding: tools='google_search_retrieval' / google_search)
    call_config = None
    if busqueda_web:
        try:
            call_config = types.GenerateContentConfig(tools=[{"google_search": {}}])
        except Exception:
            try:
                call_config = types.GenerateContentConfig(tools=[{"google_search_retrieval": {}}])
            except Exception:
                call_config = {"tools": [{"google_search": {}}]}

    # Sistema de reintentos automáticos (Manejo de Errores 503 UNAVAILABLE, fallas de conexión y tiempos de espera)
    max_intentos = 3
    for intento in range(1, max_intentos + 1):
        try:
            call_kwargs = {
                "model": "gemini-3.8-flash",
                "contents": prompt
            }
            if call_config:
                call_kwargs["config"] = call_config
            response = client.models.generate_content(**call_kwargs)
            return response.text, prompt
        except (
            ConnectionError,
            TimeoutError,
            socket.timeout,
            socket.gaierror,
            socket.error,
            OSError,
            requests.exceptions.RequestException,
            *( [httpx.RequestError, httpx.TimeoutException] if httpx else [] )
        ) as conn_err:
            if intento < max_intentos:
                st.warning(f"⚠️ Inestabilidad de red o tiempo de espera con la API de Gemini (intento {intento}/{max_intentos}). Reintentando en 3 segundos...")
                time.sleep(3)
            else:
                st.error("No hay conexión a internet o se agotó el tiempo de espera al comunicarse con Gemini.")
                raise ConnectionError(
                    f"Falla de conexión a internet o tiempo de espera agotado al consultar la API de Gemini: {conn_err}"
                ) from conn_err
        except Exception as e:
            error_str = str(e)
            is_conn_or_timeout = any(term in error_str.lower() for term in [
                "connection", "conexión", "timed out", "timeout", "connecterror",
                "readtimeout", "network", "unreachable", "getaddrinfo", "econnreset",
                "econnrefused", "temporary failure in name resolution"
            ])
            if is_conn_or_timeout:
                if intento < max_intentos:
                    st.warning(f"⚠️ Error de red o tiempo de espera detectado (intento {intento}/{max_intentos}). Reintentando en 3 segundos...")
                    time.sleep(3)
                else:
                    st.error("Error de conexión con la API de Gemini tras varios reintentos.")
                    raise ConnectionError(
                        f"Error de conexión o tiempo de espera al comunicarse con Gemini: {error_str}"
                    ) from e
            elif "503" in error_str:
                if intento < max_intentos:
                    st.warning("Servidores de Google saturados. Reintentando en 5 segundos...")
                    time.sleep(5)
                else:
                    st.error("Servidores de Google saturados tras 3 intentos. Por favor, intenta más tarde.")
                    raise e
            else:
                # Si el error no es de conexión ni 503, se propaga para su manejo
                raise e

def generate_sample_fallback(
    datos_escuela: Dict[str, Any],
    campos_formativos: list,
    metodologia: Union[str, list],
    ejes: list,
    dias_seleccionados: list = None,
    contexto_url: str = "",
    **kwargs
) -> str:
    """
    Genera una planeación didáctica pre-elaborada completa de 6° Grado en caso de que
    el usuario desee visualizar el resultado o explorar la app antes de ingresar su API Key,
    ajustando las rutinas y sesiones estrictamente a los días seleccionados.
    """
    escuela = datos_escuela.get('nombre_escuela', 'Escuela Primaria “Revolución Social de 1910”')
    cct = datos_escuela.get('cct', '10EPR0361N')
    docente = datos_escuela.get('docente', 'Maestra Aday Domínguez Domínguez')
    director = datos_escuela.get('director', 'Guillermo Gerardo Borjas Díaz')
    grado_seleccionado = datos_escuela.get('grado', '6° de Primaria')
    fase_correspondiente = datos_escuela.get('fase', 'Fase 5')
    grupo = datos_escuela.get('grupo', 'A')
    periodo = datos_escuela.get('periodo', 'Semana 20 de 37')
    ciclo = datos_escuela.get('ciclo_escolar', '2026-2027')

    if dias_seleccionados is None:
        dias_seleccionados = datos_escuela.get('dias_seleccionados') or datos_escuela.get('dias_planeados') or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    if not dias_seleccionados:
        dias_seleccionados = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    num_sesiones = len(dias_seleccionados)

    semana_num = kwargs.get('semana_seleccionada')
    if not semana_num and datos_escuela:
        semana_num = datos_escuela.get('semana') or datos_escuela.get('semana_seleccionada')
    try:
        semana_num = int(semana_num or 1)
        semana_num = max(1, min(37, semana_num))
    except Exception:
        semana_num = 1

    periodo = datos_escuela.get('periodo') or f"Semana {semana_num} de 37"
    kempis_data = obtener_proyecto_semana(semana_num)
    vincular_k = kwargs.get('vincular_cuadernillo_kempis', True)
    es_kempis = bool(vincular_k and kempis_data)

    if es_kempis and kempis_data:
        r_mat = kempis_data.get("rutinas_matutinas") or kempis_data.get("rutinas_matutinas_sugeridas") or {}
        r_dictados = r_mat.get("dictado") or {}
        r_calculo = r_mat.get("calculo_mental") or {}
        r_problemas = r_mat.get("problemas_razonados") or {}
        k_campos = list(kempis_data.get("campos", {}).items())
        ef_info = kempis_data.get("efemeride_principal", {})
        sec_dias = kempis_data.get("secuencias_por_dia", {})
        anexos_dia = kempis_data.get("anexos_por_dia", {})

        dias_rutinas_map = {}
        dias_sesiones_map = {}
        for idx, d_nom in enumerate(["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]):
            if isinstance(r_dictados, dict):
                dict_txt = r_dictados.get(d_nom, f"Palabras clave reflexivas para {d_nom} sobre {kempis_data.get('proyecto', 'el proyecto')}.")
            elif isinstance(r_dictados, list) and r_dictados:
                dict_txt = r_dictados[idx % len(r_dictados)]
            else:
                dict_txt = f"Palabras clave ortográficas para {d_nom}."

            if isinstance(r_calculo, dict):
                calc_txt = r_calculo.get(d_nom, f"Operaciones de cálculo mental contextualizadas para {d_nom}.")
            elif isinstance(r_calculo, list) and r_calculo:
                calc_txt = r_calculo[idx % len(r_calculo)]
            else:
                calc_txt = f"Cálculo mental contextualizado para {d_nom}."

            if isinstance(r_problemas, dict):
                prob_txt = r_problemas.get(d_nom, f"Problema razonado de situaciones comunitarias en Durango.")
            elif isinstance(r_problemas, list) and r_problemas:
                prob_txt = r_problemas[idx % len(r_problemas)]
            else:
                prob_txt = f"Problema razonado de aplicación para {d_nom}."

            anexo_nom = anexos_dia.get(d_nom) or (k_campos[idx][1].get("anexo_nombre") if idx < len(k_campos) else f"Anexo {semana_num}.{idx+1}")

            dias_rutinas_map[d_nom] = (
                f"- **Dictado Ortográfico (Cuadernillo y Proyecto):** {dict_txt}\n"
                f"- **Velocidad y Fluidez Lectora:** Lectura dramatizada y en voz alta (1 minuto) con modulación y registro de fluidez.\n"
                f"- **Cálculo Mental Contextualizado:** {calc_txt}\n"
                f"- **Problema Razonado Comunitario:** {prob_txt}"
            )

            s_info = sec_dias.get(d_nom, {})
            inicio_s = s_info.get("inicio") or (k_campos[idx][1].get("inicio") if idx < len(k_campos) else "Activación colectiva y recuperación de saberes previos.")
            desarrollo_s = s_info.get("desarrollo") or (k_campos[idx][1].get("desarrollo") if idx < len(k_campos) else "Indagación y aplicación práctica en comunidades de aprendizaje.")
            cierre_s = s_info.get("cierre") or (k_campos[idx][1].get("cierre") if idx < len(k_campos) else "Puesta en común, síntesis y coevaluación grupal.")

            proy_dia = s_info.get("proyecto") or (
                "¡Mi comunidad se expresa!" if d_nom == "Lunes" else
                "El poder de la alimentación" if d_nom == "Martes" else
                "Contribuyo con los servicios de mi escuela" if d_nom == "Miércoles" else
                "El club de las nutrias" if d_nom == "Jueves" else
                ("Descubrimiento de América y Encuentro de Dos Mundos (12 de Octubre) e Integración Colegiada" if semana_num == 6 else "Día Mundial de la Alimentación (16 de Octubre) e Integración Colegiada")
            )
            campo_dia = s_info.get("campo") or (
                "Lenguajes" if d_nom == "Lunes" else
                "Saberes y Pensamiento Científico" if d_nom == "Martes" else
                "Ética, Naturaleza y Sociedades" if d_nom == "Miércoles" else
                "De lo Humano y lo Comunitario" if d_nom == "Jueves" else
                "Conmemoración Cívica e Histórica / Cierre Colegiado"
            )

            dias_sesiones_map[d_nom] = f"""Fase de Intervención: {proy_dia} ({campo_dia}) — {d_nom}
- **Tiempo estimado:** 90 minutos.
- **Inicio (15-20 min):**
  * {inicio_s}
- **Desarrollo (50-60 min):**
  * {desarrollo_s}
  * Aplicación del anexo imprimible: `{anexo_nom}`.
- **Cierre (15-20 min):**
  * {cierre_s}
- **Recursos didácticos:** Libros de texto gratuitos SEP, Ficha de trabajo ({anexo_nom}) y libreta del alumno.
- **Evidencia / Evaluación formativa:** Ficha de trabajo resuelta: `{anexo_nom}` y registro en rúbrica analítica."""

        sample_rutinas = dias_rutinas_map
        sample_sesiones = dias_sesiones_map

        if semana_num in [6, 7]:
            nombre_proyecto_fallback = f"Proyectos Integradores de 6° Grado (¡Mi comunidad se expresa!, El poder de la alimentación, Contribuyo con los servicios de mi escuela, El club de las nutrias) — Semana {semana_num} (Del 5 al 16 de Octubre)"
            proposito_fallback = (
                f"Que las y los 26 alumnos de 6° Grado Grupo 'A' desarrollen transversalmente los proyectos oficiales de la NEM "
                f"para la Semana {semana_num} (bloque del 5 al 16 de octubre), fortaleciendo la comprensión "
                f"lectora, el cálculo contextualizado y la convivencia pacífica con los anexos del Cuadernillo Profa. Kempis."
            )
        else:
            nombre_proyecto_fallback = f"{kempis_data.get('titulo_general', kempis_data.get('proyecto', 'Proyecto Integrador'))} — Proyecto Oficial SEP"
            proposito_fallback = f"Que las y los 26 alumnos de 6° Grado Grupo 'A' integren y apliquen los aprendizajes de la Semana {semana_num} ({kempis_data.get('mes', '2026')}) a través del proyecto '{kempis_data.get('proyecto', 'Integrador')}', fortaleciendo la comprensión lectora, velocidad lectora, ortografía y resolución de problemas comunitarios con dinámicas vivenciales y fichas prácticas."
        
        filas_art = []
        campos_4_base = ["Lenguajes", "Saberes y Pensamiento Científico", "Ética, Naturaleza y Sociedades", "De lo Humano y lo Comunitario"]
        campos_filtrados = [c for c in campos_formativos if c in campos_4_base] if campos_formativos else campos_4_base
        campos_en_tabla = set()
        if k_campos:
            for c_n, c_v in k_campos:
                c_n_match = any((c_f.lower() in c_n.lower() or c_n.lower() in c_f.lower()) for c_f in campos_filtrados)
                if not c_n_match:
                    continue
                for c_base in campos_filtrados:
                    if c_base.lower() in c_n.lower() or c_n.lower() in c_base.lower():
                        campos_en_tabla.add(c_base)
                pda_texto = c_v.get("pda_vinculado") or c_v.get("pda") or "Proceso de desarrollo de aprendizaje oficial NEM"
                proy_campo = c_v.get("proyecto_oficial", "")
                tema_completo = f"{c_v.get('tema', kempis_data.get('proyecto', ''))}" + (f" (Proyecto: '{proy_campo}')" if proy_campo else "")
                libro_campo = c_v.get("libro_sep") or f"Libros de Texto SEP y Anexos de la Semana {semana_num}"
                ns_campo = c_v.get("nuestros_saberes")
                if ns_campo and ns_campo not in libro_campo:
                    libro_campo = f"{libro_campo} | {ns_campo}"
                filas_art.append(
                    f"| **{c_n}** | {tema_completo} | {pda_texto} | {libro_campo} | Comprensión lectora, velocidad lectora, ortografía y cálculo contextualizado |"
                )
            for c_faltante in campos_filtrados:
                if c_faltante not in campos_en_tabla:
                    filas_art.append(
                        f"| **{c_faltante}** | {kempis_data.get('proyecto', 'Proyecto Integrador')} | Procesos de desarrollo de aprendizaje oficiales acordes a la Fase 5 y la Semana {semana_num} | Libros de Texto SEP (LTG) | Comprensión lectora, velocidad, ortografía y cálculo contextualizado |"
                    )
        else:
            for c_n in campos_filtrados:
                filas_art.append(
                    f"| **{c_n}** | {kempis_data.get('proyecto', 'Proyecto Integrador')} | Procesos de desarrollo de aprendizaje acordes a la Fase 5 y la Semana {semana_num} | Libros de Texto SEP (LTG) | Comprensión lectora, velocidad, ortografía y cálculo contextualizado |"
                )
        tabla_articulacion_str = "\n".join(filas_art)
    else:
        nombre_proyecto_fallback = '"Voces Comunitarias en Acción: Lectura, Ortografía y Tecnologías para el Bienestar"'
        proposito_fallback = 'Que las y los 26 alumnos de 6° Grado Grupo “A” investiguen y elaboren textos informativos y argumentativos sobre temas de interés comunitario, superando las dificultades detectadas en comprensión lectora, velocidad lectora y ortografía, mediante dinámicas activas kinestésicas y organizadores visuales estructurados, promoviendo la lectura en familia y el uso crítico de tecnologías.'
        tabla_art_dict = {
            "Lenguajes": "| **Lenguajes** | Comprensión y producción de textos informativos y argumentativos sobre temas comunitarios. | Lee comprensivamente textos informativos y reflexiona sobre su organización; elabora resúmenes, fichas de opinión y trípticos con ortografía cuidada y coherencia sintáctica para difundir en su comunidad. | *Proyectos Comunitarios (6° grado)* (págs. 20-35) y *Múltiples lenguajes (6° grado)* (págs. 40-47) | Comprensión lectora, velocidad y ortografía |",
            "Saberes y Pensamiento Científico": "| **Saberes y Pensamiento Científico** | Relaciones de proporcionalidad y cálculo de porcentajes aplicados a la comunidad. | Resuelve situaciones problemáticas cotidianas que implican calcular porcentajes, fracciones y razones aplicadas a datos estadísticos de lectura y salud comunitaria. | *Nuestros Saberes (6° grado)* (págs. 68-76) y *Proyectos de Aula (6° grado)* (págs. 82-95) | Comprensión de textos científicos y cálculo mental |",
            "Ética, Naturaleza y Sociedades": "| **Ética, Naturaleza y Sociedades** | Movimientos sociales en el México de los siglos XIX y XX: la Independencia y la Revolución Social de 1910. | Analiza críticamente las causas y consecuencias de la Revolución Social de 1910 y los ideales de justicia social, reconociendo su vigencia en la transformación democrática de su entorno escolar y comunitario. | *Nuestros Saberes (6° grado)* (págs. 140-149) y *Proyectos Escolares (6° grado)* (págs. 80-92) | Análisis crítico de fuentes y redacción cívica |",
            "De lo Humano y lo Comunitario": "| **De lo Humano y lo Comunitario** | La comunidad como espacio para el aprendizaje y el bienestar común. | Diseña y organiza acciones colectivas para fomentar la lectura compartida en el hogar y promover el acceso ético y equitativo a tecnologías y recursos de información. | *Proyectos Comunitarios (6° grado)* (págs. 50-63) | Fomento a la lectura comunitaria y acceso a tecnologías |"
        }
        campos_filtrados = [c for c in campos_formativos if c in tabla_art_dict] if campos_formativos else list(tabla_art_dict.keys())
        tabla_articulacion_str = "\n".join(tabla_art_dict[c] for c in campos_filtrados)

        sample_rutinas = {
            "Lunes": "- **Dictado Ortográfico (Reglas y Acentuación):** 1. Comprensión, 2. Argumentación, 3. Tecnología, 4. Científico, 5. Análisis.\n- **Velocidad y Fluidez Lectora:** Lectura guiada en voz alta (1 minuto) de un fragmento de *Múltiples Lenguajes (6° grado)*, cronometrando palabras por minuto y evaluando modulación.\n- **Cálculo Mental Contextualizado:** a) 350 + 650, b) 1500 - 450, c) 12 x 8, d) El 25% de 800, e) 4.5 x 10.\n- **Problema Razonado:** En la biblioteca escolar de la Primaria Revolución Social de 1910 hay 650 libros. Si el 40% son textos informativos y el resto narrativos, ¿cuántos libros informativos hay y cuántos faltan para duplicar la colección?",
            "Martes": "- **Dictado Ortográfico (Grafías B/V y C/S/Z):** 1. Convivencia, 2. Civilización, 3. Accesibilidad, 4. Búsqueda, 5. Precisión.\n- **Velocidad y Fluidez Lectora:** Lectura por parejas en eco para corregir pausas y silabeos con énfasis en signos de puntuación.\n- **Cálculo Mental Contextualizado:** a) 3/4 + 2/4, b) 480 ÷ 6, c) 25 x 4, d) 2000 - 675, e) Triple de 3.25.\n- **Problema Razonado:** Para equipar el rincón de lectura comunitaria, 26 alumnos reunieron $78 pesos cada uno. ¿Cuánto dinero recolectaron en total y cuánto sobrará si adquieren 12 paquetes de libros de $145 pesos cada uno?",
            "Miércoles": "- **Dictado Ortográfico (Palabras Graves y Esdrújulas):** 1. Sintético, 2. Analítico, 3. Préstamo, 4. Crítico, 5. Éxito.\n- **Velocidad y Fluidez Lectora:** Lectura individual con registro de palabras leídas por minuto y rescate oral de la idea central del texto.\n- **Cálculo Mental Contextualizado:** a) 15 x 7, b) 1200 - 380, c) 1/2 de 450, d) 6.8 + 3.2, e) 81 ÷ 9.\n- **Problema Razonado:** De los 26 alumnos del grupo de 6° 'A', 18 utilizan computadoras o tabletas para consultar información en internet y el resto consulta enciclopedias físicas. ¿Qué fracción y qué porcentaje del grupo utiliza medios digitales?",
            "Jueves": "- **Dictado Ortográfico (Signos de Puntuación y Conectores):** 1. Por consiguiente, 2. No obstante, 3. Explicación, 4. Indagación, 5. Cohesión.\n- **Velocidad y Fluidez Lectora:** Dinámica 'Lectura de relevos': cada alumno lee un párrafo cuidando entonación y volumen audible.\n- **Cálculo Mental Contextualizado:** a) 60 x 7, b) 3000 - 850, c) 3/5 + 1/5, d) Cuádruple de 25, e) 72 ÷ 8 + 15.\n- **Problema Razonado:** Un informe escolar de investigación comunitaria tiene 1,200 palabras. Si un estudiante lee a una velocidad promedio de 150 palabras por minuto, ¿cuántos minutos tardará en leer el informe completo?",
            "Viernes": "- **Dictado Ortográfico (Léxico Científico e Informativo):** 1. Hipótesis, 2. Verificación, 3. Sociedad, 4. Biodiversidad, 5. Solidaridad.\n- **Velocidad y Fluidez Lectora:** Círculo de lectura compartida: lectura expresiva dramatizada con énfasis en posturas y gesticulación kinestésica.\n- **Cálculo Mental Contextualizado:** a) 90 x 5, b) 800 - 245, c) 0.50 + 0.75, d) 56 ÷ 7, e) 250 x 4.\n- **Problema Razonado:** Si se imprimen 26 trípticos informativos para promover la lectura comunitaria y cada juego de copias cuesta $6.50 pesos, ¿cuál es el costo total y cuál sería el descuento si se aplica el 15% por volumen?"
        }

        sample_sesiones = {
            "Lunes": """Fase 1. Planeación (Momento 1: Identificación y Momento 2: Recuperación)
- **Tiempo estimado:** 90 minutos.
- **Inicio (20 min):**
  * Bienvenida activa y realización de la rutina matutina (dictado y cálculo mental).
  * Dinámica detonadora "¿Qué desayunamos hoy?": En plenaria, las y los alumnos comparten sus alimentos cotidianos en una lluvia de ideas en el pizarrón.
  * Planteamiento de la pregunta generadora del proyecto: *¿De qué manera los alimentos que consumimos en la escuela y en casa impactan en nuestra energía, salud y concentración?*
- **Desarrollo (50 min):**
  * Lectura compartida en el libro *Nuestros Saberes: 6° grado*, páginas 68 a 71, analizando los conceptos de alimentos naturales, procesados y ultraprocesados.
  * En comunidades de 4 integrantes, elaboran una lista comparativa en sus libretas dividida en dos columnas: "Alimentos cotidianos nutritivos" vs. "Alimentos ultraprocesados frecuentes en la comunidad".
  * El docente acompaña a los equipos guiando la identificación del Plato del Bien Comer y la Jarra del Buen Beber.
- **Cierre (20 min):**
  * Puesta en común comunitaria: Un vocero por equipo expone uno de sus hallazgos.
  * Registro en el pizarrón del primer acuerdo de asamblea de aula para el desarrollo de la investigación.
- **Recursos didácticos:** Libro *Nuestros Saberes*, cuaderno del alumno, plumones y papel bond.
- **Evidencia:** Tabla comparativa en el cuaderno y ficha de registro de saberes previos.""",

            "Martes": """Fase 1. Planeación (Momento 3: Planificación) y Fase 2. Acción (Momento 4: Acercamiento)
- **Tiempo estimado:** 90 minutos.
- **Inicio (15 min):**
  * Rutina de inicio del día (dictado, cálculo mental y problema razonado de fracciones).
  * Recordatorio de los acuerdos de la sesión previa y lectura de una cápsula del libro *Múltiples Lenguajes*.
- **Desarrollo (55 min):**
  * Consulta del libro *Proyectos Comunitarios (6° grado)*, páginas 24 a 27.
  * Diseño participativo de un guion de entrevista para consultar a los encargados de la cooperativa escolar y familiares sobre los hábitos de consumo alimenticio.
  * Los estudiantes redactan 5 preguntas abiertas con signos de interrogación correctos y ortografía cuidada.
  * Simulación de la entrevista en parejas mediante juego de roles (entrevistador y entrevistado).
- **Cierre (20 min):**
  * Revisión en coevaluación del cuestionario diseñado.
  * Tarea de vinculación familiar: Aplicar la entrevista a dos miembros de la familia o vecinos.
- **Recursos didácticos:** Libro *Proyectos Comunitarios*, libreta de notas, lápiz y borrador.
- **Evidencia:** Borrador del guion de entrevista validado con criterios de claridad y pertinencia.""",

            "Miércoles": """Fase 2. Acción (Momento 5: Comprensión y Producción)
- **Tiempo estimado:** 90 minutos.
- **Inicio (15 min):**
  * Rutina matutina con énfasis en cálculo mental de proporciones y porcentajes simples.
  * Puesta en común de las anécdotas al aplicar la entrevista en casa.
- **Desarrollo (55 min):**
  * Vaciado colaborativo de los datos obtenidos en las entrevistas: Número de personas que consumen agua natural vs. refrescos y frutas vs. frituras.
  * Construcción de una gráfica de barras sencilla en el cuaderno para representar las frecuencias.
  * Introducción al formato del **Tríptico Informativo de Salud**: Estructura de portada, títulos, subtítulos, argumentos científicos del Plato del Bien Comer e ilustraciones.
  * Inicio del borrador del tríptico en hojas blancas dobladas en tres partes.
- **Cierre (20 min):**
  * Exposición de los primeros avances del tríptico.
  * Retroalimentación formativa del docente destacando el uso de conectores lógicos y datos verídicos.
- **Recursos didácticos:** Hojas blancas, colores, reglas, datos de las entrevistas y recortes.
- **Evidencia:** Gráfica de barras en el cuaderno y maqueta inicial del tríptico informativo.""",

            "Jueves": """Fase 2. Acción (Momento 6: Reconocimiento y Momento 7: Concreción)
- **Tiempo estimado:** 90 minutos.
- **Inicio (15 min):**
  * Rutina matutina (dictado ortográfico de términos científicos y problema matemático de medidas de capacidad).
  * Reflexión grupal sobre la importancia de la revisión y corrección de textos propios.
- **Desarrollo (55 min):**
  * Intercambio de borradores de trípticos entre comunidades de aprendizaje mediante una rúbrica sencilla de coevaluación.
  * Incorporación de sugerencias de mejora: Corrección de puntuación, mayúsculas y claridad visual.
  * Elaboración de la versión final del tríptico con tipografía cuidada, colores vivos y mensajes persuasivos para promover estilos de vida activos y saludables.
  * Ensayo breve de cómo presentarán el tríptico a otros grupos de la primaria Revolución Social 1910.
- **Cierre (20 min):**
  * Organización de la jornada de difusión: Asignación de roles (presentadores, encargados de registro fotográfico, moderadores).
- **Recursos didácticos:** Trípticos finalizados, cartulinas de apoyo, marcadores y lista de cotejo.
- **Evidencia:** Tríptico informativo final terminado y evaluado con rúbrica docente.""",

            "Viernes": """Fase 3. Intervención (Momentos 8, 9, 10 y 11: Difusión, Consideraciones y Avances)
- **Tiempo estimado:** 90 minutos.
- **Inicio (15 min):**
  * Rutina de inicio del día (dictado, cálculo mental y problema matemático integrador).
  * Palabras de motivación y recordatorio del protocolo de respeto durante las exposiciones en otros salones.
- **Desarrollo (50 min):**
  * Visita a grupos de Fase 3 y 4 (1° a 4° grado) para entregar y explicar los trípticos informativos comunitarios.
  * Colocación de un periódico mural de salud en el patio cívico escolar de la Primaria Revolución Social 1910 con el lema *"Alimentación Sana para Mentes Fuertes"*.
  * Registro de firmas y comentarios de los docentes y compañeros visitantes.
- **Cierre (25 min):**
  * Círculo de diálogo reflexivo de asamblea: ¿Qué aprendimos?, ¿qué dificultades superamos?, ¿cómo cambió nuestra manera de alimentarnos?
  * Autoevaluación final de la experiencia mediante una diana de evaluación formativa.
- **Recursos didácticos:** Mural escolar, cinta adhesiva, trípticos y dianas de evaluación.
- **Evidencia:** Registro fotográfico de la socialización, diana de autoevaluación y notas en el diario de campo."""
        }

    dias_fechas_map = datos_escuela.get("dias_fechas", {}) if isinstance(datos_escuela, dict) else {}
    rutinas_str = ""
    sesiones_str = ""
    for idx, dia in enumerate(dias_seleccionados, 1):
        r_txt = sample_rutinas.get(dia, sample_rutinas["Lunes"])
        dia_header = dias_fechas_map.get(dia, dia)
        rutinas_str += f"### Sesión {idx} ({dia_header}):\n{r_txt}\n\n"
        s_txt = sample_sesiones.get(dia, sample_sesiones["Lunes"])
        sesiones_str += f"### Sesión {idx}: {dia_header} - {s_txt}\n\n"

    dias_str = ", ".join(dias_seleccionados)
    metodologia_fallback_str = formatear_metodologia_str(metodologia)

    return f"""# I. DATOS DE IDENTIFICACIÓN Y DOSIFICADOR GENERAL DEL PROYECTO

- **Nombre del Proyecto:** {nombre_proyecto_fallback}
- **Escuela:** {escuela} | **C.C.T.:** {cct} | **Zona 49, Sector 02, Durango**
- **Docente:** {docente} | **Director:** {director}
- **Fase y Grado:** {fase_correspondiente} — {grado_seleccionado} Grupo '{grupo}' (Matrícula: 26 alumnos)
- **Temporalidad:** {periodo} ({num_sesiones} sesiones: {dias_str}) | **Ciclo Escolar:** {ciclo}
- **Escenario:** Comunitario, Escolar y de Aula
- **Metodología Sociocrítica:** {metodologia_fallback_str}
- **Ejes Articuladores:** {', '.join(ejes)}
- **Propósito:** {proposito_fallback}

---

# II. ARTICULACIÓN CURRICULAR TRANSVERSAL (TABLA NEM - 4 CAMPOS FORMATIVOS)

| Campo Formativo | Contenido Sintético | Procesos de Desarrollo de Aprendizaje (PDA) | Vinculación con Libros SEP (LTG) | Problemática Analítica Atendida |
| :--- | :--- | :--- | :--- | :--- |
{tabla_articulacion_str}

---

# III. ACTIVIDADES DE INICIO DEL DÍA (RUTINA MATUTINA - {num_sesiones} SESIONES: {dias_str.upper()})

{rutinas_str.strip()}

---

# IV. SECUENCIA DIDÁCTICA DETALLADA (PLANO DIDÁCTICO POR SESIONES: {dias_str.upper()})

{sesiones_str.strip()}

---

# V. INSTRUMENTO DE EVALUACIÓN FORMATIVA

### Rúbrica Analítica de Desempeño ({fase_correspondiente} - {grado_seleccionado})

| Criterio de Evaluación | Nivel Sobresaliente (10 - 9) | Nivel Satisfactorio (8 - 7) | Nivel Básico (6) | Requiere Apoyo (5) |
| :--- | :--- | :--- | :--- | :--- |
| **Comprensión Lectora e Inferencias** | Identifica ideas centrales y secundarias, infiere intenciones del autor y emite juicios críticos fundamentados en textos informativos. | Reconoce ideas principales y responde preguntas inferenciales básicas con autonomía. | Comprende el sentido global del texto pero requiere orientación para realizar inferencias. | Dificultad para rescatar ideas principales y comprender vocabulario contextual. |
| **Fluidez y Velocidad Lectora** | Lee en voz alta con modulación impecable, ritmo adecuado, dicción clara y respetando todos los signos de puntuación. | Lee con fluidez aceptable y volumen adecuado; comete pocas pausas innecesarias. | Lee con ritmo lento o silabeo ocasional, requiriendo apoyo para respetar signos de puntuación. | Lectura silábica o entrecortada que dificulta la comprensión personal y grupal. |
| **Ortografía y Producción Textual** | Redacta textos argumentativos/informativos con acentuación precisa, grafías correctas y conectores lógicos variados. | Elabora textos con estructura coherente y comete errores ortográficos mínimos que no alteran el sentido. | Textos con ideas aisladas o varios errores de concordancia, acentuación y puntuación. | Escritos breves e incompletos con deficiencias ortográficas severas. |
| **Trabajo Kinestésico y Visual (26 Alumnos)** | Participa proactivamente en dinámicas vivenciales y elabora esquemas visuales de alta calidad y creatividad. | Cumple adecuadamente en las estaciones prácticas y colabora en el diseño de organizadores visuales. | Participa en dinámicas pero muestra dispersión en el trabajo visual o manual. | Escasa participación en las dinámicas vivenciales y de trabajo en equipo. |

---

# VI. AJUSTES RAZONABLES Y ATENCIÓN A LA DIVERSIDAD (BAP - DUA)

1. **Principio de Múltiples Formas de Representación (DUA - Enfoque Visual):**
   - Uso intensivo de apoyos visuales de alto contraste (organizadores gráficos, tablas comparativas, infografías ilustradas y códigos de color para identificar sujeto, verbo y nexos en la redacción).
   - Proyección o exposición en láminas de modelos visuales para anclar conceptos abstractos en los 26 alumnos.
2. **Principio de Acción y Expresión (DUA - Enfoque Kinestésico):**
   - Estaciones de aprendizaje activas donde los alumnos manipulan fichas ortográficas móviles (acentuación, grafías dudosas b/v, c/s/z) y material concreto para resolver problemas de proporcionalidad y porcentajes.
   - Dinámicas vivenciales de juego de roles (entrevistadores, moderadores de debate y bibliotecarios comunitarios) para favorecer el aprendizaje por la acción.
3. **Atención a la Comprensión y Velocidad Lectora:**
   - Lectura en parejas solidarias (tutoría entre pares) con cronometrado amistoso y registro personal de avances de velocidad y fluidez.
   - Guías de interrogación de textos con preguntas detonadoras visuales para facilitar inferencias.
4. **Asuntos Comunitarios y Acceso a Tecnologías:**
   - Trabajo colaborativo en equipos heterogéneos para garantizar que los alumnos sin conectividad permanente en casa tengan acceso equitativo a dispositivos y recursos digitales escolares.

---

# VII. OBSERVACIONES GENERALES Y ESPACIO DE SEGUIMIENTO

- **Seguimiento del Diario de Clase:** Registro diario de los avances individuales de los 26 alumnos en fluidez lectora, precisión ortográfica y participación activa en proyectos.
- **Vinculación con el Programa Analítico Oficial (Ciclo 2026-2027):** Este plano didáctico atiende de forma directa los 4 ejes prioritarios identificados en el diagnóstico institucional de la Primaria “Revolución Social de 1910” (CCT: 10EPR0361N, Durango): comprensión lectora, velocidad lectora, ortografía y promoción de la lectura con acceso a tecnologías.
"""

# Alias de compatibilidad para generación demo
generar_planeacion_demo = generate_sample_fallback

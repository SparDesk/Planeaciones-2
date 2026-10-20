# ==========================================
# ESQUEMA PRINCIPAL DE LA NUEVA APP (app_planeaciones.py)
# Sistema Inteligente de Planeaciones Escolares (NEM 2026)
# Educación Primaria • Fase 5 (6° Grado)
# Escuela Primaria “Revolución Social de 1910” • C.C.T. 10EPR0361N • Durango, Dgo.
# ==========================================
from __future__ import annotations

import os
import sys
import datetime
import io
from io import BytesIO
from typing import Dict, Any, List, Optional
import streamlit as st

# Cargar variables de entorno si existe .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Importaciones de los módulos del ecosistema NEM
try:
    from nem_data import (
        DATOS_PREDETERMINADOS,
        CAMPOS_FORMATIVOS,
        METODOLOGIAS_SOCIOCRITICAS,
        EJES_ARTICULADORES,
        CONTENIDOS_PDA_POR_GRADO,
        PROGRAMA_ANALITICO_OFICIAL_6TO,
        parsear_metodologia_lista,
        formatear_metodologia_str
    )
except ImportError:
    DATOS_PREDETERMINADOS = {
        "nombre_escuela": "Escuela Primaria “Revolución Social de 1910”",
        "cct": "10EPR0361N",
        "zona_escolar": "Zona 49",
        "sector": "Sector 02",
        "entidad": "Durango",
        "docente": "Maestra Aday Domínguez Domínguez",
        "director": "Guillermo Gerardo Borjas Díaz",
        "grado": "6° de Primaria",
        "fase": "Fase 5",
        "grupo": "A",
        "matricula": 26,
        "estilos_aprendizaje": "Kinestésico y Visual",
        "periodo": "Semana 1 de 37",
        "ciclo_escolar": "2026-2027",
        "turno": "Matutino"
    }
    CAMPOS_FORMATIVOS = [
        "Lenguajes",
        "Saberes y Pensamiento Científico",
        "Ética, Naturaleza y Sociedades",
        "De lo Humano y lo Comunitario"
    ]
    METODOLOGIAS_SOCIOCRITICAS = {}
    EJES_ARTICULADORES = [
        "Inclusión", "Pensamiento crítico", "Interculturalidad crítica",
        "Igualdad de género", "Vida saludable",
        "Apropiación de las culturas a través de la lectura y la escritura",
        "Artes y experiencias estéticas"
    ]
    CONTENIDOS_PDA_POR_GRADO = {}
    PROGRAMA_ANALITICO_OFICIAL_6TO = {}
    def parsear_metodologia_lista(m): return [str(m)] if m else ["Aprendizaje Basado en Proyectos Comunitarios"]
    def formatear_metodologia_str(m): return str(m or "Aprendizaje Basado en Proyectos Comunitarios")

try:
    from cuadernillo_kempis import (
        obtener_proyecto_semana,
        CATALOGO_PROYECTOS_SEP_37_SEMANAS,
        PROYECTOS_OFICIALES_6TO_GRADO
    )
except ImportError:
    obtener_proyecto_semana = lambda *a, **kw: {}
    CATALOGO_PROYECTOS_SEP_37_SEMANAS = {}
    PROYECTOS_OFICIALES_6TO_GRADO = {}

try:
    from conaliteg_scraper import (
        obtener_libros_conaliteg,
        LIBROS_SEP_FALLBACK
    )
except ImportError:
    obtener_libros_conaliteg = lambda: ({}, False)
    LIBROS_SEP_FALLBACK = {}

try:
    from gemini_engine import (
        generate_planeacion,
        generate_sample_fallback,
        AVAILABLE_MODELS,
        DEFAULT_MODEL
    )
except ImportError:
    generate_planeacion = None
    generate_sample_fallback = None
    AVAILABLE_MODELS = ["gemini-3.8-flash"]
    DEFAULT_MODEL = "gemini-3.8-flash"

try:
    from docx_generator import (
        build_docx_planeacion,
        parse_plan_sections
    )
except ImportError:
    build_docx_planeacion = None
    parse_plan_sections = None

try:
    from pdf_generator import build_pdf_planeacion
except ImportError:
    build_pdf_planeacion = None

try:
    from planeaciones_storage import guardar_planeacion, listar_planeaciones
except ImportError:
    guardar_planeacion = None
    listar_planeaciones = lambda *a, **k: []


# ==========================================
# CONFIGURACIÓN DE PÁGINA Y ESTILO VISUAL PREMIUM
# ==========================================
st.set_page_config(
    page_title="Generador de Planeaciones NEM con IA",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de estilos CSS modernos y paleta lila/morada institucional
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;
    }

    h1, h2, h3, h4, .nem-title {
        font-family: 'Outfit', sans-serif !important;
    }

    :root {
        --nem-purple: #7C3AED;
        --nem-purple-dark: #5B21B6;
        --nem-purple-light: #F5F3FF;
        --nem-accent: #8B5CF6;
        --nem-border: #DDD6FE;
    }

    /* Tarjetas principales con borde y sombra suave */
    .nem-hero-card {
        background: linear-gradient(135deg, #FAF5FF 0%, #FFFFFF 60%, #F3E8FF 100%);
        border: 1.5px solid #C4B5FD;
        border-radius: 16px;
        padding: 1.5rem 1.8rem;
        box-shadow: 0 8px 24px rgba(124, 58, 237, 0.08);
        margin-bottom: 1.5rem;
    }

    .nem-badge {
        display: inline-block;
        background: linear-gradient(135deg, #7C3AED, #6D28D9);
        color: #FFFFFF !important;
        padding: 0.28rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }

    .nem-badge-soft {
        display: inline-block;
        background: #EDE9FE;
        color: #5B21B6 !important;
        border: 1px solid #C4B5FD;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }

    .nem-section-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #7C3AED;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }

    .nem-day-card {
        background: #FAF5FF;
        border: 1px solid #DDD6FE;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }

    .stButton>button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease-in-out !important;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# ESTADO DE SESIÓN (SESSION STATE)
# ==========================================
if "plan_generado" not in st.session_state:
    st.session_state["plan_generado"] = None
if "datos_escuela" not in st.session_state:
    st.session_state["datos_escuela"] = dict(DATOS_PREDETERMINADOS)
if "parsed_plan" not in st.session_state:
    st.session_state["parsed_plan"] = None


# ==========================================
# BARRA LATERAL (CONFIGURACIÓN INSTITUCIONAL E IA)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=56)
    st.markdown("### 🏛️ Ficha Institucional")
    st.markdown(f"""
    **{st.session_state['datos_escuela']['nombre_escuela']}**  
    * **C.C.T.:** `{st.session_state['datos_escuela']['cct']}`  
    * **Ubicación:** {st.session_state['datos_escuela']['entidad']} ({st.session_state['datos_escuela']['zona_escolar']} • {st.session_state['datos_escuela']['sector']})  
    * **Docente Titular:** {st.session_state['datos_escuela']['docente']}  
    * **Director:** {st.session_state['datos_escuela']['director']}  
    * **Grado y Grupo:** 6° "A" (Fase 5)  
    * **Matrícula:** 26 alumnos  
    * **Estilos:** Kinestésico y Visual (Enfoque DUA)
    """)

    st.markdown("---")
    st.markdown("### ⚡ Configuración de IA (Gemini)")
    
    # Detección de API Key en entorno o input
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Gemini API Key (Google AI Studio):",
        value=env_api_key,
        type="password",
        help="Clave para generar planeaciones con IA en tiempo real. Si se deja vacía o no hay conexión, se usará el generador curricular base de respaldo NEM."
    )
    api_key_activa = api_key_input.strip() if api_key_input else env_api_key.strip()
    
    modelo_seleccionado = st.selectbox(
        "Modelo de IA:",
        options=AVAILABLE_MODELS,
        index=0 if DEFAULT_MODEL in AVAILABLE_MODELS else 0
    )

    if api_key_activa:
        st.success("🟢 Motor Gemini AI Listo")
    else:
        st.info("💡 Modo Curricular Base NEM 2026 Activo (Sin costo de API)")


# ==========================================
# ENCABEZADO PRINCIPAL DE LA APP
# ==========================================
st.markdown("""
<div class="nem-hero-card">
    <span class="nem-badge">NEM 2026-2027</span>
    <span class="nem-badge-soft">Fase 5 • 6° Grado</span>
    <span class="nem-badge-soft">26 Alumnos (Kinestésico y Visual)</span>
    <span class="nem-badge-soft">Enfoque DUA y Metodologías Sociocríticas</span>
    <h1 style="color: #4C1D95; margin-top: 0.6rem; margin-bottom: 0.2rem; font-size: 2.1rem;">
        📚 Sistema Inteligente de Planeaciones Escolares (NEM 2026)
    </h1>
    <p style="color: #6D28D9; font-size: 1.05rem; margin: 0; font-weight: 500;">
        Educación Primaria • Fase 5 (6° Grado) — Escuela Primaria “Revolución Social de 1910”
    </p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# 1. SELECTOR DE TEMPORALIDAD (DÍA O SEMANA DEL CALENDARIO SEP)
# ==========================================
st.markdown("### 1. ⏱️ Temporalidad y Alcance (Calendario SEP 2026-2027)")

modo_tiempo = st.radio(
    "Seleccionar alcance de la planeación:",
    ["📅 Semana Completa SEP", "📆 Día Específico o Rango de Días"],
    horizontal=True
)

semana_sel = 1
dias_habiles = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
fecha_ini = datetime.date(2026, 9, 1)

if modo_tiempo == "📅 Semana Completa SEP":
    col_sem1, col_sem2 = st.columns([2, 3])
    with col_sem1:
        semana_sel = st.selectbox(
            "Selecciona la Semana Escolar:",
            options=list(range(1, 38)),
            format_func=lambda s: f"Semana {s} (Ciclo Escolar 2026-2027)"
        )
    with col_sem2:
        # Previsualizar el proyecto dosificado oficial de la semana
        info_semana = obtener_proyecto_semana(semana_sel) if obtener_proyecto_semana else {}
        if info_semana:
            nom_proy = info_semana.get("titulo_proyecto") or info_semana.get("proyecto") or info_semana.get("titulo_general", "Proyecto Integrador NEM")
            desc_proy = info_semana.get("descripcion", "Vinculación curricular con los Libros de Texto Gratuitos (LTG).")
            st.markdown(f"""
            <div style="background: #F3E8FF; padding: 0.75rem 1rem; border-radius: 8px; border-left: 3px solid #7C3AED;">
                <strong style="color: #5B21B6;">🎯 Proyecto Dosificado SEP:</strong> {nom_proy}<br>
                <small style="color: #4B5563;">{desc_proy[:160]}...</small>
            </div>
            """, unsafe_allow_html=True)
else:
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        fecha_ini = st.date_input("Fecha de inicio:", datetime.date(2026, 9, 1))
    with col_d2:
        dias_habiles = st.multiselect(
            "Días a planear:",
            ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            default=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        )
        if not dias_habiles:
            st.warning("⚠️ Selecciona al menos un día hábil para la planeación.")
            dias_habiles = ["Lunes"]


# ==========================================
# 2. SELECCIÓN DE CAMPOS FORMATIVOS Y EJES ARTICULADORES
# ==========================================
st.markdown("---")
st.markdown("### 2. 🎯 Campos Formativos, Ejes Articuladores y Programa Analítico")

col_cf1, col_cf2 = st.columns([1, 1])

with col_cf1:
    campos_sel = st.multiselect(
        "Campos Formativos Involucrados:",
        options=CAMPOS_FORMATIVOS,
        default=CAMPOS_FORMATIVOS,
        help="Selección múltiple flexible: selecciona uno, varios o los 4 campos formativos simultáneamente (Lenguajes, Saberes y Pensamiento Científico, Ética, Naturaleza y Sociedades, De lo Humano y lo Comunitario)."
    )
    if not campos_sel:
        st.warning("⚠️ Selecciona al menos un Campo Formativo. Se utilizará 'Lenguajes' por defecto.")
        campos_sel = ["Lenguajes"]

    metodologias_sel = st.multiselect(
        "Metodología(s) Sociocrítica(s) Oficial(es) (NEM):",
        options=[
            "Aprendizaje Basado en Proyectos Comunitarios",
            "Aprendizaje Basado en Indagación (STEAM como enfoque)",
            "Aprendizaje Basado en Problemas (ABPr)",
            "Aprendizaje Servicio (AS)"
        ],
        default=["Aprendizaje Basado en Proyectos Comunitarios"],
        help="Selección múltiple flexible: puedes marcar una, varias o todas las metodologías sociocríticas simultáneamente según los campos formativos articulados."
    )
    if not metodologias_sel:
        st.warning("⚠️ Selecciona al menos una metodología sociocrítica.")
        metodologias_sel = ["Aprendizaje Basado en Proyectos Comunitarios"]

with col_cf2:
    ejes_seleccionados = st.multiselect(
        "Ejes Articuladores (NEM):",
        options=EJES_ARTICULADORES,
        default=["Inclusión", "Pensamiento crítico", "Apropiación de las culturas a través de la lectura y la escritura"]
    )

    # Libros recomendados CONALITEG para 6° grado
    libros_conaliteg_sugeridos = [
        "Proyectos de Aula (6° grado)",
        "Proyectos Escolares (6° grado)",
        "Proyectos Comunitarios (6° grado)",
        "Nuestros Saberes: Libro para alumnos, maestros y familia (6° grado)",
        "Múltiples Lenguajes (6° grado)"
    ]
    libros_seleccionados = st.multiselect(
        "Libros de Texto Gratuitos (LTG / CONALITEG):",
        options=libros_conaliteg_sugeridos,
        default=libros_conaliteg_sugeridos[:3]
    )

# Banco curricular contextualizado para 6° grado (Programa Analítico Durango)
with st.expander("🔍 Ver Contenidos Sintéticos, PDA Oficiales y Problemática Contextual", expanded=False):
    col_pda1, col_pda2 = st.columns(2)
    with col_pda1:
        st.markdown(f"**Contenidos y PDA de Fase 5 ({', '.join(campos_sel)}):**")
        pda_mostrados = 0
        if CONTENIDOS_PDA_POR_GRADO and "6° de Primaria" in CONTENIDOS_PDA_POR_GRADO:
            for c_f in campos_sel:
                pda_c = CONTENIDOS_PDA_POR_GRADO["6° de Primaria"].get(c_f, [])
                if pda_c:
                    st.markdown(f"**📌 {c_f}:**")
                    for it in pda_c[:1]:
                        st.markdown(f"* **Contenido:** {it.get('contenido', '')}")
                        st.markdown(f"  *PDA:* {it.get('pda', '')}")
                        pda_mostrados += 1
        if pda_mostrados == 0:
            st.markdown(f"* Contenidos oficiales de los campos seleccionados ({', '.join(campos_sel)}) integrados en el Plan de Estudio 2022.")
    
    with col_pda2:
        st.markdown("**Problemática del Programa Analítico (Durango):**")
        st.markdown("""
        * **Comprensión lectora y fluidez:** Dificultad para inferir ideas centrales en textos argumentativos y científicos.
        * **Cálculo mental contextualizado:** Manejo de fracciones, decimales y situaciones financieras del entorno.
        * **Convivencia y vida saludable:** Fomento de la mediación dialógica y estilos de vida activos.
        """)

# Selector de origen de la información para la planeación estricta
modo_estricto_fuente = st.radio(
    "🔒 Selecciona la base estricta para la planeación:",
    [
        "Solo Programa Analítico (Focalizado en la escuela y contexto local)",
        "Solo Programa Sintético (Contenidos y PDA nacionales de la SEP)",
        "Ambos (Integración del Programa Analítico y Sintético)"
    ]
)

# Parámetros adicionales de proyecto y directrices docentes
col_extra1, col_extra2 = st.columns(2)
with col_extra1:
    proyecto_ltg = st.text_input(
        "Proyecto vinculado de los LTG (CONALITEG):",
        value="La cápsula del tiempo",
        help="Título del proyecto integrado en los Libros de Texto Gratuitos (Aula, Escolares o Comunitarios)."
    )
with col_extra2:
    notas_docente = st.text_input(
        "Directriz específica de la Maestra / Adecuación DUA particular:",
        value="Priorizar actividades visuales y dinámicas kinestésicas por equipos para los 26 alumnos.",
        help="Puedes indicar consignas especiales, materiales del aula o énfasis para la sesión."
    )

# Función para generar el documento de Word según la fuente elegida
def generar_documento_estricto(campo: str, proyecto: str, periodo: str, fuente: str) -> BytesIO:
    from docx import Document
    doc = Document()
    
    # Encabezado institucional fijo (Programa Analítico actualizador)
    doc.add_heading("ESCUELA PRIMARIA “REVOLUCIÓN SOCIAL DE 1910”", level=1)
    doc.add_paragraph("CCT: 10EPR0361N | Zona: 49 | Sector: 02\nGrado: 6° Grupo “A” | Maestra: Aday Domínguez Domínguez")
    doc.add_paragraph(f"📌 [MODO ESTRICTO ACTIVO • Base seleccionada: {fuente}]")
    doc.add_paragraph("---")
    
    # Datos generales
    doc.add_heading(f"Campo Formativo: {campo}", level=2)
    doc.add_paragraph(f"Proyecto Oficial vinculado (CONALITEG): {proyecto}")
    doc.add_paragraph(f"Temporalidad: {periodo}")
    
    # Desarrollo según la fuente seleccionada sin alteraciones
    if "Solo Programa Analítico" in fuente:
        doc.add_heading("1. Diagnóstico, Problemática Local y Contextualización", level=3)
        doc.add_paragraph("• Basado estrictamente en el Programa Analítico de la escuela (Dificultades lectoras, ortografía, fluidez y asuntos comunitarios de Durango).")
        doc.add_heading("2. Secuencia Didáctica basada en el Programa Analítico", level=3)
        doc.add_paragraph("• Respeto absoluto a la dosificación y contenidos locales registrados para las semanas seleccionadas.")
        
    elif "Solo Programa Sintético" in fuente:
        doc.add_heading("1. Contenidos y PDA Oficiales (Programa Sintético Fase 5)", level=3)
        doc.add_paragraph("• Extracción literal de los Procesos de Desarrollo de Aprendizaje (PDA) de la SEP sin modificaciones de contexto.")
        doc.add_heading("2. Secuencia Didáctica Nacional", level=3)
        doc.add_paragraph("• Abordaje metodológico general de los Libros de Texto Gratuito.")
        
    else: # Ambos
        doc.add_heading("1. Integración Curricular (Programa Sintético + Programa Analítico)", level=3)
        doc.add_paragraph("• Fusión rigurosa: Se cruzan los PDA oficiales nacionales con las problemáticas contextualizadas de la escuela primaria.")
        doc.add_heading("2. Secuencia Didáctica Cruzada", level=3)
        doc.add_paragraph("• Actividades alineadas a los saberes de la comunidad y los ejes articuladores de la Nueva Escuela Mexicana.")

    doc.add_heading("3. Evaluación Formativa", level=3)
    doc.add_paragraph("• Valoración continua mediante rúbricas y seguimiento estricto del proceso de aprendizaje.")

    doc.add_paragraph("\n")
    doc.add_paragraph("________________________________________          ________________________________________\n"
                      "     Maestra Aday Domínguez Domínguez                   Guillermo Gerardo Borjas Díaz     \n"
                      "              Docente Titular                                  Director Escolar           ")
    
    # Guardar en memoria (BytesIO)
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

# Alias para compatibilidad de interfaces
generar_documento_word = lambda c, p, per, est=True: generar_documento_estricto(c, p, per, modo_estricto_fuente)

# Expansor con descarga inmediata en Word sin requerir generación previa de IA
with st.expander("📥 Descarga Inmediata de Plantilla en Word (.docx) [Sin esperar IA]", expanded=False):
    periodo_val_rapido = f"Semana {semana_sel} de 37" if modo_tiempo == "📅 Semana Completa SEP" else f"Semana de {fecha_ini.strftime('%d/%m/%Y')}"
    docx_buf_rapido = generar_documento_estricto(", ".join(campos_sel), proyecto_ltg, periodo_val_rapido, modo_estricto_fuente)
    slug_r = "_".join(c.split()[0] for c in campos_sel)
    st.download_button(
        label="📥 Descargar Planeación Estricta en Word (.docx)",
        data=docx_buf_rapido,
        file_name=f"Planeacion_{slug_r}_{periodo_val_rapido.split()[0]}_{semana_sel}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="btn_descarga_word_rapida",
        use_container_width=True
    )
    st.caption("✓ Descarga instantánea generada directamente en memoria (BytesIO) lista para editar.")


# ==========================================
# 3. BOTÓN DE GENERACIÓN INTELIGENTE CON IA Y LIBROS CONALITEG
# ==========================================
st.markdown("---")
st.markdown("### 3. ✨ Generación Didáctica Automatizada con IA")

generar_clicked = st.button("✨ Generar Planeación Didáctica con IA", type="primary", use_container_width=True)

if generar_clicked:
    with st.spinner("Conectando con el Programa Analítico, Sintético y Catálogo CONALITEG en vivo..."):
        # Actualización de la ficha técnica institucional
        datos_generacion = dict(st.session_state["datos_escuela"])
        datos_generacion["periodo"] = f"Semana {semana_sel} de 37" if modo_tiempo == "📅 Semana Completa SEP" else f"Semana de {fecha_ini.strftime('%d/%m/%Y')}"
        datos_generacion["semana"] = semana_sel
        datos_generacion["semana_seleccionada"] = semana_sel
        datos_generacion["dias_seleccionados"] = dias_habiles

        # Extracción o integración de PDA para los campos seleccionados
        pda_list = []
        if CONTENIDOS_PDA_POR_GRADO and "6° de Primaria" in CONTENIDOS_PDA_POR_GRADO:
            for c_f in campos_sel:
                p_items = CONTENIDOS_PDA_POR_GRADO["6° de Primaria"].get(c_f, [])
                if p_items:
                    pda_list.extend(p_items[:2])
        if not pda_list:
            pda_list = [{"campo": c_f, "contenido": f"Contenido representativo de {c_f}", "pda": "Aplica procesos de indagación y reflexión crítica en su contexto comunitario."} for c_f in campos_sel]

        plan_resultado = ""
        prompt_utilizado = ""

        # Consigna de rigor técnico según la fuente estricta seleccionada
        directriz_final = notas_docente
        if "Solo Programa Analítico" in modo_estricto_fuente:
            directriz_final = (directriz_final + " | " if directriz_final else "") + "MODO ESTRICTO (SOLO PROGRAMA ANALÍTICO): Focalizar la planeación exclusivamente en las problemáticas educativas del aula y el contexto comunitario de Durango del Programa Analítico escolar."
        elif "Solo Programa Sintético" in modo_estricto_fuente:
            directriz_final = (directriz_final + " | " if directriz_final else "") + "MODO ESTRICTO (SOLO PROGRAMA SINTÉTICO): Mantener textualmente y sin alterar los Contenidos y PDA oficiales de la Fase 5 del Programa Sintético Nacional de la SEP."
        else: # Ambos
            directriz_final = (directriz_final + " | " if directriz_final else "") + "MODO ESTRICTO (INTEGRACIÓN): Articular de manera cruzada los PDA del Programa Sintético nacional con las problemáticas y el diagnóstico del Programa Analítico institucional."

        # Intento con motor Gemini en vivo si hay API Key disponible
        if api_key_activa and generate_planeacion:
            try:
                plan_resultado, prompt_utilizado = generate_planeacion(
                    datos_escuela=datos_generacion,
                    campos_formativos=campos_sel,
                    metodologia=metodologias_sel,
                    ejes_articuladores=ejes_seleccionados,
                    contenidos_pda=pda_list,
                    directrices_docente=directriz_final,
                    libros_seleccionados=libros_seleccionados,
                    dias_seleccionados=dias_habiles,
                    semana_seleccionada=semana_sel,
                    fase_seleccionada="Fase 5",
                    api_key=api_key_activa,
                    modelo=modelo_seleccionado
                )
            except Exception as e_gemini:
                st.warning(f"⚠️ Nota de conexión con Gemini ({str(e_gemini)}). Activando generador curricular oficial de respaldo...")
                if generate_sample_fallback:
                    plan_resultado = generate_sample_fallback(
                        datos_escuela=datos_generacion,
                        campos_formativos=campos_sel,
                        metodologia=metodologias_sel,
                        ejes=ejes_seleccionados,
                        dias_seleccionados=dias_habiles,
                        semana_seleccionada=semana_sel,
                        directrices_docente=directriz_final
                    )
        elif generate_sample_fallback:
            # Modo Curricular Base NEM de alta fidelidad
            plan_resultado = generate_sample_fallback(
                datos_escuela=datos_generacion,
                campos_formativos=campos_sel,
                metodologia=metodologias_sel,
                ejes=ejes_seleccionados,
                dias_seleccionados=dias_habiles,
                semana_seleccionada=semana_sel,
                directrices_docente=directriz_final
            )
        else:
            plan_resultado = f"Planeación Didáctica generada para {', '.join(campos_sel)} - Semana {semana_sel}."

        # Guardar en estado de sesión
        st.session_state["plan_generado"] = plan_resultado
        if parse_plan_sections:
            st.session_state["parsed_plan"] = parse_plan_sections(plan_resultado)

    st.success("✓ Planeación generada exitosamente con enfoque DUA y metodología sociocrítica.")


# ==========================================
# VISTA PREVIA ESTRUCTURADA Y ACCIONES DE DESCARGA
# ==========================================
if st.session_state.get("plan_generado"):
    plan_texto = st.session_state["plan_generado"]
    parsed = st.session_state.get("parsed_plan") or {}

    campos_titulo = ", ".join(campos_sel)
    metodologias_titulo = ", ".join(metodologias_sel)

    # Vista previa estructurada solicitada en el esquema base
    st.markdown(f"#### Planeación Didáctica - {campos_titulo}")
    st.markdown(f"""
    * **Metodología(s):** {metodologias_titulo}
    * **Inicio (Rutina Matutina):** Dictado con retos ortográficos y cálculo mental.
    * **Desarrollo (Secuencia Didáctica):** Actividades dinámicas (estilo kinestésico y visual para los 26 alumnos).
    * **Cierre y Evaluación Formativa:** Socialización comunitaria y rúbrica analítica.
    """)

    # Pestañas interactivas para revisión profunda
    tab_previa, tab_completa, tab_descargas = st.tabs([
        "📋 Vista Didáctica Detallada",
        "📄 Documento Completo NEM (Markdown)",
        "📥 Descargas Oficiales (.docx, .pdf)"
    ])

    with tab_previa:
        col_res1, col_res2 = st.columns([1, 1])
        with col_res1:
            st.markdown(f"""
            <div class="nem-section-card">
                <h4 style="color: #6D28D9; margin-top: 0;">🎯 Dosificador y Metodología</h4>
                <p><strong>Proyecto:</strong> {parsed.get('nombre_proyecto') or f'Proyecto de {campos_titulo}'}</p>
                <p><strong>Metodología(s):</strong> {metodologias_titulo}</p>
                <p><strong>Escenario:</strong> {parsed.get('escenario') or 'Aula / Comunitario'}</p>
                <p><strong>Libros LTG:</strong> {', '.join(libros_seleccionados) if libros_seleccionados else 'Libros de Texto Fase 5'}</p>
            </div>
            """, unsafe_allow_html=True)
        with col_res2:
            st.markdown(f"""
            <div class="nem-section-card">
                <h4 style="color: #6D28D9; margin-top: 0;">🧠 Inclusión y DUA (26 Alumnos)</h4>
                <p><strong>Estilos:</strong> Kinestésico y Visual</p>
                <p><strong>Ajustes Razonables:</strong> {parsed.get('adecuaciones') or 'Pistas visuales, esquemas gráficos y estaciones de aprendizaje activo en equipos.'}</p>
                <p><strong>Evaluación Formativa:</strong> Rúbrica analítica por niveles de desempeño.</p>
            </div>
            """, unsafe_allow_html=True)

        # Muestra de Rutinas Matutinas
        st.markdown("#### 🧠 Rutina Matutina Diaria (Dictado, Cálculo y Problema Razonado)")
        rutinas_dias = parsed.get("rutinas_por_dia", {})
        if rutinas_dias:
            for dia, contenido_dia in rutinas_dias.items():
                if dia in dias_habiles:
                    with st.expander(f"📌 {dia} - Rutina Matutina", expanded=(dia == dias_habiles[0])):
                        st.markdown(contenido_dia)
        else:
            st.info("La rutina matutina incluye ejercicios diarios de dictado ortográfico y retos de cálculo mental.")

        # Muestra de Secuencia Didáctica Diaria
        st.markdown("#### 🚀 Secuencia Didáctica por Sesiones")
        sesiones_dias = parsed.get("sesiones_por_dia", {})
        if sesiones_dias:
            for dia, contenido_sesion in sesiones_dias.items():
                if dia in dias_habiles:
                    with st.expander(f"📅 {dia} - Secuencia de Actividades (Inicio, Desarrollo y Cierre)", expanded=(dia == dias_habiles[0])):
                        st.markdown(contenido_sesion)
        else:
            st.markdown(plan_texto[:1500] + "...")

    with tab_completa:
        st.markdown("### 📝 Texto Completo de la Planeación (Formato NEM)")
        st.text_area(
            "Texto Markdown Oficial:",
            value=plan_resultado if 'plan_resultado' in locals() and plan_resultado else plan_texto,
            height=400
        )

    with tab_descargas:
        st.markdown("### 📥 Descargas en Formatos Oficiales SEP")
        st.markdown("Generación con encabezados institucionales, firmas de la **Mtra. Aday Domínguez** y el **Director Guillermo Borjas**, y estructura de tablas oficiales de la NEM.")

        col_d_docx, col_d_pdf, col_d_guardar = st.columns(3)
        slug_campos = "_".join(c.split()[0] for c in campos_sel)

        # 1. Descarga Word (.docx)
        with col_d_docx:
            if build_docx_planeacion:
                try:
                    docx_stream = build_docx_planeacion(st.session_state["datos_escuela"], plan_texto)
                    st.download_button(
                        label="📥 Descargar Word (.docx)",
                        data=docx_stream.getvalue(),
                        file_name=f"Planeacion_6to_{slug_campos}_Semana{semana_sel}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                except Exception as e_docx:
                    st.error(f"Error generando .docx: {e_docx}")
            else:
                st.info("Generador .docx no disponible")

        # 2. Descarga PDF (.pdf)
        with col_d_pdf:
            if build_pdf_planeacion:
                try:
                    pdf_stream = build_pdf_planeacion(st.session_state["datos_escuela"], plan_texto)
                    st.download_button(
                        label="📄 Descargar PDF (.pdf)",
                        data=pdf_stream.getvalue(),
                        file_name=f"Planeacion_6to_{slug_campos}_Semana{semana_sel}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e_pdf:
                    st.error(f"Error generando .pdf: {e_pdf}")
            else:
                st.info("Generador .pdf no disponible")

        # 3. Guardar en Base de Datos Local
        with col_d_guardar:
            if guardar_planeacion:
                if st.button("💾 Guardar en Base de Datos", use_container_width=True):
                    try:
                        record_data = {
                            "datos_escuela": st.session_state["datos_escuela"],
                            "semana": semana_sel,
                            "campo": campos_titulo,
                            "metodologia": metodologias_sel,
                            "plan_generado": plan_texto,
                            "periodo": f"Semana {semana_sel} de 37",
                            "grado": "6° de Primaria",
                            "grupo": "A"
                        }
                        plan_id = guardar_planeacion(
                            username="Mtra. Aday Domínguez Domínguez",
                            data=record_data,
                            es_autoguardado=False,
                            version_nombre=f"Semana {semana_sel} - {slug_campos}"
                        )
                        st.success(f"✓ Guardado con éxito en la base de datos institucional (ID: {plan_id})")
                    except Exception as e_save:
                        st.error(f"Error al guardar: {e_save}")

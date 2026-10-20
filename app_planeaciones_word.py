# ==========================================
# GENERADOR RÁPIDO DE PLANEACIONES EN WORD (.DOCX) EN MEMORIA
# Escuela Primaria “Revolución Social de 1910” (C.C.T. 10EPR0361N)
# Grado: 6° Grupo “A” • Fase 5 • Ciclo Escolar 2026-2027
# ==========================================
import streamlit as st
import datetime
from io import BytesIO
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(
    page_title="Generador de Planeaciones NEM en Word",
    page_icon="📝",
    layout="wide"
)

# Estilos visuales complementarios
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Outfit:wght@500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif !important;
    }
    .word-card {
        background: linear-gradient(135deg, #FAF5FF 0%, #FFFFFF 100%);
        border: 1.5px solid #DDD6FE;
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 4px 16px rgba(124, 58, 237, 0.06);
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="word-card">
    <h1 style="color: #4C1D95; margin: 0 0 0.3rem 0; font-size: 2rem;">
        📚 Sistema de Planeaciones Escolares - Fase 5 (6° Grado)
    </h1>
    <h3 style="color: #6D28D9; margin: 0; font-weight: 600; font-size: 1.15rem;">
        Escuela Primaria 'Revolución Social de 1910' (CCT: 10EPR0361N)
    </h3>
    <p style="color: #7C3AED; margin: 0.3rem 0 0 0; font-weight: 500;">
        Generación instantánea en memoria de documentos oficiales en Microsoft Word (.docx) • Ciclo Escolar 2026-2027
    </p>
</div>
""", unsafe_allow_html=True)

col_izq, col_der = st.columns([1, 1.2])

with col_izq:
    st.markdown("### 1. 🎯 Parámetros de la Planeación")
    
    campo_form = st.selectbox("Campo Formativo:", [
        "Lenguajes", 
        "Saberes y Pensamiento Científico", 
        "Ética, Naturaleza y Sociedades", 
        "De lo Humano y lo Comunitario"
    ])

    # Selector de origen de la información para la planeación estricta
    modo_estricto_fuente = st.radio(
        "🔒 Selecciona la base estricta para la planeación:",
        [
            "Solo Programa Analítico (Focalizado en la escuela y contexto local)",
            "Solo Programa Sintético (Contenidos y PDA nacionales de la SEP)",
            "Ambos (Integración del Programa Analítico y Sintético)"
        ]
    )

    proyecto_ltg = st.text_input(
        "Proyecto vinculado de los LTG (CONALITEG):", 
        value="La cápsula del tiempo",
        help="Título del proyecto integrado en los Libros de Texto Gratuitos (Aula, Escolares o Comunitarios)."
    )

    periodo_val = st.text_input(
        "Temporalidad (Ej. Semanas 8 y 9 - Octubre):", 
        value="Semanas 8 y 9 de Octubre (19 a 23 y 26 a 30)"
    )

    st.markdown("---")
    st.markdown("### 🏛️ Datos Institucionales Oficiales")
    st.info("""
    * **Escuela:** Primaria “Revolución Social de 1910”
    * **C.C.T.:** `10EPR0361N` | **Zona:** 49 | **Sector:** 02 (Durango)
    * **Docente Titular:** Maestra Aday Domínguez Domínguez
    * **Director:** Guillermo Gerardo Borjas Díaz
    * **Matrícula:** 26 alumnos (Estilos Kinestésico y Visual • DUA)
    """)

# 2. Función para generar un documento de Word (.docx) en memoria según la fuente elegida
def generar_documento_estricto(campo: str, proyecto: str, periodo: str, fuente: str) -> BytesIO:
    doc = Document()
    
    # Configuración de márgenes estándar de 1 pulgada (2.54 cm)
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)
    
    # 1. Encabezado institucional fijo (Programa Analítico actualizador)
    h1 = doc.add_heading("ESCUELA PRIMARIA “REVOLUCIÓN SOCIAL DE 1910”", level=1)
    h1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if h1.runs:
        h1.runs[0].font.name = "Calibri"
        h1.runs[0].font.size = Pt(15)
        h1.runs[0].font.bold = True
        h1.runs[0].font.color.rgb = RGBColor(76, 29, 149) # Púrpura institucional
    
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run(
        "C.C.T. 10EPR0361N | Zona Escolar: 49 | Sector: 02 | Turno: Matutino\n"
        "Grado: 6° Grupo “A” (Fase 5) | Durango, Dgo.\n"
        "Docente Titular: Maestra Aday Domínguez Domínguez | Director: Guillermo Gerardo Borjas Díaz"
    )
    run_sub.font.name = "Calibri"
    run_sub.font.size = Pt(9.5)
    run_sub.font.color.rgb = RGBColor(107, 114, 128)

    p_est = doc.add_paragraph()
    p_est.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_est = p_est.add_run(f"📌 [MODO ESTRICTO ACTIVO • Base seleccionada: {fuente}]")
    r_est.font.name = "Calibri"
    r_est.font.size = Pt(10)
    r_est.font.bold = True
    r_est.font.color.rgb = RGBColor(185, 28, 28) # Rojo oscuro institucional

    p_div = doc.add_paragraph("────────────────────────────────────────────────────────────────────────")
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if p_div.runs:
        p_div.runs[0].font.color.rgb = RGBColor(221, 214, 254)
    
    # 2. Datos generales de la planeación didáctica
    h2 = doc.add_heading(f"Campo Formativo: {campo}", level=2)
    if h2.runs:
        h2.runs[0].font.name = "Calibri"
        h2.runs[0].font.size = Pt(13)
        h2.runs[0].font.bold = True
        h2.runs[0].font.color.rgb = RGBColor(109, 40, 217)

    p_meta = doc.add_paragraph()
    r_proy = p_meta.add_run(f"• Proyecto Oficial vinculado (CONALITEG): ")
    r_proy.bold = True
    p_meta.add_run(f"{proyecto}\n")
    
    r_per = p_meta.add_run(f"• Temporalidad: ")
    r_per.bold = True
    p_meta.add_run(f"{periodo}\n")

    r_met = p_meta.add_run(f"• Enfoque Pedagógico: ")
    r_met.bold = True
    p_meta.add_run("Metodologías Sociocríticas de la NEM y Diseño Universal para el Aprendizaje (DUA)\n")

    r_alu = p_meta.add_run(f"• Matrícula y Estilos: ")
    r_alu.bold = True
    p_meta.add_run("26 alumnos (Estilos predominantes: Kinestésico y Visual)")

    # 3. Desarrollo según la fuente seleccionada
    if "Solo Programa Analítico" in fuente:
        h3_1 = doc.add_heading("1. Diagnóstico, Problemática Local y Contextualización", level=3)
        if h3_1.runs:
            h3_1.runs[0].font.name = "Calibri"
            h3_1.runs[0].font.size = Pt(11.5)
            h3_1.runs[0].font.bold = True
            h3_1.runs[0].font.color.rgb = RGBColor(91, 33, 182)
        doc.add_paragraph("• Basado estrictamente en el Programa Analítico de la escuela (Dificultades lectoras, ortografía, fluidez y asuntos comunitarios de Durango).")

        h3_2 = doc.add_heading("2. Secuencia Didáctica basada en el Programa Analítico", level=3)
        if h3_2.runs:
            h3_2.runs[0].font.name = "Calibri"
            h3_2.runs[0].font.size = Pt(11.5)
            h3_2.runs[0].font.bold = True
            h3_2.runs[0].font.color.rgb = RGBColor(91, 33, 182)
        doc.add_paragraph("• Respeto absoluto a la dosificación y contenidos locales registrados para las semanas seleccionadas.")

    elif "Solo Programa Sintético" in fuente:
        h3_1 = doc.add_heading("1. Contenidos y PDA Oficiales (Programa Sintético Fase 5)", level=3)
        if h3_1.runs:
            h3_1.runs[0].font.name = "Calibri"
            h3_1.runs[0].font.size = Pt(11.5)
            h3_1.runs[0].font.bold = True
            h3_1.runs[0].font.color.rgb = RGBColor(91, 33, 182)
        doc.add_paragraph("• Extracción literal de los Procesos de Desarrollo de Aprendizaje (PDA) de la SEP sin modificaciones de contexto.")

        h3_2 = doc.add_heading("2. Secuencia Didáctica Nacional", level=3)
        if h3_2.runs:
            h3_2.runs[0].font.name = "Calibri"
            h3_2.runs[0].font.size = Pt(11.5)
            h3_2.runs[0].font.bold = True
            h3_2.runs[0].font.color.rgb = RGBColor(91, 33, 182)
        doc.add_paragraph("• Abordaje metodológico general de los Libros de Texto Gratuito.")

    else: # Ambos
        h3_1 = doc.add_heading("1. Integración Curricular (Programa Sintético + Programa Analítico)", level=3)
        if h3_1.runs:
            h3_1.runs[0].font.name = "Calibri"
            h3_1.runs[0].font.size = Pt(11.5)
            h3_1.runs[0].font.bold = True
            h3_1.runs[0].font.color.rgb = RGBColor(91, 33, 182)
        doc.add_paragraph("• Fusión rigurosa: Se cruzan los PDA oficiales nacionales con las problemáticas contextualizadas de la escuela primaria.")

        h3_2 = doc.add_heading("2. Secuencia Didáctica Cruzada", level=3)
        if h3_2.runs:
            h3_2.runs[0].font.name = "Calibri"
            h3_2.runs[0].font.size = Pt(11.5)
            h3_2.runs[0].font.bold = True
            h3_2.runs[0].font.color.rgb = RGBColor(91, 33, 182)
        doc.add_paragraph("• Actividades alineadas a los saberes de la comunidad y los ejes articuladores de la Nueva Escuela Mexicana.")

    # 4. Sección de Cierre y Evaluación Formativa
    h3_3 = doc.add_heading("3. Evaluación Formativa", level=3)
    if h3_3.runs:
        h3_3.runs[0].font.name = "Calibri"
        h3_3.runs[0].font.size = Pt(11.5)
        h3_3.runs[0].font.bold = True
        h3_3.runs[0].font.color.rgb = RGBColor(91, 33, 182)

    doc.add_paragraph("• Valoración continua mediante rúbricas y seguimiento estricto del proceso de aprendizaje.")

    # 5. Firmas institucionales reglamentarias
    doc.add_paragraph("\n")
    p_firmas = doc.add_paragraph()
    p_firmas.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_f = p_firmas.add_run(
        "________________________________________          ________________________________________\n"
        "     Maestra Aday Domínguez Domínguez                   Guillermo Gerardo Borjas Díaz     \n"
        "              Docente Titular                                  Director Escolar           "
    )
    r_f.font.name = "Calibri"
    r_f.font.size = Pt(9.5)
    r_f.font.color.rgb = RGBColor(55, 65, 81)

    # Guardar en memoria (BytesIO)
    file_stream = BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    return file_stream

with col_der:
    st.markdown("### 2. 📄 Vista Previa y Descarga Inmediata")
    
    # Badge de modo estricto con fuente activa
    fuente_corta = "Analítico" if "Analítico" in modo_estricto_fuente and "Sintético" not in modo_estricto_fuente else ("Sintético" if "Sintético" in modo_estricto_fuente and "Analítico" not in modo_estricto_fuente else "Analítico + Sintético")
    st.markdown(f"""
    <div style="background: #FEF2F2; border: 1.5px solid #FCA5A5; color: #991B1B; padding: 0.7rem 1.1rem; border-radius: 10px; margin-bottom: 1rem; font-size: 0.88rem; font-weight: 600;">
        🔒 MODO ESTRICTO ACTIVO • Base: <b>{modo_estricto_fuente.split('(')[0].strip()}</b>
    </div>
    """, unsafe_allow_html=True)

    # Vista previa didáctica en pantalla
    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1.5px solid #7C3AED; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.04);">
        <h4 style="color: #6D28D9; margin-top: 0;">📋 Resumen de la Estructura en Word:</h4>
        <p><strong>• Encabezado:</strong> Escuela Primaria “Revolución Social de 1910” (C.C.T. 10EPR0361N)</p>
        <p><strong>• Campo Formativo:</strong> {campo_form}</p>
        <p><strong>• Proyecto Oficial Vinculado:</strong> {proyecto_ltg}</p>
        <p><strong>• Temporalidad:</strong> {periodo_val}</p>
        <p><strong>• Base Curricular:</strong> 🔒 {fuente_corta}</p>
        <hr style="border: none; border-top: 1px dashed #DDD6FE; margin: 0.8rem 0;">
        <p><strong>1. Inicio:</strong> {'Diagnóstico, Problemática Local y Contextualización' if 'Solo Programa Analítico' in modo_estricto_fuente else ('Contenidos y PDA Oficiales (Programa Sintético Fase 5)' if 'Solo Programa Sintético' in modo_estricto_fuente else 'Integración Curricular (Programa Sintético + Programa Analítico)')}.</p>
        <p><strong>2. Desarrollo:</strong> {'Secuencia Didáctica basada en el Programa Analítico' if 'Solo Programa Analítico' in modo_estricto_fuente else ('Secuencia Didáctica Nacional' if 'Solo Programa Sintético' in modo_estricto_fuente else 'Secuencia Didáctica Cruzada')}.</p>
        <p><strong>3. Cierre:</strong> Evaluación formativa continua mediante rúbricas y seguimiento estricto del proceso de aprendizaje.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Generación del archivo en memoria y botón de descarga
    nombre_archivo = f"Planeacion_Estricta_{campo_form.replace(' ', '_')}.docx"
    docx_buffer = generar_documento_estricto(campo_form, proyecto_ltg, periodo_val, modo_estricto_fuente)

    st.download_button(
        label="📥 Descargar Planeación Estricta en Word (.docx)",
        data=docx_buffer,
        file_name=nombre_archivo,
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
        use_container_width=True
    )
    
    st.success("✓ Archivo .docx generado en búfer de memoria (BytesIO), listo para descarga instantánea sin almacenamiento en disco.")

from __future__ import annotations

"""
Generador de documentos oficiales en formato Microsoft Word (.docx)
para las planeaciones escolares de la Primaria Revolución Social 1910.
Adopta estrictamente el diseño, tipografía y la paleta de colores estilo Gemini:
- Tipografía global oficial SEP ('Arial', 10 pt)
- Manipulación XML (w:shd) con sintaxis: <w:shd w:val="clear" w:color="auto" w:fill="HEX_COLOR"/>
- Encabezados principales (Días de la semana, CAMPO FORMATIVO, etc.): Fondo Morado Intenso (#7209B7), texto blanco, negrita y centrado.
- Subencabezados o Secciones (Inicio, Desarrollo, Cierre, Dictado, Cálculo, etc.): Fondo Lavanda / Lila Suave (#F3E8FF), texto Morado Oscuro (#311B92), negrita.
- Celdas de contenido (texto de planeación, dictado, desarrollo): Fondo completamente Blanco (#FFFFFF), texto oscuro.
- Bordes de tabla finos en morado tenue (#D8B4FE) para diseño limpio y minimalista.
"""

import io
import re
import json
from typing import Dict, Any, List
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

try:
    from cuadernillo_kempis import (
        detectar_relevancia_kempis,
        obtener_anexos_kempis_para_docx,
        obtener_recursos_kempis_por_semana,
        obtener_proyecto_semana,
        CUADERNILLO_KEMPIS_DATA
    )
except ImportError:
    detectar_relevancia_kempis = lambda *args, **kwargs: False
    obtener_anexos_kempis_para_docx = lambda *args, **kwargs: []
    obtener_recursos_kempis_por_semana = lambda *args, **kwargs: None
    obtener_proyecto_semana = lambda *args, **kwargs: {}
    CUADERNILLO_KEMPIS_DATA = {}


# Paleta de Colores Estilo Gemini
COLOR_MORADO_INTENSO = RGBColor(114, 9, 183)    # #7209B7 (Encabezados principales)
COLOR_MORADO_OSCURO = RGBColor(49, 27, 146)     # #311B92 (Subencabezados / Secciones)
COLOR_TEXTO_OSCURO = RGBColor(30, 41, 59)       # #1E293B (Celdas de contenido)
COLOR_BLANCO = RGBColor(255, 255, 255)           # #FFFFFF

HEX_MORADO_INTENSO = "7209B7"
HEX_MORADO_OSCURO = "311B92"
HEX_LILA_SUAVE = "F3E8FF"
HEX_BLANCO = "FFFFFF"
HEX_BORDE_TENUE = "D8B4FE"

DIAS_FECHAS_OFICIALES = {
    "Lunes": "LUNES 02 DE FEBRERO DE 2026",
    "Martes": "MARTES 03 DE FEBRERO DE 2026",
    "Miércoles": "MIÉRCOLES 04 DE FEBRERO DE 2026",
    "Jueves": "JUEVES 05 DE FEBRERO DE 2026",
    "Viernes": "VIERNES 06 DE FEBRERO DE 2026"
}


def extract_day_from_text(text: str) -> str:
    """Identifica el día de la semana normalizando acentos y variantes."""
    if not text:
        return ""
    t = text.lower()
    if re.search(r'\blunes\b', t):
        return "Lunes"
    if re.search(r'\bmartes\b', t):
        return "Martes"
    if re.search(r'\bmi[eé]rcoles\b', t):
        return "Miércoles"
    if re.search(r'\bjueves\b', t):
        return "Jueves"
    if re.search(r'\bviernes\b', t):
        return "Viernes"
    return ""


def set_cell_background(cell, hex_color: str):
    """
    Establece el color de fondo de una celda en formato XML inyectando
    el elemento <w:shd w:val="clear" w:color="auto" w:fill="HEX_COLOR"/> en tcPr.
    """
    tcPr = cell._tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag.endswith('shd'):
            tcPr.remove(child)
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{hex_color}"/>')
    tcPr.append(shading_elm)


def set_table_borders(table, color="D8B4FE", sz="4", val="single"):
    """
    Configura bordes finos en un color gris claro o morado tenue (D8B4FE)
    para que el diseño de las tablas luzca limpio, minimalista y elegante.
    """
    tblPr = table._tbl.tblPr
    for child in list(tblPr):
        if child.tag.endswith('tblBorders'):
            tblPr.remove(child)
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    """Ajusta los márgenes interiores (padding) de una celda."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for margin_name, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{margin_name}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def parse_plan_sections(plan_text: str) -> Dict[str, Any]:
    """Extrae las secciones pedagógicas del texto en Markdown para rellenar tablas (Machote 6° Grado - Estilo Profa. Kempis)."""
    data = {
        "nombre_proyecto": "Voces Comunitarias en Acción: Lectura, Ortografía y Tecnologías para el Bienestar",
        "campo_formativo": "Lenguajes, Saberes y Pensamiento Científico, Ética, Naturaleza y Sociedades, De lo Humano y lo Comunitario",
        "duracion": "Semanas 6 y 7 (del 5 al 16 de octubre del ciclo 2026-2027)",
        "proposito": "Que las y los 26 alumnos de 6° Grado Grupo “A” investiguen y elaboren textos literarios y argumentativos, analicen sellos de advertencia NOM-051 y conversiones de múltiplos del gramo, y apliquen mecanismos pacíficos de convivencia, fortaleciendo la comprensión lectora, velocidad lectora, ortografía y resolución de problemas comunitarios.",
        "metodologia": "Aprendizaje Basado en Proyectos Comunitarios (ABPC)",
        "escenario": "Proyectos Comunitarios (págs. 20-35), Proyectos de Aula (págs. 82-95) y Proyectos Escolares (págs. 80-92)",
        "libros_texto": "Proyectos Comunitarios (6° grado), Nuestros Saberes (6° grado), Proyectos de Aula (6° grado), Múltiples Lenguajes (6° grado)",
        "problematica": "Dificultades en comprensión lectora inferencial, fluidez y velocidad lectora, ortografía en redacción autónoma y cálculo mental contextualizado.",
        "ejes": "Inclusión, Pensamiento Crítico, Vida Saludable, Apropiación de las Culturas a través de la Lectura y la Escritura",
        "contenidos": "Análisis de textos literarios; alimentación saludable y sellos NOM-051; múltiplos del gramo; servicios públicos e IVA; cultura de paz.",
        "pda": "Lee y recrea cuentos y textos informativos; interpreta sellos en ultraprocesados; resuelve conversiones de gramos y porcentajes; aplica mediación dialógica.",
        "rutinas": [],
        "sesiones": [],
        "rutinas_por_dia": {},
        "sesiones_por_dia": {},
        "articulacion_filas": [],
        "evaluacion_filas": [],
        "adecuaciones": "Principio de Representación (Visual) con organizadores gráficos de alto contraste y Principio de Acción/Expresión (Kinestésico) con tarjetas ortográficas y material manipulativo para los 26 alumnos.",
        "observaciones": "Seguimiento diario en el diario de campo a la velocidad lectora (ppm) y precisión ortográfica, en cumplimiento con el Programa Analítico 2026-2027.",
        "raw_text": plan_text or ""
    }

    # Extraer campos de identificación curricular
    m_proj = re.search(r'Nombre (?:sugerido para el |del )?Proyecto[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_proj:
        data["nombre_proyecto"] = m_proj.group(1).replace('"', '').replace('*', '').strip()

    m_campo = re.search(r'Campo(?:s)? Formativo(?:s)?[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_campo:
        data["campo_formativo"] = m_campo.group(1).replace('*', '').strip()

    m_dur = re.search(r'Duración(?: Total)?(?: del Plan)?[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_dur:
        data["duracion"] = m_dur.group(1).replace('*', '').strip()

    m_prop = re.search(r'Propósito[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_prop:
        data["proposito"] = m_prop.group(1).replace('*', '').strip()

    m_met = re.search(r'Metodología(?:s)?(?: Sociocrítica(?:s)?)?[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_met:
        data["metodologia"] = m_met.group(1).replace('*', '').strip()

    m_esc = re.search(r'Escenario[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_esc:
        data["escenario"] = m_esc.group(1).replace('*', '').strip()

    m_ejes = re.search(r'Ejes Articuladores[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_ejes:
        data["ejes"] = m_ejes.group(1).replace('*', '').strip()

    m_lib = re.search(r'Libros de Texto(?: Gratuitos)?(?: \(LTG\))?[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_lib:
        data["libros_texto"] = m_lib.group(1).replace('*', '').strip()

    m_prob = re.search(r'Problemática(?: del Plan Analítico)?[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_prob:
        data["problematica"] = m_prob.group(1).replace('*', '').strip()

    m_cont = re.search(r'Contenido(?: Sintético)?[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_cont:
        data["contenidos"] = m_cont.group(1).replace('*', '').strip()

    m_pda = re.search(r'PDA[:\s\*]+([^\n]+)', plan_text, re.IGNORECASE)
    if m_pda:
        data["pda"] = m_pda.group(1).replace('*', '').strip()

    # 1. Extraer filas de la Tabla de Articulación Curricular (Sección II)
    sec_ii_match = re.search(r'# II\..*?(?=# III\.|\Z)', plan_text, re.DOTALL)
    if sec_ii_match:
        lineas_ii = sec_ii_match.group(0).split('\n')
        for l in lineas_ii:
            l_str = l.strip()
            if l_str.startswith('|') and l_str.endswith('|'):
                if set(l_str) <= {'|', '-', ' ', ':'}:
                    continue
                parts = [c.strip().replace('**', '') for c in l_str.strip('|').split('|')]
                if len(parts) >= 4 and not parts[0].lower().startswith('campo'):
                    data["articulacion_filas"].append(parts)

    # 2. Extraer actividades de inicio (rutina matutina) de la Sección III
    sec_iii_match = re.search(r'# III\..*?(?=# IV\.|\Z)', plan_text, re.DOTALL)
    sec_iii_text = sec_iii_match.group(0) if sec_iii_match else plan_text

    rutina_blocks = re.findall(r'(###[^\n]+)(.*?)(?=\n###|\n# |\Z)', sec_iii_text, re.DOTALL)
    for idx_r, (hdr, block) in enumerate(rutina_blocks, 1):
        num_m = re.search(r'Sesión (\d+)', hdr, re.IGNORECASE)
        num = num_m.group(1) if num_m else str(idx_r)
        day_detected = extract_day_from_text(hdr) or extract_day_from_text(block[:120])
        dictado_m = re.search(r'Dictado[:\s\*]+([^\n]+)', block, re.IGNORECASE)
        calculo_m = re.search(r'Cálculo Mental[:\s\*]+([^\n]+)', block, re.IGNORECASE)
        problema_m = re.search(r'Problema (?:Matemático )?Razonado[:\s\*]+([^\n]+)', block, re.IGNORECASE)

        r_item = {
            "sesion": num,
            "dia": day_detected,
            "dictado": dictado_m.group(1).replace('*', '').strip() if dictado_m else "Palabras clave del vocabulario científico y ortográfico.",
            "calculo": calculo_m.group(1).replace('*', '').strip() if calculo_m else "Operaciones combinadas de cálculo mental rápido.",
            "problema": problema_m.group(1).replace('*', '').strip() if problema_m else "Problema razonado de situaciones de la vida cotidiana."
        }
        data["rutinas"].append(r_item)
        if day_detected:
            data["rutinas_por_dia"][day_detected] = r_item

    # 3. Extraer secuencias didácticas de la Sección IV
    sec_iv_match = re.search(r'# IV\..*?(?=# V\.|\Z)', plan_text, re.DOTALL)
    sec_iv_text = sec_iv_match.group(0) if sec_iv_match else plan_text

    sesion_blocks = re.findall(r'(###[^\n]+)(.*?)(?=\n###|\n# |\Z)', sec_iv_text, re.DOTALL)
    for idx_s, (hdr, block) in enumerate(sesion_blocks, 1):
        num_m = re.search(r'Sesión (\d+)', hdr, re.IGNORECASE)
        num = num_m.group(1) if num_m else str(idx_s)
        day_detected = extract_day_from_text(hdr) or extract_day_from_text(block[:120])

        inicio_m = re.search(r'(?:^|\n)[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Inicio[^\:\n]*\:(.*?)(?=(?:\n[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Desarrollo)|\Z)', block, re.DOTALL | re.IGNORECASE)
        desarrollo_m = re.search(r'(?:^|\n)[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Desarrollo[^\:\n]*\:(.*?)(?=(?:\n[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Cierre)|\Z)', block, re.DOTALL | re.IGNORECASE)
        cierre_m = re.search(r'(?:^|\n)[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Cierre[^\:\n]*\:(.*?)(?=(?:\n[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Recursos|\n[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Evidencia)|\Z)', block, re.DOTALL | re.IGNORECASE)
        recursos_m = re.search(r'(?:^|\n)[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Recursos[^\:\n]*\:(.*?)(?=(?:\n[ \t]*(?:[-*][ \t]*)?(?:\*\*)?Evidencia)|\Z)', block, re.DOTALL | re.IGNORECASE)
        proposito_m = re.search(r'Propósito(?: de la sesión)?[:\s\*]+([^\n]+)', block, re.IGNORECASE)

        inicio_txt = inicio_m.group(1).replace('*', '').strip() if inicio_m else "[Redactar actividades de inicio aquí]"
        desarrollo_txt = desarrollo_m.group(1).replace('*', '').strip() if desarrollo_m else "[Redactar actividades de desarrollo aquí]"
        cierre_txt = cierre_m.group(1).replace('*', '').strip() if cierre_m else "[Redactar actividades de cierre aquí]"
        recursos_txt = recursos_m.group(1).replace('*', '').strip() if recursos_m else "Libro de texto gratuito, libreta de notas y materiales del aula."
        proposito_txt = proposito_m.group(1).replace('*', '').strip() if proposito_m else "Reconocer y aplicar saberes comunitarios."

        s_item = {
            "sesion": num,
            "dia": day_detected,
            "inicio": inicio_txt,
            "desarrollo": desarrollo_txt,
            "cierre": cierre_txt,
            "recursos": recursos_txt,
            "proposito": proposito_txt
        }
        data["sesiones"].append(s_item)
        if day_detected:
            data["sesiones_por_dia"][day_detected] = s_item

    # 4. Extraer filas de Rúbrica / Instrumento de Evaluación Formativa (Sección V)
    sec_v_match = re.search(r'# V\..*?(?=# VI\.|\Z)', plan_text, re.DOTALL)
    if sec_v_match:
        lineas_v = sec_v_match.group(0).split('\n')
        for l in lineas_v:
            l_str = l.strip()
            if l_str.startswith('|') and l_str.endswith('|'):
                if set(l_str) <= {'|', '-', ' ', ':'}:
                    continue
                parts = [c.strip().replace('**', '') for c in l_str.strip('|').split('|')]
                if len(parts) >= 4 and not any(parts[0].lower().startswith(x) for x in ['criterio', 'indicador']):
                    data["evaluacion_filas"].append(parts)

    # 5. Extraer Adecuaciones / Ajustes Razonables (Sección VI)
    sec_vi_match = re.search(r'# VI\..*?(?=# VII\.|\Z)', plan_text, re.DOTALL)
    if sec_vi_match:
        adecs = sec_vi_match.group(0).replace('# VI. AJUSTES RAZONABLES Y ATENCIÓN A LA DIVERSIDAD (BAP - DUA)', '').strip()
        if adecs and len(adecs) > 20:
            data["adecuaciones"] = adecs

    # 6. Extraer Observaciones Generales (Sección VII)
    sec_vii_match = re.search(r'# VII\..*?\Z', plan_text, re.DOTALL)
    if sec_vii_match:
        obs = sec_vii_match.group(0).replace('# VII. OBSERVACIONES GENERALES Y ESPACIO DE SEGUIMIENTO', '').strip()
        if obs and len(obs) > 20:
            data["observaciones"] = obs

    return data


def add_initial_signatures(doc, datos_escuela: Dict[str, Any]):
    """
    Distribución Inicial Paso 1:
    Genera las líneas de firmas centradas para el Director Escolar y Docente titular del Grupo.
    """
    docente = datos_escuela.get("docente", "Maestra Aday Domínguez Domínguez") if datos_escuela else "Maestra Aday Domínguez Domínguez"
    director = datos_escuela.get("director", "Guillermo Gerardo Borjas Díaz") if datos_escuela else "Guillermo Gerardo Borjas Díaz"

    table_firmas = doc.add_table(rows=2, cols=2)
    table_firmas.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_firmas.autofit = False
    set_table_borders(table_firmas, color=HEX_BORDE_TENUE)

    row0 = table_firmas.rows[0]
    row0.cells[0].text = "____________________________________________\nDOCENTE TITULAR DEL GRUPO"
    row0.cells[1].text = "____________________________________________\nDIRECTOR ESCOLAR"

    row1 = table_firmas.rows[1]
    row1.cells[0].text = f"Prof(a). {docente}"
    row1.cells[1].text = f"Prof. {director}"

    col_widths = [Inches(3.75), Inches(3.75)]
    for r in [row0, row1]:
        for c_idx, c in enumerate(r.cells):
            c.width = col_widths[c_idx]
            set_cell_background(c, HEX_BLANCO)
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_cell_margins(c, top=40, bottom=40, left=60, right=60)
            if c.paragraphs and c.paragraphs[0].runs:
                c.paragraphs[0].runs[0].font.name = 'Arial'
                c.paragraphs[0].runs[0].font.size = Pt(8.5)
                c.paragraphs[0].runs[0].font.bold = True
                c.paragraphs[0].runs[0].font.color.rgb = COLOR_MORADO_OSCURO

    doc.add_paragraph()  # Espacio


def add_institutional_header_table(doc, datos_escuela: Dict[str, Any]):
    """
    Distribución Inicial Paso 2:
    Crea la tabla de encabezado institucional con paleta estilo Gemini:
    Fondo Lavanda/Lila Suave (#F3E8FF) con texto Morado Oscuro (#311B92).
    """
    nombre_escuela = datos_escuela.get("nombre_escuela", "Escuela Primaria “Revolución Social de 1910”") if datos_escuela else "Escuela Primaria “Revolución Social de 1910”"
    cct = datos_escuela.get("cct", "10EPR0361N") if datos_escuela else "10EPR0361N"
    periodo = (datos_escuela.get("periodo") or f"Semana {datos_escuela.get('semana', 1)} de 37") if datos_escuela else "Semana 1 de 37"
    ciclo = datos_escuela.get("ciclo_escolar", "2026-2027") if datos_escuela else "2026-2027"
    grado = datos_escuela.get("grado", "6° de Primaria") if datos_escuela else "6° de Primaria"
    grupo = datos_escuela.get("grupo", "A") if datos_escuela else "A"
    fase = datos_escuela.get("fase", "Fase 5") if datos_escuela else "Fase 5"
    turno = datos_escuela.get("turno", "Matutino") if datos_escuela else "Matutino"
    zona_str = f"{datos_escuela.get('zona_escolar', 'Zona 49')} / {datos_escuela.get('sector', 'Sector 02')}" if datos_escuela else "Zona 49 / Sector 02"

    t_inst = doc.add_table(rows=2, cols=4)
    t_inst.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_inst.autofit = False
    set_table_borders(t_inst, color=HEX_BORDE_TENUE)

    meta_rows = [
        [("Nombre de la Escuela:", nombre_escuela.upper()), ("C.C.T.:", cct), ("Semana:", periodo), ("Ciclo Escolar:", ciclo)],
        [("Grado y Grupo:", f"{grado} '{grupo}'"), ("Fase Curricular:", fase), ("Turno:", turno), ("Zona Escolar:", zona_str)]
    ]
    for r_i, r_data in enumerate(meta_rows):
        for c_i, (lbl, val) in enumerate(r_data):
            cell = t_inst.rows[r_i].cells[c_i]
            cell.width = Inches(1.87)
            set_cell_background(cell, HEX_LILA_SUAVE if r_i == 0 else HEX_BLANCO)
            set_cell_margins(cell, top=45, bottom=45, left=55, right=55)
            cell.text = ""
            p = cell.paragraphs[0]
            r_lbl = p.add_run(f"{lbl}\n")
            r_lbl.font.name = 'Arial'
            r_lbl.font.size = Pt(7.5)
            r_lbl.font.bold = True
            r_lbl.font.color.rgb = COLOR_MORADO_OSCURO

            r_val = p.add_run(val)
            r_val.font.name = 'Arial'
            r_val.font.size = Pt(8)
            r_val.font.color.rgb = COLOR_TEXTO_OSCURO

    doc.add_paragraph()  # Espacio


def add_base_estricta_traceability_table(doc, datos_escuela=None):
    """
    Agrega la tabla institucional de Validación y Trazabilidad Curricular de Base Estricta (Tarea 93).
    Muestra el documento rector oficial, el estatus de Prioridad Absoluta y la validación técnica.
    """
    if not (datos_escuela and datos_escuela.get("modo_base_estricta") and datos_escuela.get("archivo_base_estricta")):
        return

    arch_nom = datos_escuela.get("archivo_base_estricta")
    tipo_arch = datos_escuela.get("tipo_base_estricta") or "Programa Analítico / Sintético Institucional"

    p_lbl = doc.add_paragraph()
    p_lbl.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_l = p_lbl.add_run("🔒 VALIDACIÓN Y TRAZABILIDAD CURRICULAR DE BASE ESTRICTA")
    r_l.font.name = 'Arial'
    r_l.font.bold = True
    r_l.font.size = Pt(9.5)
    r_l.font.color.rgb = COLOR_MORADO_INTENSO

    table = doc.add_table(rows=4, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table, color="10B981")

    col_widths = [Inches(2.4), Inches(5.1)]

    info_rows = [
        ("DOCUMENTO RECTOR VINCULADO:", f"{arch_nom} ({tipo_arch})"),
        ("ESTATUS DE PRIORIDAD ABSOLUTA:", "ACTIVA Y VINCULANTE (Supresión de plantillas genéricas externas)"),
        ("ALINEACIÓN CURRICULAR:", "100% de coherencia con los Contenidos, PDA y Problemáticas locales del documento cargado."),
        ("VALIDACIÓN PEDAGÓGICA INSTITUCIONAL:", "Revisado para Ficha Técnica Oficial — Primaria Revolución Social de 1910 (CCT 10EPR0361N, Zona 49, Sector 02 Durango).")
    ]

    for r_idx, (lbl, val) in enumerate(info_rows):
        row = table.rows[r_idx]
        c0 = row.cells[0]
        c0.width = col_widths[0]
        set_cell_background(c0, "ECFDF5")
        set_cell_margins(c0, top=40, bottom=40, left=50, right=50)
        c0.text = ""
        p0 = c0.paragraphs[0]
        r0 = p0.add_run(lbl)
        r0.font.name = 'Arial'
        r0.font.bold = True
        r0.font.size = Pt(7.5)
        r0.font.color.rgb = RGBColor(6, 95, 70)

        c1 = row.cells[1]
        c1.width = col_widths[1]
        set_cell_background(c1, HEX_BLANCO)
        set_cell_margins(c1, top=40, bottom=40, left=50, right=50)
        c1.text = ""
        p1 = c1.paragraphs[0]
        r1 = p1.add_run(val)
        r1.font.name = 'Arial'
        r1.font.size = Pt(7.5)
        r1.font.color.rgb = COLOR_TEXTO_OSCURO

    doc.add_paragraph()  # Espacio



def add_horario_escolar_table(doc, datos_escuela=None):
    """
    Distribución Inicial Paso 3:
    Genera la tabla general del HORARIO ESCOLAR con paleta estilo Gemini:
    - Encabezados principales: Fondo Morado Intenso (#7209B7), texto blanco centrado.
    - Columna de horarios: Fondo Lavanda/Lila Suave (#F3E8FF), texto Morado Oscuro (#311B92).
    - Celdas de contenido: Fondo Blanco (#FFFFFF), texto oscuro.
    - Bordes finos en morado tenue (#D8B4FE).
    """
    fase = datos_escuela.get('fase', 'Fase 5') if datos_escuela else 'Fase 5'
    grado = datos_escuela.get('grado', '6° de Primaria') if datos_escuela else '6° de Primaria'

    p_h = doc.add_paragraph()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_h = p_h.add_run(f"HORARIO ESCOLAR — {fase.upper()} ({grado.upper()})")
    r_h.font.name = 'Arial'
    r_h.font.bold = True
    r_h.font.size = Pt(11)
    r_h.font.color.rgb = COLOR_MORADO_INTENSO

    headers = ["Horario", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    table_h = doc.add_table(rows=7, cols=len(headers))
    table_h.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_h.autofit = False
    set_table_borders(table_h, color=HEX_BORDE_TENUE)

    col_widths = [Inches(1.5), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.2)]
    for c_idx, h_text in enumerate(headers):
        cell = table_h.rows[0].cells[c_idx]
        cell.text = h_text
        cell.width = col_widths[c_idx]
        set_cell_background(cell, HEX_MORADO_INTENSO)
        set_cell_margins(cell, top=50, bottom=50, left=50, right=50)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.color.rgb = COLOR_BLANCO

    raw_schedule = [
        ("08:00 - 08:30", ["Act. de Inicio", "Act. de Inicio", "Act. de Inicio", "Act. de Inicio", "Act. de Inicio"]),
        ("08:30 - 10:00", ["Lenguajes", "Lenguajes", "Lenguajes", "Lenguajes", "Lenguajes"]),
        ("10:00 - 10:30", ["RECESO", "RECESO", "RECESO", "RECESO", "RECESO"]),
        ("10:30 - 11:30", ["Pensamiento C.", "Pensamiento C.", "Pensamiento C.", "Pensamiento C.", "Pensamiento C."]),
        ("11:30 - 12:15", ["Ética, Nat. y Soc.", "Ética, Nat. y Soc.", "Ética, Nat. y Soc.", "Ética, Nat. y Soc.", "Ética, Nat. y Soc."]),
        ("12:15 - 13:00", ["De lo Humano", "Ed. Física", "De lo Humano", "Artes", "De lo Humano"])
    ]

    for r_idx, (hora, materias) in enumerate(raw_schedule, 1):
        row = table_h.rows[r_idx]
        row_vals = [hora] + materias
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.text = val
            cell.width = col_widths[c_idx]
            set_cell_margins(cell, top=45, bottom=45, left=45, right=45)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

            if c_idx == 0:
                # Subencabezado de horario: Fondo Lila Suave, texto Morado Oscuro negrita
                set_cell_background(cell, HEX_LILA_SUAVE)
                if p.runs:
                    p.runs[0].font.name = 'Arial'
                    p.runs[0].font.size = Pt(7.5)
                    p.runs[0].font.bold = True
                    p.runs[0].font.color.rgb = COLOR_MORADO_OSCURO
            elif val == "RECESO":
                # Resaltado especial de receso
                set_cell_background(cell, HEX_LILA_SUAVE)
                if p.runs:
                    p.runs[0].font.name = 'Arial'
                    p.runs[0].font.size = Pt(7.5)
                    p.runs[0].font.bold = True
                    p.runs[0].font.color.rgb = COLOR_MORADO_INTENSO
            else:
                # Celdas de contenido: Fondo Blanco (#FFFFFF)
                set_cell_background(cell, HEX_BLANCO)
                if p.runs:
                    p.runs[0].font.name = 'Arial'
                    p.runs[0].font.size = Pt(7.5)
                    p.runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

    doc.add_paragraph()  # Espacio


def add_project_metadata_table(doc, parsed_info: Dict[str, Any], datos_escuela: Dict[str, Any]):
    """
    Distribución Inicial Paso 4:
    Crea la tabla de metadatos del proyecto con paleta estilo Gemini:
    Subencabezados en Morado Oscuro sobre fondo Lila Suave (#F3E8FF) / Blanco (#FFFFFF).
    Incluye los campos de proyectos comunitarios, de aula y escolares de 6° grado.
    """
    campo_formativo = parsed_info.get("campo_formativo", "Lenguajes, Saberes y Pensamiento Científico")
    if datos_escuela and "campos_formativos" in datos_escuela and datos_escuela["campos_formativos"]:
        if isinstance(datos_escuela["campos_formativos"], list):
            campo_formativo = ", ".join(datos_escuela["campos_formativos"])
        else:
            campo_formativo = str(datos_escuela["campos_formativos"])

    periodo = datos_escuela.get('periodo', 'Semana 6 de 37') if datos_escuela else 'Semana 6 de 37'
    duracion = parsed_info.get("duracion", f"{periodo} (2 semanas)")
    fase = datos_escuela.get('fase', 'Fase 5') if datos_escuela else 'Fase 5'
    grado = datos_escuela.get('grado', '6° de Primaria') if datos_escuela else '6° de Primaria'
    grupo = datos_escuela.get('grupo', 'A') if datos_escuela else 'A'

    metodologia_doc = parsed_info.get('metodologia')
    if (not metodologia_doc or metodologia_doc == "Aprendizaje Basado en Proyectos Comunitarios (ABPC)") and datos_escuela and "metodologia" in datos_escuela:
        metodologia_doc = datos_escuela["metodologia"]
    
    if isinstance(metodologia_doc, (list, tuple, set)):
        metodologia_display = ", ".join(str(m).strip() for m in metodologia_doc if str(m).strip())
    elif isinstance(metodologia_doc, str) and metodologia_doc.strip().startswith("[") and metodologia_doc.strip().endswith("]"):
        try:
            parsed_m = json.loads(metodologia_doc)
            if isinstance(parsed_m, list):
                metodologia_display = ", ".join(str(m).strip() for m in parsed_m if str(m).strip())
            else:
                metodologia_display = metodologia_doc
        except Exception:
            metodologia_display = metodologia_doc
    else:
        metodologia_display = str(metodologia_doc or "Aprendizaje Basado en Proyectos Comunitarios")

    t_meta = doc.add_table(rows=7, cols=2)
    t_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_meta.autofit = False
    set_table_borders(t_meta, color=HEX_BORDE_TENUE)

    meta_cells = [
        (("Nombre del Proyecto Integrador:", parsed_info['nombre_proyecto']), ("Campos Formativos Articulados:", campo_formativo)),
        (("Duración / Temporalidad:", duracion), ("Metodología(s) Sociocrítica(s):", metodologia_display)),
        (("Escenarios del Proyecto:", parsed_info['escenario']), ("Libros de Texto SEP (LTG 6°):", parsed_info['libros_texto'])),
        (("Problemática Priorizada (P.A.):", parsed_info['problematica']), ("Ejes Articuladores:", parsed_info['ejes'])),
        (("Propósito General del Proyecto:", parsed_info['proposito']), ("Fase y Grado Escolar:", f"{fase} — {grado} '{grupo}' (26 Alumnos)")),
        (("Contenidos Sintéticos (Fase 5 - 6°):", parsed_info['contenidos']), ("Procesos de Desarrollo (PDA):", parsed_info['pda'])),
        (("Proyectos de Aula y Escolares:", "Proyectos de Aula (6° grado) y Proyectos Escolares (6° grado)"), ("Proyectos Comunitarios:", "Proyectos Comunitarios (6° grado) y Cuadernillo Profa. Kempis"))
    ]

    for r_i, (c0_pair, c1_pair) in enumerate(meta_cells):
        r = t_meta.rows[r_i]
        bg_color = HEX_LILA_SUAVE if r_i % 2 == 0 else HEX_BLANCO
        for c_i, (lbl, val) in enumerate([c0_pair, c1_pair]):
            cell = r.cells[c_i]
            cell.width = Inches(3.75)
            set_cell_background(cell, bg_color)
            set_cell_margins(cell, top=45, bottom=45, left=60, right=60)
            cell.text = ""
            p = cell.paragraphs[0]
            r_lbl = p.add_run(f"{lbl}\n")
            r_lbl.font.name = 'Arial'
            r_lbl.font.size = Pt(7.5)
            r_lbl.font.bold = True
            r_lbl.font.color.rgb = COLOR_MORADO_OSCURO

            r_val = p.add_run(val)
            r_val.font.name = 'Arial'
            r_val.font.size = Pt(8)
            r_val.font.color.rgb = COLOR_TEXTO_OSCURO

    doc.add_paragraph()  # Espacio


def add_articulacion_curricular_table(doc, parsed_info: Dict[str, Any], datos_escuela: Dict[str, Any]):
    """
    Tabla Oficial de Articulación Curricular de los 4 Campos Formativos (Estilo Profa. Kempis - 6° Grado).
    Articula transversalmente los Contenidos y PDA de Lenguajes, Saberes, Ética y De lo Humano
    con los escenarios (Comunitario, Aula, Escolar) y libros de texto de 6° grado.
    """
    p_h = doc.add_paragraph()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_h = p_h.add_run("TABLA DE ARTICULACIÓN CURRICULAR DE LOS 4 CAMPOS FORMATIVOS (FASE 5 — 6° DE PRIMARIA)")
    r_h.font.name = 'Arial'
    r_h.font.bold = True
    r_h.font.size = Pt(10.5)
    r_h.font.color.rgb = COLOR_MORADO_INTENSO

    headers = [
        "CAMPO FORMATIVO",
        "PROYECTO Y ESCENARIO (LTG 6°)",
        "CONTENIDO SINTÉTICO (6°)",
        "PDA OFICIAL ESPECÍFICO",
        "VINCULACIÓN LTG Y NUESTROS SABERES"
    ]
    col_widths = [Inches(1.2), Inches(1.4), Inches(1.6), Inches(1.8), Inches(1.5)]

    filas_art = parsed_info.get("articulacion_filas", [])
    if not filas_art or len(filas_art) < 4:
        filas_art = [
            [
                "Lenguajes",
                "Proyecto: ¡Mi comunidad se expresa!\nProyectos de Aula (págs. 20-35 / 34-49) y Múltiples Lenguajes (págs. 40-47).\nEscenario Aula / Comunitario.",
                "Análisis y representación de textos literarios: el cuento y la lectura dramatizada.",
                "Lee, analiza y recrea cuentos reconociendo planteamiento, nudo y desenlace; interpreta guiones teatrales empleando acotaciones, modulación de voz y expresión corporal.",
                "Nuestros Saberes (págs. 28-35): Recursos literarios, la narración y estructura del cuento. Anexos 6.1 y 7.1."
            ],
            [
                "Saberes y Pensamiento Científico",
                "Proyecto: El poder de la alimentación\nProyectos de Aula (págs. 140-153).\nEscenario Aula / Escolar.",
                "Alimentación saludable: alimentos procesados, sellos de advertencia NOM-051, Plato del Bien Comer y múltiplos y submúltiplos del gramo.",
                "Analiza etiquetas y sellos de advertencia en alimentos ultraprocesados; diseña menús balanceados con el Plato del Bien Comer y resuelve problemas con múltiplos del gramo y cálculo de porcentajes e IVA del 16%.",
                "Nuestros Saberes (págs. 68-76): El sistema digestivo, nutrición, sellos NOM-051 y unidades de masa: múltiplos del gramo. Anexos 6.2 y 7.2."
            ],
            [
                "Ética, Naturaleza y Sociedades",
                "Proyecto: Contribuyo con los servicios de mi escuela\nProyectos Escolares (págs. 194-207 / 210-225).\nEscenario Escolar / Comunitario.",
                "Cultura democrática: servicios públicos, satisfacción de necesidades básicas e impacto social de los impuestos y el IVA; conmemoraciones cívicas.",
                "Diagnostica los servicios públicos de su entorno escolar y comunitario; comprende la importancia de la contribución ciudadana y el destino de los impuestos para el bienestar colectivo en Durango.",
                "Nuestros Saberes (págs. 140-149): Servicios públicos, cultura contributiva e IVA (16%). Anexos 6.3 y 7.3."
            ],
            [
                "De lo Humano y lo Comunitario",
                "Proyecto: El club de las nutrias\nProyectos de Aula (págs. 320-333) y Proyectos Comunitarios (págs. 50-63 / 278-293).\nEscenario Aula / Comunitario.",
                "Estilos de vida activos y saludables, circuitos motrices, prevención del sedentarismo y resolución pacífica de desacuerdos.",
                "Organiza y participa en circuitos motrices y dinámicas de actividad física para valorar el impacto del ejercicio continuo en el bienestar integral y resolver desacuerdos mediante la mediación dialógica.",
                "Nuestros Saberes (págs. 202-211): Mediación dialógica, cultura de paz, estilos de vida activos y circuitos motrices. Anexos 6.4 y 7.4."
            ]
        ]

    table_art = doc.add_table(rows=len(filas_art) + 1, cols=len(headers))
    table_art.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_art.autofit = False
    set_table_borders(table_art, color=HEX_BORDE_TENUE)

    for c_i, h_txt in enumerate(headers):
        cell = table_art.rows[0].cells[c_i]
        cell.text = h_txt
        cell.width = col_widths[c_i]
        set_cell_background(cell, HEX_MORADO_INTENSO)
        set_cell_margins(cell, top=50, bottom=50, left=45, right=45)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.color.rgb = COLOR_BLANCO

    for r_idx, row_data in enumerate(filas_art, 1):
        row = table_art.rows[r_idx]
        for c_idx, val in enumerate(row_data[:len(headers)]):
            cell = row.cells[c_idx]
            cell.text = str(val).strip()
            cell.width = col_widths[c_idx]
            set_cell_margins(cell, top=45, bottom=45, left=45, right=45)
            p = cell.paragraphs[0]
            if c_idx == 0:
                set_cell_background(cell, HEX_LILA_SUAVE)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if p.runs:
                    p.runs[0].font.name = 'Arial'
                    p.runs[0].font.size = Pt(7.5)
                    p.runs[0].font.bold = True
                    p.runs[0].font.color.rgb = COLOR_MORADO_OSCURO
            else:
                set_cell_background(cell, HEX_BLANCO)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                if p.runs:
                    p.runs[0].font.name = 'Arial'
                    p.runs[0].font.size = Pt(7.5)
                    p.runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

    doc.add_paragraph()  # Espacio


def add_evaluacion_formativa_table(doc, parsed_info: Dict[str, Any], datos_escuela: Dict[str, Any]):
    """
    Tabla Oficial de Instrumentos de Evaluación Formativa y Criterios de Desempeño (Estilo Profa. Kempis - 6° Grado).
    Establece los niveles de logro (Sobresaliente, Satisfactorio, Básico, Requiere Apoyo) e instrumentos
    específicos para las problemáticas prioritarias y los aprendizajes de 6° grado.
    """
    p_h = doc.add_paragraph()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_h = p_h.add_run("INSTRUMENTOS DE EVALUACIÓN FORMATIVA Y CRITERIOS DE DESEMPEÑO (6° DE PRIMARIA)")
    r_h.font.name = 'Arial'
    r_h.font.bold = True
    r_h.font.size = Pt(10.5)
    r_h.font.color.rgb = COLOR_MORADO_INTENSO

    headers = [
        "CRITERIO / CAMPO FORMATIVO",
        "SOBRESALIENTE (10)",
        "SATISFACTORIO (8-9)",
        "BÁSICO (6-7)",
        "REQUIERE APOYO (5)",
        "INSTRUMENTO Y EVIDENCIA"
    ]
    col_widths = [Inches(1.4), Inches(1.2), Inches(1.2), Inches(1.2), Inches(1.1), Inches(1.4)]

    filas_eva = parsed_info.get("evaluacion_filas", [])
    if not filas_eva or len(filas_eva) < 4:
        filas_eva = [
            [
                "Comprensión Lectora e Inferencias (Lenguajes)",
                "Identifica ideas clave y secundarias, infiere la intención del autor y recrea cuentos o guiones teatrales con acotaciones y modulación impecable.",
                "Reconoce planteamiento, nudo y desenlace y responde preguntas inferenciales básicas con autonomía y coherencia.",
                "Comprende el sentido global del texto pero requiere acompañamiento docente para rescatar ideas inferenciales secundarias.",
                "Dificultad marcada para rescatar ideas principales y comprender el léxico del texto.",
                "Rúbrica analítica, organizadores visuales y ficha del Cuadernillo Profa. Kempis."
            ],
            [
                "Velocidad y Fluidez Lectora",
                "Lee en voz alta con modulación precisa, dicción clara, entonación adecuada y respetando todos los signos de puntuación (>120 ppm).",
                "Lee con fluidez adecuada y volumen audible cometiendo mínimas pausas innecesarias (100-119 ppm).",
                "Ritmo pausado con silabeos ocasionales, requiriendo apoyo para respetar puntos y comas (80-99 ppm).",
                "Lectura silábica o entrecortada que dificulta la comprensión personal y grupal (<80 ppm).",
                "Registro de fluidez lectora, cronometrado de 1 minuto y lectura dramatizada en asamblea."
            ],
            [
                "Ortografía y Redacción Autónoma",
                "Redacta textos propios con acentuación rigurosa (agudas, graves, esdrújulas), grafías dudosas correctas y conectores variados.",
                "Elabora textos con estructura clara y coherente; presenta errores ortográficos mínimos que no alteran el sentido.",
                "Textos con ideas breves o errores recurrentes de acentuación, concordancia y signos de puntuación.",
                "Producciones muy breves e incompletas con deficiencias ortográficas severas.",
                "Lista de cotejo de producción escrita, dictados matutinos y borradores en el cuaderno."
            ],
            [
                "Cálculo Mental y Problemas Contextualizados (Saberes)",
                "Resuelve con agilidad mental y exactitud conversiones de múltiplos del gramo, cálculo de porcentajes y aplicación del IVA del 16%.",
                "Aplica procedimientos matemáticos correctos en conversiones de unidades y situaciones problemáticas con apoyo mínimo.",
                "Resuelve operaciones básicas pero comete equivocaciones en conversiones de unidades o cálculo de descuentos.",
                "Confunde operaciones básicas y requiere mediación constante y material concreto para resolver problemas.",
                "Escala estimativa, ejercicios de cálculo matutino y fichas prácticas del Cuadernillo Kempis."
            ],
            [
                "Convivencia Pacífica y Mediación (Ética y De lo Humano)",
                "Aplica activamente mecanismos de resolución pacífica de conflictos y colabora con entusiasmo en asambleas y proyectos comunitarios.",
                "Participa de forma respetuosa en dinámicas grupales y respeta acuerdos colectivos de aula.",
                "Requiere intervención docente para resolver desacuerdos con sus pares de forma pacífica.",
                "Presenta actitudes de exclusión o resistencia al trabajo colaborativo en equipo.",
                "Registro anecdótico, diario de campo docente y diana de autoevaluación/coevaluación."
            ]
        ]

    table_eva = doc.add_table(rows=len(filas_eva) + 1, cols=len(headers))
    table_eva.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_eva.autofit = False
    set_table_borders(table_eva, color=HEX_BORDE_TENUE)

    for c_i, h_txt in enumerate(headers):
        cell = table_eva.rows[0].cells[c_i]
        cell.text = h_txt
        cell.width = col_widths[c_i]
        set_cell_background(cell, HEX_MORADO_INTENSO)
        set_cell_margins(cell, top=50, bottom=50, left=45, right=45)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.color.rgb = COLOR_BLANCO

    for r_idx, row_data in enumerate(filas_eva, 1):
        row = table_eva.rows[r_idx]
        for c_idx, val in enumerate(row_data[:len(headers)]):
            cell = row.cells[c_idx]
            cell.text = str(val).strip()
            cell.width = col_widths[c_idx]
            set_cell_margins(cell, top=45, bottom=45, left=45, right=45)
            p = cell.paragraphs[0]
            if c_idx == 0:
                set_cell_background(cell, HEX_LILA_SUAVE)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if p.runs:
                    p.runs[0].font.name = 'Arial'
                    p.runs[0].font.size = Pt(7.5)
                    p.runs[0].font.bold = True
                    p.runs[0].font.color.rgb = COLOR_MORADO_OSCURO
            else:
                set_cell_background(cell, HEX_BLANCO)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                if p.runs:
                    p.runs[0].font.name = 'Arial'
                    p.runs[0].font.size = Pt(7.5)
                    p.runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

    doc.add_paragraph()  # Espacio


def add_ajustes_razonables_table(doc, parsed_info: Dict[str, Any], datos_escuela: Dict[str, Any]):
    """
    Agrega la tabla de Ajustes Razonables (DUA - BAP) y Seguimiento en Diario de Clase.
    Atiende a los 26 alumnos del grupo de 6° 'A' con énfasis en estilos kinestésico y visual.
    """
    p_h = doc.add_paragraph()
    p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_h = p_h.add_run("AJUSTES RAZONABLES (DUA) Y OBSERVACIONES DOCENTES (CICLO 2026-2027)")
    r_h.font.name = 'Arial'
    r_h.font.bold = True
    r_h.font.size = Pt(10.5)
    r_h.font.color.rgb = COLOR_MORADO_INTENSO

    headers = [
        "ATENCIÓN A LA DIVERSIDAD Y BAP (DISEÑO UNIVERSAL PARA EL APRENDIZAJE)",
        "SEGUIMIENTO EN EL DIARIO DE CLASE Y COMPROMISOS INSTITUCIONALES"
    ]
    col_widths = [Inches(3.75), Inches(3.75)]

    table_adj = doc.add_table(rows=2, cols=2)
    table_adj.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_adj.autofit = False
    set_table_borders(table_adj, color=HEX_BORDE_TENUE)

    for c_i, h_txt in enumerate(headers):
        cell = table_adj.rows[0].cells[c_i]
        cell.text = h_txt
        cell.width = col_widths[c_i]
        set_cell_background(cell, HEX_MORADO_INTENSO)
        set_cell_margins(cell, top=50, bottom=50, left=50, right=50)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.color.rgb = COLOR_BLANCO

    r1_c0 = table_adj.rows[1].cells[0]
    adecs_txt = parsed_info.get("adecuaciones", "").strip()
    if not adecs_txt or len(adecs_txt) < 30:
        adecs_txt = (
            "• Principio de Representación (Visual): Uso de organizadores gráficos de alto contraste, esquemas y tablas ilustradas para los 26 alumnos.\n"
            "• Principio de Acción y Expresión (Kinestésico): Manipulación de tarjetas ortográficas móviles, material concreto para múltiplos del gramo y dramatizaciones teatrales.\n"
            "• Tutoría entre pares y nivelación personalizada en velocidad lectora y ortografía.\n"
            "• Acceso equitativo a dispositivos digitales y recursos en el aula."
        )
    r1_c0.text = adecs_txt
    r1_c0.width = col_widths[0]
    set_cell_background(r1_c0, HEX_BLANCO)
    set_cell_margins(r1_c0, top=45, bottom=45, left=50, right=50)
    for p in r1_c0.paragraphs:
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.size = Pt(7.5)
            p.runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

    r1_c1 = table_adj.rows[1].cells[1]
    obs_txt = parsed_info.get("observaciones", "").strip()
    if not obs_txt or len(obs_txt) < 30:
        obs_txt = (
            "• Registro diario de avances en velocidad y fluidez lectora (palabras por minuto) y precisión ortográfica en el diario de campo.\n"
            "• Cumplimiento de compromisos del Programa Analítico Oficial de la Primaria Revolución Social de 1910 (CCT: 10EPR0361N, Durango).\n"
            "• Vinculación continua con familias para el fomento a la lectura compartida en el hogar."
        )
    r1_c1.text = obs_txt
    r1_c1.width = col_widths[1]
    set_cell_background(r1_c1, HEX_BLANCO)
    set_cell_margins(r1_c1, top=45, bottom=45, left=50, right=50)
    for p in r1_c1.paragraphs:
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.size = Pt(7.5)
            p.runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

    doc.add_paragraph()  # Espacio


def add_document_credits(doc):
    """Agrega la frase oficial de créditos al pie del documento Word generado."""
    doc.add_paragraph()
    p_cred = doc.add_paragraph()
    p_cred.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cred = p_cred.add_run("Desarrollado para la labor pedagógica")
    r_cred.font.name = 'Arial'
    r_cred.font.size = Pt(8.5)
    r_cred.font.italic = True
    r_cred.font.color.rgb = COLOR_MORADO_OSCURO

    for section in doc.sections:
        footer = section.footer
        p_foot = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        p_foot.text = "Desarrollado para la labor pedagógica"
        p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p_foot.runs:
            p_foot.runs[0].font.name = 'Arial'
            p_foot.runs[0].font.size = Pt(8)
            p_foot.runs[0].font.italic = True
            p_foot.runs[0].font.color.rgb = RGBColor(148, 163, 184)


def add_cuadernillo_kempis_section(doc, parsed_info: Dict[str, Any], datos_escuela: Dict[str, Any]):
    """
    Integra formalmente la sección didáctica y los anexos imprimibles del
    Cuadernillo de Actividades (Semanas 6 y 7 - Profa Kempis) como recurso de apoyo,
    incluyendo tablas con fichas de trabajo, conversión de múltiplos del gramo,
    análisis de sellos de advertencia NOM-051, cálculo del IVA y enlaces a videos explicativos.
    """
    periodo_str = str(datos_escuela.get("periodo", "") if datos_escuela else "").lower()
    raw_text = (parsed_info.get("raw_text", "") + " " + periodo_str).lower()

    semana_num = None
    if datos_escuela and "semana" in datos_escuela:
        try:
            semana_num = int(datos_escuela["semana"])
        except Exception:
            pass
    if not semana_num:
        m_sem = re.search(r'semana\s*(\d+)', periodo_str)
        if m_sem:
            semana_num = int(m_sem.group(1))

    es_relevante = detectar_relevancia_kempis(
        semana=semana_num,
        directrices_o_texto=raw_text
    )

    if not es_relevante and semana_num not in [6, 7]:
        return

    sem_kempis = semana_num or int(datos_escuela.get("semana", 1)) if datos_escuela else 1

    kempis_meta = obtener_recursos_kempis_por_semana(sem_kempis)
    if not kempis_meta:
        kempis_meta = CUADERNILLO_KEMPIS_DATA.get(sem_kempis)
    if not kempis_meta:
        return

    anexos_lista = obtener_anexos_kempis_para_docx(sem_kempis)
    if not anexos_lista:
        return

    # 1. Salto de página para presentar los anexos imprimibles
    doc.add_page_break()

    # 2. Encabezado principal de la sección
    p_hdr = doc.add_paragraph()
    p_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_hdr.add_run("RECURSOS DIDÁCTICOS Y MATERIALES IMPRIMIBLES DE APOYO\n")
    r_sub.font.name = 'Arial'
    r_sub.font.bold = True
    r_sub.font.size = Pt(10)
    r_sub.font.color.rgb = COLOR_MORADO_OSCURO

    tit_banner = f"CUADERNILLO DE ACTIVIDADES — SEMANA {sem_kempis} (PROFA KEMPIS)\n" if sem_kempis in [6, 7] else f"ANEXOS IMPRIMIBLES DEL PROYECTO — SEMANA {sem_kempis} DE 37\n"
    r_tit = p_hdr.add_run(tit_banner)
    r_tit.font.name = 'Arial'
    r_tit.font.bold = True
    r_tit.font.size = Pt(12)
    r_tit.font.color.rgb = COLOR_MORADO_INTENSO

    r_desc = p_hdr.add_run(f"{kempis_meta.get('descripcion', '')} Fichas didácticas organizadas por Campo Formativo y día listas para fotocopiar.")
    r_desc.font.name = 'Arial'
    r_desc.font.size = Pt(8.5)
    r_desc.font.italic = True
    r_desc.font.color.rgb = COLOR_TEXTO_OSCURO

    doc.add_paragraph()

    # 3. Tabla Resumen de Anexos y Fichas Didácticas
    p_t_lbl = doc.add_paragraph()
    r_tl = p_t_lbl.add_run("1. ÍNDICE DE ANEXOS Y FICHAS DIDÁCTICAS IMPRIMIBLES:")
    r_tl.font.name = 'Arial'
    r_tl.font.bold = True
    r_tl.font.size = Pt(9.5)
    r_tl.font.color.rgb = COLOR_MORADO_INTENSO

    tbl_resumen = doc.add_table(rows=len(anexos_lista) + 1, cols=4)
    tbl_resumen.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_resumen.autofit = False
    set_table_borders(tbl_resumen, color=HEX_BORDE_TENUE)

    headers_res = ["CAMPO FORMATIVO", "ANEXO IMPRIMIBLE", "ACTIVIDAD VIVENCIAL", "PROPÓSITO Y PRODUCTO"]
    widths_res = [Inches(1.5), Inches(2.0), Inches(2.3), Inches(1.7)]

    for c_i, h_txt in enumerate(headers_res):
        c = tbl_resumen.rows[0].cells[c_i]
        c.width = widths_res[c_i]
        c.text = h_txt
        set_cell_background(c, HEX_MORADO_INTENSO)
        set_cell_margins(c, top=45, bottom=45, left=45, right=45)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p.runs:
            p.runs[0].font.name = 'Arial'
            p.runs[0].font.bold = True
            p.runs[0].font.size = Pt(8)
            p.runs[0].font.color.rgb = COLOR_BLANCO

    for row_idx, anexo in enumerate(anexos_lista, 1):
        row = tbl_resumen.rows[row_idx]
        for c_i, w in enumerate(widths_res):
            row.cells[c_i].width = w

        c0 = row.cells[0]
        c0.text = anexo.get("campo", "")
        set_cell_background(c0, HEX_LILA_SUAVE)
        set_cell_margins(c0, top=40, bottom=40, left=40, right=40)
        if c0.paragraphs and c0.paragraphs[0].runs:
            c0.paragraphs[0].runs[0].font.name = 'Arial'
            c0.paragraphs[0].runs[0].font.size = Pt(7.5)
            c0.paragraphs[0].runs[0].font.bold = True
            c0.paragraphs[0].runs[0].font.color.rgb = COLOR_MORADO_OSCURO

        c1 = row.cells[1]
        c1.text = f"{anexo.get('nombre', '')}\n\n{anexo.get('descripcion', '')}"
        set_cell_background(c1, HEX_BLANCO)
        set_cell_margins(c1, top=40, bottom=40, left=40, right=40)
        if c1.paragraphs and c1.paragraphs[0].runs:
            c1.paragraphs[0].runs[0].font.name = 'Arial'
            c1.paragraphs[0].runs[0].font.size = Pt(7.5)
            c1.paragraphs[0].runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

        c2 = row.cells[2]
        c2.text = anexo.get("actividad", "")
        set_cell_background(c2, HEX_BLANCO)
        set_cell_margins(c2, top=40, bottom=40, left=40, right=40)
        if c2.paragraphs and c2.paragraphs[0].runs:
            c2.paragraphs[0].runs[0].font.name = 'Arial'
            c2.paragraphs[0].runs[0].font.size = Pt(7.5)
            c2.paragraphs[0].runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

        c3 = row.cells[3]
        c3.text = f"🎯 Enfoque NEM:\n{anexo.get('tema', '')}\n\n📋 Producto:\nFicha de trabajo completada"
        set_cell_background(c3, HEX_BLANCO)
        set_cell_margins(c3, top=40, bottom=40, left=40, right=40)
        if c3.paragraphs and c3.paragraphs[0].runs:
            c3.paragraphs[0].runs[0].font.name = 'Arial'
            c3.paragraphs[0].runs[0].font.size = Pt(7.5)
            c3.paragraphs[0].runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

    doc.add_paragraph()

    # 4. Fichas de Trabajo Imprimibles Detalladas
    p_fichas_lbl = doc.add_paragraph()
    r_fl = p_fichas_lbl.add_run("2. FICHAS DE TRABAJO IMPRIMIBLES (ANEXOS LISTOS PARA EL ALUMNO):")
    r_fl.font.name = 'Arial'
    r_fl.font.bold = True
    r_fl.font.size = Pt(9.5)
    r_fl.font.color.rgb = COLOR_MORADO_INTENSO

    for anexo in anexos_lista:
        t_ficha = doc.add_table(rows=3, cols=1)
        t_ficha.alignment = WD_TABLE_ALIGNMENT.CENTER
        t_ficha.autofit = False
        set_table_borders(t_ficha, color=HEX_BORDE_TENUE)

        c_hdr = t_ficha.rows[0].cells[0]
        c_hdr.width = Inches(7.5)
        c_hdr.text = f"ESCUELA PRIMARIA “REVOLUCIÓN SOCIAL DE 1910” | 6° GRADO “A”\n{anexo.get('nombre', '').upper()}"
        set_cell_background(c_hdr, HEX_LILA_SUAVE)
        set_cell_margins(c_hdr, top=45, bottom=45, left=60, right=60)
        p_ch = c_hdr.paragraphs[0]
        p_ch.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p_ch.runs:
            p_ch.runs[0].font.name = 'Arial'
            p_ch.runs[0].font.bold = True
            p_ch.runs[0].font.size = Pt(8.5)
            p_ch.runs[0].font.color.rgb = COLOR_MORADO_OSCURO

        c_al = t_ficha.rows[1].cells[0]
        c_al.width = Inches(7.5)
        c_al.text = "Nombre del alumno(a): ____________________________________________________  Fecha: ____________________"
        set_cell_background(c_al, HEX_BLANCO)
        set_cell_margins(c_al, top=35, bottom=35, left=60, right=60)
        if c_al.paragraphs and c_al.paragraphs[0].runs:
            c_al.paragraphs[0].runs[0].font.name = 'Arial'
            c_al.paragraphs[0].runs[0].font.size = Pt(8)
            c_al.paragraphs[0].runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

        c_body = t_ficha.rows[2].cells[0]
        c_body.width = Inches(7.5)

        a_nom = anexo.get('nombre', '')
        if "6.1" in a_nom:
            c_body.text = (
                "INSTRUCCIONES:\n"
                "1. Lee con atención el cuento seleccionado en el libro Múltiples Lenguajes (o el propuesto por la maestra).\n"
                "2. Completa el siguiente organizador gráfico identificando la estructura de la narración:\n\n"
                "• PLANTEAMIENTO / INICIO (¿Quiénes son los personajes y dónde ocurre la historia?):\n"
                "  _______________________________________________________________________________________________\n\n"
                "• NUDO / CONFLICTO (¿Qué problema o reto enfrentan los protagonistas?):\n"
                "  _______________________________________________________________________________________________\n\n"
                "• DESENLACE (¿Cómo se resuelve la situación y qué aprendieron?):\n"
                "  _______________________________________________________________________________________________\n\n"
                "• TIPO DE NARRADOR (Marca con una X):  (   ) Primera persona (Protagonista/Testigo)    (   ) Tercera persona (Omnisciente)\n\n"
                "• Reflexión final: ¿Qué valores o enseñanzas comunitarias aporta este texto literario?\n"
                "  _______________________________________________________________________________________________"
            )
        elif "6.2" in a_nom:
            c_body.text = (
                "INSTRUCCIONES:\n"
                "1. Observa el empaque de alimento que trajiste y completa la tabla de conversión (Método de la escalera: kg, hg, dag, g, dg, cg, mg).\n"
                "2. Responde las preguntas de análisis nutricional:\n\n"
                "• Nombre del producto: ________________________________  Contenido neto en gramos: ____________ g\n"
                "• Conversión de masa: En kilogramos (kg): ___________ kg  |  En miligramos (mg): ___________ mg\n"
                "• Sellos NOM-051 identificados (marca los que contiene):\n"
                "  [  ] EXCESO CALORÍAS   [  ] EXCESO AZÚCARES   [  ] EXCESO GRASAS SATURADAS   [  ] EXCESO SODIO\n"
                "• Si una porción de 100 g contiene 14 g de grasas, ¿cuántos gramos de grasa consumirá una persona en 350 g?\n"
                "  Operaciones: ____________________________________________________  Resultado: _____________ g\n\n"
                "• Decisión saludable: ¿Por qué es conveniente reducir el consumo de alimentos ultraprocesados con sellos negros?\n"
                "  _______________________________________________________________________________________________"
            )
        elif "6.3" in a_nom:
            c_body.text = (
                "INSTRUCCIONES:\n"
                "1. Clasifica los servicios públicos de tu comunidad (agua, luz, recolección de basura, parques, escuelas).\n"
                "2. Resuelve el cálculo del IVA (16%) en los siguientes recibos de compra simulados:\n\n"
                "• Compra A: Artículos de limpieza escolar -> Subtotal: $300.00 pesos.\n"
                "  Cálculo del IVA (300 x 0.16) = $___________  |  Total a pagar (Subtotal + IVA) = $___________\n\n"
                "• Compra B: Balones y material deportivo -> Subtotal: $650.00 pesos.\n"
                "  Cálculo del IVA (650 x 0.16) = $___________  |  Total a pagar (Subtotal + IVA) = $___________\n\n"
                "• Pregunta de reflexión ciudadana: ¿Por qué es fundamental que todos contribuyamos con los impuestos?\n"
                "  Respuesta: ___________________________________________________________________________________"
            )
        elif "6.4" in a_nom:
            c_body.text = (
                "INSTRUCCIONES:\n"
                "1. Lee el caso práctico escolar: 'En el recreo, dos equipos de 6° grado quieren utilizar la única cancha disponible al mismo tiempo y comienzan a discutir acaloradamente'.\n"
                "2. Aplica la ruta de mediación dialógica y responde:\n\n"
                "• ¿Cuál es el origen o necesidad real de cada una de las partes? ____________________________________\n"
                "• ¿Qué acuerdo pacífico propondrías tú como mediador(a) escolar? __________________________________\n"
                "• Menciona los 3 valores indispensables para resolver desacuerdos sin violencia: ____________________\n\n"
                "• Compromiso: Mi compromiso personal para mantener un aula libre de violencia es:\n"
                "  _______________________________________________________________________________________________"
            )
        elif "7.1" in a_nom:
            c_body.text = (
                "INSTRUCCIONES:\n"
                "1. Lee el fragmento del guión teatral en equipo. Observa que los diálogos van precedidos por el nombre del personaje y las acotaciones entre paréntesis ( ).\n"
                "2. Ensayen la lectura dramatizada cuidando entonación, pausas, volumen y gesticulación:\n\n"
                "PERSONAJE A (con asombro y señalando al horizonte): —¡Miren lo que encontramos en el huerto escolar!\n"
                "PERSONAJE B (acercándose con paso rápido y voz entusiasta): —¡Son las verduras que sembramos hace dos meses!\n"
                "PERSONAJE C (sonriendo y tomando nota en su bitácora): —Registremos el peso en gramos antes de cosechar.\n\n"
                "• Evaluación del equipo: Fluidez lectora: [  ] Sobresaliente  [  ] Satisfactorio  [  ] Por mejorar\n\n"
                "• Acotaciones identificadas: ¿Qué expresan las acotaciones sobre las emociones de los personajes?\n"
                "  _______________________________________________________________________________________________"
            )
        elif "7.2" in a_nom:
            c_body.text = (
                "INSTRUCCIONES:\n"
                "1. Diseña un menú escolar saludable para un día, balanceando los 3 grupos del Plato del Bien Comer.\n"
                "2. Estima la masa en gramos de cada alimento para asegurar una comida balanceada:\n\n"
                "• Desayuno saludable:\n"
                "  - Verduras y frutas (50% del plato): ____________________________ (Estimado: ________ g)\n"
                "  - Granos y cereales integrales (30% del plato): _________________ (Estimado: ________ g)\n"
                "  - Leguminosas y alimentos origen animal (20%): _________________ (Estimado: ________ g)\n\n"
                "• Compromiso de hidratación: ¿Cuántos vasos de agua potable beberé hoy? (Meta: 6 a 8 vasos) -> [  ] Cumplido\n"
                "• ¿Qué beneficio tiene para mi rendimiento escolar el consumo diario de agua simple potable?\n"
                "  _______________________________________________________________________________________________"
            )
        elif "7.3" in a_nom:
            c_body.text = (
                "INSTRUCCIONES:\n"
                "Evalúa los indicadores de calidad de vida en tu colonia/comunidad en Durango marcando de 1 a 5 estrellas:\n\n"
                "• Acceso a agua potable y drenaje seguro:  [ ★ ★ ★ ★ ★ ]\n"
                "• Alumbrado y seguridad en las calles:     [ ★ ★ ★ ★ ★ ]\n"
                "• Espacios verdes, parques y canchas:     [ ★ ★ ★ ★ ★ ]\n"
                "• Servicios médicos y centros de salud:   [ ★ ★ ★ ★ ★ ]\n\n"
                "• Propuesta comunitaria: ¿Qué acción colaborativa podemos realizar en la escuela para mejorar nuestro entorno?\n"
                "  _______________________________________________________________________________________________"
            )
        elif "7.4" in a_nom:
            c_body.text = (
                "INSTRUCCIONES:\n"
                "Registra tu participación en el circuito kinestésico saludable de 6° 'A':\n\n"
                "• Estación 1: Salto continuo de cuerda (1 minuto) -> Número de saltos: ________\n"
                "• Estación 2: Carrera de relevos en zigzag -> Tiempo cronometrado: ________ seg\n"
                "• Estación 3: Ejercicios de equilibrio y estiramiento muscular -> [  ] Realizado con éxito\n"
                "• Pulso cardíaco en reposo: ______ lpm  |  Pulso cardíaco después de la actividad: ______ lpm\n\n"
                "• Reflexión de salud: ¿Cómo influye el ejercicio diario en mi bienestar físico y emocional?\n"
                "  _______________________________________________________________________________________________"
            )
        else:
            c_body.text = (
                f"INSTRUCCIONES:\n"
                f"1. Reflexiona sobre la conmemoración de: {anexo.get('tema')}.\n"
                "2. Responde las siguientes interrogantes y elabora un dibujo o lema alusivo:\n\n"
                f"• {anexo.get('actividad')}\n"
                "• ¿Por qué es importante conmemorar esta fecha en nuestra comunidad escolar?\n"
                "  _______________________________________________________________________________________________\n"
                "• Lema o frase de acción comunitaria: ___________________________________________________________"
            )

        set_cell_background(c_body, HEX_BLANCO)
        set_cell_margins(c_body, top=45, bottom=45, left=60, right=60)
        for p_line in c_body.paragraphs:
            if p_line.runs:
                p_line.runs[0].font.name = 'Arial'
                p_line.runs[0].font.size = Pt(7.5)
                p_line.runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

        doc.add_paragraph()


def build_docx_planeacion(datos_escuela: Dict[str, Any], plan_text: str) -> io.BytesIO:

    """
    Construye la planeación oficial en Word (.docx) con rediseño tecnológico estilo Gemini:
    - Tipografía global estándar SEP: 'Arial' 10 pt
    - Encabezados principales: Fondo Morado Intenso (#7209B7), texto Blanco, negrita y centrado.
    - Subencabezados o Secciones: Fondo Lavanda / Lila Suave (#F3E8FF), texto Morado Oscuro (#311B92), negrita.
    - Celdas de contenido: Fondo completamente Blanco (#FFFFFF), texto oscuro (#1E293B).
    - Bordes de tablas finos en morado tenue (#D8B4FE).
    - Secuencia de actividades optimizada como la columna más ancha.
    """
    parsed_info = parse_plan_sections(plan_text)

    doc = Document()
    document = doc

    # Configuración del estilo global del documento: Arial 10 pt
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Arial'
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = COLOR_TEXTO_OSCURO
    rFonts = normal_style.element.rPr.get_or_add_rFonts()
    rFonts.set(qn('w:ascii'), 'Arial')
    rFonts.set(qn('w:hAnsi'), 'Arial')
    rFonts.set(qn('w:cs'), 'Arial')

    for section in doc.sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

    # Encabezado principal del documento
    p_header = doc.add_paragraph()
    p_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_header.add_run("SECRETARÍA DE EDUCACIÓN PÚBLICA — NUEVA ESCUELA MEXICANA\n")
    r_sub.font.name = 'Arial'
    r_sub.font.bold = True
    r_sub.font.size = Pt(9.5)
    r_sub.font.color.rgb = COLOR_MORADO_OSCURO

    r_plano = p_header.add_run("PLANO DIDÁCTICO DE INTERVENCIÓN DOCENTE")
    r_plano.font.name = 'Arial'
    r_plano.font.bold = True
    r_plano.font.size = Pt(12)
    r_plano.font.color.rgb = COLOR_MORADO_INTENSO

    # =======================================================
    # DISTRIBUCIÓN INICIAL (Antes de los días)
    # =======================================================
    # 1. Líneas de firmas centradas para "Director Escolar" y "Docente titular del Grupo"
    add_initial_signatures(doc, datos_escuela)

    # 2. Tabla de encabezado institucional (Nombre de Escuela, CCT, Semana y Ciclo Escolar)
    add_institutional_header_table(doc, datos_escuela)

    # 2.1 Validación y Trazabilidad Curricular de Base Estricta (Tarea 93)
    add_base_estricta_traceability_table(doc, datos_escuela)

    # 3. Tabla general del "HORARIO ESCOLAR" con columnas de lunes a viernes
    add_horario_escolar_table(doc, datos_escuela=datos_escuela)

    # 4. Tabla de metadatos del proyecto (Nombre, Campo, Duración, Metodología, Escenario, Libro, Problemática, Ejes, Propósito, Contenidos y PDA)
    add_project_metadata_table(doc, parsed_info, datos_escuela)

    # 5. Tabla de articulación curricular de los 4 Campos Formativos (Estilo Profa. Kempis - 6° Grado)
    add_articulacion_curricular_table(doc, parsed_info, datos_escuela)

    # =======================================================
    # DISTRIBUCIÓN DINÁMICA POR DÍA (for dia in dias_seleccionados:)
    # =======================================================
    dias_seleccionados = datos_escuela.get('dias_seleccionados') or datos_escuela.get('dias_planeados') or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    periodo_str = str(datos_escuela.get("periodo", "") if datos_escuela else "").lower()
    raw_text = (parsed_info.get("raw_text", "") + " " + periodo_str).lower()
    sem_val = None
    if datos_escuela and "semana" in datos_escuela:
        try:
            sem_val = int(datos_escuela["semana"])
        except Exception:
            pass
    if not sem_val:
        m_s = re.search(r'semana\s*(\d+)', periodo_str)
        if m_s:
            sem_val = int(m_s.group(1))

    es_kempis_activo = detectar_relevancia_kempis(semana=sem_val, directrices_o_texto=raw_text)
    sem_kempis = sem_val or 1

    for dia in dias_seleccionados:
        dia_idx = dias_seleccionados.index(dia)

        # 1. Asignar la rutina correspondiente al día específico
        rutina = None
        if "rutinas_por_dia" in parsed_info and dia in parsed_info["rutinas_por_dia"]:
            rutina = parsed_info["rutinas_por_dia"][dia]
        elif dia_idx < len(parsed_info.get("rutinas", [])):
            rutina = parsed_info["rutinas"][dia_idx]

        if not rutina:
            rutina = {
                "dictado": f"Palabras clave y vocabulario ortográfico para {dia}.",
                "calculo": f"Operaciones combinadas de cálculo mental para {dia}.",
                "problema": f"Problema matemático razonado contextualizado para {dia}."
            }

        # 2. Asignar la secuencia didáctica correspondiente al día específico
        sesion = None
        if "sesiones_por_dia" in parsed_info and dia in parsed_info["sesiones_por_dia"]:
            sesion = parsed_info["sesiones_por_dia"][dia]
        elif dia_idx < len(parsed_info.get("sesiones", [])):
            sesion = parsed_info["sesiones"][dia_idx]

        if not sesion:
            sesion = {
                "inicio": f"[Redactar actividades de inicio para {dia} aquí]",
                "desarrollo": f"[Redactar actividades de desarrollo para {dia} aquí]",
                "cierre": f"[Redactar actividades de cierre para {dia} aquí]",
                "recursos": "Materiales del aula y libros de texto SEP.",
                "proposito": "Fortalecer saberes comunitarios y pensamiento crítico."
            }

        # Encabezado de nivel 2 para el día
        h_dia = document.add_heading(f"Día: {dia}", level=2)
        h_dia.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if h_dia.runs:
            h_dia.runs[0].font.name = 'Arial'
            h_dia.runs[0].font.size = Pt(11)
            h_dia.runs[0].font.bold = True
            h_dia.runs[0].font.color.rgb = COLOR_MORADO_INTENSO

        # Construir tabla unificada de 5 filas y 4 columnas
        table = document.add_table(rows=5, cols=4)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        set_table_borders(table, color=HEX_BORDE_TENUE)

        # Ajuste de Columnas: configurar anchos de celda de modo que la secuencia de actividades sea la más ancha
        col_widths = [Inches(1.4), Inches(3.4), Inches(1.2), Inches(1.5)]
        for row in table.rows:
            for c_i, w in enumerate(col_widths):
                row.cells[c_i].width = w

        # 1. Fila de Título del Día: Centrada, abarcando todas las columnas (ej. "MARTES 03 DE FEBRERO DE 2026")
        # Regla 1: Encabezado principal -> Fondo Morado Intenso (#7209B7), texto Blanco, negrita y centrado
        title_cell = table.rows[0].cells[0].merge(table.rows[0].cells[3])
        title_cell.width = Inches(7.5)
        dias_fechas_map = (datos_escuela.get("dias_fechas") or {}) if isinstance(datos_escuela, dict) else {}
        title_text = dias_fechas_map.get(dia) or DIAS_FECHAS_OFICIALES.get(dia, f"{dia.upper()} DE LA SEMANA ESCOLAR")
        title_cell.text = title_text
        set_cell_background(title_cell, HEX_MORADO_INTENSO)
        set_cell_margins(title_cell, top=60, bottom=60, left=80, right=80)
        p_title = title_cell.paragraphs[0]
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p_title.runs:
            p_title.runs[0].font.name = 'Arial'
            p_title.runs[0].font.bold = True
            p_title.runs[0].font.size = Pt(11)
            p_title.runs[0].font.color.rgb = COLOR_BLANCO

        # 2. Fila de Actividades de Inicio: Con las cabeceras exactas
        # Regla 2: Subencabezados o Secciones -> Fondo Lavanda o Lila Suave (#F3E8FF), texto Morado Oscuro (#311B92), negrita
        headers_inicio = ["ACTIVIDADES DE INICIO DEL DÍA", "DICTADO", "CÁLCULO MENTAL", "PROBLEMA MATEMÁTICO"]
        for c_idx, h_txt in enumerate(headers_inicio):
            c = table.rows[1].cells[c_idx]
            c.text = h_txt
            set_cell_background(c, HEX_LILA_SUAVE)
            set_cell_margins(c, top=45, bottom=45, left=45, right=45)
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.runs:
                p.runs[0].font.name = 'Arial'
                p.runs[0].font.bold = True
                p.runs[0].font.size = Pt(8)
                p.runs[0].font.color.rgb = COLOR_MORADO_OSCURO

        # Fila 2: Llenar las celdas de inicio con la información correspondiente generada por la IA
        # Col 0: Subencabezado en Lila Suave (#F3E8FF)
        c0_rutina = table.rows[2].cells[0]
        c0_rutina.text = "RUTINA MATUTINA\nPERMANENTE"
        set_cell_background(c0_rutina, HEX_LILA_SUAVE)
        set_cell_margins(c0_rutina, top=45, bottom=45, left=45, right=45)
        p_r0 = c0_rutina.paragraphs[0]
        p_r0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if p_r0.runs:
            p_r0.runs[0].font.name = 'Arial'
            p_r0.runs[0].font.bold = True
            p_r0.runs[0].font.size = Pt(7.5)
            p_r0.runs[0].font.color.rgb = COLOR_MORADO_OSCURO

        # Cols 1, 2, 3: Regla 3 -> Celdas de contenido: Fondo completamente Blanco (#FFFFFF), texto Gris Oscuro
        contenido_inicio = [rutina.get("dictado", ""), rutina.get("calculo", ""), rutina.get("problema", "")]
        for c_idx, txt in enumerate(contenido_inicio, 1):
            c = table.rows[2].cells[c_idx]
            c.text = txt
            set_cell_background(c, HEX_BLANCO)
            set_cell_margins(c, top=45, bottom=45, left=45, right=45)
            if c.paragraphs and c.paragraphs[0].runs:
                c.paragraphs[0].runs[0].font.name = 'Arial'
                c.paragraphs[0].runs[0].font.size = Pt(7.5)
                c.paragraphs[0].runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

        # 3. Fila de Cabeceras de Secuencia: "CAMPO FORMATIVO", "SECUENCIA DE ACTIVIDADES", etc.
        # Regla 1: Encabezados principales -> Fondo Morado Intenso (#7209B7), texto Blanco, negrita y centrado
        headers_secuencia = ["CAMPO FORMATIVO", "SECUENCIA DE ACTIVIDADES", "RECURSOS DIDÁCTICOS", "EVALUACIÓN"]
        for c_idx, h_txt in enumerate(headers_secuencia):
            c = table.rows[3].cells[c_idx]
            c.text = h_txt
            set_cell_background(c, HEX_MORADO_INTENSO)
            set_cell_margins(c, top=45, bottom=45, left=45, right=45)
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.runs:
                p.runs[0].font.name = 'Arial'
                p.runs[0].font.bold = True
                p.runs[0].font.size = Pt(8)
                p.runs[0].font.color.rgb = COLOR_BLANCO

        # 4. Filas de Campos Formativos: Por cada campo, coloca su nombre en la 1ra col,
        # y en la 2da divide claramente los momentos de "Inicio:", "Desarrollo:" y "Cierre:"
        campo_nombre = parsed_info.get("campo_formativo", "Lenguajes")
        if datos_escuela and "campos_formativos" in datos_escuela and datos_escuela["campos_formativos"]:
            if isinstance(datos_escuela["campos_formativos"], list):
                campo_nombre = ", ".join(datos_escuela["campos_formativos"])
            else:
                campo_nombre = str(datos_escuela["campos_formativos"])

        proposito_sesion = sesion.get("proposito") or parsed_info.get("proposito", "Fortalecer saberes de la comunidad y pensamiento crítico.")

        # Col 0: Subencabezado / Sección -> Fondo Lavanda o Lila Suave (#F3E8FF)
        c_campo = table.rows[4].cells[0]
        c_campo.text = f"{campo_nombre.upper()}\n\nSESIÓN {sesion.get('sesion', '1')}\n\nPropósito de la sesión:\n{proposito_sesion}"
        set_cell_background(c_campo, HEX_LILA_SUAVE)
        set_cell_margins(c_campo, top=45, bottom=45, left=45, right=45)
        if c_campo.paragraphs and c_campo.paragraphs[0].runs:
            c_campo.paragraphs[0].runs[0].font.name = 'Arial'
            c_campo.paragraphs[0].runs[0].font.size = Pt(7.5)
            c_campo.paragraphs[0].runs[0].font.bold = True
            c_campo.paragraphs[0].runs[0].font.color.rgb = COLOR_MORADO_OSCURO

        # Col 1: Regla 3 -> Celda de contenido con fondo completamente Blanco (#FFFFFF)
        # Subsecciones Inicio, Desarrollo, Cierre resaltadas en Morado Oscuro
        c_seq = table.rows[4].cells[1]
        c_seq.text = f"Inicio:\n{sesion['inicio']}\n\nDesarrollo:\n{sesion['desarrollo']}\n\nCierre:\n{sesion['cierre']}"
        set_cell_background(c_seq, HEX_BLANCO)
        set_cell_margins(c_seq, top=45, bottom=45, left=50, right=50)
        for p in c_seq.paragraphs:
            if p.runs:
                p.runs[0].font.name = 'Arial'
                p.runs[0].font.size = Pt(7.5)
                p.runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

        # Col 2: Recursos didácticos -> Celda de contenido con fondo completamente Blanco (#FFFFFF)
        c_rec = table.rows[4].cells[2]
        rec_txt = str(sesion.get('recursos', 'Cuaderno del alumno, anexos y libros de texto SEP.'))
        if es_kempis_activo and "kempis" not in rec_txt.lower():
            rec_txt += f"\n\n• Cuadernillo Profa Kempis (Semana {sem_kempis}) y fichas imprimibles de trabajo."
        c_rec.text = rec_txt
        set_cell_background(c_rec, HEX_BLANCO)
        set_cell_margins(c_rec, top=45, bottom=45, left=45, right=45)
        if c_rec.paragraphs and c_rec.paragraphs[0].runs:
            c_rec.paragraphs[0].runs[0].font.name = 'Arial'
            c_rec.paragraphs[0].runs[0].font.size = Pt(7.5)
            c_rec.paragraphs[0].runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

        # Col 3: Evaluación formativa -> Celda de contenido con fondo completamente Blanco (#FFFFFF)
        c_eva = table.rows[4].cells[3]
        c_eva.text = "Listas de cotejo, observación directa, registro en diario de campo y producciones en el cuaderno."
        set_cell_background(c_eva, HEX_BLANCO)
        set_cell_margins(c_eva, top=45, bottom=45, left=45, right=45)
        if c_eva.paragraphs and c_eva.paragraphs[0].runs:
            c_eva.paragraphs[0].runs[0].font.name = 'Arial'
            c_eva.paragraphs[0].runs[0].font.size = Pt(7.5)
            c_eva.paragraphs[0].runs[0].font.color.rgb = COLOR_TEXTO_OSCURO

        document.add_paragraph()

    # 6. Tabla de Evaluación Formativa e Instrumentos con criterios específicos (Estilo Profa. Kempis - 6° Grado)
    add_evaluacion_formativa_table(doc, parsed_info, datos_escuela)

    # 7. Ajustes Razonables (DUA) y Observaciones Docentes
    add_ajustes_razonables_table(doc, parsed_info, datos_escuela)

    # 8. Integración del Cuadernillo de Actividades y Anexos Imprimibles (Profa Kempis)
    add_cuadernillo_kempis_section(doc, parsed_info, datos_escuela)

    add_document_credits(doc)


    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# Alias para compatibilidad de interfaz
generate_docx_planeacion = build_docx_planeacion


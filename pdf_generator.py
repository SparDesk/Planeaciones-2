from __future__ import annotations

"""
Generador de documentos oficiales en formato PDF (.pdf)
para las planeaciones escolares de la Primaria Revolución Social 1910
siguiendo las directrices estéticas de la SEP y el modelo de la NEM.
Utiliza fpdf2 en modo compatible y universal (sin dependencias externas).
"""

import io
from typing import Dict, Any
from fpdf import FPDF
from docx_generator import parse_plan_sections

# Paleta de colores institucionales SEP
RGB_SEP_GUINDA = (105, 28, 50)     # #691C32
RGB_SEP_DORADO = (188, 149, 91)    # #BC955B
RGB_GRIS_FONDO = (245, 247, 250)   # #F5F7FA
RGB_TEXTO_OSCURO = (30, 41, 59)    # #1E293B
RGB_BLANCO = (255, 255, 255)
RGB_LINEA = (203, 213, 225)        # #CBD5E1

def sanitize_latin1(text: str) -> str:
    """Reemplaza caracteres tipográficos para compatibilidad total con fuentes PDF core."""
    if not text:
        return ""
    replacements = {
        '\u2014': '-',
        '\u2013': '-',
        '\u201c': '"',
        '\u201d': '"',
        '\u2018': "'",
        '\u2019': "'",
        '\u2022': '*',
        '\u2026': '...',
        '\xa0': ' '
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

class PlaneacionPDF(FPDF):
    def __init__(self, datos_escuela: Dict[str, Any]):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.datos_escuela = datos_escuela
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(12, 12, 12)

    def header(self):
        if self.page_no() == 1:
            # Encabezado institucional en la primera página
            self.set_fill_color(*RGB_SEP_GUINDA)
            self.rect(12, 10, 186, 1.5, 'F')
            
            self.set_font('Helvetica', 'B', 8)
            self.set_text_color(*RGB_SEP_DORADO)
            self.cell(0, 5, sanitize_latin1("SECRETARÍA DE EDUCACIÓN PÚBLICA — SUBSECRETARÍA DE EDUCACIÓN BÁSICA"), new_x='LMARGIN', new_y='NEXT', align='C')
            
            self.set_font('Helvetica', 'B', 13)
            self.set_text_color(*RGB_SEP_GUINDA)
            escuela = self.datos_escuela.get('nombre_escuela', 'Escuela Primaria “Revolución Social de 1910”').upper()
            self.cell(0, 7, sanitize_latin1(escuela), new_x='LMARGIN', new_y='NEXT', align='C')
            
            self.set_font('Helvetica', 'B', 9.5)
            self.set_text_color(*RGB_TEXTO_OSCURO)
            cct = self.datos_escuela.get('cct', '10EPR0361N')
            zona = self.datos_escuela.get('zona_escolar', 'Zona 49')
            sector = self.datos_escuela.get('sector', 'Sector 02')
            grado = self.datos_escuela.get('grado', '6° de Primaria')
            grupo = self.datos_escuela.get('grupo', 'A')
            fase = self.datos_escuela.get('fase', 'Fase 5')
            periodo = self.datos_escuela.get('periodo') or f"Semana {self.datos_escuela.get('semana', 1)} de 37"
            ciclo = self.datos_escuela.get('ciclo_escolar', '2026-2027')
            self.cell(0, 5, sanitize_latin1(f"C.C.T. {cct} | {zona} | {sector} | {grado} '{grupo}' ({fase}) | {periodo} | CICLO ESCOLAR {ciclo}"), new_x='LMARGIN', new_y='NEXT', align='C')
            
            self.set_font('Helvetica', '', 8.5)
            docente = self.datos_escuela.get('docente', 'Maestra Aday Domínguez Domínguez')
            director = self.datos_escuela.get('director', 'Guillermo Gerardo Borjas Díaz')
            self.cell(0, 5, sanitize_latin1(f"Docente Titular: Prof(a). {docente}   |   Director: Prof. {director}"), new_x='LMARGIN', new_y='NEXT', align='C')
            
            if self.datos_escuela.get('modo_base_estricta') and self.datos_escuela.get('archivo_base_estricta'):
                arch_est = self.datos_escuela.get('archivo_base_estricta')
                tipo_est = self.datos_escuela.get('tipo_base_estricta') or "Programa Analítico/Sintético"
                self.set_fill_color(236, 253, 245)
                self.set_draw_color(16, 185, 129)
                self.set_font('Helvetica', 'B', 7.5)
                self.set_text_color(6, 95, 70)
                self.cell(0, 4.5, sanitize_latin1(f"[BASE ESTRICTA VINCULADA: {arch_est} ({tipo_est}) - PRIORIDAD ABSOLUTA]"), border=1, fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
            
            self.set_fill_color(*RGB_SEP_DORADO)
            self.rect(12, self.get_y() + 1, 186, 0.8, 'F')
            self.ln(3)
        else:
            # Encabezado compacto en páginas secundarias
            self.set_font('Helvetica', 'I', 7.5)
            self.set_text_color(100, 116, 139)
            escuela = self.datos_escuela.get('nombre_escuela', 'Escuela Primaria “Revolución Social de 1910”')
            periodo = self.datos_escuela.get('periodo') or f"Semana {self.datos_escuela.get('semana', 1)} de 37"
            self.cell(0, 5, sanitize_latin1(f"{escuela} — Plano Didáctico ({periodo}) — Nueva Escuela Mexicana"), new_x='LMARGIN', new_y='NEXT', align='L')
            self.line(12, self.get_y(), 198, self.get_y())
            self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 7.5)
        self.set_text_color(148, 163, 184)
        self.cell(0, 8, sanitize_latin1(f"Desarrollado para la labor pedagógica   •   Página {self.page_no()}/{{nb}}"), align='C')

def build_pdf_planeacion(datos_escuela: Dict[str, Any], plan_text: str) -> io.BytesIO:
    """
    Construye un archivo PDF profesional y completo con la planeación de la Primaria Revolución Social 1910.
    """
    pdf = PlaneacionPDF(datos_escuela)
    pdf.alias_nb_pages()
    pdf.add_page()

    if datos_escuela.get('modo_base_estricta') and datos_escuela.get('archivo_base_estricta'):
        arch_est = datos_escuela.get('archivo_base_estricta')
        tipo_est = datos_escuela.get('tipo_base_estricta') or "Programa Analítico/Sintético"
        pdf.set_fill_color(236, 253, 245)
        pdf.set_draw_color(16, 185, 129)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(6, 95, 70)
        pdf.cell(186, 5, sanitize_latin1(f"VALIDACION DE BASE ESTRICTA: {arch_est} ({tipo_est}) | PRIORIDAD ABSOLUTA"), border=1, fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(1)

    # ==========================================
    # 1. TABLA DE HORARIO ESCOLAR SEMANAL
    # ==========================================
    pdf.set_fill_color(*RGB_SEP_GUINDA)
    pdf.set_text_color(*RGB_BLANCO)
    fase = datos_escuela.get('fase', 'Fase 5')
    grado = datos_escuela.get('grado', '6° de Primaria')
    pdf.cell(186, 6, sanitize_latin1(f"HORARIO ESCOLAR SEMANAL ({fase.upper()} — {grado.upper()})"), border=1, new_x='LMARGIN', new_y='NEXT', align='C', fill=True)

    dias_sel = datos_escuela.get('dias_seleccionados') or datos_escuela.get('dias_planeados') or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    dias_header = ["Horario"] + [d.capitalize() for d in dias_sel]
    num_cols = len(dias_header)
    col_w_horario = 26
    col_w_dia = (186 - col_w_horario) / (num_cols - 1) if num_cols > 1 else 160
    col_widths_h = [col_w_horario] + [col_w_dia] * (num_cols - 1)
    
    pdf.set_fill_color(*RGB_SEP_DORADO)
    pdf.set_font('Helvetica', 'B', 7.5)
    for w, d in zip(col_widths_h, dias_header):
        pdf.cell(w, 5, sanitize_latin1(d), border=1, fill=True, align='C')
    pdf.ln()

    raw_schedule = [
        ("08:00 - 08:30", {"Lunes": "Act. de Inicio", "Martes": "Act. de Inicio", "Miércoles": "Act. de Inicio", "Jueves": "Act. de Inicio", "Viernes": "Act. de Inicio"}),
        ("08:30 - 10:00", {"Lunes": "Lenguajes", "Martes": "Lenguajes", "Miércoles": "Lenguajes", "Jueves": "Lenguajes", "Viernes": "Lenguajes"}),
        ("10:00 - 10:30", {"Lunes": "RECESO", "Martes": "RECESO", "Miércoles": "RECESO", "Jueves": "RECESO", "Viernes": "RECESO"}),
        ("10:30 - 11:30", {"Lunes": "Pensamiento C.", "Martes": "Pensamiento C.", "Miércoles": "Pensamiento C.", "Jueves": "Pensamiento C.", "Viernes": "Pensamiento C."}),
        ("11:30 - 12:15", {"Lunes": "Ética, Nat. y Soc.", "Martes": "Ética, Nat. y Soc.", "Miércoles": "Ética, Nat. y Soc.", "Jueves": "Ética, Nat. y Soc.", "Viernes": "Ética, Nat. y Soc."}),
        ("12:15 - 13:00", {"Lunes": "De lo Humano", "Martes": "Ed. Física", "Miércoles": "De lo Humano", "Jueves": "Artes", "Viernes": "De lo Humano"})
    ]

    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(*RGB_TEXTO_OSCURO)
    for r_idx, (hora, materias_map) in enumerate(raw_schedule):
        fill_bg = (r_idx % 2 == 1)
        if fill_bg:
            pdf.set_fill_color(*RGB_GRIS_FONDO)
        else:
            pdf.set_fill_color(*RGB_BLANCO)
            
        h_row = [hora] + [materias_map.get(d.capitalize(), "Lenguajes") for d in dias_sel]
        for w, val in zip(col_widths_h, h_row):
            if val == "RECESO":
                pdf.set_font('Helvetica', 'B', 7)
                pdf.set_text_color(*RGB_SEP_GUINDA)
            else:
                pdf.set_font('Helvetica', '', 7)
                pdf.set_text_color(*RGB_TEXTO_OSCURO)
            pdf.cell(w, 4.5, sanitize_latin1(val), border=1, fill=True, align='C')
        pdf.ln()

    pdf.ln(4)

    # ==========================================
    # 2. CUERPO DE LA PLANEACIÓN (TEXTO / TABLAS)
    # ==========================================
    lines = plan_text.split("\n")
    in_table = False
    table_rows = []

    def render_pdf_table(rows):
        if not rows:
            return
        parsed = []
        for r in rows:
            if set(r.strip()) <= {'|', '-', ' ', ':'}:
                continue
            cells = [c.strip() for c in r.strip().strip('|').split('|')]
            if cells:
                parsed.append(cells)
        if not parsed:
            return

        num_cols = max(len(row) for row in parsed)
        col_width = 186 / num_cols
        
        for r_i, r_data in enumerate(parsed):
            is_head = (r_i == 0)
            if is_head:
                pdf.set_fill_color(*RGB_SEP_GUINDA)
                pdf.set_text_color(*RGB_BLANCO)
                pdf.set_font('Helvetica', 'B', 7.5)
            else:
                pdf.set_text_color(*RGB_TEXTO_OSCURO)
                pdf.set_font('Helvetica', '', 7)
                if r_i % 2 == 1:
                    pdf.set_fill_color(*RGB_BLANCO)
                else:
                    pdf.set_fill_color(*RGB_GRIS_FONDO)

            # Calcular altura requerida para la fila
            y_before = pdf.get_y()
            if y_before > 260:
                pdf.add_page()

            for c_i in range(num_cols):
                val = r_data[c_i] if c_i < len(r_data) else ""
                # Si es celda muy larga, usar multi_cell o recortar adecuadamente
                val_clean = sanitize_latin1(val)
                pdf.cell(col_width, 5.5, val_clean[:65], border=1, fill=True)
            pdf.ln()
        pdf.ln(2)

    parsed_info = parse_plan_sections(plan_text)
    dias_seleccionados = datos_escuela.get('dias_seleccionados') or datos_escuela.get('dias_planeados') or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    in_secuencia_iv = False

    for line in lines:
        stripped = line.strip()

        # Detección de tablas markdown
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_rows.append(stripped)
            continue
        else:
            if in_table:
                render_pdf_table(table_rows)
                table_rows = []
                in_table = False

        if not stripped:
            continue

        if in_secuencia_iv:
            if stripped.startswith("# ") and not (stripped.startswith("# IV.") or stripped.startswith("# IV ")):
                in_secuencia_iv = False
            else:
                continue

        # Sección IV: Secuencia Didáctica separada por días
        if stripped.startswith("# IV.") or stripped.startswith("# IV "):
            if in_table:
                render_pdf_table(table_rows)
                table_rows = []
                in_table = False

            # Encabezado de la Sección IV
            pdf.ln(3)
            pdf.set_fill_color(*RGB_SEP_GUINDA)
            pdf.set_text_color(*RGB_BLANCO)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(186, 6.5, sanitize_latin1("IV. SECUENCIA DIDÁCTICA DETALLADA (PLANO DIDÁCTICO POR DÍAS)"), border=0, fill=True, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(1.5)

            # Bucle for dia in dias_seleccionados
            for dia_idx, dia in enumerate(dias_seleccionados):
                rutina = None
                if "rutinas_por_dia" in parsed_info and dia in parsed_info["rutinas_por_dia"]:
                    rutina = parsed_info["rutinas_por_dia"][dia]
                elif dia_idx < len(parsed_info.get("rutinas", [])):
                    rutina = parsed_info["rutinas"][dia_idx]

                if not rutina:
                    rutina = {
                        "dictado": f"Palabras clave para {dia}.",
                        "calculo": f"Cálculo mental para {dia}.",
                        "problema": f"Problema razonado para {dia}."
                    }

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
                        "recursos": "Materiales del aula y libros de texto SEP."
                    }

                # Subtítulo o encabezado que indique el día (ejemplo: "**Día: Lunes**")
                pdf.ln(2)
                if pdf.get_y() > 235:
                    pdf.add_page()
                pdf.set_font('Helvetica', 'B', 9)
                dias_fechas_map = (datos_escuela.get("dias_fechas") or {}) if isinstance(datos_escuela, dict) else {}
                dia_label = dias_fechas_map.get(dia, dia)
                pdf.cell(186, 6, sanitize_latin1(f"**Día: {dia_label}**"), border=0, new_x='LMARGIN', new_y='NEXT')
                pdf.ln(1)

                # Tabla correspondiente con las celdas de Inicio, Desarrollo y Cierre exclusivas para ese día
                pdf.set_font('Helvetica', '', 7.5)
                pdf.set_text_color(*RGB_TEXTO_OSCURO)
                with pdf.table(col_widths=(28, 102, 28, 28), text_align=('CENTER', 'LEFT', 'LEFT', 'LEFT')) as table:
                    h_row = table.row()
                    for h_text in ["MOMENTO", "SECUENCIA DE ACTIVIDADES", "RECURSOS", "EVALUACION"]:
                        h_row.cell(h_text)

                    r_ini = table.row()
                    r_ini.cell("INICIO\n(15-20 min)")
                    r_ini.cell(sanitize_latin1(sesion.get("inicio", "[Actividades de inicio]")))
                    r_ini.cell("Preguntas detonadoras y saberes previos.")
                    r_ini.cell("Diagnostica / Observacion.")

                    r_des = table.row()
                    r_des.cell("DESARROLLO\n(50-60 min)")
                    r_des.cell(sanitize_latin1(sesion.get("desarrollo", "[Actividades de desarrollo]")))
                    r_des.cell(sanitize_latin1(sesion.get("recursos", "Libros SEP y cuaderno.")))
                    r_des.cell("Formativa / Producciones.")

                    r_cie = table.row()
                    r_cie.cell("CIERRE\n(15-20 min)")
                    r_cie.cell(sanitize_latin1(sesion.get("cierre", "[Actividades de cierre]")))
                    r_cie.cell("Cuaderno del alumno y plenaria.")
                    r_cie.cell("Formativa / Metacognicion.")
                pdf.ln(2)

            in_secuencia_iv = True
            continue

        # Encabezados
        if stripped.startswith("# "):
            pdf.ln(3)
            pdf.set_fill_color(*RGB_SEP_GUINDA)
            pdf.set_text_color(*RGB_BLANCO)
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(186, 6.5, sanitize_latin1(stripped[2:]), border=0, fill=True, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(1.5)
        elif stripped.startswith("## "):
            pdf.ln(2)
            pdf.set_text_color(*RGB_SEP_GUINDA)
            pdf.set_font('Helvetica', 'B', 8.5)
            pdf.cell(186, 5.5, sanitize_latin1(stripped[3:]), new_x='LMARGIN', new_y='NEXT')
            pdf.ln(1)
        elif stripped.startswith("### "):
            pdf.ln(1.5)
            pdf.set_text_color(*RGB_SEP_DORADO)
            pdf.set_font('Helvetica', 'B', 8)
            pdf.cell(186, 5, sanitize_latin1(stripped[4:]), new_x='LMARGIN', new_y='NEXT')
            pdf.ln(1)
        elif stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_text_color(*RGB_TEXTO_OSCURO)
            pdf.set_font('Helvetica', '', 7.5)
            clean_text = sanitize_latin1("•  " + stripped[2:].replace("**", ""))
            pdf.multi_cell(186, 4, clean_text)
        else:
            pdf.set_text_color(*RGB_TEXTO_OSCURO)
            pdf.set_font('Helvetica', '', 7.5)
            clean_text = sanitize_latin1(stripped.replace("**", ""))
            pdf.multi_cell(186, 4, clean_text)

    if in_table:
        render_pdf_table(table_rows)

    # ==========================================
    # 3. FIRMAS INSTITUCIONALES AL PIE
    # ==========================================
    pdf.ln(8)
    if pdf.get_y() > 245:
        pdf.add_page()

    y_firmas = pdf.get_y()
    pdf.set_draw_color(*RGB_TEXTO_OSCURO)
    pdf.line(25, y_firmas + 10, 85, y_firmas + 10)
    pdf.line(125, y_firmas + 10, 185, y_firmas + 10)

    pdf.set_y(y_firmas + 11)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(*RGB_SEP_GUINDA)
    docente = datos_escuela.get('docente', 'Maestra Aday Domínguez Domínguez')
    director = datos_escuela.get('director', 'Guillermo Gerardo Borjas Díaz')
    
    pdf.cell(93, 4, sanitize_latin1(f"Prof(a). {docente}"), align='C')
    pdf.cell(93, 4, sanitize_latin1(f"Prof. {director}"), align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(*RGB_TEXTO_OSCURO)
    pdf.cell(93, 4, sanitize_latin1("DOCENTE TITULAR DE GRUPO"), align='C')
    pdf.cell(93, 4, sanitize_latin1("DIRECTOR ESCOLAR"), align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(5)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(186, 5, sanitize_latin1("Desarrollado para la labor pedagógica"), align='C')

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf

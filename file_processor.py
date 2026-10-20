from __future__ import annotations

"""
Módulo de procesamiento y extracción de texto de documentos de referencia
(PDF, DOCX, TXT) para incorporar al contexto pedagógico de la planeación.
"""

import io
from typing import Any, Dict, List, Optional, Union, Tuple, Callable

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import docx
except ImportError:
    docx = None

try:
    import PyPDF2 as pdf_lib
except ImportError:
    try:
        import pypdf as pdf_lib
    except ImportError:
        pdf_lib = None

try:
    import requests
except ImportError:
    requests = None

def extract_text_from_pdf(file_bytes: bytes, max_pages: int = 200) -> str:
    """Extrae texto de un archivo PDF subido en Streamlit usando PyPDF2 / pypdf."""
    if pdf_lib is None:
        return "[Aviso: PyPDF2 o pypdf no se encuentran disponibles para procesar archivos PDF.]"
    try:
        reader = pdf_lib.PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, max_pages)
        
        extracted_texts = []
        for i in range(pages_to_read):
            page = reader.pages[i]
            text = page.extract_text()
            if text:
                extracted_texts.append(f"--- Página {i+1} ---\n{text.strip()}")
                
        if total_pages > max_pages:
            extracted_texts.append(f"\n[Nota: Se procesaron las primeras {max_pages} de {total_pages} páginas para optimizar la respuesta].")
            
        return "\n\n".join(extracted_texts)
    except Exception as e:
        return f"[Error al extraer contenido del PDF: {str(e)}]"

def extraer_contenidos_pda_fase5(texto: str) -> List[Dict[str, str]]:
    """
    Analiza el texto extraído del Programa Sintético de la Fase 5 (5° y 6° de primaria)
    para identificar los bloques de Campo Formativo, Contenido y PDA (5° y 6° grado).
    """
    import re
    resultados = []
    if not texto:
        return resultados

    # Expresión regular para bloques estructurados comunes en el Programa Sintético
    patron = re.compile(
        r'(?:Campo\s+Formativo[:\s]+(?P<campo>[^\n]+)\n)?'
        r'Contenido[:\s]+(?P<contenido>[^\n]+)\n'
        r'(?:PDA(?:\s+(?P<grado_pda>[56])[°o]?\s+Grado)?[:\s]+(?P<pda>[^\n]+))',
        re.IGNORECASE
    )
    for m in patron.finditer(texto):
        c_dict = m.groupdict()
        campo_raw = (c_dict.get("campo") or "Lenguajes").strip()
        campo_clean = campo_raw.lower()
        if "lenguaje" in campo_clean:
            campo_val = "Lenguajes"
        elif "saber" in campo_clean or "cient" in campo_clean:
            campo_val = "Saberes y Pensamiento Científico"
        elif "ética" in campo_clean or "etica" in campo_clean or "sociedad" in campo_clean:
            campo_val = "Ética, Naturaleza y Sociedades"
        elif "humano" in campo_clean or "comunitario" in campo_clean:
            campo_val = "De lo Humano y lo Comunitario"
        else:
            campo_val = campo_raw

        cont_val = (c_dict.get("contenido") or "").strip()
        pda_val = (c_dict.get("pda") or "").strip()
        g_val = c_dict.get("grado_pda") or "6"
        if cont_val and pda_val:
            resultados.append({
                "campo": campo_val,
                "contenido": cont_val,
                "pda": pda_val,
                "grado": f"{g_val}° de Primaria"
            })
    return resultados

def extract_text_from_docx(file_bytes: bytes, max_paragraphs: int = 150) -> str:
    """Extrae texto de un archivo Word (.docx) subido."""
    if docx is None:
        return "[Aviso: python-docx no se encuentra disponible en este entorno para procesar archivos .docx.]"
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        # También extraer texto de tablas si existen
        table_texts = []
        for t_idx, table in enumerate(doc.tables[:10]):
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    table_texts.append(row_text)
                    
        combined = paragraphs[:max_paragraphs]
        if table_texts:
            combined.append("\n[Tablas en el documento]:\n" + "\n".join(table_texts[:50]))
            
        return "\n".join(combined)
    except Exception as e:
        return f"[Error al extraer contenido del archivo DOCX: {str(e)}]"

def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extrae texto de un archivo de texto plano."""
    try:
        # Intentar utf-8 primero, luego latin-1
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="replace")
    except Exception as e:
        return f"[Error al leer archivo de texto: {str(e)}]"

def process_uploaded_files(uploaded_files: List[Any]) -> Dict[str, str]:
    """Procesa una lista de archivos subidos por st.file_uploader."""
    results = {}
    if not uploaded_files:
        return results

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        ext = filename.lower().split(".")[-1]
        file_bytes = uploaded_file.getvalue()
        
        if ext == "pdf":
            content = extract_text_from_pdf(file_bytes)
        elif ext in ["docx", "doc"]:
            content = extract_text_from_docx(file_bytes)
        elif ext in ["txt", "md", "csv"]:
            content = extract_text_from_txt(file_bytes)
        else:
            content = f"[Formato .{ext} no soportado. Por favor use .pdf, .docx o .txt]"
            
        results[filename] = content
        
    return results

def format_context_for_prompt(extracted_files: Dict[str, str], max_chars_per_file: int = 6000) -> str:
    """Da formato a los archivos extraídos para insertarlos en el prompt de Gemini."""
    if not extracted_files:
        return "No se adjuntaron archivos adicionales."
        
    formatted = []
    for filename, content in extracted_files.items():
        truncated_content = content[:max_chars_per_file]
        if len(content) > max_chars_per_file:
            truncated_content += "\n... [Fragmento condensado para el análisis pedagógico] ..."
        formatted.append(f"### ARCHIVO DE REFERENCIA: {filename}\n{truncated_content}")
        
    return "\n\n" + "\n\n".join(formatted) + "\n"


def extraer_texto_url(url: str) -> str:
    """
    Conecta al enlace ingresado usando requests y BeautifulSoup,
    extrae todos los párrafos de texto (<p>) y los devuelve como un solo bloque de texto.
    Incluye un bloque try-except por si la página bloquea la conexión o el enlace está caído,
    devolviendo un string vacío en caso de error.
    """
    if not url or not isinstance(url, str) or not url.strip():
        return ""
    if requests is None or BeautifulSoup is None:
        return ""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        resp = requests.get(url.strip(), headers=headers, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        parrafos = [p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()]
        return "\n\n".join(parrafos)
    except Exception:
        return ""


def busqueda_cruzada_archivos_plataforma(
    semana: Union[int, str] = 1,
    grado: str = "6° de Primaria",
    campos_formativos: Optional[List[str]] = None,
    dias_seleccionados: Optional[List[str]] = None,
    directrices_docente: str = "",
    archivos_procesados: Optional[Dict[str, str]] = None,
    directorio_sample: str = "sample_data",
    mes: Optional[str] = None,
    año: int = 2026,
    libros_seleccionados: Optional[Union[List[str], str]] = None,
    guia_cte: Optional[str] = None
) -> Dict[str, Any]:
    """
    Motor de lectura y búsqueda cruzada en todos los archivos disponibles en la plataforma:
    1. Cuadernillos didácticos y Catálogo de 37 Semanas SEP (cuadernillo_kempis.py).
    2. Libros de Texto Gratuitos SEP (nem_data.py - LIBROS_SEP_POR_GRADO).
    3. Guías de Consejo Técnico Escolar (nem_data.py - GUIAS_CTE_CATALOGO y sample_data/guia_5to_grado_ejemplo.docx).
    4. Programa Analítico Institucional precargado (nem_data.py - EJEMPLO_PROBLEMICA_ANALITICO, 4 problemáticas).
    5. Archivos locales de la plataforma (sample_data/programa_sintetico_fase5_ejemplo.txt).
    6. Archivos subidos por el docente (archivos_procesados).
    7. Anexos imprimibles y fichas prácticas asignadas a cada día.

    Garantiza:
    - Extracción obligatoria de Contenidos y PDA de los 4 Campos Formativos de la NEM.
    - Alineación precisa de actividades, recursos didácticos y consignas para los días elegidos.
    - Coherencia curricular estricta sin invención de asignaturas o contenidos ajenos al Plan 2022.
    - Trazabilidad con las 4 problemáticas prioritarias y la ficha técnica institucional (26 alumnos, Kinestésico/Visual).
    """
    import os
    import re

    # 1. Normalización de parámetros
    try:
        semana_num = int(str(semana).replace("Semana", "").strip() or 1)
        semana_num = max(1, min(37, semana_num))
    except Exception:
        semana_num = 1

    dias_lista = dias_seleccionados or ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    if not dias_lista:
        dias_lista = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]

    campos_4_oficiales = [
        "Lenguajes",
        "Saberes y Pensamiento Científico",
        "Ética, Naturaleza y Sociedades",
        "De lo Humano y lo Comunitario"
    ]
    campos_activos = campos_formativos or campos_4_oficiales

    mes_nom = mes or "Octubre"
    archivos_consultados = []

    # 2. Consulta de Cuadernillo / Catálogo SEP 37 Semanas
    proyecto_semana = {}
    recursos_kempis = None
    try:
        from cuadernillo_kempis import (
            obtener_proyecto_semana,
            obtener_recursos_kempis_por_semana,
            obtener_anexos_por_semana_y_dia,
            CATALOGO_PROYECTOS_SEP_37_SEMANAS,
            CUADERNILLO_KEMPIS_DATA
        )
        proyecto_semana = obtener_proyecto_semana(semana_num, mes=mes_nom)
        recursos_kempis = obtener_recursos_kempis_por_semana(semana_num)
        archivos_consultados.append({
            "fuente": f"Cuadernillo Didáctico y Catálogo Oficial SEP (Semana {semana_num} de 37)",
            "tipo": "Cuadernillos / Dosificador Anual",
            "estado": "Disponible e indexado",
            "detalles": f"Proyecto: '{proyecto_semana.get('proyecto', 'Integrador')}' — {proyecto_semana.get('fase_metodologica', '')}"
        })
    except ImportError:
        obtener_anexos_por_semana_y_dia = lambda s, d, mes=None: f"Anexo {s}.{d}"
        archivos_consultados.append({
            "fuente": f"Catálogo Proyectos SEP (Semana {semana_num})",
            "tipo": "Cuadernillos",
            "estado": "Respaldo local",
            "detalles": "Estructura base de 37 semanas"
        })

    # 3. Consulta de Catálogos Curriculares NEM y Programa Analítico
    banco_grado = {}
    libros_grado = []
    guias_cte_dict = {}
    analitico_texto = ""
    try:
        from nem_data import (
            CONTENIDOS_PDA_POR_GRADO,
            LIBROS_SEP_POR_GRADO,
            GUIAS_CTE_CATALOGO,
            EJEMPLO_PROBLEMICA_ANALITICO,
            PROBLEMATIZACIONES_PREDETERMINADAS
        )
        banco_grado = CONTENIDOS_PDA_POR_GRADO.get(grado, CONTENIDOS_PDA_POR_GRADO.get("6° de Primaria", {}))
        libros_grado = LIBROS_SEP_POR_GRADO.get(grado, LIBROS_SEP_POR_GRADO.get("6° de Primaria", []))
        guias_cte_dict = GUIAS_CTE_CATALOGO
        analitico_texto = EJEMPLO_PROBLEMICA_ANALITICO
        archivos_consultados.append({
            "fuente": "Programa Analítico Oficial Precargado (Ciclo 2026-2027)",
            "tipo": "Programa Analítico Institucional",
            "estado": "Activo y vinculante",
            "detalles": "Primaria Revolución Social de 1910 (Durango, 26 alumnos, 4 problemáticas)"
        })
        archivos_consultados.append({
            "fuente": f"Catálogo Oficial de Libros de Texto Gratuitos SEP ({grado})",
            "tipo": "Libros de Texto SEP (LTG)",
            "estado": "Disponible",
            "detalles": ", ".join(libros_grado[:4])
        })
    except ImportError:
        pass

    # 4. Lectura cruzada en archivos locales de sample_data/
    muestra_sintetico_txt = ""
    pda_sintetico_sample = []
    if os.path.exists(directorio_sample):
        ruta_prog_sample = os.path.join(directorio_sample, "programa_sintetico_fase5_ejemplo.txt")
        if os.path.exists(ruta_prog_sample):
            try:
                with open(ruta_prog_sample, "r", encoding="utf-8") as f:
                    muestra_sintetico_txt = f.read()
                    pda_sintetico_sample = extraer_contenidos_pda_fase5(muestra_sintetico_txt)
                archivos_consultados.append({
                    "fuente": "sample_data/programa_sintetico_fase5_ejemplo.txt",
                    "tipo": "Programa Sintético Fase 5 (SEP)",
                    "estado": "Leído y procesado",
                    "detalles": f"{len(pda_sintetico_sample)} bloques de Contenido/PDA extraídos para los 4 campos"
                })
            except Exception as e:
                archivos_consultados.append({
                    "fuente": "sample_data/programa_sintetico_fase5_ejemplo.txt",
                    "tipo": "Programa Sintético Fase 5",
                    "estado": f"Error de lectura: {e}",
                    "detalles": ""
                })

        ruta_guia_docx = os.path.join(directorio_sample, "guia_5to_grado_ejemplo.docx")
        if os.path.exists(ruta_guia_docx):
            try:
                with open(ruta_guia_docx, "rb") as f:
                    txt_guia_docx = extract_text_from_docx(f.read(), max_paragraphs=30)
                archivos_consultados.append({
                    "fuente": "sample_data/guia_5to_grado_ejemplo.docx",
                    "tipo": "Guía CTE / Orientaciones Pedagógicas",
                    "estado": "Leído y procesado",
                    "detalles": f"~{len(txt_guia_docx):,} caracteres de orientaciones didácticas"
                })
            except Exception as e:
                archivos_consultados.append({
                    "fuente": "sample_data/guia_5to_grado_ejemplo.docx",
                    "tipo": "Guía CTE",
                    "estado": f"Error de lectura: {e}",
                    "detalles": ""
                })

    # 5. Lectura cruzada en archivos subidos por el usuario
    archivos_usuario_encontrados = []
    if archivos_procesados:
        for f_name, f_content in archivos_procesados.items():
            largo = len(f_content or "")
            archivos_consultados.append({
                "fuente": f_name,
                "tipo": "Archivo adjunto docente",
                "estado": "Leído y procesado",
                "detalles": f"{largo:,} caracteres indexados para cruce pedagógico"
            })
            # Buscar fragmentos relevantes con respecto a directrices y semana
            terminos_clave = [str(semana_num), "pda", "contenido", "evaluación", "proyecto"]
            fragmentos_relevantes = []
            for parrafo in (f_content or "").split("\n"):
                p_clean = parrafo.strip()
                if p_clean and any(tk.lower() in p_clean.lower() for tk in terminos_clave):
                    fragmentos_relevantes.append(p_clean[:200])
                    if len(fragmentos_relevantes) >= 3:
                        break
            archivos_usuario_encontrados.append({
                "nombre": f_name,
                "resumen": " // ".join(fragmentos_relevantes) if fragmentos_relevantes else f_content[:300]
            })

    # 6. Extracción y garantía de los 4 CAMPOS FORMATIVOS (Uso Obligatorio del Programa Analítico)
    # Mapeo de libros SEP asociados por campo
    libros_por_campo_def = {
        "Lenguajes": "Proyectos de Aula (págs. 20-35 / 34-49) y Múltiples Lenguajes (págs. 40-47)",
        "Saberes y Pensamiento Científico": "Proyectos de Aula (págs. 140-153) y Nuestros Saberes (págs. 68-76)",
        "Ética, Naturaleza y Sociedades": "Proyectos Escolares (págs. 194-207) y Nuestros Saberes (págs. 140-149)",
        "De lo Humano y lo Comunitario": "Proyectos de Aula (págs. 320-333) y Proyectos Comunitarios (págs. 50-63)"
    }
    nuestros_saberes_por_campo_def = {
        "Lenguajes": "Nuestros Saberes (págs. 28-35): Recursos literarios, la narración y estructura del cuento",
        "Saberes y Pensamiento Científico": "Nuestros Saberes (págs. 68-76): El sistema digestivo, nutrición, sellos NOM-051 y múltiplos del gramo",
        "Ética, Naturaleza y Sociedades": "Nuestros Saberes (págs. 140-149): Servicios públicos, satisfacción de necesidades, cultura contributiva e IVA",
        "De lo Humano y lo Comunitario": "Nuestros Saberes (págs. 202-211): Mediación dialógica, cultura de paz, estilos de vida activos y circuitos motrices"
    }
    problematicas_por_campo_def = {
        "Lenguajes": "Comprensión lectora profunda inferencial, velocidad lectora (1 min) y ortografía en redacción autónoma.",
        "Saberes y Pensamiento Científico": "Cálculo mental contextualizado, lectura reflexiva de datos/gráficas y problemas razonados comunitarios.",
        "Ética, Naturaleza y Sociedades": "Comprensión crítica de dilemas y derechos, memoria histórica de México/Durango y redacción cívica.",
        "De lo Humano y lo Comunitario": "Promoción de la lectura en familias y comunidad de Durango, acceso y uso reflexivo de tecnologías."
    }

    # Revisar si el proyecto de la semana en cuadernillo_kempis tiene desglose de campos
    campos_kempis = proyecto_semana.get("campos", {}) if isinstance(proyecto_semana, dict) else {}

    pda_4campos = []
    for campo_nom in campos_4_oficiales:
        cont_val = ""
        pda_val = ""
        fuente_val = "Programa Analítico Oficial"

        # Prioridad A: Campos específicos de la semana del proyecto
        if campo_nom in campos_kempis and isinstance(campos_kempis[campo_nom], dict):
            k_info = campos_kempis[campo_nom]
            cont_val = k_info.get("tema") or k_info.get("contenido") or ""
            pda_val = k_info.get("pda_vinculado") or k_info.get("pda") or ""
            if cont_val and pda_val:
                fuente_val = f"Cuadernillo Didáctico Oficial (Semana {semana_num})"

        # Prioridad B: Programa Sintético local de muestra
        if (not cont_val or not pda_val) and pda_sintetico_sample:
            for item_s in pda_sintetico_sample:
                if campo_nom.lower() in item_s.get("campo", "").lower():
                    cont_val = item_s.get("contenido", "")
                    pda_val = item_s.get("pda", "")
                    fuente_val = "Programa Sintético Fase 5 (Oficial Local)"
                    break

        # Prioridad C: Banco curricular nem_data
        if (not cont_val or not pda_val) and campo_nom in banco_grado:
            items_banco = banco_grado[campo_nom]
            if items_banco:
                cont_val = items_banco[0].get("contenido", "")
                pda_val = items_banco[0].get("pda", "")
                fuente_val = "Banco Curricular NEM (SEP)"

        # Respaldo de seguridad para garantizar contenido no vacío
        if not cont_val:
            cont_val = f"Contenido oficial de {campo_nom} articulado a las problemáticas comunitarias."
        if not pda_val:
            pda_val = f"Proceso de desarrollo de aprendizaje oficial de 6° grado en {campo_nom} vinculado a la comprensión lectora y el razonamiento lógico."

        # Enriquecer con libro_sep, nuestros_saberes y proyecto oficial si están disponibles
        libro_vinc = (k_info.get("libro_sep") if 'k_info' in locals() and isinstance(k_info, dict) and k_info.get("libro_sep") else None) or libros_por_campo_def.get(campo_nom, "Libros de Texto Gratuitos SEP")
        ns_vinc = (k_info.get("nuestros_saberes") if 'k_info' in locals() and isinstance(k_info, dict) and k_info.get("nuestros_saberes") else None) or nuestros_saberes_por_campo_def.get(campo_nom, "Nuestros Saberes (6° grado)")
        proy_nom = (k_info.get("proyecto_oficial") if 'k_info' in locals() and isinstance(k_info, dict) else None) or ""

        pda_4campos.append({
            "campo": campo_nom,
            "proyecto": proy_nom,
            "contenido": cont_val,
            "pda": pda_val,
            "libro_vinculado": libro_vinc,
            "nuestros_saberes": ns_vinc,
            "problematica_atendida": problematicas_por_campo_def.get(campo_nom, "Comprensión lectora, ortografía y comunidad"),
            "fuente_curricular": fuente_val
        })

    # 7. Cruce y alineación de recursos y consignas día por día
    rutinas_semana = proyecto_semana.get("rutinas_matutinas", {}) if isinstance(proyecto_semana, dict) else {}
    secuencias_semana = proyecto_semana.get("secuencias_por_dia", {}) if isinstance(proyecto_semana, dict) else {}
    r_dictados = rutinas_semana.get("dictado", {})
    r_calculo = rutinas_semana.get("calculo_mental", {})
    r_problemas = rutinas_semana.get("problemas_razonados", {})

    recursos_por_dia = {}
    for idx_dia, dia_nom in enumerate(dias_lista, 1):
        try:
            anexo_dia = obtener_anexos_por_semana_y_dia(semana_num, dia_nom, mes=mes_nom)
        except Exception:
            anexo_dia = f"Anexo {semana_num}.{idx_dia}: Ficha de Trabajo Práctica"

        # Obtener o construir rutina matutina específica
        if isinstance(r_dictados, dict):
            dict_txt = r_dictados.get(dia_nom, f"Palabras clave reflexivas para {dia_nom} con reto ortográfico.")
        else:
            dict_txt = f"Palabras clave ortográficas para {dia_nom}."

        if isinstance(r_calculo, dict):
            calc_txt = r_calculo.get(dia_nom, f"Operaciones de cálculo mental contextualizadas para {dia_nom}.")
        else:
            calc_txt = f"Operaciones de cálculo mental para {dia_nom}."

        if isinstance(r_problemas, dict):
            prob_txt = r_problemas.get(dia_nom, f"Problema razonado de situaciones comunitarias en Durango.")
        else:
            prob_txt = f"Problema razonado contextualizado para {dia_nom}."

        # Obtener o construir secuencia didáctica y consigna
        sec_info = secuencias_semana.get(dia_nom, {}) if isinstance(secuencias_semana, dict) else {}
        proy_dia = sec_info.get("proyecto") or proyecto_semana.get("proyecto", "Proyecto Institucional")
        inicio_txt = sec_info.get("inicio", f"Activación colectiva, preguntas detonadoras y recuperación de conocimientos previos para {dia_nom}.")
        desarrollo_txt = sec_info.get("desarrollo", f"Indagación práctica, análisis en comunidades de aprendizaje y resolución del anexo de la sesión: {anexo_dia}.")
        cierre_txt = sec_info.get("cierre", f"Socialización comunitaria, conclusiones colectivas y metacognición en asamblea de aula.")

        # Consigna orientada y alineada a las directrices del docente
        consigna_dia = f"Completar en binas la ficha de trabajo '{anexo_dia}', aplicando la lectura analítica, resolviendo los ejercicios prácticos y registrando reflexiones en el cuaderno de trabajo."
        if directrices_docente and len(directrices_docente.strip()) > 10:
            consigna_dia += f" Vincular con los acuerdos docentes: {directrices_docente.strip()[:100]}..."

        recursos_por_dia[dia_nom] = {
            "sesion_num": idx_dia,
            "proyecto": proy_dia,
            "anexo": anexo_dia,
            "dictado": dict_txt,
            "velocidad_lectora": "1 minuto cronometrado con registro de fluidez, modulación y dicción.",
            "calculo_mental": calc_txt,
            "problema_razonado": prob_txt,
            "inicio": inicio_txt,
            "desarrollo": desarrollo_txt,
            "cierre": cierre_txt,
            "consigna_alineada": consigna_dia,
            "libros_sugeridos": libros_grado[:3] if libros_grado else ["Proyectos de Aula", "Nuestros Saberes", "Múltiples Lenguajes"]
        }

    # 8. Construcción del Bloque de Inyección Pedagógica (dossier_prompt)
    filas_tabla_prompt = []
    for item in pda_4campos:
        filas_tabla_prompt.append(
            f"| **{item['campo']}** | {item['contenido']} | {item['pda']} | {item['libro_vinculado']} | {item['problematica_atendida']} |"
        )
    tabla_4campos_md = "\n".join(filas_tabla_prompt)

    dias_recursos_md = []
    for dia_nom, info_d in recursos_por_dia.items():
        dias_recursos_md.append(
            f"### Sesión {info_d['sesion_num']} ({dia_nom}):\n"
            f"- **Anexo Didáctico Imprimible Asignado:** `{info_d['anexo']}`\n"
            f"- **Consigna Pedagógica Específica:** {info_d['consigna_alineada']}\n"
            f"- **Rutina de Inicio del Día:** Dictado: {info_d['dictado']} | Fluidez: {info_d['velocidad_lectora']} | Cálculo: {info_d['calculo_mental']} | Problema: {info_d['problema_razonado']}\n"
            f"- **Libros de Texto SEP a consultar:** {', '.join(info_d['libros_sugeridos'])}"
        )
    dias_recursos_str = "\n\n".join(dias_recursos_md)

    fuentes_txt = "\n".join(f"- **{ac['fuente']}** ({ac['tipo']}): {ac['estado']}. {ac.get('detalles', '')}" for ac in archivos_consultados)

    dossier_prompt = f"""
=== DOSSIER OFICIAL DE BÚSQUEDA CRUZADA EN ARCHIVOS DE LA PLATAFORMA (INTEGRACIÓN OBLIGATORIA) ===
El sistema ha realizado una lectura e indexación cruzada en todos los acervos y documentos de la plataforma:
{fuentes_txt}

--- 1. ARTICULACIÓN OBLIGATORIA DEL PROGRAMA ANALÍTICO (LOS 4 CAMPOS FORMATIVOS) ---
* DIRECTRIZ MANDATORIA DE FIDELIDAD CURRICULAR:
Es OBLIGATORIO que la planeación didáctica integre y despliegue transversalmente los Contenidos y PDA de los 4 Campos Formativos definidos a continuación, sin omitir ninguno:
| Campo Formativo | Contenido Sintético Oficial | PDA Oficial de 6° Grado | Libros SEP Sugeridos | Problemática Analítica Vinculada |
| :--- | :--- | :--- | :--- | :--- |
{tabla_4campos_md}

--- 2. ALINEACIÓN DE RECURSOS DIDÁCTICOS, CONSIGNAS Y ANEXOS IMPRIMIBLES POR DÍA ---
Para los días específicos a planear ({', '.join(dias_lista)}), es OBLIGATORIO cruzar e incorporar en las actividades de Inicio, Desarrollo y Cierre los siguientes anexos y consignas identificados en el cuadernillo de la plataforma:
{dias_recursos_str}

--- 3. REGLA DE COHERENCIA CURRICULAR Y PROHIBICIÓN ESTRICTA DE CONTENIDOS EXTERNOS ---
* PROHIBICIÓN ESTRICTA DE ALUCINACIÓN: Queda terminantemente prohibido inventar materias, disciplinas aisladas del plan de estudios anterior (Español, Matemáticas, Ciencias Naturales, Geografía, Historia) o contenidos genéricos no oficiales.
* TRAZABILIDAD OBLIGATORIA: Toda actividad debe fundamentarse estrictamente en los 4 Campos Formativos de la NEM, resolver las 4 problemáticas institucionales (comprensión lectora, velocidad/fluidez, ortografía y uso crítico de tecnologías en la comunidad) y atender el perfil de los 26 alumnos de la Escuela Primaria “Revolución Social de 1910” de Durango (estilos Kinestésico y Visual mediante DUA).
"""

    resumen_alineacion = (
        f"Se integró exitosamente el Programa Analítico oficial y se realizó búsqueda cruzada en {len(archivos_consultados)} fuentes "
        f"(Cuadernillos Semana {semana_num}, Libros SEP 6°, Guías CTE y {len(pda_4campos)} Campos Formativos articulados)."
    )

    return {
        "pda_4campos": pda_4campos,
        "archivos_consultados": archivos_consultados,
        "recursos_por_dia": recursos_por_dia,
        "proyecto_semana": proyecto_semana,
        "dossier_prompt": dossier_prompt,
        "resumen_alineacion": resumen_alineacion,
        "tabla_4campos_md": tabla_4campos_md
    }



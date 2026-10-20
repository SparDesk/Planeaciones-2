from __future__ import annotations

"""
Módulo de conexión y extracción web en tiempo real con el catálogo oficial
de la Comisión Nacional de Libros de Texto Gratuitos (CONALITEG - SEP).
URL oficial: https://libros.conaliteg.gob.mx/primaria.html
"""

import re
import urllib3
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple

__all__ = [
    "obtener_libros_conaliteg",
    "buscar_programa_sintetico_sep",
    "LIBROS_SEP_FALLBACK",
    "clean_title",
]

# Diccionario base de respaldo de la Nueva Escuela Mexicana (NEM)
LIBROS_SEP_FALLBACK = {
    "1° de Primaria": [
        "Proyectos de Aula (1° grado)",
        "Proyectos Escolares (1° grado)",
        "Proyectos Comunitarios (1° grado)",
        "Nuestros Saberes: Libro para alumnos, maestros y familia (1° grado)",
        "Múltiples lenguajes (1° grado)",
        "Múltiples lenguajes: Trazos y palabras (1° grado)"
    ],
    "2° de Primaria": [
        "Proyectos de Aula (2° grado)",
        "Proyectos Escolares (2° grado)",
        "Proyectos Comunitarios (2° grado)",
        "Nuestros Saberes: Libro para alumnos, maestros y familia (2° grado)",
        "Múltiples lenguajes (2° grado)"
    ],
    "3° de Primaria": [
        "Proyectos de Aula (3° grado)",
        "Proyectos Escolares (3° grado)",
        "Proyectos Comunitarios (3° grado)",
        "Nuestros Saberes: Libro para alumnos, maestros y familia (3° grado)",
        "Múltiples lenguajes (3° grado)"
    ],
    "4° de Primaria": [
        "Proyectos de Aula (4° grado)",
        "Proyectos Escolares (4° grado)",
        "Proyectos Comunitarios (4° grado)",
        "Nuestros Saberes: Libro para alumnos, maestros y familia (4° grado)",
        "Múltiples lenguajes (4° grado)",
        "Cartografía de México y el mundo (Fases 4 y 5)"
    ],
    "5° de Primaria": [
        "Proyectos de Aula (5° grado)",
        "Proyectos Escolares (5° grado)",
        "Proyectos Comunitarios (5° grado)",
        "Nuestros Saberes: Libro para alumnos, maestros y familia (5° grado)",
        "Múltiples lenguajes (5° grado)",
        "Cartografía de México y el mundo (5° grado)"
    ],
    "6° de Primaria": [
        "Proyectos de Aula (6° grado)",
        "Proyectos Escolares (6° grado)",
        "Proyectos Comunitarios (6° grado)",
        "Nuestros Saberes: Libro para alumnos, maestros y familia (6° grado)",
        "Múltiples lenguajes (6° grado)",
        "Cartografía de México y el mundo (6° grado)"
    ]
}

# Desactivar advertencias de SSL en caso de certificados intermedios
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONALITEG_URL = "https://libros.conaliteg.gob.mx/primaria.html"

GRADE_MAPPING = {
    "1": "1° de Primaria",
    "2": "2° de Primaria",
    "3": "3° de Primaria",
    "4": "4° de Primaria",
    "5": "5° de Primaria",
    "6": "6° de Primaria"
}

def clean_title(title: str) -> str:
    """Corrige inconsistencias tipográficas presentes en el HTML de CONALITEG."""
    if not title:
        return ""
    t = title
    # Arreglar errores de codificación y acentuación en Múltiples lenguajes
    t = t.replace("MÃºltiples lenguajes", "Múltiples lenguajes")
    t = t.replace("mÃºltiples lenguajes", "múltiples lenguajes")
    t = t.replace("MÃºltiples Lenguajes", "Múltiples lenguajes")
    t = t.replace("MÃºltiples", "Múltiples")
    t = t.replace("mÃºltiples", "múltiples")
    t = t.replace("Mltiples lenguajes", "Múltiples lenguajes")
    t = t.replace("Mltiples", "Múltiples")
    t = t.replace("Múltiples Lenguajes", "Múltiples lenguajes")
    t = t.replace("Cartograf\xada", "Cartografía")
    t = t.replace("Cartografa", "Cartografía")
    t = t.replace("Mxico", "México")
    t = t.replace("Galera", "Galería")
    t = t.rstrip(".").strip()
    return t

def obtener_libros_conaliteg() -> Tuple[Dict[str, List[str]], bool]:
    """
    Realiza web scraping en tiempo real de la página oficial de CONALITEG
    para extraer los libros de texto gratuitos vigentes del ciclo 2026-2027
    clasificados por grado (1° a 6° de primaria).
    
    Retorna:
        Tuple[Dict[str, List[str]], bool]:
            - Diccionario con los grados como claves y listas de títulos de libros como valores.
            - Booleano (True si se obtuvo exitosamente en vivo de CONALITEG, False si se usó el fallback).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8"
    }

    try:
        response = requests.get(CONALITEG_URL, headers=headers, timeout=6, verify=False)
        response.encoding = 'utf-8'
        if response.status_code == 200 and response.text:
            soup = BeautifulSoup(response.text, "html.parser")
            libros_extraidos = {grado_std: [] for grado_std in GRADE_MAPPING.values()}

            # Buscar enlaces de libros que contengan Editorial SEP y Grado
            anchors = soup.find_all("a")
            for a in anchors:
                txt = a.get_text(separator=" | ", strip=True)
                if "Editorial: SEP" in txt and "Grado:" in txt:
                    parts = [p.strip() for p in txt.split("|")]
                    raw_title = parts[0]
                    titulo = clean_title(raw_title)
                    
                    # Extraer el número de grado
                    grado_match = re.search(r"Grado:\s*([1-6])", txt)
                    if grado_match:
                        g_num = grado_match.group(1)
                        standard_grade = GRADE_MAPPING.get(g_num)
                        if standard_grade and titulo:
                            if titulo not in libros_extraidos[standard_grade]:
                                libros_extraidos[standard_grade].append(titulo)

            # Verificar que se hayan extraído libros válidos para al menos 4 grados
            grados_con_libros = sum(1 for g in libros_extraidos.values() if len(g) > 0)
            if grados_con_libros >= 4:
                return libros_extraidos, True

    except Exception:
        # En caso de caída del servidor CONALITEG, timeout o bloqueo de red
        pass

    # Respaldo (Fallback) con el catálogo oficial de la Nueva Escuela Mexicana
    return dict(LIBROS_SEP_FALLBACK), False


from typing import Dict, List, Tuple, Optional, Union

def buscar_programa_sintetico_sep(
    fase_seleccionada: str = "Fase 5",
    semana: Optional[Union[int, str]] = None,
    mes: Optional[str] = None,
    dia: Optional[str] = None,
    proyecto: Optional[str] = None,
    max_resultados: int = 3,
    fase: Optional[str] = None,
    **kwargs
) -> Tuple[str, bool]:
    """
    Función auxiliar de búsqueda y web scraping de respaldo para el Programa Sintético oficial de la SEP
    y lineamientos de la Nueva Escuela Mexicana (NEM).
    Construye consultas dinámicas contextualmente enriquecidas con Fase, Semana (1 a 37), Mes del ciclo 2026-2027,
    Día de la semana y Proyecto vinculante, eliminando cualquier valor estático o fijo.
    """
    fase_activa = fase or fase_seleccionada or "Fase 5"
    fase_limpia = str(fase_activa).replace("Fase", "").strip() or "5"
    fase_termino = f"Fase {fase_limpia}"

    componentes_busqueda = [f'"Programa Sintético"', f'"{fase_termino}"']
    if semana is not None and str(semana).strip():
        sem_str = str(semana).replace("Semana", "").strip()
        if sem_str:
            componentes_busqueda.append(f'"Semana {sem_str}"')
    if mes and str(mes).strip():
        componentes_busqueda.append(f'"{str(mes).strip()}"')
    if dia and str(dia).strip():
        componentes_busqueda.append(f'"{str(dia).strip()}"')
    if proyecto and str(proyecto).strip():
        proy_limpio = re.sub(r'["\n\r]', '', str(proyecto).strip())[:50]
        if proy_limpio:
            componentes_busqueda.append(f'"{proy_limpio}"')

    query = f'site:sep.gob.mx OR site:conaliteg.sep.gob.mx {" ".join(componentes_busqueda)}'
    urls = []

    # 1. Utilizar googlesearch-python
    try:
        from googlesearch import search
        for item in search(query, num_results=max_resultados, lang="es", timeout=5):
            u = getattr(item, "url", item) if not isinstance(item, str) else item
            if u and isinstance(u, str) and u.startswith("http"):
                urls.append(u)
            if len(urls) >= max_resultados:
                break
    except Exception:
        pass

    # 2. Respaldo secundario si Google bloquea la petición automatizada
    if not urls:
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                ddg_res = list(ddgs.text(query, max_results=max_resultados))
                for item in ddg_res:
                    link = item.get("href") or item.get("link")
                    if link and ("sep.gob.mx" in link or "conaliteg.sep.gob.mx" in link):
                        urls.append(link)
        except Exception:
            pass

    # 3. Extraer contenido de los primeros resultados con requests y BeautifulSoup
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9"
    }

    resumenes = []
    for u in urls[:max_resultados]:
        try:
            resp = requests.get(u, headers=headers, timeout=6, verify=False)
            if resp.status_code == 200 and resp.text:
                soup = BeautifulSoup(resp.text, "html.parser")
                for s in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                    s.decompose()
                parrafos = [
                    p.get_text(strip=True)
                    for p in soup.find_all(["p", "h1", "h2", "h3", "li"])
                    if len(p.get_text(strip=True)) > 30
                ]
                texto_pagina = " ".join(parrafos[:15])
                if len(texto_pagina.strip()) > 80:
                    resumenes.append(f"Fuente ({u}):\n{texto_pagina[:1200]}")
        except Exception:
            continue

    if resumenes:
        return "\n\n---\n\n".join(resumenes), True

    return "", False


# Alias de compatibilidad para integraciones externas
get_conaliteg_books = obtener_libros_conaliteg
get_libros_conaliteg = obtener_libros_conaliteg
scrape_conaliteg = obtener_libros_conaliteg
buscar_programa_sintetico = buscar_programa_sintetico_sep
buscar_programa_sep = buscar_programa_sintetico_sep


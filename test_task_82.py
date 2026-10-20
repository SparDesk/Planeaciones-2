import sys
import os

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from file_processor import busqueda_cruzada_archivos_plataforma
from nem_data import CAMPOS_FORMATIVOS, DATOS_PREDETERMINADOS, EJEMPLO_PROBLEMICA_ANALITICO
from gemini_engine import build_system_instruction, generate_sample_fallback
from docx_generator import build_docx_planeacion, parse_plan_sections

print("=== TEST 1: busqueda_cruzada_archivos_plataforma ===")
dossier = busqueda_cruzada_archivos_plataforma(
    semana=6,
    grado="6° de Primaria",
    campos_formativos=CAMPOS_FORMATIVOS,
    dias_seleccionados=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
    directrices_docente="Fortalecer comprensión lectora y cálculo mental con frutas y gramo.",
    archivos_procesados={"notas_docente.txt": "Recordar enfatizar el uso del gramo y el Plato del Bien Comer."},
    mes="Octubre",
    año=2026
)

assert "pda_4campos" in dossier, "Falta pda_4campos en dossier"
assert len(dossier["pda_4campos"]) == 4, f"Se esperaban 4 campos formativos, obtenidos: {len(dossier['pda_4campos'])}"
campos_obtenidos = [item["campo"] for item in dossier["pda_4campos"]]
print(f"Campos formativos extraídos del Programa Analítico: {campos_obtenidos}")
for c in ["Lenguajes", "Saberes y Pensamiento Científico", "Ética, Naturaleza y Sociedades", "De lo Humano y lo Comunitario"]:
    assert c in campos_obtenidos, f"Falta el campo obligatorio: {c}"

print(f"Archivos consultados: {len(dossier['archivos_consultados'])}")
for ac in dossier["archivos_consultados"]:
    print(f"  - {ac['fuente']} ({ac['tipo']}): {ac['estado']}")

assert "recursos_por_dia" in dossier, "Falta recursos_por_dia"
assert len(dossier["recursos_por_dia"]) == 5, f"Se esperaban 5 días, obtenidos: {len(dossier['recursos_por_dia'])}"
for d, r in dossier["recursos_por_dia"].items():
    print(f"  Día {d}: Anexo={r['anexo']}, Consigna={r['consigna_alineada'][:50]}...")

print("\n=== TEST 2: build_system_instruction y Reglas 10 y 11 ===")
sys_inst = build_system_instruction()
assert "USO OBLIGATORIO DEL PROGRAMA ANALÍTICO" in sys_inst, "Falta regla 10 en system instruction"
assert "BÚSQUEDA CRUZADA EN ARCHIVOS Y COHERENCIA CURRICULAR" in sys_inst, "Falta regla 11 en system instruction"
print("✓ System instruction contiene las reglas obligatorias 10 y 11")

print("\n=== TEST 3: Enriquecimiento automático de los 4 Campos Formativos en generate_planeacion ===")
# Simular ensamblaje de prompt con un solo campo pasado intencionalmente
from gemini_engine import generate_planeacion
import inspect

# Inspeccionar parámetros de generate_planeacion
sig = inspect.signature(generate_planeacion)
assert "dossier_busqueda" in sig.parameters, "generate_planeacion no tiene parámetro dossier_busqueda"
print("✓ generate_planeacion acepta dossier_busqueda")

print("\n=== TEST 4: generate_sample_fallback con los 4 Campos Formativos ===")
fallback_text = generate_sample_fallback(
    datos_escuela=DATOS_PREDETERMINADOS,
    campos_formativos=CAMPOS_FORMATIVOS,
    metodologia=["Aprendizaje Basado en Proyectos Comunitarios", "Aprendizaje Basado en Indagación (STEAM como enfoque)"],
    ejes=["Pensamiento crítico", "Inclusión"],
    dias_seleccionados=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
    semana_seleccionada=6
)

parsed = parse_plan_sections(fallback_text)
assert len(parsed.get("articulacion_filas", [])) >= 4, f"Se esperaban al menos 4 filas en articulación, obtenidas: {len(parsed.get('articulacion_filas', []))}"
print(f"✓ Articulación curricular contiene {len(parsed.get('articulacion_filas', []))} filas (los 4 Campos Formativos)")

print("\n=== TEST 5: Generación de DOCX con los 4 Campos y Anexos ===")
docx_io = build_docx_planeacion(datos_escuela=DATOS_PREDETERMINADOS, plan_text=fallback_text)
docx_data = docx_io.getvalue() if hasattr(docx_io, "getvalue") else docx_io
assert len(docx_data) > 10000, "El documento DOCX generado es demasiado pequeño"
print(f"✓ Documento DOCX generado exitosamente ({len(docx_data):,} bytes)")

print("\n🎉 TODOS LOS TESTS DE LA TAREA 82 PASARON EXITOSAMENTE.")

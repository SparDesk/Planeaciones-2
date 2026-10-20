"""
Prueba Integral de Validación - Tarea 87:
INTEGRACIÓN OFICIAL DEL PROGRAMA ANALÍTICO (ESCUELA REVOLUCIÓN SOCIAL DE 1910)
Y DATOS INSTITUCIONALES EN PLANIFICACIONES ESCOLARES (FASE 5 / 6° GRADO)
"""

import sys
import os
import io

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def test_task_87():
    print("=== INICIANDO VALIDACIÓN DE TAREA 87 ===")

    # -------------------------------------------------------------
    # 1. VALIDACIÓN DE DATOS INSTITUCIONALES Y FICHA TÉCNICA OFICIAL
    # -------------------------------------------------------------
    print("\n--- 1. Verificando Datos Institucionales y Ficha Técnica ---")
    import nem_data
    from nem_data import DATOS_PREDETERMINADOS, PROGRAMA_ANALITICO_OFICIAL_6TO, obtener_programa_analitico_6to

    assert "Revolución Social de 1910" in DATOS_PREDETERMINADOS["nombre_escuela"], "Nombre de escuela no coincide"
    assert DATOS_PREDETERMINADOS["cct"] == "10EPR0361N", f"CCT incorrecto: {DATOS_PREDETERMINADOS['cct']}"
    assert "49" in DATOS_PREDETERMINADOS["zona_escolar"], f"Zona escolar incorrecta: {DATOS_PREDETERMINADOS['zona_escolar']}"
    assert "02" in DATOS_PREDETERMINADOS["sector"], f"Sector incorrecto: {DATOS_PREDETERMINADOS['sector']}"
    assert "Durango" in DATOS_PREDETERMINADOS["entidad"], f"Entidad incorrecta: {DATOS_PREDETERMINADOS['entidad']}"
    assert "Aday Domínguez Domínguez" in DATOS_PREDETERMINADOS["docente"], f"Docente incorrecta: {DATOS_PREDETERMINADOS['docente']}"
    assert "Guillermo Gerardo Borjas Díaz" in DATOS_PREDETERMINADOS["director"], f"Director incorrecto: {DATOS_PREDETERMINADOS['director']}"
    assert DATOS_PREDETERMINADOS["fase"] == "Fase 5", f"Fase incorrecta: {DATOS_PREDETERMINADOS['fase']}"
    assert "6" in DATOS_PREDETERMINADOS["grado"], f"Grado incorrecto: {DATOS_PREDETERMINADOS['grado']}"
    assert DATOS_PREDETERMINADOS["grupo"] == "A", f"Grupo incorrecto: {DATOS_PREDETERMINADOS['grupo']}"
    assert DATOS_PREDETERMINADOS["matricula"] == 26, f"Matrícula incorrecta: {DATOS_PREDETERMINADOS['matricula']}"

    ficha = PROGRAMA_ANALITICO_OFICIAL_6TO["ficha_tecnica"]
    assert ficha["cct"] == "10EPR0361N"
    assert ficha["director"] == "Guillermo Gerardo Borjas Díaz"
    assert ficha["docente"] == "Maestra Aday Domínguez Domínguez"
    assert ficha["matricula"] == 26

    # Validar función helper obtener_programa_analitico_6to
    prog_full = obtener_programa_analitico_6to()
    assert "proyectos_principales_6to" in prog_full
    prog_leng = obtener_programa_analitico_6to("Lenguajes")
    assert prog_leng["proyecto"] == "¡Mi comunidad se expresa!"
    print("[OK] Ficha técnica y datos institucionales configurados con total fidelidad.")

    # -------------------------------------------------------------
    # 2. VALIDACIÓN DE BASE DE DATOS DE CONTENIDOS, PDA Y NUESTROS SABERES
    # -------------------------------------------------------------
    print("\n--- 2. Verificando Contenidos, PDA, Proyectos LTG y Nuestros Saberes ---")
    banco_6to = nem_data.CONTENIDOS_PDA_POR_GRADO["6° de Primaria"]
    campos_requeridos = [
        "Lenguajes",
        "Saberes y Pensamiento Científico",
        "Ética, Naturaleza y Sociedades",
        "De lo Humano y lo Comunitario"
    ]

    for c in campos_requeridos:
        assert c in banco_6to, f"Falta campo {c} en banco_6to"
        items = banco_6to[c]
        assert len(items) >= 3, f"Se esperaban al menos 3 items curriculares para {c}"
        for it in items:
            assert "contenido" in it and len(it["contenido"]) > 5
            assert "pda" in it and len(it["pda"]) > 5
            assert "proyecto_ltg" in it, f"Falta proyecto_ltg en {it['contenido'][:30]}"
            assert "libro_ltg" in it, f"Falta libro_ltg en {it['contenido'][:30]}"
            assert "vinculacion_nuestros_saberes" in it, f"Falta vinculacion_nuestros_saberes en {it['contenido'][:30]}"

    # Validar que los 4 proyectos oficiales del Programa Analítico están presentes en el banco de 6°
    proyectos_banco = {it["proyecto_ltg"] for c in campos_requeridos for it in banco_6to[c]}
    assert "¡Mi comunidad se expresa!" in proyectos_banco
    assert "El poder de la alimentación" in proyectos_banco
    assert "Contribuyo con los servicios de mi escuela" in proyectos_banco
    assert "El club de las nutrias" in proyectos_banco
    print("[OK] Base de datos indexa los 4 campos formativos con proyectos LTG y vinculación a Nuestros Saberes.")

    # -------------------------------------------------------------
    # 3. VALIDACIÓN EN CUADERNILLO KEMPIS Y VINCULACIÓN CON NUESTROS SABERES
    # -------------------------------------------------------------
    print("\n--- 3. Verificando Cuadernillo Kempis y Vinculación Semanal ---")
    from cuadernillo_kempis import PROYECTOS_OFICIALES_6TO_GRADO, CUADERNILLO_KEMPIS_DATA, formatear_kempis_para_prompt

    for c in campos_requeridos:
        assert c in PROYECTOS_OFICIALES_6TO_GRADO
        p_info = PROYECTOS_OFICIALES_6TO_GRADO[c]
        assert "nuestros_saberes" in p_info, f"Falta nuestros_saberes en {c}"
        assert "págs." in p_info["nuestros_saberes"], f"Falta paginación en nuestros_saberes para {c}"

    # Semanas 6 y 7
    for sem in [6, 7]:
        k_data = CUADERNILLO_KEMPIS_DATA[sem]
        for c in campos_requeridos:
            c_dict = k_data["campos"][c]
            assert "nuestros_saberes" in c_dict, f"Falta nuestros_saberes en semana {sem} para {c}"
            assert "Nuestros Saberes" in c_dict["nuestros_saberes"]

    # Prompt con Nuestros Saberes
    p_txt = formatear_kempis_para_prompt(semana=6)
    assert "Nuestros Saberes" in p_txt
    assert "¡Mi comunidad se expresa!" in p_txt
    assert "El poder de la alimentación" in p_txt
    assert "Contribuyo con los servicios de mi escuela" in p_txt
    assert "El club de las nutrias" in p_txt
    print("[OK] Cuadernillo Kempis incorpora Nuestros Saberes con paginación oficial en los 4 proyectos.")

    # -------------------------------------------------------------
    # 4. VALIDACIÓN DE EXTRACCIÓN AUTOMÁTICA EN APP.PY
    # -------------------------------------------------------------
    print("\n--- 4. Verificando Sincronización en app.py ---")
    import app
    assert "Revolución Social de 1910" in app.DATOS_PREDETERMINADOS["nombre_escuela"]
    assert app.DATOS_PREDETERMINADOS["cct"] == "10EPR0361N"
    assert app.DATOS_PREDETERMINADOS["docente"] == "Maestra Aday Domínguez Domínguez"
    assert app.DATOS_PREDETERMINADOS["director"] == "Guillermo Gerardo Borjas Díaz"

    # Verificar que CONTENIDOS_PDA_POR_GRADO["6° de Primaria"] en app.py está sincronizado con nem_data
    app_6to = app.CONTENIDOS_PDA_POR_GRADO["6° de Primaria"]
    app_proys = {it.get("proyecto_ltg") for c in campos_requeridos for it in app_6to[c]}
    assert "¡Mi comunidad se expresa!" in app_proys
    assert "El poder de la alimentación" in app_proys
    assert "Contribuyo con los servicios de mi escuela" in app_proys
    assert "El club de las nutrias" in app_proys
    print("[OK] app.py sincronizado con los 4 proyectos oficiales y sus metadatos de Nuestros Saberes.")

    # -------------------------------------------------------------
    # 5. VALIDACIÓN DE GENERADORES DE DOCUMENTOS WORD Y PDF
    # -------------------------------------------------------------
    print("\n--- 5. Verificando Generación de Documentos Word (DOCX) y PDF ---")
    from gemini_engine import generate_sample_fallback
    from docx_generator import generate_docx_planeacion, parse_plan_sections
    from pdf_generator import build_pdf_planeacion

    # Generar planeación de prueba para Semana 6 (Octubre)
    plan_sem6 = generate_sample_fallback(
        datos_escuela=DATOS_PREDETERMINADOS,
        campos_formativos=campos_requeridos,
        metodologia=["Aprendizaje Basado en Proyectos Comunitarios"],
        ejes=["Pensamiento crítico", "Apropiación de las culturas a través de la lectura y la escritura"],
        dias_seleccionados=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        semana_seleccionada=6
    )

    # Validar que el texto de la planeación contenga los 4 proyectos y Nuestros Saberes
    assert "¡Mi comunidad se expresa!" in plan_sem6
    assert "El poder de la alimentación" in plan_sem6
    assert "Contribuyo con los servicios de mi escuela" in plan_sem6
    assert "El club de las nutrias" in plan_sem6
    assert "Nuestros Saberes" in plan_sem6
    assert "10EPR0361N" in plan_sem6
    assert "Aday Domínguez Domínguez" in plan_sem6
    assert "Guillermo Gerardo Borjas Díaz" in plan_sem6

    # Validar DOCX
    docx_bytes = generate_docx_planeacion(DATOS_PREDETERMINADOS, plan_sem6)
    assert isinstance(docx_bytes, io.BytesIO)
    assert docx_bytes.getbuffer().nbytes > 10000, "El documento Word es demasiado pequeño"
    print(f"[OK] Documento Word (DOCX) generado exitosamente ({docx_bytes.getbuffer().nbytes} bytes).")

    # Validar PDF
    pdf_bytes = build_pdf_planeacion(DATOS_PREDETERMINADOS, plan_sem6)
    assert isinstance(pdf_bytes, io.BytesIO)
    assert pdf_bytes.getbuffer().nbytes > 5000, "El documento PDF es demasiado pequeño"
    print(f"[OK] Documento PDF generado exitosamente ({pdf_bytes.getbuffer().nbytes} bytes).")

    print("\n🎉 TODAS LAS PRUEBAS DE LA TAREA 87 PASARON EXITOSAMENTE AL 100%.")

if __name__ == "__main__":
    test_task_87()

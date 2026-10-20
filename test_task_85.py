"""
Prueba Integral de Validación - Tarea 85:
Sincronización Estricta de Semanas y Programa Analítico para 6° de Primaria
(Bloque del 5 al 16 de Octubre - Semanas 6 y 7)
"""
import sys
import os

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def test_task_85():
    print("=== INICIANDO VALIDACION DE TAREA 85 ===")

    # 1. Verificar definición y exportación de PROYECTOS_OFICIALES_6TO_GRADO
    from cuadernillo_kempis import (
        PROYECTOS_OFICIALES_6TO_GRADO,
        CUADERNILLO_KEMPIS_DATA,
        obtener_proyecto_semana,
        obtener_anexos_por_semana_y_dia,
        formatear_kempis_para_prompt
    )

    proyectos_esperados = {
        "Lenguajes": "¡Mi comunidad se expresa!",
        "Saberes y Pensamiento Científico": "El poder de la alimentación",
        "Ética, Naturaleza y Sociedades": "Contribuyo con los servicios de mi escuela",
        "De lo Humano y lo Comunitario": "El club de las nutrias"
    }

    for campo, proy_tit in proyectos_esperados.items():
        assert campo in PROYECTOS_OFICIALES_6TO_GRADO, f"Falta campo {campo} en PROYECTOS_OFICIALES_6TO_GRADO"
        assert PROYECTOS_OFICIALES_6TO_GRADO[campo]["proyecto"] == proy_tit, f"Proyecto no coincide para {campo}"
        assert "libro_sep" in PROYECTOS_OFICIALES_6TO_GRADO[campo], f"Falta libro_sep para {campo}"
        assert "dia_sugerido" in PROYECTOS_OFICIALES_6TO_GRADO[campo], f"Falta dia_sugerido para {campo}"
    print(f"[OK] Los 4 proyectos oficiales de 6° Grado verificados: {list(proyectos_esperados.values())}")

    # 2. Verificar datos y metadatos de Semana 6 y Semana 7 (Bloque 5 al 16 de Octubre)
    for sem in [6, 7]:
        k_data = CUADERNILLO_KEMPIS_DATA[sem]
        assert "5 al 16 de Octubre" in k_data.get("bloque_fechas", ""), f"Falta bloque_fechas en semana {sem}"
        if sem == 6:
            assert "5 al 9" in k_data.get("rango_fechas", ""), "Rango fechas Semana 6 debe ser 5 al 9 de Octubre"
        else:
            assert "12 al 16" in k_data.get("rango_fechas", ""), "Rango fechas Semana 7 debe ser 12 al 16 de Octubre"

        campos = k_data["campos"]
        for campo, proy_tit in proyectos_esperados.items():
            assert campo in campos, f"Campo {campo} no está en semana {sem}"
            assert campos[campo]["proyecto_oficial"] == proy_tit, f"Proyecto oficial incorrecto en semana {sem}"

        # Verificar anexos y su vinculación con los proyectos
        anexos = k_data["anexos"]
        assert len(anexos) >= 5, f"Se esperaban al menos 5 anexos para la semana {sem}"
        dias_anexos = {a["dia"]: a for a in anexos}
        assert dias_anexos["Lunes"]["proyecto"] == "¡Mi comunidad se expresa!"
        assert dias_anexos["Martes"]["proyecto"] == "El poder de la alimentación"
        assert dias_anexos["Miércoles"]["proyecto"] == "Contribuyo con los servicios de mi escuela"
        assert dias_anexos["Jueves"]["proyecto"] == "El club de las nutrias"
    print("[OK] Semanas 6 y 7 configuradas estrictamente con el bloque del 5 al 16 de Octubre y proyectos día por día.")

    # 3. Validar obtener_proyecto_semana y secuencias_por_dia
    for sem in [6, 7]:
        p_sem = obtener_proyecto_semana(sem)
        assert "proyectos_oficiales_6to" in p_sem, f"Falta proyectos_oficiales_6to en obtener_proyecto_semana({sem})"
        assert "bloque_sincronizado" in p_sem, f"Falta bloque_sincronizado en obtener_proyecto_semana({sem})"
        sec = p_sem["secuencias_por_dia"]
        assert sec["Lunes"]["proyecto"] == "¡Mi comunidad se expresa!"
        assert sec["Martes"]["proyecto"] == "El poder de la alimentación"
        assert sec["Miércoles"]["proyecto"] == "Contribuyo con los servicios de mi escuela"
        assert sec["Jueves"]["proyecto"] == "El club de las nutrias"
    print("[OK] obtener_proyecto_semana genera secuencias_por_dia articuladas día por día con los 4 proyectos oficiales.")

    # 4. Validar formatear_kempis_para_prompt
    prompt_sem6 = formatear_kempis_para_prompt(6)
    assert "Del 5 al 16 de Octubre" in prompt_sem6, "Prompt semana 6 debe contener bloque 5 al 16 de Octubre"
    assert "¡Mi comunidad se expresa!" in prompt_sem6
    assert "El poder de la alimentación" in prompt_sem6
    assert "Contribuyo con los servicios de mi escuela" in prompt_sem6
    assert "El club de las nutrias" in prompt_sem6
    print("[OK] formatear_kempis_para_prompt inyecta obligatoriamente el bloque y los 4 proyectos oficiales de 6° grado.")

    # 5. Validar busqueda_cruzada_archivos_plataforma en file_processor.py
    from file_processor import busqueda_cruzada_archivos_plataforma
    dossier_sem6 = busqueda_cruzada_archivos_plataforma(semana=6, grado="6° de Primaria")
    proys_dossier = [item.get("proyecto") for item in dossier_sem6["pda_4campos"]]
    for proy_tit in proyectos_esperados.values():
        assert proy_tit in proys_dossier, f"Proyecto {proy_tit} debe estar presente en pda_4campos del dossier"
    
    rec_dias = dossier_sem6["recursos_por_dia"]
    assert rec_dias["Lunes"]["proyecto"] == "¡Mi comunidad se expresa!"
    assert rec_dias["Martes"]["proyecto"] == "El poder de la alimentación"
    assert rec_dias["Miércoles"]["proyecto"] == "Contribuyo con los servicios de mi escuela"
    assert rec_dias["Jueves"]["proyecto"] == "El club de las nutrias"
    print("[OK] busqueda_cruzada_archivos_plataforma alinea los 4 proyectos día por día en 6° de Primaria.")

    # 6. Validar generate_sample_fallback en gemini_engine.py
    from gemini_engine import generate_sample_fallback
    from nem_data import DATOS_PREDETERMINADOS, CAMPOS_FORMATIVOS
    from docx_generator import parse_plan_sections

    fallback_sem6 = generate_sample_fallback(
        datos_escuela=DATOS_PREDETERMINADOS,
        campos_formativos=CAMPOS_FORMATIVOS,
        metodologia=["Aprendizaje Basado en Proyectos Comunitarios"],
        ejes=["Pensamiento crítico"],
        dias_seleccionados=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        semana_seleccionada=6
    )

    assert "¡Mi comunidad se expresa!" in fallback_sem6
    assert "El poder de la alimentación" in fallback_sem6
    assert "Contribuyo con los servicios de mi escuela" in fallback_sem6
    assert "El club de las nutrias" in fallback_sem6
    assert "Del 5 al 16 de Octubre" in fallback_sem6

    parsed_fb = parse_plan_sections(fallback_sem6)
    assert len(parsed_fb.get("articulacion_filas", [])) >= 4
    print("[OK] generate_sample_fallback genera planeación completa con los 4 proyectos y bloque del 5 al 16 de Octubre.")

    # 7. Validar catálogo escolar SEP en app.py
    from app import CATALOGO_SEMANAS_SEP
    sem6_info = CATALOGO_SEMANAS_SEP[6]
    sem7_info = CATALOGO_SEMANAS_SEP[7]
    assert sem6_info["mes_nombre"] == "Octubre"
    assert sem7_info["mes_nombre"] == "Octubre"
    assert sem6_info["lunes"].day == 5 and sem6_info["viernes"].day == 9
    assert sem7_info["lunes"].day == 12 and sem7_info["viernes"].day == 16
    print(f"[OK] Fechas oficiales SEP verificadas: Sem 6 ({sem6_info['rango_str']}), Sem 7 ({sem7_info['rango_str']}) -> Bloque exacto del 5 al 16 de Octubre.")

    print("\n🎉 TODAS LAS PRUEBAS DE LA TAREA 85 PASARON EXITOSAMENTE AL 100%.")

if __name__ == "__main__":
    test_task_85()

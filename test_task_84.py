"""
Prueba Integral de Validación - Tarea 84:
Soporte Multiusuario, Repositorio Compartido y Colaboración Concurrente en Tiempo Real.
"""
import sys
import os
import json

# Asegurar codificación utf-8 para salida en terminal Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def test_task_84():
    print("=== INICIANDO VALIDACION DE TAREA 84 ===")
    
    # 1. Importar modulos
    from planeaciones_storage import (
        init_db,
        obtener_estado_bd_centralizada,
        guardar_planeacion,
        obtener_planeacion_por_id,
        listar_planeaciones,
        obtener_planeaciones_compartidas,
        cambiar_visibilidad_planeacion,
        duplicar_planeacion_para_usuario,
        registrar_latido_presencia,
        obtener_colaboradores_activos,
        limpiar_presencia_usuario,
        agregar_comentario_colaborativo,
        listar_comentarios_colaborativos,
        eliminar_comentario_colaborativo,
        obtener_historial_colaboracion,
        obtener_o_crear_usuario,
        listar_usuarios
    )
    from app import cargar_credenciales

    init_db()
    print("[OK] Modulos inicializados correctamente.")

    # 2. Verificar estado de la BD centralizada y persistente (WAL mode)
    estado_bd = obtener_estado_bd_centralizada()
    print(f"[OK] Estado BD Centralizada: Motor={estado_bd['motor']}, Concurrencia={estado_bd['modo_concurrencia']}, Tamano={estado_bd['tamanio_kb']} KB")
    assert "WAL" in estado_bd["modo_concurrencia"], "El modo WAL debe estar activo para concurrencia multiusuario."

    # 3. Verificar cuentas institucionales multiusuario
    creds, _ = cargar_credenciales()
    usuarios_esperados = ["docente", "aday", "director", "apoyo_pedagogico", "maestro_educacion_fisica", "maestro_ingles"]
    for u in usuarios_esperados:
        assert u in creds["usernames"], f"Usuario '{u}' debe estar en las credenciales institucionales."
    print(f"[OK] {len(creds['usernames'])} cuentas multiusuario verificadas ({', '.join(usuarios_esperados)}).")

    # 4. Registrar usuarios en la tabla centralizada
    u_aday = obtener_o_crear_usuario("aday", "Maestra Aday Domínguez Domínguez", "docente@escuela.gob.mx", "Docente Titular (6° A)")
    u_dir = obtener_o_crear_usuario("director", "Prof. Guillermo Gerardo Borjas Díaz", "director@escuela.gob.mx", "Director Escolar")
    u_atp = obtener_o_crear_usuario("apoyo_pedagogico", "Mtra. Claudia Elena Morales", "atp@escuela.gob.mx", "Asesora Técnico Pedagógica / DUA")
    assert u_aday["username"] == "aday" and "Docente" in u_aday["rol"]
    assert u_dir["username"] == "director" and "Director" in u_dir["rol"]
    print("[OK] Perfiles y roles institucionales registrados en la base centralizada.")

    # 5. Mtra. Aday crea una planeacion compartida (Version 1)
    data_plan = {
        "semana": 22,
        "periodo": "16 al 20 de febrero de 2026",
        "grado": "6° de Primaria",
        "grupo": "A",
        "campos_formativos": ["Lenguajes", "Saberes y Pensamiento Cientifico"],
        "metodologia": ["Aprendizaje Basado en Proyectos Comunitarios"],
        "ejes_articuladores": ["Pensamiento critico", "Apropiacion de las culturas"],
        "num_sesiones": 5,
        "planeacion_generada": "Estructura pedagogica colegiada de 6...",
        "nombre_archivo": "Proyecto_Comunitario_Sem22",
        "categoria_ruta": "Proyectos Comunitarios"
    }

    res_v1 = guardar_planeacion(
        username="aday",
        data=data_plan,
        es_autoguardado=False,
        es_compartida=True,
        nombre_editor="Mtra. Aday",
        return_details=True
    )
    assert res_v1["status"] == "success"
    plan_id = res_v1["id"]
    version_v1 = res_v1["version"]
    assert version_v1 == 1, f"Version inicial debe ser 1, obtenido: {version_v1}"
    print(f"[OK] Mtra. Aday creo planeacion compartida ID={plan_id} (v{version_v1}).")

    # 6. Verificar que la planeacion aparece en el Repositorio Colectivo Escolar
    compartidas = obtener_planeaciones_compartidas()
    ids_comp = [p["id"] for p in compartidas]
    assert plan_id in ids_comp, "La planeacion debe aparecer en el repositorio compartido colectivo."
    p_comp = next(p for p in compartidas if p["id"] == plan_id)
    assert "Aday" in p_comp["autor"]
    assert p_comp["es_compartida"] == 1
    print(f"[OK] Planeacion visible en Repositorio Colectivo por otros docentes (Autor: {p_comp['autor']}).")

    # 7. Simulacion de Colaboracion Concurrente:
    # El Director y la Mtra. Aday abren la planeacion al mismo tiempo (ambos parten de base_version = 1).
    dir_base_version = version_v1

    # Mtra. Aday hace un ajuste y guarda primero (Avanza a v2)
    data_plan["planeacion_generada"] = "Ajuste pedagogico realizado por Mtra. Aday en sesion 3..."
    res_v2 = guardar_planeacion(
        username="aday",
        data=data_plan,
        planeacion_id=plan_id,
        base_version=version_v1,
        nombre_editor="Mtra. Aday",
        return_details=True
    )
    assert res_v2["status"] == "success"
    assert res_v2["version"] == 2, f"Version debe avanzar a 2, obtenido: {res_v2['version']}"
    print(f"[OK] Mtra. Aday guardo cambios actualizando a v{res_v2['version']}.")

    # Ahora el Director (que seguia con base_version = 1) intenta guardar sus cambios sin haber recargado:
    data_dir_edit = dict(data_plan)
    data_dir_edit["planeacion_generada"] = "Revision directiva: Sugerencia de evaluacion formativa..."
    res_conflict = guardar_planeacion(
        username="director",
        data=data_dir_edit,
        planeacion_id=plan_id,
        base_version=dir_base_version,  # Envia base_version = 1 (desactualizado)
        nombre_editor="Director Guillermo",
        return_details=True
    )

    # Debe detectar el conflicto de concurrencia y NO sobrescribir silenciosamente
    assert isinstance(res_conflict, dict), "Debe retornar diccionario de conflicto"
    assert res_conflict.get("status") == "conflict", f"Debe detectar conflicto de concurrencia. Obtenido: {res_conflict}"
    assert res_conflict.get("db_version") == 2, "La version en BD debe ser 2"
    assert res_conflict.get("base_version") == 1, "La version base del Director era 1"
    print(f"[OK] Control de Concurrencia Optimista Exitoso. Colision detectada: {res_conflict['message']}")

    # 8. Resolucion de conflicto: El Director decide duplicar la planeacion para su propio archivo
    id_copia_dir = duplicar_planeacion_para_usuario(plan_id, "director")
    assert id_copia_dir is not None
    assert id_copia_dir != plan_id
    copia_dir = obtener_planeacion_por_id(id_copia_dir)
    assert copia_dir["username"] == "director"
    assert "copia" in copia_dir["nombre_archivo"].lower() or "copia" in copia_dir.get("version_nombre", "").lower()
    print(f"[OK] Duplicacion independiente completada (ID={id_copia_dir}, Propietario={copia_dir['username']}).")

    # 9. Presencia activa y latidos en tiempo real (Heartbeats)
    latido_aday = registrar_latido_presencia(plan_id, "aday", "Mtra. Aday", "Docente", "Sesion 2")
    latido_dir = registrar_latido_presencia(plan_id, "director", "Director Guillermo", "Director", "Co-diseno")
    latido_atp = registrar_latido_presencia(plan_id, "apoyo_pedagogico", "Mtra. Valeria", "ATP", "Ajustes DUA")

    colaboradores_activos = obtener_colaboradores_activos(plan_id)
    nombres_activos = [c["nombre_usuario"] for c in colaboradores_activos]
    assert "Mtra. Aday" in nombres_activos
    assert "Director Guillermo" in nombres_activos
    assert "Mtra. Valeria" in nombres_activos
    print(f"[OK] Presencia en vivo detectada: {len(colaboradores_activos)} colaboradores activos en linea: {nombres_activos}")

    # Limpieza de presencia cuando un usuario sale
    limpiar_presencia_usuario(plan_id, "director")
    colaboradores_post = obtener_colaboradores_activos(plan_id)
    assert "Director Guillermo" not in [c["nombre_usuario"] for c in colaboradores_post]
    print("[OK] Cierre de sesion y limpieza de presencia en tiempo real verificado.")

    # 10. Muro de comentarios y acuerdos pedagogicos colegiados
    com1_id = agregar_comentario_colaborativo(
        planeacion_id=plan_id,
        username="director",
        nombre_usuario="Director Guillermo",
        rol="Director de Escuela",
        tipo="Aprobacion Directiva",
        comentario="Excelente alineacion con el Programa Analitico. Sugiero agregar lista de cotejo en sesion 4."
    )
    com2_id = agregar_comentario_colaborativo(
        planeacion_id=plan_id,
        username="apoyo_pedagogico",
        nombre_usuario="Mtra. Valeria",
        rol="ATP / Inclusion",
        tipo="Ajuste DUA / Inclusion",
        comentario="Para los alumnos con barreras de aprendizaje, agregar material pictografico en la actividad 2."
    )
    assert com1_id > 0 and com2_id > 0

    lista_comentarios = listar_comentarios_colaborativos(plan_id)
    assert len(lista_comentarios) == 2
    print(f"[OK] {len(lista_comentarios)} comentarios y acuerdos colegiados registrados correctamente.")

    # 11. Historial de colaboracion y auditoria
    historial = obtener_historial_colaboracion(plan_id)
    assert historial["total_cambios"] >= 2
    assert historial["total_comentarios"] == 2
    assert "aday" in historial["colaboradores"]
    print(f"[OK] Auditoria colegiada completa: {historial['total_cambios']} versiones, {historial['total_comentarios']} comentarios.")

    print("\n=== TODAS LAS PRUEBAS DE LA TAREA 84 PASARON AL 100% ===")

if __name__ == "__main__":
    test_task_84()

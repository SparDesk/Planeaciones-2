"""
test_task_92.py
Pruebas automatizadas para la Tarea 92:
1. Selector de Base Estricta dinámico en app.py (Programa Analítico / Sintético subido).
2. Prioridad Absoluta (Base Estricta) en gemini_engine.py para gobernar Contenidos, PDA y Problemáticas.
3. Validación Visual destacada del archivo activo tanto en configuración como en resultados.
"""
import unittest
import inspect
from unittest.mock import patch, MagicMock

import gemini_engine


class TestTask92BaseEstricta(unittest.TestCase):
    def test_gemini_engine_signature_and_prompt(self):
        """Verifica que generate_planeacion acepte los parámetros de Base Estricta y arme el prompt con Prioridad Absoluta."""
        sig = inspect.signature(gemini_engine.generate_planeacion)
        self.assertIn("archivo_base_estricta", sig.parameters, "Falta archivo_base_estricta en generate_planeacion")
        self.assertIn("contenido_base_estricta", sig.parameters, "Falta contenido_base_estricta en generate_planeacion")
        self.assertIn("modo_base_estricta", sig.parameters, "Falta modo_base_estricta en generate_planeacion")

        mock_content = "CONTENIDO_ESCOLAR_REVOLUCION_1910: PDA 6° grado sobre participación comunitaria y huerto escolar."
        mock_filename = "Programa_Analitico_Escuela_Revolucion_1910.pdf"

        # Simular llamada a generate_planeacion con modo_base_estricta activo
        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_response = MagicMock()
            mock_response.text = "Planeación generada exitosamente con Base Estricta."
            mock_client.models.generate_content.return_value = mock_response

            plan, prompt = gemini_engine.generate_planeacion(
                datos_escuela={
                    "nombre": "Escuela Primaria Revolución Social de 1910",
                    "cct": "10EPR0361N",
                    "zona": "49",
                    "sector": "02",
                    "docente": "Maestra Aday Domínguez Domínguez",
                    "grado": "6° Grado",
                    "grupo": "A",
                    "turno": "Matutino",
                    "ciclo": "2026-2027",
                    "temporalidad": "Semanal"
                },
                campos_formativos=["Lenguajes", "Saberes y Pensamiento Científico"],
                metodologia=["Aprendizaje Basado en Proyectos Comunitarios"],
                ejes_articuladores=["Pensamiento crítico", "Apropiación de las culturas"],
                contenidos_pda=[{"campo": "Lenguajes", "contenido": "La comunidad", "pda": "Investiga en su comunidad"}],
                directrices_docente="Enfocar en proyectos comunitarios",
                contexto_archivos="",
                libros_seleccionados=["Proyectos Comunitarios"],
                guia_cte="Guía CTE",
                dias_seleccionados=["Lunes", "Martes"],
                semana_seleccionada=6,
                mes_seleccionado="Octubre",
                año_seleccionado=2026,
                api_key="TEST_FAKE_KEY",
                dossier_busqueda={"archivos_consultados": [], "pda_4campos": []},
                archivo_base_estricta=mock_filename,
                contenido_base_estricta=mock_content,
                modo_base_estricta=True
            )

            # Validar directrices de Prioridad Absoluta en el prompt enviado a Gemini
            self.assertIn("DIRECTRIZ SUPREMA DE PRIORIDAD ABSOLUTA - BASE ESTRICTA OBLIGATORIA DEL DOCENTE", prompt)
            self.assertIn(mock_filename, prompt)
            self.assertIn(mock_content, prompt)
            self.assertIn("FUENTE ESTRICTA, EXCLUSIVA Y", prompt)
            self.assertIn("QUEDA TOTALMENTE PROHIBIDO recurrir a plantillas genéricas", prompt)

    def test_app_py_selector_and_visual_validation(self):
        """Verifica que app.py contenga el selector dinámico de Base Estricta y las validaciones visuales."""
        with open("app.py", "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        # 1. Selector dinámico
        self.assertIn("Selector de Base Estricta", code)
        self.assertIn("archivos_disponibles_estrictos", code)
        self.assertIn("sel_base_estricta", code)
        self.assertIn("chk_prioridad_absoluta", code)

        # 2. Prioridad Absoluta pasada al motor de generación
        self.assertIn("archivo_base_estricta=st.session_state.get(\"archivo_base_estricta_activo\")", code)
        self.assertIn("contenido_base_estricta=st.session_state.get(\"contenido_base_estricta_activo\")", code)
        self.assertIn("modo_base_estricta=st.session_state.get(\"modo_base_estricta_activo\", False)", code)

        # 3. Validación visual en interfaz (Sección 2 y Sección 4)
        self.assertIn("ARCHIVO ACTIVO RIGIDOR:", code)
        self.assertIn("BASE ESTRICTA VINCULADA", code)
        self.assertIn("ARCHIVO ACTIVO RECTOR (BASE ESTRICTA):", code)
        self.assertIn("PRIORIDAD ABSOLUTA ACTIVA", code)


if __name__ == "__main__":
    unittest.main()

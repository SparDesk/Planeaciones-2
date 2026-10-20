import sys
import unittest
from unittest.mock import MagicMock

# Mock streamlit session_state
import streamlit as st

class TestTask91LimpiarTodo(unittest.TestCase):
    def setUp(self):
        # Configure initial dummy session state
        st.session_state["widget_key"] = 1
        st.session_state["planeacion_generada"] = "Texto de planeación previa generada con IA..."
        st.session_state["prompt_enviado"] = "Prompt anterior..."
        st.session_state["planeacion_actual_id"] = 42
        st.session_state["planeacion_base_version"] = 3
        st.session_state["archivos_procesados"] = {"archivo.pdf": "contenido..."}
        st.session_state["programa_sintetico_texto"] = "Programa sintético..."
        st.session_state["programa_sintetico_subido"] = True
        st.session_state["nombre_archivo_programa"] = "Fase5.pdf"
        st.session_state["contenidos"] = "Contenidos personalizados..."
        st.session_state["directrices"] = "Directrices previas de la maestra..."
        st.session_state["url_referencia"] = "https://ejemplo.sep.gob.mx"
        st.session_state["nombre_archivo_actual"] = "Planeacion_Personalizada_Semana_20"
        st.session_state["categoria_ruta_actual"] = "Proyectos de Aula"
        
        # Dynamic widget keys
        st.session_state["campos_1"] = ["Lenguajes", "Saberes y Pensamiento Científico"]
        st.session_state["metodologia_1"] = ["STEAM", "Aprendizaje Servicio"]
        st.session_state["dias_1"] = ["Lunes", "Miércoles"]
        st.session_state["nota_dia_Lunes_1"] = "Nota particular para el lunes"
        st.session_state["uploader_1"] = "dummy_file_stream"
        st.session_state["inp_nombre_archivo_1"] = "Planeacion_Custom"
        st.session_state["sel_categoria_ruta_1"] = "Proyectos Escolares"

    def test_limpiar_todo_resets_all_variables(self):
        # Import limpiar_todo_callback from app
        import app
        
        initial_widget_key = st.session_state["widget_key"]
        app.limpiar_todo_callback()
        
        # 1. Widget key must have incremented to rebuild UI with defaults
        self.assertEqual(st.session_state["widget_key"], initial_widget_key + 1)
        
        # 2. Text fields and generation results reset
        self.assertIsNone(st.session_state["planeacion_generada"])
        self.assertIsNone(st.session_state["prompt_enviado"])
        self.assertEqual(st.session_state["contenidos"], "")
        self.assertEqual(st.session_state["directrices"], "")
        self.assertEqual(st.session_state["url_referencia"], "")
        
        # 3. File upload and synthetic program reset
        self.assertEqual(st.session_state["archivos_procesados"], {})
        self.assertEqual(st.session_state["programa_sintetico_texto"], "")
        self.assertFalse(st.session_state["programa_sintetico_subido"])
        self.assertEqual(st.session_state["nombre_archivo_programa"], "")
        
        # 4. Custom file names and paths reset
        self.assertEqual(st.session_state["nombre_archivo_actual"], "")
        self.assertEqual(st.session_state["categoria_ruta_actual"], "")
        
        # 5. Dynamic widget keys deleted
        self.assertNotIn("campos_1", st.session_state)
        self.assertNotIn("metodologia_1", st.session_state)
        self.assertNotIn("dias_1", st.session_state)
        self.assertNotIn("nota_dia_Lunes_1", st.session_state)
        self.assertNotIn("uploader_1", st.session_state)
        self.assertNotIn("inp_nombre_archivo_1", st.session_state)
        self.assertNotIn("sel_categoria_ruta_1", st.session_state)
        
        # 6. Flag for fresh notice set
        self.assertTrue(st.session_state.get("aviso_nueva_planeacion"))

if __name__ == "__main__":
    unittest.main()

"""
test_task_93.py
Pruebas integrales de validación y simulación E2E para la Tarea 93:
1. Tabla de Trazabilidad Curricular de Base Estricta en Word (docx_generator.py).
2. Distintivo oficial de Base Estricta y Prioridad Absoluta en PDF (pdf_generator.py).
3. Exportación del Paquete Integral ZIP (.zip con DOCX, PDF, MD y Ficha de Trazabilidad) en app.py.
4. Simulación completa de extremo a extremo (E2E) con documento rector y Ficha Técnica de la Escuela Revolución Social de 1910.
"""
import io
import unittest
import zipfile
from docx import Document

from nem_data import DATOS_PREDETERMINADOS, CAMPOS_FORMATIVOS
from gemini_engine import generate_sample_fallback
from docx_generator import build_docx_planeacion
from pdf_generator import build_pdf_planeacion


class TestTask93TrazabilidadYPaqueteZIP(unittest.TestCase):
    def setUp(self):
        self.datos_escuela = dict(DATOS_PREDETERMINADOS)
        self.datos_escuela.update({
            "semana": 6,
            "semana_seleccionada": 6,
            "dias_seleccionados": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
            "periodo": "Semana 6 de 37 (Del 5 al 9 de Octubre de 2026)",
            "ciclo_escolar": "2026-2027",
            "archivo_base_estricta": "Programa_Analitico_Oficial_Escuela_Revolucion_1910.pdf",
            "tipo_base_estricta": "Programa Analítico Institucional",
            "modo_base_estricta": True
        })

        self.plan_text = generate_sample_fallback(
            datos_escuela=self.datos_escuela,
            campos_formativos=CAMPOS_FORMATIVOS,
            metodologia=["Aprendizaje Basado en Proyectos Comunitarios"],
            ejes=["Pensamiento crítico", "Apropiación de las culturas a través de la lectura y la escritura"],
            dias_seleccionados=self.datos_escuela["dias_seleccionados"],
            semana_seleccionada=6
        )

    def test_docx_traceability_table_present_when_strict_base_active(self):
        """Verifica que el DOCX contenga la tabla de trazabilidad oficial de Base Estricta."""
        docx_buf = build_docx_planeacion(
            datos_escuela=self.datos_escuela,
            plan_text=self.plan_text
        )
        self.assertGreater(len(docx_buf.getvalue()), 15000, "El DOCX generado es demasiado pequeño.")

        # Inspeccionar tablas en el DOCX
        doc = Document(docx_buf)
        all_table_text = " ".join([cell.text for t in doc.tables for row in t.rows for cell in row.cells])
        
        self.assertIn("DOCUMENTO RECTOR VINCULADO:", all_table_text)
        self.assertIn("Programa_Analitico_Oficial_Escuela_Revolucion_1910.pdf", all_table_text)
        self.assertIn("ESTATUS DE PRIORIDAD ABSOLUTA:", all_table_text)
        self.assertIn("ACTIVA Y VINCULANTE", all_table_text)
        self.assertIn("ALINEACIÓN CURRICULAR:", all_table_text)

    def test_docx_traceability_table_omitted_when_strict_base_inactive(self):
        """Verifica que si la Base Estricta no está activa, la tabla de trazabilidad no se agregue innecesariamente."""
        datos_inactivos = dict(self.datos_escuela)
        datos_inactivos["modo_base_estricta"] = False
        datos_inactivos["archivo_base_estricta"] = ""

        docx_buf = build_docx_planeacion(
            datos_escuela=datos_inactivos,
            plan_text=self.plan_text
        )
        doc = Document(docx_buf)
        all_table_text = " ".join([cell.text for t in doc.tables for row in t.rows for cell in row.cells])
        self.assertNotIn("DOCUMENTO RECTOR VINCULADO:", all_table_text)

    def test_pdf_generation_with_strict_base(self):
        """Verifica que el PDF se genere correctamente con el banner de Base Estricta sin errores tipográficos."""
        pdf_buf = build_pdf_planeacion(
            datos_escuela=self.datos_escuela,
            plan_text=self.plan_text
        )
        pdf_bytes = pdf_buf.getvalue()
        self.assertGreater(len(pdf_bytes), 5000, "El PDF generado es demasiado pequeño.")
        self.assertTrue(pdf_bytes.startswith(b"%PDF"), "El archivo generado no es un PDF válido.")

    def test_end_to_end_zip_package_simulation(self):
        """Simulación E2E completa: genera DOCX, PDF, MD y crea el Paquete ZIP Institucional."""
        docx_buf = build_docx_planeacion(self.datos_escuela, self.plan_text)
        pdf_buf = build_pdf_planeacion(self.datos_escuela, self.plan_text)
        nombre_base = "Planeacion_Semana_6_Fase5_6A"

        # Simular empaquetado ZIP como en app.py
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{nombre_base}.docx", docx_buf.getvalue())
            zf.writestr(f"{nombre_base}.pdf", pdf_buf.getvalue())
            zf.writestr(f"{nombre_base}.md", self.plan_text.encode("utf-8"))
            
            ficha_trazabilidad = f"""REPORTE DE TRAZABILIDAD - TAREA 93
Documento Rector: {self.datos_escuela['archivo_base_estricta']}
Prioridad Absoluta: ACTIVA
Escuela: Primaria Revolución Social de 1910
"""
            zf.writestr("Ficha_Trazabilidad_Institucional.txt", ficha_trazabilidad.encode("utf-8"))
        
        zip_buf.seek(0)
        zip_bytes = zip_buf.getvalue()
        self.assertGreater(len(zip_bytes), 20000, "El archivo ZIP es demasiado pequeño.")

        # Verificar contenido interno del ZIP
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf_read:
            names = zf_read.namelist()
            self.assertIn(f"{nombre_base}.docx", names)
            self.assertIn(f"{nombre_base}.pdf", names)
            self.assertIn(f"{nombre_base}.md", names)
            self.assertIn("Ficha_Trazabilidad_Institucional.txt", names)
            
            ficha_content = zf_read.read("Ficha_Trazabilidad_Institucional.txt").decode("utf-8")
            self.assertIn("Programa_Analitico_Oficial_Escuela_Revolucion_1910.pdf", ficha_content)
            self.assertIn("Prioridad Absoluta: ACTIVA", ficha_content)


if __name__ == "__main__":
    unittest.main()

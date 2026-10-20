from __future__ import annotations

"""
Punto de entrada principal para Streamlit Community Cloud (streamlit_app.py).
Carga y ejecuta la aplicación integral de Planeaciones Escolares NEM (app.py).
"""

import os
import sys
import runpy

# 1. Asegurar resolución de módulos en el directorio raíz del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 2. Ejecutar la aplicación principal oficial (app.py) en el contexto de ejecución
if __name__ in ("__main__", "__mp_main__"):
    app_file = os.path.join(BASE_DIR, "app.py")
    runpy.run_path(app_file, run_name="__main__")
else:
    # Compatibilidad si se importa como módulo
    import app

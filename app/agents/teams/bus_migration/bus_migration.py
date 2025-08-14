import os
import logging
import shutil
from .utilities.migration import DummyJsonWorkflow
from ..utilities.save_and_generate_url import save_and_generate_url_s3, eliminar_archivo_temporal
import json
logger = logging.getLogger(__name__)
def eliminar_carpeta_completa(path: str):
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path)
        print(f"Carpeta eliminada: {path}")
    else:
        print(f"La ruta no existe o no es una carpeta: {path}")
def bus_migration_team(input_path_file):
    files = os.listdir(input_path_file)
    esql_path = os.path.join(input_path_file, [f for f in files if f.endswith('.esql')][0])
    xcel_path = os.path.join(input_path_file, [f for f in files if f.endswith('.xlsx')][0])
    logger.info(f"estos son los paths de entrada: {esql_path}, {xcel_path}")
    output_path_base = os.path.join(os.path.dirname(__file__), "tmp", "output")
    os.makedirs(output_path_base, exist_ok=True)
    workflow = DummyJsonWorkflow()    

    # Ejecutar el workflow
    response = workflow.run(
        esql_path=esql_path,
        excel_path=xcel_path,
        output_path_base=output_path_base,
        action_description="""
            realiza la migración de un flujo en formato XML a JSON, tomando como base el archivo de mapeo
            y el archivo de origen, generando el archivo de salida en formato JSON.
            El flujo de origen es un flujo de Oracle Bus, archivo .esql, y el archivo de mapeo es un archivo Excel.
        """,
    )
    print("Response from DummyJsonWorkflow:", json.loads(response.content))
    data = json.loads(response.content)
    file_path = data["file_path"]
    s3_key = f"bus_migration/{os.path.basename(file_path)}"
    url_download = save_and_generate_url_s3(s3_key, file_path)
    user_response = f'''
    ## Migración completada con éxito

El flujo ESQL fue transformado de formato XML a formato JSON utilizando el archivo de mapeo proporcionado. Durante la migración, se identificaron y ajustaron automáticamente los módulos `Request` y `Response`, aplicando los cambios necesarios en las estructuras de datos para que el flujo sea compatible con el nuevo esquema en JSON.

Este proceso garantiza que las asignaciones y referencias dentro del código ESQL respeten la estructura de salida esperada, facilitando su integración con sistemas modernos basados en JSON.

Puedes descargar el archivo migrado desde el siguiente enlace:

[Descargar archivo]({url_download})'''
    return user_response
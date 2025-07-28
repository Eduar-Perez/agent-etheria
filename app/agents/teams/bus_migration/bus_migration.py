import os
import logging
from .utilities.migration import DummyJsonWorkflow

logger = logging.getLogger(__name__)

def bus_migration_team(input_path_file):
    files = os.listdir(input_path_file)
    esql_path = os.path.join(input_path_file, [f for f in files if f.endswith('.esql')][0])
    xcel_path = os.path.join(input_path_file, [f for f in files if f.endswith('.xlsx')][0])
    logger.info(f"estos son los paths de entrada: {esql_path}, {xcel_path}")
    output_path_base = os.path.join(os.path.dirname(__file__), "tmp", "output")
    os.makedirs(output_path_base, exist_ok=True)
    workflow = DummyJsonWorkflow()    

    # Ejecutar el workflow
    result = workflow.run(
        esql_path=esql_path,
        excel_path=xcel_path,
        output_path_base=output_path_base,
        action_description="""
            realiza la migración de un flujo en formato XML a JSON, tomando como base el archivo de mapeo
            y el archivo de origen, generando el archivo de salida en formato JSON.
            El flujo de origen es un flujo de Oracle Bus, archivo .esql, y el archivo de mapeo es un archivo Excel.
        """,
    )

    print("\nResultado del agente:\n")
    print(result.content)
    return result.content if hasattr(result, "content") else "null"
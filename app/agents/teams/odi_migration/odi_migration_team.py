import os
import json
from langchain_aws import ChatBedrock
from .utilities.xml_to_json import convert_all_xml_to_json
from .utilities.dtsge_agent_analyzer import ejecutar_grafo
from .utilities.dtsge_agent_descripcion_tarea import describir_etl_desde_proceso
# from python.DataStageAgentAnalisisJSON import ejecutar_grafo
# from python.DataStageAgentDescripcionTarea import describir_etl_desde_proceso
import logging

MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
logger = logging.getLogger(__name__)


def get_prompt_path(filename):
    base_dir = os.path.dirname(
        os.path.abspath(__file__)
    )  # directorio actual del script
    return os.path.join(base_dir, "prompts", filename)


def run_notebook(notebook_name, nombre_proceso=None):
    logger.info(f"Ejecutando: {notebook_name}")
    if not os.path.exists(notebook_name):
        logger.error(f"No se encontró el archivo: {notebook_name}")
        return
    try:
        with open(notebook_name, "r", encoding="utf-8") as f:
            nb = json.load(f)
        code_cells = [
            cell for cell in nb.get("cells", []) if cell.get("cell_type") == "code"
        ]
        code = ""
        for cell in code_cells:
            code += "".join(cell.get("source", [])) + "\n"
        exec_globals = {}
        if nombre_proceso:
            exec_globals["nombre_proceso_ppal"] = nombre_proceso
        exec(code, exec_globals)
    except Exception as e:
        logger.error(f"Error ejecutando {notebook_name}: {e}")


def run_pipeline(ruta_json, nombre_proceso):
    """
    Ejecuta el pipeline completo: análisis y agentes/notebooks.
    """
    run_notebook("DataStageAgentExtraccion.ipynb", nombre_proceso=nombre_proceso)
    run_notebook("DataStageAgentTransform.ipynb", nombre_proceso=nombre_proceso)
    run_notebook("DataStageAgentJoin.ipynb", nombre_proceso=nombre_proceso)
    run_notebook("DatastageAgentInsert.ipynb", nombre_proceso=nombre_proceso)
    return "Traducción completa ejecutada para el proceso."


def get_bedrock_llm():
    return ChatBedrock(
        model_id=MODEL,
        model_kwargs={
            "max_tokens": 4096,
            "temperature": 0,
            "anthropic_version": "bedrock-2023-05-31",
        },
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


def user_explanation(technical_explanation: str) -> str:
    # Lee el prompt amigable
    # prompt_path = os.path.join('prompts', 'user_experto_with_multiple_task.txt')
    prompt_path =  os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prompts', 'experto_dastage_extraccion.txt'))
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    # prompt = prompt_template.format(technical_explanation=technical_explanation, nombre_proceso_ppal=nombre_proceso_ppal)
    prompt = prompt_template.format(technical_explanation=technical_explanation)
    llm = get_bedrock_llm()
    respuesta = llm.invoke([{"role": "user", "content": prompt}])
    return respuesta.content if hasattr(respuesta, "content") else str(respuesta)


def correct_prompt_datastage(answer: str) -> str:
    """
    Esa función retorna una respeusta de 1 o True si el cliente esta duacuerdo
    con el proceso de migración, sino ajusta o corrige el propmt de entrada a
    los agentes de migración a dataStage a partir de la respuesta del usuario.
    """
    prompt_path = os.path.join("prompts", "correct_propmt_dataStage.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()
    prompt = prompt_template.format(answer=answer)
    llm = get_bedrock_llm()
    respuesta = llm.invoke([{"role": "user", "content": prompt}])
    return respuesta.content if hasattr(respuesta, "content") else str(respuesta)


def load_process(nombre_proceso_ppal):
    ruta = os.path.join("prompts_datastage", nombre_proceso_ppal)
    # Busca todos los archivos de descripción generados
    archivos = [
        f
        for f in os.listdir(ruta)
        if f.startswith("descripcion_") and f.endswith(".json")
    ]
    explicaciones = {}
    for archivo in archivos:
        ruta_archivo = os.path.join(ruta, archivo)
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
        explicaciones[archivo] = data
        break  # eliminar para tomar todas las tareas
    return explicaciones


def odi_migration_team(xml_input_folder):
    json_odi_interpeted = os.path.join(
        os.path.dirname(__file__), "..", "..", "tmp", "odi_interpeted_json"
    )
    xml_inputs = [f for f in os.listdir(xml_input_folder) if f.endswith(".xml")]
    for xml_input in xml_inputs:
        nombre_proceso = xml_input.split(".")[0]
        json_filename = convert_all_xml_to_json(
            nombre_proceso, xml_input_folder, json_odi_interpeted
        )
        ruta_json = f"{json_odi_interpeted}/{json_filename}"
        if not os.path.exists(ruta_json):
            print(f"No se encontró el archivo: {ruta_json}")
            return
        print(f"\n Estamos traduciendo el proceso: '{nombre_proceso}' ...\n")
        ejecutar_grafo(ruta_json)
        print("Creando descripción tecnica del proceso ...\n")
        describir_etl_desde_proceso(json_filename[:-5])
        # Generar y mostrar explicación
        tecnical_explanation = load_process(json_filename[:-5])  # Elimina '.json' del final
        print("traduciendo respuesta para el usuario...")
        user_explanation_text = user_explanation(tecnical_explanation)
        print("=========================================")
        print(user_explanation_text)
        print("=========================================")
        return user_explanation_text
        # print("\n¿Apruebas esta migración? Si no estás de acuerdo, escribe tus comentarios")
        # respuesta = input("> ").strip().lower()
        # if respuesta == "si":
        #     print("\n Listo! empezamos la traducción ...\n")
        #     # resultado = run_pipeline(ruta_json, nombre_proceso)
        #     # print(resultado)
        #     print("\n Proceso finalizado. Puedes revisar los resultados.")
        # else:
        #     print("\n Entendido... Vamos a volver a procesar tu información.")

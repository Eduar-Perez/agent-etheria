import os
import json
import logging
import boto3
from botocore.config import Config
from langchain_aws import ChatBedrock
from .utilities.xml_to_json import convert_all_xml_to_json
from .utilities.dtsge_agent_analyzer import ejecutar_grafo
from .utilities.dtsge_agent_descripcion_tarea import describir_etl_desde_proceso
from .utilities.DataStageAgentExtraccion import run as run_extraccion
from .utilities.DataStageAgentTransform import run as run_transform
from .utilities.DataStageAgentJoin import run as run_join
from .utilities.DatastageAgentInsert import run as run_insert
from ..utilities.save_and_generate_url import save_and_generate_url_s3

MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
logger = logging.getLogger(__name__)


def get_prompt_path(filename):
    base_dir = os.path.dirname(
        os.path.abspath(__file__)
    )  # directorio actual del script
    return os.path.join(base_dir, "prompts", filename)



def run_pipeline(ruta_json, nombre_proceso):
    """
    Ejecuta el pipeline completo: análisis y agentes/notebooks.
    """
    run_extraccion(nombre_proceso)
    run_transform(nombre_proceso)
    run_join(nombre_proceso)
    run_insert(nombre_proceso)
    return "Traducción completa ejecutada para el proceso."


def get_bedrock_llm():
    boto3_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        config=Config(read_timeout=180, connect_timeout=30)
    )

    return ChatBedrock(
        client=boto3_client,
        model_id=MODEL,
        model_kwargs={
            "max_tokens": 4096,
            "temperature": 0,
            "anthropic_version": "bedrock-2023-05-31",
        }
    )


def user_explanation(technical_explanation: str) -> str:
    # Lee el prompt amigable
    # prompt_path = os.path.join('prompts', 'user_experto_with_multiple_task.txt')
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'user_experto_3.txt')
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
    base_tmp = os.path.abspath(os.path.join(os.path.dirname(__file__), "tmp"))
    ruta = os.path.join(base_tmp, "prompts_datastage", nombre_proceso_ppal)
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No se encontró la ruta esperada: {ruta}")

    archivos = [
        f for f in os.listdir(ruta)
        if f.startswith("descripcion_") and f.endswith(".json")
    ]
    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos de descripción en: {ruta}")

    explicaciones = {}
    for archivo in archivos:
        ruta_archivo = os.path.join(ruta, archivo)
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
        explicaciones[archivo] = data
        #break  #  Eliminar si quieres procesar todos los archivos
    return explicaciones


def odi_migration_team(xml_input_folder):
    json_odi_interpeted = os.path.join(os.path.dirname(__file__), "tmp", "odi_interpeted_json")
    os.makedirs(json_odi_interpeted, exist_ok=True)

    xml_inputs = [f for f in os.listdir(xml_input_folder) if f.endswith(".xml")]
    if len(xml_inputs) < 1:
        return "No se encontraron archivos .xml en la carpeta proporcionada"
    response = []
    for xml_input in xml_inputs:
        nombre_proceso = xml_input.split(".")[0]
        #Inteprretar XML y maperarlo en json
        json_filename = convert_all_xml_to_json(
            nombre_proceso, xml_input_folder, json_odi_interpeted
        )
        ruta_json = f"{json_odi_interpeted}/{json_filename}"
        if not os.path.exists(ruta_json):
            print(f"No se encontró el archivo: {ruta_json}")
            return
        print(f"\n Estamos traduciendo el proceso: '{nombre_proceso}' ...\n")
        # Ejecutar el grafo de DataStage
        ejecutar_grafo(ruta_json)
        print("Creando descripción tecnica del proceso ...\n")
        with open(ruta_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        nombre_proceso_ppal = data.get("SCEN_NAME")

        # describir_etl_desde_proceso(json_filename[:-5])
        describir_etl_desde_proceso(nombre_proceso_ppal)
        
        # Generar y mostrar explicación
        tecnical_explanation = load_process(nombre_proceso_ppal)
        # tecnical_explanation = load_process(json_filename[:-5])  # Elimina '.json' del final
        print("traduciendo respuesta para el usuario...")
        user_explanation_text = user_explanation(tecnical_explanation)
        response.append(user_explanation_text)
        # print("=========================================")
        print("\EXPLICACION A USUARIOS\n", user_explanation_text)
        # print("=========================================")
        # return user_explanation_text

        print("\n Listo! empezamos la traducción ...\n")
        resultado = run_pipeline(ruta_json, nombre_proceso_ppal)
        print(resultado)
        print("\n Proceso finalizado. Puedes revisar los resultados.")
        break
    return ["\n\n".join(response)]

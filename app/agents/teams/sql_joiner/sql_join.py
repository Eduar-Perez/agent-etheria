import os
import re
import json
import boto3
import logging
import textwrap

# from dotenv import load_dotenv
from botocore.config import Config
from langchain_aws import ChatBedrock

# Configurar el logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Cargar variables de entorno desde el archivo .env
# dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
# load_dotenv(dotenv_path)

MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

def get_prompt_path(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))  # directorio actual del script
    return os.path.join(base_dir, "prompts", filename)

def get_bedrock_llm():
    """Inicializa el cliente de Bedrock y devuelve el modelo de lenguaje."""
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
        config=Config(read_timeout=300, connect_timeout=60)
    )
    return ChatBedrock(
        model_id=MODEL_ID,
        model_kwargs={
            "max_tokens": 8192,
            "temperature": 0,
            "anthropic_version": "bedrock-2023-05-31",
        },
        client=client,
    )


def join_sql_scripts(folder_path, output_filename="join_sql_files_no_errors.txt"):
    """Une todos los archivos .sql de una carpeta en un solo archivo de texto."""
    sql_files = sorted(f for f in os.listdir(folder_path) if f.endswith(".sql"))
    combined_sql = ""

    with open(output_filename, "w", encoding="utf-8") as output_file:
        for i, filename in enumerate(sql_files, 1):
            path = os.path.join(folder_path, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                header = f"--- SCRIPT {i}: {filename} ---\n"
                output_file.write(header + content + "\n\n")
                combined_sql += header + content + "\n\n"
    return combined_sql, sql_files


def request_grouping(sql_text: str) -> str:
    """Envía los scripts SQL unidos al modelo para que agrupe por compatibilidad."""
    prompt_path = get_prompt_path("detect_sqls_to_join.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        template = file.read()
    prompt = template.format(sql_join=sql_text)
    llm = get_bedrock_llm()
    response = llm.invoke([{"role": "user", "content": prompt}])
    return str(response.content) if hasattr(response, "content") else str(response)


def clean_and_parse_json(raw_text: str) -> dict:
    """Limpia y convierte una respuesta con JSON en un objeto de Python."""
    cleaned = (
        re.sub(r"```(?:json)?", "", raw_text, flags=re.IGNORECASE)
        .replace("```", "")
        .strip()
    )
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No se encontró bloque JSON válido")
    json_str = cleaned[start: end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error("Error al parsear JSON:\n", json_str[:1000])
        raise ValueError(f"JSON inválido: {e}") from e


def save_merged_sql(
    sql_text,
    subfolder: str,
    group_number: str,
    group_name: str,
    folder_name="SQL_unificados",
):
    """Guarda el SQL unificado en una carpeta organizada por grupos."""
    os.makedirs(folder_name, exist_ok=True)
    save_path = os.path.join(folder_name, subfolder)
    os.makedirs(save_path, exist_ok=True)

    safe_name = re.sub(r"\W+", "_", group_name)
    file_name = f"{group_number}_{safe_name}.sql"
    full_path = os.path.join(save_path, file_name)

    with open(full_path, "w", encoding="utf-8") as file:
        file.write(f"-- Grupo: {group_number}\n\n")
        file.write(sql_text)

    return [full_path]


# las function: def show_grouping_explanation(data: dict):
#     """Imprime la explicación generada por el modelo sobre cómo agrupó los scripts."""
#     print("\n" + "=" * 60)
#     print("EXPLICACIÓN DEL PROCESO DE AGRUPACIÓN")
#     print("=" * 60)

#     print(f"\n{data.get('explicacion', '').strip()}\n")

#     groups = data.get("grupos", [])
#     if groups:
#         print("Grupos detectados:")
#         for group in groups:
#             print(f"\n {group['nombre_grupo']}:")
#             print(f"   Explicación: {group.get('explicacion_union', 'No disponible')}")
#             for script in group["scripts"]:
#                 print(f"   - {script}")
#     else:
#         print("No se detectaron grupos.")

#     ungrouped = data.get("no_agrupados", [])
#     if ungrouped:
#         print("\nReportes no agrupados:")
#         for entry in ungrouped:
#             print(f"   - {entry['script']}: {entry['razon']}")
#     else:
#         print("\nTodos los scripts fueron agrupados correctamente.")

#     print("\n" + "=" * 60 + "\n")


def show_grouping_explanation(data: dict) -> str:
    """Genera un resumen explicativo en texto sobre cómo se agruparon los scripts."""
    lines = []
    lines.append("=" * 60)
    lines.append("EXPLICACIÓN DEL PROCESO DE AGRUPACIÓN")
    lines.append("=" * 60)
    lines.append("")

    lines.append(data.get("explicacion", "").strip())

    groups = data.get("grupos", [])
    if groups:
        lines.append("\nGrupos detectados:")
        for group in groups:
            lines.append(f"\n{group['nombre_grupo']}:")
            lines.append(
                f"  Explicación: {group.get('explicacion_union', 'No disponible')}"
            )
            for script in group["scripts"]:
                lines.append(f"  - {script}")
    else:
        lines.append("\nNo se detectaron grupos.")

    ungrouped = data.get("no_agrupados", [])
    if ungrouped:
        lines.append("\nReportes no agrupados:")
        for entry in ungrouped:
            lines.append(f"  - {entry['script']}: {entry['razon']}")
    else:
        lines.append("\nTodos los scripts fueron agrupados correctamente.")

    lines.append("\n" + "=" * 60 + "\n")
    return "\n".join(lines)


def separate_sql_by_keyword(source_folder, output_folder="./tmp/SQL_separados"):
    """
    Separa los scripts SQL en carpetas organizadas por contenido:
    - "ADMODS" → ODS
    - "CHEQUES_GERENCIA" → CBS - CHEQUES_GERENCIA
    - Otro → CBS - PRODUCTOS PASIVAS
    """
    for file in sorted(f for f in os.listdir(source_folder) if f.endswith(".sql")):
        full_path = os.path.join(source_folder, file)
        with open(full_path, "r", encoding="utf-8") as input_file:
            content = input_file.read()

            if "ADMODS" in content:
                category = "ODS"
            elif "CHEQUES_GERENCIA" in content:
                category = "CBS - CHEQUES_GERENCIA"
            else:
                category = "CBS - PRODUCTOS PASIVAS"

            output_path = os.path.join(output_folder, category, file)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as output_file:
                output_file.write(content)

    return output_folder


def merge_sql_group(
    folder_path, files_to_merge, output_filename="join_sql_files_no_errors.txt"
):
    """Une scripts SQL específicos en un solo bloque de texto."""
    files_to_merge.sort()
    combined = ""

    with open(output_filename, "w", encoding="utf-8") as output:
        for i, filename in enumerate(files_to_merge, 1):
            full_path = os.path.join(folder_path, filename)
            with open(full_path, "r", encoding="utf-8") as file:
                content = file.read()
                header = f"--- SCRIPT {i}: {filename} ---\n"
                output.write(header + content + "\n\n")
                combined += header + content + "\n\n"
    return combined


def unify_sqls_with_model(sql_block: str) -> str:
    """Envía los scripts agrupados al modelo para que los combine en uno solo."""
    prompt_path = get_prompt_path("join_sqls.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        template = file.read()
    prompt = template.format(sql_join=sql_block)
    llm = get_bedrock_llm()
    response = llm.invoke([{"role": "user", "content": prompt}])
    return response.content if hasattr(response, "content") else str(response)


def optimze_sql(sql_text: str) -> str:
    """Optimiza el SQL unificado enviándolo al modelo."""
    prompt_path = get_prompt_path("optimize_sql.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        template = file.read()
    prompt = template.format(sql_to_optimize=sql_text)
    llm = get_bedrock_llm()
    response = llm.invoke([{"role": "user", "content": prompt}])
    return response.content if hasattr(response, "content") else str(response)


def join_sql_scripts_team(folder_path):
    logger.info("Optimiza tus archivos de SQL")
    input_folder = folder_path
    absolute_path = os.path.abspath(f"../app/{input_folder}")
    if not os.path.exists(absolute_path):
        logger.error(f"No se encontró la carpeta: {absolute_path}")
        return
    separated_folder = separate_sql_by_keyword(absolute_path)
    sql_unified = {}
    grouping_explanation = {}
    for category in os.listdir(separated_folder):
        category_path = os.path.join(separated_folder, category)
        sql_combined, file_list = join_sql_scripts(category_path)
        logger.info(f"\nAnalizano archivos de {category}:\n")
        for i, file in enumerate(file_list, 1):
            logger.info(f"  {i}. {file}")
        logger.info("\nEnviando a modelo...")
        try:
            logger.info("\n" + "=" * 60)
            logger.info("Analizando cuales scripts deben unirse...")
            raw_response = request_grouping(sql_combined)
            parsed_json = clean_and_parse_json(raw_response)
            grouping_explanation[category] = show_grouping_explanation(parsed_json)
            for i, group in enumerate(parsed_json.get("grupos", []), 1):
                logger.info(f"\nUnificando scripts de {category}...")
                logger.info(f"Convirtiendo {group['nombre_grupo']}")
                group_scripts = list(group["scripts"])
                merged_sql = merge_sql_group(category_path, group_scripts)
                unified_sql = unify_sqls_with_model(merged_sql)
                sql_unified[category] = unified_sql
                # saved_paths = save_merged_sql(unified_sql, category, str(i), group["nombre_grupo"])
        # print("\nLos archivos SQL unificados se guardaron en:")
        # for path in saved_paths:
        #     print(f" - {path}")
        except ValueError as err:
            logger.error("Error al procesar la respuesta del modelo:")
            logger.error(err)
    return [sql_unified, grouping_explanation]

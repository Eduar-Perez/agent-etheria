import os
import re
import json
import boto3
import logging
from typing import Dict, List
from ..utilities.save_and_generate_url import save_and_generate_url_s3
from botocore.config import Config
from langchain_aws import ChatBedrock

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MODEL_ID = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# ---------- Infra / helpers ----------

def get_prompt_path(filename: str) -> str:
    """Resuelve ruta absoluta del archivo de prompt junto al módulo actual."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "prompts", filename)

def get_bedrock_llm():
    """Inicializa cliente de Bedrock usando el rol/credenciales del entorno."""
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
        config=Config(read_timeout=300, connect_timeout=60),
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

# ---------- IO / SQL helpers ----------

def join_sql_scripts(folder_path: str, output_filename: str = "join_sql_files_no_errors.txt"):
    """Concatena todos los .sql de una carpeta (solo de esa carpeta, no recursivo)."""
    sql_files = sorted(f for f in os.listdir(folder_path) if f.endswith(".sql"))
    combined_sql = ""
    with open(output_filename, "w", encoding="utf-8") as out:
        for i, filename in enumerate(sql_files, 1):
            path = os.path.join(folder_path, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            header = f"--- SCRIPT {i}: {filename} ---\n"
            out.write(header + content + "\n\n")
            combined_sql += header + content + "\n\n"
    return combined_sql, sql_files

def request_grouping(sql_text: str) -> str:
    """Pide al modelo que agrupe scripts compatibles."""
    prompt_path = get_prompt_path("detect_sqls_to_join.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        template = file.read()
    prompt = template.format(sql_join=sql_text)
    llm = get_bedrock_llm()
    resp = llm.invoke([{"role": "user", "content": prompt}])
    return str(resp.content) if hasattr(resp, "content") else str(resp)

def clean_and_parse_json(raw_text: str) -> dict:
    """Extrae el bloque JSON de la respuesta del modelo y lo parsea."""
    cleaned = re.sub(r"```(?:json)?", "", raw_text, flags=re.IGNORECASE).replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No se encontró bloque JSON válido")
    json_str = cleaned[start:end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error("Error al parsear JSON:\n%s", json_str[:1000])
        raise ValueError(f"JSON inválido: {e}") from e

def save_merged_sql(
    sql_text: str,
    subfolder: str,
    group_number: str,
    group_name: str,
    folder_name: str = "tmp/SQL_unificados",
) -> str:
    """Guarda el SQL unificado (1 archivo) y retorna la ruta."""
    os.makedirs(folder_name, exist_ok=True)
    save_path = os.path.join(folder_name, subfolder)
    os.makedirs(save_path, exist_ok=True)
    safe_name = re.sub(r"\W+", "_", group_name).strip("_") or "grupo"
    file_name = f"{group_number}_{safe_name}.sql"
    full_path = os.path.join(save_path, file_name)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(f"-- Grupo: {group_number}\n\n")
        f.write(sql_text)
    return full_path

def show_grouping_explanation(data: dict) -> str:
    """Convierte la explicación de agrupación en texto plano."""
    lines = []
    lines.append("=" * 60)
    lines.append("EXPLICACIÓN DEL PROCESO DE AGRUPACIÓN")
    lines.append("=" * 60)
    lines.append("")
    lines.append((data.get("explicacion") or "").strip())

    groups = data.get("grupos", [])
    if groups:
        lines.append("\nGrupos detectados:")
        for group in groups:
            lines.append(f"\n{group.get('nombre_grupo','(sin nombre)')}:")
            lines.append(f"  Explicación: {group.get('explicacion_union', 'No disponible')}")
            for script in group.get("scripts", []):
                lines.append(f"  - {script}")
    else:
        lines.append("\nNo se detectaron grupos.")

    ungrouped = data.get("no_agrupados", [])
    if ungrouped:
        lines.append("\nReportes no agrupados:")
        for entry in ungrouped:
            lines.append(f"  - {entry.get('script','(sin nombre)')}: {entry.get('razon','(sin razón)')}")
    else:
        lines.append("\nTodos los scripts fueron agrupados correctamente.")

    lines.append("\n" + "=" * 60 + "\n")
    return "\n".join(lines)

def separate_sql_by_keyword(source_folder: str) -> str:
    """
    Separa los .sql directos de source_folder según contenido:
      - Contiene 'ADMODS'  -> 'ODS'
      - Contiene 'CHEQUES_GERENCIA' -> 'CBS - CHEQUES_GERENCIA'
      - Otro -> 'CBS - PRODUCTOS PASIVAS'
    Retorna la ruta de la carpeta de salida.
    """
    output_folder = os.path.join(source_folder, "SQL_separados")
    os.makedirs(output_folder, exist_ok=True)

    for file in sorted(f for f in os.listdir(source_folder) if f.endswith(".sql")):
        full_path = os.path.join(source_folder, file)
        with open(full_path, "r", encoding="utf-8", errors="ignore") as inp:
            content = inp.read()

        if re.search(r"\bADMODS\b", content, flags=re.IGNORECASE):
            category = "ODS"
        elif re.search(r"\bCHEQUES?_GERENCIA\b", content, flags=re.IGNORECASE):
            category = "CBS - CHEQUES_GERENCIA"
        else:
            category = "CBS - PRODUCTOS PASIVAS"

        logger.info("[split] %s -> %s", file, category)
        output_path = os.path.join(output_folder, category, file)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(content)

    return output_folder

def merge_sql_group(folder_path: str, files_to_merge: List[str]) -> str:
    """Une un subconjunto de archivos .sql (en 'folder_path') en un solo string."""
    combined = []
    for i, filename in enumerate(sorted(files_to_merge), 1):
        full_path = os.path.join(folder_path, filename)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        header = f"--- SCRIPT {i}: {filename} ---\n"
        combined.append(header + content + "\n")
    return "".join(combined)

def unify_sqls_with_model(sql_block: str) -> str:
    """Pide al modelo que unifique varios scripts en uno solo."""
    prompt_path = get_prompt_path("join_sqls.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        template = file.read()
    prompt = template.format(sql_join=sql_block)
    llm = get_bedrock_llm()
    resp = llm.invoke([{"role": "user", "content": prompt}])
    return resp.content if hasattr(resp, "content") else str(resp)

def optimze_sql(sql_text: str) -> str:
    """Pide al modelo que optimice el SQL unificado (opcional)."""
    prompt_path = get_prompt_path("optimize_sql.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        template = file.read()
    prompt = template.format(sql_to_optimize=sql_text)
    llm = get_bedrock_llm()
    resp = llm.invoke([{"role": "user", "content": prompt}])
    return resp.content if hasattr(resp, "content") else str(resp)

def convert_to_markdown(sql_text: str) -> str:
    """Convierte SQL a bloque apto para ngx-markdown."""
    # OJO: corrige el typo del archivo
    prompt_path = get_prompt_path("convert_to_markdown.txt")
    with open(prompt_path, "r", encoding="utf-8") as file:
        template = file.read()
    prompt = template.format(sql_to_optimize=sql_text)
    llm = get_bedrock_llm()
    resp = llm.invoke([{"role": "user", "content": prompt}])
    return resp.content if hasattr(resp, "content") else str(resp)

# ---------- Orquestador principal ----------

def join_sql_scripts_team(folder_path: str) -> str:
    """
    1) Separa por categoría
    2) Une por carpeta y pide agrupación al modelo
    3) Unifica por grupo
    4) Sube a S3 cada SQL resultante y arma respuesta markdown con links
    """
    logger.info("Optimiza tus archivos de SQL")

    if not os.path.exists(folder_path):
        logger.error("No se encontró la carpeta: %s", folder_path)
        return "No se encontró la carpeta de entrada."

    separated_folder = separate_sql_by_keyword(folder_path)

    sql_unified: Dict[str, List[str]] = {}          # categoría -> [sql_text_unificado, ...]
    saved_paths: Dict[str, List[str]] = {}          # categoría -> [ruta_archivo, ...]
    grouping_explanation: Dict[str, str] = {}       # categoría -> explicación

    for category in sorted(os.listdir(separated_folder)):
        category_path = os.path.join(separated_folder, category)
        if not os.path.isdir(category_path):
            continue  # ignora archivos sueltos
        sql_combined, file_list = join_sql_scripts(category_path)
        if not file_list:
            continue

        logger.info("\nAnalizando archivos de %s:\n", category)
        for i, file in enumerate(file_list, 1):
            logger.info("  %d. %s", i, file)
        logger.info("\nEnviando a modelo...")

        try:
            logger.info("\n" + "=" * 60)
            logger.info("Analizando cuáles scripts deben unirse...")
            raw_response = request_grouping(sql_combined)
            parsed_json = clean_and_parse_json(raw_response)
            grouping_explanation[category] = show_grouping_explanation(parsed_json)

            grupos = parsed_json.get("grupos", [])
            if not grupos:
                logger.info("No se detectaron grupos para %s", category)
                continue

            for i, group in enumerate(grupos, 1):
                logger.info("\nUnificando scripts de %s...", category)
                logger.info("Convirtiendo %s", group.get("nombre_grupo", f"grupo_{i}"))
                group_scripts = list(group.get("scripts", []))
                if not group_scripts:
                    continue
                merged_sql = merge_sql_group(category_path, group_scripts)
                unified_sql = unify_sqls_with_model(merged_sql)
                sql_unified.setdefault(category, []).append(unified_sql)
                out_path = save_merged_sql(
                    unified_sql, category, str(i), group.get("nombre_grupo", f"grupo_{i}")
                )
                saved_paths.setdefault(category, []).append(out_path)

        except ValueError as err:
            logger.error("Error al procesar la respuesta del modelo:")
            logger.exception(err)

    # Subida a S3 y armado de links
    url_download: Dict[str, List[str]] = {}
    for category, paths in saved_paths.items():
        urls = []
        for p in paths:
            s3_key = f"sql-joiner/{os.path.basename(p)}"
            try:
                url = save_and_generate_url_s3(s3_key, p)
                urls.append(url)
            except Exception as e:
                logger.exception("Error subiendo %s a S3: %s", p, e)
        if urls:
            url_download[category] = urls

    # Respuesta final en Markdown
    # Nota: mostramos la explicación por categoría y luego la lista de URLs
    lines = []
    lines.append("## Se unificaron correctamente los SQL de la siguiente forma:\n")
    for category in sorted(grouping_explanation.keys()):
        lines.append(f"### {category}\n")
        lines.append("```text")
        lines.append(grouping_explanation[category].rstrip())
        lines.append("```")
        if url_download.get(category):
            lines.append("**Descargas:**")
            for idx, url in enumerate(url_download[category], 1):
                lines.append(f"- [Archivo {idx}]({url})")
        lines.append("")  # separador

    if not lines:
        return "No se generaron unificaciones (ver logs)."

    return "\n".join(lines)

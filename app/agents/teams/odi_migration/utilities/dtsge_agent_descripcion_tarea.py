import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_aws import ChatBedrock
from typing import TypedDict, List
import json
import glob

MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"


# Configuración del modelo Claude 3 Sonnet en AWS Bedrock
def get_bedrock_llm():
    """Inicializa el cliente de Bedrock y devuelve el modelo de lenguaje."""
    client = boto3.client(
        service_name="bedrock-runtime",
        region_name="us-east-1",
        config=Config(read_timeout=300, connect_timeout=60),
    )
    return ChatBedrock(
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        model_kwargs={
            "max_tokens": 4096,
            "temperature": 0,
            "anthropic_version": "bedrock-2023-05-31",
        },
        client=client,
    )


# Definición de los datos de entrada y salida del grafo
class DescripcionState(TypedDict):
    ruta_analisis: str
    contenido_analisis: str
    descripcion_tarea: str
    nombre_proceso_ppal: str  # <-- nuevo campo
    nombre_archivo: str


# Buscar archivos analisis_*
def buscar_archivos_analisis(
    state: DescripcionState, directorio="clean"
) -> DescripcionState:
    base_tmp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp"))
    directorio = os.path.join(base_tmp, "clean")
    archivos = glob.glob(
        os.path.join(directorio, state["nombre_proceso_ppal"], "analisis_*.txt"),
        recursive=True,
    )
    # Excluir archivos que inician con analisis_VAP_ o analisis_VAG_
    archivos = [
        a
        for a in archivos
        if not (
            os.path.basename(a).startswith("analisis_VAP_")
            or os.path.basename(a).startswith("analisis_VAG_")
        )
    ]
    state["archivos_analisis"] = archivos
    return state


def definir_promts_pasos_job(state: DescripcionState) -> DescripcionState:
    """
    Divide el contenido del análisis en pasos individuales.
    """
    base_tmp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp"))
    ruta = os.path.join(base_tmp, "prompts_datastage", state["nombre_proceso_ppal"])
    prompt_dir = os.path.join(base_tmp, "prompt_clean", state["nombre_proceso_ppal"])
    os.makedirs(prompt_dir, exist_ok=True)
    # print(f"Creando carpeta de salida: {prompt_dir}")
    # Buscar todos los archivos de análisis
    clean_dir = os.path.join(base_tmp, "clean", state["nombre_proceso_ppal"])
    archivos = glob.glob(os.path.join(clean_dir, "analisis_*.txt"), recursive=True)

    archivos = [
        a
        for a in archivos
        if not (
            os.path.basename(a).startswith("analisis_VAP_")
            or os.path.basename(a).startswith("analisis_VAG_")
        )
    ]
    # print(f"Archivos encontrados: {archivos}")

    for archivo in archivos:
        with open(archivo, "r", encoding="utf-8") as f:
            try:
                bloques = json.load(f)
            except Exception as e:
                print(f"Error leyendo {archivo}: {e}")
                continue
        for bloque in bloques:
            nombre_job = bloque.get("NOMBRE_JOB")
            descripcion = bloque.get("DESCRIPCION_TAREA", "")
            etapa = bloque.get("ETAPA", "")
            esquema = bloque.get("ESQUEMA", "")
            sentencia_sql = bloque.get("SENTENCIA_SQL", "")
            nombre_proyecto = bloque.get("NOMBRE_PROYECTO", "")
            # Leer el prompt desde el archivo de carge
            prompt_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "prompts",
                    "experto_dastage_extraccion.txt",
                )
            )
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            prompt_ext = prompt_template.format(
                nombre_job=nombre_job,
                descripcion=descripcion,
                etapa=etapa,
                esquema=esquema,
                sentencia_sql=sentencia_sql,
                nombre_proyecto=nombre_proyecto,
            )

            # Leer el prompt desde el archivo de transformaciones
            prompt_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "prompts",
                    "experto_dastage_transformacion.txt",
                )
            )
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            prompt_trf = prompt_template.format(
                nombre_job=nombre_job,
                descripcion=descripcion,
                etapa=etapa,
                esquema=esquema,
                sentencia_sql=sentencia_sql,
                nombre_proyecto=nombre_proyecto,
            )

            # Leer el prompt desde el archivo de transformaciones
            prompt_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "prompts",
                    "experto_dastage_carge.txt",
                )
            )
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            prompt_lod = prompt_template.format(
                nombre_job=nombre_job,
                descripcion=descripcion,
                etapa=etapa,
                esquema=esquema,
                sentencia_sql=sentencia_sql,
                nombre_proyecto=nombre_proyecto,
            )

            prompt = f"""Usa las sigueintes reglas para generar un prompt de experto en DataStage:
- Para las extracciones, usa el prompt de extracciones.
    {prompt_ext}   

- Para las transformaciones, usa el prompt de transformaciones.
    {prompt_trf}
    
- Para las cargas, usa el prompt de cargas.
    {prompt_lod}

Siempre debes generar un prompt que incluya minimo el proceso de extraccion y el proceso de carga, si no se requiere transformacion, no debes incluir el campo de transformacion en el prompt. Es obligatorio que se incluyan estos 2 pasos.    
                        
Genera el archivo de salida en formato JSON con la siguiente estructura:
{{
    {{"EXTRACCION": "descripcion del proceso de extraccion en leguaje natural, debe incluir todos los datos que cada regla solicita, en la etapa de extraccion, se debe incluir de forma textual el select de origen sin nigun cambio",}},
    {{"TRANSFORMACION_JN": "descripcion del proceso de transformacion en leguaje natural, debe incluir todos los datos que cada regla solicita, este solo aplicara cuando la etapa requiere hacer un join, si no se requiere un join, este campo no debe aparecer"}},
    {{"TRANSFORMACION_TRF": "descripcion del proceso de transformacion en leguaje natural, debe incluir todos los datos que cada regla solicita, este solo aplicara cuando la etapa requiere hacer un transformer, si no se requiere un transformer, este campo no debe aparecer"}},
    {{"CARGA": "descripcion del proceso de cargue en leguaje natural, debe incluir todos los datos que cada regla solicita, cuando se tenga un merge o un upsert, se debe incluir el merge o upsert de forma textual sin nigun cambio"}},
}}
El archivo solo debe contener la descripción de cada paso del proceso de DataStage. Omite las reglas y el texto introductorio.
Debes asegurarte que si en el archivo de análisis no se encuentra un paso, este no se incluya en el archivo de salida. y de igual forma que si un paso esta en el archivo de análisis, este se incluya en el archivo de salida.
Solamente debes escribir la estructura json, nada mas, no debes escribir ningun texto adicional, ni explicaciones, ni reglas, ni instrucciones.
Aplica este prompt a cada uno de los pasos del proceso de DataStage en:

{{contenido_analisis}}
                    """
            # Guardar el prompt en un archivo individual
            nombre_archivo = os.path.basename(archivo).replace("analisis_", "prompts_datastage_")
            ruta_salida = os.path.join(prompt_dir, nombre_archivo)


            with open(ruta_salida, "w", encoding="utf-8") as fout:
                fout.write(prompt)
    state["mensaje"] = f"Archivos generados en {ruta}"
    return state


def leer_contenido_analisis(state: DescripcionState) -> DescripcionState:

    ruta_dir = state["ruta_analisis"]
    archivos = glob.glob(os.path.join(ruta_dir, "analisis_*_json.txt"), recursive=True)
    contenidos = []
    for archivo in archivos:
        with open(archivo, "r", encoding="utf-8") as f:
            contenidos.append(f.read())
    # Concatenar todos los contenidos en un solo string
    state["contenido_analisis"] = "\n".join(contenidos)
    return state


def describir_tarea_datastage(state: DescripcionState) -> DescripcionState:
    llm = get_bedrock_llm()
    base_tmp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp"))
    prompt_dir = os.path.join(base_tmp, "prompt_clean", state["nombre_proceso_ppal"])
    os.makedirs(prompt_dir, exist_ok=True)
    # print(f"Directorio {prompt_dir} creado.")
    archivos = glob.glob(os.path.join(prompt_dir, "prompts_datastage_*.txt"))
    # Excluir archivos que inician con analisis_VAP_ o analisis_VAG_
    archivos = [
        a
        for a in archivos
        if not (
            os.path.basename(a).startswith("analisis_VAP_")
            or os.path.basename(a).startswith("analisis_VAG_")
        )
    ]
    descripciones = {}
    for archivo in archivos:
        with open(archivo, "r", encoding="utf-8") as f:
            prompt_template = f.read().strip()
        if not prompt_template:
            print(f"Archivo vacío: {archivo}, se omite.")
            continue
        prompt = prompt_template.replace(
            "{contenido_analisis}", state["contenido_analisis"]
        )
        if not prompt.strip():
            print(f"Prompt vacío para {archivo}, se omite.")
            continue
        messages = [{"role": "user", "content": prompt}]
        respuesta = llm.invoke(messages)
        if hasattr(respuesta, "content"):
            descripcion = respuesta.content
        else:
            descripcion = str(respuesta)
        # Eliminar todos los delimitadores ```json y ``` en cualquier parte de la respuesta
        descripcion = descripcion.replace("```json", "").replace("```", "").strip()
        try:
            descripcion_json = json.loads(descripcion)
        except Exception:
            descripcion_json = (
                descripcion  # Si no es JSON válido, guarda como texto plano
            )
        nombre_archivo = os.path.basename(archivo).replace(
            "prompts_datastage_", "descripcion_"
        )
        # Cambia la extensión a .json si es un dict (JSON válido)
        if isinstance(descripcion_json, dict):
            nombre_archivo = os.path.splitext(nombre_archivo)[0] + ".json"
        ruta_salida = os.path.join(
            base_tmp, "prompts_datastage", state["nombre_proceso_ppal"], nombre_archivo
        )
        os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
        with open(ruta_salida, "w", encoding="utf-8") as fout:
            if isinstance(descripcion_json, dict):
                json.dump(descripcion_json, fout, ensure_ascii=False, indent=4)
            else:
                fout.write(descripcion)
        descripciones[nombre_archivo] = descripcion_json
    state["descripcion_tarea"] = descripciones
    state["mensaje"] = (
        f"Descripciones generadas para {len(descripciones)} archivos en prompts_datastage/{state['nombre_proceso_ppal']}/"
    )
    print(state["mensaje"])
    return state


def exportar_por_llave_descripcion_state(state: DescripcionState) -> DescripcionState:
    nombre_proceso_ppal = state["nombre_proceso_ppal"]
    # ruta = os.path.join("prompts_datastage", nombre_proceso_ppal)
    base_tmp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp"))
    ruta = os.path.join(base_tmp, "prompts_datastage", nombre_proceso_ppal)
    if not os.path.exists(ruta):
        os.makedirs(ruta, exist_ok=True)
    archivos = [f for f in os.listdir(ruta) if f.endswith(".json")]
    archivos_generados = []
    print("Archivos generados:")
    for archivo in archivos:
        print(f" \n- {archivo}")
        ruta_archivo = os.path.join(ruta, archivo)
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            data = json.load(f)
        # nombre_job = archivo.replace("descripcion_", "").replace("_json.json", "")
        nombre_job = os.path.splitext(archivo.replace("descripcion_", ""))[0]

        for llave, contenido in data.items():
            if llave == "EXTRACCION":
                nombre_salida = f"EXT_{nombre_job}.txt"
            elif llave == "TRANSFORMACION_JN":
                nombre_salida = f"TRF_JN_{nombre_job}.txt"
            elif llave == "TRANSFORMACION_TRF":
                nombre_salida = f"TRF_TRF_{nombre_job}.txt"
            elif llave == "CARGA":
                nombre_salida = f"LOD_{nombre_job}.txt"
            elif llave == "Variable":
                continue  # Omitir llaves de tipo Variable, no generar archivo
            else:
                continue  # omitir llaves desconocidas
            ruta_salida = os.path.join(ruta, nombre_salida)
            with open(ruta_salida, "w", encoding="utf-8") as fout:
                fout.write(contenido)
            archivos_generados.append(ruta_salida)
    state["archivos_exportados"] = archivos_generados
    state["mensaje_exportar"] = (
        f"Archivos individuales generados en {ruta}: {len(archivos_generados)}"
    )
    return state


def describir_etl_desde_proceso(nombre_proceso_ppal: str) -> dict:
    """
    Ejecuta el grafo de descripción para el proceso dado y retorna el resultado.
    """
    # Construcción del grafo LangGraph actualizado
    sg = StateGraph(DescripcionState)
    sg.add_node("buscar_archivos_analisis", buscar_archivos_analisis)
    sg.add_node("leer_analisis", leer_contenido_analisis)
    sg.add_node("definir_prompts", definir_promts_pasos_job)
    sg.add_node("describir_tarea", describir_tarea_datastage)
    sg.add_node("exportar_por_llave", exportar_por_llave_descripcion_state)

    sg.set_entry_point("buscar_archivos_analisis")
    sg.add_edge("buscar_archivos_analisis", "leer_analisis")
    sg.add_edge("leer_analisis", "definir_prompts")
    sg.add_edge("definir_prompts", "describir_tarea")
    sg.add_edge("describir_tarea", "exportar_por_llave")
    sg.add_edge("exportar_por_llave", END)

    grafo = sg.compile()

    nombre_archivo = f"prompt_{nombre_proceso_ppal}.txt"
    base_tmp = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmp"))
    ruta_analisis = os.path.join(base_tmp, "clean", nombre_proceso_ppal)

    estado_inicial = {
        "ruta_analisis": ruta_analisis,
        "contenido_analisis": "",
        "descripcion_tarea": "",
        "nombre_proceso_ppal": nombre_proceso_ppal,
        "nombre_archivo": nombre_archivo,
    }
    grafo.invoke(estado_inicial)

import os
import boto3
import re
import json
from dotenv import load_dotenv
from typing import TypedDict
from botocore.config import Config
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage
from langchain_aws import ChatBedrock
from typing import TypedDict

# Cargar variables de entorno
def cargar_entorno():
    load_dotenv()

class GrafoState(TypedDict):
    ruta_json: str
    json_data: dict
    json_limpio: dict
    ruta_clean: str
    archivos_steps: list
    rutas_bloques: list
    rutas_analisis: list

def leer_json_desde_archivo(path: str) -> dict:
    """Descipcion: Lee un archivo JSON desde la ruta especificada y devuelve su contenido como un diccionario.
        Parámetros:
            path (str): Ruta del archivo JSON a leer.
        Retorna:
            dict: Contenido del archivo JSON como un diccionario.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
# --- Utilidad para limpiar bloques vacíos de tipo SERIAL y guardar el resultado ---
def eliminar_bloques_serial_vacios(data):
    """
    Elimina de forma recursiva los objetos donde COL_TXT y DEF_TXT estén vacíos.
    Si se pasa ruta_original, guarda el JSON limpio en la carpeta 'clean' con sufijo _clean.
    Devuelve el JSON limpio.
    """
    if isinstance(data, list):
        nueva_lista = []
        for item in data:
            if isinstance(item, dict):
                if (
                    item.get("TASK_NAME1") == "SERIAL"
                    and item.get("COL_TXT", "") == ""
                    and item.get("DEF_TXT", "") == ""
                ):
                    continue
                for k, v in item.items():
                    item[k] = eliminar_bloques_serial_vacios(v)
                nueva_lista.append(item)
            else:
                nueva_lista.append(eliminar_bloques_serial_vacios(item))
        return nueva_lista
    elif isinstance(data, dict):
        return {k: eliminar_bloques_serial_vacios(v) for k, v in data.items()}
    else:
        return data

# --- Guardar el JSON limpio en la carpeta 'clean' con sufijo _clean ---
def guardar_json_limpio(json_limpio, ruta_original):
    nombre_archivo = os.path.basename(ruta_original)
    nombre_sin_ext, ext = os.path.splitext(nombre_archivo)
    nombre_clean = f"{nombre_sin_ext}_clean{ext}"
    carpeta_clean = os.path.join(os.path.dirname(ruta_original), '..', 'clean')
    carpeta_clean = os.path.abspath(carpeta_clean)
    os.makedirs(carpeta_clean, exist_ok=True)
    ruta_clean = os.path.join(carpeta_clean, nombre_clean)
    with open(ruta_clean, 'w', encoding='utf-8') as f:
        json.dump(json_limpio, f, ensure_ascii=False, indent=2)
    print(f"✅ Archivo limpio guardado en: {ruta_clean}")
    return ruta_clean  

def exportar_steps_por_proceso(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    scen_name = data.get('SCEN_NAME', 'proceso_desconocido')
    detalles = data.get('details', [])
    # Crear carpeta clean/SCEN_NAME
    carpeta_base = os.path.join('clean', scen_name)
    os.makedirs(carpeta_base, exist_ok=True)
    archivos_generados = []
    for bloque in detalles:
        step_name = bloque.get('STEP_NAME', 'step_desconocido')
        subdetails = bloque.get('subdetails', [])
        # Guardar subdetails en archivo
        nombre_archivo = f"{step_name}.json"
        ruta_archivo = os.path.join(carpeta_base, nombre_archivo)
        with open(ruta_archivo, 'w', encoding='utf-8') as f_out:
            json.dump(subdetails, f_out, ensure_ascii=False, indent=2)
        archivos_generados.append(ruta_archivo)
    print(f"✅ Archivos generados en: {carpeta_base}")
    return archivos_generados

def describir_bloques_json_a_txt(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Si es lista, es un archivo de subdetails de un STEP_NAME
    if isinstance(data, list):
        detalles = [{'STEP_NAME': os.path.splitext(os.path.basename(json_path))[0], 'subdetails': data}]
    elif isinstance(data, dict):
        detalles = data.get('details', [])
    else:
        raise ValueError("Formato de archivo no soportado.")
    
    step_name = detalles[0].get('STEP_NAME', 'Sin_nombre') if detalles else 'Sin_nombre'

    def reemplazar_patrones(texto, step_name):
        # Reemplazo de <?= odiRef.getObjectName("L", "STG_INFO_BASICA_CLIENTE", "STAGE", "D") ?>
        patron_tabla = re.compile(r'<\?= *odiRef\.getObjectName\("L",\s*"([^"]+)",\s*"([^"]+)"(?:,\s*"[^"]*")*\) *\?>')
        texto = patron_tabla.sub(lambda m: f"{m.group(2)}.{m.group(1)}", texto)
        # Reemplazo de <?= odiRef.getObjectName("L", "%COL_PRF0DEFAULT", "W") ?>
        patron_work = re.compile(r'<\?= *odiRef\.getObjectName\("L",\s*"%COL_PRF0DEFAULT[^"]*",\s*"W"\) *\?>')
        texto = patron_work.sub(f"work_table.{step_name}", texto)
        # Reemplazo de W.%COL_PRF0DEFAULT o variantes por work_table_{step_name}
        patron_w_colprf = re.compile(r'W\.\%COL_PRF0DEFAULT\w*')
        texto = patron_w_colprf.sub(f"work_table.{step_name}", texto)
        return texto

    descripciones = []
    for bloque in detalles:
        step_name = bloque.get('STEP_NAME', 'Sin_nombre')
        subdetails = bloque.get('subdetails', [])
        acciones = []
        for sub in subdetails:
            task = sub.get('TASK_NAME1', '')
            def_txt = sub.get('DEF_TXT', '').strip()
            col_txt = sub.get('COL_TXT', '').strip()
            SCEN_TASK_NO = sub.get('SCEN_TASK_NO', 'Tarea sin número')
            col_lschema = sub.get('COL_LSCHEMA_NAME', '')
            def_lschema = sub.get('DEF_LSCHEMA_NAME', '')

            # Reemplazar patrones en los textos antes de armar la acción
            def_txt = reemplazar_patrones(def_txt, step_name)
            col_txt = reemplazar_patrones(col_txt, step_name)

            if task == 'Drop work table' and def_txt:
                acciones.append(f"{SCEN_TASK_NO} - Borra una tabla de trabajo en el esquema {def_lschema} con la sentencia: {def_txt}")
            elif task == 'Create work table' and def_txt:
                acciones.append(f"{SCEN_TASK_NO} - Crea una tabla de trabajo en el esquema {def_lschema} con la sentencia: {def_txt}")
            elif task == 'Load data' and col_txt and def_txt:
                columnas = re.findall(r'AS ([A-Z0-9_]+)', col_txt)
                acciones.append(f"{SCEN_TASK_NO} - Carga datos haciendo un SELECT de la tabla fuente en el esquema {col_lschema}, con la sentencia: {col_txt}, extrayendo las columnas: {', '.join(columnas)}. \n\n Luego inserta en la tabla destino con: {def_txt}")
            elif task == 'Load data' and col_txt:
                columnas = re.findall(r'AS ([A-Z0-9_]+)', col_txt)
                acciones.append(f"{SCEN_TASK_NO} - Carga datos haciendo un SELECT de la tabla fuente en el esquema {col_lschema}, con la sentencia: {col_txt}, extrayendo las columnas: {', '.join(columnas)}.")
            elif task == 'Load data' and def_txt:
                acciones.append(f"{SCEN_TASK_NO} - Inserta datos en la tabla destino con: {def_txt}")
            elif task == 'Insert new rows' and def_txt:
                acciones.append(f"{SCEN_TASK_NO} - Inserta nuevas filas en la tabla destino con: {def_txt}")
            elif task == 'Truncate target table' and def_txt:
                acciones.append(f"{SCEN_TASK_NO} - Trunca la tabla destino con: {def_txt}")
            elif task == 'Commit transaction':
                acciones.append(f"{SCEN_TASK_NO} - Realiza un commit de la transacción.")
            elif task == 'Analyze work table' and def_txt:
                acciones.append(f"{SCEN_TASK_NO} - Analiza la tabla de trabajo con: {def_txt}")
            elif task == 'Drop work table' and not def_txt:
                acciones.append(f"{SCEN_TASK_NO} - Borra una tabla de trabajo en el esquema {def_lschema} (sentencia no especificada)")
            elif task == 'Create work table' and not def_txt:
                acciones.append(f"{SCEN_TASK_NO} - Crea una tabla de trabajo en el esquema {def_lschema} (sentencia no especificada)")
            elif task == 'SERIAL':
                continue
            elif task == 'Procedimiento' and def_txt:
                acciones.append(f"{SCEN_TASK_NO} - Ejecuta un procedimiento PL/SQL: {def_txt}")
            else:
                if def_txt or col_txt:
                    acciones.append(f"{SCEN_TASK_NO} - Acción personalizada: {task}. DEF_TXT: {def_txt} COL_TXT: {col_txt}")
        descripciones.append(f"Bloque '{step_name}':\n- " + "\n- ".join(acciones) + "\n")
    analisis_txt = "\n".join(descripciones)
    nombre_json = os.path.splitext(os.path.basename(json_path))[0]
    nombre_txt = f"bloques_{nombre_json}.txt"
    carpeta = os.path.dirname(json_path)
    ruta_txt = os.path.join(carpeta, nombre_txt)
    with open(ruta_txt, 'w', encoding='utf-8') as f:
        f.write(analisis_txt)
    print(f"✅ Archivo de bloques escrito en: {ruta_txt}")
    return ruta_txt


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
            "max_tokens": 4096,
            "temperature": 0,
            "anthropic_version": "bedrock-2023-05-31",
        },
        client=client,
    )


# --- 2. Invocar el agente sobre el archivo de bloques generado ---
def analizar_bloques_con_llm(ruta_bloques):
    llm = get_bedrock_llm()
    with open(ruta_bloques, 'r', encoding='utf-8') as f:
        texto_bloques = f.read()
    # Leer el prompt desde el archivo externo
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'analizar_bloques_con_llm.txt')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()
    prompt = prompt_template.replace('{texto_bloques}', texto_bloques)
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content
    idx_ini = content.find('[')
    idx_fin = content.rfind(']')
    if idx_ini != -1 and idx_fin != -1 and idx_fin > idx_ini:
        content = content[idx_ini:idx_fin+1]
    else:
        # Si no encuentra los corchetes, forzar error para que se registre en el archivo de error
        raise ValueError("No se encontraron corchetes '[' y ']' válidos en la respuesta del LLM. No se puede decodificar JSON.")
    nombre_txt = os.path.basename(ruta_bloques)
    nombre_analisis = f"analisis_{nombre_txt.replace('bloques_','').replace('.txt','')}_json.txt"
    carpeta = os.path.dirname(ruta_bloques)
    ruta_analisis = os.path.join(carpeta, nombre_analisis)
    try:
        resultado = json.loads(content)
        assert isinstance(resultado, list)
        # Filtrar bloques EXT cuya SENTENCIA_SQL sea igual a la de algún bloque TRF
        sentencias_trf = set(
            b["SENTENCIA_SQL"] for b in resultado if b.get("ETAPA") == "TRF" and b.get("SENTENCIA_SQL")
        )
        resultado_filtrado = []
        for bloque in resultado:
            if bloque.get("ETAPA") == "EXT" and bloque.get("SENTENCIA_SQL") in sentencias_trf:
                continue  # Ignorar este bloque EXT
            resultado_filtrado.append(bloque)
        for bloque in resultado_filtrado:
            assert all(k in bloque for k in ["ETAPA", "ESQUEMA", "NOMBRE_PROYECTO", "DESCRIPCION_TAREA", "NOMBRE_JOB", "SENTENCIA_SQL"])
        with open(ruta_analisis, 'w', encoding='utf-8') as f:
            f.write(json.dumps(resultado_filtrado, ensure_ascii=False, indent=2))
        print(f"✅ Análisis final escrito en: {ruta_analisis}")
        return ruta_analisis
    except Exception as e:
        nombre_error = f"error_{nombre_txt.replace('bloques_','').replace('.txt','')}.txt"
        ruta_error = os.path.join(carpeta, nombre_error)
        with open(ruta_error, 'w', encoding='utf-8') as f:
            f.write(f"Error de formato en la respuesta del LLM:\n{str(e)}\n\nRespuesta recibida:\n{response.content}")
        print(f"❌ La respuesta no cumple con la estructura esperada. Error guardado en: {ruta_error}")
        return None

# Paso 1: Leer JSON original
def nodo_leer_json(state: GrafoState) -> GrafoState:
    ruta_json = state["ruta_json"]
    json_data = leer_json_desde_archivo(ruta_json)
    state["json_data"] = json_data
    return state

# Paso 2: Limpiar bloques SERIAL vacíos
def nodo_limpiar_serial(state: GrafoState) -> GrafoState:
    json_limpio = eliminar_bloques_serial_vacios(state["json_data"])
    state["json_limpio"] = json_limpio
    return state

# Paso 3: Guardar JSON limpio
def nodo_guardar_limpio(state: GrafoState) -> GrafoState:
    ruta_clean = guardar_json_limpio(state["json_limpio"], state["ruta_json"])
    state["ruta_clean"] = ruta_clean
    return state

# Paso 4: Exportar steps por proceso
def nodo_exportar_steps(state: GrafoState) -> GrafoState:
    archivos_steps = exportar_steps_por_proceso(state["ruta_clean"])
    state["archivos_steps"] = archivos_steps
    return state

# Paso 5: Describir bloques de todos los steps
def nodo_describir_bloques(state: GrafoState) -> GrafoState:
    rutas_bloques = []
    for paso_limpio in state["archivos_steps"]:
        ruta_bloques = describir_bloques_json_a_txt(paso_limpio)
        rutas_bloques.append(ruta_bloques)
    state["rutas_bloques"] = rutas_bloques
    return state

# Paso 6: Analizar todos los bloques con LLM
def nodo_analizar_llm(state: GrafoState) -> GrafoState:
    rutas_analisis = []
    for ruta_bloques in state["rutas_bloques"]:
        print(f"Analizando bloques en: {ruta_bloques}")
        ruta_analisis = analizar_bloques_con_llm(ruta_bloques)
        rutas_analisis.append(ruta_analisis)
    state["rutas_analisis"] = rutas_analisis
    return state

# Construir el grafo
grafo = StateGraph(GrafoState)
grafo.add_node("leer_json", nodo_leer_json)
grafo.add_node("limpiar_serial", nodo_limpiar_serial)
grafo.add_node("guardar_limpio", nodo_guardar_limpio)
grafo.add_node("exportar_steps", nodo_exportar_steps)
grafo.add_node("describir_bloques", nodo_describir_bloques)
grafo.add_node("analizar_llm", nodo_analizar_llm)

# Definir el flujo entre nodos
grafo.add_edge("leer_json", "limpiar_serial")
grafo.add_edge("limpiar_serial", "guardar_limpio")
grafo.add_edge("guardar_limpio", "exportar_steps")
grafo.add_edge("exportar_steps", "describir_bloques")
grafo.add_edge("describir_bloques", "analizar_llm")
grafo.add_edge("analizar_llm", END)

grafo.set_entry_point("leer_json")
# Ejecutar el grafo
def ejecutar_grafo(ruta_json):
    grafo_compilado = grafo.compile()
    estado_inicial = {
        "ruta_json": ruta_json
    }
    resultado = grafo_compilado.invoke(estado_inicial)
    return resultado
import os
import json
import re
import boto3
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import TypedDict
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage
from langchain_aws import ChatBedrock
from dotenv import load_dotenv
from botocore.config import Config


# Cargar variables de entorno desde .env
# load_dotenv()
MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# Configuración del modelo Claude 3 Sonnet en AWS Bedrock
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

llm = get_bedrock_llm()
class AgentState(TypedDict):
    natural_language_request: str
    generated_xml: str

def indent_xml(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent_xml(e, level + 1)
            if not e.tail or not e.tail.strip():
                e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i
    return elem

def agregar_header(root):
    ET.SubElement(root, "Header", {
        "CharacterSet": "CP1252",
        "ExportingTool": "IBM InfoSphere DataStage Export",
        "ToolVersion": "8",
        "ServerName": "LDBOG284V",
        "ToolInstanceID": "PRY_CTIF",
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Time": datetime.now().strftime("%H.%M.%S"),
        "ServerVersion": "11.7"
    })


def construir_mapeo_ids(data):
    return {stage["name"]: f"V0S{i}" for i, stage in enumerate(data["stages"])}

def crear_columna_completa(col):
    props = [
        ("Name", col["Name"]),
        ("SqlType", str(col.get("SqlType", 12))),
        ("Precision", str(col.get("Precision", 20))),
        ("Scale", "0"),
        ("Nullable", "1"),
        ("KeyPosition", "0"),
        ("DisplaySize", "0"),
        ("Group", "0"),
        ("SortKey", "0"),
        ("SortType", "0"),
        ("AllowCRLF", "0"),
        ("LevelNo", "0"),
        ("Occurs", "0"),
        ("PadNulls", "0"),
        ("SignOption", "0"),
        ("SortingOrder", "0"),
        ("ArrayHandling", "0"),
        ("SyncIndicator", "0"),
        ("PadChar", ""),
        ("ExtendedPrecision", "0"),
        ("TaggedSubrec", "0"),
        ("OccursVarying", "0"),
        ("PKeyIsCaseless", "0"),
        ("SCDPurpose", "0")
    ]
    return props

def agregar_record_root(job, job_name):
    rec = ET.SubElement(job, "Record", {"Identifier": "ROOT", "Type": "JobDefn", "Readonly": "0"})
    ET.SubElement(rec, "Property", {"Name": "Name"}).text = job_name
    ET.SubElement(rec, "Property", {"Name": "NextID"}).text = "1"
    ET.SubElement(rec, "Property", {"Name": "Container"}).text = "V0"
    ET.SubElement(rec, "Property", {"Name": "JobVersion"}).text = "56.0.0"
    ET.SubElement(rec, "Property", {"Name": "ControlAfterSubr"}).text = "0"

    metabag = ET.SubElement(rec, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"})
    sr = ET.SubElement(metabag, "SubRecord")
    ET.SubElement(sr, "Property", {"Name": "Owner"}).text = "APT"
    ET.SubElement(sr, "Property", {"Name": "Name"}).text = "AdvancedRuntimeOptions"
    ET.SubElement(sr, "Property", {"Name": "Value"}).text = "#DSProjectARTOptions#"

    props = {
        "NULLIndicatorPosition": "0",
        "IsTemplate": "0",
        "JobType": "3",
        "Category": r"\Jobs\UTILIDADES",
        "CenturyBreakYear": "30",
        "NextAliasID": "2",
        "ParameterFileDDName": "DD00001",
        "ReservedWordCheck": "1",
        "TransactionSize": "0",
        "ValidationStatus": "0",
        "Uploadable": "0",
        "PgmCustomizationFlag": "0",
        "JobReportFlag": "0",
        "AllowMultipleInvocations": "0",
        "Act2ActOverideDefaults": "0",
        "Act2ActEnableRowBuffer": "0",
        "Act2ActUseIPC": "0",
        "Act2ActBufferSize": "0",
        "Act2ActIPCTimeout": "0",
        "ExpressionSemanticCheckFlag": "0",
        "TraceOption": "0",
        "EnableCacheSharing": "0",
        "RuntimeColumnPropagation": "0",
        "RelStagesInJobStatus": "-1",
        "WebServiceEnabled": "0",
        "MFProcessMetaData": "0",
        "MFProcessMetaDataXMLFileExchangeMethod": "0",
        "IMSProgType": "0",
        "CopyLibPrefix": "ARDT",
        "RecordPerformanceResults": "0"
    }
    for k, v in props.items():
        ET.SubElement(rec, "Property", {"Name": k}).text = v

    return rec


def agregar_container_view(job):
    rec = ET.SubElement(job, "Record", {"Identifier": "V0", "Type": "ContainerView", "Readonly": "0"})
    props = {
        "Name": "Job",
        "NextID": "1",
        "IsTopLevel": "0",
        "StageList": "V0S0|V0S3",
        "StageXPos": "192|456",
        "StageYPos": "168|168",
        "StageTypes": "CCustomStage|CCustomStage.CC_GUI",  # ✅ Tipo correcto para OracleConnectorPX
        "NextStageID": "4",
        "SnapToGrid": "1",
        "GridLines": "0",
        "ZoomValue": "100",
        "StageXSize": "48|48",
        "StageYSize": "48|48",
        "ContainerViewSizing": "0052 0052 0575 0343 0000 0001 0000 0000",
        "StageNames": "DATASET1|ORA_INSERT",
        "StageTypeIDs": "PxDataSet|OracleConnectorPX",
        "LinkNames": "LNK_1|\\(20)",
        "LinkHasMetaDatas": "True|\\(20)",
        "LinkTypes": "1|\\(20)",
        "LinkNamePositionXs": "309|\\(20)",
        "LinkNamePositionYs": "175|\\(20)",
        "TargetStageIDs": "V0S3|\\(20)",
        "SourceStageEffectiveExecutionModes": "2|\\(20)",
        "SourceStageRuntimeExecutionModes": "2|\\(20)",
        "TargetStageEffectiveExecutionModes": "2|\\(20)",
        "TargetStageRuntimeExecutionModes": "2|\\(20)",
        "LinkIsSingleOperatorLookup": "False|\\(20)",
        "LinkIsSortSequential": "False|\\(20)",
        "LinkSortMode": "0|\\(20)",
        "LinkPartColMode": "1|\\(20)",
        "LinkSourcePinIDs": "V0S0P1|\\(20)"
    }
    for k, v in props.items():
        ET.SubElement(rec, "Property", {"Name": k}).text = v

    return rec


def agregar_metabag_completo(parent, entries, owner="APT", name="MetaBag", tipo="MetaProperty"):
    """
    Agrega una colección completa tipo MetaBag o CustomProperty.
    - parent: nodo padre XML.
    - entries: dict con {nombre: valor}.
    - owner: propietario (usualmente "APT").
    - name: nombre de la colección (MetaBag o Properties).
    - tipo: tipo de colección (MetaProperty o CustomProperty).
    """
    metabag = ET.SubElement(parent, "Collection", {"Name": name, "Type": tipo})
    for k, v in entries.items():
        sr = ET.SubElement(metabag, "SubRecord")
        if tipo == "MetaProperty":  # ✅ Solo se incluye 'Owner' en MetaProperty
            ET.SubElement(sr, "Property", {"Name": "Owner"}).text = owner
        ET.SubElement(sr, "Property", {"Name": "Name"}).text = k
        ET.SubElement(sr, "Property", {"Name": "Value"}).text = v
    return metabag


def agregar_custom_properties(etapa, props_list):
    props = ET.SubElement(etapa, "Collection", {"Name": "Properties", "Type": "CustomProperty"})
    for p in props_list:
        sub = ET.SubElement(props, "SubRecord")
        ET.SubElement(sub, "Property", {"Name": "Name"}).text = p["name"]
        ET.SubElement(sub, "Property", {"Name": "Value"}).text = p["value"]



def agregar_stage(job, identifier, name, stage_type, input_pin=None, output_pin=None):
    stage = ET.SubElement(job, "Record", {"Identifier": identifier, "Type": "CustomStage", "Readonly": "0"})
    ET.SubElement(stage, "Property", {"Name": "Name"}).text = name
    if input_pin:
        ET.SubElement(stage, "Property", {"Name": "InputPins"}).text = input_pin
    if output_pin:
        ET.SubElement(stage, "Property", {"Name": "OutputPins"}).text = output_pin
    ET.SubElement(stage, "Property", {"Name": "StageType"}).text = stage_type
    ET.SubElement(stage, "Property", {"Name": "AllowColumnMapping"}).text = "0"
    ET.SubElement(stage, "Property", {"Name": "NextID"}).text = "2"
    ET.SubElement(stage, "Property", {"Name": "NextRecordID"}).text = "0"  # ✅ Requerido por ORA_INSERT
    return stage


def agregar_pin(job, id, tipo, nombre, partner, props_dict=None, metabag_dict=None, columns=None, coords=None):
    pin = ET.SubElement(job, "Record", {
        "Identifier": id,
        "Type": tipo,
        "Readonly": "0"
    })

    ET.SubElement(pin, "Property", {"Name": "Name"}).text = nombre
    ET.SubElement(pin, "Property", {"Name": "Partner"}).text = partner

    if coords:
        ET.SubElement(pin, "Property", {"Name": "LeftTextPos"}).text = str(coords[0])
        ET.SubElement(pin, "Property", {"Name": "TopTextPos"}).text = str(coords[1])

    if props_dict:
        props_list = [{"name": k, "value": v} for k, v in props_dict.items()]
        agregar_custom_properties(pin, props_list)

    if metabag_dict:
        metabag = ET.SubElement(pin, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"})
        for k, v in metabag_dict.items():
            sub = ET.SubElement(metabag, "SubRecord")
            ET.SubElement(sub, "Property", {"Name": "Owner"}).text = "APT"
            ET.SubElement(sub, "Property", {"Name": "Name"}).text = k
            ET.SubElement(sub, "Property", {"Name": "Value"}).text = v

    if columns:
        cols = ET.SubElement(pin, "Collection", {"Name": "Columns", "Type": "OutputColumn"})
        for col in columns:
            col_sub = ET.SubElement(cols, "SubRecord")
            for key, val in col.items():
                ET.SubElement(col_sub, "Property", {"Name": key}).text = str(val)

    ET.SubElement(pin, "Property", {"Name": "LinkMinimised"}).text = "0"

    # Solo agregar si no es CustomOutput con partner tipo PxDataSet
    #if not (tipo == "CustomOutput" and "PxDataSet" in partner):
        #ET.SubElement(pin, "Property", {"Name": "TransactionSize"}).text = "0"
        #ET.SubElement(pin, "Property", {"Name": "TXNBehaviour"}).text = "0"
        #ET.SubElement(pin, "Property", {"Name": "EnableTxGroup"}).text = "0"


def interpretar_y_generar_insert_xml(state: dict) -> dict:
    prompt = f"""
    Eres un experto en IBM DataStage Designer.
    Eres un generador automático de estructuras JSON para IBM DataStage.

    Analiza esta solicitud:
    {state["natural_language_request"]}
    
    Tu única tarea es devolver un objeto JSON válido, sin explicaciones, sin texto adicional, sin etiquetas, ni código de ejemplo.
    Reemplazando el nombre del job desde la solicitud. y los campos de la tabla por los nombres de los campos que se mencionan en la solicitud.

    la estructura JSON debe tener el siguiente formato:

    Devuelve solo el JSON:
    {{
      "job_name": "JOB_EJ_ORA_INSERT_CONFIG",
      "stages": [
        {{"name": "DATASET1", "type": "PxDataSet"}},
        {{"name": "ORA_INSERT", "type": "OracleConnectorPX"}}
      ],
      "columns": [
        {{"Name": "CAMPO1", "SqlType": 12, "Precision": 20}},
        {{"Name": "CAMPO2", "SqlType": 12, "Precision": 20}}
      ]
    }}
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()
    
    try:
        if raw.startswith('{'):
            data = json.loads(raw)
        else:
            match = re.search(r"\{[\s\S]*\}", raw)
            if not match:
                raise ValueError("No se encontró JSON válido.")
            data = json.loads(match.group())
    
        if "columns" not in data:
            raise KeyError("'columns' no está presente en la respuesta JSON.\nRespuesta recibida:\n" + json.dumps(data, indent=2))
    
    except Exception as e:
        raise RuntimeError(f"Error extrayendo JSON válido: {e}\n\nRespuesta recibida:\n{raw}")


    root = ET.Element("DSExport")
    agregar_header(root)

    job = ET.SubElement(root, "Job", {
        "Identifier": data["job_name"],
        "DateModified": datetime.now().strftime("%Y-%m-%d"),
        "TimeModified": datetime.now().strftime("%H.%M.%S")
    })

    agregar_record_root(job, data["job_name"])
    agregar_container_view(job)

    agregar_stage(job, "V0S0", "DATASET1", "PxDataSet", output_pin="V0S0P1")
    agregar_pin(
        job, "V0S0P1", "CustomOutput", "LNK_1", "V0S3|V0S3P1",
        props_dict={"dataset": "RUTA_DS_1.ds", "missingcolmode": "\\(20)"},
        metabag_dict={
            "DiskWriteInc": "1048576", "BufFreeRun": "50",
            "MaxMemBufSize": "3145728", "QueueUpperSize": "0"
        },
        columns=data["columns"],
        coords=(309, 175)
    )

    agregar_stage(job, "V0S3", "ORA_INSERT", "OracleConnectorPX", input_pin="V0S3P1")

    agregar_metabag_completo(job[-1], {
    "VariantName": "11",
    "VariantLibrary": "ccora11g",
    "VariantVersion": "1.0",
    "SupportedVariants": r'V1;11:"11g":ccora11g;12:"12c":ccora12c',
    "SupportedVariantsLibraries": "ccora11g,ccora12c",
    "SupportedVariantsVersions": "1.0,1.0",
    "Orientation": "link",
    "RejectFromLink": "-1",
    "RejectThreshold": "0",
    "RejectNumber": "0",
    "RejectUsesPercentage": "false",
    "ConnectorName": "OracleConnector",
    "Engine": "EE",
    "Context": "target",
    "ConnectionString": "/Connection/Server",
    "Username": "/Connection/Username",
    "Password": "/Connection/Password",
    "RACName": "/Connection/RACName",
    "xaoDbName": "/Connection/xaoDbName",
    "OSLevelAuthentication": "/Connection/OSLevelAuthentication",
    "supportedTransactionModel": "local",
    "XMLProperties": """<?xml version='1.0' encoding='UTF-16'?><Properties version='1.1'><Common><Context type='int'>2</Context><Variant type='string'>11</Variant><DescriptorVersion type='string'>1.0</DescriptorVersion><PartitionType type='int'>-1</PartitionType><RCP type='int'>0</RCP></Common><Connection><Username type='string'><![CDATA[]]></Username><Password type='protectedstring'><![CDATA[{iisenc}]]></Password><OSLevelAuthentication type='bool'><![CDATA[0]]></OSLevelAuthentication><Version type='string'><![CDATA[11g]]></Version></Connection><Usage><WriteMode type='int'><![CDATA[0]]></WriteMode><GenerateSQL modified='1' type='bool'><![CDATA[0]]></GenerateSQL><EnableQuotedIDs type='bool'><![CDATA[0]]></EnableQuotedIDs><SQL><InsertStatement collapsed='1' modified='1' type='string'><![CDATA[{INSERT INTO <TABLENAME> (CAMPO1,CAMPO2) VALUES(ORCHESTRATE.CAMPO1,ORCHESTRATE.CAMPO2)}]]></InsertStatement><ReadFromFileInsert type='bool'><![CDATA[0]]></ReadFromFileInsert><Tables collapsed='1'></Tables><Parameters collapsed='1'></Parameters><Columns collapsed='1'></Columns></SQL><TableAction collapsed='1' type='int'><![CDATA[0]]></TableAction><Transaction><IsolationLevel type='int'><![CDATA[0]]></IsolationLevel><RecordCount type='int'><![CDATA[2000]]></RecordCount></Transaction><Session><ArraySize type='int'><![CDATA[2000]]></ArraySize><DropUnmatchedFields type='bool'><![CDATA[0]]></DropUnmatchedFields><TreatWarningsAsErrors type='bool'><![CDATA[0]]></TreatWarningsAsErrors><PreserveTrailingBlanks type='bool'><![CDATA[1]]></PreserveTrailingBlanks><FailOnRowErrorPX type='bool'><![CDATA[1]]></FailOnRowErrorPX></Session><Logging><LogColumnValues collapsed='1' type='bool'><![CDATA[0]]></LogColumnValues></Logging><BeforeAfter collapsed='1' type='bool'><![CDATA[0]]></BeforeAfter><ApplicationFailoverControl collapsed='1' type='bool'><![CDATA[0]]></ApplicationFailoverControl><Reconnect collapsed='1' type='bool'><![CDATA[0]]></Reconnect><Disconnect collapsed='1' type='int'><![CDATA[0]]></Disconnect></Usage></Properties >"""
    }, name="Properties", tipo="CustomProperty")

    agregar_pin(
        job, "V0S3P1", "CustomInput", "LNK_1", "V0S0|V0S0P1",
        props_dict={
            "VariantName": "11", "VariantLibrary": "ccora11g", "VariantVersion": "1.0",
            "RejectFromLink": "-1", "RejectThreshold": "0", "RejectNumber": "0",
            "RejectUsesPercentage": "false", "ConnectorName": "OracleConnector"
        },
        metabag_dict={"RTColumnProp": "0"}
    )

    indent_xml(root)
    xml_str = ET.tostring(root, encoding="UTF-8", xml_declaration=True).decode("UTF-8")

    return {
        "natural_language_request": state["natural_language_request"],
        "generated_xml": xml_str
    }

def actualizar_input_request_desde_archivos(ruta_prompts: str):
    """
    Lee los archivos desde la ruta especificada, busca los archivos que inician por 'LOD_',
    y genera un XML para cada archivo encontrado.

    Args:
        ruta_prompts (str): Ruta donde se encuentran los archivos de prompts.
    """
    if not os.path.exists(ruta_prompts):
        raise FileNotFoundError(f"La ruta especificada no existe: {ruta_prompts}")

    archivos_ext = [archivo for archivo in os.listdir(ruta_prompts) if archivo.startswith("LOD_")]

    if not archivos_ext:
        print("No se encontraron archivos que inicien con 'LOD_' en la ruta especificada.")
        return

    for archivo in archivos_ext:
        ruta_archivo = os.path.join(ruta_prompts, archivo)
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            contenido = f.read()
            print(f"Procesando archivo: {archivo}")
            # Crear el input request para LangGraph
            
            input_request = {"natural_language_request": contenido}

            # Ejecutar el grafo de LangGraph
            result = graph.invoke(input_request)

            # Guardar el archivo XML generado
            guardar_xml(result["generated_xml"], nombre_archivo=f"{archivo.replace('.txt', '')}.xml")

            print(f"✅ Extracción creada exitosamente para el archivo: {archivo}")

def guardar_xml(xml_content, ruta_directorio="./output", nombre_archivo=None):
    if ruta_directorio is None:
        ruta_directorio = os.path.join(os.path.dirname(__file__), "..", "tmp", "output")
    os.makedirs(ruta_directorio, exist_ok=True)
    if nombre_archivo is None:
        fecha_hora = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_archivo = f"JOB_LOD_AGENTE_{fecha_hora}.xml"
    ruta_completa = os.path.join(ruta_directorio, nombre_archivo)
    with open(ruta_completa, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"✅ Archivo guardado exitosamente en: {ruta_completa}")

builder = StateGraph(AgentState)
builder.add_node("interpretar_y_generar_insert_xml", interpretar_y_generar_insert_xml)
builder.set_entry_point("interpretar_y_generar_insert_xml")
builder.add_edge("interpretar_y_generar_insert_xml", END)
graph = builder.compile()

def run(nombre_proceso_ppal: str):
    base_dir = os.path.dirname(__file__)
    ruta = os.path.join(base_dir, "..", "tmp", "prompts_datastage", nombre_proceso_ppal)
    archivo_prompt = os.path.join(ruta, f"LOD_{nombre_proceso_ppal}.txt")
    if not os.path.exists(archivo_prompt):
        print(f"⚠️ No se encontró el archivo: {archivo_prompt}")
        return
    with open(archivo_prompt, "r", encoding="utf-8") as f:
        contenido_prompt = f.read()
    input_request = {
        "natural_language_request": contenido_prompt
    }
    try:
        result = graph.invoke(input_request)
        guardar_xml(result["generated_xml"])
        print(f"✅ XML generado exitosamente para {nombre_proceso_ppal}")
    except Exception as e:
        print(f"❌ Error al generar XML para {nombre_proceso_ppal}: {e}")

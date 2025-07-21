import os
import re
from datetime import datetime

from dotenv import load_dotenv
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import TypedDict
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage
from langchain_aws import ChatBedrock
from datetime import datetime

# Cargar variables de entorno desde .env
# load_dotenv()
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# Configuración del modelo Claude 3 Sonnet en AWS Bedrock
def get_bedrock_llm():
    return ChatBedrock(
        model_id=MODEL,
        model_kwargs={
            "max_tokens": 4096,
            "temperature": 0,
            "anthropic_version": "bedrock-2023-05-31"
        },
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )

llm = get_bedrock_llm()

class AgentState(TypedDict):
    natural_language_request: str
    generated_xml: str

# ----------------------
# Helper: identación bonita del XML
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

# ----------------------
# Hardcodeado: cabecera fija
def crear_header(job_name: str) -> ET.Element:
    ahora = datetime.now()
    fecha = ahora.strftime("%Y-%m-%d")
    hora = ahora.strftime("%H.%M.%S")
    root = ET.Element("DSExport")
    ET.SubElement(root, "Header", {
        "CharacterSet": "CP1252",
        "ExportingTool": "IBM InfoSphere DataStage Export",
        "ToolVersion": "8",
        "ServerName": "LDBOG284V",
        "ToolInstanceID": "PRY_CTIF",
        "Date": fecha,
        "Time": hora,
        "ServerVersion": "11.7"
    })
    return root

def agregar_parameters(record):
    param_coll = ET.SubElement(record, "Collection", {"Name": "Parameters", "Type": "Parameters"})
    for param in [
        {"Name": "PSET_RUTAS", "Prompt": "Rutas params", "Default": "(As pre-defined)"},
        {"Name": "PSET_SAM", "Prompt": "SAM params", "Default": "(As pre-defined)"}
    ]:
        sub_rec = ET.SubElement(param_coll, "SubRecord")
        for k, v in param.items():
            ET.SubElement(sub_rec, "Property", {"Name": k}).text = str(v)


def agregar_meta_bag(record):
    meta_bag = ET.SubElement(record, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"})
    for meta in [
        {"Owner": "APT", "Name": "AdvancedRuntimeOptions", "Value": "#DSProjectARTOptions#"},
        {"Owner": "APT", "Name": "TraceMode", "Value": "0"},
        {"Owner": "APT", "Name": "TraceSeq", "Value": "1"},
        {"Owner": "APT", "Name": "TraceRecords", "Value": "100"},
        {"Owner": "APT", "Name": "TraceSkip", "Value": "0"},
        {"Owner": "APT", "Name": "TracePeriod", "Value": "1"},
        {"Owner": "APT", "Name": "RecordJobPerformanceData", "Value": "0"},
        {"Owner": "APT", "Name": "IdentList", "Value": "ORA1"},
        {"Owner": "APT", "Name": "ClientCodePage", "Value": "1252"}
    ]:
        sub_rec = ET.SubElement(meta_bag, "SubRecord")
        for k, v in meta.items():
            ET.SubElement(sub_rec, "Property", {"Name": k}).text = str(v)

def construir_orchestrate_code(json_response):
    job_name = json_response["job_name"]

    # Buscar primer stage OracleConnectorPX
    oracle_stage = next((s for s in json_response["stages"] if s["type"] == "OracleConnectorPX"), None)
    if oracle_stage is None:
        raise ValueError("No se encontró un stage OracleConnectorPX en la definición")

    oracle_stage_name = oracle_stage["name"]
    sql_query = oracle_stage.get("sql_query", "SELECT 1")

    # Buscar primer link
    first_link = json_response["links"][0]
    link_name = first_link["name"]

    # Buscar primer stage PxDataSet
    px_stage = next((s for s in json_response["stages"] if s["type"] == "PxDataSet"), None)
    if px_stage is None:
        raise ValueError("No se encontró un stage PxDataSet en la definición")

    px_target_name = px_stage["name"]
    dataset_name = px_target_name  # Puedes cambiar esto si usas otro nombre para el dataset

    # Construir el orchestrate_code en formato multilínea
    orchestrate_code = f"""Job {job_name}
(
    OracleConnectorPX {oracle_stage_name}
    (
        '{sql_query}'
    )
    -> {link_name}
    -> PxDataSet {px_target_name}
    (
        '{dataset_name}'
    )
)"""

    return orchestrate_code

def agregar_orchestrate_code(record, code: str):
    ET.SubElement(record, "Property", {"Name": "OrchestrateCode", "PreFormatted": "1"}).text = str(code)

def agregar_root_record(root, job_name, orchestrate_code):
    job = ET.SubElement(root, "Job", {
        "Identifier": job_name,
        "DateModified": datetime.now().strftime("%Y-%m-%d"),
        "TimeModified": datetime.now().strftime("%H.%M.%S")
    })
    root_rec = ET.SubElement(job, "Record", {"Identifier": "ROOT", "Type": "JobDefn", "Readonly": "0"})
    propiedades_fijas = {
        "Name": job_name,
        "NextID": "1",
        "Container": "V0",
        "JobVersion": "56.0.0",
        "ControlAfterSubr": "0",
        "NULLIndicatorPosition": "0",
        "IsTemplate": "0",
        "NLSLocale": ",,,,",
        "JobType": "3",
        "Category": "\\Jobs\\UTILIDADES",
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

    #  Agregar solo las básicas primero
    for k in ["Name", "NextID", "Container", "JobVersion", "ControlAfterSubr"]:
        ET.SubElement(root_rec, "Property", {"Name": k}).text = propiedades_fijas[k]

    #  Ahora agregar Parameters y MetaBag
    agregar_parameters(root_rec)
    agregar_meta_bag(root_rec)

    #  Agregar el resto de propiedades después
    for k, v in propiedades_fijas.items():
        if k not in ["Name", "NextID", "Container", "JobVersion", "ControlAfterSubr"]:
            ET.SubElement(root_rec, "Property", {"Name": k}).text = str(v)

    #  Agregar OrchestrateCode al final
    agregar_orchestrate_code(root_rec, orchestrate_code)



# Contadores globales por tipo
contadores_por_tipo = {}

def obtener_nombre(tipo, nombre_usuario=None):
    tipo_clean = tipo.lower()
    if nombre_usuario:
        return nombre_usuario
    contador = contadores_por_tipo.get(tipo_clean, 1)
    nombre_generado = f"{tipo_clean}_default_{str(contador).zfill(2)}"
    contadores_por_tipo[tipo_clean] = contador + 1
    return nombre_generado


def agregar_stages(root, stages, links):
    job = root.find("Job")
    for stage in stages:
        stage_id = stage["id"]
        stage_name = stage["name"]
        stage_type = stage["type"]

        stage_rec = ET.SubElement(job, "Record", {"Identifier": stage_id, "Type": "CustomStage", "Readonly": "0"})
        ET.SubElement(stage_rec, "Property", {"Name": "Name"}).text = stage_name
        ET.SubElement(stage_rec, "Property", {"Name": "StageType"}).text = stage_type
        ET.SubElement(stage_rec, "Property", {"Name": "AllowColumnMapping"}).text = "0"
        ET.SubElement(stage_rec, "Property", {"Name": "NextID"}).text = "2"
        ET.SubElement(stage_rec, "Property", {"Name": "NextRecordID"}).text = "0"

        if any(link["source"] == stage_id for link in links):
            ET.SubElement(stage_rec, "Property", {"Name": "OutputPins"}).text = f"{stage_id}P1"
        if any(link["target"] == stage_id for link in links):
            ET.SubElement(stage_rec, "Property", {"Name": "InputPins"}).text = f"{stage_id}P1"

        props_coll = ET.SubElement(stage_rec, "Collection", {"Name": "Properties", "Type": "CustomProperty"})

        for prop_name, prop_value in [
            ("VariantName", "11"),
            ("VariantLibrary", "ccora11g"),
            ("VariantVersion", "1.0"),
            ("SupportedVariants", 'V1;11:"11g":ccora11g;12:"12c":ccora12c'),
            ("SupportedVariantsLibraries", "ccora11g,ccora12c"),
            ("SupportedVariantsVersions", "1.0,1.0"),
            ("Orientation", "link"),
            ("RejectFromLink", "-1"),
            ("RejectThreshold", "0"),
            ("RejectNumber", "0"),
            ("RejectUsesPercentage", "false"),
            ("ConnectorName", "OracleConnector"),
            ("Engine", "EE"),
            ("Context", "source")
        ]:
            sub_rec = ET.SubElement(props_coll, "SubRecord")
            ET.SubElement(sub_rec, "Property", {"Name": "Name"}).text = prop_name
            ET.SubElement(sub_rec, "Property", {"Name": "Value"}).text = prop_value

        if stage_type == "OracleConnectorPX":
            sql_query = stage.get('sql_query', 'SELECT 1')
            for extra_prop in [
                ("ConnectionString", "/Connection/Server"),
                ("Username", "/Connection/Username"),
                ("Password", "/Connection/Password"),
                ("RACName", "/Connection/RACName"),
                ("xaoDbName", "/Connection/xaoDbName"),
                ("OSLevelAuthentication", "/Connection/OSLevelAuthentication")
            ]:
                sub_rec = ET.SubElement(props_coll, "SubRecord")
                ET.SubElement(sub_rec, "Property", {"Name": "Name"}).text = extra_prop[0]
                ET.SubElement(sub_rec, "Property", {"Name": "Value"}).text = extra_prop[1]

            xml_properties_value = (
                "<?xml version='1.0' encoding='UTF-16'?>"
                "<Properties version='1.1'>"
                "<Common>"
                "<Context type='int'>1</Context>"
                "<Variant type='string'>11</Variant>"
                "<DescriptorVersion type='string'>1.0</DescriptorVersion>"
                "<PartitionType type='int'>-1</PartitionType>"
                "<RCP type='int'>0</RCP>"
                "</Common>"
                "<Connection>"
                "<Server modified='1' type='string'><![CDATA[#PSET_SAM.$VAG_ORA_URI_ADMSAM#]]></Server>"
                "<Username modified='1' type='string'><![CDATA[#PSET_SAM.$VAG_ORA_USU_ADMSAM#]]></Username>"
                "<Password modified='1' type='string'><![CDATA[#PSET_SAM.$VAG_ORA_PASS_ADMSAM#]]></Password>"
                "<OSLevelAuthentication type='bool'><![CDATA[0]]></OSLevelAuthentication>"
                "<Version type='string'><![CDATA[11g]]></Version>"
                "</Connection>"
                "<Usage>"
                "<ReadMode type='int'><![CDATA[0]]></ReadMode>"
                "<GenerateSQL type='bool'><![CDATA[0]]></GenerateSQL>"
                "<EnableQuotedIDs type='bool'><![CDATA[0]]></EnableQuotedIDs>"
                "<SQL>"
                f"<SelectStatement modified='1' type='string'><![CDATA[{sql_query}]]></SelectStatement>"
                "<ReadFromFileSelect type='bool'><![CDATA[0]]></ReadFromFileSelect>"
                "<Tables collapsed='1'></Tables>"
                "<Parameters collapsed='1'></Parameters>"
                "<Columns collapsed='1'></Columns>"
                "</SQL>"
                "<EnablePartitionedReads collapsed='1' type='bool'><![CDATA[0]]></EnablePartitionedReads>"
                "<Transaction>"
                "<IsolationLevel type='int'><![CDATA[0]]></IsolationLevel>"
                "<RecordCount type='int'><![CDATA[2000]]></RecordCount>"
                "<EndOfWave type='int'><![CDATA[0]]></EndOfWave>"
                "</Transaction>"
                "<Session>"
                "<ArraySize type='int'><![CDATA[2000]]></ArraySize>"
                "<PrefetchRowCount type='int'><![CDATA[1]]></PrefetchRowCount>"
                "<PrefetchMemorySize type='int'><![CDATA[0]]></PrefetchMemorySize>"
                "<PassLobLocator collapsed='1' type='bool'><![CDATA[0]]></PassLobLocator>"
                "<BFILEasBLOB type='bool'><![CDATA[0]]></BFILEasBLOB>"
                "<TreatWarningsAsErrors type='bool'><![CDATA[0]]></TreatWarningsAsErrors>"
                "<TreatFetchTruncateAsError type='bool'><![CDATA[1]]></TreatFetchTruncateAsError>"
                "</Session>"
                "<BeforeAfter collapsed='1' type='bool'><![CDATA[0]]></BeforeAfter>"
                "<ApplicationFailoverControl collapsed='1' type='bool'><![CDATA[0]]></ApplicationFailoverControl>"
                "<LimitRows collapsed='1' type='bool'><![CDATA[0]]></LimitRows>"
                "</Usage>"
                "</Properties>"
            )

            sub_rec = ET.SubElement(props_coll, "SubRecord")
            ET.SubElement(sub_rec, "Property", {"Name": "Name"}).text = "XMLProperties"
            ET.SubElement(sub_rec, "Property", {"Name": "Value"}).text = xml_properties_value

        if stage_type == "PxDataSet":
            sub_rec = ET.SubElement(props_coll, "SubRecord")
            ET.SubElement(sub_rec, "Property", {"Name": "Name"}).text = "dataset"
            ET.SubElement(sub_rec, "Property", {"Name": "Value"}).text = f"{stage_name}.ds"


def generar_columnas_completas(padre_xml, columnas, tipo_columna):
    """
    Agrega una colección de columnas al nodo padre.
    tipo_columna debe ser 'OutputColumn' o 'InputColumn'
    """
    columnas_coll = ET.SubElement(padre_xml, "Collection", {"Name": "Columns", "Type": tipo_columna})
    for col in columnas:
        col_rec = ET.SubElement(columnas_coll, "SubRecord")
        ET.SubElement(col_rec, "Property", {"Name": "Name"}).text = col["Name"]
        ET.SubElement(col_rec, "Property", {"Name": "SqlType"}).text = str(col.get("SqlType", 12))
        ET.SubElement(col_rec, "Property", {"Name": "Precision"}).text = str(col.get("Precision", 20))
        ET.SubElement(col_rec, "Property", {"Name": "Scale"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "Nullable"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "KeyPosition"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "DisplaySize"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "Group"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "SortKey"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "SortType"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "AllowCRLF"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "LevelNo"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "Occurs"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "PadNulls"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "SignOption"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "SortingOrder"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "ArrayHandling"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "SyncIndicator"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "PadChar"})
        ET.SubElement(col_rec, "Property", {"Name": "ExtendedPrecision"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "TaggedSubrec"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "OccursVarying"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "PKeyIsCaseless"}).text = "0"
        ET.SubElement(col_rec, "Property", {"Name": "SCDPurpose"}).text = "0"




def agregar_links(root, links):
    job = root.find("Job")
    for link in links:
        link_id = link["id"]
        link_name = link["name"]
        source_id = link["source"]
        target_id = link["target"]

        # Output pin (CustomOutput)
        out_rec = ET.SubElement(job, "Record", {"Identifier": f"{source_id}P1", "Type": "CustomOutput", "Readonly": "0"})
        ET.SubElement(out_rec, "Property", {"Name": "Name"}).text = link_name
        ET.SubElement(out_rec, "Property", {"Name": "Partner"}).text = f"{target_id}|{target_id}P1"

        props_coll = ET.SubElement(out_rec, "Collection", {"Name": "Properties", "Type": "CustomProperty"})
        for prop_name, prop_value in [
            ("lookup\\type", ""),
            ("VariantName", "11"),
            ("VariantLibrary", "ccora11g"),
            ("VariantVersion", "1.0"),
            ("RejectFromLink", "-1"),
            ("RejectThreshold", "0"),
            ("RejectNumber", "0"),
            ("RejectUsesPercentage", "false"),
            ("ConnectorName", "OracleConnector")
        ]:
            sub_rec = ET.SubElement(props_coll, "SubRecord")
            ET.SubElement(sub_rec, "Property", {"Name": "Name"}).text = prop_name
            ET.SubElement(sub_rec, "Property", {"Name": "Value"}).text = prop_value

        # ✅ Columns → OutputColumns (cambio aquí)
        columns_coll = ET.SubElement(out_rec, "Collection", {"Name": "Columns", "Type": "OutputColumn"})
        #columns_coll = ET.SubElement(out_rec, "Collection", {"Name": "OutputColumns", "Type": "OutputColumn"})
        for col in link["columns"]:
            col_rec = ET.SubElement(columns_coll, "SubRecord")
            for prop_name, prop_value in [
                ("Name", col["Name"]),
                ("SqlType", str(col.get("SqlType", 12))),
                ("Precision", str(col.get("Precision", 20))),
                ("Scale", "0"),
                ("Nullable", "0"),
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
            ]:
                ET.SubElement(col_rec, "Property", {"Name": prop_name}).text = prop_value

        # MetaBag
        metabag = ET.SubElement(out_rec, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"})
        for meta in [
            {"Owner": "APT", "Name": "DiskWriteInc", "Value": "1048576"},
            {"Owner": "APT", "Name": "BufFreeRun", "Value": "50"},
            {"Owner": "APT", "Name": "MaxMemBufSize", "Value": "3145728"},
            {"Owner": "APT", "Name": "QueueUpperSize", "Value": "0"}
        ]:
            sub_rec = ET.SubElement(metabag, "SubRecord")
            for k, v in meta.items():
                ET.SubElement(sub_rec, "Property", {"Name": k}).text = str(v)

        # Input pin (CustomInput)
        in_rec = ET.SubElement(job, "Record", {"Identifier": f"{target_id}P1", "Type": "CustomInput", "Readonly": "0"})
        ET.SubElement(in_rec, "Property", {"Name": "Name"}).text = link_name
        ET.SubElement(in_rec, "Property", {"Name": "Partner"}).text = f"{source_id}|{source_id}P1"
        ET.SubElement(in_rec, "Property", {"Name": "LinkType"}).text = "1"
        ET.SubElement(in_rec, "Property", {"Name": "ConditionNotMet"}).text = "fail"
        ET.SubElement(in_rec, "Property", {"Name": "LookupFail"}).text = "fail"
        ET.SubElement(in_rec, "Property", {"Name": "TransactionSize"}).text = "0"
        ET.SubElement(in_rec, "Property", {"Name": "TXNBehaviour"}).text = "0"
        ET.SubElement(in_rec, "Property", {"Name": "EnableTxGroup"}).text = "0"
        ET.SubElement(in_rec, "Property", {"Name": "LinkMinimised"}).text = "0"

        props_in = ET.SubElement(in_rec, "Collection", {"Name": "Properties", "Type": "CustomProperty"})
        for prop_name, prop_value in [
            ("dataset", f"{link_name}.ds"),
            ("datasetmode", ">| [ds")
        ]:
            sub_rec = ET.SubElement(props_in, "SubRecord")
            ET.SubElement(sub_rec, "Property", {"Name": "Name"}).text = prop_name
            ET.SubElement(sub_rec, "Property", {"Name": "Value"}).text = prop_value

        # MetaBag Input
        metabag_in = ET.SubElement(in_rec, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"})
        ET.SubElement(metabag_in, "SubRecord")
        ET.SubElement(metabag_in[0], "Property", {"Name": "Owner"}).text = "APT"
        ET.SubElement(metabag_in[0], "Property", {"Name": "Name"}).text = "RTColumnProp"
        ET.SubElement(metabag_in[0], "Property", {"Name": "Value"}).text = "0"

        # ✅ Columns → InputColumns (cambio aquí)
        #columns_in = ET.SubElement(in_rec, "Collection", {"Name": "Columns", "Type": "InputColumn"})
        #columns_in = ET.SubElement(in_rec, "Collection", {"Name": "InputColumns", "Type": "InputColumn"})
        #for col in link["columns"]:
        #    col_rec = ET.SubElement(columns_in, "SubRecord")
        #    for prop_name, prop_value in [
        #        ("Name", col["Name"]),
        #        ("SqlType", str(col.get("SqlType", 12))),
        #        ("Precision", str(col.get("Precision", 20))),
        #        ("Scale", "0"),
        #        ("Nullable", "0"),
        #        ("KeyPosition", "0"),
        #        ("DisplaySize", "0"),
        #        ("Group", "0"),
        #        ("SortKey", "0"),
        #        ("SortType", "0"),
        #        ("AllowCRLF", "0"),
        #        ("LevelNo", "0"),
        #        ("Occurs", "0"),
        #        ("PadNulls", "0"),
        #        ("SignOption", "0"),
        #        ("SortingOrder", "0"),
        #        ("ArrayHandling", "0"),
        #        ("SyncIndicator", "0"),
        #        ("PadChar", ""),
        #        ("ExtendedPrecision", "0"),
        #        ("TaggedSubrec", "0"),
        #        ("OccursVarying", "0"),
        #        ("PKeyIsCaseless", "0"),
        #        ("SCDPurpose", "0")
        #    ]:
        #        ET.SubElement(col_rec, "Property", {"Name": prop_name}).text = prop_value

def agregar_columns_a_links(root, links):
    # ¡ELIMINADO! No se deben agregar columnas directamente a los links.
    pass  # Este método ya no hace nada.


def agregar_metabag_a_links(root, links):
    job = root.find("Job")
    for link in links:
        # Buscar el registro de Output
        output_id = f"{link['source']}P1"
        output_rec = next((rec for rec in job.findall("Record") if rec.get("Identifier") == output_id), None)
        if output_rec is not None:
            meta_bag_out = ET.SubElement(output_rec, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"})
            for meta in [
                {"Owner": "APT", "Name": "DiskWriteInc", "Value": "1048576"},
                {"Owner": "APT", "Name": "BufFreeRun", "Value": "50"},
                {"Owner": "APT", "Name": "MaxMemBufSize", "Value": "3145728"},
                {"Owner": "APT", "Name": "QueueUpperSize", "Value": "0"}
            ]:
                sub_rec = ET.SubElement(meta_bag_out, "SubRecord")
                for k, v in meta.items():
                    ET.SubElement(sub_rec, "Property", {"Name": k}).text = str(v)

        # Buscar el registro de Input
        input_id = f"{link['target']}P1"
        input_rec = next((rec for rec in job.findall("Record") if rec.get("Identifier") == input_id), None)
        if input_rec is not None:
            meta_bag_in = ET.SubElement(input_rec, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"})
            for meta in [
                {"Owner": "APT", "Name": "RTColumnProp", "Value": "0"}
            ]:
                sub_rec = ET.SubElement(meta_bag_in, "SubRecord")
                for k, v in meta.items():
                    ET.SubElement(sub_rec, "Property", {"Name": k}).text = str(v)


def agregar_container_view(root, stages, links):
    job = root.find("Job")
    container = ET.SubElement(job, "Record", {"Identifier": "V0", "Type": "ContainerView", "Readonly": "0"})

    # Sacamos los datos de stages y links
    stage_ids = [stage["id"] for stage in stages]
    stage_names = [stage["name"] for stage in stages]
    stage_types = [stage["type"] for stage in stages]
    link_names = [link["name"] for link in links]
    target_stage_ids = [link["target"] for link in links]
    source_pins = [f"{link['source']}P1" for link in links]

    # Configuración de posiciones
    stage_x_pos = "|".join(["144", "312"] if len(stages) == 2 else ["96" for _ in stages])
    stage_y_pos = "|".join(["192" for _ in stages])
    stage_x_size = "|".join(["48" for _ in stages])
    stage_y_size = "|".join(["48" for _ in stages])
    stage_types_gui = "|".join(["CCustomStage.CC_GUI" if i == 0 else "CCustomStage" for i in range(len(stages))])

    # Construimos todas las propiedades clave
    ET.SubElement(container, "Property", {"Name": "Name"}).text = "Job"
    ET.SubElement(container, "Property", {"Name": "NextID"}).text = str(len(stages) + 1)
    ET.SubElement(container, "Property", {"Name": "IsTopLevel"}).text = "0"
    ET.SubElement(container, "Property", {"Name": "StageList"}).text = "|".join(stage_ids)
    ET.SubElement(container, "Property", {"Name": "StageXPos"}).text = stage_x_pos
    ET.SubElement(container, "Property", {"Name": "StageYPos"}).text = stage_y_pos
    ET.SubElement(container, "Property", {"Name": "StageTypes"}).text = stage_types_gui
    ET.SubElement(container, "Property", {"Name": "NextStageID"}).text = str(len(stages) + 2)
    ET.SubElement(container, "Property", {"Name": "SnapToGrid"}).text = "1"
    ET.SubElement(container, "Property", {"Name": "GridLines"}).text = "0"
    ET.SubElement(container, "Property", {"Name": "ZoomValue"}).text = "100"
    ET.SubElement(container, "Property", {"Name": "StageXSize"}).text = stage_x_size
    ET.SubElement(container, "Property", {"Name": "StageYSize"}).text = stage_y_size
    ET.SubElement(container, "Property", {"Name": "ContainerViewSizing"}).text = "0104 0104 0555 0435 0000 0001 0000 0000"
    ET.SubElement(container, "Property", {"Name": "StageNames"}).text = "|".join(stage_names)
    ET.SubElement(container, "Property", {"Name": "StageTypeIDs"}).text = "|".join(stage_types)
    ET.SubElement(container, "Property", {"Name": "LinkNames"}).text = "|".join(link_names)
    ET.SubElement(container, "Property", {"Name": "TargetStageIDs"}).text = "|".join(target_stage_ids)
    ET.SubElement(container, "Property", {"Name": "LinkSourcePinIDs"}).text = "|".join(source_pins)
    ET.SubElement(container, "Property", {"Name": "SourceStageEffectiveExecutionModes"}).text = "|".join(["2" for _ in links])
    ET.SubElement(container, "Property", {"Name": "SourceStageRuntimeExecutionModes"}).text = "|".join(["2" for _ in links])
    ET.SubElement(container, "Property", {"Name": "TargetStageEffectiveExecutionModes"}).text = "|".join(["2" for _ in links])
    ET.SubElement(container, "Property", {"Name": "TargetStageRuntimeExecutionModes"}).text = "|".join(["2" for _ in links])
    ET.SubElement(container, "Property", {"Name": "LinkIsSingleOperatorLookup"}).text = "|".join(["False" for _ in links])
    ET.SubElement(container, "Property", {"Name": "LinkIsSortSequential"}).text = "|".join(["False" for _ in links])
    ET.SubElement(container, "Property", {"Name": "LinkSortMode"}).text = "|".join(["0" for _ in links])
    ET.SubElement(container, "Property", {"Name": "LinkPartColMode"}).text = "|".join(["1" for _ in links])
    ET.SubElement(container, "Property", {"Name": "LinkHasMetaDatas"}).text = "|".join(["True" for _ in links])
    ET.SubElement(container, "Property", {"Name": "LinkTypes"}).text = "|".join(["1" for _ in links])
    ET.SubElement(container, "Property", {"Name": "LinkNamePositionXs"}).text = "|".join(["260" for _ in links])
    ET.SubElement(container, "Property", {"Name": "LinkNamePositionYs"}).text = "|".join(["216" for _ in links])



# ----------------------
# Lógica principal
def interpretar_y_generar_xml(state: AgentState) -> AgentState:
    prompt = f"""
Eres un experto en IBM DataStage Designer.

Analiza esta solicitud:
{state["natural_language_request"]}

Responde SOLO con un JSON perfectamente formateado y parseable por json.loads(), usando estas claves:
- "job_name": nombre del job.
- "stages": lista de stages, cada uno con:
    - "id": identificador único (por ejemplo V0S0, V0S1).
    - "name": nombre del stage.
    - "type": tipo del stage (por ejemplo: OracleConnectorPX, PxDataSet).
    - "sql_query": la consulta SQL (solo si aplica, como en OracleConnectorPX).
    - "table_name": nombre de la tabla principal (solo si aplica).
    - "column_list": lista de columnas usadas (como texto separado por comas, ej. col1,col2).
- "links": lista de links, cada uno con:
    - "id": identificador único (ej. LNK1).
    - "name": nombre del link.
    - "source": id del stage origen (ej. V0S0).
    - "target": id del stage destino (ej. V0S1).
    - "columns": lista de columnas, cada una como:
        - "Name": nombre de la columna.
        - "SqlType": tipo SQL (como número, ej. 4 para int).
        - "Precision": precisión numérica (ej. 5).

IMPORTANTE:
- Usa nombres generados automáticamente si no se proporcionan, siguiendo el patrón: {{tipo}}_default_01, {{tipo}}_default_02, etc.
- Asegúrate de incluir los detalles de conexión Oracle, incluyendo sql_query, table_name y column_list.
- Responde SOLO con el JSON, sin comentarios adicionales.
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        # Extraer solo el bloque JSON si hay texto adicional
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            json_str = match.group()
        else:
            json_str = raw
        json_response = json.loads(json_str)
    except Exception as e:
        print("Respuesta del modelo:\n", response.content)
        raise RuntimeError(f"Error interpretando respuesta IA: {e}")

    try:
        # Construir orchestrate_code manualmente, no confiar en JSON
        orchestrate_code = construir_orchestrate_code(json_response)

        # Crear XML base
        root = crear_header(json_response["job_name"])
        agregar_root_record(root, json_response["job_name"], orchestrate_code)
        agregar_container_view(root, json_response["stages"], json_response["links"])
        agregar_stages(root, json_response["stages"], json_response["links"])
        agregar_links(root, json_response["links"])
        
        # Formatear indentación bonita
        indent_xml(root)

        # Convertir a string final
        xml_generado = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

        return {
            "natural_language_request": state["natural_language_request"],
            "generated_xml": xml_generado
        }

    except Exception as e:
        raise RuntimeError(f"Error generando XML final: {e}")
    
def actualizar_input_request_desde_archivos(ruta_prompts: str):
    """
    Lee los archivos desde la ruta especificada, busca los archivos que inician por 'EXT_',
    y genera un XML para cada archivo encontrado.

    Args:
        ruta_prompts (str): Ruta donde se encuentran los archivos de prompts.
    """
    if not os.path.exists(ruta_prompts):
        raise FileNotFoundError(f"La ruta especificada no existe: {ruta_prompts}")

    archivos_ext = [archivo for archivo in os.listdir(ruta_prompts) if archivo.startswith("EXT_")]

    if not archivos_ext:
        print("No se encontraron archivos que inicien con 'EXT_' en la ruta especificada.")
        return

    for archivo in archivos_ext:
        ruta_archivo = os.path.join(ruta_prompts, archivo)
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            contenido = f.read()
            input_request = {"natural_language_request": contenido}

            # Ejecutar el grafo de LangGraph
            result = graph.invoke(input_request)

            # Guardar el archivo XML generado
            guardar_xml(result["generated_xml"], nombre_archivo=f"{archivo.replace('.txt', '')}.xml")

            print(f"✅ Extracción creada exitosamente para el archivo: {archivo}")

def guardar_xml(xml_content, ruta_directorio=None, nombre_archivo=None):
    if ruta_directorio is None:
        ruta_directorio = os.path.join(os.path.dirname(__file__), "..", "tmp", "output")
    os.makedirs(ruta_directorio, exist_ok=True)
    if nombre_archivo is None:
        fecha_hora = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_archivo = f"JOB_EXT_AGENTE_{fecha_hora}.xml"
    ruta_completa = os.path.join(ruta_directorio, nombre_archivo)
    with open(ruta_completa, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"✅ Archivo guardado exitosamente en: {ruta_completa}")


def run(nombre_proceso_ppal: str):
    builder = StateGraph(AgentState)
    builder.add_node("interpretar_y_generar_xml", interpretar_y_generar_xml)
    builder.set_entry_point("interpretar_y_generar_xml")
    builder.add_node("Leer prompts", lambda state: actualizar_input_request_desde_archivos("./prompts"))
    builder.add_edge("interpretar_y_generar_xml", END)
    graph = builder.compile()
    nombre_proceso_ppal = globals().get('nombre_proceso_ppal', None)
    if nombre_proceso_ppal is None:
        # Si no se pasa como variable global, usar valor por defecto o lanzar error
        nombre_proceso_ppal = "PAQ_PPAL_DIM_CLIENTE"  # Valor por defecto o puedes lanzar una excepción

    ruta= f"./prompts_datastage/{nombre_proceso_ppal}"
    input_request = {
    "natural_language_request": "quiero que me haga una extración de datos de la tabla cliente, con las columnas id_cliente, nombre, apellido y fecha_registro. La consulta SQL debe ser: SELECT id_cliente, nombre, apellido, fecha_registro FROM cliente WHERE activo = 1;"
    }
    ruta = f"./prompts_datastage/{nombre_proceso_ppal}"
    archivo_prompt = os.path.join(ruta, f"EXT_{nombre_proceso_ppal}.txt")

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
    except Exception as e:
        print(f"❌ Error al generar XML para {nombre_proceso_ppal}: {e}")

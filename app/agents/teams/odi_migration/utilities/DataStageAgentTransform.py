import os
import xml.etree.ElementTree as ET
import json
import re
from dotenv import load_dotenv
from datetime import datetime
from typing import TypedDict
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage
from langchain_aws import ChatBedrock

# Cargar variables de entorno desde .env
# load_dotenv()
MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

# Configuración del modelo Claude 3 Sonnet en AWS Bedrock
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


def crear_columna_completa(col_dict):
    props = [
        ("Name", col_dict["Name"]),
        ("SqlType", str(col_dict.get("SqlType", 12))),
        ("Precision", str(col_dict.get("Precision", 20))),
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
        ("SCDPurpose", "0"),
    ]
    return props


def crear_header(job_name: str) -> ET.Element:
    ahora = datetime.now()
    root = ET.Element("DSExport")
    ET.SubElement(
        root,
        "Header",
        {
            "CharacterSet": "CP1252",
            "ExportingTool": "IBM InfoSphere DataStage Export",
            "ToolVersion": "8",
            "ServerName": "LDBOG284V",
            "ToolInstanceID": "PRY_CTIF",
            "Date": ahora.strftime("%Y-%m-%d"),
            "Time": ahora.strftime("%H.%M.%S"),
            "ServerVersion": "11.7",
        },
    )
    return root


def construir_orchestrate_code(job_name: str, stages):
    if len(stages) == 3:
        dataset_in = stages[0]["name"]
        transformer = stages[1]["name"]
        dataset_out = stages[2]["name"]
        return f"""Job {job_name}
(
    PxDataSet {dataset_in}('RUTA_DATASET_1.ds')
    -> LINK_1
    -> Transformer {transformer}
    -> LNK_SALIDA
    -> PxDataSet {dataset_out}('RUTA_DATASET_SALIDA.ds')
)"""
    else:
        raise ValueError(
            "La estructura esperada para este job es DATASET -> TRANSFORMER -> DATASET."
        )


def construir_mapeo_ids(data):
    return {stage["name"]: f"V0S{i}" for i, stage in enumerate(data["stages"])}


def agregar_metabag_default(parent_elem):
    metabag = ET.SubElement(
        parent_elem, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"}
    )
    for name, value in [
        ("DiskWriteInc", "1048576"),
        ("BufFreeRun", "50"),
        ("MaxMemBufSize", "3145728"),
        ("QueueUpperSize", "0"),
    ]:
        sub = ET.SubElement(metabag, "SubRecord")
        ET.SubElement(sub, "Property", {"Name": "Owner"}).text = "APT"
        ET.SubElement(sub, "Property", {"Name": "Name"}).text = name
        ET.SubElement(sub, "Property", {"Name": "Value"}).text = value


def agregar_columnas_completas(parent_elem, columns):
    cols = ET.SubElement(
        parent_elem, "Collection", {"Name": "Columns", "Type": "OutputColumn"}
    )
    for col in columns:
        col_rec = ET.SubElement(cols, "SubRecord")
        for name, value in crear_columna_completa(col):
            ET.SubElement(col_rec, "Property", {"Name": name}).text = value
        if "Derivation" in col:
            ET.SubElement(col_rec, "Property", {"Name": "Derivation"}).text = col[
                "Derivation"
            ]
            ET.SubElement(col_rec, "Property", {"Name": "ParsedDerivation"}).text = col[
                "Derivation"
            ]
            ET.SubElement(col_rec, "Property", {"Name": "SourceColumn"}).text = col[
                "Derivation"
            ]


def pin_id_output(stage_id, pin_number):
    return f"{stage_id}PO{pin_number}"


def pin_id_input(stage_id, pin_number):
    return f"{stage_id}PI{pin_number}"


def agregar_output_pins_completo(job, outputs, nombre_a_id):
    for out in outputs:
        stage_id = nombre_a_id[out["stage"]]
        pin_id = pin_id_output(stage_id, out["pin_number"])

        is_transformer = any(
            r.attrib.get("Identifier") == stage_id
            and r.find("./Property[@Name='StageType']").text == "CTransformerStage"
            for r in job.findall("Record")
        )
        pin_type = "TrxOutput" if is_transformer else "CustomOutput"

        rec = ET.SubElement(
            job, "Record", {"Identifier": pin_id, "Type": pin_type, "Readonly": "0"}
        )

        ET.SubElement(rec, "Property", {"Name": "Name"}).text = out["link_name"]
        ET.SubElement(rec, "Property", {"Name": "Partner"}).text = out["partner"]
        ET.SubElement(rec, "Property", {"Name": "LeftTextPos"}).text = str(
            out.get("left", 0)
        )
        ET.SubElement(rec, "Property", {"Name": "TopTextPos"}).text = str(
            out.get("top", 0)
        )
        ET.SubElement(rec, "Property", {"Name": "LinkMinimised"}).text = "0"

        if is_transformer:
            ET.SubElement(rec, "Property", {"Name": "Reject"}).text = "0"
            ET.SubElement(rec, "Property", {"Name": "ErrorPin"}).text = "0"
            ET.SubElement(rec, "Property", {"Name": "RowLimit"}).text = "0"

        # props = ET.SubElement(rec, "Collection", {"Name": "Properties", "Type": "CustomProperty"})
        # for p in out.get("properties", []):
        # sub = ET.SubElement(props, "SubRecord")
        # ET.SubElement(sub, "Property", {"Name": "Name"}).text = p["Name"]
        # ET.SubElement(sub, "Property", {"Name": "Value"}).text = p["Value"]

        if not is_transformer:
            props = ET.SubElement(
                rec, "Collection", {"Name": "Properties", "Type": "CustomProperty"}
            )
            for p in out.get("properties", []):
                sub = ET.SubElement(props, "SubRecord")
                ET.SubElement(sub, "Property", {"Name": "Name"}).text = p["Name"]
                ET.SubElement(sub, "Property", {"Name": "Value"}).text = p["Value"]

        cols = ET.SubElement(
            rec, "Collection", {"Name": "Columns", "Type": "OutputColumn"}
        )
        for col in out.get("columns", []):
            sub = ET.SubElement(cols, "SubRecord")
            for name, value in crear_columna_completa(col):
                ET.SubElement(sub, "Property", {"Name": name}).text = value

            # Derivaciones necesarias
            deriv = col.get("Derivation", col["Name"])
            for key in ["Derivation", "ParsedDerivation", "SourceColumn"]:
                ET.SubElement(sub, "Property", {"Name": key}).text = deriv

        agregar_metabag_default(rec)


def agregar_input_pins_completo(job, inputs, nombre_a_id):
    for inp in inputs:
        stage_id = nombre_a_id[inp["stage"]]
        pin_id = pin_id_input(stage_id, inp["pin_number"])

        # Detectar si es Transformer
        is_transformer = any(
            r.attrib.get("Identifier") == stage_id
            and r.find("./Property[@Name='StageType']").text == "CTransformerStage"
            for r in job.findall("Record")
        )
        pin_type = "TrxInput" if is_transformer else "CustomInput"

        rec = ET.SubElement(
            job, "Record", {"Identifier": pin_id, "Type": pin_type, "Readonly": "0"}
        )

        ET.SubElement(rec, "Property", {"Name": "Name"}).text = inp["link_name"]
        ET.SubElement(rec, "Property", {"Name": "Partner"}).text = inp["partner"]

        if not is_transformer:
            for k, v in {
                "LinkType": "1",
                "ConditionNotMet": "fail",
                "LookupFail": "fail",
                "TransactionSize": "0",
                "TXNBehaviour": "0",
                "EnableTxGroup": "0",
                "LinkMinimised": "0",
            }.items():
                ET.SubElement(rec, "Property", {"Name": k}).text = v

        if inp["stage"].startswith("DS_") or "SALIDA" in inp["stage"]:
            props = ET.SubElement(
                rec, "Collection", {"Name": "Properties", "Type": "CustomProperty"}
            )
            sub1 = ET.SubElement(props, "SubRecord")
            ET.SubElement(sub1, "Property", {"Name": "Name"}).text = "dataset"
            ET.SubElement(sub1, "Property", {"Name": "Value"}).text = (
                "RUTA_DATASET_SALIDA.ds"
            )

            sub2 = ET.SubElement(props, "SubRecord")
            ET.SubElement(sub2, "Property", {"Name": "Name"}).text = "datasetmode"
            ET.SubElement(sub2, "Property", {"Name": "Value"}).text = ">| [ds"

        # Columnas si existen
        if "columns" in inp:
            cols = ET.SubElement(
                rec, "Collection", {"Name": "Columns", "Type": "OutputColumn"}
            )
            for col in inp["columns"]:
                col_rec = ET.SubElement(cols, "SubRecord")
                for name, value in crear_columna_completa(col):
                    ET.SubElement(col_rec, "Property", {"Name": name}).text = value
                if "Derivation" in col:
                    for key in ["Derivation", "ParsedDerivation", "SourceColumn"]:
                        ET.SubElement(col_rec, "Property", {"Name": key}).text = col[
                            "Derivation"
                        ]

        # MetaBag según tipo
        if is_transformer:
            metabag = ET.SubElement(
                rec, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"}
            )
            sub = ET.SubElement(metabag, "SubRecord")
            ET.SubElement(sub, "Property", {"Name": "Owner"}).text = "APT"
            ET.SubElement(sub, "Property", {"Name": "Name"}).text = "RTColumnProp"
            ET.SubElement(sub, "Property", {"Name": "Value"}).text = "0"
        else:
            agregar_metabag_default(rec)


def agregar_links_desde_definicion(job, link_props):
    """
    Inserta propiedades en ContainerView y genera los Records tipo Link necesarios
    sin crear duplicados (verifica existencia).
    """
    container_view = next(
        r for r in job.findall("Record") if r.attrib.get("Identifier") == "V0"
    )

    def agregar_propiedad(name, value):
        ET.SubElement(container_view, "Property", {"Name": name}).text = value

    campos_esperados = [
        "LinkNames",
        "LinkTypes",
        "LinkSourcePinIDs",
        "TargetStageIDs",
        "LinkHasMetaDatas",
        "LinkNamePositionXs",
        "LinkNamePositionYs",
        "SourceStageEffectiveExecutionModes",
        "TargetStageEffectiveExecutionModes",
        "SourceStageRuntimeExecutionModes",
        "TargetStageRuntimeExecutionModes",
        "LinkIsSingleOperatorLookup",
        "LinkIsSortSequential",
        "LinkSortMode",
        "LinkPartColMode",
    ]

    for campo in campos_esperados:
        if campo in link_props:
            agregar_propiedad(campo, link_props[campo])

    nombres = link_props.get("LinkNames", "").split("|")
    from_pins = link_props.get("LinkSourcePinIDs", "").split("|")
    to_stages = link_props.get("TargetStageIDs", "").split("|")

    for i, name in enumerate(nombres):
        if i >= len(from_pins) or i >= len(to_stages):
            continue

        record_id = f"{from_pins[i]}_{to_stages[i]}"
        if job.find(f"./Record[@Identifier='{record_id}']") is not None:
            continue  # evita duplicado

        rec = ET.SubElement(
            job, "Record", {"Identifier": record_id, "Type": "Link", "Readonly": "0"}
        )
        ET.SubElement(rec, "Property", {"Name": "Name"}).text = name
        ET.SubElement(rec, "Property", {"Name": "FromStageID"}).text = from_pins[i][:4]
        ET.SubElement(rec, "Property", {"Name": "ToStageID"}).text = to_stages[i]
        ET.SubElement(rec, "Property", {"Name": "FromPinID"}).text = from_pins[i]
        ET.SubElement(rec, "Property", {"Name": "ToPinID"}).text = f"{to_stages[i]}P1"
        ET.SubElement(rec, "Property", {"Name": "ExecutionOrder"}).text = "0"
        ET.SubElement(rec, "Property", {"Name": "LinkColor"}).text = "0"


def agregar_links_explicitamente(job, data, nombre_a_id):
    """
    Genera registros de tipo 'Link' para visualización en DataStage Designer
    con los IDs correctos de stages y pins, y sin duplicados.
    """
    ya_creados = set()

    for out in data["output_pins"]:
        stage_id = nombre_a_id[out["stage"]]
        pin_id = f"{stage_id}P{out['pin_number']}"

        partner_stage_id, partner_pin_id = out["partner"].split("|")

        # ✅ Corrección aquí:
        link_id = f"{pin_id}_{partner_pin_id}"

        # Evita duplicados
        if link_id in ya_creados:
            continue
        ya_creados.add(link_id)

        rec = ET.SubElement(
            job, "Record", {"Identifier": link_id, "Type": "Link", "Readonly": "0"}
        )

        ET.SubElement(rec, "Property", {"Name": "Name"}).text = out["link_name"]
        ET.SubElement(rec, "Property", {"Name": "FromStageID"}).text = stage_id
        ET.SubElement(rec, "Property", {"Name": "ToStageID"}).text = partner_stage_id
        ET.SubElement(rec, "Property", {"Name": "FromPinID"}).text = pin_id
        ET.SubElement(rec, "Property", {"Name": "ToPinID"}).text = partner_pin_id
        ET.SubElement(rec, "Property", {"Name": "ExecutionOrder"}).text = "0"
        ET.SubElement(rec, "Property", {"Name": "LinkColor"}).text = "0"


def agregar_stages_reescrito(job, stages, input_pins, output_pins, nombre_a_id):
    for stage in stages:
        stage_id = nombre_a_id[stage["name"]]
        stage_type = stage["type"]

        if stage_type == "TransformerStage":
            record_type = "TransformerStage"
            stage_type_value = "CTransformerStage"
        elif stage_type == "PxDataSet":
            record_type = "CustomStage"
            stage_type_value = "PxDataSet"
        elif stage_type == "Join":
            record_type = "CustomStage"
            stage_type_value = "PxJoin"
        else:
            record_type = "CustomStage"
            stage_type_value = stage_type  # por si se agregan nuevos

        rec = ET.SubElement(
            job,
            "Record",
            {"Identifier": stage_id, "Type": record_type, "Readonly": "0"},
        )

        ET.SubElement(rec, "Property", {"Name": "Name"}).text = stage["name"]
        ET.SubElement(rec, "Property", {"Name": "StageType"}).text = stage_type_value
        # ET.SubElement(rec, "Property", {"Name": "AllowColumnMapping"}).text = "0"
        ET.SubElement(rec, "Property", {"Name": "NextID"}).text = "2"
        # ET.SubElement(rec, "Property", {"Name": "NextRecordID"}).text = "0"

        in_pins = [
            pin_id_input(stage_id, p["pin_number"])
            for p in input_pins
            if p["stage"] == stage["name"]
        ]
        if in_pins:
            ET.SubElement(rec, "Property", {"Name": "InputPins"}).text = "|".join(
                in_pins
            )

        out_pins = [
            pin_id_output(stage_id, p["pin_number"])
            for p in output_pins
            if p["stage"] == stage["name"]
        ]
        if out_pins:
            ET.SubElement(rec, "Property", {"Name": "OutputPins"}).text = "|".join(
                out_pins
            )

        # Propiedades específicas por tipo
        if stage_type == "Join":
            props = ET.SubElement(
                rec, "Collection", {"Name": "Properties", "Type": "CustomProperty"}
            )
            join_type = stage.get("properties", {}).get("JoinType", "inner").lower()
            join_key = stage.get("properties", {}).get("JoinKey", "")
            key_encoded = f"\\(2)\\(2)0\\(1)\\(3)key\\(2){join_key}\\(2)0"
            for name, value in [("operator", join_type + "join"), ("key", key_encoded)]:
                sub = ET.SubElement(props, "SubRecord")
                ET.SubElement(sub, "Property", {"Name": "Name"}).text = name
                ET.SubElement(sub, "Property", {"Name": "Value"}).text = value

        elif stage_type == "TransformerStage":
            ET.SubElement(rec, "Property", {"Name": "ValidationStatus"}).text = "0"
            ET.SubElement(rec, "Property", {"Name": "BlockSize"}).text = "0"
            ET.SubElement(rec, "Property", {"Name": "StageVarsMinimised"}).text = "0"
            ET.SubElement(rec, "Property", {"Name": "LoopVarsMaximised"}).text = "0"
            ET.SubElement(rec, "Property", {"Name": "MaxLoopIterations"}).text = "0"


def agregar_root_record(job, data, orchestrate_code):
    rec = ET.SubElement(
        job, "Record", {"Identifier": "ROOT", "Type": "JobDefn", "Readonly": "0"}
    )
    ET.SubElement(rec, "Property", {"Name": "Name"}).text = data["job_name"]
    ET.SubElement(rec, "Property", {"Name": "NextID"}).text = "1"
    ET.SubElement(rec, "Property", {"Name": "Container"}).text = "V0"
    ET.SubElement(rec, "Property", {"Name": "JobVersion"}).text = "56.0.0"
    ET.SubElement(rec, "Property", {"Name": "ControlAfterSubr"}).text = "0"

    # MetaBag con AdvancedRuntimeOptions
    metabag = ET.SubElement(
        rec, "Collection", {"Name": "MetaBag", "Type": "MetaProperty"}
    )
    sub = ET.SubElement(metabag, "SubRecord")
    ET.SubElement(sub, "Property", {"Name": "Owner"}).text = "APT"
    ET.SubElement(sub, "Property", {"Name": "Name"}).text = "AdvancedRuntimeOptions"
    ET.SubElement(sub, "Property", {"Name": "Value"}).text = "#DSProjectARTOptions#"

    ET.SubElement(rec, "Property", {"Name": "NULLIndicatorPosition"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "IsTemplate"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "JobType"}).text = "3"
    ET.SubElement(rec, "Property", {"Name": "Category"}).text = "\\Jobs\\UTILIDADES"
    ET.SubElement(rec, "Property", {"Name": "CenturyBreakYear"}).text = "30"
    ET.SubElement(rec, "Property", {"Name": "NextAliasID"}).text = "2"
    ET.SubElement(rec, "Property", {"Name": "ParameterFileDDName"}).text = "DD00001"
    ET.SubElement(rec, "Property", {"Name": "ReservedWordCheck"}).text = "1"
    ET.SubElement(rec, "Property", {"Name": "TransactionSize"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "ValidationStatus"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "Uploadable"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "PgmCustomizationFlag"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "JobReportFlag"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "AllowMultipleInvocations"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "Act2ActOverideDefaults"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "Act2ActEnableRowBuffer"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "Act2ActUseIPC"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "Act2ActBufferSize"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "Act2ActIPCTimeout"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "ExpressionSemanticCheckFlag"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "TraceOption"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "EnableCacheSharing"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "RuntimeColumnPropagation"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "RelStagesInJobStatus"}).text = "-1"
    ET.SubElement(rec, "Property", {"Name": "WebServiceEnabled"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "MFProcessMetaData"}).text = "0"
    ET.SubElement(
        rec, "Property", {"Name": "MFProcessMetaDataXMLFileExchangeMethod"}
    ).text = "0"
    ET.SubElement(rec, "Property", {"Name": "IMSProgType"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "CopyLibPrefix"}).text = "ARDT"
    ET.SubElement(rec, "Property", {"Name": "RecordPerformanceResults"}).text = "0"
    ET.SubElement(
        rec, "Property", {"Name": "OrchestrateCode", "PreFormatted": "1"}
    ).text = orchestrate_code


def agregar_container_view_completo_reescrito(job, data, nombre_a_id):
    rec = ET.SubElement(
        job, "Record", {"Identifier": "V0", "Type": "ContainerView", "Readonly": "0"}
    )

    ET.SubElement(rec, "Property", {"Name": "Name"}).text = "Job"
    ET.SubElement(rec, "Property", {"Name": "NextID"}).text = "1"
    ET.SubElement(rec, "Property", {"Name": "IsTopLevel"}).text = "0"

    # Etapas
    stage_ids = [nombre_a_id[stage["name"]] for stage in data["stages"]]
    stage_names = [stage["name"] for stage in data["stages"]]

    link_props = data.get("link_props", {})

    ET.SubElement(rec, "Property", {"Name": "StageList"}).text = "|".join(stage_ids)
    ET.SubElement(rec, "Property", {"Name": "StageXPos"}).text = "|".join(
        link_props.get("StageXPos", ["0"] * len(stage_ids))
    )
    ET.SubElement(rec, "Property", {"Name": "StageYPos"}).text = "|".join(
        link_props.get("StageYPos", ["0"] * len(stage_ids))
    )
    ET.SubElement(rec, "Property", {"Name": "StageXSize"}).text = "|".join(
        ["48"] * len(stage_ids)
    )
    ET.SubElement(rec, "Property", {"Name": "StageYSize"}).text = "|".join(
        ["48"] * len(stage_ids)
    )
    ET.SubElement(rec, "Property", {"Name": "StageNames"}).text = "|".join(stage_names)

    # Tipos de Stage para compatibilidad visual y lógica
    stage_types = []
    stage_type_ids = []
    for stage in data["stages"]:
        tipo = stage["type"]
        if tipo in ["Transformer", "TransformerStage"]:
            stage_types.append("CTransformerStage")
            stage_type_ids.append("CTransformerStage")
        elif tipo == "PxDataSet":
            stage_types.append("CCustomStage")
            stage_type_ids.append("PxDataSet")
        elif tipo in ["Join", "PxJoin"]:
            stage_types.append("CCustomStage")
            stage_type_ids.append("PxJoin")
        else:
            stage_types.append("CCustomStage")
            stage_type_ids.append(tipo)

    ET.SubElement(rec, "Property", {"Name": "StageTypes"}).text = "|".join(stage_types)
    ET.SubElement(rec, "Property", {"Name": "StageTypeIDs"}).text = "|".join(
        stage_type_ids
    )

    # Propiedades visuales de links
    campos_extra = [
        "LinkNames",
        "LinkTypes",
        "LinkSourcePinIDs",
        "TargetStageIDs",
        "LinkHasMetaDatas",
        "LinkNamePositionXs",
        "LinkNamePositionYs",
        "SourceStageEffectiveExecutionModes",
        "TargetStageEffectiveExecutionModes",
        "SourceStageRuntimeExecutionModes",
        "TargetStageRuntimeExecutionModes",
        "LinkIsSingleOperatorLookup",
        "LinkIsSortSequential",
        "LinkSortMode",
        "LinkPartColMode",
    ]

    for prop in campos_extra:
        ET.SubElement(rec, "Property", {"Name": prop}).text = link_props.get(prop, "")

    ET.SubElement(rec, "Property", {"Name": "NextStageID"}).text = str(
        len(stage_ids) + 1
    )
    ET.SubElement(rec, "Property", {"Name": "SnapToGrid"}).text = "1"
    ET.SubElement(rec, "Property", {"Name": "GridLines"}).text = "0"
    ET.SubElement(rec, "Property", {"Name": "ZoomValue"}).text = "100"
    ET.SubElement(rec, "Property", {"Name": "ContainerViewSizing"}).text = (
        "0078 0078 0536 0366 0000 0001 0000 0000"
    )


def interpretar_y_generar_xml(state: dict) -> dict:

    prompt = f"""
    Eres un experto en IBM DataStage Designer.
    
    Analiza esta solicitud:
    {state["natural_language_request"]}
    
    * Analiza esta solicitud y responde ÚNICAMENTE con un JSON válido. No incluyas explicaciones, comentarios ni etiquetas de código como ```json.
    * Esta estructura es obligatoria.
    * Incluye también la clave 'link_props' con todas las propiedades visuales necesarias para el ContainerView.
    * Asegúrate de incluir el atributo 'columns' con los metadatos (Name, SqlType, Precision y Derivation si aplica) para **todos los output_pins**, incluyendo los de DATASET_1 y DATASET_2.
    
    Responde con un JSON que siga esta estructura (tomarlo como referencia y construir los stages necesarios según corresponda):
    
    {{
      "job_name": "JOB_EJ_JOIN_TRANSFORM_CONFIG",
      "stages": [
        {{
          "name": "DATASET_1",
          "type": "PxDataSet"
        }},
        {{
          "name": "DATASET_2",
          "type": "PxDataSet"
        }},
        {{
          "name": "JOIN_1",
          "type": "PxJoin",
          "properties": {{
            "JoinType": "Inner",
            "JoinKey": "CAMPO1_LLAVE"
          }}
        }},
        {{
          "name": "TRANSFORM_1",
          "type": "TransformerStage",
          "properties": {{
            "StageType": "CTransformerStage"
          }}
        }},
        {{
          "name": "DS_SALIDA",
          "type": "PxDataSet"
        }}
      ],
      "output_pins": [
        {{
          "stage": "DATASET_1",
          "pin_number": 1,
          "link_name": "LINK_1",
          "partner": "V0S2|V0S2P2",
          "properties": [
            {{"Name": "dataset", "Value": "RUTA_DATASET_1.ds"}},
            {{"Name": "missingcolmode", "Value": "\\\\(20)"}}
          ],
          "left": 244,
          "top": 133,
          "columns": [
            {{
              "Name": "CAMPO1_LLAVE",
              "SqlType": 12,
              "Precision": 20
            }},
            {{
              "Name": "CAMPO2",
              "SqlType": 12,
              "Precision": 20
            }}
          ]
        }},
        {{
          "stage": "DATASET_2",
          "pin_number": 1,
          "link_name": "LNK_2",
          "partner": "V0S2|V0S2P1",
          "properties": [
            {{"Name": "dataset", "Value": "RUTA_DATASET_2.ds"}},
            {{"Name": "missingcolmode", "Value": "\\\\(20)"}}
          ],
          "left": 231,
          "top": 244,
          "columns": [
            {{
              "Name": "CAMPO1_LLAVE",
              "SqlType": 12,
              "Precision": 20
            }},
            {{
              "Name": "CAMPO_DS_2",
              "SqlType": 12,
              "Precision": 20
            }}
          ]
        }},
        {{
          "stage": "JOIN_1",
          "pin_number": 3,
          "link_name": "LNK_SALIDA_JOIN",
          "partner": "V0S3|V0S3P1",
          "properties": [],
          "left": 344,
          "top": 175,
          "columns": [
            {{
              "Name": "CAMPO1_LLAVE",
              "Derivation": "LINK_1.CAMPO1_LLAVE",
              "SqlType": 12,
              "Precision": 20
            }},
            {{
              "Name": "CAMPO2",
              "Derivation": "LINK_1.CAMPO2",
              "SqlType": 12,
              "Precision": 20
            }},
            {{
              "Name": "CAMPO_DS_2",
              "Derivation": "LNK_2.CAMPO_DS_2",
              "SqlType": 12,
              "Precision": 20
            }}
          ]
        }},
        {{
          "stage": "TRANSFORM_1",
          "pin_number": 1,
          "link_name": "LNK_SALIDA_TRANSFORM",
          "partner": "V0S4|V0S4P1",
          "type": "TrxOutput",
          "left": 444,
          "top": 170,
          "properties": [],
          "columns": [
            {{
              "Name": "CAMPO1_LLAVE",
              "Derivation": "LNK_SALIDA_JOIN.CAMPO1_LLAVE",
              "SqlType": 12,
              "Precision": 20
            }},
            {{
              "Name": "CAMPO2",
              "Derivation": "LNK_SALIDA_JOIN.CAMPO2",
              "SqlType": 12,
              "Precision": 20
            }},
            {{
              "Name": "CAMPO_DS_2",
              "Derivation": "LNK_SALIDA_JOIN.CAMPO_DS_2",
              "SqlType": 12,
              "Precision": 20
            }}
          ]
        }}
      ],
      "input_pins": [
        {{
          "stage": "JOIN_1",
          "pin_number": 2,
          "link_name": "LINK_1",
          "partner": "V0S0|V0S0P1"
        }},
        {{
          "stage": "JOIN_1",
          "pin_number": 1,
          "link_name": "LNK_2",
          "partner": "V0S1|V0S1P1"
        }},
        {{
          "stage": "TRANSFORM_1",
          "pin_number": 1,
          "link_name": "LNK_SALIDA_JOIN",
          "partner": "V0S2|V0S2P3",
          "type": "TrxInput",
          "metabag": [
            {{
              "Owner": "APT",
              "Name": "RTColumnProp",
              "Value": "0"
            }}
          ],
          "properties": [
            {{"Name": "MultiRow", "Value": "0"}},
            {{"Name": "LinkMinimised", "Value": "0"}}
          ]
        }},
        {{
          "stage": "DS_SALIDA",
          "pin_number": 1,
          "link_name": "LNK_SALIDA_TRANSFORM",
          "partner": "V0S3|V0S3P1"
        }}
      ],
      "links": [
        {{
          "name": "LINK_1",
          "from_stage": "V0S0",
          "to_stage": "V0S2",
          "from_pin": "V0S0P1",
          "to_pin": "V0S2P2"
        }},
        {{
          "name": "LNK_2",
          "from_stage": "V0S1",
          "to_stage": "V0S2",
          "from_pin": "V0S1P1",
          "to_pin": "V0S2P1"
        }},
        {{
          "name": "LNK_SALIDA_JOIN",
          "from_stage": "V0S2",
          "to_stage": "V0S3",
          "from_pin": "V0S2P3",
          "to_pin": "V0S3P1"
        }},
        {{
          "name": "LNK_SALIDA_TRANSFORM",
          "from_stage": "V0S3",
          "to_stage": "V0S4",
          "from_pin": "V0S3P1",
          "to_pin": "V0S4P1"
        }}
      ],
      "link_props": {{
        "StageXPos": ["120", "120", "288", "384", "480"],
        "StageYPos": ["96", "264", "168", "168", "168"],
        "LinkNames": "LINK_1|LNK_2|LNK_SALIDA_JOIN|LNK_SALIDA_TRANSFORM",
        "LinkTypes": "1|1|1|1",
        "LinkSourcePinIDs": "V0S0P1|V0S1P1|V0S2P3|V0S3P1",
        "TargetStageIDs": "V0S2|V0S2|V0S3|V0S4",
        "LinkHasMetaDatas": "True|True|True|True",
        "LinkNamePositionXs": "244|231|344|444",
        "LinkNamePositionYs": "133|244|175|170",
        "SourceStageEffectiveExecutionModes": "2|2|2|2",
        "TargetStageEffectiveExecutionModes": "2|2|2|2",
        "SourceStageRuntimeExecutionModes": "2|2|2|2",
        "TargetStageRuntimeExecutionModes": "2|2|2|2",
        "LinkIsSingleOperatorLookup": "False|False|False|False",
        "LinkIsSortSequential": "False|False|False|False",
        "LinkSortMode": "0|0|0|0",
        "LinkPartColMode": "1|1|1|1"
      }}
    }}
    """.strip()

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                data = json.loads(match.group())
            else:
                raise RuntimeError(f"JSON no encontrado en la respuesta:\n{raw}")
    except Exception as e:
        raise RuntimeError(f"JSON inválido:\n{raw}\n\nError: {e}")

    try:
        nombre_a_id = construir_mapeo_ids(data)
        orchestrate_code = construir_orchestrate_code(data["job_name"], data["stages"])

        root = crear_header(data["job_name"])
        job = ET.SubElement(
            root,
            "Job",
            {
                "Identifier": data["job_name"],
                "DateModified": datetime.now().strftime("%Y-%m-%d"),
                "TimeModified": datetime.now().strftime("%H.%M.%S"),
            },
        )

        agregar_root_record(job, data, orchestrate_code)
        agregar_container_view_completo_reescrito(job, data, nombre_a_id)
        agregar_stages_reescrito(
            job, data["stages"], data["input_pins"], data["output_pins"], nombre_a_id
        )
        agregar_output_pins_completo(job, data["output_pins"], nombre_a_id)
        agregar_input_pins_completo(job, data["input_pins"], nombre_a_id)
        # agregar_links_desde_definicion(job, data["link_props"])
        # agregar_links_explicitamente(job, data, nombre_a_id)

        indent_xml(root)
        xml_generado = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode(
            "utf-8"
        )

        return {
            "natural_language_request": state["natural_language_request"],
            "generated_xml": xml_generado,
        }

    except Exception as e:
        raise RuntimeError(f"Error generando XML final: {e}")


def actualizar_input_request_desde_archivos(ruta_prompts: str):
    """
    Lee los archivos desde la ruta especificada, busca los archivos que inician por 'TRF_',
    y construye un input_request con el contenido de esos archivos."""

    if not os.path.exists(ruta_prompts):
        raise FileNotFoundError(f"La ruta especificada no existe: {ruta_prompts}")

    archivos_trf = [
        archivo
        for archivo in os.listdir(ruta_prompts)
        if archivo.startswith("TRF_TRF_")
    ]

    if not archivos_trf:
        print(
            "No se encontraron archivos que inicien con 'TRF_TRF_' en la ruta especificada."
        )
        return

    for archivo in archivos_trf:
        ruta_archivo = os.path.join(ruta_prompts, archivo)
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            contenido = f.read()
            input_request = {"natural_language_request": contenido}

            try:
                # Ejecutar el grafo de LangGraph
                result = graph.invoke(input_request)

                # Validar la estructura esperada
                if "generated_xml" not in result:
                    raise RuntimeError(
                        "La estructura esperada para este job es DATASET -> TRANSFORMER -> DATASET."
                    )

                # Guardar el archivo XML generado
                guardar_xml(
                    result["generated_xml"],
                    nombre_archivo=f"{archivo.replace('.txt', '')}.xml",
                )

                print(
                    f"✅ Transformación creada exitosamente para el archivo: {archivo}"
                )
            except RuntimeError as e:
                print(f"⚠️ Error procesando el archivo {archivo}: {e}")
                continue


def guardar_xml(xml_content, ruta_directorio="./output", nombre_archivo=None):
    if not os.path.exists(ruta_directorio):
        os.makedirs(ruta_directorio)
    if nombre_archivo is None:
        fecha_hora = datetime.now().strftime("%Y%m%d_%H%M")
        nombre_archivo = f"JOB_TRF_AGENTE_{fecha_hora}.xml"
    ruta_completa = os.path.join(ruta_directorio, nombre_archivo)
    with open(ruta_completa, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"✅ Archivo guardado exitosamente en: {ruta_completa}")


def run(nombre_proceso_ppal: str):
    builder = StateGraph(AgentState)
    builder.add_node("interpretar_y_generar_xml", interpretar_y_generar_xml)
    builder.set_entry_point("interpretar_y_generar_xml")
    builder.add_edge("interpretar_y_generar_xml", END)
    graph = builder.compile()
    ruta = f"./prompts_datastage/{nombre_proceso_ppal}"
    archivo_prompt = os.path.join(ruta, f"TRF_{nombre_proceso_ppal}.txt")
    if not os.path.exists(archivo_prompt):
        print(f"No se encontró el archivo: {archivo_prompt}")
        return
    with open(archivo_prompt, "r", encoding="utf-8") as f:
        contenido_prompt = f.read()
    input_request = {"natural_language_request": contenido_prompt}
    try:
        result = graph.invoke(input_request)
        guardar_xml(result["generated_xml"])
        print(f"XML generado exitosamente para {nombre_proceso_ppal}")
    except Exception as e:
        print(f"Error al generar XML para {nombre_proceso_ppal}: {e}")

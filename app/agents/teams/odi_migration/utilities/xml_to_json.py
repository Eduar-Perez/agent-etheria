import os
import xml.etree.ElementTree as ET
import json


def parse_snp_sb(root):
    data = {}
    for obj in root.findall(".//Object"):
        cls = obj.get("class")
        if cls.endswith("SnpSb"):
            for field in obj.findall("Field"):
                name = field.get("name")
                value = field.text.strip() if field.text else None
                if name == "SbNo":
                    data["SB_NO"] = value
                elif name == "ScenName":
                    data["SCEN_NAME"] = value
                elif name == "IPackage":
                    data["I_PACKAGE"] = value
            break

    details = []
    current_step = None
    for obj in root.findall(".//Object"):
        cls = obj.get("class")
        if cls.endswith("SnpSbStep"):
            step = {}
            for field in obj.findall("Field"):
                name = field.get("name")
                if name == "Nno":
                    step["NNO"] = field.text.strip()
                elif name == "StepName":
                    step["STEP_NAME"] = field.text.strip()
            step["subdetails"] = []
            details.append(step)
            current_step = step
        elif cls.endswith("SnpSbTask") and current_step is not None:
            scen_task_no = task_name1 = col_lschema = col_txt = def_lschema = (
                def_txt
            ) = ord_trt = None
            for field in obj.findall("Field"):
                name = field.get("name")
                text = (
                    field.text.strip()
                    if field.text and field.text.strip().lower() != "null"
                    else None
                )
                if name == "ScenTaskNo":
                    scen_task_no = int(text) if text and text.isdigit() else None
                elif name == "TaskName1":
                    task_name1 = text
                elif name == "ColLschemaName":
                    col_lschema = text
                elif name == "ColTxt":
                    col_txt = text
                elif name == "DefLschemaName":
                    def_lschema = text
                elif name == "DefTxt":
                    def_txt = text
                elif name == "OrdTrt":
                    ord_trt = int(text) if text and text.isdigit() else None

            task = {
                "SCEN_TASK_NO": scen_task_no,
                "TASK_NAME1": task_name1,
                "COL_LSCHEMA_NAME": col_lschema,
                "COL_TXT": col_txt,
                "DEF_LSCHEMA_NAME": def_lschema,
                "DEF_TXT": def_txt,
                "ORD_TRT": ord_trt,
            }
            current_step["subdetails"].append(task)

    for step in details:
        step["subdetails"].sort(
            key=lambda x: (
                x["ORD_TRT"] if x["ORD_TRT"] is not None else float("inf"),
                x["SCEN_TASK_NO"] if x["SCEN_TASK_NO"] is not None else float("inf"),
            )
        )
    data["details"] = details
    return data, data["SCEN_NAME"]


def parse_snp_session(root):
    data = {}
    for obj in root.findall(".//Object"):
        cls = obj.get("class")
        if cls.endswith("SnpSession"):
            for field in obj.findall("Field"):
                name = field.get("name")
                value = field.text.strip() if field.text else None
                if name == "SbNo":
                    data["SB_NO"] = value
                elif name == "ScenName":
                    data["SCEN_NAME"] = value
                elif name == "SessNo":
                    data["SESS_NO"] = value
                elif name == "SessBeg":
                    data["SESS_BEG"] = value
            break
    return data, data.get("SCEN_NAME", "session_output")


def detect_and_parse(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    if root.find('.//Object[@class="com.sunopsis.dwg.dbobj.SnpSb"]') is not None:
        return parse_snp_sb(root)
    elif root.find('.//Object[@class="com.sunopsis.dwg.dbobj.SnpSession"]') is not None:
        return parse_snp_session(root)
    else:
        return {
            "message": "Unknown XML structure",
            "file": os.path.basename(xml_path),
        }, "unknown"


def replace_none_with_empty(obj):
    if isinstance(obj, dict):
        return {k: replace_none_with_empty(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_none_with_empty(item) for item in obj]
    elif obj is None:
        return ""
    else:
        return obj


def convert_all_xml_to_json(filen_name, xml_dir, output_dir):
    file_name = filen_name + ".xml"
    xml_path = os.path.join(xml_dir, file_name)

    if not os.path.exists(xml_path):
        raise FileNotFoundError(f"No se encontró el archivo: {xml_path}")

    os.makedirs(output_dir, exist_ok=True)
    print(f"Convirtiendo {xml_path} a JSON...")

    try:
        parsed_data, sn_name = detect_and_parse(xml_path)
        parsed_data = replace_none_with_empty(parsed_data)
        json_filename = os.path.splitext(sn_name)[0] + ".json"
        json_path = os.path.join(output_dir, json_filename)

        print(f"Escribiendo archivo JSON: {json_path}")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(parsed_data, jf, ensure_ascii=False, indent=4)
        return json_filename

    except Exception as e:
        print(f"Error al procesar el archivo: {e}")

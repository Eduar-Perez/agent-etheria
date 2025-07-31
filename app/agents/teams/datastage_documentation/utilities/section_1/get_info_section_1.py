import os
import re
import html
import json

PARAM_TYPE_MAP = {
    "0": "String",
    "1": "Integer",
    "2": "Float",
    "3": "Date",
    "4": "Time",
    "5": "Timestamp",
    "6": "Boolean",
    "13": "Parameter Set"
}

def get_param_type(name):
    if "VAP" in name:
        return "vap"
    elif "PSET" in name:
        return "pset"
    return "OTRO"

def extraer_parametros_secuencia_ppal(xml_path):
    with open(xml_path, "r", encoding="utf-8") as archivo:
        xml = html.unescape(archivo.read())

    # Buscar el bloque del job SEQ_PPAL
    bloque_seq_ppal = re.search(r'<Job Identifier="[^"]*SEQ_PPAL[^"]*".*?</Job>', xml, re.DOTALL)
    if not bloque_seq_ppal:
        print("No se encontró la secuencia principal con SEQ_PPAL.")
        return []

    bloque = bloque_seq_ppal.group(0)
    parametros = []

    # Buscar todos los <SubRecord> dentro del bloque de parámetros
    bloques_param = re.findall(r'<Collection Name="Parameters".*?>(.*?)</Collection>', bloque, re.DOTALL)
    for bloque_param in bloques_param:
        subrecords = re.findall(r'<SubRecord>(.*?)</SubRecord>', bloque_param, re.DOTALL)
        for param in subrecords:
            nombre = re.search(r'<Property Name="Name">(.*?)</Property>', param)
            tipo = re.search(r'<Property Name="ParamType">(.*?)</Property>', param)
            default = re.search(r'<Property Name="Default">(.*?)</Property>', param)
            prompt = re.search(r'<Property Name="Prompt">(.*?)</Property>', param)
            descripcion = ( ## no s eusa por ahora porque el elemento descripcion noestá bien definido en el json
                prompt.group(1).strip()
                if prompt else (
                    default.group(1).strip() if default else "Sin descripción"
                )
            )
            tipo = tipo.group(1).strip() if tipo else ""
            parametros.append({
                "nombre": nombre.group(1).strip() if nombre else "",
                "tipo": PARAM_TYPE_MAP.get(tipo, "OTRO"),
                "descripcion": "",
                "tipo_parametro": get_param_type(nombre.group(1).strip()) if nombre else "OTRO"
            })
    return json.dumps(parametros)

def get_complements_tales(json_path):
    json_path = os.path.join(json_path, "datastage_json.json")
    with open(json_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    agrupaciones = set()
    homologaciones = set()

    for job in jobs:
        for query in job.get("queries", []):
            query = query.replace("&apos;", "'")  # decodificar XML

            # AGRUPACIONES.STR_NOMBRE = 'valor'
            matches_agrup = re.findall(r'AGRUPACIONES\.STR_NOMBRE\s*=\s*[\'"]([^\'"]+)[\'"]', query, re.IGNORECASE)
            agrupaciones.update(matches_agrup)

            # STR_ID_TIPO_HOMOLOGACION = 'valor'
            matches_homo = re.findall(r'STR_ID_TIPO_HOMOLOGACION\s*=\s*[\'"]([^\'"]+)[\'"]', query, re.IGNORECASE)
            homologaciones.update(matches_homo)

    return {
        "tablas_agrupaciones": sorted(agrupaciones),
        "tipos_homologaciones": sorted(homologaciones)
    }

def get_info_section_1(xml_path, json_path):
    parameters = extraer_parametros_secuencia_ppal(xml_path)
    complementary_tables = get_complements_tales(json_path)
    return{"parameters":parameters, "tables":complementary_tables}
import os
import re
import html
import json

def extraer_atributos_de_columns(block):
    
    atributos = []
    columnas = re.findall(r'<SubRecord>(.*?)</SubRecord>', block, re.DOTALL)
    for columna in columnas:
        nombre = re.search(r'<Property Name="Name">(.*?)</Property>', columna)
        tipo = re.search(r'<Property Name="SqlType">(.*?)</Property>', columna)
        tamano = re.search(r'<Property Name="Precision">(.*?)</Property>', columna)
        obligatorio = re.search(r'<Property Name="Nullable">(.*?)</Property>', columna)
        clave = re.search(r'<Property Name="KeyPosition">(.*?)</Property>', columna)

        atributos.append({
            "nombre": nombre.group(1).strip() if nombre else "",
            "tipo_dato": tipo.group(1).strip() if tipo else "",
            "tamano": tamano.group(1).strip() if tamano else "",
            "obligatorio": "NO" if obligatorio and obligatorio.group(1).strip() == "0" else "SÍ",
            "clave": "SÍ" if clave and clave.group(1).strip() != "0" else "NO",
            "descripcion": ""
        })
    return atributos

def get_job_type(name):
    if "JOB_EXT" in name:
        return "extracción"
    elif "JOB_TRF" in name:
        return "transformación"
    elif "JOB_LOD" in name:
        return "cargue"
    elif "SEQ_PPAL" in name:
        return "principal"
    return "OTRO"

def extraer_jobs_con_queries(ruta_archivo,output_path):
    with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
        xml_content = archivo.read()

    xml_content = html.unescape(xml_content)
    job_blocks = re.findall(r"<Job Identifier=.*?</Job>", xml_content, re.DOTALL)
    jobs_info = []

    for block in job_blocks:
        job = {}

        job["nombre"] = re.search(r'<Property Name="Name">(.*?)</Property>', block).group(1).strip() if re.search(r'<Property Name="Name">(.*?)</Property>', block) else ""
        job["descripcion"] = re.search(r'<Property Name="Description">(.*?)</Property>', block).group(1).strip() if re.search(r'<Property Name="Description">(.*?)</Property>', block) else ""
        job["ruta"] = re.search(r'<Property Name="Category">(.*?)</Property>', block).group(1).strip() if re.search(r'<Property Name="Category">(.*?)</Property>', block) else ""
        full_desc_match = re.search(r'<Property Name="FullDescription".*?>(.*?)</Property>', block, re.DOTALL)
        job["full_description"] = full_desc_match.group(1).strip() if full_desc_match else ""

        query_matches = re.findall(r'<!\[CDATA\[\s*(?i:select)[\s\S]*?\]\]>', block, re.DOTALL)
        job["queries"] = [q.replace("<![CDATA[", "").replace("]]>", "").strip() for q in query_matches]

        # Extraer atributos
        columnas_block = re.search(r'<Collection Name="Columns" Type="OutputColumn">(.*?)</Collection>', block, re.DOTALL)
        job["atributos"] = extraer_atributos_de_columns(columnas_block.group(1)) if columnas_block else []
        job["tipo_proceso"] = get_job_type(job["nombre"])
        jobs_info.append(job)
    os.makedirs(output_path, exist_ok=True)
    output_path_write = os.path.join(output_path,"datastage_json.json")
    with open(output_path_write, "w", encoding="utf-8") as f:
        json.dump(jobs_info, f, ensure_ascii=False, indent=4)
    return
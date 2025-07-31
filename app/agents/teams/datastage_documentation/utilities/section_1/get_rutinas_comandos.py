import xml.etree.ElementTree as ET
import json
TYPE_DICY = {
    "0": "Indefinido",
    "1": "String",
    "2": "Integer",
    "3": "Float",
    "4": "Variable",
    "5": "Boolean",
    "6": "Path",
    "7": "Archivo"
}

def extraer_rutinas_comandos(ruta_xml):
    tree = ET.parse(ruta_xml)
    root = tree.getroot()
    rutinas = []
    for record in root.findall(".//Record[@Type='JSRoutineActivity']"):
        nombre_rutina = record.findtext("./Property[@Name='Name']", default="").strip()
        nombre_real = record.findtext("./Property[@Name='Routinename']", default="").strip()
        parametros = []
        for sub in record.findall(".//Collection[@Name='ParameterValues']/SubRecord"):
            nombre_param = sub.findtext("./Property[@Name='Name']", default="").strip()
            descripcion = sub.findtext("./Property[@Name='Description']", default="").strip()
            valor = sub.findtext("./Property[@Name='DisplayValue']", default="").strip()
            tipo = sub.findtext("./Property[@Name='ValueType']", default="").strip()
            tipo = TYPE_DICY.get(tipo, "Indefinido")
            parametros.append({
                "parametro": nombre_param,
                "descripcion": descripcion,
                "valor": valor,
                "tipo": tipo
            })
        rutinas.append({
            "rutina": nombre_rutina,
            "routinename": nombre_real,
            "parametros": parametros
        })

    comandos = []
    for record in root.findall(".//Record[@Type='JSExecCmdActivity']"):
        name = record.findtext("./Property[@Name='Name']", default="").strip()
        path = record.findtext("./Property[@Name='Path']", default="").strip()

        comandos.append({
            "nombre": name,
            "path": path
        })
    return rutinas ,comandos


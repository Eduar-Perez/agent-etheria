import os
import re
import json
import html
from docx import Document
from docx.oxml.ns import qn
from datetime import datetime
from docx.shared import Inches
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from .introduction_generator import intro_generator
from .section_1_text import intro_section_1
from .generate_description import descripcion_generador

SQL_TYPE_MAP = {
    "12": "VARCHAR",
    "4": "INTEGER",
    "2": "NUMERIC",
    "3": "DECIMAL",
    "91": "DATE",
    "93": "TIMESTAMP",
    "1": "CHAR",
    "9": "DATE",  # según cómo lo interpreta tu XML
    "1111": "OTHER"
}

def sombreado(hex_color):
    """Devuelve un sombreado de fondo azul (hex) para una celda de tabla."""
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    return shd

def agregar_portada(doc, titulo, subtitulo, autor, fecha):
    """
    Agrega una portada al documento con salto de página al final.
    """
    # Título principal centrado
    titulo_parrafo = doc.add_paragraph()
    titulo_parrafo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = titulo_parrafo.add_run(titulo)
    run.bold = True
    run.font.size = Pt(24)

    # Subtítulo
    doc.add_paragraph("")
    subtitulo_parrafo = doc.add_paragraph()
    subtitulo_parrafo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = subtitulo_parrafo.add_run(subtitulo)
    run.font.size = Pt(16)

    # Espaciado
    doc.add_paragraph("")
    doc.add_paragraph("")
    #Logo del banco
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER  # Centrar el párrafo

    # Insertar imagen en el párrafo
    run = paragraph.add_run()
    run.add_picture('./input_data/banco_logo_portada.png', width=Inches(2))
    # Autor
    autor_parrafo = doc.add_paragraph()
    autor_parrafo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = autor_parrafo.add_run(f"Autor: {autor}")
    run.font.size = Pt(12)
    
    doc.add_paragraph("")
    doc.add_paragraph("")
    # Fecha
    fecha_parrafo = doc.add_paragraph()
    fecha_parrafo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = fecha_parrafo.add_run(f"Fecha: {fecha}")
    run.font.size = Pt(12)
    # Salto de página
    doc.add_page_break()

def insertar_tabla_contenido(doc):
    # Agrega un título visible con estilo
    p = doc.add_paragraph("Tabla de Contenido")
    p.style = 'Heading 1'
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    # Campo TOC para que Word lo genere al actualizar
    paragraph = doc.add_paragraph()
    run = paragraph.add_run()

    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')

    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = 'TOC \\o "1-3" \\h \\z \\u'

    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'separate')

    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'end')

    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)

    # Salto de página
    doc.add_page_break()

def agregar_encabezado_personalizado(doc, logo_izq_path, logo_der_path,titulo_encabezado):
    """
    Inserta un encabezado con logos y texto alineado al centro
    """
    section = doc.sections[0]
    section.different_first_page_header_footer = True  

    header = section.header

    # Crear una tabla de 3 columnas
    table = header.add_table(rows=1, cols=3, width=Inches(6.5))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    # Columna 1: logo izquierdo
    cell1 = table.cell(0, 0)
    paragraph1 = cell1.paragraphs[0]
    run1 = paragraph1.add_run()
    run1.add_picture(logo_izq_path, width=Inches(1))
    paragraph1.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT

    # Columna 2: texto central
    cell2 = table.cell(0, 1)
    paragraph2 = cell2.paragraphs[0]
    paragraph2.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    fecha_actual = datetime.now().strftime("%Y-%m-%d")

    paragraph2.add_run("USO INTERNO\n").bold = True
    paragraph2.add_run(f"Diseño Proceso ETL\t\t{fecha_actual}\n")
    paragraph2.add_run(titulo_encabezado)

    # Columna 3: logo derecho
    cell3 = table.cell(0, 2)
    paragraph3 = cell3.paragraphs[0]
    run3 = paragraph3.add_run()
    run3.add_picture(logo_der_path, width=Inches(0.5))
    paragraph3.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT

def agregar_control_versiones(doc):
    # Título: Control de versiones
    p = doc.add_paragraph("Control de Versiones:")
    p.runs[0].bold = True

    # Tabla 1: Control de versiones
    table1 = doc.add_table(rows=2, cols=4)
    table1.style = 'Table Grid'
    table1.autofit = True

    encabezados1 = ["Versión", "Fecha", "Adiciones / Modificaciones", "Preparado por"]
    valores1 = ["", "", "", ""]

    for i, texto in enumerate(encabezados1):
        cell = table1.rows[0].cells[i]
        run = cell.paragraphs[0].add_run(texto)
        run.bold = True
        cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        tcPr = cell._element.get_or_add_tcPr()
        shading = OxmlElement('w:shd')
        shading.set(qn('w:val'), 'clear')
        shading.set(qn('w:color'), 'auto')
        shading.set(qn('w:fill'), '4472C4')  # Color azul
        tcPr.append(shading)

    for i, texto in enumerate(valores1):
        table1.rows[1].cells[i].text = texto

    doc.add_paragraph("")  # Espacio entre tablas

    # Título: Aprobado por
    p = doc.add_paragraph("Aprobado Por:")
    p.runs[0].bold = True

    # Tabla 2: Aprobado por
    table2 = doc.add_table(rows=2, cols=3)
    table2.style = 'Table Grid'
    encabezados2 = ["Nombre y Apellido", "Cargo y Área", "Fecha de Aprobación"]
    valores2 = ["", "", ""]

    for i, texto in enumerate(encabezados2):
        cell = table2.rows[0].cells[i]
        run = cell.paragraphs[0].add_run(texto)
        run.bold = True
        cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        tcPr = cell._element.get_or_add_tcPr()
        shading = OxmlElement('w:shd')
        shading.set(qn('w:val'), 'clear')
        shading.set(qn('w:color'), 'auto')
        shading.set(qn('w:fill'), '4472C4')  # Color azul
        tcPr.append(shading)

    for i, texto in enumerate(valores2):
        table2.rows[1].cells[i].text = texto
    doc.add_page_break()  # Salto de página al final

def agregar_introduccion(doc, texto):
    # Título de la sección
    titulo = doc.add_paragraph("Introducción")
    titulo.style = 'Heading 1'
    titulo.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    # Párrafo del contenido
    parrafo = doc.add_paragraph(texto)
    parrafo.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    doc.add_page_break()

def agregar_tabla_seccion_1(doc, jobs_data):
        # Agrupar jobs
    agrupados = {
        "PPAL": [],
        "EXT": [],
        "TRF": [],
        "LOD": [],
        "OTRO": []
    }

    for job in jobs_data:
        tipo = job.get("tipo_proceso", "")
        nombre = job.get("nombre", "")
        if tipo == "principal":
            agrupados["PPAL"].append(nombre)
        elif tipo == "extracción":
            agrupados["EXT"].append(nombre)
        elif tipo == "transformación":
            agrupados["TRF"].append(nombre)
        elif tipo == "cargue":
            agrupados["LOD"].append(nombre)
        else:
            agrupados["OTRO"].append(nombre)

    # Calcular total de filas
    total_filas = 1 + sum(len(jobs) for jobs in agrupados.values())

    table = doc.add_table(rows=total_filas, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    table.style = 'Table Grid'
    

    # Título en la segunda celda de la primera fila
    cell_merged = table.cell(0, 0).merge(table.cell(0, 1))
    cell_merged.text = "Jobs del proceso ETL "
    
    p = cell_merged.paragraphs[0]
    p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    p.color = RGBColor(255, 255, 255)
    run = p.runs[0]
    run.bold = True
    run.font.color.rgb = RGBColor(255, 255, 255)  # Blanco
    
    cell_merged._element.get_or_add_tcPr().append(sombreado('4472C4'))
    # Agregar los grupos
    fila = 1
    for etiqueta, jobs in agrupados.items():
        if not jobs:
            continue
        # Combinar celdas verticales de la izquierda
        cell_inicio = table.cell(fila, 0)
        cell_inicio.text = etiqueta
        for i, job_name in enumerate(jobs):
            table.cell(fila + i, 1).text = job_name
            if i > 0:
                table.cell(fila + i, 0).merge(cell_inicio)
        fila += len(jobs)

def agregar_tabla_ficha_jobs_section_2(doc, job_name, db, esquema, tipo, descripcion, atributos, query_sql=""):
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    table.autofit = True


    # Fila título azul
    cell = table.rows[0].cells[0]
    cell.text = f"JOB {job_name}"
    for i in range(1, 5):
        cell.merge(table.rows[0].cells[i])
    run = cell.paragraphs[0].runs[0]
    run.bold = True
    run.font.color.rgb = RGBColor(255, 255, 255)
    cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), '0070C0')
    cell._element.get_or_add_tcPr().append(shading)

    # Fila datos generales
    row = table.add_row().cells
    row[0].text = "Base de datos:"
    row[1].text = db
    row[2].text = "Esquema:"
    row[3].text = esquema
    row[4].text = f"Tipo: {tipo}"

    # Fila descripción
    row = table.add_row().cells
    row[0].text = "Descripción:"
    for i in range(1, 5):
        row[0].merge(row[i])
    row[0].paragraphs[0].add_run(f"\n{descripcion}")

    # Encabezado columnas
    encabezados = ["Atributos", "Tipo de Dato", "Obligatorio", "Clave", "Descripción"]
    row = table.add_row().cells
    for i, titulo in enumerate(encabezados):
        run = row[i].paragraphs[0].add_run(titulo)
        run.bold = True

    # Filas de atributos
    for campo in atributos:
        tipo_crudo = campo.get("tipo_dato", "")
        tamano = campo.get("tamano", "")
        tipo_dato = SQL_TYPE_MAP.get(tipo_crudo, tipo_crudo)
        if tamano:
            tipo_dato += f"({tamano})"
        row = table.add_row().cells
        row[0].text = campo.get("nombre", "")
        row[1].text = tipo_dato
        row[2].text = campo.get("obligatorio", "")
        row[3].text = campo.get("clave", "")
        row[4].text = campo.get("descripcion", "")
    if query_sql:
        row = table.add_row().cells
        row[0].text = "SQL Asociado:"
        for i in range(1, 5):
            row[0].merge(row[i])
        p = row[0].paragraphs[0]
        p.add_run("\n" + query_sql.strip()).italic = True

    doc.add_paragraph("")

def agregar_tabla_parametros(doc, parametros, type_param):
    # Título
    titulo_text = "VAP" if type_param == "vap" else "PSET"
    titulo = doc.add_paragraph(titulo_text+": ")
    titulo.runs[0].bold = True

    # Crear tabla con encabezado
    table = doc.add_table(rows=1, cols=3)
    table.autofit = True

    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    encabezados = ["Nombre del parámetro", "Tipo de dato", "Descripción"]
    header_row = table.rows[0].cells

    for i, texto in enumerate(encabezados):
        cell = header_row[i]
        cell.text = texto
        run = cell.paragraphs[0].runs[0]
        run.bold = True
        cell.paragraphs[0].alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
        cell._element.get_or_add_tcPr().append(sombreado("4472C4"))  # Azul

    # Agregar filas de parámetros
    for param in parametros:
        if isinstance(param, dict) and param.get("tipo_parametro", "").lower() == type_param.lower():
            row = table.add_row().cells
            row[0].text = param.get("nombre", "")
            row[1].text = param.get("tipo", "")
            row[2].text = param.get("descripcion", "")
    doc.add_paragraph("")  # Espacio entre tablas

def agregar_lista_secuencias_ext(doc, jobs_data, tipo_sec):
    # Filtrar nombres que empiezan por SEQ_E
    secuencias_ext = [
        item["nombre"] for item in jobs_data
        if item.get("nombre", "").startswith(tipo_sec)
    ]

    if secuencias_ext:
        for nombre in secuencias_ext:
            doc.add_paragraph(nombre, style="List Bullet")
    else:
        doc.add_paragraph("")

def agregar_tabla_rutinas(doc, json_data):
    for rutina in json_data:
        
        num_parametros = len(rutina.get("parametros", []))
        total_rows = 3 + num_parametros  # Rutina + Mapeo + encabezado + parámetros

        table = doc.add_table(rows=total_rows, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        table.style = 'Table Grid'

        # Fila 1: Rutina
        table.cell(0, 0).text = "Rutina"
        table.cell(0, 0)._element.get_or_add_tcPr().append(sombreado("4472C4")) 
        
        merged_row = table.cell(0, 1).merge(table.cell(0, 2))
        merged_row.text = rutina.get("rutina", "")
        merged_row._element.get_or_add_tcPr().append(sombreado("4472C4"))

        # Fila 2: Mapeo del parámetro
        table.cell(1, 0).text = "Mapeo del parametro"
        merged_row = table.cell(1, 1).merge(table.cell(1, 2))
        merged_row.text = rutina.get("routinename", "")
        
        # Fila 3: Encabezados
        table.cell(2, 0).text = "Parametros"
        table.cell(2, 1).text = "tipo"
        table.cell(2, 2).text = "valor"

        # Filas siguientes: parámetros
        for i, param in enumerate(rutina.get("parametros", [])):
            row = table.rows[3 + i]
            row.cells[0].text = param.get("parametro", "")
            row.cells[1].text = param.get("tipo", "")
            row.cells[2].text = param.get("valor", "")

        doc.add_paragraph("") 

def agregar_tabla_comandos(doc, comandos):
    num_comandos = len(comandos)

    table = doc.add_table(rows=num_comandos+1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    table.style = 'Table Grid'

    table.cell(0, 0).text = "Nombre"
    table.cell(0, 0)._element.get_or_add_tcPr().append(sombreado("4472C4")) 
    table.cell(0, 1).text = "Path"
    table.cell(0, 1)._element.get_or_add_tcPr().append(sombreado("4472C4")) 
    
    for i, comando in enumerate(comandos):
        table.cell(i+1,0).text = comando["nombre"]
        table.cell(i+1,1).text = comando["path"]
    doc.add_paragraph("") 

def document_generator(json_path, output_docx, parameters_ppal, rutinas,comandos):
    with open(json_path, "r", encoding="utf-8") as f:
        jobs_data = json.load(f)
    #Rerte de json para generar introducción
    jobs_descriptions = []
    for job in jobs_data:
        jobs_descriptions.append({
            "nombre": job.get("nombre", ""),
            "descripcion": job.get("descripcion", ""),
            "full_description": job.get("full_description", "")
        })
    
    jobs_queryes = []
    for job in jobs_data:
        jobs_queryes.append({
            "nombre": job.get("nombre", ""),
            "descripcion": job.get("descripcion", ""),
            "full_description": job.get("full_description", ""),
            "query_sql": job.get("queries", "")
        })
        
    # Crear documento
    doc = Document()
    
    #Generar texto de introduccion
    # intro_text = intro_generator(jobs_descriptions)
    intro_text = '''El presente documento técnico detalla el diseño de procesos ETL implementados en IBM DataStage v11.7 para la gestión de transacciones financieras y operaciones de compensación electrónica. El conjunto de jobs documentados está enfocado principalmente en la extracción de información desde sistemas como FLEXCUBE, ODS y archivos externos, su transformación mediante reglas de negocio específicas, y la carga de datos procesados tanto en sistemas de archivos como en bases de datos destino.

La estructura de los procesos ETL se organiza en tres tipos principales de jobs: extracción (identificados con el prefijo "JOB_EXT3"), transformación (con prefijo "JOB_TRF") y carga (con prefijo "JOB_LOD"). Adicionalmente, se han implementado jobs auxiliares para la gestión de variables de control y limpieza de datasets temporales, como el "JOB_BORRA_DS_ICBS" y "JOB_VARIABLES_TBL_CTL_CARGUE_ICBS".

Los procesos extraen información desde diversas fuentes, destacando tablas como ACVW_ALL_AC_ENTRIES, GWTB_MSG_IN_LOG, archivos de conciliación provenientes de ATH ("BTXAVAL_BOCC_Conciliacion_AAAAMMDD_HHMM.txt") y datos de los sistemas FLEXCUBE y ODS. Los destinos principales incluyen datasets temporales (DS_ACVW_ALL_AC_ENTRIES.ds, DS_COMPENSACION_ELECTRONICA_3P.ds) y archivos de salida con formato específico para la compensación electrónica y transferencias ICBS.

El flujo de procesamiento incluye secuencias (SEQ_LOD_EXCEL_TRASN_ICBS, SEQ_LOD_SF_TRASN_ICBS, SEQ_PPAL_TRANSFERENCIAS_ICBS) que orquestan la ejecución de los jobs principales, utilizando parámetros como "VAP_RUTA_ETL" para definir rutas de procesamiento. Particularmente, el proceso de compensación electrónica implementado por SOPHOS SOLUTIONS entre 2020 y 2021 (requerimientos como SBBO0303) contempla la extracción, transformación y generación de archivos para transacciones y conciliación entre sistemas.
'''
    
    #Flujo Seccion 2
    
    # Portada
    titulo_portada = [item["nombre"] for item in jobs_data if item.get("nombre", "").startswith("SEQ_PPAL_")][0][9:]
    titulo_portada = titulo_portada.replace("_", " ")
    agregar_portada(
        doc,
        titulo="Documento técnico",
        subtitulo= titulo_portada,
        autor="Equipo de Ingeniería de Datos",
        fecha=datetime.now().strftime("%Y-%m-%d")
    )

    # Encabezado con logos
    agregar_encabezado_personalizado(
        doc,
        logo_izq_path="./input_data/periferia_logo.png",
        logo_der_path="./input_data/banco_logo.png",
        titulo_encabezado= titulo_portada
    )
    
    # Tabla de contenido
    insertar_tabla_contenido(doc)
    
    # Control de versiones
    agregar_control_versiones(doc)
    
    agregar_introduccion(doc, intro_text)

    # Agrupar los jobs por tipo
    tipos = {
        "extracción": lambda nombre: nombre.startswith("JOB_EXT"),
        "transformación": lambda nombre: nombre.startswith("JOB_TRF"),
        "cargue": lambda nombre: nombre.startswith("JOB_LOD"),
    }

    tipo_secciones = {
        "extracción": "2.1",
        "transformación": "2.2",
        "cargue": "2.3",
    }
#============construccion de seccion 1 parametros de ppal============
    doc.add_heading("1. Diseño técnico de la solución", level=1)
    # aqui esta el texto de introudccion a la seccion
    # text_section_1 = intro_section_1(jobs_descriptions)
    text_section_1 = "La solución ETL implementada en IBM DataStage está diseñada para soportar el proceso de compensación electrónica y gestión de transferencias bancarias. El sistema se encarga de extraer información de diversas fuentes como tablas de FLEXCUBE (ACVW_ALL_AC_ENTRIES), archivos enviados por ATH y otros sistemas operativos, procesarla mediante transformaciones intermedias y finalmente cargar los resultados en archivos estructurados para su posterior uso. El flujo automatizado incluye tareas de mantenimiento como la limpieza de datasets temporales, el cargue de variables de control, y la generación de archivos de salida en formatos específicos para las transferencias ICBS. La arquitectura permite la interacción entre diferentes sistemas bancarios, facilitando la conciliación de transacciones y el procesamiento de operaciones masivas, todo ello orquestado mediante una secuencia controlada de jobs que garantiza la integridad y consistencia de los datos a lo largo del proceso."
    parrafo = doc.add_paragraph(text_section_1)
    parrafo.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    doc.add_heading("1.1 Diagrama de flujo de información", level=2)
    # doc.add_picture("./input_data/etl_diagram.png", width=Inches(2))
    doc.add_heading("1.2 Diagrama de procesos de la solución", level=2)
    agregar_tabla_seccion_1(doc, jobs_data)
    doc.add_heading("1.3 Parámetros de la secuencia principal", level=2)
    parrafo = doc.add_paragraph("En esta sección se describen los parámetros de entrada de la solución")
    parrafo.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    parametros = json.loads(parameters_ppal["parameters"])
    agregar_tabla_parametros(doc, parametros, "vap")
    agregar_tabla_parametros(doc, parametros, "pset")
    doc.add_heading("1.4 Información general", level=2)
    doc.add_paragraph(
        "Esta sección contiene información general sobre los procesos de ETL implementados en IBM DataStage 11.7."
    )
    doc.add_heading("Secuencia principal: ", level=3)
    ruta_seq_ppal = next((item for item in jobs_data if item.get("nombre", "").startswith("SEQ_PPAL")), None)
    ruta_seq_ppal = ruta_seq_ppal.get("ruta", "No disponible") if ruta_seq_ppal else "No disponible"
    doc.add_paragraph(f"{ruta_seq_ppal}")
    
    doc.add_heading("Tablas de homologación ", level=4)
    homologacion_table = parameters_ppal["tables"]["tipos_homologaciones"]
    if len(homologacion_table) >0:
        doc.add_paragraph(f"{homologacion_table[0]}", style="List Bullet")

    doc.add_heading("Tablas de agrupación ", level=4)
    agrupacion_table = parameters_ppal["tables"]["tablas_agrupaciones"]
    if len(agrupacion_table) > 0:
        doc.add_paragraph(f"{agrupacion_table[0]}", style="List Bullet")
        
    doc.add_heading("Rutinas: ", level=3)
    agregar_tabla_rutinas(doc, rutinas)
    
    doc.add_heading("Comandos: ", level=3)
    agregar_tabla_comandos(doc, comandos)
    
    secuencias = [
        item["nombre"] for item in jobs_data
        if item.get("nombre", "").startswith("SEQ_E")
    ]
    if len(secuencias) > 0:
        doc.add_heading("Secuencia de extracción:  ", level=3)
        agregar_lista_secuencias_ext(doc, jobs_data, "SEQ_E")
    
    secuencias = [
        item["nombre"] for item in jobs_data
        if item.get("nombre", "").startswith("SEQ_T")
    ]
    if len(secuencias) > 0:
        doc.add_heading("Secuencia de transformación:  ", level=3)
        agregar_lista_secuencias_ext(doc, jobs_data, "SEQ_T")
    
    secuencias = [
    item["nombre"] for item in jobs_data
    if item.get("nombre", "").startswith("SEQ_L")
    ]
    if len(secuencias) > 0:
        doc.add_heading("Secuencia de carga:  ", level=3)
        agregar_lista_secuencias_ext(doc, jobs_data, "SEQ_L")
    
    doc.add_heading("Nombre archivo entrada: ", level=3)
    doc.add_heading("Nombre archivo salida: ", level=3)
#======================= end Section 1 =======================
    
#======================= Sección 2: Procesos de integración ETL =======================
    doc.add_heading("2. Especificación de los procesos de integración ETL", level=1)
    # doc.add_picture("./input_data/etl_diagram.png", width=Inches(2))

    filtered_data = [
        {
            "nombre": item["nombre"],
            "descripcion": item.get("descripcion") or item.get("full_description", "") or ""
        }
        for item in jobs_data
        if (item.get("descripcion")  or item.get("full_description", "") or "").strip() != ""
    ]
    descripcion_text_corrected = descripcion_generador(filtered_data)
    descripcion_text_corrected_dict = {
                item["nombre"]: item for item in descripcion_text_corrected
            }
    for tipo, filtro in tipos.items():
        jobs_filtrados = [j for j in jobs_data if filtro(j.get("nombre", ""))]
        if not jobs_filtrados:
            continue
        seccion = tipo_secciones[tipo]
        # Agregar título por tipo
        doc.add_heading(f"{seccion} Procesos de {tipo.capitalize()}", level=2)
        doc.add_heading(f"{seccion}.1 ESPECIFICACIÓN PROCESO DE {tipo.upper()}", level=3)
        doc.add_paragraph(f"Resumen general de los procesos de {tipo.lower()}.", style="Normal")
        doc.add_heading(f"{seccion}.1.1 Jobs de {tipo.capitalize()}", level=4)
        # Listar jobs
        for job in jobs_filtrados:
            doc.add_paragraph(job["nombre"], style="List Bullet")
        # Agregar fichas        
        for i, job in enumerate(jobs_filtrados, start=1):
            nombre = job.get("nombre", "")
            esquema = "ADMODS" if "ADMODS" in nombre else "ODS"
            tipo_bd = "ORACLE"
            descripcion_no_clean = job.get("descripcion") or job.get("full_description") or ""
            desrcipcion_clean = descripcion_text_corrected_dict[nombre]["descripcion_optimizada"] if nombre in descripcion_text_corrected_dict else ""
            descripcion = desrcipcion_clean if desrcipcion_clean else descripcion_no_clean
            query_sql = job["queries"][0] if job.get("queries") else ""
            db = re.search(r'(from|join)\s+([a-zA-Z0-9_]+)\.', query_sql, re.IGNORECASE)
            db =db.group(2) if db else ""
            # Simulación de atributos si no hay
            atributos = job.get("atributos") or [{
                "nombre": "COLUMNA_1",
                "tipo_dato": "VARCHAR(100)",
                "obligatorio": "NO",
                "clave": "NO",
                "descripcion": "Descripción del campo"
            }]
            # Ficha técnica
            agregar_tabla_ficha_jobs_section_2(
                doc,
                job_name=nombre.replace("JOB_", ""),
                db= db if db else "No disponible",
                esquema=esquema,
                tipo=tipo_bd,
                descripcion=descripcion,
                atributos=atributos,
                query_sql=query_sql
            )
    os.makedirs(output_docx, exist_ok=True)
    output_docx_path = os.path.join(output_docx,f"{titulo_portada}.docx")
    doc.save(output_docx_path)
    print(f"✅ Documento generado: {output_docx_path}")
    return output_docx_path


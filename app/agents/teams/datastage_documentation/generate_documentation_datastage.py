from ..utilities.save_and_generate_url import save_and_generate_url_s3
from .utilities.section_2 import extraer_jobs_con_queries
from .utilities import document_generator
from .utilities.section_1 import get_info_section_1, extraer_rutinas_comandos
import os


def generate_document_datastage(intpu_tmp_folder):
    xmls_files = os.listdir(intpu_tmp_folder)
    for xmls_file in xmls_files:
        xml_path = os.path.join(intpu_tmp_folder, xmls_file)
        output_docx_path = os.path.join(intpu_tmp_folder,"..","output_documents", "datastage")
        json_output = os.path.join(intpu_tmp_folder,".." "output_data", "datastage")
        extraer_jobs_con_queries(xml_path, json_output)
        section_1 = get_info_section_1(xml_path,json_output)
        rutinas,comandos = extraer_rutinas_comandos(xml_path)
        path_docx = document_generator(json_output, output_docx_path,section_1,rutinas,comandos)
        s3_key = f"sql-joiner/{os.path.basename(path_docx)}" 
        url_download = save_and_generate_url_s3(s3_key, s3_key)
    response = f'''##Generación de Documento Exitosa

El documento ha sido generado exitosamente.
Todos los datos han sido procesados correctamente y el archivo está listo para su uso.
Puedes descargar el archivo desde este link:
[Descargar archivo]({url_download})'''
    return response
        



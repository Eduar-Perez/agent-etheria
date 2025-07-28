import json
from agno.workflow.workflow import Workflow
from pydantic import BaseModel, Field
from agno.agent.agent import Agent
from agno.run.response import RunResponse
from agno.utils.log import logger
from typing import List
import pandas as pd
import re
from typing import List, Tuple
from agno.models.aws import Claude
import os


MODEL = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"

class DummyJson(BaseModel):
    mapping_file_name: str = Field(description="nombre del archivo de mapeo")
    file_name: str = Field(description="nombre del archivo migrado")
    file_name_source: str = Field(description="nombre del archivo original")
    migrate_module: str = Field(description="nombre del archivo original")

class DummyJsonWorkflow(Workflow):
    screening_agent: Agent = Agent(
        description="Eres un experto en el Bus de Oracle, y vas a actuar como validador del codigo migrado.",
        model=Claude(id=MODEL),
        instructions=[
            "Eres un experto en procesos de migracion de flujos del Bus de oracle, para cambiar flujos en XML a JSON en archivos ESQL.",
            "vas a identificar los archivos de entrada de tipo ESQL",
            "Luego vas a identificar el archivo de mapeo",
            "Con el archivo de mapeo vas a identificar el nommbre de los modulos a migrar",
            "finalmente vas a generar la modificacion del archivo ESQL tanto en el request como en el response",
            "por ultimo se va a generar el archivo de salida en formato esql, con el mismo nombre que el archivo de entrada pero terminado en _salida.esql",
        ],
        user_message="Dime las funcionalidades de este agente",
        response_model=DummyJson,
    )
    
    def read_excel_mapping(self, file_path: str):
        df = pd.read_excel(file_path, header=None)

        request_module_name = df.iloc[0, 0]
        request_mapping = []

        idx = 1
        while idx < len(df):
            original = df.iloc[idx, 0]
            new = df.iloc[idx, 1] if df.shape[1] > 1 else None
            if pd.isna(original):
                idx += 1
                break
            if pd.notna(new):
                request_mapping.append((original.strip(), new.strip()))
            idx += 1

        # Buscar el siguiente módulo (Response)
        while idx < len(df) and pd.isna(df.iloc[idx, 0]):
            idx += 1

        if idx < len(df):
            response_module_name = df.iloc[idx, 0]
            response_mapping = []
            idx += 1
            while idx < len(df):
                original = df.iloc[idx, 0]
                new = df.iloc[idx, 1] if df.shape[1] > 1 else None
                if pd.isna(original):
                    break
                if pd.notna(new):
                    response_mapping.append((original.strip(), new.strip()))
                idx += 1
        else:
            response_module_name = None
            response_mapping = []

        return request_module_name.strip(), request_mapping, response_module_name.strip(), response_mapping
    # --------------------------
    # EXTRACCIÓN DEL BLOQUE MODULE
    # --------------------------

    def extract_compute_module(self, esql_code: str, module_name: str):
        pattern = re.compile(
            rf"(CREATE COMPUTE MODULE {re.escape(module_name)}.*?END MODULE;)",
            re.DOTALL
        )
        match = pattern.search(esql_code)
        if not match:
            raise ValueError(f"No se encontró el Compute Module: {module_name}")
        return match.group(1)


    # --------------------------
    # CONVERSIÓN JSON HEADER
    # --------------------------

    def convert_module_to_json(self, module_code: str, is_response=False) -> str:
        updated_lines = []
        for line in module_code.splitlines():
            if is_response:
                # Solo mensajeRespIn se convierte a JSON
                if 'REFERENCE TO InputRoot.XMLNSC' in line and 'mensajeRespIn' in line:
                    line = line.replace('REFERENCE TO InputRoot.XMLNSC', 'REFERENCE TO InputRoot.JSON')
            else:
                # Para Request: OutputRoot + DECLARE completo se convierte
                if 'OutputRoot.XMLNSC' in line:
                    line = line.replace('OutputRoot.XMLNSC', 'OutputRoot.JSON')
                if 'REFERENCE TO OutputRoot.XMLNSC' in line:
                    line = line.replace('REFERENCE TO OutputRoot.XMLNSC', 'REFERENCE TO OutputRoot.JSON')
            updated_lines.append(line)
        return '\n'.join(updated_lines)


    # --------------------------
    # FUNCIONES AUXILIARES
    # --------------------------

    def extract_right_match_key(self, column_b: str) -> str:
        """
        De columna B tipo 'fmgres:RespuestaFMG.fmgres:Cabecera.enc:PtcionId'
        devuelve 'fmgres:Cabecera.enc:PtcionId'
        """
        if '.' in column_b:
            return column_b.split('.', 1)[-1].strip()
        return column_b.strip()

    def extract_final_field_name(self, column_a: str) -> str:
        """
        De columna A tipo 'InputRoot.JSON.Data.SecuenciaIdentificadorMigrado'
        devuelve 'SecuenciaIdentificadorMigrado'
        """
        return column_a.strip().split('.')[-1]


    # --------------------------
    # PROCESADO: RESPONSE
    # --------------------------

    def process_response_module(self, module_code: str, mapping: List[Tuple[str, str]]) -> str:
        lines = module_code.splitlines()
        new_lines = []

        # Crear el diccionario de mapeo
        mapping_dict = {}
        for col_a, col_b in mapping:
            key_to_find = self.extract_right_match_key(col_b)
            new_field_name = self.extract_final_field_name(col_a)
            mapping_dict[key_to_find] = new_field_name

        for line in lines:
            if 'SET' in line and 'mensajeRespIn' in line:
                indent = line[:line.find(line.lstrip())]
                updated_line = line
                matched_any = False

                for key_to_find, final_field in mapping_dict.items():
                    if key_to_find in line:
                        #  Solo reemplaza la parte del mensajeRespIn que coincide
                        pattern = re.escape('mensajeRespIn.') + r'[\w\.\:]*' + re.escape(key_to_find)
                        updated_line = re.sub(pattern, f"mensajeRespIn.Data.{final_field}", updated_line)
                        matched_any = True

                #  Si encontramos algún mensajeRespIn en la línea y lo reemplazamos, lo guardamos
                if matched_any:
                    new_lines.append(updated_line)
                else:
                    #  Si hay mensajeRespIn pero no mapeado, NO eliminamos nada: lo dejamos igual
                    new_lines.append(line)
            else:
                # Líneas sin mensajeRespIn se mantienen igual
                new_lines.append(line)

        return '\n'.join(new_lines)



    # --------------------------
    # PROCESADO: REQUEST 
    # --------------------------

    def process_request_module(self, module_code: str, mapping: List[Tuple[str, str]]) -> str:
        lines = module_code.splitlines()
        new_lines = []

        mapping_dict = {}
        for orig, new in mapping:
            key_last = orig.strip().split(':')[-1]
            new_last = new.strip().split('.')[-1]
            mapping_dict[key_last] = new_last

        for line in lines:
            if 'SET' in line and 'msgSalida' in line:
                keep = False
                for key_last, new_field in mapping_dict.items():
                    if f"msgSalida" in line and f":{key_last}" in line:
                        # Hacemos el cambio
                        pattern = re.compile(r'(msgSalida\.[\w\.\:]+)')
                        matches = pattern.findall(line)
                        for match in matches:
                            if match.endswith(f":{key_last}"):
                                new_line = line.replace(match, f"msgSalida.Data.{new_field}")
                                new_lines.append(new_line)
                                keep = True
                if not keep:
                    # Eliminar líneas que no están mapeadas
                    continue
            else:
                new_lines.append(line)

        return '\n'.join(new_lines)
    
    def write_file(self, file_name: str, content: str):
        """
        escribe el archivo .esql migrado.
        """
        with open(f"{file_name}", 'w', encoding='utf-8') as f:
            f.write(content)
            logger.info(f"Archivo {file_name} creado con éxito.")

    def run(
            self, excel_path,esql_path,output_path_base, action_description: str
        ):
            
            if not esql_path:
                raise Exception("archivos_esql cannot be empty")
            else:
                excel_path = excel_path
                esql_path = esql_path
                request_module_name, request_mapping, response_module_name, response_mapping = self.read_excel_mapping(excel_path)
                logger.info(f"request_module_name: {request_module_name}")
                logger.info(f"request_mapping: {request_mapping}")
                logger.info(f"response_module_name: {response_module_name}")
                logger.info(f"response_mapping: {response_mapping}")
                with open(esql_path, 'r', encoding='utf-8') as f:
                    esql_code = f.read()
                #  PROCESS REQUEST
                module_code_request = self.extract_compute_module(esql_code, request_module_name)
                #logger.info(f"module_code_request: {module_code_request}")
                module_json_request = self.convert_module_to_json(module_code_request)
                #logger.info(f"module_json_request: {module_json_request}")
                module_final_request = self.process_request_module(module_json_request, request_mapping)
                #logger.info(f"module_final_request: {module_final_request}")
                esql_code = esql_code.replace(module_code_request, module_final_request)
                #logger.info(f"esql_code: {esql_code}")
                input = f"Candidate Job description: {action_description}"
                screening_result = self.screening_agent.run(input)
                file_name = f"{esql_path.split('/')[-1].split('.')[0]}_salida.esql"
                output_path = os.path.join(output_path_base,file_name)
                self.write_file(output_path, esql_code)
            return RunResponse(
                content=json.dumps({
                    **screening_result.model_dump(),  # convierte DummyJson a dict serializable
                    "file_path": output_path
                }, ensure_ascii=False)
            )
     

from save_and_generate_url import save_and_generate_url_s3

def main():
    bucket_name = "agents-temp-files"
    s3_key = "sql-joiner/migracion_odi_a_datastage_2025-07-21.xml"
    file_path = "../../../../temporal_files/DM_CHQGEREN_010 - CHEQUES DE GERENCIA MOVIMIENTOS DÍA.sql"
    url = save_and_generate_url_s3( s3_key, file_path)
    return url

if __name__ == "__main__":
    print(main())
    
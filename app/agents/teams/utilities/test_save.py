from save_and_generate_url import save_and_generate_url_s3

def main():
    bucket_name = "agents-temp-files"
    s3_key = "sql-joiner/migracion_odi_a_datastage_2025-07-21.xml"
    file_path = "../../../../utilities/DM_CHQGEREN_002 - Cheques de Gerencia Pendientes de Pago.sql"
    url = save_and_generate_url_s3(bucket_name, s3_key, file_path)
    return url

if __name__ == "__main__":
    print(main())
    
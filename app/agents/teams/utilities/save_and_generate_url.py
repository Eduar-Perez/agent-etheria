import boto3
import time
import threading
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

# Configura tus valores
# Ruta en S3
REGION_NAME = "us-east-1"
# Cliente de S3
s3 = boto3.client("s3", region_name=REGION_NAME)


def subir_a_s3_y_generar_url(file_path: str, bucket_name, s3_key) -> str:
    # Subir archivo al bucket
    s3.upload_file(file_path, bucket_name, s3_key)
    print(f"Archivo subido: s3://{bucket_name}/{s3_key}")

    # Crear URL prefirmada por 5 minutos
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": s3_key},
        ExpiresIn=300,  # 5 minutos
    )
    print(f"URL temporal generado: {url}")

    # Crear hilo para borrar el archivo después de 5 minutos
    threading.Thread(target=eliminar_archivo_temporal, args=(s3_key, 300)).start()

    return url

def eliminar_archivo_temporal(key: str, delay_seconds: int):
    bucket_name = "agents-temp-files"
    time.sleep(delay_seconds)
    try:
        s3.delete_object(Bucket=bucket_name, Key=key)
        print(f"Archivo eliminado: {key}")
    except ClientError as e:
        print(f"Error al eliminar archivo: {e}")


# USO EJEMPLO
def save_and_generate_url_s3(s3_key, file_path):
    """Save a local XML file to S3 and generate a temporary download URL."""
    bucket_name="agents-temp-files"
    url = subir_a_s3_y_generar_url(file_path, bucket_name, s3_key)
    # print(f"Enlace de descarga (válido 5 min): {url}")
    return url

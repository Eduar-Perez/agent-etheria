# secrets_loader.py

import boto3
import json
import os
from botocore.exceptions import ClientError

def load_aws_secrets(secret_name="secretsManager/etheria", region_name="us-east-1"):
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        secrets_dict = json.loads(secret)

        # Carga cada secreto en las variables de entorno
        for key, value in secrets_dict.items():
            os.environ[key] = value

    except ClientError as e:
        raise RuntimeError(f"Error al obtener el secreto desde Secrets Manager: {e}")

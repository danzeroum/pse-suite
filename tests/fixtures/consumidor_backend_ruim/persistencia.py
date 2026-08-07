"""S-16: a politica declara BR e o bucket e o banco pousam nos EUA."""
import boto3
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://app@clientes.cluster-abc.us-east-1.rds.amazonaws.com/prod")

s3 = boto3.client("s3", region_name="us-east-1")


def guardar(chave, corpo):
    return s3.put_object(Bucket="clientes-backup", Key=chave, Body=corpo)

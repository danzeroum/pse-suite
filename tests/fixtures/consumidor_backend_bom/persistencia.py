"""A politica declara BR, e o banco e o bucket ficam em sa-east-1."""
import boto3
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://app@clientes.cluster-abc.sa-east-1.rds.amazonaws.com/prod")

s3 = boto3.client("s3", region_name="sa-east-1")


def guardar(chave, corpo):
    return s3.put_object(Bucket="clientes-backup", Key=chave, Body=corpo)

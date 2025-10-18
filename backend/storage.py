import boto3, os
from botocore.client import Config

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)

def ensure_bucket(name: str):
    try:
        s3.create_bucket(Bucket=name)
    except Exception:
        pass

def put_bytes(bucket: str, key: str, data: bytes):
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType="application/json")
    return f"s3://{bucket}/{key}"

# data service

import boto3
import os
from botocore.exceptions import ClientError
from pymemcache.client.base import Client

MEMCACHED_ENDPOINT = os.getenv("MEMCACHED_ENDPOINT")
MEMCACHED_TTL = int(os.getenv("MEMCACHED_TTL"))

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")
PRESIGNED_URL_EXPIRY = os.getenv("PRESIGNED_URL_EXPIRY")
DB_TABLE_NAME = os.getenv("DB_TABLE_NAME")
QUT_USERNAME = os.getenv("QUT_USERNAME")

db_client = boto3.resource("dynamodb", region_name=AWS_REGION)
db_table = db_client.Table(DB_TABLE_NAME)
s3_client = boto3.client("s3", region_name=AWS_REGION)
memcached_client = Client(MEMCACHED_ENDPOINT)

def s3_write_image(key: str, image_bytes):
    try:
        res = s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Body=image_bytes,                  
            ContentType="image/png"
        )
        return res
    except ClientError as e:
        print(e)

def s3_delete(key: str):
    try: 
        res = s3_client.delete_object(Bucket=S3_BUCKET_NAME,
                                      Key=key)
        return res
    except ClientError as e:
        print(e)

def s3_get_presigned_url(key: str):
    try:
        res = s3_client.generate_presigned_url('get_object',
                                               Params={'Bucket': S3_BUCKET_NAME,
                                                       'Key': key},
                                                ExpiresIn=PRESIGNED_URL_EXPIRY)
        return res
    except ClientError as e:
        return f"error, {e}"
    
def db_put(metadata):
    try:
        res = db_table.put_item(
            Item={
                "qut-username": QUT_USERNAME,
                "filename": metadata["file_name"],
                "region": metadata["region"],
                "city": metadata["city"],
                "size": metadata["size"],
                "generated_at": metadata["generated_at"],
            },
        )
        return res
    except ClientError as e:
        print(e)

def db_get(filename):
    try:
        res = db_table.get_item(
            Key={
                "qut-username": {"S": QUT_USERNAME},
                "filename": {"S": filename},
            },
        )
        return res
    except ClientError as e:
        print(e)

def cache_filename(filename):
    memcached_client.set(filename, "exists", expire=MEMCACHED_TTL)

def cache_check_filename(filename):
    return memcached_client.get(filename) is not None

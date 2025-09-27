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
        print(f"wrote image to s3!:\n{res}")
        return res
    except ClientError as e:
        print(e)

def s3_delete(key: str):
    try: 
        res = s3_client.delete_object(Bucket=S3_BUCKET_NAME,
                                      Key=key)
        print(f"deleted s3 object!:\n{res}")
        return res
    except ClientError as e:
        print(e)

def s3_get_presigned_url(key: str):
    try:
        res = s3_client.generate_presigned_url('get_object',
                                               Params={'Bucket': S3_BUCKET_NAME,
                                                       'Key': key},
                                                ExpiresIn=PRESIGNED_URL_EXPIRY)
        print(f"fetched presigned url!:\n{res}")
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
        print(f"added metadata to dynamodb!:\n{res}")
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
        print(f"fetched metadata from dynamodb!:\n{res}")
        return res
    except ClientError as e:
        print(e)

def cache_filename(filename):
    res = memcached_client.set(filename, "exists", expire=MEMCACHED_TTL)
    if res:
        print(f"cached filename, '{filename}', to elasticache!")
    else:
        print(f"failed to cache filename, '{filename}'!")
    

def cache_check_filename(filename):
    return memcached_client.get(filename) is not None

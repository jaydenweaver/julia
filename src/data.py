# data service

import boto3
import os
from botocore.exceptions import ClientError
from io import BytesIO
from pymemcache.client.base import Client

memcached_endpoint = os.getenv(MEMCACHED_ENDPOINT)
memcached_ttl = os.getenv(MEMCACHED_TTL)

s3_bucket_name = os.getenv("S3_BUCKET_NAME")
aws_region = os.getenv("AWS_REGION")
presigned_url_expiry = os.getenv("PRESIGNED_URL_EXPIRY")
qut_username = os.getenv("QUT_USERNAME")
db_table_name = os.getenv("DB_TABLE_NAME")

db_client = boto3.resource("dynamodb", region_name=aws_region)
db_table = db_client.Table(db_table_name)
s3_client = boto3.client("s3", region_name=aws_region)
memcached_client = Client(memcached_endpoint)

def s3_write_image(key: str, image_bytes):
    try:
        res = s3_client.put_object(
            Bucket=s3_bucket_name,
            Key=key,
            Body=image_bytes,                  
            ContentType="image/png"
        )
        print("put response: ", res)
    except ClientError as e:
        print(e)

def s3_delete(key: str):
    try: 
        res = s3_client.delete_object(Bucket=s3_bucket_name,
                                      Key=key)
        print("delete response: ", res)
    except ClientError as e:
        print(e)

def s3_get_presigned_url(key: str):
    try:
        res = s3_client.generate_presigned_url('get_object',
                                               Params={'Bucket': s3_bucket_name,
                                                       'Key': key},
                                                ExpiresIn=presigned_url_expiry)
        return res
    except ClientError as e:
        return f"error, {e}"
    
def db_put(item):
    try:
        res = db_table.put_item(Item=item)
        print("put response: ", res)
    except ClientError as e:
        print(e)

def db_get(key):
    try:
        res = db_table.get_item(Key=key)
        print("get response: ", res.get("Item"))
    except ClientError as e:
        print(e)

def cache_filename(filename):
    memcached_client.set(filename, "exists", expire=memcached_ttl)

def cache_check_filename(filename):
    return memcached_client.get(filename) is not None

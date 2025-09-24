# data service

import boto3
import os
from botocore.exceptions import ClientError

s3_bucket_name = os.getenv("S3_BUCKET_NAME")
aws_region = os.getenv("AWS_REGION")
presigned_url_expiry = os.getenv("PRESIGNED_URL_EXPIRY")
qut_username = os.getenv("QUT_USERNAME")
db_table_name = os.getenv("DB_TABLE_NAME")

db_client = boto3.client("dynamodb", region_name=aws_region)
s3_client = boto3.client("s3", region_name=aws_region)

def s3_write(key: str, data):
    try:
        res = s3_client.put_object(Bucket=s3_bucket_name,
                                   Key=key,
                                   Body=data)
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
        res = db_client.put_item(
            TableName=db_table_name,
            Item=item,
        )
        print("put response: ", res)
    except ClientError as e:
        print(e)

def db_get(key):
    try:
        res = db_client.get_item(
            TableName=db_table_name,
            Key=key,
        )
        print("get response: ", res.get("Item"))
    except ClientError as e:
        print(e)
# data service

import boto3
import os
from botocore.exceptions import ClientError

s3_bucket_name = os.getenv("S3_BUCKET_NAME")
aws_region = os.getenv("AWS_REGION")

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
                                                ExpiresIn=3600)
        return res
    except ClientError as e:
        return f"error, {e}"
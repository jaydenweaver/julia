import boto3
import os
from botocore.exceptions import ClientError
from pymemcache.client.base import Client
from fastapi import HTTPException
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("data-service")

class DataService:
    def __init__(self):
        self.memcached_endpoint = os.getenv("MEMCACHED_ENDPOINT")
        self.memcached_ttl = int(os.getenv("MEMCACHED_TTL", "300"))
        self.s3_bucket_name = os.getenv("S3_BUCKET_NAME")
        self.aws_region = os.getenv("AWS_REGION", "ap-southeast-2")
        self.presigned_url_expiry = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))
        self.db_table_name = os.getenv("DB_TABLE_NAME")
        self.qut_username = os.getenv("QUT_USERNAME", "default-user")

        self.db_client = boto3.resource("dynamodb", region_name=self.aws_region)
        self.db_table = self.db_client.Table(self.db_table_name)
        self.s3_client = boto3.client("s3", region_name=self.aws_region)
        self.memcached_client = Client(self.memcached_endpoint)

    # -------- s3 --------
    def write_image(self, key: str, image_bytes: bytes):
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket_name,
                Key=key,
                Body=image_bytes,
                ContentType="image/png",
            )
            logger.info(f"Uploaded image {key} to S3.")
        except ClientError as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e))

    def delete_image(self, key: str):
        try:
            self.s3_client.delete_object(Bucket=self.s3_bucket_name, Key=key)
            logger.info(f"Deleted S3 object {key}")
        except ClientError as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e))

    def get_presigned_url(self, key: str):
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket_name, "Key": key},
                ExpiresIn=self.presigned_url_expiry,
            )
            logger.info(f"Generated presigned URL for {key}")
            return url
        except ClientError as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e))

    # -------- db --------
    def put_metadata(self, metadata: dict):
        try:
            self.db_table.put_item(
                Item={
                    "qut-username": self.qut_username,
                    "filename": metadata["file_name"],
                    "region": metadata["region"],
                    "city": metadata["city"],
                    "size": metadata["size"],
                    "generated_at": metadata["generated_at"],
                }
            )
            logger.info(f"Inserted metadata for {metadata['file_name']}")
        except ClientError as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e))

    def get_metadata(self, filename: str):
        try:
            res = self.db_table.get_item(
                Key={
                    "qut-username": self.qut_username,
                    "filename": filename,
                }
            )
            item = res.get("Item")
            if not item:
                raise HTTPException(status_code=404, detail="Metadata not found")
            logger.info(f"Fetched metadata for {filename}")
            return item
        except ClientError as e:
            logger.error(e)
            raise HTTPException(status_code=500, detail=str(e))

    # -------- cache --------
    def cache_filename(self, filename: str):
        result = self.memcached_client.set(filename, "exists", expire=self.memcached_ttl)
        if result:
            logger.info(f"Cached {filename}")
        else:
            logger.warning(f"Failed to cache {filename}")
        return result

    def check_cache(self, filename: str):
        exists = self.memcached_client.get(filename) is not None
        logger.info(f"Cache check {filename}: {exists}")
        return exists

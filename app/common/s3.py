import os
from typing import Optional
from uuid import uuid4
from botocore.exceptions import ClientError
from fastapi import HTTPException

import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError
from dotenv import load_dotenv
from fastapi import UploadFile
from starlette import status

load_dotenv()

AWS_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_KEY")
AWS_REGION = os.environ.get("S3_REGION")
AWS_S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

async def upload_file_to_s3(file: UploadFile, folder: str, name: str) -> tuple:
    """Uploads a file to S3 within a specified folder and returns the URL."""
    try:
        contents = await file.read()
        ext = os.path.splitext(file.filename)[1]
        key = f"{folder}/{name}{ext}"  # Generate a unique key
        # key = f"{folder}/test-{name}{ext}"  # for tests
        s3_client.put_object(Bucket=AWS_S3_BUCKET_NAME, Key=key, Body=contents)
        url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"
        return url, key
    except(BotoCoreError, NoCredentialsError, Exception) as e:
        raise Exception(f"Erreur lors de l'upload vers S3: {str(e)}")


def get_s3_temporary_url(name: str = None) -> str | None:
    if not name:
        return None
    s3_client = boto3.client("s3",region_name=AWS_REGION,aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY,)

    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_S3_BUCKET_NAME, "Key": f"{name}"},
            ExpiresIn=20 * 60  # 20 minutes
        )
        return url
    except (ClientError, Exception) as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors de la génération de l'URL temporaire S3")
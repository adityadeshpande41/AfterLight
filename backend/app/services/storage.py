"""
S3-compatible object storage service.

Works with both:
- MinIO (local development)
- AWS S3 (production)

Only the environment variables change.
"""

import uuid

import boto3
from botocore.config import Config

from app.config import settings


def get_s3_client():
    """Create an S3 client configured for the current environment."""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists():
    """Create the evidence bucket if it doesn't exist (for local dev)."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except client.exceptions.ClientError:
        client.create_bucket(Bucket=settings.s3_bucket)


def generate_upload_url(
    incident_id: str,
    filename: str,
    content_type: str = "application/octet-stream",
    expires_in: int = 3600,
) -> dict:
    """
    Generate a presigned PUT URL for direct browser upload.

    Returns:
        {
            "upload_url": "https://...",
            "object_key": "evidence/incident-id/uuid-filename",
            "expires_in": 3600
        }
    """
    # Generate a unique object key
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique_name = f"{uuid.uuid4().hex[:12]}_{filename}"
    object_key = f"evidence/{incident_id}/{unique_name}"

    client = get_s3_client()
    upload_url = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )

    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "expires_in": expires_in,
    }


def generate_download_url(object_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned GET URL to view/download a file."""
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": object_key,
        },
        ExpiresIn=expires_in,
    )

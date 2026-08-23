"""File upload endpoints — presigned URL pattern."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EvidenceItem
from app.schemas.evidence import EvidenceItemResponse
from app.services.storage import generate_download_url, generate_upload_url

router = APIRouter(prefix="/uploads", tags=["uploads"])


class UploadURLRequest(BaseModel):
    evidence_id: str
    filename: str
    content_type: str = "application/octet-stream"


class UploadURLResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int


class ConfirmUploadRequest(BaseModel):
    evidence_id: str
    object_key: str
    file_hash: str | None = None


@router.post("/request-url", response_model=UploadURLResponse)
async def request_upload_url(
    body: UploadURLRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a presigned URL for direct browser-to-S3 upload.

    Flow:
    1. Frontend calls this endpoint with evidence_id + filename
    2. Backend returns a presigned PUT URL
    3. Frontend uploads the file directly to S3/MinIO using that URL
    4. Frontend calls /uploads/confirm after upload succeeds
    """
    # Verify evidence item exists
    result = await db.execute(
        select(EvidenceItem).where(EvidenceItem.id == body.evidence_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    url_data = generate_upload_url(
        incident_id=str(item.incident_id),
        filename=body.filename,
        content_type=body.content_type,
    )

    return UploadURLResponse(**url_data)


@router.post("/confirm", response_model=EvidenceItemResponse)
async def confirm_upload(
    body: ConfirmUploadRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm that a file upload completed successfully.
    Updates the evidence item with the object key and sets status to Pending review.
    """
    result = await db.execute(
        select(EvidenceItem).where(EvidenceItem.id == body.evidence_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence item not found")

    item.object_key = body.object_key
    item.file_hash = body.file_hash
    item.status = "Pending review"

    await db.commit()
    await db.refresh(item)

    return EvidenceItemResponse.model_validate(item)


class DownloadURLResponse(BaseModel):
    download_url: str
    expires_in: int


@router.get("/download/{evidence_id}", response_model=DownloadURLResponse)
async def get_download_url(
    evidence_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a presigned download URL for an evidence file."""
    result = await db.execute(
        select(EvidenceItem).where(EvidenceItem.id == evidence_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    if not item.object_key:
        raise HTTPException(status_code=404, detail="No file uploaded for this evidence item")

    url = generate_download_url(item.object_key)

    return DownloadURLResponse(download_url=url, expires_in=3600)

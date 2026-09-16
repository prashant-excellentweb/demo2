from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import AttachmentServiceDep, CurrentUser
from app.schemas.attachment import AttachmentRead

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    user: CurrentUser,
    service: AttachmentServiceDep,
    file: UploadFile = File(...),
) -> AttachmentRead:
    """Store an upload and return metadata.

    The response deliberately omits file contents: the old endpoint handed the
    whole base64 payload back to the browser only for it to be posted straight
    back, doubling transfer for every attachment.
    """
    attachment = await service.store(user, file)
    return AttachmentRead.model_validate(attachment)


@router.get("/{attachment_id}/content")
def download_attachment(
    attachment_id: str, user: CurrentUser, service: AttachmentServiceDep
) -> FileResponse:
    attachment, path = service.resolve_file(attachment_id, user)
    return FileResponse(
        path,
        media_type=attachment.content_type,
        filename=attachment.filename,
        content_disposition_type="inline" if attachment.is_image else "attachment",
        headers={
            # Never let the browser re-interpret a stored file as something
            # executable, and keep private uploads out of shared caches.
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=3600",
        },
    )

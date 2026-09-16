from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    """Metadata only.

    Image bytes are fetched on demand from `/api/attachments/{id}/content`, which
    keeps chat payloads small and lets the browser cache the file.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    size_bytes: int
    is_image: bool

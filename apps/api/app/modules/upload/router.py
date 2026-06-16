import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.modules.auth.router import AdminDep
from app.shared.responses import ApiResponse

router = APIRouter()
logger = logging.getLogger(__name__)

CHUNK_SIZE = 8192

_CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

_FORMAT_NAMES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WebP",
    "image/gif": "GIF",
}


@router.post("/login-background", response_model=ApiResponse[dict])
def upload_login_background(
    user: AdminDep,
    file: UploadFile = File(...),
):
    ext = _CONTENT_TYPE_TO_EXT.get(file.content_type or "")
    if ext is None:
        allowed = "/".join(
            _FORMAT_NAMES.get(t, t) for t in settings.upload_allowed_image_types
        )
        raise HTTPException(status_code=400, detail=f"不支持的图片格式，仅支持 {allowed} 图片")

    uploads_dir = settings.uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)

    filename = f"login-bg-{user.id}-{uuid.uuid4()}{ext}"
    file_path = uploads_dir / filename

    total = 0
    oversized = False
    try:
        with file_path.open("wb") as buffer:
            while chunk := file.file.read(CHUNK_SIZE):
                total += len(chunk)
                if total > settings.upload_max_size_bytes:
                    oversized = True
                    break
                buffer.write(chunk)
    except Exception:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        logger.exception("Failed to read upload file stream")
        raise HTTPException(status_code=400, detail="文件上传失败")
    finally:
        file.file.close()

    if total == 0:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="上传文件为空")

    if oversized:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=f"图片大小不能超过 {settings.upload_max_size_bytes // (1024 * 1024)}MB",
        )

    url = f"{settings.uploads_url_path}/{filename}"
    return ApiResponse(data={"url": url})

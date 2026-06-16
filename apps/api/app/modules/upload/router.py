import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.modules.auth.router import AdminDep
from app.shared.responses import ApiResponse

router = APIRouter()

CHUNK_SIZE = 8192

_CONTENT_TYPE_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


@router.post("/login-background", response_model=ApiResponse[dict])
def upload_login_background(
    user: AdminDep,
    file: UploadFile = File(...),
):
    if file.content_type not in settings.upload_allowed_image_types:
        raise HTTPException(status_code=400, detail="仅支持 JPEG/PNG/WebP/GIF 图片")

    ext = _CONTENT_TYPE_TO_EXT.get(file.content_type)
    if ext is None:
        raise HTTPException(status_code=400, detail="不支持的图片格式")

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
            file_path.unlink()
        raise HTTPException(status_code=400, detail="文件上传失败")

    if oversized:
        file_path.unlink()
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    url = f"{settings.uploads_url_path}/{filename}"
    return ApiResponse(data={"url": url})

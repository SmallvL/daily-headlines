import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.modules.auth.router import CurrentUserDep
from app.shared.responses import ApiResponse

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/login-background", response_model=ApiResponse[dict])
def upload_login_background(
    user: CurrentUserDep,
    file: UploadFile = File(...),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPEG/PNG/WebP/GIF 图片")

    uploads_dir = settings.uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "bg.jpg").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"

    filename = f"login-bg-{user.id}-{uuid.uuid4()}{ext}"
    file_path = uploads_dir / filename

    # Fast path: reject immediately if the framework already knows the size.
    known_size = getattr(file, "size", None)
    if known_size is not None and known_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    total = 0
    oversized = False
    with file_path.open("wb") as buffer:
        while chunk := file.file.read(8192):
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                oversized = True
                break
            buffer.write(chunk)

    if oversized:
        file_path.unlink()
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    url = f"{settings.uploads_url_path}/{filename}"
    return ApiResponse(data={"url": url})

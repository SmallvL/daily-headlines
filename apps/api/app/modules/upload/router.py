import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.router import CurrentUserDep
from app.shared.responses import ApiResponse

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/login-background", response_model=ApiResponse[dict])
def upload_login_background(
    user: CurrentUserDep,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPEG/PNG/WebP/GIF 图片")

    uploads_dir = settings.uploads_dir
    uploads_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "bg.jpg").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"

    filename = f"login-bg-{user.id}-{uuid.uuid4().hex}{ext}"
    file_path = uploads_dir / filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Basic size check after write
    if file_path.stat().st_size > MAX_FILE_SIZE:
        file_path.unlink()
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    url = f"{settings.uploads_url_path}/{filename}"
    return ApiResponse(data={"url": url})

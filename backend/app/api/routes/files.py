from fastapi import APIRouter
from backend.app.api.dependencies import Owner
from backend.app.models.api import FileItem
from backend.app.services.file_service import list_files

router = APIRouter()

@router.get("/files", response_model=list[FileItem])
def files(owner: Owner):
    return list_files()

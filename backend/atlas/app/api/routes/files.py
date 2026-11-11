from functools import partial
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from backend.atlas.app.api.dependencies import Owner
from backend.atlas.app.models.api import FileItem, FileEdit
from backend.atlas.app.services import file_service as files

router = APIRouter()

@router.get("/files", response_model=list[FileItem])
def listing(owner: Owner, directory: str = ""):
    return files.list_files(directory)

@router.get("/files/content")
def download(owner: Owner, path: str = Query(min_length=1, max_length=160)):
    data, revision = files.read(path)
    return Response(data, media_type="application/octet-stream", headers={"ETag": f'"{revision}"', "X-Content-Type-Options": "nosniff"})

@router.get("/files/text")
def document(owner: Owner, path: str = Query(min_length=1, max_length=160)):
    return files.document(path)

@router.post("/files/upload", response_model=FileItem, status_code=201)
async def upload(request: Request, owner: Owner, name: str = Query(min_length=1, max_length=120)):
    files.target(f"workspace/{name}", writing=True)
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > files.MAX_BYTES:
            raise HTTPException(413, "Uploads are limited to 5 MiB")
        data.extend(chunk)
    return await run_in_threadpool(partial(files.write, f"workspace/{name}", bytes(data), None))

@router.put("/files/text", response_model=FileItem)
def edit(body: FileEdit, owner: Owner, path: str = Query(min_length=1, max_length=160)):
    data = body.content.encode("utf-8")
    if len(data) > files.MAX_TEXT_BYTES or "\x00" in body.content:
        raise HTTPException(413, "Editor requires UTF-8 text up to 256 KiB")
    return files.write(path, data, body.revision)

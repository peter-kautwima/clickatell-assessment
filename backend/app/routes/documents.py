from fastapi import APIRouter, UploadFile, File

router = APIRouter()


@router.post("/documents")
async def upload_document(file: UploadFile = File(...)) -> dict[str, str]:
    return {"status": "uploaded", "filename": file.filename}

from fastapi import APIRouter

router = APIRouter()


@router.get("/query")
def query_documents() -> dict[str, str]:
    return {"status": "ready"}

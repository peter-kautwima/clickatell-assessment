from fastapi import FastAPI

from backend.app.routes.documents import router as documents_router
from backend.app.routes.query import router as query_router

app = FastAPI(title="Clickatell Assessment API")

app.include_router(documents_router)
app.include_router(query_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello from Clickatell Assessment API"}

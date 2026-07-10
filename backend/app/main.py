from contextlib import asynccontextmanager

from fastapi import FastAPI

# Use package-relative imports so the app can be run from the `backend/` folder
from .routes.documents import router as documents_router
from .routes.query import router as query_router
from .services import embedding


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Module-qualified call (not `from .services.embedding import _get_model`)
    # so tests' monkeypatched mock is what actually runs here, not a
    # from-import name bound to the real function at import time (D2).
    # The wrapper is async because that's FastAPI's lifespan signature; the
    # actual load is still a plain, blocking sync call — nothing else is
    # running yet, so there's no event loop to freeze (rule 9 doesn't apply
    # at startup).
    embedding._get_model()
    yield


app = FastAPI(title="Clickatell Assessment API", lifespan=lifespan)

app.include_router(documents_router)
app.include_router(query_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello from Clickatell Assessment API"}

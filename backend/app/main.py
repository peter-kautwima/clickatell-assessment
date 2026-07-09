from fastapi import FastAPI

app = FastAPI(title="Clickatell Assessment API")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}

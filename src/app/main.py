import fastapi

from app.schemas import health_check

app = fastapi.FastAPI()


@app.get("/", response_model=health_check.HealthResponse)
def root():
    return {"api": "fastit"}

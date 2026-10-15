"""BidRadar API 진입점."""

from fastapi import FastAPI

app = FastAPI(title="BidRadar API", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

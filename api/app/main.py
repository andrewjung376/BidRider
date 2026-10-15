"""BidRadar API 진입점."""

from fastapi import FastAPI

from app.routes.bids import router as bids_router

app = FastAPI(title="BidRadar API", version="0.1.0")
app.include_router(bids_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import create_db_and_tables
from app.routers import ai, auth, buyer_profiles, listings, notifications, tpqc, transactions
from app.services.chroma_seed import seed_buyers


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_buyers()
    yield

app = FastAPI(
    title="CircularX API",
    description="Autonomous Waste-to-Wealth Broker Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(buyer_profiles.router, prefix="/buyer-profiles", tags=["buyer-profiles"])
app.include_router(listings.router, prefix="/listings", tags=["listings"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(tpqc.router, prefix="/tpqc", tags=["tpqc"])

os.makedirs("storage/dpps", exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok", "service": "CircularX API"}

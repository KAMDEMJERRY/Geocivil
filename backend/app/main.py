from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import settings
from .database import SessionLocal
from .routers import auth, prices, projects
from .seed import seed_prices


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        seed_prices(db)
    yield


app = FastAPI(title="GéoCivil API", version="0.1.0", lifespan=lifespan,
              docs_url=None if settings.environment == "production" else "/docs")
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, projects.router, prices.router):
    app.include_router(r)


@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok"}

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from auth import hash_password
from config import settings
from db import get_connection, init_db
from routers import doctors as doctors_router
from routers import appointments as appointments_router
from routers import auth

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("hospital_api.log")
    ],
)
logger = logging.getLogger("hospital_api")


def _seed_default_users():
    with get_connection() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if n == 0:
            conn.execute(
                "INSERT INTO users (username, hashed_pw, role) "
                "VALUES (?, ?, ?)",
                ("admin", hash_password("admin123"), "admin"),
            )
            conn.execute(
                "INSERT INTO users (username, hashed_pw, role) "
                "VALUES (?, ?, ?)",
                ("user", hash_password("user123"), "normal"),
            )
            conn.commit()
            logger.info(
                "Seeded default users: admin/admin123 (role=admin), "
                "user/user123 (role=viewer)"
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Startup: initialising database")
    init_db()
    _seed_default_users()
    yield
    logger.info("Shutdown")


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan,
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %s (%.1f ms)", request.method,
                request.url.path, response.status_code, ms)
    return response

app.add_middleware(CORSMiddleware,
                   allow_methods=["POST","GET"],
                   allow_headers=["*"])


app.include_router(doctors_router.router, prefix="/doctors", tags=["doctors"])
app.include_router(appointments_router.router, prefix="/appointments", tags=["appointments"])
app.include_router(auth.router, prefix="/user", tags=["auth"])

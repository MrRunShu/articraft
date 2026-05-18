from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import database
from app.routers.health import router as health_router
from app.routers.user import router as user_router
from app.routers.article import router as article_router
from app.routers.payment import router as payment_router
from app.exceptions import BusinessException, ErrorCode
from app.utils.session import init_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    await init_redis()
    yield
    await database.disconnect()
    await close_redis()


app = FastAPI(
    title="AI 爆款文章创作器",
    version="0.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return JSONResponse(
        status_code=200,
        content={"code": exc.error_code.code, "data": None, "message": exc.message},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={"code": ErrorCode.SYSTEM_ERROR.code, "data": None, "message": str(exc)},
    )


app.include_router(health_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(article_router, prefix="/api")
app.include_router(payment_router, prefix="/api")

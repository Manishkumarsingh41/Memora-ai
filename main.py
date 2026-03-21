import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from logging_config import get_logger
from routers.admin import router as admin_router
from routers.webhook import router as webhook_router
from services.database import init_db
from services.pending_store import close_redis, get_redis


logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
	try:
		init_db()
		os.makedirs("./temp_files", exist_ok=True)
		os.makedirs("./chroma_db", exist_ok=True)
		os.makedirs("./logs", exist_ok=True)

		try:
			redis = await get_redis()
			await redis.ping()
			logger.info("Redis connection test successful")
		except Exception as exc:
			logger.warning("Redis connection test failed: %s", exc)

		logger.info("Memora AI startup complete")
	except Exception:
		logger.exception("Startup failed")
		raise

	yield

	try:
		await close_redis()
	except Exception:
		logger.exception("Failed closing Redis during shutdown")


app = FastAPI(title="Memora AI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
	if exc.status_code == 404:
		return JSONResponse(status_code=404, content={"error": "Not found"})
	return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	fields = []
	for error in exc.errors():
		loc = ".".join(str(part) for part in error.get("loc", []))
		fields.append({"field": loc, "message": error.get("msg", "Invalid value")})
	return JSONResponse(status_code=422, content={"error": "Validation error", "fields": fields})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
	logger.error("Unhandled exception: %s", traceback.format_exc())
	return JSONResponse(status_code=500, content={"error": "Internal server error"})


app.include_router(webhook_router, prefix="")
app.include_router(admin_router, prefix="/admin")


@app.get("/")
async def root():
	return {"status": "ok", "app": "Memora AI", "version": "1.0.0"}


@app.get("/health")
async def health():
	return {"status": "ok"}


import logging
import json
import google.cloud.logging
import os
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from sqlalchemy.orm import Session

# Database imports
from app.database.database import SessionLocal, init_db

# Router import
from app.api.routes import router as reports_router

# Initialize Google Cloud Logging client
client = google.cloud.logging.Client()
default_handler = client.get_default_handler()
json_formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
default_handler.setFormatter(json_formatter)
logging.getLogger().addHandler(default_handler)
client.setup_logging()

# Configure basic logging for structured output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

# Read environment variables (if needed here)
MAX_UPLOAD_SIZE_MB = os.getenv("MAX_UPLOAD_SIZE_MB", "25")
REPORTS_BUCKET_NAME = os.getenv("REPORTS_BUCKET_NAME", "my-reports-bucket")

app = FastAPI(title="GFV Investment Readiness Report API")

# CORS: in production, restrict allowed_origins as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(json.dumps({
        "event": "request_received",
        "method": request.method,
        "url": str(request.url)
    }))
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(json.dumps({
            "event": "request_error",
            "error": str(e)
        }), exc_info=True)
        raise e
    logger.info(json.dumps({
        "event": "request_completed",
        "status_code": response.status_code,
        "url": str(request.url)
    }))
    return response

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_token(token: str = Depends(oauth2_scheme)):
    """
    Simple stub function to validate a token. Replace with real JWT or OAuth checks.
    """
    expected_token = "expected_static_token"
    if token != expected_token:
        logger.warning("Unauthorized access attempt with token: %s", token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info("Token verified successfully.")
    return token

def get_db():
    """
    Yields a database session for each request, ensuring it is closed afterward.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Include the reports router with '/api' prefix to match the README
app.include_router(
    reports_router,
    prefix="/api",
    tags=["Reports"]
)

@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}

# ------------------------------------------------------------------
# Exception Handlers
# ------------------------------------------------------------------

@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    if exc.status_code == 404:
        logger.warning("HTTP 404 for %s: %s", request.url, exc.detail)
    else:
        logger.error("HTTPException for %s: %s", request.url, exc.detail, exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception for %s: %s", request.url, str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

@app.on_event("startup")
async def startup_event():
    # Initialize the database: create missing tables such as 'reports'
    init_db()
    logger.info("Database initialized.")

    # Log environment variables (optional for debugging)
    logger.info(f"MAX_UPLOAD_SIZE_MB is set to {MAX_UPLOAD_SIZE_MB}")
    logger.info(f"REPORTS_BUCKET_NAME is set to {REPORTS_BUCKET_NAME}")

    logger.info("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown complete.")

import logging
import json
import google.cloud.logging
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from sqlalchemy.orm import Session

# Import the session factory from your database module.
from app.database.database import SessionLocal

# Initialize the Google Cloud Logging client.
client = google.cloud.logging.Client()
default_handler = client.get_default_handler()
# Optionally configure a JSON formatter for structured logs.
json_formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
default_handler.setFormatter(json_formatter)
logging.getLogger().addHandler(default_handler)
client.setup_logging()

# Configure basic logging for structured output.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize the FastAPI application.
app = FastAPI(title="AI-Powered Report Generation API")

# Set up CORS middleware; in production, limit allowed origins as needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origins in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to log each incoming request and its outcome.
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
        # Log at ERROR level with traceback for unhandled exceptions
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

# Define the OAuth2 scheme for Bearer token extraction.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_token(token: str = Depends(oauth2_scheme)):
    """
    Dependency to verify the OAuth2 Bearer token.
    This stub function performs a static check for demonstration purposes.
    Extend this logic with proper token validation (e.g., JWT verification) as needed.
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
    Dependency that provides a SQLAlchemy database session.
    This function yields a session and ensures it is properly closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/reports", dependencies=[Depends(verify_token)])
def get_reports(db: Session = Depends(get_db)):
    """
    Protected endpoint to retrieve reports.
    Requires a valid OAuth2 Bearer token and access to the database.
    """
    logger.info("Fetching reports from the database")
    return {"message": "Access granted to reports endpoint", "reports": []}

@app.get("/health")
def health_check():
    """
    A simple health check endpoint to verify that the service is running.
    This endpoint does not require authentication.
    """
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}

# ------------------------------------------------------------------------
# Exception Handlers
# ------------------------------------------------------------------------

@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    """
    This handler processes known HTTP exceptions (e.g., 404, 400, etc.).
    Logs at WARNING level for 404 and ERROR level otherwise (with traceback).
    """
    if exc.status_code == 404:
        logger.warning("HTTP 404 error for %s: %s", request.url, exc.detail)
    else:
        logger.error("HTTPException for %s: %s", request.url, exc.detail, exc_info=True)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    This handler processes unhandled exceptions (HTTP 500).
    Logs at ERROR level with full stack trace, returning a sanitized response.
    """
    logger.error("Unhandled exception for %s: %s", request.url, str(exc), exc_info=True)
    # Cloud Error Reporting will automatically capture these error logs.
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown complete.")

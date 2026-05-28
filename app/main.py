from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from routes import auth_routes, file_routes, web_routes, admin_routes
from models.database import init_database
from config import Config
import os

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app = FastAPI(title="UEBA Cloud Storage")

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"]
)

# Include all routes
app.include_router(auth_routes.router)
app.include_router(file_routes.router)
app.include_router(web_routes.router)
app.include_router(admin_routes.router)

@app.on_event("startup")
def startup():
    init_database()
    os.makedirs(Config.UPLOAD_BASE_DIR, exist_ok=True)
    os.makedirs(Config.TRASH_DIR, exist_ok=True)
    print("Application started successfully")

@app.get("/health")
def health():
    return {"status": "healthy"}
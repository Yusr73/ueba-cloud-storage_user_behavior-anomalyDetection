from fastapi import FastAPI
from routes import auth_routes, file_routes, web_routes, admin_routes
from models.database import init_database
from config import Config
import os

app = FastAPI(title="UEBA Cloud Storage")

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
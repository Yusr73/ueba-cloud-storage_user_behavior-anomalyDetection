from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from controllers.auth_controller import AuthController, get_current_user

router = APIRouter(tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None

@router.post("/register")
def register(request: RegisterRequest):
    return AuthController.register(request.username, request.password, request.email)

@router.post("/login")
def login(request: LoginRequest, req: Request = None):
    ip = req.client.host if req else None
    return AuthController.login(request.username, request.password, ip)

@router.post("/logout")
def logout(current_user = Depends(get_current_user)):
    return AuthController.logout(current_user)

@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    return current_user
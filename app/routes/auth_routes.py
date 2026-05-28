from fastapi import APIRouter, Depends, Response
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
def login(request: LoginRequest, response: Response):
    return AuthController.login(request.username, request.password, response)

@router.post("/logout")
def logout(response: Response, current_user = Depends(get_current_user)):
    return AuthController.logout(response, current_user)

@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    return current_user
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user_model import UserModel
from utils.security import create_access_token, decode_token
from utils.logger import write_log

security = HTTPBearer()

class AuthController:
    @staticmethod
    def register(username: str, password: str, email: str = None):
        uid = UserModel.create_user(username, password, email)
        
        if uid:
            write_log(
                event_type="user_created",
                uid=uid,
                uid_type="uid",
                params={"username": username, "email": email},
                role="user",
                is_local_ip=True,
                location={"city": "unknown"}
            )
            return {"message": "User created", "uid": uid}
        
        raise HTTPException(status_code=400, detail="Username already exists")
    
    @staticmethod
    def login(username: str, password: str, response: Response):
        user = UserModel.authenticate(username, password)
        
        write_log(
            event_type="login_attempt",
            uid=username,
            uid_type="name",
            params={"username": username, "success": user is not None},
            role="user" if user else None,
            is_local_ip=True,
            location={"city": "unknown"}
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        write_log(
            event_type="login_successful",
            uid=user['uid'],
            uid_type="uid",
            params={"username": username},
            role=user['role'],
            is_local_ip=True,
            location={"city": "unknown"}
        )
        
        token = create_access_token({
            "sub": user['username'],
            "role": user['role'],
            "uid": user['uid']
        })
        
        # Set httpOnly cookie
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=3600
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "uid": user['uid'],
            "role": user['role']
        }
    
    @staticmethod
    def logout(response: Response, current_user):
        write_log(
            event_type="logout_occured",
            uid=current_user['uid'],
            uid_type="uid",
            params={"username": current_user['username']},
            role=current_user['role'],
            is_local_ip=True,
            location={"city": "unknown"}
        )
        response.delete_cookie("access_token")
        return {"message": "Logged out"}


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = None
    
    # Try Authorization header first
    if credentials:
        token = credentials.credentials
    
    # Try cookie if no header
    if not token:
        token = request.cookies.get('access_token')
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = UserModel.get_user_by_uid(payload.get("uid"))
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "username": user['username'],
        "role": user['role'],
        "uid": user['uid']
    }
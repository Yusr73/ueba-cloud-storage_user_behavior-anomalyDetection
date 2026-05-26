from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user_model import UserModel
from utils.security import create_access_token, decode_token
from utils.logger import write_log

security = HTTPBearer()

class AuthController:
    @staticmethod
    def register(username: str, password: str, email: str = None):
        """Register a new user."""
        uid = UserModel.create_user(username, password, email)
        
        if uid:
            write_log(
                event_type="user_created",
                uid=uid,
                uid_type="uid",
                params={"username": username},
                role="user"
            )
            return {"message": "User created", "uid": uid}
        
        raise HTTPException(status_code=400, detail="Username already exists")
    
    @staticmethod
    def login(username: str, password: str, ip_address: str = None):
        """Authenticate user and log attempt (CLUE compliant)."""
        user = UserModel.authenticate(username, password)
        
        # Always log login_attempt (CLUE standard)
        write_log(
            event_type="login_attempt",
            uid=username,
            uid_type="name",
            params={"username": username, "success": user is not None},
            ip_address=ip_address
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Log successful login separately (CLUE standard)
        write_log(
            event_type="login_successful",
            uid=user['uid'],
            uid_type="name",
            params={"username": username},
            role=user['role'],
            ip_address=ip_address
        )
        
        token = create_access_token({
            "sub": user['username'],
            "role": user['role'],
            "uid": user['uid']
        })
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "uid": user['uid'],
            "role": user['role']
        }
    
    @staticmethod
    def logout(current_user):
        """Log user logout."""
        write_log(
            event_type="logout_occured",
            uid=current_user['uid'],
            uid_type="name",
            params={"username": current_user['username']},
            role=current_user['role']
        )
        return {"message": "Logged out"}


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate current user from JWT token."""
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "username": payload.get("sub"),
        "role": payload.get("role"),
        "uid": payload.get("uid")
    }
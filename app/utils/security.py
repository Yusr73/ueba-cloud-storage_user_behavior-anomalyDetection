import bcrypt
from datetime import datetime, timezone, timedelta
from jose import jwt
from config import Config

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
    except:
        return None
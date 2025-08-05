from jose import JWTError,jwt
from datetime import datetime,timedelta,UTC
from ..config import JWT_SECRET

print("JWT_SECRET is:", JWT_SECRET)

ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    print("create token")
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire})
    print("token returned")
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)

def verify_access_token(token: str):
    try:
        print("Verifying token:", token)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

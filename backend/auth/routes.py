from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_email(db, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password):
        return False
    return user

class UserCreate(BaseModel):
    email: str
    password: str
    name: str = ""
    ssn: str = ""
    dob: str = ""
    address: str = ""
    state: str = ""

class UserOut(BaseModel):
    email: str
    name: str = ""
    state: str = ""

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        password=hashed_pw,
        name=user.name,
        ssn=user.ssn,
        dob=user.dob,
        address=user.address,
        state=user.state
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserOut(email=new_user.email, name=new_user.name, state=new_user.state)

@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return Token(access_token=access_token, token_type="bearer")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception
    return user

@router.get("/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    return UserOut(email=current_user.email, name=current_user.name, state=current_user.state)
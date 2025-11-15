import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Literal
from database import create_document, get_documents, db
from schemas import AuthUser
from passlib.context import CryptContext
from bson.objectid import ObjectId

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal["job_seeker", "hirer"]

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PublicUser(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Literal["job_seeker", "hirer"]

@app.get("/")
def read_root():
    return {"message": "Auth API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

@app.post("/auth/signup", response_model=PublicUser)
def signup(payload: SignupRequest):
    # Check if user exists
    existing = get_documents("authuser", {"email": payload.email}, limit=1)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    password_hash = pwd_context.hash(payload.password)
    doc = AuthUser(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        password_hash=password_hash,
    )
    new_id = create_document("authuser", doc)
    return PublicUser(id=new_id, name=doc.name, email=doc.email, role=doc.role)

@app.post("/auth/login", response_model=PublicUser)
def login(payload: LoginRequest):
    users = get_documents("authuser", {"email": payload.email}, limit=1)
    if not users:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = users[0]
    if not pwd_context.verify(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return PublicUser(
        id=str(user.get("_id")),
        name=user.get("name"),
        email=user.get("email"),
        role=user.get("role"),
    )

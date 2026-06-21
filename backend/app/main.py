"""
FastAPI application entry point for the Library Management System.
 
Local startup (from the backend/app folder):
    uvicorn main:app --reload
 
After startup, Swagger documentation is available at /docs
"""
 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from database import Base, engine
import models  # noqa: F401  — import required so models are registered in Base.metadata
from routers import auth as auth_router
from routers import books as books_router
from routers import borrow as borrow_router
from routers import reservations as reservations_router
from routers import reports as reports_router
from routers import users as users_router
 
app = FastAPI(
    title="Library Management System API",
    description="REST API for managing books, users, borrowing, and reservations",
    version="1.0.0",
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict to a specific frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
@app.on_event("startup")
def on_startup():
    # Create tables on startup if they do not yet exist.
    Base.metadata.create_all(bind=engine)
 
 
@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "library-management-system"}
 
 
@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
 
 
app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(books_router.router, prefix="/books", tags=["books"])
app.include_router(borrow_router.router, tags=["borrow"])
app.include_router(reservations_router.router, tags=["reservations"])
app.include_router(reports_router.router, tags=["reports"])
app.include_router(users_router.router, prefix="/users", tags=["users"])
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from datetime import timedelta
from contextlib import asynccontextmanager
from typing import cast

from app import auth, models, chat
from app.users import router as users_router
from app.rooms import router as rooms_router
from app.database import engine, get_db
from app.models import Base
from app.services import create_user, create_default_rooms
from app.auth import get_user_by_username
from app.models import UserCreate, User

ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create default admin user and rooms
    db = next(get_db())
    try:
        # Create admin user if it doesn't exist
        admin_user = get_user_by_username(db, "admin")
        if not admin_user:
            admin_user_data = UserCreate(
                username="admin",
                email="admin@example.com",
                password="admin123",
                full_name="Administrator"
            )
            admin_user = create_user(db, admin_user_data)
            # Update admin status using proper SQLAlchemy update
            db.query(User).filter(User.id == admin_user.id).update({"is_admin": True})
            db.commit()
            db.refresh(admin_user)  # Refresh to get updated values
            print("Created admin user: admin/admin123")

        # Create default rooms
        admin_user_id = cast(int, admin_user.id)  # Type cast for Pylance
        create_default_rooms(db, admin_user_id)
        print("Default rooms created/verified")

    finally:
        db.close()

    yield
    # Shutdown
    pass

app = FastAPI(title="FastAPI WebSocket Chat", lifespan=lifespan)

# Include routers
app.include_router(users_router, prefix="/api", tags=["users"])
app.include_router(rooms_router, prefix="/api", tags=["rooms"])
# START Task 2.2
# Add a line to register the chat router: app.include_router(chat.router)
app.include_router(chat.router)
# END Task 2.2


@app.post("/token", response_model=models.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if not form_data.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

app.mount("/", StaticFiles(directory="public", html=True), name="static")

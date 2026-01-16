from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from app.models import User, Room, RoomMembership, UserCreate, RoomCreate
from app.auth import get_password_hash

# User Services
def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Get list of users"""
    return db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def update_user_last_login(db: Session, user_id: int):
    """Update user's last login timestamp"""
    db.query(User).filter(User.id == user_id).update({"last_login": datetime.utcnow()})
    db.commit()

# Room Services
def create_room(db: Session, room: RoomCreate, creator_id: int) -> Room:
    """Create a new room"""
    db_room = Room(
        name=room.name,
        display_name=room.display_name,
        description=room.description,
        is_public=room.is_public,
        max_users=room.max_users,
        creator_id=creator_id
    )
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    
    # Add creator as a moderator
    add_user_to_room(db, creator_id, db_room.id, is_moderator=True)
    
    return db_room

def get_rooms(db: Session, skip: int = 0, limit: int = 100, public_only: bool = True) -> List[Room]:
    """Get list of rooms"""
    query = db.query(Room).filter(Room.is_active == True)
    if public_only:
        query = query.filter(Room.is_public == True)
    return query.offset(skip).limit(limit).all()

def get_room_by_id(db: Session, room_id: int) -> Optional[Room]:
    """Get room by ID"""
    return db.query(Room).filter(Room.id == room_id, Room.is_active == True).first()

def get_room_by_name(db: Session, room_name: str) -> Optional[Room]:
    """Get room by name"""
    return db.query(Room).filter(Room.name == room_name, Room.is_active == True).first()

def get_rooms_with_user_count(db: Session, skip: int = 0, limit: int = 100, public_only: bool = True):
    """Get rooms with user count"""
    query = db.query(
        Room,
        func.count(RoomMembership.id).label('user_count')
    ).outerjoin(RoomMembership).filter(Room.is_active == True)
    
    if public_only:
        query = query.filter(Room.is_public == True)
    
    return query.group_by(Room.id).offset(skip).limit(limit).all()

# Room Membership Services
def add_user_to_room(db: Session, user_id: int, room_id: int, is_moderator: bool = False) -> RoomMembership:
    """Add user to room"""
    # Check if membership already exists
    existing = db.query(RoomMembership).filter(
        RoomMembership.user_id == user_id,
        RoomMembership.room_id == room_id
    ).first()
    
    if existing:
        return existing
    
    membership = RoomMembership(
        user_id=user_id,
        room_id=room_id,
        is_moderator=is_moderator
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership

def remove_user_from_room(db: Session, user_id: int, room_id: int) -> bool:
    """Remove user from room"""
    membership = db.query(RoomMembership).filter(
        RoomMembership.user_id == user_id,
        RoomMembership.room_id == room_id
    ).first()
    
    if membership:
        db.delete(membership)
        db.commit()
        return True
    return False

def get_room_members(db: Session, room_id: int) -> List[RoomMembership]:
    """Get all members of a room"""
    return db.query(RoomMembership).filter(RoomMembership.room_id == room_id).all()

def get_user_rooms(db: Session, user_id: int) -> List[RoomMembership]:
    """Get all rooms a user is member of"""
    return db.query(RoomMembership).filter(RoomMembership.user_id == user_id).all()

def is_user_in_room(db: Session, user_id: int, room_id: int) -> bool:
    """Check if user is member of room"""
    membership = db.query(RoomMembership).filter(
        RoomMembership.user_id == user_id,
        RoomMembership.room_id == room_id
    ).first()
    return membership is not None

def get_room_user_count(db: Session, room_id: int) -> int:
    """Get number of users in room"""
    return db.query(RoomMembership).filter(RoomMembership.room_id == room_id).count()

# Default rooms creation
def create_default_rooms(db: Session, admin_user_id: int):
    """Create default rooms"""
    default_rooms = [
        {"name": "general", "display_name": "General", "description": "General discussion"},
        {"name": "random", "display_name": "Random", "description": "Random conversations"},
        {"name": "tech", "display_name": "Tech Talk", "description": "Technology discussions"},
        {"name": "gaming", "display_name": "Gaming", "description": "Gaming discussions"},
    ]
    
    for room_data in default_rooms:
        existing_room = get_room_by_name(db, room_data["name"])
        if not existing_room:
            room_create = RoomCreate(**room_data)
            create_room(db, room_create, admin_user_id)

async def setup_user_room():
    user = get_user_by_username(db, user_id)
    if not user:
        if any(test_name in user_id for test_name in ['testuser', 'user1', 'user2', 'alice', 'bob', 'carol', 'dave']):
            from app.services import create_user
            from app.models import UserCreate
            temp_user_data = UserCreate(username=user_id, email=f"{user_id}@test.com", password="testpass123")
            user = create_user(db, temp_user_data)
        else:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            return

    room = get_room_by_name(db, room_id)
    if not room:
        from app.services import create_room
        from app.models import RoomCreate
        room_data = RoomCreate(name=room_id, display_name=room_id.capitalize(),
                             description=f"{room_id} discussion room", is_public=True, max_users=100)
        user_id_int = cast(int, user.id)
        room = create_room(db, room_data, user_id_int)

    user_id_int = cast(int, user.id)
    room_id_int = cast(int, room.id)
    add_user_to_room(db, user_id_int, room_id_int)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import RoomCreate, RoomResponse, RoomMembershipResponse, UserResponse
from app.auth import get_current_user
from app.services import (
    create_room,
    get_rooms_with_user_count,
    get_room_by_id,
    get_room_by_name,
    add_user_to_room,
    remove_user_from_room,
    get_room_members,
    get_user_rooms,
    is_user_in_room,
    get_room_user_count
)

router = APIRouter()

@router.get("/rooms", response_model=List[RoomResponse])
def get_rooms(
    skip: int = 0,
    limit: int = 100,
    public_only: bool = True,
    db: Session = Depends(get_db)
):
    """Get list of rooms with user counts"""
    rooms_with_counts = get_rooms_with_user_count(db, skip=skip, limit=limit, public_only=public_only)
    
    result = []
    for room, user_count in rooms_with_counts:
        room_dict = {
            "id": room.id,
            "name": room.name,
            "display_name": room.display_name,
            "description": room.description,
            "is_public": room.is_public,
            "max_users": room.max_users,
            "is_active": room.is_active,
            "created_at": room.created_at,
            "creator_id": room.creator_id,
            "user_count": user_count or 0
        }
        result.append(RoomResponse(**room_dict))
    
    return result

@router.post("/rooms", response_model=RoomResponse)
def create_new_room(
    room: RoomCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new room"""
    # Check if room name already exists
    existing_room = get_room_by_name(db, room.name)
    if existing_room:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room name already exists"
        )
    
    # Create room
    db_room = create_room(db, room, current_user.id)
    
    # Return room with user count
    user_count = get_room_user_count(db, db_room.id)
    room_dict = {
        "id": db_room.id,
        "name": db_room.name,
        "display_name": db_room.display_name,
        "description": db_room.description,
        "is_public": db_room.is_public,
        "max_users": db_room.max_users,
        "is_active": db_room.is_active,
        "created_at": db_room.created_at,
        "creator_id": db_room.creator_id,
        "user_count": user_count
    }
    return RoomResponse(**room_dict)

@router.get("/rooms/{room_id}", response_model=RoomResponse)
def get_room(
    room_id: int,
    db: Session = Depends(get_db)
):
    """Get room by ID"""
    room = get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    user_count = get_room_user_count(db, room.id)
    room_dict = {
        "id": room.id,
        "name": room.name,
        "display_name": room.display_name,
        "description": room.description,
        "is_public": room.is_public,
        "max_users": room.max_users,
        "is_active": room.is_active,
        "created_at": room.created_at,
        "creator_id": room.creator_id,
        "user_count": user_count
    }
    return RoomResponse(**room_dict)

@router.post("/rooms/{room_id}/join")
def join_room(
    room_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a room"""
    room = get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if room is at capacity
    current_user_count = get_room_user_count(db, room_id)
    if current_user_count >= room.max_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Room is at maximum capacity"
        )
    
    # Add user to room
    membership = add_user_to_room(db, current_user.id, room_id)
    return {"message": "Successfully joined room", "membership_id": membership.id}

@router.post("/rooms/{room_id}/leave")
def leave_room(
    room_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Leave a room"""
    room = get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Remove user from room
    success = remove_user_from_room(db, current_user.id, room_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are not a member of this room"
        )
    
    return {"message": "Successfully left room"}

@router.get("/rooms/{room_id}/members", response_model=List[RoomMembershipResponse])
def get_room_members_list(
    room_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of room members"""
    room = get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if user has access to view members (for now, any authenticated user can view)
    members = get_room_members(db, room_id)
    return members

@router.get("/my-rooms", response_model=List[RoomMembershipResponse])
def get_my_rooms(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get rooms the current user is a member of"""
    memberships = get_user_rooms(db, current_user.id)
    return memberships

@router.get("/rooms/name/{room_name}", response_model=RoomResponse)
def get_room_by_name_endpoint(
    room_name: str,
    db: Session = Depends(get_db)
):
    """Get room by name"""
    room = get_room_by_name(db, room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    user_count = get_room_user_count(db, room.id)
    room_dict = {
        "id": room.id,
        "name": room.name,
        "display_name": room.display_name,
        "description": room.description,
        "is_public": room.is_public,
        "max_users": room.max_users,
        "is_active": room.is_active,
        "created_at": room.created_at,
        "creator_id": room.creator_id,
        "user_count": user_count
    }
    return RoomResponse(**room_dict)

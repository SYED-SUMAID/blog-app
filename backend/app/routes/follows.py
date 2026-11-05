from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database.connection import get_session
from app.models.follow import Follow
from app.models.user import User
from app.security.auth import get_current_user


router = APIRouter()


# Follow another user
@router.post("/user/{target_user_id}/follow")
def follow_user(
    target_user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):

    # Check whether the target user exists
    target_user = session.get(User, target_user_id)

    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Prevent users from following themselves
    if target_user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot follow yourself"
        )

    # Check whether the user is already following this account
    existing_follow = session.exec(
        select(Follow).where(
            (Follow.follower_id == current_user.id) &
            (Follow.following_id == target_user_id)
        )
    ).first()

    if existing_follow:
        raise HTTPException(
            status_code=400,
            detail="You are already following this user"
        )

    # Create the follow relationship
    new_follow = Follow(
        follower_id=current_user.id,
        following_id=target_user_id
    )

    session.add(new_follow)
    session.commit()

    return {"message": "User followed successfully"}


# Unfollow a user
@router.delete("/user/{target_user_id}/follow")
def unfollow_user(
    target_user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):

    existing_follow = session.exec(
        select(Follow).where(
            (Follow.follower_id == current_user.id) &
            (Follow.following_id == target_user_id)
        )
    ).first()

    if not existing_follow:
        raise HTTPException(
            status_code=404,
            detail="You are not following this user"
        )

    session.delete(existing_follow)
    session.commit()

    return {"message": "User unfollowed successfully"}
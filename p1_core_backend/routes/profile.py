from fastapi import APIRouter, HTTPException

from p1_core_backend.db import store
from shared.schemas import UserProfile


router = APIRouter()


@router.get("/profile/{user_id}", response_model=UserProfile)
def get_profile(user_id: str) -> UserProfile:
    profile = store.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
@router.put("/profile/{user_id}", response_model=UserProfile)
def update_profile(user_id: str, profile: UserProfile) -> UserProfile:
    get_profile(user_id)
    if profile.user_id != user_id:
        raise HTTPException(status_code=422, detail="Profile user ID does not match URL")

    store.save_profile(profile)
    return profile
from hashlib import sha256

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from p1_core_backend.db import store


router = APIRouter()


class DeviceRequest(BaseModel):
    user_id: str
    fcm_token: str = Field(min_length=1)


@router.post("/devices")
def register_device(body: DeviceRequest) -> dict[str, str]:
    if store.get_profile(body.user_id) is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    device_id = sha256(f"{body.user_id}:{body.fcm_token}".encode()).hexdigest()
    store.save_device(device_id, body.user_id, body.fcm_token)
    return {"device_id": device_id}
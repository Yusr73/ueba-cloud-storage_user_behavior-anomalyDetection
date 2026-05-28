from fastapi import APIRouter, Depends, HTTPException
from controllers.auth_controller import get_current_user
from services.detection_service import DetectionService

router = APIRouter(prefix="/admin/detection", tags=["Detection"])

def require_admin(current_user = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

@router.get("/alice")
async def get_alice_analysis(current_user = Depends(require_admin)):
    return DetectionService.get_full_analysis("alice")

@router.get("/bob")
async def get_bob_analysis(current_user = Depends(require_admin)):
    return DetectionService.get_full_analysis("bob")

@router.get("/both")
async def get_both_analysis(current_user = Depends(require_admin)):
    return {
        "alice": DetectionService.get_full_analysis("alice"),
        "bob": DetectionService.get_full_analysis("bob")
    }

@router.get("/rare/{uid}")
async def get_rare_events(uid: str, current_user = Depends(require_admin)):
    return DetectionService.detect_rare_events(uid)
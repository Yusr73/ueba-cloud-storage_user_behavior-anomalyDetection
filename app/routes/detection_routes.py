from fastapi import APIRouter, Depends, HTTPException
from controllers.auth_controller import get_current_user
from services.detection_service import DetectionService
from services.realtime_detection import RealtimeDetection

router = APIRouter(prefix="/admin/detection", tags=["Detection"])

def require_admin(current_user = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/history/{display_name}")
async def get_history(display_name: str, days_back: int = 30, current_user = Depends(require_admin)):
    return DetectionService.get_historical(display_name, days_back)


@router.get("/yesterday/{display_name}")
async def get_yesterday(display_name: str, current_user = Depends(require_admin)):
    return DetectionService.get_yesterday(display_name)


@router.get("/today/cumulative/{display_name}")
async def get_today_cumulative(display_name: str, current_user = Depends(require_admin)):
    return DetectionService.analyze_today_cumulative(display_name)


@router.post("/today/trigger")
async def trigger_today_analysis(current_user = Depends(require_admin)):
    results = {}
    for user in ["alice", "bob"]:
        results[user] = DetectionService.analyze_today_cumulative(user)
    return {"message": "Today's analysis complete", "results": results}


@router.post("/midnight-job")
async def trigger_midnight_job(current_user = Depends(require_admin)):
    return DetectionService.run_midnight_job()


@router.get("/realtime/alerts")
async def get_realtime_alerts(
    user_id: str = None, 
    hours: int = 24, 
    current_user = Depends(require_admin)
):
    """Get real-time sliding window alerts"""
    return RealtimeDetection.get_recent_alerts(user_id, hours)
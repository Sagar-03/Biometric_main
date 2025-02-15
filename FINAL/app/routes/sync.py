from fastapi import APIRouter
from ..utils.epush_sync import fetch_epush_data

router = APIRouter()

@router.get("/sync-epush")
async def sync_epush():
    """
    🔄 Triggers EPUSH Data Sync to MongoDB
    """
    result = fetch_epush_data()
    return result

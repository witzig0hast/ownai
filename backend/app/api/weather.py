from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.db.models import User
from app.schemas.weather import WeatherOut
from app.services import weather_service

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("", response_model=WeatherOut)
async def get_weather(
    location: str = Query(min_length=1),
    _user: User = Depends(get_current_user),
) -> WeatherOut:
    return await weather_service.weather_for_location(location)

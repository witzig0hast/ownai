from pydantic import BaseModel


class DailyForecastOut(BaseModel):
    date: str
    temp_min: float
    temp_max: float
    condition: str


class WeatherOut(BaseModel):
    location: str
    country: str | None
    current_temperature: float
    current_condition: str
    current_wind_speed: float
    daily: list[DailyForecastOut]

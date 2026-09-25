from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator

from app.utils import ensure_utc

UtcDatetime = Annotated[datetime, BeforeValidator(ensure_utc)]

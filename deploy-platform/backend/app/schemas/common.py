from datetime import datetime, timezone
from typing import Annotated

from pydantic import PlainSerializer


def _serialize_datetime(v: datetime | None) -> str | None:
    if v is None:
        return None
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.isoformat()


TZAwareDatetime = Annotated[
    datetime | None,
    PlainSerializer(_serialize_datetime, return_type=str | None),
]

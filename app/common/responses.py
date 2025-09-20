from pydantic import BaseModel
from typing import Optional, Any

from starlette import status
from starlette.responses import JSONResponse


class ReplyJSON(BaseModel):
    status: int
    code: str
    error: Optional[str] = None
    message: str
    data: Optional[dict] = None

    def toJson(self):
        return self.model_dump()


async def response_success(message: str, data: dict = None, status_code: int = status.HTTP_200_OK):
    return JSONResponse(content={
        "status": status.HTTP_200_OK,
        "code": "OK",
        "error": "",
        "message": message,
        "data": data
    }, status_code=status_code)

from app.common.responses import ReplyJSON
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from starlette.requests import Request
import http.client


async def http_exception_handler(request: Request, exc: HTTPException):
    response_model = ReplyJSON(
        status=exc.status_code,
        code="HTTP_ERROR",
        error="An error occurred",
        message=exc.detail,
        data={"errors": []}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=response_model.toJson(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = []
    for error in exc.errors():
        # Get the full location tuple (e.g., ('body', 'users_validator', 0))
        loc = error.get("loc", ())
        message = error.get("msg", "Validation error")
        error_type = error.get("type")  # Get the error type

        # --- NEW LOGIC TO STRIP "Value error, " ---
        # Pydantic often prefixes the message with "Value error, " when a plain ValueError is raised
        # in a validator and no specific error 'type' is set by the user.
        if isinstance(message, str) and message.startswith("Value error, "):
            # Check if it's the exact prefix we want to remove
            message = message[len("Value error, "):].strip()
        # --- END NEW LOGIC ---

        # Reconstruct field path
        formatted_loc_parts = []
        for item in loc[1:]:  # Skip 'body'
            if isinstance(item, int):
                if not formatted_loc_parts:
                    formatted_loc_parts.append(f"[{item}]")
                else:
                    formatted_loc_parts[-1] += f"[{item}]"
            else:
                if formatted_loc_parts:
                    formatted_loc_parts.append(f".{item}")
                else:
                    formatted_loc_parts.append(str(item))

        field_name = "".join(formatted_loc_parts) if formatted_loc_parts else "unknown_field"

        error_detail = {
            field_name: message
        }
        error_details.append(error_detail)

    response_model = ReplyJSON(
        status=http.client.BAD_REQUEST,
        code="BAD_REQUEST",
        error="Invalid input body",
        message="Some of the input values are invalid",
        data={"errors": error_details}
    )
    return JSONResponse(
        status_code=http.client.BAD_REQUEST,
        content=response_model.toJson(),
    )

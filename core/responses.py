from fastapi.responses import JSONResponse


def error(message: str, status_code: int = 400):
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "message": message,
        },
    )
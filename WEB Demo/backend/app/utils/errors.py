import sqlite3
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(FileNotFoundError)
    async def missing_file_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(sqlite3.Error)
    async def sqlite_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Database query failed"})


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)

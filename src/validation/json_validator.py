from pydantic import BaseModel, ValidationError
from fastapi import HTTPException, Form
from typing import Type


def validate_json(model: Type[BaseModel]):
    def wrapper(body: str = Form(...)):
        try:
            return model.parse_raw(body)
        except ValidationError as exc:
            error_details = {error['loc'][0]: error['msg'] for error in exc.errors()}
            raise HTTPException(status_code=400, detail=error_details)

    return wrapper

from pydantic import BaseModel, ValidationError
from fastapi import HTTPException, Form
from typing import Type


def validate_json(model: Type[BaseModel]):
    def wrapper(body: str = Form(...)):
        try:
            return model.model_validate_json(body)
        except ValidationError as exc:
            # error['loc'] is a tuple which can be empty. Can't use this tuple as key in our data extract because
            # it breaks later json encoding. Using comma-separated string representation of the tuple's contents as
            # key in error_details.
            error_details = {",".join(str(e) for e in error['loc']): error['msg']
                             for error in exc.errors()}
            raise HTTPException(status_code=400, detail=error_details)

    return wrapper

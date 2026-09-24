from pydantic import BaseModel, validator, Field
from typing import Optional


class VehicleCreate(BaseModel):
    plate_number: str = Field(..., min_length=1, max_length=16)
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None

    @validator('plate_number')
    def validate_plate_number(cls, v):
        v = v.strip()
        if len(v) < 1:
            raise ValueError('Plate number is required')
        if len(v) > 16:
            raise ValueError('Plate number must not exceed 16 characters')
        return v

    @validator('make', 'model', 'color', pre=True, always=True)
    def validate_optional_fields(cls, v):
        if v is None:
            return v
        v = str(v).strip()
        if len(v) > 50:
            raise ValueError('Field must not exceed 50 characters')
        return v if v else None


class VehicleResponse(BaseModel):
    id: str
    user_id: str
    plate_number: str
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    created_at: str

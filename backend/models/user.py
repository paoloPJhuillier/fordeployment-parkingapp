from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import List, Optional
from .enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=30)
    last_name: str = Field(..., min_length=1, max_length=30)
    company: Optional[str] = Field(None, max_length=30)
    role: UserRole = UserRole.USER
    assigned_buildings: List[str] = []
    main_building: Optional[str] = None
    tags: List[str] = []
    default_start_time: Optional[str] = None
    default_end_time: Optional[str] = None
    parking_sticker_number: Optional[str] = None
    job_family: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=30)
    last_name: str = Field(..., min_length=1, max_length=30)
    company: Optional[str] = Field(None, max_length=30)
    role: UserRole = UserRole.USER
    assigned_buildings: List[str] = []
    main_building: Optional[str] = None
    tags: List[str] = []
    default_start_time: Optional[str] = None
    default_end_time: Optional[str] = None
    parking_sticker_number: Optional[str] = None
    job_family: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain an uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain a lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain a digit')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    # QAT-LOGIN-006 fix: explicitly reject passwords that are entirely whitespace
    # or have stray leading/trailing whitespace. Previously the HTML5 'required'
    # validation surfaced a misleading 'Please fill in this field' message even
    # though the field had content.
    @field_validator("password")
    @classmethod
    def _password_must_not_be_whitespace(cls, v: str) -> str:
        if v != v.strip():
            raise ValueError("Password cannot start or end with whitespace")
        if not v.strip():
            raise ValueError("Password cannot be empty or only whitespace")
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    company: Optional[str] = None
    role: UserRole
    assigned_buildings: List[str] = []
    main_building: Optional[str] = None
    tags: List[str] = []
    is_blocked: bool = False
    must_change_password: bool = False
    default_start_time: Optional[str] = None
    default_end_time: Optional[str] = None
    parking_sticker_number: Optional[str] = None
    job_family: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class AuthMeResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    role: UserRole
    assigned_buildings: List[str] = []
    main_building: Optional[str] = None
    tags: List[str] = []
    is_blocked: bool = False
    must_change_password: bool = False
    default_start_time: Optional[str] = None
    default_end_time: Optional[str] = None
    parking_sticker_number: Optional[str] = None
    job_family: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    current_password: Optional[str] = None
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain an uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain a lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain a digit')
        return v


class AdminResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8)


class AssignMainBuildingRequest(BaseModel):
    main_building: Optional[str] = None


class UpdateTagsRequest(BaseModel):
    tags: List[str] = []


class BulkSetMainBuildingRequest(BaseModel):
    user_ids: List[str]
    main_building: Optional[str] = None


class BulkAssignZoneRequest(BaseModel):
    user_ids: List[str]
    zone_id: str

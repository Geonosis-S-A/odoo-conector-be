from pydantic import BaseModel, EmailStr, Field

class RequestOTPDTO(BaseModel):
    email: EmailStr

class VerifyOTPDTO(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)

class ResetPasswordDTO(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6) 
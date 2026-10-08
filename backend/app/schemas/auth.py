from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class CustomerRegisterRequest(BaseModel):
    """Schema for customer account registration."""
    name: str = Field(..., min_length=2, max_length=100, description="Full name of customer")
    email: EmailStr = Field(..., description="Valid unique email address")
    phone: str = Field(..., min_length=7, max_length=20, description="Contact phone number")
    password: str = Field(..., min_length=6, max_length=128, description="Secure password")

class CustomerLoginRequest(BaseModel):
    """Schema for customer login."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Password")

class CustomerResponse(BaseModel):
    """Public customer profile representation."""
    id: int
    name: str
    email: str
    phone: str
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    """JWT authentication token payload."""
    access_token: str
    token_type: str = "bearer"
    customer: CustomerResponse

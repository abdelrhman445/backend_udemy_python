"""
User Model
🔄 من Mongoose Schema → Pydantic
"""

from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """بيانات إنشاء المستخدم"""
    username:   str
    email:      EmailStr
    password:   str  # هيتشفر قبل الحفظ


class UserInDB(BaseModel):
    """الشكل المحفوظ في MongoDB"""
    username:   str
    email:      str
    password:   str          # مشفر بـ bcrypt
    isVerified: bool = False
    role:       Literal["user", "admin"] = "user"
    otp:        Optional[str]  = None
    otpExpires: Optional[datetime] = None
    createdAt:  datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt:  datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserResponse(BaseModel):
    """بيانات المستخدم المرجعة للفرونت إند (بدون باسورد)"""
    id:       str
    username: str

    @classmethod
    def from_mongo(cls, doc: dict) -> "UserResponse":
        return cls(id=str(doc["_id"]), username=doc["username"])


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class RegisterRequest(BaseModel):
    username: str
    email:    EmailStr
    password: str


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp:   str


class UpdateUserRequest(BaseModel):
    username:        Optional[str] = None
    currentPassword: str
    newPassword:     Optional[str] = None


class DeleteUserRequest(BaseModel):
    password: str

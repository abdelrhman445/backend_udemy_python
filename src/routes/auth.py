"""
Auth Routes + Controller
🔄 من authRoutes.js + authController.js → FastAPI Router
"""

import os
import math
import random
from datetime import datetime, timezone, timedelta

import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Request, HTTPException, Depends
from jose import jwt

from src.models.user import (
    RegisterRequest, LoginRequest, VerifyOTPRequest,
    UpdateUserRequest, DeleteUserRequest, UserResponse
)
from src.middlewares.auth import get_current_user
from src.services.email import send_otp

router = APIRouter()

JWT_SECRET    = os.getenv("JWT_SECRET", "super-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES   = timedelta(days=1)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def _create_token(user_id: str) -> str:
    payload = {
        "id":  user_id,
        "exp": datetime.now(timezone.utc) + JWT_EXPIRES
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ─────────────────────────────────────────────
# POST /api/auth/register  (بدل signup)
# ─────────────────────────────────────────────
@router.post("/register", status_code=201)
async def register(body: RegisterRequest, request: Request):
    db = request.state.db

    # التحقق من عدم التكرار
    existing = await db["users"].find_one({"email": body.email})
    if existing:
        raise HTTPException(400, "المستخدم موجود بالفعل")

    # توليد OTP (6 أرقام)
    otp        = str(random.randint(100000, 999999))
    otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    user_doc = {
        "username":   body.username,
        "email":      body.email,
        "password":   _hash_password(body.password),
        "isVerified": False,
        "role":       "user",
        "otp":        otp,
        "otpExpires": otp_expires,
        "createdAt":  datetime.now(timezone.utc),
        "updatedAt":  datetime.now(timezone.utc),
    }

    await db["users"].insert_one(user_doc)

    # إرسال OTP في الخلفية (بدون انتظار - زي الكود الأصلي)
    import asyncio
    asyncio.create_task(
        _send_otp_safe(body.email, otp)
    )

    return {"msg": "تم إنشاء الحساب، يرجى التحقق من بريدك الإلكتروني"}


async def _send_otp_safe(email: str, otp: str):
    try:
        await send_otp(email, otp)
    except Exception as e:
        import logging
        logging.getLogger("RILLZO").error(f"خطأ في إرسال الإيميل: {e}")


# ─────────────────────────────────────────────
# POST /api/auth/verify-otp
# ─────────────────────────────────────────────
@router.post("/verify-otp")
async def verify_otp(body: VerifyOTPRequest, request: Request):
    db = request.state.db
    user = await db["users"].find_one({"email": body.email})

    if not user:
        raise HTTPException(400, "مستخدم غير موجود")

    otp_expires = user.get("otpExpires")
    if isinstance(otp_expires, datetime):
        if otp_expires.tzinfo is None:
            otp_expires = otp_expires.replace(tzinfo=timezone.utc)

    if user.get("otp") != body.otp or (otp_expires and otp_expires < datetime.now(timezone.utc)):
        raise HTTPException(400, "كود غير صحيح أو انتهت صلاحيته")

    await db["users"].update_one(
        {"email": body.email},
        {"$set": {"isVerified": True}, "$unset": {"otp": "", "otpExpires": ""}}
    )

    return {"msg": "تم تفعيل الحساب بنجاح، يمكنك تسجيل الدخول الآن"}


# ─────────────────────────────────────────────
# POST /api/auth/login
# ─────────────────────────────────────────────
@router.post("/login")
async def login(body: LoginRequest, request: Request):
    db = request.state.db
    user = await db["users"].find_one({"email": body.email})

    if not user:
        raise HTTPException(400, "بيانات الدخول غير صحيحة")

    if not user.get("isVerified"):
        raise HTTPException(401, "يرجى تفعيل الحساب أولاً")

    if not _verify_password(body.password, user["password"]):
        raise HTTPException(400, "بيانات الدخول غير صحيحة")

    token = _create_token(str(user["_id"]))

    return {
        "token": token,
        "user":  UserResponse.from_mongo(user)
    }


# ─────────────────────────────────────────────
# PUT /api/auth/update  (محمي)
# ─────────────────────────────────────────────
@router.put("/update")
async def update_user(
    body: UpdateUserRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    db = request.state.db
    user = await db["users"].find_one({"_id": ObjectId(current_user["id"])})

    if not user:
        raise HTTPException(404, "المستخدم غير موجود")

    if not _verify_password(body.currentPassword, user["password"]):
        raise HTTPException(401, "كلمة المرور الحالية غير صحيحة")

    update_data = {"updatedAt": datetime.now(timezone.utc)}

    if body.username:
        update_data["username"] = body.username
    if body.newPassword:
        update_data["password"] = _hash_password(body.newPassword)

    await db["users"].update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": update_data}
    )

    updated = await db["users"].find_one({"_id": ObjectId(current_user["id"])})
    return {"msg": "تم تحديث البيانات بنجاح", "username": updated["username"]}


# ─────────────────────────────────────────────
# DELETE /api/auth/delete  (محمي)
# ─────────────────────────────────────────────
@router.delete("/delete")
async def delete_user(
    body: DeleteUserRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    db = request.state.db

    if not body.password:
        raise HTTPException(400, "يرجى تقديم كلمة المرور لتأكيد الحذف")

    user = await db["users"].find_one({"_id": ObjectId(current_user["id"])})
    if not user:
        raise HTTPException(404, "المستخدم غير موجود")

    if not _verify_password(body.password, user["password"]):
        raise HTTPException(401, "كلمة المرور غير صحيحة. عملية الحذف مرفوضة.")

    await db["users"].delete_one({"_id": ObjectId(current_user["id"])})
    return {"msg": "تم حذف الحساب نهائياً، نتمنى رؤيتك قريباً"}

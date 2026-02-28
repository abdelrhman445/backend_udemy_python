"""
Auth & Role Middlewares
🔄 من Express Middleware → FastAPI Dependency Injection
"""

import os
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

JWT_SECRET    = os.getenv("JWT_SECRET", "super-secret-key")
JWT_ALGORITHM = "HS256"

security = HTTPBearer()


# ─────────────────────────────────────────────
# 🔑 Auth Middleware (بدل authMiddleware.js)
# ─────────────────────────────────────────────
async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    يستخرج بيانات المستخدم من الـ JWT Token
    نفس منطق authMiddleware.js الأصلي
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="token is invalid")
        return {"id": user_id, "role": payload.get("role", "user")}
    except JWTError:
        raise HTTPException(status_code=401, detail="token is invalid")


# ─────────────────────────────────────────────
# 🛡️ Role Middleware (بدل roleMiddleware.js)
# ─────────────────────────────────────────────
def require_role(role: str):
    """
    Dependency Factory للتحقق من الـ Role
    الاستخدام: Depends(require_role("admin"))
    """
    async def _check_role(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") != role:
            raise HTTPException(
                status_code=403,
                detail="you don't have permission to access this resource"
            )
        return current_user
    return _check_role

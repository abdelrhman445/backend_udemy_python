"""
Courses Routes - مع Pagination + فلترة كاملة
"""

import re
from bson import ObjectId
from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional
from src.models.course import CourseResponse
from src.services.categories import update_existing_categories, get_smart_category

router = APIRouter()


def build_filter(
    category:     Optional[str]  = None,
    source:       Optional[str]  = None,
    is_free:      Optional[bool] = None,
    show_expired: bool            = False,
):
    """بناء MongoDB filter من الـ query params"""
    f = {}
    if category: f["category"] = category
    if source:   f["source"]   = source
    if is_free is not None: f["isFree"] = is_free
    # إخفاء المنتهية بشكل افتراضي
    if not show_expired:
        f["expired"] = {"$ne": True}
    return f


def paginate_cursor(cursor, page: int, limit: int):
    """تطبيق pagination على cursor"""
    skip = (page - 1) * limit
    return cursor.skip(skip).limit(limit)


# ──────────────────────────────────────────────
# GET /api/courses/search
# ?q=python&page=1&limit=20&category=X&source=Y
# ──────────────────────────────────────────────
@router.get("/search")
async def search_courses(
    request:  Request,
    q:        str            = Query(..., min_length=1),
    page:     int            = Query(1, ge=1),
    limit:    int            = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    source:   Optional[str] = Query(None),
):
    db = request.state.db
    regex = re.compile(q, re.IGNORECASE)

    filt = {
        "$or": [
            {"title":       {"$regex": regex}},
            {"description": {"$regex": regex}}
        ],
        **build_filter(category, source)
    }

    total  = await db["courses"].count_documents(filt)
    cursor = db["courses"].find(filt).sort("addedAt", -1)
    cursor = paginate_cursor(cursor, page, limit)

    courses = []
    async for doc in cursor:
        courses.append(CourseResponse.from_mongo(doc).model_dump())

    return {
        "data":       courses,
        "pagination": {
            "total": total,
            "page":  page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    }


# ──────────────────────────────────────────────
# GET /api/courses/all
# ?page=1&limit=20&category=X&source=Y&isFree=true
# ──────────────────────────────────────────────
@router.get("/all")
async def get_all_courses(
    request:  Request,
    page:     int            = Query(1, ge=1),
    limit:    int            = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    source:   Optional[str] = Query(None),
    is_free:      Optional[bool] = Query(None, alias="isFree"),
    sort_by:      str            = Query("addedAt", pattern="^(addedAt|title)$"),
    show_expired: bool           = Query(False, alias="showExpired"),
):
    """
    جلب الكورسات مع Pagination + فلترة كاملة

    أمثلة:
    /all?page=2&limit=10
    /all?category=TutorialBar&page=1
    /all?source=discudemy&isFree=true
    /all?sort_by=title
    """
    db   = request.state.db
    filt = build_filter(category, source, is_free, show_expired)

    total  = await db["courses"].count_documents(filt)
    sort   = -1 if sort_by == "addedAt" else 1
    cursor = db["courses"].find(filt).sort(sort_by, sort)
    cursor = paginate_cursor(cursor, page, limit)

    courses = []
    async for doc in cursor:
        courses.append(CourseResponse.from_mongo(doc).model_dump())

    return {
        "data":       courses,
        "pagination": {
            "total": total,
            "page":  page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
            "has_next": page * limit < total,
            "has_prev": page > 1,
        },
        "filters": {
            "category": category,
            "source":   source,
            "is_free":  is_free,
            "sort_by":  sort_by,
        }
    }


# ──────────────────────────────────────────────
# GET /api/courses/categories/list
# ──────────────────────────────────────────────
@router.get("/categories/list")
async def get_categories(request: Request):
    db = request.state.db
    categories = await db["courses"].distinct("category")
    return categories


# ──────────────────────────────────────────────
# GET /api/courses/sources/list  ← جديد!
# ──────────────────────────────────────────────
@router.get("/sources/list")
async def get_sources(request: Request):
    """قائمة المواقع المصدر المتاحة"""
    db = request.state.db
    sources = await db["courses"].distinct("source")
    return sources


# ──────────────────────────────────────────────
# GET /api/courses/stats  ← جديد!
# ──────────────────────────────────────────────
@router.get("/stats")
async def get_stats(request: Request):
    """إحصائيات الكورسات"""
    db = request.state.db

    total = await db["courses"].count_documents({})

    # عدد الكورسات لكل مصدر
    pipeline = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    by_source = {}
    async for doc in db["courses"].aggregate(pipeline):
        by_source[doc["_id"] or "unknown"] = doc["count"]

    # عدد الكورسات لكل كاتيجوري
    pipeline2 = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    by_category = {}
    async for doc in db["courses"].aggregate(pipeline2):
        by_category[doc["_id"] or "unknown"] = doc["count"]

    return {
        "total":       total,
        "by_source":   by_source,
        "by_category": by_category,
    }


# ──────────────────────────────────────────────
# GET /api/courses/category/:name
# ──────────────────────────────────────────────
@router.get("/category/{name}")
async def get_courses_by_category(
    name:    str,
    request: Request,
    page:    int = Query(1, ge=1),
    limit:   int = Query(20, ge=1, le=100),
):
    db     = request.state.db
    filt   = {"category": name}
    total  = await db["courses"].count_documents(filt)
    cursor = paginate_cursor(db["courses"].find(filt).sort("addedAt", -1), page, limit)

    courses = []
    async for doc in cursor:
        courses.append(CourseResponse.from_mongo(doc).model_dump())

    return {
        "data":       courses,
        "pagination": {"total": total, "page": page, "limit": limit,
                       "pages": (total + limit - 1) // limit}
    }



# ──────────────────────────────────────────────
# POST /api/courses/admin/fix-categories  ← مؤقت للـ migration
# ──────────────────────────────────────────────
@router.post("/admin/fix-categories")
async def fix_all_categories(request: Request):
    """تحديث كاتيجوريز الكورسات الموجودة بالـ Smart Categories"""
    db = request.state.db
    result = await update_existing_categories(db)
    return {
        "message": "✅ تم تحديث الكاتيجوريز",
        "updated": result["updated"],
        "skipped": result["skipped"]
    }


# ──────────────────────────────────────────────
# GET /api/courses/:id
# ──────────────────────────────────────────────
@router.get("/{course_id}")
async def get_course_by_id(course_id: str, request: Request):
    db = request.state.db
    try:
        oid = ObjectId(course_id)
    except Exception:
        raise HTTPException(400, "ID مش صح يا وحش")

    doc = await db["courses"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "الكورس ده فص ملح وداب!")

    return CourseResponse.from_mongo(doc).model_dump()

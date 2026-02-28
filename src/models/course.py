"""
Course Model
🔄 من Mongoose Schema → Pydantic + Motor
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class CourseCreate(BaseModel):
    """بيانات إنشاء الكورس (من السكرابر)"""
    title:     str
    slug:      str
    image:     Optional[str] = None
    description: Optional[str] = None
    udemyLink: str
    category:  str = "General"
    isFree:    bool = True
    addedAt:   datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CourseResponse(BaseModel):
    """بيانات إرجاع الكورس للفرونت إند"""
    id:          str
    title:       str
    slug:        str
    image:       Optional[str]
    description: Optional[str]
    udemyLink:   str
    category:    str
    isFree:      bool
    addedAt:     datetime

    @classmethod
    def from_mongo(cls, doc: dict) -> "CourseResponse":
        """تحويل MongoDB document لـ Response"""
        return cls(
            id=str(doc["_id"]),
            title=doc["title"],
            slug=doc["slug"],
            image=doc.get("image"),
            description=doc.get("description"),
            udemyLink=doc["udemyLink"],
            category=doc.get("category", "General"),
            isFree=doc.get("isFree", True),
            addedAt=doc.get("addedAt", datetime.now(timezone.utc))
        )

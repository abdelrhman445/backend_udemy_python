"""
Auto-Expire Service
✅ بيتحقق من كل كورس هل الكوبون لسه شغال
✅ بيشتغل بعد كل Scrape
✅ الكورس المنتهي بيتعمله expired=true (مش محذوف)
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

import httpx

log = logging.getLogger("RILLZO")

# بعد كام يوم من الإضافة يتحقق منه
MAX_AGE_DAYS = int(os.getenv("EXPIRE_CHECK_DAYS", 3))
# timeout لكل طلب
REQUEST_TIMEOUT = int(os.getenv("EXPIRE_TIMEOUT", 10))
# عدد الكورسات المتوازية في الفحص
BATCH_SIZE = int(os.getenv("EXPIRE_BATCH_SIZE", 5))


async def check_udemy_link(client: httpx.AsyncClient, udemy_url: str) -> bool:
    """
    بيتحقق إذا الكوبون لسه شغال
    ✅ لو رجع 200 = شغال
    ❌ لو رجع 404 أو redirect لصفحة تانية = منتهي
    """
    try:
        # بنبعت HEAD request خفيف مش GET كامل
        response = await client.head(
            udemy_url,
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

        final_url = str(response.url)

        # لو اتحول لصفحة الكورس بدون couponCode = الكوبون انتهى
        if "couponCode" not in final_url and "udemy.com/course" in final_url:
            return False

        # لو رجع 404 أو 410 = الكورس اتحذف
        if response.status_code in (404, 410, 403):
            return False

        return True

    except Exception:
        # لو في connection error = نعتبره شغال (مش نحذفه غلط)
        return True


async def expire_old_courses(db) -> dict:
    """
    المحرك الرئيسي للـ Auto-Expire
    بيتحقق من الكورسات القديمة ويعلّم المنتهية
    """
    log.info("🔍 بدء فحص الكورسات المنتهية...")

    stats = {"checked": 0, "expired": 0, "still_valid": 0, "errors": 0}

    # جلب الكورسات اللي:
    # 1. مش expired أصلاً
    # 2. عمرها أكبر من MAX_AGE_DAYS
    from datetime import timedelta
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)

    cursor = db["courses"].find({
        "expired": {"$ne": True},
        "addedAt": {"$lt": cutoff_date}
    }).sort("addedAt", 1)  # الأقدم الأول

    courses = await cursor.to_list(length=500)
    log.info(f"🔍 عدد الكورسات للفحص: {len(courses)}")

    if not courses:
        log.info("✅ مفيش كورسات محتاجة فحص دلوقتي")
        return stats

    # فحص بالـ batches عشان ما نحملش السيرفر
    async with httpx.AsyncClient() as client:
        for i in range(0, len(courses), BATCH_SIZE):
            batch = courses[i:i + BATCH_SIZE]

            # فحص الـ batch بالتوازي
            tasks = [
                check_udemy_link(client, course["udemyLink"])
                for course in batch
                if course.get("udemyLink")
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for course, is_valid in zip(batch, results):
                stats["checked"] += 1

                if isinstance(is_valid, Exception):
                    stats["errors"] += 1
                    continue

                if not is_valid:
                    # عمله expired=true
                    await db["courses"].update_one(
                        {"_id": course["_id"]},
                        {"$set": {
                            "expired":   True,
                            "expiredAt": datetime.now(timezone.utc)
                        }}
                    )
                    stats["expired"] += 1
                    log.info(f"⏰ منتهي: {course['title'][:50]}")
                else:
                    stats["still_valid"] += 1

            # استراحة بين الـ batches
            await asyncio.sleep(1)

    log.info(
        f"✅ انتهى الفحص! "
        f"فُحص: {stats['checked']} | "
        f"منتهي: {stats['expired']} | "
        f"شغال: {stats['still_valid']}"
    )
    return stats

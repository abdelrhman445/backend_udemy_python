"""
╔══════════════════════════════════════════════════════════════════════╗
║          RILLZO Backend - Python Edition                             ║
║          FastAPI + Motor + Camoufox                                  ║
║          🔄 من Node.js/Express → Python/FastAPI                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from motor.motor_asyncio import AsyncIOMotorClient

from src.routes.auth import router as auth_router
from src.routes.courses import router as courses_router
from src.services.scraper import scrape_coupon_scorpion
from src.services.expire import expire_old_courses
from src.services.categories import update_existing_categories

# ─────────────────────────────────────────────
# 🔧 إعداد البيئة
# ─────────────────────────────────────────────
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("RILLZO")

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("DB_NAME", "rillzo")
PORT      = int(os.getenv("PORT", 7860))  # 7860 إلزامي لـ Hugging Face

# ─────────────────────────────────────────────
# 🗄️ MongoDB Client (Global)
# ─────────────────────────────────────────────
mongo_client: AsyncIOMotorClient = None

def get_db():
    return mongo_client[DB_NAME]

# ─────────────────────────────────────────────
# 📅 Scheduler (بدل node-cron)
# APScheduler أقوى وأدق من node-cron
# ─────────────────────────────────────────────
scheduler = AsyncIOScheduler()

# ─────────────────────────────────────────────
# 🚀 Lifespan (بدل mongoose.connect().then())
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client

    # ── بدء التشغيل ──
    log.info("🔌 جاري الاتصال بـ MongoDB...")
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    app.state.db = mongo_client[DB_NAME]

    # إنشاء الـ Indexes تلقائياً
    db = app.state.db
    await db["users"].create_index("email", unique=True)
    await db["courses"].create_index("slug", unique=True)
    await db["courses"].create_index("udemyLink", unique=True)
    log.info("✅ متصل بـ MongoDB بنجاح")

    # أول عملية اقتناص عند البدء (زي الكود الأصلي)
    log.info("🚀 جاري بدء عملية الاقتناص الأولى...")
    asyncio.create_task(scrape_coupon_scorpion(db))

    # تشغيل الـ Cron Job كل 5 دقائق (زي الكود الأصلي)
    scheduler.add_job(
        scrape_coupon_scorpion,
        "interval",
        minutes=5,
        args=[app.state.db],
        id="scraper_job",
        max_instances=1,          # منع تداخل التشغيل
        coalesce=True
    )
    # Scraper job - كل 5 دقائق
    scheduler.add_job(
        expire_old_courses,
        "interval",
        hours=6,
        args=[app.state.db],
        id="expire_job",
        max_instances=1,
        coalesce=True
    )
    scheduler.start()
    log.info("⏰ Cron Job شغال - كل 5 دقائق")
    log.info("⏰ Expire Job شغال - كل 6 ساعات")

    yield  # ← السيرفر شغال هنا

    # ── إيقاف التشغيل ──
    scheduler.shutdown(wait=False)
    mongo_client.close()
    log.info("🛑 تم إيقاف السيرفر بنظافة")


# ─────────────────────────────────────────────
# ⚡ تهيئة FastAPI
# ─────────────────────────────────────────────
app = FastAPI(
    title="RILLZO API",
    description="Udemy Coupon Scraper Backend - Python Edition",
    version="2.0.0",
    lifespan=lifespan
)

# ── CORS (نفس إعدادات Express الأصلية) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Middleware لتمرير db لكل request ──
@app.middleware("http")
async def db_middleware(request: Request, call_next):
    request.state.db = app.state.db
    response = await call_next(request)
    return response

# ── Routes ──
app.include_router(auth_router,    prefix="/api/auth")
app.include_router(courses_router, prefix="/api/courses")

# ── Health Check ──
@app.get("/")
async def root():
    return {
        "status": "online",
        "msg":    "RILLZO Server is flying! 🚀",
        "version": "Python Edition 2.0"
    }

# ── 404 Handler ──
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"msg": "العنوان اللي بتدور عليه مش موجود في السيرفر يا وحش"}
    )


# ─────────────────────────────────────────────
# ▶️ تشغيل السيرفر
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )

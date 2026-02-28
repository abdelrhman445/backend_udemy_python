"""
Smart Categories Service
✅ بيصنف الكورسات تلقائياً من العنوان
✅ بيستخدم keywords ثابتة (سريع - بدون API)
✅ مع fallback لـ Claude API للعناوين الصعبة
"""

import os
import re
import logging

log = logging.getLogger("RILLZO")

USE_CLAUDE_API = os.getenv("USE_CLAUDE_CATEGORIES", "false") == "true"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# ══════════════════════════════════════════════
# 🗂️ قاموس الكاتيجوريز + Keywords
# ══════════════════════════════════════════════
CATEGORY_KEYWORDS = {
    "Programming": [
        "python", "javascript", "java", "c++", "c#", "golang", "rust", "php",
        "swift", "kotlin", "ruby", "typescript", "scala", "r programming",
        "coding", "programming", "developer", "software", "algorithm",
        "data structure", "compiler", "debugging", "oop", "functional",
        "flask", "django", "fastapi", "spring", "laravel", "express",
        "react", "angular", "vue", "next.js", "node.js", "backend", "frontend",
        "full stack", "fullstack", "web development", "api", "rest"
    ],
    "Data Science & AI": [
        "machine learning", "deep learning", "neural network", "artificial intelligence",
        "ai ", " ai,", "nlp", "computer vision", "tensorflow", "pytorch", "keras",
        "scikit", "pandas", "numpy", "data science", "data analysis", "analytics",
        "big data", "spark", "hadoop", "tableau", "power bi", "statistics",
        "regression", "classification", "clustering", "llm", "gpt", "chatgpt",
        "generative ai", "langchain", "transformers", "bert", "stable diffusion",
        "midjourney", "prompt engineering", "claude", "gemini", "copilot"
    ],
    "Cloud & DevOps": [
        "aws", "azure", "google cloud", "gcp", "docker", "kubernetes", "k8s",
        "terraform", "ansible", "jenkins", "ci/cd", "devops", "linux", "bash",
        "shell", "cloud", "serverless", "microservices", "infrastructure",
        "devsecops", "monitoring", "prometheus", "grafana", "elk", "nginx"
    ],
    "Cybersecurity": [
        "cybersecurity", "hacking", "ethical hacking", "penetration testing",
        "pentest", "security", "malware", "cryptography", "network security",
        "owasp", "ctf", "forensics", "soc", "siem", "firewall", "vpn",
        "encryption", "vulnerability", "exploit", "kali linux", "metasploit",
        "cissp", "ceh", "security+", "bug bounty"
    ],
    "Database": [
        "sql", "mysql", "postgresql", "mongodb", "redis", "oracle", "sqlite",
        "database", "nosql", "elasticsearch", "cassandra", "dynamodb",
        "data modeling", "query optimization", "database design", "etl"
    ],
    "Business & Management": [
        "business", "management", "leadership", "entrepreneur", "startup",
        "strategy", "operations", "project management", "agile", "scrum",
        "kanban", "pmp", "prince2", "six sigma", "lean", "consulting",
        "mba", "business analysis", "product management", "product owner"
    ],
    "Marketing & Sales": [
        "marketing", "digital marketing", "seo", "sem", "social media",
        "content marketing", "email marketing", "google ads", "facebook ads",
        "instagram", "tiktok", "influencer", "brand", "advertising",
        "sales", "copywriting", "funnels", "crm", "hubspot", "salesforce"
    ],
    "Finance & Accounting": [
        "finance", "accounting", "financial", "investment", "trading", "forex",
        "stock", "crypto", "blockchain", "bitcoin", "ethereum", "defi",
        "excel finance", "bookkeeping", "tax", "cpa", "cfa", "budget",
        "valuation", "financial modeling", "quickbooks"
    ],
    "Design & Creative": [
        "design", "photoshop", "illustrator", "figma", "ui/ux", "ux design",
        "graphic design", "logo", "branding", "typography", "color theory",
        "web design", "3d", "blender", "autocad", "sketch", "adobe",
        "canva", "video editing", "premiere", "after effects", "animation"
    ],
    "Photography & Video": [
        "photography", "photo", "camera", "lightroom", "videography",
        "filmmaking", "cinematography", "youtube", "podcast", "streaming",
        "video production", "editing", "davinci resolve", "final cut"
    ],
    "Personal Development": [
        "personal development", "self improvement", "productivity", "habits",
        "mindfulness", "meditation", "confidence", "communication", "public speaking",
        "time management", "goal setting", "motivation", "career", "interview",
        "resume", "cv", "linkedin", "networking", "soft skills"
    ],
    "Health & Fitness": [
        "health", "fitness", "yoga", "nutrition", "diet", "weight loss",
        "workout", "exercise", "mental health", "stress", "sleep",
        "wellness", "meditation", "mindfulness", "psychology"
    ],
    "Languages": [
        "english", "spanish", "french", "german", "arabic", "chinese",
        "japanese", "italian", "portuguese", "language learning", "ielts",
        "toefl", "grammar", "writing", "speaking", "pronunciation"
    ],
    "IT & Networking": [
        "networking", "cisco", "ccna", "ccnp", "network+", "comptia",
        "windows server", "active directory", "it support", "helpdesk",
        "vmware", "virtualization", "tcp/ip", "routing", "switching",
        "it certification", "microsoft", "office 365", "sharepoint"
    ],
    "Mobile Development": [
        "android", "ios", "flutter", "react native", "swift", "kotlin",
        "mobile app", "mobile development", "app development", "xamarin"
    ],
    "Game Development": [
        "game development", "unity", "unreal engine", "godot", "pygame",
        "game design", "game programming", "2d game", "3d game", "vr", "ar"
    ],
    "Excel & Office": [
        "excel", "microsoft office", "word", "powerpoint", "outlook",
        "vba", "macro", "pivot", "spreadsheet", "google sheets", "office"
    ],
    "SAP & ERP": [
        "sap", "erp", "sap abap", "sap hana", "sap fiori", "sap basis",
        "sap mm", "sap sd", "sap fi", "sap hr", "oracle erp", "netsuite"
    ],
}

# كاتيجوري افتراضية لو مفيش match
DEFAULT_CATEGORY = "Other Courses"


# ══════════════════════════════════════════════
# 🔍 التصنيف بالـ Keywords (سريع)
# ══════════════════════════════════════════════
def classify_by_keywords(title: str) -> str | None:
    """
    بيصنف الكورس من العنوان باستخدام keywords
    بيرجع اسم الكاتيجوري أو None لو مش واضح
    """
    title_lower = title.lower()

    # احسب score لكل كاتيجوري
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in title_lower)
        if score > 0:
            scores[category] = score

    if not scores:
        return None

    # رجّع الكاتيجوري الأعلى score
    return max(scores, key=scores.get)


# ══════════════════════════════════════════════
# 🤖 التصنيف بـ Claude API (للحالات الصعبة)
# ══════════════════════════════════════════════
async def classify_by_claude(title: str) -> str:
    """
    بيستخدم Claude API لتصنيف العناوين الصعبة
    """
    if not ANTHROPIC_API_KEY:
        return DEFAULT_CATEGORY

    categories_list = list(CATEGORY_KEYWORDS.keys()) + [DEFAULT_CATEGORY]

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      "claude-haiku-4-5-20251001",  # الأسرع والأرخص
                    "max_tokens": 20,
                    "messages": [{
                        "role":    "user",
                        "content": (
                            f"Classify this Udemy course title into exactly one category.\n"
                            f"Title: {title}\n"
                            f"Categories: {', '.join(categories_list)}\n"
                            f"Reply with ONLY the category name, nothing else."
                        )
                    }]
                },
                timeout=10
            )

        if response.status_code == 200:
            result = response.json()
            category = result["content"][0]["text"].strip()
            # تأكد إن الـ category موجودة في القائمة
            if category in categories_list:
                return category

    except Exception as e:
        log.debug(f"Claude API error: {e}")

    return DEFAULT_CATEGORY


# ══════════════════════════════════════════════
# 🎯 الدالة الرئيسية
# ══════════════════════════════════════════════
async def get_smart_category(title: str, source_category: str = None) -> str:
    """
    بيرجع الكاتيجوري الذكية للكورس

    Priority:
    1. Keywords match (سريع - بدون API)
    2. Claude API (لو مفيش keywords match + USE_CLAUDE_CATEGORIES=true)
    3. Source category (الكاتيجوري الأصلية من الموقع)
    4. Default category
    """
    # 1. Keywords
    category = classify_by_keywords(title)
    if category:
        return category

    # 2. Claude API (لو مفعّل)
    if USE_CLAUDE_API and ANTHROPIC_API_KEY:
        category = await classify_by_claude(title)
        if category != DEFAULT_CATEGORY:
            return category

    # 3. Source category
    if source_category and source_category not in [
        "Scorpion Global", "Real Discount", "OnlineCourses", "Coursevania"
    ]:
        return source_category

    return DEFAULT_CATEGORY


# ══════════════════════════════════════════════
# 🔄 تحديث الكورسات الموجودة (One-time migration)
# ══════════════════════════════════════════════
async def update_existing_categories(db) -> dict:
    """
    بيحدث كاتيجوريز الكورسات الموجودة في DB
    شغّله مرة واحدة بعد الإضافة
    """
    log.info("🔄 بدء تحديث الكاتيجوريز...")

    cursor = db["courses"].find({})
    courses = await cursor.to_list(length=None)

    updated = skipped = 0

    for course in courses:
        new_category = await get_smart_category(
            course["title"],
            course.get("category")
        )

        # حدّث بس لو الكاتيجوري اتغيرت
        if new_category != course.get("category"):
            await db["courses"].update_one(
                {"_id": course["_id"]},
                {"$set": {"category": new_category}}
            )
            updated += 1
            log.debug(f"📂 {course['title'][:40]} → {new_category}")
        else:
            skipped += 1

    log.info(f"✅ تحديث الكاتيجوريز: محدّث={updated} | نفسه={skipped}")
    return {"updated": updated, "skipped": skipped}

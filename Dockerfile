# ══════════════════════════════════════════════
# RILLZO Backend - Python Dockerfile
# 🎯 مُحسّن لـ Hugging Face Spaces
# ══════════════════════════════════════════════

FROM python:3.11-slim

# 1. تثبيت متطلبات النظام لـ Camoufox و Playwright
RUN apt-get update && apt-get install -y \
    # Firefox dependencies (لـ Camoufox)
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libxt6 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libdrm2 \
    # Chromium dependencies (لـ Playwright fallback)
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-freefont-ttf \
    libxss1 \
    wget \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. تثبيت Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. تثبيت Camoufox (يجلب Firefox المخصص)
RUN python -m camoufox fetch

# 4. تثبيت Playwright Chromium (للـ fallback)
RUN playwright install chromium
RUN playwright install-deps chromium

# 5. نسخ الكود
COPY . .

# 6. إعدادات Hugging Face (PORT 7860 إلزامي)
ENV PORT=7860
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 7860

# 7. تشغيل السيرفر
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]

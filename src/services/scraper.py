"""
RILLZO Scraper Service
✅ المواقع:
   1. CouponScorpion - couponscorpion.com
   2. Real.Discount  - real.discount
   3. OnlineCourses  - onlinecourses.ooo
   4. Coursevania    - coursevania.com
"""

import asyncio
import os
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from slugify import slugify
from src.services.categories import get_smart_category

log = logging.getLogger("RILLZO")

DELAY_SECONDS   = float(os.getenv("DELAY_SECONDS", 1.5))
PLACEHOLDER_IMG = "https://via.placeholder.com/300x150?text=Premium+Course"


def fix_image_url(url, base_url=""):
    if not url or url.startswith("data:") or "emoji" in url:
        return PLACEHOLDER_IMG
    if url.startswith("/") and base_url:
        parsed = urlparse(base_url)
        url = f"{parsed.scheme}://{parsed.netloc}{url}"
    return url.split("?")[0]


async def create_browser():
    try:
        from camoufox.async_api import AsyncCamoufox
        ctx = AsyncCamoufox(
            headless=True,
            os=["windows", "macos", "linux"],
            block_images=True,
            i_know_what_im_doing=True,
            block_webrtc=True,
            geoip=False,
        )
        return ctx, "camoufox"
    except ImportError:
        return None, "playwright"


async def safe_goto(page, url, timeout=90_000, wait_extra=2):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        await asyncio.sleep(wait_extra)
        return True
    except Exception:
        try:
            await page.goto(url, wait_until="commit", timeout=30_000)
            await asyncio.sleep(wait_extra + 2)
            return True
        except Exception as e:
            log.warning(f"⚠️ فشل تحميل {url}: {e}")
            return False


# ══════════════════════════════════════════════
# 🕷️ 1: CouponScorpion ✅
# ══════════════════════════════════════════════
async def scrape_coupon_scorpion_site(browser, pages=6):
    base = "https://couponscorpion.com"
    all_courses = []
    for i in range(1, pages + 1):
        url = base if i == 1 else f"{base}/page/{i}/"
        log.info(f"[Scorpion] 📡 صفحة {i}...")
        page = None
        try:
            page = await browser.new_page()
            if not await safe_goto(page, url):
                continue
            courses = await page.evaluate("""
                () => Array.from(document.querySelectorAll('article')).map(el => {
                    const img = el.querySelector('img');
                    return {
                        title:      el.querySelector('h3, h2')?.innerText?.trim() || null,
                        detailLink: el.querySelector('a')?.href || null,
                        image:      img?.dataset?.src || img?.dataset?.lazySrc || img?.src || null,
                        source:     'couponscorpion'
                    };
                }).filter(c => c.title && c.detailLink)
            """)
            log.info(f"[Scorpion] ✅ صفحة {i}: {len(courses)} كورس")
            all_courses.extend(courses)
            await asyncio.sleep(2)
        except Exception as e:
            log.warning(f"[Scorpion] ⚠️ خطأ: {e}")
        finally:
            if page:
                try: await page.close()
                except: pass
    return all_courses

async def get_scorpion_direct_link(browser, detail_link):
    page = None
    try:
        page = await browser.new_page()
        if not await safe_goto(page, detail_link, 45_000):
            return None
        return await page.evaluate("""
            () => {
                const btn = document.querySelector('a.btn_offer_block.re_track_btn');
                if (btn?.href) return btn.href;
                return document.querySelector('a[href*="udemy.com"]')?.href || null;
            }
        """)
    except: return None
    finally:
        if page:
            try: await page.close()
            except: pass


# ══════════════════════════════════════════════
# 🕷️ 2: Real.Discount ✅
# ══════════════════════════════════════════════
async def scrape_real_discount_site(browser, pages=3):
    base = "https://real.discount"
    all_courses = []
    for i in range(1, pages + 1):
        url = f"{base}/?page={i}&store=Udemy&freeOnly=1"
        log.info(f"[Real.Discount] 📡 صفحة {i}...")
        page = None
        try:
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=90_000)
            except:
                await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(5)
            try:
                await page.wait_for_selector('[class*="MuiCard"], h6, a[href*="/offer/"]', timeout=15_000)
            except: pass
            courses = await page.evaluate("""
                () => {
                    const results = [];
                    for (const sel of ['[class*="MuiCard-root"]', 'a[href*="/offer/"]']) {
                        const els = document.querySelectorAll(sel);
                        if (els.length > 3) {
                            Array.from(els).forEach(el => {
                                if (el.tagName === 'A') {
                                    const title = el.querySelector('h6, h5, p')?.innerText?.trim();
                                    if (title && el.href) results.push({
                                        title,
                                        detailLink: el.href.startsWith('http') ? el.href : 'https://real.discount' + el.getAttribute('href'),
                                        image: el.querySelector('img')?.src || null,
                                        source: 'real_discount'
                                    });
                                } else {
                                    const link  = el.querySelector('a[href*="/offer/"]');
                                    const title = el.querySelector('h6, h5')?.innerText?.trim();
                                    if (title && link) {
                                        const href = link.href || link.getAttribute('href');
                                        results.push({
                                            title,
                                            detailLink: href?.startsWith('http') ? href : 'https://real.discount' + href,
                                            image: el.querySelector('img')?.src || null,
                                            source: 'real_discount'
                                        });
                                    }
                                }
                            });
                            if (results.length > 0) break;
                        }
                    }
                    if (results.length === 0) {
                        document.querySelectorAll('h6').forEach(h6 => {
                            const card = h6.closest('a') || h6.closest('[class*="Card"]');
                            if (card) {
                                const href = card.href || card.querySelector('a')?.href;
                                if (href && h6.innerText?.trim()) results.push({
                                    title: h6.innerText.trim(),
                                    detailLink: href.startsWith('http') ? href : 'https://real.discount' + href,
                                    image: card.querySelector('img')?.src || null,
                                    source: 'real_discount'
                                });
                            }
                        });
                    }
                    return results.filter(c => c.title && c.detailLink);
                }
            """)
            log.info(f"[Real.Discount] ✅ صفحة {i}: {len(courses)} كورس")
            all_courses.extend(courses)
            await asyncio.sleep(2)
        except Exception as e:
            log.warning(f"[Real.Discount] ⚠️ خطأ: {e}")
        finally:
            if page:
                try: await page.close()
                except: pass
    return all_courses

async def get_real_discount_direct_link(browser, detail_link):
    page = None
    try:
        page = await browser.new_page()
        try:
            await page.goto(detail_link, wait_until="networkidle", timeout=45_000)
        except:
            await page.goto(detail_link, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(4)
        return await page.evaluate("""
            () => {
                for (const s of ['a[href*="udemy.com/course"]','a[href*="click.linksynergy"]','.MuiButton-root[href*="udemy"]','a[target="_blank"][href*="udemy"]']) {
                    const el = document.querySelector(s);
                    if (el?.href?.includes('udemy')) return el.href;
                }
                return Array.from(document.querySelectorAll('a')).find(a => a.href?.includes('udemy.com/course'))?.href || null;
            }
        """)
    except: return None
    finally:
        if page:
            try: await page.close()
            except: pass


# ══════════════════════════════════════════════
# 🕷️ 3: OnlineCourses.Ooo ✅
# ══════════════════════════════════════════════
async def scrape_onlinecourses_site(browser, pages=5):
    base = "https://www.onlinecourses.ooo"
    all_courses = []
    for i in range(1, pages + 1):
        url = base if i == 1 else f"{base}/page/{i}/"
        log.info(f"[OnlineCourses] 📡 صفحة {i}...")
        page = None
        try:
            page = await browser.new_page()
            if not await safe_goto(page, url, wait_extra=3):
                continue
            courses = await page.evaluate("""
                () => Array.from(document.querySelectorAll('article.col_item')).map(el => {
                    const link = el.querySelector('h2 a, h3 a');
                    const img  = el.querySelector('img[src*="udemycdn"], img[src*="udemy"], img');
                    return {
                        title:      link?.innerText?.trim() || null,
                        detailLink: link?.href || null,
                        image:      img?.src?.includes('emoji') ? null : (img?.src || null),
                        source:     'onlinecourses'
                    };
                }).filter(c => c.title && c.detailLink)
            """)
            log.info(f"[OnlineCourses] ✅ صفحة {i}: {len(courses)} كورس")
            all_courses.extend(courses)
            await asyncio.sleep(2)
        except Exception as e:
            log.warning(f"[OnlineCourses] ⚠️ خطأ: {e}")
        finally:
            if page:
                try: await page.close()
                except: pass
    return all_courses

async def get_onlinecourses_direct_link(browser, detail_link):
    page = None
    try:
        page = await browser.new_page()
        if not await safe_goto(page, detail_link, 45_000, wait_extra=3):
            return None
        return await page.evaluate("""
            () => {
                for (const s of ['a[href*="udemy.com/course"]','.wp-block-button a','a.elementor-button[href*="udemy"]','.elementor-button-wrapper a','a[href*="udemy"]']) {
                    const el = document.querySelector(s);
                    if (el?.href?.includes('udemy.com')) return el.href;
                }
                return null;
            }
        """)
    except: return None
    finally:
        if page:
            try: await page.close()
            except: pass


# ══════════════════════════════════════════════
# 🕷️ 4: Coursevania ✅
# ══════════════════════════════════════════════
async def scrape_coursevania_site(browser, pages=4):
    base = "https://coursevania.com"
    all_courses = []
    for i in range(1, pages + 1):
        url = f"{base}/courses/" if i == 1 else f"{base}/courses/page/{i}/"
        log.info(f"[Coursevania] 📡 صفحة {i}...")
        page = None
        try:
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=90_000)
            except:
                await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            await asyncio.sleep(5)
            try:
                await page.wait_for_selector('article, h2 a, h3 a, [class*="course"]', timeout=15_000)
            except: pass
            courses = await page.evaluate("""
                () => {
                    const results = [];
                    const selectors = ['article h2 a','article h3 a','.course-item h2 a','.entry-title a','h2.course-title a','.wp-block-post h2 a'];
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        if (els.length > 1) {
                            Array.from(els).forEach(a => {
                                const container = a.closest('article') || a.closest('li') || a.parentElement;
                                const img = container?.querySelector('img');
                                if (a.innerText?.trim() && a.href) results.push({
                                    title: a.innerText.trim(),
                                    detailLink: a.href,
                                    image: img?.src || img?.dataset?.src || null,
                                    source: 'coursevania'
                                });
                            });
                            if (results.length > 0) break;
                        }
                    }
                    return results.filter(c => c.title && c.detailLink);
                }
            """)
            log.info(f"[Coursevania] ✅ صفحة {i}: {len(courses)} كورس")
            all_courses.extend(courses)
            await asyncio.sleep(2)
        except Exception as e:
            log.warning(f"[Coursevania] ⚠️ خطأ: {e}")
        finally:
            if page:
                try: await page.close()
                except: pass
    return all_courses

async def get_coursevania_direct_link(browser, detail_link):
    page = None
    try:
        page = await browser.new_page()
        try:
            await page.goto(detail_link, wait_until="networkidle", timeout=45_000)
        except:
            await page.goto(detail_link, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(3)
        return await page.evaluate("""
            () => {
                for (const s of ['a[href*="udemy.com/course"]','.coupon-btn a','a.btn[href*="udemy"]','.wp-block-button a','a[href*="udemy"]']) {
                    const el = document.querySelector(s);
                    if (el?.href?.includes('udemy.com')) return el.href;
                }
                return null;
            }
        """)
    except: return None
    finally:
        if page:
            try: await page.close()
            except: pass


# ══════════════════════════════════════════════
# 🗂️ خريطة المواقع
# ══════════════════════════════════════════════
SITES = {
    "couponscorpion": {
        "enabled":  os.getenv("SCRAPE_SCORPION", "true") == "true",
        "scraper":  scrape_coupon_scorpion_site,
        "get_link": get_scorpion_direct_link,
        "pages":    int(os.getenv("SCORPION_PAGES", 6)),
        "category": "Scorpion Global",
    },
    "real_discount": {
        "enabled":  os.getenv("SCRAPE_REAL_DISCOUNT", "true") == "true",
        "scraper":  scrape_real_discount_site,
        "get_link": get_real_discount_direct_link,
        "pages":    int(os.getenv("REAL_DISCOUNT_PAGES", 3)),
        "category": "Real Discount",
    },
    "onlinecourses": {
        "enabled":  os.getenv("SCRAPE_ONLINECOURSES", "true") == "true",
        "scraper":  scrape_onlinecourses_site,
        "get_link": get_onlinecourses_direct_link,
        "pages":    int(os.getenv("ONLINECOURSES_PAGES", 5)),
        "category": "OnlineCourses",
    },
    "coursevania": {
        "enabled":  os.getenv("SCRAPE_COURSEVANIA", "true") == "true",
        "scraper":  scrape_coursevania_site,
        "get_link": get_coursevania_direct_link,
        "pages":    int(os.getenv("COURSEVANIA_PAGES", 4)),
        "category": "Coursevania",
    },
}


# ══════════════════════════════════════════════
# 💾 حفظ في MongoDB
# ══════════════════════════════════════════════
async def save_course(db, course_doc):
    try:
        result = await db["courses"].update_one(
            {"slug": course_doc["slug"]},
            {"$setOnInsert": course_doc},
            upsert=True
        )
        return result.upserted_id is not None
    except Exception as e:
        if hasattr(e, "code") and e.code == 11000:
            return False
        log.error(f"⚠️ خطأ في الحفظ: {e}")
        return False


# ══════════════════════════════════════════════
# 🚀 المحرك الرئيسي
# ══════════════════════════════════════════════
async def scrape_coupon_scorpion(db):
    log.info("🛡️ جاري تشغيل المحرك...")
    ctx, engine = await create_browser()
    if engine == "camoufox" and ctx:
        async with ctx as browser:
            await _run_all_sites(db, browser)
    else:
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox",
                      "--disable-dev-shm-usage", "--disable-gpu"]
            )
            try:
                await _run_all_sites(db, browser)
            finally:
                await browser.close()


async def _run_all_sites(db, browser):
    total_saved = total_skipped = 0
    for site_key, cfg in SITES.items():
        if not cfg["enabled"]:
            log.info(f"⏭️ [{site_key}] معطل")
            continue
        log.info(f"\n{'='*50}\n🌐 {site_key}\n{'='*50}")
        try:
            raw = await cfg["scraper"](browser, cfg["pages"])
            log.info(f"[{site_key}] 🔍 مكتشف: {len(raw)}")
            saved = skipped = 0
            for course in raw:
                if not course.get("title") or not course.get("detailLink"):
                    continue
                slug = slugify(course["title"])
                exists = await db["courses"].find_one({
                    "$or": [{"slug": slug}, {"title": course["title"]}]
                })
                if exists:
                    skipped += 1
                    continue
                link = await cfg["get_link"](browser, course["detailLink"])
                if not link:
                    skipped += 1
                    continue
                smart_cat = await get_smart_category(course["title"], cfg["category"])
                is_new = await save_course(db, {
                    "title":     course["title"],
                    "slug":      slug,
                    "image":     fix_image_url(course.get("image"), course.get("detailLink", "")),
                    "udemyLink": link,
                    "category":  smart_cat,
                    "source":    site_key,
                    "isFree":    True,
                    "addedAt":   datetime.now(timezone.utc),
                })
                if is_new:
                    saved += 1
                    log.info(f"[{site_key}] ✅ {course['title'][:50]}")
                else:
                    skipped += 1
                await asyncio.sleep(DELAY_SECONDS)
            log.info(f"[{site_key}] 🏁 محفوظ: {saved} | متخطى: {skipped}")
            total_saved   += saved
            total_skipped += skipped
        except Exception as e:
            log.error(f"[{site_key}] ❌ خطأ: {e}")
    log.info(f"\n🎉 انتهى الكل! 💾 محفوظ: {total_saved} | ⏭️ متخطى: {total_skipped}")

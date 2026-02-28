"""
Debug لـ OnlineCourses و Coursevania - شغّل: python debug_new_sites.py
"""
import asyncio

async def debug(browser, url, name):
    print(f"\n{'='*60}\n🔍 {name}\n{'='*60}")
    page = await browser.new_page()
    try:
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)

        result = await page.evaluate("""
            () => {
                const info = {};
                info.title = document.title;
                info.url   = location.href;

                // Articles
                const arts = document.querySelectorAll('article');
                info.articleCount = arts.length;
                info.articleClasses = Array.from(arts).slice(0,3).map(a => a.className);
                if (arts.length > 0) {
                    info.firstArticleHTML = arts[0].outerHTML.substring(0, 1000);
                }

                // H2/H3 links
                const hLinks = document.querySelectorAll('h2 a, h3 a');
                info.hLinksCount = hLinks.length;
                info.hLinksSamples = Array.from(hLinks).slice(0, 5).map(a => ({
                    text:        a.innerText?.trim()?.substring(0, 60),
                    href:        a.href,
                    parentTag:   a.parentElement?.tagName,
                    parentClass: a.parentElement?.className?.substring(0, 60),
                    grandClass:  a.parentElement?.parentElement?.className?.substring(0, 60)
                }));

                // Articles detail
                info.articlesDetail = Array.from(arts).slice(0, 5).map(art => {
                    const h = art.querySelector('h1, h2, h3, h4');
                    const img = art.querySelector('img');
                    const links = art.querySelectorAll('a');
                    return {
                        articleClass: art.className?.substring(0, 80),
                        headingText:  h?.innerText?.trim()?.substring(0, 60),
                        headingTag:   h?.tagName,
                        headingClass: h?.className?.substring(0, 60),
                        firstLinkHref: links[0]?.href,
                        imgSrc:       img?.src?.substring(0, 80),
                        linksCount:   links.length
                    };
                });

                return info;
            }
        """)

        print(f"📄 Title: {result['title']}")
        print(f"🌐 URL:   {result['url']}")
        print(f"\n📦 Articles: {result['articleCount']}")
        print(f"   Classes: {result.get('articleClasses', [])}")

        print(f"\n🔗 H2/H3 Links: {result['hLinksCount']}")
        for l in result.get('hLinksSamples', []):
            print(f"   📌 {l['text']}")
            print(f"      href:        {l['href']}")
            print(f"      parent:      <{l['parentTag']} class='{l['parentClass']}'>")
            print(f"      grandparent: {l['grandClass']}")

        print(f"\n📋 Articles Detail:")
        for a in result.get('articlesDetail', []):
            print(f"   [{a['articleClass']}]")
            print(f"   <{a['headingTag']} class='{a['headingClass']}'> {a['headingText']}")
            print(f"   link:  {a['firstLinkHref']}")
            print(f"   image: {a['imgSrc']}")
            print(f"   links: {a['linksCount']}")
            print()

        if result.get('firstArticleHTML'):
            print(f"\n📝 First Article HTML:")
            print(result['firstArticleHTML'])

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await page.close()


async def main():
    try:
        from camoufox.async_api import AsyncCamoufox
        ctx = AsyncCamoufox(headless=True, geoip=False, block_images=True, i_know_what_im_doing=True)
        async with ctx as browser:
            await debug(browser, "https://www.onlinecourses.ooo/", "OnlineCourses.Ooo")
            await debug(browser, "https://coursevania.com/courses/", "Coursevania /courses/")
            await debug(browser, "https://coursevania.com/", "Coursevania /")
    except Exception as ex:
        print(f"Camoufox error: {ex}, جاري تجربة Playwright...")
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
            try:
                await debug(browser, "https://www.onlinecourses.ooo/", "OnlineCourses.Ooo")
                await debug(browser, "https://coursevania.com/courses/", "Coursevania /courses/")
                await debug(browser, "https://coursevania.com/", "Coursevania /")
            finally:
                await browser.close()

    print("\n✅ انتهى الفحص!")

if __name__ == "__main__":
    asyncio.run(main())

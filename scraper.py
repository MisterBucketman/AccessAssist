"""Scrape interactive page elements via Playwright for the accessibility assistant."""
import json
import time
from playwright.sync_api import sync_playwright

from config import HEADLESS, SCRAPE_SCROLL_STEPS, SCRAPE_TIMEOUT_MS

INTERACTIVE_SELECTORS = """
a[href],
button,
input,
select,
textarea,
[role="button"],
[role="link"],
[onclick],
[tabindex]
"""


def scrape_page(url, headless=None):
    """
    Scrape visible interactive elements from url. Uses Playwright; scrolls to load lazy content.
    headless: True for no window (default from config), False to show browser.
    """
    if headless is None:
        headless = HEADLESS
    scroll_steps = SCRAPE_SCROLL_STEPS
    timeout_ms = SCRAPE_TIMEOUT_MS

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,slow_mo=1000, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        # page = browser.new_page()
        print(f"[INFO] Navigating to {url}...")
        page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        # Wait for body to be in DOM; use state="attached" so hidden body (e.g. YouTube) does not timeout
        page.wait_for_selector("body", state="attached", timeout=15000)

        elements_data = {}
        seen_selectors = set()

        print("[INFO] Starting scroll + scrape...")
        for _ in range(scroll_steps):
            collect_visible_elements(page, elements_data, seen_selectors)
            page.evaluate("window.scrollBy(0, window.innerHeight);")
            time.sleep(0.5)

        browser.close()
        return {"url": url, "elements": list(elements_data.values())}


def collect_visible_elements(page, elements_data, seen_selectors):
    elements = page.query_selector_all(INTERACTIVE_SELECTORS)
    for el in elements:
        box = el.bounding_box()
        if not box or box["width"] == 0 or box["height"] == 0:
            continue

        css_selector = el.evaluate("""
            el => {
                let sel = el.tagName.toLowerCase();
                if (el.id) sel += '#' + el.id;
                if (el.className) sel += '.' + el.className.trim().replace(/\\s+/g, '.');
                return sel;
            }
        """)
        xpath_selector = el.evaluate("""
            el => {
                function getXPath(node) {
                    if (node.id)
                        return '//*[@id="' + node.id + '"]';
                    if (node === document.body)
                        return '/html/body';
                    let ix = 0;
                    const siblings = node.parentNode ? node.parentNode.childNodes : [];
                    for (let i=0; i<siblings.length; i++) {
                        const sibling = siblings[i];
                        if (sibling.nodeType === 1 && sibling.tagName === node.tagName) {
                            ix++;
                        }
                        if (sibling === node) {
                            return getXPath(node.parentNode) + '/' + node.tagName.toLowerCase() + '[' + ix + ']';
                        }
                    }
                }
                return getXPath(el);
            }
        """)

        unique_key = xpath_selector or css_selector
        if unique_key in seen_selectors:
            continue
        seen_selectors.add(unique_key)

        element_data = {
            "tag": el.evaluate("el => el.tagName.toLowerCase()"),
            "text": el.inner_text().strip(),
            "id": el.get_attribute("id"),
            "name": el.get_attribute("name"),
            "type": el.get_attribute("type"),
            "href": el.get_attribute("href"),
            "role": el.get_attribute("role"),
            "aria_label": el.get_attribute("aria-label"),
            "placeholder": el.get_attribute("placeholder"),
            "value": el.get_attribute("value"),
            "classes": el.get_attribute("class"),
            "onclick": el.get_attribute("onclick"),
            "css_selector": css_selector,
            "xpath_selector": xpath_selector
        }
        elements_data[unique_key] = element_data


if __name__ == "__main__":
    result = scrape_page("https://www.ask.com")
    print(json.dumps(result, indent=2))

# # # from playwright.sync_api import sync_playwright
# # # from bs4 import BeautifulSoup
# # # import json
# # #
# # #
# # # def scrape_page(url):
# # #     with sync_playwright() as p:
# # #         browser = p.chromium.launch()
# # #         page = browser.new_page()
# # #         page.goto(url)
# # #
# # #         # Wait for critical elements
# # #         page.wait_for_selector("body")
# # #
# # #         # Get HTML and parse with BeautifulSoup
# # #         html = page.content()
# # #         soup = BeautifulSoup(html, 'html.parser')
# # #
# # #         # Extract semantic elements
# # #         elements = []
# # #         for tag in soup.find_all(['a', 'button', 'input', 'form', 'h1', 'h2', 'h3']):
# # #             element_data = {
# # #                 "tag": tag.name,
# # #                 "text": tag.get_text(strip=True),
# # #                 "id": tag.get('id', ''),
# # #                 "name": tag.get('name', ''),
# # #                 "type": tag.get('type', ''),
# # #                 "href": tag.get('href', ''),
# # #                 "aria_label": tag.get('aria-label', ''),
# # #                 "placeholder": tag.get('placeholder', ''),
# # #                 "value": tag.get('value', ''),
# # #                 "classes": tag.get('class', []),
# # #                 "xpath": get_xpath(tag)  # New helper function
# # #             }
# # #             elements.append(element_data)
# # #
# # #         browser.close()
# # #         return {
# # #             "url": url,
# # #             "elements": elements,
# # #             "html": str(soup.body)  # For debugging
# # #         }
# # #
# # # def get_xpath(element):
# # #     components = []
# # #     child = element if element.name else element.parent
# # #     for parent in child.parents:
# # #         siblings = parent.find_all(child.name, recursive=False)
# # #         components.append(
# # #             child.name +
# # #             (f"[{siblings.index(child)+1}]" if len(siblings) > 1 else '')
# # #         )
# # #         child = parent
# # #     components.reverse()
# # #     return '/' + '/'.join(components)
# # #
# # # if __name__ == "__main__":
# # #     result = scrape_page("http://google.com")
# # #     print(json.dumps(result, indent=2))
# #
# # from playwright.sync_api import sync_playwright
# # from bs4 import BeautifulSoup
# # import json
# #
# #
# # def scrape_page(url):
# #     with sync_playwright() as p:
# #         browser = p.chromium.launch(headless=True)
# #         page = browser.new_page()
# #         page.goto(url, timeout=30000)
# #         page.wait_for_selector("body")
# #
# #         html = page.content()
# #         soup = BeautifulSoup(html, 'html.parser')
# #
# #         elements = []
# #         for tag in soup.find_all(True):
# #             if not is_interactable(tag):
# #                 continue
# #
# #             element_data = {
# #                 "tag": tag.name,
# #                 "text": tag.get_text(strip=True),
# #                 "id": tag.get('id', ''),
# #                 "name": tag.get('name', ''),
# #                 "type": tag.get('type', ''),
# #                 "href": tag.get('href', ''),
# #                 "role": tag.get('role', ''),
# #                 "aria_label": tag.get('aria-label', ''),
# #                 "placeholder": tag.get('placeholder', ''),
# #                 "value": tag.get('value', ''),
# #                 "classes": tag.get('class', []),
# #                 "onclick": tag.get('onclick', ''),
# #                 "xpath": get_xpath(tag)
# #             }
# #             elements.append(element_data)
# #
# #         browser.close()
# #         return {
# #             "url": url,
# #             "elements": elements
# #         }
# #
# #
# # def is_interactable(tag):
# #     interactive_tags = {'a', 'button', 'input', 'select', 'textarea', 'form'}
# #
# #     # Check tag type
# #     if tag.name in interactive_tags:
# #         return has_meaning(tag)
# #
# #     # Check clickable role or JS action
# #     if tag.get('role') in ['button', 'link'] or tag.get('onclick'):
# #         return True
# #
# #     return False
# #
# #
# # def has_meaning(tag):
# #     # Skip empty or hidden
# #     if not tag.get_text(strip=True) and not tag.get('placeholder') and not tag.get('value'):
# #         return False
# #     if 'hidden' in tag.attrs or 'display:none' in str(tag.get('style', '')):
# #         return False
# #     if tag.name == 'a' and not tag.get('href') and not tag.get('onclick'):
# #         return False
# #     return True
# #
# #
# # def get_xpath(element):
# #     components = []
# #     child = element if element.name else element.parent
# #     for parent in child.parents:
# #         siblings = parent.find_all(child.name, recursive=False)
# #         components.append(
# #             child.name + (f"[{siblings.index(child) + 1}]" if len(siblings) > 1 else '')
# #         )
# #         child = parent
# #     components.reverse()
# #     return '/' + '/'.join(components)
# #
# #
# # if __name__ == "__main__":
# #     result = scrape_page("https://www.google.com")
# #     print(json.dumps(result, indent=2))
#
# from playwright.sync_api import sync_playwright
# import json
#
# INTERACTIVE_SELECTORS = """
# a[href],
# button,
# input,
# select,
# textarea,
# [role="button"],
# [role="link"],
# [onclick],
# [tabindex]
# """
#
# def scrape_page(url):
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=False)  # Debugging? use headless=True for prod
#         page = browser.new_page()
#         print("[INFO] Navigating to page...")
#         page.goto(url, timeout=60000, wait_until="domcontentloaded")
#         print("[INFO] Page loaded, starting scrape...")
#         page.wait_for_selector("body", timeout=10000)
#
#         # Scroll to reveal lazy-loaded content
#         auto_scroll(page)
#
#         elements_data = []
#         elements = page.query_selector_all(INTERACTIVE_SELECTORS)
#
#         for el in elements:
#             if not el.is_visible():
#                 continue
#
#             el_data = {
#                 "tag": el.evaluate("el => el.tagName.toLowerCase()"),
#                 "text": el.inner_text().strip(),
#                 "id": el.get_attribute("id"),
#                 "name": el.get_attribute("name"),
#                 "type": el.get_attribute("type"),
#                 "href": el.get_attribute("href"),
#                 "role": el.get_attribute("role"),
#                 "aria_label": el.get_attribute("aria-label"),
#                 "placeholder": el.get_attribute("placeholder"),
#                 "value": el.get_attribute("value"),
#                 "classes": el.get_attribute("class"),
#                 "onclick": el.get_attribute("onclick"),
#                 "css_selector": el.evaluate("el => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '')")
#             }
#             elements_data.append(el_data)
#
#         browser.close()
#         return {"url": url, "elements": elements_data}
#
# def auto_scroll(page):
#     page.evaluate("""
#         async () => {
#             await new Promise(resolve => {
#                 let totalHeight = 0;
#                 const distance = 500;
#                 const timer = setInterval(() => {
#                     const scrollHeight = document.body.scrollHeight;
#                     window.scrollBy(0, distance);
#                     totalHeight += distance;
#                     if(totalHeight >= scrollHeight){
#                         clearInterval(timer);
#                         resolve();
#                     }
#                 }, 200);
#             });
#         }
#     """)
#
# if __name__ == "__main__":
#     result = scrape_page("https://www.amazon.com")
#     print(json.dumps(result, indent=2))

from playwright.sync_api import sync_playwright
import json
import time

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

def scrape_page(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Change to False to debug visually
        page = browser.new_page()
        print(f"[INFO] Navigating to {url}...")
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_selector("body", timeout=15000)

        elements_data = {}
        seen_selectors = set()

        print("[INFO] Starting scroll + scrape...")
        for _ in range(20):  # Scroll in 20 steps
            collect_visible_elements(page, elements_data, seen_selectors)
            page.evaluate("window.scrollBy(0, window.innerHeight);")
            time.sleep(0.5)  # Wait for lazy-loaded content

        browser.close()
        return {"url": url, "elements": list(elements_data.values())}

def collect_visible_elements(page, elements_data, seen_selectors):
    elements = page.query_selector_all(INTERACTIVE_SELECTORS)

    for el in elements:
        box = el.bounding_box()
        if not box or box["width"] == 0 or box["height"] == 0:
            continue  # Skip invisible or zero-size elements

        # Create stable locators
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
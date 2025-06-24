from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json


def scrape_page(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        # Wait for critical elements
        page.wait_for_selector("body")

        # Get HTML and parse with BeautifulSoup
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Extract semantic elements
        elements = []
        for tag in soup.find_all(['a', 'button', 'input', 'form', 'h1', 'h2', 'h3']):
            element_data = {
                "tag": tag.name,
                "text": tag.get_text(strip=True),
                "id": tag.get('id', ''),
                "name": tag.get('name', ''),
                "type": tag.get('type', ''),
                "href": tag.get('href', ''),
                "aria_label": tag.get('aria-label', ''),
                "placeholder": tag.get('placeholder', ''),
                "value": tag.get('value', ''),
                "classes": tag.get('class', []),
                "xpath": get_xpath(tag)  # New helper function
            }
            elements.append(element_data)

        browser.close()
        return {
            "url": url,
            "elements": elements,
            "html": str(soup.body)  # For debugging
        }

def get_xpath(element):
    components = []
    child = element if element.name else element.parent
    for parent in child.parents:
        siblings = parent.find_all(child.name, recursive=False)
        components.append(
            child.name +
            (f"[{siblings.index(child)+1}]" if len(siblings) > 1 else '')
        )
        child = parent
    components.reverse()
    return '/' + '/'.join(components)

if __name__ == "__main__":
    result = scrape_page("http://localhost:8000/index.html")
    print(json.dumps(result, indent=2))
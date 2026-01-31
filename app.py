"""Flask app for Accessibility Assistant: process, label, manual record, execute, speak."""
import json
import os
from datetime import datetime
from urllib.parse import urlparse

from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright
import pyttsx3

from scraper import scrape_page
from ollama_integration import get_llm_response
from executor import execute_actions
from scrape_cache import get_cached_scrape, set_cached_scrape

app = Flask(__name__)

ALLOWED_SCHEMES = ("http", "https")


def validate_url(url):
    """Validate URL: only http/https. Returns (is_valid, error_message)."""
    if not url or not isinstance(url, str):
        return False, "URL is required"
    url = url.strip()
    if not url:
        return False, "URL is required"
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False, f"URL scheme must be one of {ALLOWED_SCHEMES}"
        if not parsed.netloc:
            return False, "URL must have a host"
        return True, None
    except Exception as e:
        return False, str(e)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/scrape', methods=['POST'])
def scrape_only():
    """Scrape the page only and save to cache. Does not call the LLM."""
    data = request.json or {}
    url = data.get('url', '').strip()

    ok, err = validate_url(url)
    if not ok:
        return jsonify({"error": err, "website_data": None}), 400

    website_data = scrape_page(url)
    set_cached_scrape(url, website_data)

    return jsonify({
        "website_data": website_data,
        "cached": False,
        "message": "Page scraped and cached."
    })


@app.route('/process', methods=['POST'])
def process():
    """
    Process request: (1) Get scraped data (from cache if use_cache and available, else scrape and cache).
    (2) Run LLM on scraped data + query.
    """
    data = request.json or {}
    url = data.get('url', '').strip()
    query = data.get('query', '').strip()
    use_cache = data.get('use_cache', False)

    ok, err = validate_url(url)
    if not ok:
        return jsonify({"error": err, "website_data": None, "llm_response": None}), 400

    website_data = None
    if use_cache:
        website_data = get_cached_scrape(url)
    if website_data is None:
        website_data = scrape_page(url)
        set_cached_scrape(url, website_data)
        used_cache = False
    else:
        used_cache = True

    llm_response = get_llm_response(website_data, query)

    return jsonify({
        "website_data": website_data,
        "llm_response": llm_response,
        "used_cache": used_cache
    })


@app.route('/label_llm_result', methods=['POST'])
def label_llm_result():
    data = request.json or {}
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = "llm_labels"
    os.makedirs(save_dir, exist_ok=True)

    file_path = os.path.join(save_dir, f"label_{timestamp}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    queries_dir = os.path.join(save_dir, "queries")
    os.makedirs(queries_dir, exist_ok=True)
    query_file = os.path.join(queries_dir, f"query_{timestamp}.txt")
    with open(query_file, "w", encoding="utf-8") as f:
        f.write(data.get("query", ""))

    return jsonify({"status": "success", "file": file_path})


@app.route('/manual_record', methods=['POST'])
def manual_record():
    """Record correct actions by opening a browser; user performs steps, then stops. LLM's suggested actions are passed as llm_action_sequence (for reference only)."""
    data = request.json or {}
    url = data.get("url", "").strip()
    user_query = data.get("query", "")
    original_scrape = data.get("original_scrape", {})
    llm_action_sequence = data.get("llm_action_sequence", data.get("correct_actions", []))

    ok, err = validate_url(url)
    if not ok:
        return jsonify({"status": "error", "error": err}), 400

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = "training_data"
    os.makedirs(save_dir, exist_ok=True)

    correct_actions = record_manual_actions(url)

    record = {
        "url": url,
        "user_query": user_query,
        "original_scrape": original_scrape,
        "correct_actions": correct_actions
    }
    with open(os.path.join(save_dir, f"session_{timestamp}.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    return jsonify({"status": "success", "file": f"session_{timestamp}.json", "correct_actions": correct_actions})


def record_manual_actions(url):
    actions = []

    def record_click(selector):
        actions.append({"action": "click", "target": selector})

    def record_fill(selector, value):
        actions.append({"action": "fill", "target": selector, "value": value})

    def record_press(selector, key):
        actions.append({"action": "press", "target": selector, "key": key})

    def record_scroll(direction, amount):
        actions.append({"action": "scroll", "direction": direction, "amount": amount})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,
                args=["--start-maximized"])
        context = browser.new_context()
        page = context.new_page()

        page.expose_binding("recordClick", lambda source, selector: record_click(selector))
        page.expose_binding("recordFill", lambda source, selector, value: record_fill(selector, value))
        page.expose_binding("recordPress", lambda source, selector, key: record_press(selector, key))
        page.expose_binding("recordScroll", lambda source, direction, amount: record_scroll(direction, amount))

        page.goto(url)

        page.evaluate("""(function() {
            function buildSelector(el) {
                if (!el || !el.tagName) return "";
                var s = el.tagName.toLowerCase();
                if (el.id && typeof el.id === "string") return s + "#" + el.id;
                var cn = el.className;
                if (cn) {
                    var str = typeof cn === "string" ? cn : (cn.baseVal != null ? cn.baseVal : "");
                    if (str && typeof str === "string" && str.indexOf("object") === -1)
                        return s + "." + str.trim().split(/\\s+/).filter(Boolean).join(".");
                }
                return s;
            }

            function getClickableElement(el) {
                var interactive = ["BUTTON", "A", "INPUT", "SELECT", "TEXTAREA"];
                var clickableRoles = ["button", "link", "option", "menuitem", "tab"];
                var n = el;
                while (n && n !== document.body) {
                    var tag = n.tagName;
                    var role = (n.getAttribute && n.getAttribute("role")) || "";
                    var hasOnclick = n.onclick || (n.getAttribute && n.getAttribute("onclick"));
                    var hasTabindex = n.tabIndex >= 0;
                    var isRoleClickable = clickableRoles.indexOf(role.toLowerCase()) >= 0;
                    if (interactive.indexOf(tag) >= 0 || isRoleClickable || hasOnclick || (hasTabindex && (tag === "DIV" || tag === "SPAN")))
                        return n;
                    n = n.parentElement;
                }
                return el;
            }

            document.addEventListener("click", function(e) {
                var clickable = getClickableElement(e.target);
                var sel = buildSelector(clickable);
                if (sel) window.recordClick(sel);
            }, true);

            document.addEventListener("blur", function(e) {
                var tag = (e.target.tagName || "").toLowerCase();
                if (tag !== "input" && tag !== "textarea" && tag !== "select") return;
                var sel = buildSelector(e.target);
                if (sel) window.recordFill(sel, e.target.value || "");
            }, true);

            var RECORD_KEYS = ["Enter", "Tab", "Escape", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "];
            document.addEventListener("keydown", function(e) {
                if (RECORD_KEYS.indexOf(e.key) < 0) return;
                var active = document.activeElement;
                if (!active || active === document.body) return;
                var sel = buildSelector(active);
                if (sel) window.recordPress(sel, e.key === " " ? "Space" : e.key);
            }, true);

            var lastScrollY = window.scrollY;
            var lastScrollX = window.scrollX;
            var scrollThrottle = null;
            window.addEventListener("scroll", function() {
                if (scrollThrottle) return;
                scrollThrottle = setTimeout(function() {
                    scrollThrottle = null;
                    var dy = window.scrollY - lastScrollY;
                    var dx = window.scrollX - lastScrollX;
                    lastScrollY = window.scrollY;
                    lastScrollX = window.scrollX;
                    if (Math.abs(dy) >= 50) window.recordScroll(dy > 0 ? "down" : "up", Math.abs(dy));
                    if (Math.abs(dx) >= 50) window.recordScroll(dx > 0 ? "right" : "left", Math.abs(dx));
                }, 300);
            }, { passive: true });
        })();""")

        print("Perform your manual actions in the browser window now...")
        input("Press Enter here in console to stop recording and save actions...")

        browser.close()

    return actions


@app.route('/execute', methods=['POST'])
def execute():
    data = request.json or {}
    url = data.get('url', '').strip()
    actions = data.get('actions', [])

    ok, err = validate_url(url)
    if not ok:
        return jsonify({"status": "error", "steps": [], "logs": err, "error": err}), 400

    try:
        result = execute_actions(url, actions)
        return jsonify({
            "status": result.get("status", "error"),
            "steps": result.get("steps", []),
            "logs": "\n".join(result.get("logs", [])),
            "final_url": result.get("final_url")
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "steps": [],
            "logs": str(e),
            "error": str(e)
        })


@app.route('/speak', methods=['POST'])
def speak():
    text = (request.json or {}).get('text', '')
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return jsonify({"status": "success"})


if __name__ == '__main__':
    app.run(port=5000, debug=True)

from flask import Flask, render_template, request, jsonify
from scraper import scrape_page
from ollama_integration import get_llm_response
from executor import execute_actions
import pyttsx3
import time

import json
import os
from datetime import datetime
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process', methods=['POST'])
def process():
    data = request.json
    url = data.get('url', '')
    query = data.get('query', '')

    # Scrape website
    website_data = scrape_page(url)
    # time.sleep(30)


    # Get LLM response
    llm_response = get_llm_response(website_data, query)

    return jsonify({
        "website_data": website_data,
        "llm_response": llm_response
    })


@app.route('/label_llm_result', methods=['POST'])
def label_llm_result():
    data = request.json
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    save_dir = "llm_labels"
    os.makedirs(save_dir, exist_ok=True)

    # Save full labeled record
    file_path = os.path.join(save_dir, f"label_{timestamp}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Also save just the query separately
    queries_dir = os.path.join(save_dir, "queries")
    os.makedirs(queries_dir, exist_ok=True)
    query_file = os.path.join(queries_dir, f"query_{timestamp}.txt")
    with open(query_file, "w", encoding="utf-8") as f:
        f.write(data.get("query", ""))

    return jsonify({"status": "success", "file": file_path})


@app.route('/manual_record', methods=['POST'])
def manual_record():
    """Record correct actions by opening a browser; user performs steps, then stops. LLM's suggested actions are passed as llm_action_sequence (for reference only)."""
    data = request.json
    url = data.get("url", "")
    user_query = data.get("query", "")
    original_scrape = data.get("original_scrape", {})
    # LLM's suggested action sequence (may be incorrect; we record the correct one below)
    llm_action_sequence = data.get("llm_action_sequence", data.get("correct_actions", []))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = "training_data"
    os.makedirs(save_dir, exist_ok=True)

    correct_actions = record_manual_actions(url)

    # Save combined record
    record = {
        "url": url,
        "user_query": user_query,
        "original_scrape": original_scrape,
        "correct_actions": correct_actions
    }
    with open(os.path.join(save_dir, f"session_{timestamp}.json"), "w") as f:
        json.dump(record, f, indent=2)
    print(record)
    return jsonify({"status": "success", "file": f"session_{timestamp}.json", "correct_actions": correct_actions})


def record_manual_actions(url):
    actions = []

    def record_click(selector):
        actions.append({
            "action": "click",
            "target": selector
        })

    def record_fill(selector, value):
        actions.append({
            "action": "fill",
            "target": selector,
            "value": value
        })

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Expose Python functions callable from JS
        page.expose_binding("recordClick", lambda source, selector: record_click(selector))
        page.expose_binding("recordFill", lambda source, selector, value: record_fill(selector, value))

        page.goto(url)

        # Attach DOM event listeners inside page context
        page.evaluate("""
            document.addEventListener("click", e => {
                // Build a simple selector string
                let sel = e.target.tagName.toLowerCase();
                if (e.target.id) sel += "#" + e.target.id;
                else if (e.target.className) sel += "." + e.target.className.toString().split(' ').join('.');
                window.recordClick(sel);
            });

            document.addEventListener("input", e => {
                let sel = e.target.tagName.toLowerCase();
                if (e.target.id) sel += "#" + e.target.id;
                else if (e.target.className) sel += "." + e.target.className.toString().split(' ').join('.');
                window.recordFill(sel, e.target.value);
            });
        """)

        print("Perform your manual actions in the browser window now...")
        input("Press Enter here in console to stop recording and save actions...")

        browser.close()

    return actions


@app.route('/execute', methods=['POST'])
def execute():
    data = request.json
    url = data.get('url', '')
    actions = data.get('actions', [])

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
    text = request.json.get('text', '')
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    return jsonify({"status": "success"})


if __name__ == '__main__':
    app.run(port=5000, debug=True)
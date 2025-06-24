from flask import Flask, render_template, request, jsonify
from scraper import scrape_page
from ollama_integration import get_llm_response
from executor import execute_actions
import pyttsx3

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

    # Get LLM response
    llm_response = get_llm_response(website_data, query)

    return jsonify({
        "website_data": website_data,
        "llm_response": llm_response
    })


@app.route('/execute', methods=['POST'])
def execute():
    data = request.json
    url = data.get('url', '')
    actions = data.get('actions', [])

    # Capture print output
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        try:
            execute_actions(url, actions)
            status = "success"
        except Exception as e:
            print(f"Critical error: {str(e)}")
            status = "error"

    logs = f.getvalue()
    print(logs)  # Also show in console

    return jsonify({
        "status": status,
        "logs": logs
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
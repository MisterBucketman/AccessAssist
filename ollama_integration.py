"""LLM integration for accessibility assistant. Uses Ollama with configurable model."""
import json
import ollama

from config import OLLAMA_MODEL


def _validate_action_sequence(obj):
    """Ensure action_sequence exists, is a list, and each action has action and target (and value for fill)."""
    if not isinstance(obj, dict):
        return False, "Response is not a JSON object"
    action_sequence = obj.get("action_sequence")
    if action_sequence is None:
        return False, "Missing action_sequence"
    if not isinstance(action_sequence, list):
        return False, "action_sequence is not a list"
    for i, action in enumerate(action_sequence):
        if not isinstance(action, dict):
            return False, f"Action {i} is not an object"
        if not action.get("action"):
            return False, f"Action {i} missing 'action'"
        if action.get("action") not in ("click", "fill", "navigate", "press", "scroll"):
            return False, f"Action {i} has invalid 'action'"
        if not action.get("target") and action.get("action") not in ("navigate", "scroll"):
            return False, f"Action {i} missing 'target'"
        if action.get("action") == "fill" and "value" not in action:
            action["value"] = ""  # allow missing value, default to empty
        if action.get("action") == "press" and "key" not in action:
            action["key"] = "Enter"
        if action.get("action") == "scroll" and "direction" not in action:
            action["direction"] = "down"
            action["amount"] = action.get("amount", 300)
    return True, None


def get_llm_response(website_data, user_query):
    """
    Ask the LLM for an action sequence and verbal guide. Requires the LLM to use
    exact css_selector (or xpath_selector) from the website structure as "target"
    so the executor can locate elements reliably.
    """
    model = OLLAMA_MODEL
    prompt = f"""
You are an accessibility assistant. The WEBSITE STRUCTURE below shows the currently VISIBLE part of the page only. Prefer actions that use only these elements; only suggest "scroll" if the user's goal clearly requires content that is not visible.

You must choose elements from the structure and use their exact "css_selector" or "xpath_selector" as "target". Prefer stable identifiers:
- For buttons (especially search): prefer "aria_label" when present (e.g. button[aria-label="Search"] or the element's id like #search-icon-legacy). These are more reliable than long class strings.
- For inputs: prefer id, name, or placeholder when present.

WEBSITE STRUCTURE (each element has css_selector, xpath_selector, text, id, aria_label, role, etc.):
{json.dumps(website_data.get('elements', []), indent=2)}

USER REQUEST: "{user_query}"

Output valid JSON with:
- "action_sequence": list of action objects:
  - "action": "click" | "fill" | "navigate" | "press"
  "target": MUST be the exact "css_selector" or "xpath_selector" string from an element in WEBSITE STRUCTURE above (e.g. "input#email", "button.submit-btn"). Use only values that appear in the structure.
  - "value": string to type (required for "fill" actions, omit for click/navigate)
  - "key": for "press" actions (e.g. "Enter")
- "verbal_guide": short step-by-step instructions in plain English

Example (targets must come from the website structure):
{{
  "action_sequence": [
    {{"action": "fill", "target": "input#email", "value": "user@example.com"}},
    {{"action": "fill", "target": "input#password", "value": "secret"}},
    {{"action": "click", "target": "button.sign-in"}}
  ],
  "verbal_guide": "Enter your email, then password, then click Sign In."
}}
"""

    print("\nSending prompt to LLM:")
    print(prompt[:1500] + "..." if len(prompt) > 1500 else prompt)

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.2}
        )
    except Exception as e:
        return {
            "error": f"Ollama request failed: {str(e)}",
            "action_sequence": [],
            "verbal_guide": ""
        }

    raw = response.get("message", {}).get("content", "")
    print("\nReceived LLM response:")
    print(raw[:500] + "..." if len(raw) > 500 else raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        return {
            "error": f"Invalid JSON from LLM: {e}",
            "raw_response": raw,
            "action_sequence": [],
            "verbal_guide": ""
        }

    ok, err = _validate_action_sequence(parsed)
    if not ok:
        return {
            "error": err,
            "raw_response": raw,
            "action_sequence": parsed.get("action_sequence", []) if isinstance(parsed.get("action_sequence"), list) else [],
            "verbal_guide": parsed.get("verbal_guide", "") if isinstance(parsed.get("verbal_guide"), str) else ""
        }

    return parsed

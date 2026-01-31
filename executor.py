"""Execute action sequences (click, fill) on a page via Playwright. Returns structured step results."""
import re
import time
from playwright.sync_api import sync_playwright


def execute_actions(url, actions):
    """
    Run a list of actions on the given URL. Returns a dict with status, steps, logs, and optional final_url.
    Does not block on input(); browser closes after actions complete.
    """
    steps = []
    logs = []
    final_url = None

    def log(msg):
        logs.append(msg)
        print(msg)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=1000,
                args=["--start-maximized"]
            )
        except Exception as e:
            return {
                "status": "error",
                "steps": [],
                "logs": [f"Failed to launch browser: {str(e)}"],
                "error": str(e)
            }

        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        try:
            page.goto(url)
            final_url = page.url
            log(f"Opened page: {page.url}")
            page.wait_for_load_state("networkidle")
            page.screenshot(path="before_actions.png")
        except Exception as e:
            log(f"Navigation error: {str(e)}")
            browser.close()
            return {
                "status": "error",
                "steps": [],
                "logs": logs,
                "error": str(e)
            }

        for i, action in enumerate(actions):
            action_type = action.get("action")
            target = action.get("target", "")
            value = action.get("value", "")

            step_result = {
                "action": action_type,
                "target": target,
                "success": False,
                "error": None
            }
            if action_type == "fill":
                step_result["value"] = value

            log(f"\nExecuting action {i+1}/{len(actions)}: {action}")

            try:
                if not target:
                    step_result["error"] = "Missing target"
                    steps.append(step_result)
                    continue

                if any(sym in target for sym in ["#", ".", "[", ">", " "]):
                    element = page.locator(target)
                else:
                    element = page.locator(f"#{target}")
                    if element.count() == 0:
                        element = page.locator(f"[name='{target}']")
                    if element.count() == 0:
                        element = page.locator(f"[placeholder='{target}']")
                    if element.count() == 0:
                        element = page.get_by_label(re.compile(target, re.IGNORECASE), exact=False)
                    if element.count() == 0:
                        element = page.locator(f"label:has-text('{target}') + input")

                log(f"Found {element.count()} elements matching '{target}'")

                if element.count() > 0:
                    element.first.scroll_into_view_if_needed()
                    if action_type == "fill":
                        element.first.fill(value)
                        log(f"Filled element '{target}' with '{value}'")
                    elif action_type == "click":
                        element.first.click()
                        log(f"Clicked element '{target}'")
                    step_result["success"] = True
                    page.screenshot(path=f"after_action_{i}.png")
                else:
                    step_result["error"] = f"No element found for: {target}"
                    log(step_result["error"])

                steps.append(step_result)
                time.sleep(1)

            except Exception as e:
                step_result["error"] = str(e)
                steps.append(step_result)
                log(f"Error executing action: {action}")
                log(f"Error details: {str(e)}")

        try:
            page.screenshot(path="after_actions.png")
            final_url = page.url
            log("\nAll actions executed.")
        except Exception:
            pass

        browser.close()

    status = "success" if all(s.get("success") for s in steps) else "error"
    return {
        "status": status,
        "steps": steps,
        "logs": logs,
        "final_url": final_url
    }

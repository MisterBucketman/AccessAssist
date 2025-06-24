from playwright.sync_api import sync_playwright
import time
import re


def execute_actions(url, actions):
    with sync_playwright() as p:
        # Launch browser with visible UI
        browser = p.chromium.launch(
            headless=False,
            slow_mo=1000,  # Slow down execution for visibility
            args=["--start-maximized"]  # Start maximized
        )
        context = browser.new_context(no_viewport=True)  # Use full window
        page = context.new_page()

        # Navigate to the URL
        page.goto(url)
        print(f"Opened page: {page.url}")

        # Wait for page to load
        page.wait_for_load_state("networkidle")

        # Take screenshot for debugging
        page.screenshot(path="before_actions.png")

        # Execute each action
        for i, action in enumerate(actions):
            action_type = action.get("action")
            target = action.get("target")
            value = action.get("value", "")

            print(f"\nExecuting action {i + 1}/{len(actions)}: {action}")

            try:
                if action_type == "fill":
                    # Try multiple strategies to find the element
                    if target.startswith("#"):
                        element = page.locator(f"#{target[1:]}")
                    elif target.startswith("."):
                        element = page.locator(target)
                    else:
                        # Try by ID
                        element = page.locator(f"#{target}")
                        if element.count() == 0:
                            # Try by name
                            element = page.locator(f"[name='{target}']")
                        if element.count() == 0:
                            # Try by placeholder
                            element = page.locator(f"[placeholder='{target}']")
                        if element.count() == 0:
                            # Try by label text (case-insensitive, partial match)
                            element = page.get_by_label(re.compile(target, re.IGNORECASE), exact=False)
                        if element.count() == 0:
                            # Try by associated label text
                            element = page.locator(f"label:has-text('{target}') + input")

                    print(f"Found {element.count()} elements matching '{target}'")

                    if element.count() > 0:
                        element.first.scroll_into_view_if_needed()
                        element.first.fill(value)
                        print(f"Filled element: {target} with '{value}'")

                        # Take screenshot after fill
                        page.screenshot(path=f"after_action_{i}.png")
                    else:
                        print(f"No element found for: {target}")

                elif action_type == "click":
                    # Try multiple strategies to find the element
                    if target.startswith("#"):
                        element = page.locator(f"#{target[1:]}")
                    elif target.startswith("."):
                        element = page.locator(target)
                    else:
                        # Try by ID
                        element = page.locator(f"#{target}")
                        if element.count() == 0:
                            # Try by text (case-insensitive, partial match)
                            element = page.get_by_text(re.compile(target, re.IGNORECASE), exact=False)
                        if element.count() == 0:
                            # Try by role
                            element = page.get_by_role("button", name=re.compile(target, re.IGNORECASE))
                        if element.count() == 0:
                            # Try by value attribute
                            element = page.locator(f"[value='{target}']")

                    print(f"Found {element.count()} elements matching '{target}'")

                    if element.count() > 0:
                        element.first.scroll_into_view_if_needed()
                        element.first.click()
                        print(f"Clicked element: {target}")

                        # Take screenshot after click
                        page.screenshot(path=f"after_action_{i}.png")
                    else:
                        print(f"No element found for: {target}")

                # Add a short delay between actions
                time.sleep(1)

            except Exception as e:
                print(f"Error executing action: {action}")
                print(f"Error details: {str(e)}")

        # Final screenshot
        page.screenshot(path="after_actions.png")
        print("\nAll actions executed. Browser will remain open for inspection.")
        input("Press Enter to close browser...")
        browser.close()
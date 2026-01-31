"""
Persistent browser session for continuous use: one Chromium instance stays open
in a dedicated thread so all Playwright calls run on the same thread (avoids
"cannot switch to a different thread" errors). Use submit_* to run commands.
"""
import queue
import threading
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from scraper import scrape_from_page, QUICK_SCROLL_STEPS
from executor import execute_actions_on_page

# Session state (only touched by worker thread)
_playwright = None
_browser = None
_context = None
_page = None
_current_url = None

# Request/result queues for thread-safe calls from Flask
_request_queue = queue.Queue()
_result_queue = queue.Queue()
_worker_thread = None
_worker_started = threading.Event()


def _normalize_for_compare(url):
    """Normalize URL for comparison (strip trailing slash, fragment)."""
    if not url or not url.strip():
        return ""
    url = url.strip()
    try:
        parsed = urlparse(url)
        path = (parsed.path or "/").rstrip("/") or "/"
        return f"{parsed.scheme or 'https'}://{(parsed.netloc or '').lower()}{path}{'?' + parsed.query if parsed.query else ''}"
    except Exception:
        return url


def _get_or_create_page(url):
    """Run in worker thread only."""
    global _playwright, _browser, _context, _page, _current_url

    target = _normalize_for_compare(url)
    if not target:
        raise ValueError("URL is required")

    if _page is not None and not _page.is_closed():
        current = _normalize_for_compare(_page.url)
        if current == target:
            return _page
        _page.goto(url, wait_until="domcontentloaded")
        _page.wait_for_load_state("networkidle", timeout=15000)
        _current_url = _page.url
        return _page

    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(
        headless=False,
        slow_mo=1000,
        args=["--start-maximized"]
    )
    _context = _browser.new_context(no_viewport=True)
    _page = _context.new_page()
    _page.goto(url, wait_until="domcontentloaded")
    _page.wait_for_load_state("networkidle", timeout=15000)
    _current_url = _page.url
    return _page


def _scrape_current_page(scroll_steps=None):
    """Run in worker thread only. scroll_steps=None uses default; 0 = viewport only."""
    if _page is None or _page.is_closed():
        raise RuntimeError("No browser session; run Process or Execute first.")
    return scrape_from_page(_page, _page.url, scroll_steps=scroll_steps)


def _execute_on_session(actions, query, after_each_action, before_scroll):
    """Run in worker thread only."""
    if _page is None or _page.is_closed():
        raise RuntimeError("No browser session; open a URL via Process or Execute first.")
    return execute_actions_on_page(
        _page, actions,
        query=query,
        after_each_action=after_each_action,
        before_scroll=before_scroll,
    )


def _close_session():
    """Run in worker thread only."""
    global _playwright, _browser, _context, _page, _current_url
    try:
        if _browser:
            _browser.close()
    except Exception:
        pass
    try:
        if _playwright:
            _playwright.stop()
    except Exception:
        pass
    _playwright = None
    _browser = None
    _context = None
    _page = None
    _current_url = None


def _worker_loop():
    """Runs in dedicated thread; all Playwright usage happens here."""
    global _worker_started
    _worker_started.set()
    while True:
        try:
            item = _request_queue.get()
            if item is None:
                break
            cmd, args = item
            try:
                if cmd == "get_or_create_page":
                    r = _get_or_create_page(args[0])
                    _result_queue.put(("ok", r))
                elif cmd == "scrape_current_page":
                    scroll_steps = args[0] if args else None
                    r = _scrape_current_page(scroll_steps)
                    _result_queue.put(("ok", r))
                elif cmd == "execute_on_session":
                    actions, query, after_each_action, before_scroll = args
                    r = _execute_on_session(actions, query, after_each_action, before_scroll)
                    _result_queue.put(("ok", r))
                elif cmd == "close_session":
                    _close_session()
                    _result_queue.put(("ok", None))
                elif cmd == "has_session":
                    ok = _page is not None and not _page.is_closed()
                    _result_queue.put(("ok", ok))
                elif cmd == "get_current_url":
                    u = None
                    if _page is not None and not _page.is_closed():
                        try:
                            u = _page.url
                        except Exception:
                            u = _current_url
                    else:
                        u = _current_url
                    _result_queue.put(("ok", u))
                else:
                    _result_queue.put(("error", ValueError(f"Unknown command: {cmd}")))
            except Exception as e:
                _result_queue.put(("error", e))
        except Exception as e:
            _result_queue.put(("error", e))


def _ensure_worker():
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
        _worker_thread.start()
        _worker_started.wait(timeout=5)


def _submit(cmd, args):
    """Submit a command to the session thread and block for result."""
    _ensure_worker()
    _request_queue.put((cmd, args))
    status, data = _result_queue.get()
    if status == "error":
        raise data
    return data


def has_session():
    """Return True if a browser session is active (via session thread)."""
    try:
        return _submit("has_session", ())
    except Exception:
        return False


def get_current_url():
    """Return the URL of the current page, or None (via session thread)."""
    try:
        return _submit("get_current_url", ())
    except Exception:
        return None


def get_or_create_page(url):
    """
    Ensure we have a page at the given URL (runs in session thread).
    Launches browser if needed, or navigates the existing page if URL changed.
    Caller must not use the page object; all further work goes through submit_*.
    """
    _submit("get_or_create_page", (url,))


def scrape_current_page(scroll_steps=None):
    """
    Scrape the current session page (runs in session thread).
    scroll_steps: None = default, 0 = viewport only (evaluate existing page first).
    Returns website_data dict (url + elements).
    """
    return _submit("scrape_current_page", (scroll_steps,))


def execute_on_session(actions, query=None, after_each_action=None, before_scroll=None):
    """
    Run actions on the current session page (same Chromium instance, in session thread).
    Does not close the browser.
    """
    return _submit("execute_on_session", (actions, query, after_each_action, before_scroll))


def close_session():
    """Close the browser and clear session state (runs in session thread)."""
    try:
        _submit("close_session", ())
    except Exception:
        pass
    # Allow worker to keep running for future sessions

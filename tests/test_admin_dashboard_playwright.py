import asyncio
import importlib.util
import os
import socket
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

from playwright.async_api import async_playwright
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]


def _load_app():
    os.environ.setdefault("FLASK_ENV", "development")
    os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

    spec = importlib.util.spec_from_file_location("app", str(ROOT / "__init__.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["app"] = module
    spec.loader.exec_module(module)
    return module.create_app()


def _find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def run_app_server():
    app = _load_app()
    port = _find_free_port()
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


async def _login_and_collect_dashboard_text(base_url):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(f"{base_url}/admin/login", wait_until="networkidle")
        await page.fill("#username", "admin")
        await page.fill("#password", "admin-pass")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/admin/dashboard", timeout=15000)
        await page.wait_for_load_state("networkidle")
        text = await page.locator("body").inner_text()
        url = page.url
        await browser.close()
        return url, text


def test_admin_dashboard_components_are_visible():
    with run_app_server() as base_url:
        url, text = asyncio.run(_login_and_collect_dashboard_text(base_url))

    assert url.endswith("/admin/dashboard")
    assert "Welcome back!" in text
    assert "Consignment Sheet" in text
    assert "Leads Panel" in text
    assert "Database Backup" in text
    assert "Gram SCS Admin" in text

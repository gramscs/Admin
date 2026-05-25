#!/usr/bin/env python3
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


async def _login_and_open_consignments(base_url):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(f"{base_url}/admin/login", wait_until="networkidle")
        await page.fill("#username", "admin")
        await page.fill("#password", "admin-pass")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/admin/dashboard", timeout=15000)
        await page.goto(f"{base_url}/admin/consignments", wait_until="networkidle")
        html = await page.content()
        await browser.close()
        return html


def main():
    with run_app_server() as base_url:
        html = asyncio.run(_login_and_open_consignments(base_url))

    if "model-list" in html:
        print("PASS: consignments admin list loaded (model-list present)")
        sys.exit(0)
    else:
        print("FAIL: consignments admin list did not load; 'model-list' missing")
        sys.exit(2)


if __name__ == "__main__":
    main()

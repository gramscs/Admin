from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context()
    page = context.new_page()

    console_messages = []
    def on_console(msg):
        console_messages.append((msg.type, msg.text))
    page.on("console", on_console)

    network = []
    def on_request(request):
        network.append(("request", request.method, request.url))
    def on_response(response):
        network.append(("response", response.status, response.url))
    page.on("request", on_request)
    page.on("response", on_response)

    # Login
    page.goto('http://127.0.0.1:5000/admin/login')
    page.fill('input[name="username"]', 'admin')
    page.fill('input[name="password"]', 'admin-pass')
    page.click('button[type="submit"]')
    time.sleep(1)

    # Navigate to consignments
    page.goto('http://127.0.0.1:5000/admin/consignments')
    time.sleep(2)

    print('CONSOLE:')
    for m in console_messages:
        print(m)
    print('\nNETWORK:')
    for n in network:
        print(n)

    browser.close()

"""Independent Chrome reproduction for allocation display and invalid Enter submission."""

from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright


ROOT = Path.cwd()
BASE = "http://127.0.0.1:5189"


def start(command, cwd):
    return subprocess.Popen(command, cwd=cwd, creationflags=subprocess.CREATE_NO_WINDOW)


def wait_for(url, process):
    for _ in range(80):
        if process.poll() is not None:
            raise RuntimeError(f"Process exited with {process.returncode}")
        try:
            urllib.request.urlopen(url, timeout=1).close()
            return
        except OSError:
            time.sleep(.125)
    raise RuntimeError(f"Unable to open {url}")


api = start([sys.executable, "-m", "uvicorn", "backend.src.api.main:app", "--host", "127.0.0.1", "--port", "8000"], ROOT)
vite = None
try:
    wait_for("http://127.0.0.1:8000/health", api)
    vite = start(["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5189", "--strictPort"], ROOT / "frontend")
    wait_for(BASE + "/api/indexes", vite)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe")
        page = browser.new_page(viewport={"width": 1280, "height": 960})
        response = page.goto(BASE)
        print(f"Page HTTP {response.status}, Chrome {browser.version}")
        ibov = page.get_by_label("IBOVESPA allocation percentage")
        ifix = page.get_by_label("IFIX allocation percentage")

        def values(suffix):
            return [page.get_by_label(f"{name} allocation {suffix}").input_value()
                    for name in ["IBOVESPA", "IFIX", "Selic", "S&P 500"]]

        print("Initial fields:", values("percentage"))
        page.get_by_label("Initial date").fill("2020-01-01")
        page.get_by_label("End date").fill("2024-12-31")
        ibov.fill("40")
        ibov.press("Tab")
        ifix.fill("50")
        ifix.press("Tab")
        print("After typing 40 in IBOVESPA and 50 in IFIX:")
        print("Visible fields:", values("percentage"))
        print("Sliders:", values("slider"))
        print("Visible total:", page.locator(".allocation-total").inner_text())
        with page.expect_response(lambda result: result.url.endswith("/api/portfolio")) as result:
            page.get_by_role("button", name="Submit portfolio").click()
        print("Submitted:", result.value.request.post_data, "HTTP", result.value.status)
        ifix.fill("101")
        print("Invalid-field alert:", page.get_by_role("alert").all_text_contents())
        with page.expect_response(lambda result: result.url.endswith("/api/portfolio")) as result:
            ifix.press("Enter")
        print("Enter while showing 101 submitted:", result.value.request.post_data, "HTTP", result.value.status)
        print("Success:", page.get_by_text("Settings were received.", exact=False).inner_text())
        page.get_by_text("Read the example data").click()
        for width in (1280, 768):
            page.set_viewport_size({"width": width, "height": 960})
            page.wait_for_timeout(250)
            print(f"Layout {width}:", page.evaluate("""() => ({
                client: document.documentElement.clientWidth,
                scroll: document.documentElement.scrollWidth,
                chartLeft: document.querySelector('.chart-card').getBoundingClientRect().left,
                formLeft: document.querySelector('.portfolio-card').getBoundingClientRect().left,
            })"""))
        browser.close()
finally:
    if vite is not None:
        vite.terminate()
        vite.wait(timeout=10)
    api.terminate()
    api.wait(timeout=10)

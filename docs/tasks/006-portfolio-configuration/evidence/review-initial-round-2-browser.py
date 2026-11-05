"""Review recheck against the live Vite and FastAPI development servers."""

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


def luminance(color):
    rgb = [int(component) / 255 for component in color[4:-1].split(",")]
    linear = [n / 12.92 if n <= .04045 else ((n + .055) / 1.055) ** 2.4 for n in rgb]
    return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))


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
        names = ["IBOVESPA", "IFIX", "Selic", "S&P 500"]
        fields = [page.get_by_label(f"{name} allocation percentage") for name in names]

        def values():
            return [field.input_value() for field in fields]

        assert values() == ["25.00"] * 4
        page.get_by_label("Initial date").fill("2020-01-01")
        page.get_by_label("End date").fill("2024-12-31")
        fields[0].fill("40")
        fields[0].press("Tab")
        fields[1].fill("50")
        fields[1].press("Tab")
        assert values() == ["25.00", "50.00", "12.50", "12.50"]
        assert page.locator(".allocation-total").inner_text() == "100.00%"
        with page.expect_response(lambda result: result.url.endswith("/api/portfolio")) as result:
            page.get_by_role("button", name="Submit portfolio").click()
        submitted = result.value.request.post_data_json
        assert [line["percentage"] for line in submitted["allocations"]] == [25, 50, 12.5, 12.5]
        assert result.value.status == 200
        print("PC-R01 settled fields", values(), "total 100.00%, POST", submitted, "HTTP", result.value.status)

        posts = []
        page.on("request", lambda request: posts.append(request) if request.url.endswith("/api/portfolio") else None)
        fields[1].fill("101")
        fields[1].press("Enter")
        page.wait_for_timeout(200)
        assert not posts
        assert "Enter a percentage" in page.get_by_role("alert").inner_text()
        assert not page.get_by_text("Settings were received.", exact=False).count()
        fields[1].press("Tab")
        assert values() == ["25.00", "50.00", "12.50", "12.50"]
        print("PC-R02 invalid focused draft displayed error, Enter sent zero requests, Tab restored the committed share.")

        page.keyboard.press("Shift+Tab")
        guidance_color = page.locator(".allocation-guidance").evaluate("(node) => getComputedStyle(node).color")
        focus_color = fields[1].evaluate("(node) => getComputedStyle(node).outlineColor")
        assert fields[1].evaluate("(node) => node.matches(':focus-visible')")
        guidance_contrast = 1.05 / (luminance(guidance_color) + .05)
        focus_contrast = 1.05 / (luminance(focus_color) + .05)
        assert guidance_contrast >= 4.5 and focus_contrast >= 3
        print(f"PC-R05 browser computed guidance {guidance_contrast:.2f}:1 and keyboard outline {focus_contrast:.2f}:1 against white.")
        browser.close()
finally:
    if vite is not None:
        vite.terminate()
        vite.wait(timeout=10)
    api.terminate()
    api.wait(timeout=10)

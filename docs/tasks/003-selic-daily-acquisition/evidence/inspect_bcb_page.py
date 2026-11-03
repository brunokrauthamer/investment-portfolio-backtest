import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from playwright.sync_api import sync_playwright
from backend.src.internet_data_getter.selic.source import CHART_URL
with sync_playwright() as p:
 b=p.chromium.launch(headless=True, channel="chromium"); page=b.new_page(); page.goto(CHART_URL,wait_until="domcontentloaded")
 meta=page.locator("#seriesSelecionadas").inner_text(); end=re.findall(r"\b\d{2}/\d{2}/\d{4}\b",meta)[-1]
 page.locator("#dataInicio").fill("01/01/2011"); page.locator("#dataFim").fill(end); page.locator("input.botao[value='Refresh chart']").click()
 image=page.frame_locator("#frmGraficoAlt").locator("img"); image.wait_for(state="visible",timeout=30000); image.evaluate("img => img.complete && img.naturalWidth > 0")
 page.locator("input.botao[value='View values from chart']").click(); print(repr(page.locator("#seriesSelecionadas").inner_text())); print(repr(page.locator("#valoresSeries").inner_text()[:140]))
 b.close()

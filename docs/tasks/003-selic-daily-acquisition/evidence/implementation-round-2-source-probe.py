"""Inspect selected-series metadata and the refreshed table header on the live BCB chart."""
from __future__ import annotations

from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from playwright.sync_api import sync_playwright
from backend.src.internet_data_getter.selic.source import CHART_URL


with sync_playwright() as runtime:
    browser = runtime.chromium.launch(headless=True)
    try:
        page = browser.new_page()
        page.set_default_timeout(30_000)
        page.goto(CHART_URL, wait_until="domcontentloaded")
        initial = page.locator("#seriesSelecionadas").inner_text()
        print("INITIAL_METADATA", repr(initial))
        dates = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", initial)
        end_date = dates[-1]
        page.locator("#dataInicio").fill("01/01/2011")
        page.locator("#dataFim").fill(end_date)
        page.frame_locator("#frmGraficoAlt").locator("form").first.wait_for(state="attached")
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and "atualizarGraficoEstatico" in response.url
        ) as refresh:
            page.locator("input.botao[value='Refresh chart']").click()
        print("REFRESH_STATUS", refresh.value.status)
        page.frame_locator("#frmGraficoAlt").locator("img").wait_for(state="visible")
        page.locator("input.botao[value='View values from chart']").click()
        print("RESULT_METADATA", repr(page.locator("#seriesSelecionadas").inner_text()))
        rows = page.locator("#valoresSeries tr").all()
        for index, row in enumerate(rows[:15]):
            print(f"TABLE_ROW_{index}", repr(row.locator("th, td").all_inner_texts()))
        print("TABLE_HEADER", repr(page.locator("#valoresSeries").inner_text()[:500]))
        page.on("request", lambda request: print(
            "PAGING_REQUEST", request.method, request.url, repr(request.post_data)
        ))
        page.on("response", lambda response: print(
            "PAGING_RESPONSE", response.status, response.url
        ))
        print("NEXT_LINKS", repr(page.get_by_role("link", name="Next", exact=True).evaluate_all(
            "nodes => nodes.map(node => [node.outerHTML, node.getAttribute('onclick')])"
        )))
        page.get_by_role("link", name="Next", exact=True).first.click()
        page.wait_for_load_state("networkidle", timeout=30_000)
        print("AFTER_NEXT_URL", page.url)
        print("AFTER_NEXT_TABLE", repr(page.locator("#valoresSeries").inner_text()[:180]))
    finally:
        browser.close()

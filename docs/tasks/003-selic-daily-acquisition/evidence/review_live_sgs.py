"""Read-only review trace for the SGS series 11 browser workflow."""
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from playwright.sync_api import sync_playwright

from backend.src.internet_data_getter.selic.source import CHART_URL


def trace_request(request):
    parsed = urlparse(request.url)
    if parsed.hostname != 'www3.bcb.gov.br' or not parsed.path.endswith('.do'):
        return
    query = parse_qs(parsed.query)
    fields = parse_qs(request.post_data or '')
    print('REQUEST', request.method, parsed.path.rsplit('/', 1)[-1], query.get('method'),
          {name: fields.get(name) for name in ('dataInicio', 'dataFim', 'hdPagina', 'hdOidSeriesSelecionadas')}, flush=True)


def trace_response(response):
    parsed = urlparse(response.url)
    if parsed.hostname != 'www3.bcb.gov.br' or not parsed.path.endswith('.do'):
        return
    query = parse_qs(parsed.query)
    print('RESPONSE', response.status, parsed.path.rsplit('/', 1)[-1], query.get('method'),
          {key: response.headers.get(key) for key in ('age', 'cache-control', 'x-cache')}, flush=True)


with sync_playwright() as runtime:
    browser = runtime.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(15_000)
    page.on('request', trace_request)
    page.on('response', trace_response)
    page.goto(CHART_URL, wait_until='domcontentloaded', timeout=15_000)
    selected = page.locator('#seriesSelecionadas').inner_text()
    latest = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', selected)[-1]
    buttons = page.locator('input.botao').evaluate_all(
        "nodes => nodes.map(n => [n.value, n.getAttribute('onclick')])"
    )
    print('BUTTONS', buttons, flush=True)
    page.locator('#dataInicio').fill('01/01/2011')
    page.locator('#dataFim').fill(latest)
    if '--wait-for-refresh' in sys.argv:
        page.frame_locator('#frmGraficoAlt').locator('form').first.wait_for(state='attached')
        with page.expect_response(lambda response: response.request.method == 'POST' and
                                  'atualizarGraficoEstatico' in response.url) as refresh_response:
            page.locator("input.botao[value='Refresh chart']").click()
        print('REFRESH STATUS', refresh_response.value.status, flush=True)
    else:
        page.locator("input.botao[value='Refresh chart']").click()
    image = page.frame_locator('#frmGraficoAlt').locator('img')
    image.wait_for(state='visible')
    print('IMAGE', image.evaluate('img => img.complete && img.naturalWidth > 0'), flush=True)
    page.locator("input.botao[value='View values from chart']").click()
    print('RESULT METADATA', repr(page.locator('#seriesSelecionadas').inner_text()), flush=True)
    print('RESULT HEADER', repr(page.locator('#valoresSeries').inner_text()[:115]), flush=True)
    browser.close()

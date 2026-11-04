"""Independently read and page the BCB SGS 11 table for QA comparison."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait


URL = (
    "https://www3.bcb.gov.br/sgspub/consultarvalores/"
    "consultarValoresSeries.do?method=consultarGraficoPorId&hdOidSeriesSelecionadas=11"
)
TIMEOUT = 45


def browser_events(driver):
    for entry in driver.get_log("performance"):
        try:
            yield json.loads(entry["message"])["message"]
        except (KeyError, ValueError, TypeError):
            continue


def successful_post(driver, token):
    requests = {}
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        for event in browser_events(driver):
            method = event.get("method")
            params = event.get("params", {})
            request_id = params.get("requestId")
            if method == "Network.requestWillBeSent" and request_id:
                request = params.get("request", {})
                requests[request_id] = (
                    request.get("method", ""), request.get("url", "")
                )
            elif method == "Network.responseReceived" and request_id in requests:
                verb, url = requests[request_id]
                status = params.get("response", {}).get("status")
                if verb == "POST" and token in url:
                    if not isinstance(status, (int, float)) or not 200 <= status < 400:
                        raise AssertionError(f"{token} returned HTTP {status}: {url}")
                    return {"url": url, "method": verb, "status": status}
        time.sleep(0.1)
    raise AssertionError(f"No successful POST response observed for {token}")


def read_table(driver):
    table = driver.find_element("id", "valoresSeries")
    rows = []
    for tr in table.find_elements("css selector", "tr"):
        cells = [cell.text.strip() for cell in tr.find_elements("css selector", "th, td")]
        if len(cells) == 2 and re.fullmatch(r"\d{2}/\d{2}/\d{4}", cells[0]):
            rows.append(
                {
                    "date": datetime.strptime(cells[0], "%d/%m/%Y").date().isoformat(),
                    "rate_percent_per_day": cells[1].replace(",", "."),
                }
            )
    return table, rows


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("prefs", {"intl.accept_languages": "en-US,en"})
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(TIMEOUT)
    driver.execute_cdp_cmd("Network.enable", {})
    try:
        wait = WebDriverWait(driver, TIMEOUT, poll_frequency=0.1)
        driver.get(URL)
        selected = wait.until(
            lambda d: (e.text if (e := d.find_element("id", "seriesSelecionadas")).is_displayed() else False)
        )
        if "11 Interest rate - Selic" not in selected or "% p.d." not in selected:
            raise AssertionError(f"Unexpected source identity or unit: {selected!r}")
        date_tokens = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", selected)
        if len(date_tokens) < 2:
            raise AssertionError(f"Source metadata has no requested range: {selected!r}")
        latest_text = date_tokens[-1]

        requested_values = {"dataInicio": "01/01/2011", "dataFim": latest_text}
        for element_id, expected in requested_values.items():
            field = driver.find_element("id", element_id)
            field.clear()
            field.send_keys(expected.replace("/", ""))
            if field.get_attribute("value") != expected:
                raise AssertionError(
                    f"{element_id} displays {field.get_attribute('value')!r}, expected {expected!r}"
                )

        frame = wait.until(lambda d: d.find_element("id", "frmGraficoAlt"))
        driver.switch_to.frame(frame)
        wait.until(lambda d: d.find_element("tag name", "form").is_displayed())
        driver.switch_to.default_content()
        driver.find_element("css selector", "input.botao[value='Refresh chart']").click()
        refresh = successful_post(driver, "atualizarGraficoEstatico")
        driver.switch_to.frame(frame)
        chart_image = wait.until(lambda d: d.find_element("tag name", "img"))
        wait.until(
            lambda d: d.execute_script(
                "return arguments[0].complete && arguments[0].naturalWidth > 0", chart_image
            )
        )
        driver.switch_to.default_content()
        driver.find_element("css selector", "input.botao[value='View values from chart']").click()
        wait.until(lambda d: d.find_element("id", "valoresSeries").is_displayed())

        metadata = driver.find_element("id", "seriesSelecionadas").text
        values_text = driver.find_element("id", "valoresSeries").text
        if "Linear" not in metadata or "% p.d." not in values_text:
            raise AssertionError("Values view does not confirm Linear and % p.d.")
        count_match = re.search(r"Found registers by series\s*:\s*([\d.]+)", values_text)
        if not count_match:
            raise AssertionError(f"Source values page has no reported count: {values_text!r}")
        count = int(count_match.group(1).replace(".", ""))
        all_rows = []
        page_summaries = []
        while True:
            table, rows = read_table(driver)
            if not rows:
                raise AssertionError("Source page contains no observations")
            all_rows.extend(rows)
            page_summaries.append({"page": len(page_summaries) + 1, "rows": len(rows)})
            links = driver.find_elements("link text", "Next")
            if not links:
                break
            prior_id = table.id
            links[0].click()
            wait.until(lambda d: d.find_element("id", "valoresSeries").id != prior_id)
            pagination = successful_post(driver, "method=getPagina")

        if len(all_rows) != count:
            raise AssertionError(f"Read {len(all_rows)} observations; source reports {count}")
        if any(a["date"] >= b["date"] for a, b in zip(all_rows, all_rows[1:])):
            raise AssertionError("Source observations are duplicated or not strictly increasing")
        if all_rows[0]["date"][:4] != "2011" or all_rows[-1]["date"] != datetime.strptime(latest_text, "%d/%m/%Y").date().isoformat():
            raise AssertionError("Source observation coverage differs from selected range")
        samples = {
            "first": all_rows[0],
            "middle": all_rows[len(all_rows) // 2],
            "last": all_rows[-1],
        }
        print(
            json.dumps(
                {
                    "source": URL,
                    "source_metadata": selected,
                    "values_metadata": metadata,
                    "latest_text": latest_text,
                    "reported_count": count,
                    "read_count": len(all_rows),
                    "range": [all_rows[0]["date"], all_rows[-1]["date"]],
                    "pages": page_summaries,
                    "refresh_post": refresh,
                    "last_pagination_post": pagination if len(page_summaries) > 1 else None,
                    "samples": samples,
                },
                indent=2,
            )
        )
    finally:
        driver.quit()


if __name__ == "__main__":
    main()

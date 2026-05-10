import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By


REPO_ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def base_url():
    for port in (8000, 0):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), QuietHandler)
            break
        except OSError:
            continue
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(scope="module")
def driver():
    opts = webdriver.ChromeOptions()
    opts.page_load_strategy = "eager"
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1400,900")
    drv = webdriver.Chrome(options=opts)
    drv.set_page_load_timeout(30)
    yield drv
    drv.quit()


def test_landing_page_loads(driver, base_url):
    driver.get(f"{base_url}/index.html")
    time.sleep(1)
    assert "MetaSprint DTA" in driver.title
    assert len(driver.find_elements(By.CSS_SELECTOR, "a.card")) > 2


def test_main_app_bootstraps(driver, base_url):
    driver.get(f"{base_url}/e156-submission/assets/metasprint-dta.html")
    time.sleep(3)
    driver.execute_script(
        """
        const overlay = document.getElementById('onboardOverlay');
        if (overlay) overlay.style.display = 'none';
        """
    )
    state = driver.execute_script(
        """
        return {
          hasRunAnalysis: typeof window.runAnalysis === 'function',
          hasButtons: document.querySelectorAll('button').length,
          hasTabs: document.querySelectorAll('[data-tab], [role="tab"]').length
        };
        """
    )
    assert state["hasRunAnalysis"] is True
    assert state["hasButtons"] > 10
    assert state["hasTabs"] > 0

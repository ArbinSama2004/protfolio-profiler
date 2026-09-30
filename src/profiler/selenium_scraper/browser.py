"""Selenium fetching for JavaScript-rendered sites (React, Next.js, ...)."""

import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

MIN_BODY_CHARS = 200
MAX_SCROLLS = 8


class BrowserSession:
    """One headless Chrome that is reused for every page of a site."""

    def __init__(self, headless: bool = True, wait_seconds: int = 15):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1280,1600")
        options.add_argument("--disable-gpu")
        self.wait_seconds = wait_seconds
        # Selenium 4.6+ downloads a matching chromedriver automatically.
        self.driver = webdriver.Chrome(options=options)

    def get_html(self, url: str) -> str:
        """Load a page, wait for the app to render, scroll to load lazy content."""
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, self.wait_seconds).until(self._has_content)
        except TimeoutException:
            pass  # return whatever rendered; the pipeline decides if it is enough
        self._scroll_to_bottom()
        return self.driver.page_source

    def _has_content(self, driver) -> bool:
        body = driver.find_element(By.TAG_NAME, "body")
        return len(body.text.strip()) > MIN_BODY_CHARS

    def _scroll_to_bottom(self) -> None:
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(MAX_SCROLLS):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.8)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def close(self) -> None:
        self.driver.quit()

    def __enter__(self) -> "BrowserSession":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

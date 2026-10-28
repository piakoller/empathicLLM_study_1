"""Open the study app in a headless browser so Streamlit Community Cloud does not put it to sleep.

A plain HTTP request is not enough: it gets the hosting page, but does not start the app.
If the app is already asleep, the "Yes, get this app back up!" button is clicked and the
script waits until the app has started. Opening the start page saves nothing: a participant
is only stored after the "Angaben zu Ihrer Person" page.

    python .github/scripts/keep_awake.py [url]
"""

import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://empathicllmstudy1.streamlit.app/"
WAKE_BUTTON = "Yes, get this app back up"
APP_TEXT = "Herzlich willkommen"


def app_visible(page) -> bool:
    # On Streamlit Cloud the app itself runs inside an iframe.
    return any(APP_TEXT in (frame.content() or "") for frame in page.frames)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(10_000)

        wake = page.get_by_text(WAKE_BUTTON)
        if wake.count():
            print("App was asleep - waking it up")
            wake.first.click()

        for _ in range(24):                     # up to 4 minutes for the app to start
            if app_visible(page):
                print(f"App is up: {URL}")
                browser.close()
                return 0
            page.wait_for_timeout(10_000)

        print(f"App did not show '{APP_TEXT}' within 4 minutes: {URL}")
        browser.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())

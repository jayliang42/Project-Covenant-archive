#!/usr/bin/env python3
"""Browser regression checks for verified output; never a deployment command.

Playwright is a development-only dependency. The input site and its CSP are
never modified. Only approved static output is served, on loopback, temporarily.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from time import monotonic, sleep
from urllib.parse import quote, unquote, urljoin, urlsplit

WIDTHS = (320, 390, 768, 1024, 1440)


class BrowserCheckError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise BrowserCheckError(code)


class SiteHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass

    def list_directory(self, path: str):
        self.send_error(404)
        return None


@contextmanager
def serve(root: Path):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SiteHandler, directory=str(root))
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "BROWSER_SYMLINK_FORBIDDEN")
        if path.is_file():
            name = path.relative_to(root).as_posix()
            require(name.endswith(".html") or name == "assets/site.css" or (name.startswith("assets/maps/") and name.endswith(".svg")) or (name.startswith("assets/illustrations/") and name.endswith(".jpg")),
                    "BROWSER_UNEXPECTED_SITE_FILE")
            digest.update(name.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def layout(page) -> None:
    state = page.evaluate("""() => {
      let loaded = false;
      try { loaded = document.styleSheets.length === 1 &&
                       !!document.querySelector('link[rel="stylesheet"]').sheet; } catch (_) {}
      return {
        loaded,
        accent: getComputedStyle(document.body).getPropertyValue('--accent').trim(),
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        main: document.querySelectorAll('main').length,
        article: document.querySelectorAll('article.reading-body').length,
        images: [...document.images].every(img => img.complete && img.naturalWidth > 0 && img.alt.trim() && ['file:', location.protocol].includes(new URL(img.currentSrc).protocol)),
        active: document.querySelectorAll('script,iframe,form,input').length
      };
    }""")
    require(state["loaded"] and bool(state["accent"]), "BROWSER_CSS_NOT_LOADED")
    require(not state["overflow"], "BROWSER_HORIZONTAL_OVERFLOW")
    require(state["main"] == state["article"] == 1, "BROWSER_STRUCTURE_INVALID")
    require(state["active"] == 0, "BROWSER_ACTIVE_CONTENT")
    require(state["images"], "BROWSER_IMAGE_NOT_LOADED")
    policy = page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute("content")
    require("script-src 'none'" in (policy or ""), "BROWSER_CSP_MISSING")


def toggle_by_keyboard(page, selector: str) -> None:
    control = page.locator(selector)
    summary = control.locator("summary").first
    summary.focus()
    summary.press("Enter")
    require(control.evaluate("el => el.open"), "BROWSER_MENU_DID_NOT_OPEN")
    layout(page)
    summary.press("Enter")
    require(not control.evaluate("el => el.open"), "BROWSER_MENU_DID_NOT_CLOSE")


def click_navigation(page, selector: str) -> None:
    print(f"browser_navigation={selector}", flush=True)
    link = page.locator(selector).first
    target = urljoin(page.url, link.get_attribute("href") or "")
    require(urlsplit(target).scheme in {"file", "http"}, "BROWSER_BAD_TEST_TARGET")
    link.click()
    page.wait_for_url(target)
    page.wait_for_load_state("load")
    require(unquote(page.url) == unquote(target), "BROWSER_NAVIGATION_FAILED")
    layout(page)


def interactions(page, home: str, output: Path, mode: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.goto(home, wait_until="load")
    page.screenshot(path=str(output / f"{mode}-home.png"))
    click_navigation(page, "a.start-reading")
    original = page.url
    page.screenshot(path=str(output / f"{mode}-reader.png"))
    click_navigation(page, ".reading-pager .next")
    click_navigation(page, ".reading-pager .previous")
    require(page.url == original, "BROWSER_PAGER_ROUNDTRIP_FAILED")

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(original, wait_until="load")
    toggle_by_keyboard(page, ".mobile-navigation details")
    toggle_by_keyboard(page, "details.mobile-toc")
    page.locator("details.mobile-toc > summary").click()
    toc_link = page.locator("details.mobile-toc .reader-toc a").first
    fragment = toc_link.get_attribute("href") or ""
    print("browser_interaction=toc", flush=True)
    toc_link.click()
    page.wait_for_url(urljoin(original, fragment))
    require(page.evaluate("id => !!document.getElementById(id)", unquote(fragment[1:])),
            "BROWSER_TOC_TARGET_MISSING")
    click_navigation(page, ".reading-end a")
    deadline = monotonic() + 5
    while page.evaluate("scrollY") >= 300 and monotonic() < deadline:
        sleep(0.05)
    require(page.evaluate("scrollY") < 300, "BROWSER_BACK_TO_TOP_FAILED")
    page.goto(original, wait_until="load")
    page.screenshot(path=str(output / f"{mode}-mobile.png"))

    page.emulate_media(color_scheme="dark", reduced_motion="reduce")
    require(page.evaluate("getComputedStyle(document.body).backgroundColor") ==
            "rgb(25, 28, 25)", "BROWSER_DARK_MODE_FAILED")
    require(page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") ==
            "auto", "BROWSER_REDUCED_MOTION_FAILED")
    layout(page)
    page.screenshot(path=str(output / f"{mode}-dark.png"))
    page.emulate_media(media="print")
    require(not page.locator(".site-header").is_visible(), "BROWSER_PRINT_HEADER_VISIBLE")
    require(not page.locator(".mobile-navigation").is_visible(), "BROWSER_PRINT_MENU_VISIBLE")
    page.emulate_media(media="screen", color_scheme="light", reduced_motion="no-preference")

    page.goto(home, wait_until="load")
    page.keyboard.press("Tab")
    require(page.locator(".skip-link").evaluate("el => el === document.activeElement"),
            "BROWSER_SKIP_LINK_NOT_FIRST")
    page.keyboard.press("Enter")
    require(page.locator("main").evaluate("el => el === document.activeElement"),
            "BROWSER_SKIP_FOCUS_FAILED")


def run(site: Path, output: Path) -> dict:
    from playwright.sync_api import sync_playwright

    require(site.is_dir() and not site.is_symlink(), "BROWSER_SITE_INVALID")
    site = site.resolve()
    require(not output.resolve().is_relative_to(site), "BROWSER_OUTPUT_INSIDE_SITE")
    before = fingerprint(site)
    pages = sorted(site.rglob("*.html"))
    require(bool(pages) and (site / "index.html").is_file(), "BROWSER_HOME_MISSING")
    output.mkdir(parents=True, exist_ok=False)
    result = {"pages": len(pages), "widths": list(WIDTHS), "layout_checks": 0,
              "protocols": ["file", "http"], "status": "FAIL"}
    errors: list[str] = []
    try:
        with serve(site) as base, sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            result["chromium_version"] = browser.version
            context = browser.new_context(color_scheme="light")
            context.set_default_timeout(15000)

            def route_request(route):
                url = route.request.url
                parsed = urlsplit(url)
                allowed = url.startswith(base)
                if parsed.scheme == "file":
                    allowed = Path(unquote(parsed.path)).resolve().is_relative_to(site)
                if allowed:
                    route.continue_()
                else:
                    errors.append("BROWSER_REMOTE_REQUEST")
                    route.abort()

            context.route("**/*", route_request)
            page = context.new_page()
            page.on("pageerror", lambda _: errors.append("BROWSER_PAGE_ERROR"))
            page.on("requestfailed", lambda _: errors.append("BROWSER_REQUEST_FAILED"))
            page.on("response", lambda r: errors.append("BROWSER_HTTP_ERROR") if r.status >= 400 else None)
            for mode in result["protocols"]:
                for index, path in enumerate(pages):
                    url = path.as_uri() if mode == "file" else base + quote(path.relative_to(site).as_posix())
                    result["last_page_index"] = index
                    result["last_protocol"] = mode
                    page.goto(url, wait_until="load")
                    for width in WIDTHS:
                        result["last_width"] = width
                        page.set_viewport_size({"width": width, "height": 900})
                        layout(page)
                        if width == 390:
                            toggle_by_keyboard(page, ".mobile-navigation details")
                            if page.locator("details.mobile-toc").count():
                                toggle_by_keyboard(page, "details.mobile-toc")
                        result["layout_checks"] += 1
                home = (site / "index.html").as_uri() if mode == "file" else base + "index.html"
                interactions(page, home, output, mode)
                print(f"browser_{mode}_pages={len(pages)}", flush=True)
            context.close()
            browser.close()
        require(not errors, errors[0] if errors else "BROWSER_REQUEST_ERROR")
        require(before == fingerprint(site), "BROWSER_SITE_CHANGED")
        result["status"] = "PASS"
        result["request_errors"] = 0
        return result
    except Exception as error:
        result["error_type"] = type(error).__name__
        trace = error.__traceback__
        while trace is not None:
            if Path(trace.tb_frame.f_code.co_filename).name == Path(__file__).name:
                result["failed_script_line"] = trace.tb_lineno
            trace = trace.tb_next
        result["error_code"] = str(error) if isinstance(error, BrowserCheckError) else "BROWSER_RUNTIME_ERROR"
        raise BrowserCheckError(result["error_code"]) from None
    finally:
        (output / "report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(args.site, args.output)
    except Exception as error:
        code = str(error) if isinstance(error, BrowserCheckError) else "BROWSER_RUNTIME_ERROR"
        print(f"error_code={code}\nbrowser_check=FAIL")
        return 1
    print(f"browser_pages={result['pages']}\nbrowser_layout_checks={result['layout_checks']}")
    print("browser_check=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

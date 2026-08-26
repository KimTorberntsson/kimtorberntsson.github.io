"""Fixtures for the browser tests.

The suite drives a real (headless) Chromium against a running Jekyll build. If
nothing is listening on the base URL, it starts `bundle exec jekyll serve`
itself and shuts it down afterwards, so `./tests/run.sh` works from a cold
start.
"""

import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest
from playwright.sync_api import sync_playwright

DEFAULT_BASE_URL = "http://localhost:4000"
SERVER_BOOT_TIMEOUT = 180  # a full build of ~700 photos is not quick


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        default=os.environ.get("BASE_URL", DEFAULT_BASE_URL),
        help="Site to test against (default: %s)" % DEFAULT_BASE_URL,
    )
    parser.addoption(
        "--headed",
        action="store_true",
        help="Show the browser window instead of running headless.",
    )
    parser.addoption(
        "--slowmo",
        type=int,
        default=0,
        help="Milliseconds to pause between actions, for watching a run.",
    )


def _responds(url, timeout=2.0):
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except urllib.error.HTTPError:
        return True  # answering at all is enough
    except Exception:
        return False


@pytest.fixture(scope="session")
def base_url(request):
    url = request.config.getoption("--base-url").rstrip("/")

    if _responds(url):
        yield url
        return

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    port = urllib.parse.urlsplit(url).port or 4000
    print("\nnothing on %s, starting jekyll..." % url)
    server = subprocess.Popen(
        ["bundle", "exec", "jekyll", "serve", "--port", str(port)],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    deadline = time.time() + SERVER_BOOT_TIMEOUT
    while time.time() < deadline:
        if server.poll() is not None:
            pytest.fail("jekyll serve exited with code %s" % server.returncode)
        if _responds(url):
            break
        time.sleep(1.0)
    else:
        server.terminate()
        pytest.fail("jekyll did not come up on %s within %ds" % (url, SERVER_BOOT_TIMEOUT))

    try:
        yield url
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()


@pytest.fixture(scope="session")
def production_site(tmp_path_factory):
    """A build made with the real config, in its own directory.

    Tests about absolute URLs cannot read _site: `jekyll serve` regenerates it
    continuously with site.url pointing at localhost, so whether the files hold
    production URLs depends on which process wrote them last.
    """
    import shutil
    import subprocess

    # run.sh builds once and shares it, so the parallel workers do not each
    # spend ten seconds rebuilding the same site.
    shared = os.environ.get("PRODUCTION_SITE")
    if shared and os.path.isdir(os.path.join(shared, "assets")):
        yield shared
        return

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest = tmp_path_factory.mktemp("production-site")
    result = subprocess.run(
        ["bundle", "exec", "jekyll", "build", "--destination", str(dest), "--quiet"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.fail("jekyll build failed:\n%s" % (result.stderr or result.stdout))
    yield str(dest)
    shutil.rmtree(str(dest), ignore_errors=True)


@pytest.fixture(scope="session")
def playwright():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright, request):
    browser = playwright.chromium.launch(
        headless=not request.config.getoption("--headed"),
        slow_mo=request.config.getoption("--slowmo"),
    )
    yield browser
    browser.close()


def _viewer(browser, base_url, **context_args):
    from viewer import Viewer

    context = browser.new_context(**context_args)
    page = context.new_page()
    cdp = context.new_cdp_session(page)
    view = Viewer(page, cdp, base_url)
    try:
        yield view
    finally:
        context.close()


@pytest.fixture
def desktop(browser, base_url):
    """A laptop-sized window with a mouse and a keyboard."""
    yield from _viewer(browser, base_url, viewport={"width": 1440, "height": 900})


@pytest.fixture
def phone(playwright, browser, base_url):
    """An iPhone 13, with touch input and a coarse pointer."""
    yield from _viewer(browser, base_url, **playwright.devices["iPhone 13"])


@pytest.fixture(autouse=True)
def no_browser_errors(request):
    """Fail any test that logged a console error or an uncaught exception.

    The viewers are resolved during setup rather than teardown. That makes them
    dependencies of this fixture, so teardown runs in reverse order and the
    pages are still alive when the check happens.
    """
    views = [
        request.getfixturevalue(name)
        for name in ("desktop", "phone")
        if name in request.fixturenames
    ]
    # A test module may define its own fixture called `phone`, which will not be
    # a Viewer, so only check the ones that collect errors.
    views = [v for v in views if hasattr(v, "errors")]
    yield
    for view in views:
        assert not view.errors, "browser reported errors: %s" % view.errors

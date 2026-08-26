"""The footer.

It used to be `position: fixed` at `z-index: -2`, sitting behind main's white
background so that it was revealed as you reached the end of the page, with
main carrying a bottom margin to reserve the space. It is an ordinary element
at the end of the document now.
"""

import pytest

PAGES = ["/", "/gallery/", "/archive/", "/about/"]


@pytest.fixture
def phone_page(browser, base_url, playwright):
    context = browser.new_context(**playwright.devices["iPhone 13"])
    page = context.new_page()
    page.base = base_url
    yield page
    context.close()


def layout(page):
    return page.evaluate("""() => {
        var f = document.querySelector('footer');
        var m = document.querySelector('main');
        var a = document.querySelector('article');
        var fs = getComputedStyle(f);
        var r = f.getBoundingClientRect(), mr = m.getBoundingClientRect();
        return {position: fs.position, zIndex: fs.zIndex,
                mainZ: getComputedStyle(m).zIndex,
                articleZ: getComputedStyle(a).zIndex,
                mainMarginBottom: getComputedStyle(m).marginBottom,
                gapAfterMain: Math.round(r.top - mr.bottom),
                top: Math.round(r.top), height: Math.round(r.height),
                viewport: window.innerHeight,
                docHeight: document.documentElement.scrollHeight};
    }""")


@pytest.mark.parametrize("path", PAGES)
def test_the_footer_is_an_ordinary_element(phone_page, path):
    phone_page.goto(phone_page.base + path, wait_until="load")
    phone_page.wait_for_timeout(400)
    state = layout(phone_page)
    assert state["position"] == "static", "footer is %s" % state["position"]
    assert state["zIndex"] == "auto", "footer still has z-index %s" % state["zIndex"]


@pytest.mark.parametrize("path", PAGES)
def test_nothing_is_pushed_behind_anything(phone_page, path):
    """article was -1 and main 0, purely to let the fixed footer hide behind."""
    phone_page.goto(phone_page.base + path, wait_until="load")
    state = layout(phone_page)
    assert state["mainZ"] == "auto", "main z-index is %s" % state["mainZ"]
    assert state["articleZ"] == "auto", "article z-index is %s" % state["articleZ"]


@pytest.mark.parametrize("path", PAGES)
def test_the_footer_follows_the_content_with_no_gap(phone_page, path):
    """main carried a bottom margin to reserve room for the fixed footer."""
    phone_page.goto(phone_page.base + path, wait_until="load")
    state = layout(phone_page)
    assert state["mainMarginBottom"] in ("0px", "auto"), \
        "main still reserves %s below itself" % state["mainMarginBottom"]
    assert state["gapAfterMain"] == 0, \
        "%dpx of gap between the content and the footer" % state["gapAfterMain"]


@pytest.mark.parametrize("path", PAGES)
def test_the_footer_is_not_on_screen_until_you_reach_the_end(phone_page, path):
    """The old one was always at the bottom of the viewport, behind the page."""
    phone_page.goto(phone_page.base + path, wait_until="load")
    phone_page.wait_for_timeout(400)
    state = layout(phone_page)
    assert state["top"] >= state["viewport"], \
        "footer is already in view at the top of %s" % path


@pytest.mark.parametrize("path", PAGES)
def test_scrolling_to_the_end_reaches_the_footer(phone_page, path):
    phone_page.goto(phone_page.base + path, wait_until="load")
    phone_page.wait_for_timeout(400)
    phone_page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    phone_page.wait_for_timeout(700)
    state = layout(phone_page)
    assert state["top"] < state["viewport"], "footer never comes into view on %s" % path
    assert state["height"] > 20, "footer collapsed to %dpx" % state["height"]


def test_the_footer_links_are_still_there(phone_page):
    phone_page.goto(phone_page.base + "/about/", wait_until="load")
    count = phone_page.evaluate("document.querySelectorAll('footer a').length")
    assert count == 7, "expected seven social links, found %d" % count

"""The footer.

It used to be `position: fixed` at `z-index: -2`, sitting behind main's white
background so that it was revealed as you reached the end of the page, with
main carrying a bottom margin to reserve the space. It is an ordinary element
at the end of the document now.
"""

import pytest

from conftest import sample_pixels

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
    """A photo band above the footer was tried and dropped: the backdrop is
    fixed to the viewport, so the gap at the bottom exposed an arbitrary lower
    slice of the image rather than a composed crop."""
    phone_page.goto(phone_page.base + path, wait_until="load")
    state = layout(phone_page)
    assert state["mainMarginBottom"] in ("0px", "auto"), \
        "main should not reserve space below itself: %s" % state["mainMarginBottom"]
    assert state["gapAfterMain"] == 0, \
        "%dpx between the content and the footer" % state["gapAfterMain"]


def test_bouncing_past_the_end_cannot_reveal_the_backdrop(phone_page):
    """The backdrop is fixed, so an elastic bounce would lift the content off
    the bottom of the window and show the photo under the footer."""
    phone_page.goto(phone_page.base + "/about/", wait_until="load")
    behavior = phone_page.evaluate(
        "getComputedStyle(document.documentElement).overscrollBehaviorY")
    assert behavior == "none", "overscroll-behavior-y is %s" % behavior


FOOTER_GREY = (211, 211, 211)   # LightGrey


def test_the_bottom_of_the_window_is_footer_coloured(phone_page):
    """Sub-pixel rounding of the document height left a sliver of photo under
    the footer even without any overscroll."""
    phone_page.goto(phone_page.base + "/about/", wait_until="load")
    phone_page.wait_for_timeout(500)
    phone_page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    phone_page.wait_for_timeout(700)

    size = phone_page.evaluate("[innerWidth, innerHeight]")
    colour = sample_pixels(phone_page, {"x": 0, "y": size[1] - 3,
                                        "width": size[0], "height": 3})
    for got, want in zip(colour, FOOTER_GREY):
        assert abs(got - want) <= 6, \
            "the last rows are %s, not the footer's %s" % (colour, list(FOOTER_GREY))


def test_a_page_shorter_than_the_window_still_ends_in_the_footer(phone_page):
    """The same thing overscroll exposes, reachable without gesture support:
    force the document short and look at what fills the rest of the window."""
    phone_page.goto(phone_page.base + "/about/", wait_until="load")
    phone_page.add_style_tag(content="""
        header #hero { height: 0 !important; min-height: 0 !important; }
        main article > * { display: none !important; }
        main { min-height: 0 !important; }
    """)
    phone_page.wait_for_timeout(700)

    size = phone_page.evaluate("[innerWidth, innerHeight]")
    exposed = phone_page.evaluate("""() => Math.round(innerHeight
        - document.querySelector('footer').getBoundingClientRect().bottom)""")
    assert exposed > 50, "expected the window to extend past the footer"

    colour = sample_pixels(phone_page, {"x": 0, "y": size[1] - exposed + 4,
                                        "width": size[0], "height": exposed - 8})
    for got, want in zip(colour, FOOTER_GREY):
        assert abs(got - want) <= 6, \
            "below the footer is %s, not the footer's %s" % (colour, list(FOOTER_GREY))


@pytest.mark.parametrize("path", PAGES)
def test_the_footer_contains_its_own_content(phone_page, path):
    """footer had a fixed height its content outgrew once the links became
    inline-block for the tap targets, so it spilled past the grey bar and
    showed as a sliver of photo underneath."""
    phone_page.goto(phone_page.base + path, wait_until="load")
    phone_page.wait_for_timeout(300)
    spill = phone_page.evaluate("""() => {
        var f = document.querySelector('footer').getBoundingClientRect();
        var inner = [...document.querySelectorAll('footer *')]
            .map(e => e.getBoundingClientRect().bottom);
        return Math.round(Math.max(...inner) - f.bottom);
    }""")
    assert spill <= 0, "footer content spills %dpx past the bar" % spill


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
    links = phone_page.evaluate(
        "[...document.querySelectorAll('footer a')].map(a => a.getAttribute('aria-label'))")
    assert links == ["Facebook", "GitHub", "LinkedIn", "Instagram", "Tumblr"], \
        "unexpected footer links: %s" % links
    for gone in ("Twitter", "Email me"):
        assert gone not in links

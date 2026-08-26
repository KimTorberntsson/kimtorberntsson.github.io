"""Inline SVG icons.

scripts/svg-transform.js used to fetch every icon over XHR and swap the <img>
for inline SVG, which cost 30 round trips a page, flashed while it worked, and
was the only reason jQuery was loaded at all. The icons are now Jekyll includes
of inline SVG.
"""

import pytest

PAGES = ["/", "/gallery/", "/archive/", "/about/"]


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append("pageerror: %s" % e))
    page.on("console",
            lambda m: page.errors.append("console: %s" % m.text) if m.type == "error" else None)
    page.svg_requests = []
    page.on("request",
            lambda r: page.svg_requests.append(r.url) if r.url.endswith(".svg") else None)
    page.base = base_url
    yield page
    context.close()


@pytest.mark.parametrize("path", PAGES)
def test_icons_cost_no_requests(page, path):
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(600)
    assert page.svg_requests == [], "icons were fetched: %s" % page.svg_requests[:5]


@pytest.mark.parametrize("path", PAGES)
def test_no_icon_is_left_as_an_image(page, path):
    page.goto(page.base + path, wait_until="load")
    assert page.evaluate("document.querySelectorAll('img.svg').length") == 0
    assert page.evaluate("document.querySelectorAll('svg').length") > 5


@pytest.mark.parametrize("path", PAGES)
def test_jquery_is_gone(page, path):
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(400)
    assert page.evaluate("typeof window.jQuery") == "undefined"
    assert page.evaluate("typeof window.$") == "undefined"
    assert not page.errors, page.errors


@pytest.mark.parametrize("path", PAGES)
def test_every_icon_actually_renders(page, path):
    """A stripped viewBox or a dropped class would leave a zero sized SVG."""
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(400)
    empty = page.evaluate("""() => [...document.querySelectorAll('svg')]
        .filter(s => { var r = s.getBoundingClientRect();
                       return r.width < 2 || r.height < 2; })
        .map(s => s.getAttribute('class'))""")
    assert not empty, "collapsed icons: %s" % empty


def test_hover_still_recolours_an_icon(page):
    """The colour classes fill the SVG, which only works if it is inline."""
    page.goto(page.base + "/gallery/", wait_until="load")
    page.wait_for_timeout(400)
    resting = page.eval_on_selector("nav li.blue-icon a .svg", "e => getComputedStyle(e).fill")
    page.locator("nav li.blue-icon a").first.hover()
    page.wait_for_timeout(250)
    hovered = page.eval_on_selector("nav li.blue-icon a .svg", "e => getComputedStyle(e).fill")
    assert resting != hovered, "hover no longer changes the icon colour"
    assert hovered == "rgb(0, 182, 255)", hovered


@pytest.mark.parametrize("path,label", [("/gallery/", "Gallery"),
                                        ("/archive/", "Archive"),
                                        ("/about/", "About"),
                                        ("/", "Blog")])
def test_the_current_section_is_marked_and_enlarged(page, path, label):
    """#active was an id used as a styling hook; it is a class on the link now."""
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(400)
    state = page.evaluate("""() => {
        var links = [...document.querySelectorAll('nav a')];
        var active = links.filter(a => a.classList.contains('is-active'));
        var plain = links.find(a => !a.classList.contains('is-active'));
        var size = a => { var r = a.querySelector('.svg').getBoundingClientRect();
                          return Math.round(r.width); };
        return {count: active.length,
                text: active.length ? active[0].textContent.trim() : null,
                current: active.length ? active[0].getAttribute('aria-current') : null,
                activeSize: active.length ? size(active[0]) : null,
                plainSize: size(plain)};
    }""")
    assert state["count"] == 1, "expected exactly one active nav item, got %d" % state["count"]
    assert state["text"] == label
    assert state["current"] == "page"
    assert state["activeSize"] > state["plainSize"], \
        "active icon is not enlarged: %s vs %s" % (state["activeSize"], state["plainSize"])


def test_icon_only_links_have_accessible_names(page):
    """Inline SVG has no alt, so the labels moved onto the links."""
    page.goto(page.base + "/gallery/", wait_until="load")
    unnamed = page.evaluate("""() => [...document.querySelectorAll('footer a, #logo a, #arrow-down a')]
        .filter(a => !a.getAttribute('aria-label') && !a.textContent.trim())
        .map(a => a.getAttribute('href'))""")
    assert not unnamed, "links with no accessible name: %s" % unnamed


def test_anchor_scrolling_is_native_and_smooth(page):
    """Replaces scripts/smooth-scroll.js, a 1000ms jQuery animate."""
    page.goto(page.base + "/gallery/", wait_until="load")
    assert page.evaluate(
        "getComputedStyle(document.documentElement).scrollBehavior") == "smooth"


def test_the_skip_link_reaches_the_content(page):
    page.goto(page.base + "/gallery/", wait_until="load")
    page.wait_for_timeout(300)
    page.evaluate("document.querySelector('#arrow-down a').click()")
    page.wait_for_timeout(1200)
    assert page.evaluate("window.scrollY") > 200, "the skip link did not scroll"

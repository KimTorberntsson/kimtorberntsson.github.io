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
    # Not the current section: that one is already coloured at rest.
    selector = "nav li.red-icon a"
    resting = page.eval_on_selector(selector + " .svg", "e => getComputedStyle(e).fill")
    page.locator(selector).first.hover()
    page.wait_for_timeout(250)
    hovered = page.eval_on_selector(selector + " .svg", "e => getComputedStyle(e).fill")
    assert resting != hovered, "hover no longer changes the icon colour"
    assert hovered == "rgb(255, 0, 0)", hovered


@pytest.mark.parametrize("path,label", [("/gallery/", "Gallery"),
                                        ("/archive/", "Archive"),
                                        ("/about/", "About"),
                                        ("/subscribe/", "Subscribe"),
                                        ("/", "Blog")])
def test_the_current_section_is_marked_and_coloured(page, path, label):
    """#active was an id used as a styling hook; it is a class on the link now."""
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(400)
    state = page.evaluate("""() => {
        var links = [...document.querySelectorAll('nav a')];
        var active = links.filter(a => a.classList.contains('is-active'));
        var plain = links.find(a => !a.classList.contains('is-active'));
        var fill = a => getComputedStyle(a.querySelector('.svg')).fill;
        return {count: active.length,
                text: active.length ? active[0].textContent.trim() : null,
                current: active.length ? active[0].getAttribute('aria-current') : null,
                activeFill: active.length ? fill(active[0]) : null,
                plainFill: fill(plain)};
    }""")
    assert state["count"] == 1, "expected exactly one active nav item, got %d" % state["count"]
    assert state["text"] == label
    assert state["current"] == "page"
    assert state["activeFill"] != state["plainFill"], \
        "the current section is not coloured: %s" % state["activeFill"]
    assert state["plainFill"] == "rgb(0, 0, 0)", \
        "the other icons should stay black, got %s" % state["plainFill"]


def test_icon_only_links_have_accessible_names(page):
    """Inline SVG has no alt, so the labels moved onto the links."""
    page.goto(page.base + "/gallery/", wait_until="load")
    unnamed = page.evaluate("""() => [...document.querySelectorAll('footer a, #logo a')]
        .filter(a => !a.getAttribute('aria-label') && !a.textContent.trim())
        .map(a => a.getAttribute('href'))""")
    assert not unnamed, "links with no accessible name: %s" % unnamed


def test_anchor_scrolling_is_native_and_smooth(page):
    """Replaces scripts/smooth-scroll.js, a 1000ms jQuery animate."""
    page.goto(page.base + "/gallery/", wait_until="load")
    assert page.evaluate(
        "getComputedStyle(document.documentElement).scrollBehavior") == "smooth"


@pytest.mark.parametrize("path", PAGES)
def test_the_decorative_arrows_are_gone(page, path):
    """The down arrow existed to skip a 100vh hero. The hero is a band now, so
    the content is already on screen and there is nothing to skip. The up arrow
    duplicated what the browser and the OS already do, and overlapped the
    article between 60 and 65em."""
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(300)
    assert page.evaluate(
        "document.querySelectorAll('#arrow-up, #arrow-down').length") == 0
    assert page.evaluate(
        "[...document.querySelectorAll('a')].filter(a => a.getAttribute('href') === '#main'"
        " || a.getAttribute('href') === '#header').length") == 0, \
        "a link still points at the removed anchors"


@pytest.mark.parametrize("width", [320, 375, 390, 414])
def test_nav_labels_fit_their_items(browser, base_url, width):
    """A fixed 3em item was narrower than "Gallery" and "Archive", so those
    labels spilled into the gap between items, leaving about 3px between them.
    """
    context = browser.new_context(viewport={"width": width, "height": 800})
    page = context.new_page()
    page.goto(base_url + "/gallery/", wait_until="load")
    page.wait_for_timeout(500)

    items = page.evaluate("""() => [...document.querySelectorAll('nav li')].map(li => {
        var a = li.querySelector('a');
        var text = [...a.childNodes].find(n => n.nodeType === 3 && n.textContent.trim());
        var range = document.createRange();
        range.selectNode(text);
        var tr = range.getBoundingClientRect(), lr = li.getBoundingClientRect();
        return {label: text.textContent.trim(),
                item: lr.width, text: tr.width,
                left: lr.left, right: lr.right,
                top: lr.top, bottom: lr.bottom,
                textLeft: tr.left, textRight: tr.right};
    })""")
    context.close()

    spilling = [i for i in items if i["text"] > i["item"] + 1]
    assert not spilling, "labels wider than their item at %dpx: %s" % (
        width, [(i["label"], "%.0f in %.0f" % (i["text"], i["item"])) for i in spilling])

    # And the labels must not run into each other.
    # Share a row means overlapping vertically, not having the same top: the
    # current section's icon is 3em against everyone else's 2.5em, so it is
    # taller and sits higher.
    ordered = sorted(items, key=lambda i: i["left"])
    first = ordered[0]
    stacked = [i["label"] for i in ordered
               if i["top"] >= first["bottom"] or i["bottom"] <= first["top"]]
    assert not stacked, "the nav wrapped at %dpx, below the first row: %s" % (
        width, stacked)

    for earlier, later in zip(ordered, ordered[1:]):
        gap = later["textLeft"] - earlier["textRight"]
        assert gap > 2, "%r and %r are %.1fpx apart at %dpx" % (
            earlier["label"], later["label"], gap, width)


def test_the_nav_holds_only_pages(browser, base_url):
    """RSS used to sit here. It is not a page: clicking it dumps XML, which reads
    as a broken link to anyone who is not a feed reader user, and it spent a
    fifth of the mobile nav doing so."""
    context = browser.new_context(viewport={"width": 390, "height": 800})
    page = context.new_page()
    page.goto(base_url + "/gallery/", wait_until="load")
    page.wait_for_timeout(400)
    hrefs = page.evaluate(
        "[...document.querySelectorAll('nav a')].map(a => a.getAttribute('href'))")
    context.close()

    assert hrefs == ["/", "/gallery", "/archive", "/about", "/subscribe/"], hrefs
    assert not [h for h in hrefs if h.endswith(".xml")], \
        "the nav still links to a raw file: %s" % hrefs


def test_the_feed_is_still_reachable_and_discoverable(browser, base_url):
    """Moving it out of the nav must not hide it: readers find it through the
    alternate link, people through the footer."""
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.goto(base_url + "/gallery/", wait_until="load")
    page.wait_for_timeout(400)
    state = page.evaluate("""() => {
        var alt = document.querySelector('link[rel="alternate"]');
        var footer = [...document.querySelectorAll('footer a')]
            .map(a => a.getAttribute('href'));
        return {alternate: alt && alt.getAttribute('type'),
                alternateHref: alt && alt.getAttribute('href'),
                subscribeInNav: [...document.querySelectorAll('nav a')]
                    .map(a => a.getAttribute('href'))
                    .filter(h => h === '/subscribe/').length};
    }""")
    context.close()

    assert state["alternate"] == "application/rss+xml", state
    assert state["alternateHref"].endswith("/feed.xml"), state
    assert state["subscribeInNav"] == 1, \
        "the nav does not lead to the subscribe page"


@pytest.mark.parametrize("width", [390, 1280])
def test_the_nav_row_is_centred_in_its_bar(browser, base_url, width):
    """The row is a flex container, and flex defaults to align-items: stretch,
    which grew the items from 64px to 80px and left their contents sitting at
    the top of the bar."""
    context = browser.new_context(viewport={"width": width, "height": 800})
    page = context.new_page()
    page.goto(base_url + "/gallery/", wait_until="load")
    page.wait_for_timeout(500)
    box = page.evaluate("""() => {
        var nav = document.querySelector('header nav').getBoundingClientRect();
        var li = document.querySelector('header nav li').getBoundingClientRect();
        return {navHeight: nav.height, itemHeight: li.height,
                above: li.top - nav.top, below: nav.bottom - li.bottom};
    }""")
    context.close()

    assert box["itemHeight"] < box["navHeight"] - 8, \
        "items are stretching to fill the bar: %.0f of %.0f" % (
            box["itemHeight"], box["navHeight"])
    assert abs(box["above"] - box["below"]) <= 6, \
        "the row sits %.0fpx from the top and %.0fpx from the bottom at %dpx" % (
            box["above"], box["below"], width)


@pytest.mark.parametrize("width", [320, 390, 768, 1280])
def test_the_nav_labels_share_a_baseline(browser, base_url, width):
    """The current section's icon is 3em against everyone else's 2.5em. Centring
    the items dropped that one's label out of line; aligning baselines keeps the
    labels on one line and lets the taller icon rise above them, which is what
    inline-block gave for free."""
    context = browser.new_context(viewport={"width": width, "height": 600})
    page = context.new_page()
    page.goto(base_url + "/gallery/", wait_until="load")
    page.wait_for_timeout(500)
    baselines = page.evaluate("""() => [...document.querySelectorAll('nav li')].map(li => {
        var a = li.querySelector('a');
        var text = [...a.childNodes].find(n => n.nodeType === 3 && n.textContent.trim());
        var range = document.createRange();
        range.selectNode(text);
        return Math.round(range.getBoundingClientRect().bottom);
    })""")
    icons = page.evaluate(
        "[...document.querySelectorAll('nav li svg')].map(s => Math.round(s.getBoundingClientRect().height))")
    context.close()

    assert len(set(baselines)) == 1, \
        "labels sit on %d different baselines at %dpx: %s" % (
            len(set(baselines)), width, baselines)
    assert len(set(icons)) == 1, \
        "icons differ in size again, which breaks the baseline: %s" % icons


@pytest.mark.parametrize("width", [390, 1280])
def test_the_bar_is_opaque_across_its_whole_width(browser, base_url, width):
    """nav is a flex container, and a flex container establishes its own
    formatting context, so it is placed beside a float rather than letting the
    float overlap it. That pushed the bar's white background to the right of the
    logo and the fixed backdrop showed through behind it.
    """
    from conftest import sample_pixels

    context = browser.new_context(viewport={"width": width, "height": 400},
                                  device_scale_factor=1)
    page = context.new_page()
    page.goto(base_url + "/gallery/", wait_until="load")
    page.wait_for_timeout(700)

    bar = page.evaluate("""() => {
        var r = document.querySelector('header nav').getBoundingClientRect();
        return {top: Math.round(r.top), bottom: Math.round(r.bottom)};
    }""")
    # The far left, clear of the logo glyph, is where the backdrop showed.
    colour = sample_pixels(page, {"x": 0, "y": bar["top"] + 2,
                                 "width": 6, "height": bar["bottom"] - bar["top"] - 4})
    context.close()

    for channel in colour:
        assert channel >= 250, \
            "the left edge of the bar is %s, not white, at %dpx" % (colour, width)

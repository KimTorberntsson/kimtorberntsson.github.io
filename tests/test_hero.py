"""The header hero photo.

Its size and position live in css/main.sass; head.html contributes only which
photo. That split matters: as a `background:` shorthand the per-page rule reset
background-position to top left on every page, which is what cropped the
subject off wide screens.
"""

import pytest

PHOTO_WIDTH, PHOTO_HEIGHT = 1631, 1080   # the backgrounds are roughly 3:2
CAP_PX = 1600                # css/main.sass caps the hero at 100em


def hero(page):
    return page.evaluate("""() => {
        var el = document.querySelector('#background');
        var s = getComputedStyle(el);
        var r = el.getBoundingClientRect();
        return {position: s.backgroundPosition, size: s.backgroundSize,
                repeat: s.backgroundRepeat, image: s.backgroundImage,
                width: Math.round(r.width), height: Math.round(r.height),
                left: Math.round(r.left),
                right: Math.round(window.innerWidth - r.right),
                overflow: document.documentElement.scrollWidth > window.innerWidth};
    }""")


def upscale(state):
    """How far the photo has to be blown up to cover the backdrop."""
    return max(state["width"] / PHOTO_WIDTH, state["height"] / PHOTO_HEIGHT)


@pytest.fixture
def at_width(browser, base_url):
    made = []

    def open_at(width, height=900, path="/gallery/"):
        context = browser.new_context(viewport={"width": width, "height": height})
        made.append(context)
        page = context.new_page()
        page.goto(base_url + path, wait_until="load")
        page.wait_for_timeout(400)
        return page

    yield open_at
    for context in made:
        context.close()


def test_the_hero_crop_is_centred(at_width):
    """Defaulting to top left kept a strip of sky and cut the subject."""
    state = hero(at_width(1440))
    assert state["position"] == "50% 50%", \
        "hero is not centred (%s) -- did a background shorthand come back?" \
        % state["position"]
    assert state["size"] == "cover"
    assert state["repeat"] == "no-repeat"


def test_the_hero_actually_has_a_photo(at_width):
    state = hero(at_width(1440))
    assert "/assets/backgrounds/" in state["image"], state["image"]


@pytest.mark.parametrize("width", [390, 768, 1280, 1440])
def test_the_hero_is_edge_to_edge_up_to_the_cap(at_width, width):
    state = hero(at_width(width))
    assert state["width"] == width
    assert state["left"] == 0


@pytest.mark.parametrize("width", [1700, 1920, 2560, 3440])
def test_the_hero_stops_growing_on_wide_screens(at_width, width):
    state = hero(at_width(width))
    assert state["width"] == CAP_PX, "hero is %dpx wide at %dpx" % (state["width"], width)
    assert abs(state["left"] - state["right"]) <= 2, \
        "hero is off centre: %d vs %d" % (state["left"], state["right"])


@pytest.mark.parametrize("width", [2560, 3440])
def test_the_cap_keeps_the_photo_from_being_blown_up(at_width, width):
    """The reason the cap survives now that the backdrop is full height: the
    photos are only 1631px wide, so an uncapped ultrawide would upscale them.
    """
    state = hero(at_width(width))
    uncapped = {"width": width, "height": state["height"]}
    assert upscale(state) < upscale(uncapped), "the cap does not reduce upscaling"
    assert upscale(state) < 1.6, "photo is upscaled %.2fx at %dpx" % (upscale(state), width)


@pytest.mark.parametrize("width", [390, 1440, 2560, 3440])
def test_no_horizontal_overflow(at_width, width):
    assert not hero(at_width(width))["overflow"], "page scrolls sideways at %dpx" % width


# ------------------------------------------------------------------- the band

def band_height(page):
    """The visible strip of photo: the gap between the nav and the content.

    Not the backdrop's own height. The backdrop is a fixed, full viewport
    element behind the page; what a reader sees is whatever the opaque nav and
    article leave uncovered.
    """
    return page.evaluate("""() => {
        var nav = document.querySelector('header nav').getBoundingClientRect();
        var main = document.querySelector('main').getBoundingClientRect();
        var clamp = y => Math.max(0, Math.min(window.innerHeight, y));
        // Clamped to the viewport: the nav and the content scroll together, so
        // the distance between them never changes. What shrinks is how much of
        // that gap is still on screen.
        return Math.round(clamp(main.top) - clamp(nav.bottom));
    }""")


@pytest.mark.parametrize("width,height", [(390, 664), (768, 1024), (1440, 900)])
def test_the_band_is_a_strip_not_a_whole_screen(at_width, width, height):
    """It used to be height: 100vh, so every page opened with a full screen of
    photo that had to be scrolled past."""
    band = band_height(at_width(width, height))
    assert band < height * 0.72, "band takes %dpx of a %dpx viewport" % (band, height)
    assert band > 150, "band is only %dpx" % band


@pytest.mark.parametrize("width,height", [(390, 664), (1280, 800), (1440, 900)])
def test_content_is_visible_without_scrolling(at_width, width, height):
    page = at_width(width, height)
    visible = page.evaluate("""() => {
        var a = document.querySelector('article').getBoundingClientRect();
        return Math.max(0, Math.round(window.innerHeight - a.top));
    }""")
    assert visible > 150, "only %dpx of content above the fold at %dx%d" % (
        visible, width, height)


def test_the_band_survives_a_phone_held_landscape(at_width):
    """45% of a 390px tall viewport is a sliver, hence the short-viewport floor."""
    assert band_height(at_width(844, 390)) >= 150


def test_the_backdrop_stays_put_while_you_scroll(at_width):
    """The whole point: background-attachment: fixed would be the obvious way to
    do this and is the way that does not work, since iOS Safari ignores it. A
    fixed element behind opaque content behaves the same and works everywhere.
    """
    page = at_width(1280, 800)
    assert page.evaluate(
        "getComputedStyle(document.querySelector('#background')).position") == "fixed"

    tops = []
    for y in (0, 200, 500):
        page.evaluate("window.scrollTo(0, %d)" % y)
        page.wait_for_timeout(250)
        tops.append(page.evaluate(
            "Math.round(document.querySelector('#background').getBoundingClientRect().top)"))
    assert tops == [0, 0, 0], "the backdrop moved with the page: %s" % tops


def test_the_content_scrolls_over_the_photo(at_width):
    page = at_width(1280, 800)
    bands = []
    for y in (0, 150, 300):
        page.evaluate("window.scrollTo(0, %d)" % y)
        page.wait_for_timeout(250)
        bands.append(band_height(page))
    assert bands[0] > bands[1] > bands[2], \
        "the content is not covering the photo as it scrolls: %s" % bands
    assert bands[0] - bands[2] > 200, "barely any travel: %s" % bands


def test_the_backdrop_sits_behind_the_page(at_width):
    page = at_width(1280, 800)
    assert page.evaluate(
        "getComputedStyle(document.querySelector('#background')).zIndex") == "-1"
    for selector in ("main", "footer", "header nav"):
        opaque = page.evaluate("""sel => {
            var bg = getComputedStyle(document.querySelector(sel)).backgroundColor;
            return bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent';
        }""", selector)
        assert opaque, "%s is not opaque, so the backdrop shows through it" % selector


def test_the_band_depth_does_not_depend_on_browser_chrome(at_width):
    """svh is the viewport with the mobile chrome showing, so the band does not
    resize as that chrome hides and the page does not reflow under the reader."""
    page = at_width(390, 664)
    css = page.evaluate("""() => [...document.styleSheets]
        .flatMap(s => { try { return [...s.cssRules]; } catch (e) { return []; } })
        .map(r => r.cssText).filter(t => t.includes('#hero')).join(' ')""")
    assert "svh" in css, "the band is not using svh: %s" % css[:300]


# ------------------------------------------------------------- the masthead

# The palest heroes on the site: white bedding, snow, overcast sky. If a scrim
# holds up anywhere it has to hold up here.
PALE_HEROES = ["/2019/05/06/update-from-the-baby-bubble.html",
               "/2019/04/24/astrid.html",
               "/",
               "/gallery/"]


def _contrast_with_white(rgb):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    lum = 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])
    return 1.05 / (lum + 0.05)


def test_the_title_is_the_hero_not_the_article(at_width):
    page = at_width(1280)
    state = page.evaluate("""() => ({
        hero: document.querySelectorAll('#hero h1').length,
        article: document.querySelectorAll('article h1').length,
        colour: getComputedStyle(document.querySelector('#hero h1')).color,
    })""")
    assert state["hero"] == 1, "expected one title in the hero"
    assert state["article"] == 0, "the title is still in the article as well"
    assert state["colour"] == "rgb(255, 255, 255)"


def test_the_date_appears_on_posts_only(at_width):
    """A section page has no date to show."""
    post = at_width(1280, path="/2019/04/24/astrid.html")
    assert post.evaluate("!!document.querySelector('#hero .hero-date')"), \
        "a post should carry its date under the title"
    section = at_width(1280, path="/gallery/")
    assert not section.evaluate("!!document.querySelector('#hero .hero-date')"), \
        "a section page has no date, so it should not render one"


def test_the_index_masthead_is_not_a_section_label(at_width):
    """page.title there is "Blog Posts", which read as a label competing with the
    first post's own title right below it."""
    page = at_width(1280, path="/")
    title = page.evaluate("document.querySelector('#hero h1').textContent.trim()")
    assert title != "Blog Posts", "the index masthead is still the section label"
    assert title, "the index masthead is empty"


@pytest.mark.parametrize("path", PALE_HEROES)
def test_white_text_stays_legible_over_a_pale_photo(at_width, path):
    """The risk with a masthead over arbitrary photos. Measured from the pixels
    beside the text, since a gradient is paint and tells you nothing in the
    computed style."""
    from conftest import sample_pixels

    page = at_width(1280, path=path)
    page.wait_for_timeout(700)
    spots = page.evaluate("""() => {
        var h1 = document.querySelector('#hero h1').getBoundingClientRect();
        var d = document.querySelector('#hero .hero-date');
        var beside = r => ({x: 20, y: Math.round(r.top), width: 140,
                            height: Math.max(8, Math.round(r.height))});
        return {title: beside(h1),
                date: d ? beside(d.getBoundingClientRect()) : null};
    }""")

    # 40px counts as large text under WCAG, so 3:1; the date is normal text.
    title = _contrast_with_white(sample_pixels(page, spots["title"]))
    assert title >= 3.0, "the title is %.2f:1 against its photo on %s" % (title, path)

    if spots["date"]:
        date = _contrast_with_white(sample_pixels(page, spots["date"]))
        assert date >= 4.5, "the date is %.2f:1 against its photo on %s" % (date, path)


def test_the_scrim_only_darkens_the_bottom(at_width):
    """It has to leave the top of the photo alone, or the band just looks murky."""
    from conftest import sample_pixels

    page = at_width(1280, path="/2016/02/28/point-reyes.html")
    page.wait_for_timeout(700)
    band = page.evaluate("""() => {
        var r = document.querySelector('#hero').getBoundingClientRect();
        return {top: Math.round(r.top), bottom: Math.round(r.bottom),
                height: Math.round(r.height)};
    }""")
    high = sample_pixels(page, {"x": 20, "y": band["top"] + 10,
                                "width": 200, "height": 40})
    low = sample_pixels(page, {"x": 20, "y": band["bottom"] - 50,
                               "width": 200, "height": 40})
    assert sum(low) < sum(high), \
        "the bottom of the band (%s) is not darker than the top (%s)" % (low, high)


def test_every_page_hero_photo_exists(production_site, base_url):
    """The photo is named after the page title, so renaming a page silently
    breaks its hero unless the page carries a `hero` override. That trap has
    fired twice, hence the test."""
    import os
    import re
    import urllib.parse
    import urllib.request

    missing = []
    for root, _, files in os.walk(production_site):
        for name in files:
            if not name.endswith(".html"):
                continue
            path = os.path.join(root, name)
            html = open(path, encoding="utf-8", errors="replace").read()
            found = re.search(r'#background\s*\{\s*background-image:\s*url\("([^"]+)"\)', html)
            if not found:
                continue
            url = base_url + urllib.parse.quote(found.group(1), safe="/:%")
            request = urllib.request.Request(url, method="HEAD")
            try:
                if urllib.request.urlopen(request, timeout=20).status != 200:
                    missing.append((path[len(production_site):], found.group(1)))
            except Exception:
                missing.append((path[len(production_site):], found.group(1)))
    assert not missing, "pages whose hero photo does not exist: %s" % missing[:6]


@pytest.mark.parametrize("path", ["/", "/about/", "/gallery/", "/archive/"])
def test_the_backdrop_never_reaches_the_bottom_of_the_window(at_width, path):
    """An elastic overscroll on iOS lifts the content off the bottom of the
    window while the fixed backdrop stays, so the photo appeared under the
    footer. overscroll-behavior does not stop Safari's document bounce, and a
    box-shadow painted past the end of the document is clipped away with it.

    So the backdrop simply does not reach that far any more. It is only ever
    visible in the gap between the nav and the content, which is always in the
    upper part of the screen, and nothing can reveal what is not there.
    """
    page = at_width(1280, path=path)
    room = page.evaluate("""() => {
        var bg = document.querySelector('#background').getBoundingClientRect();
        return Math.round(window.innerHeight - bg.bottom);
    }""")
    assert room > 60, \
        "the backdrop stops only %dpx above the bottom of the window on %s" % (room, path)


def test_the_backdrop_still_covers_the_band(at_width):
    """It has to stop short of the bottom without stopping short of the photo."""
    page = at_width(1280)
    state = page.evaluate("""() => {
        var bg = document.querySelector('#background').getBoundingClientRect();
        var hero = document.querySelector('#hero').getBoundingClientRect();
        return {backdropBottom: Math.round(bg.bottom),
                heroBottom: Math.round(hero.bottom)};
    }""")
    assert state["backdropBottom"] >= state["heroBottom"], \
        "the backdrop ends at %d but the band runs to %d" % (
            state["backdropBottom"], state["heroBottom"])


@pytest.mark.parametrize("path", ["/gallery/", "/archive/", "/about/", "/"])
def test_the_title_line_box_contains_its_descenders(at_width, path):
    """reset.css sets line-height: 1 on everything, so the glyphs spilled out of
    their own box. Nothing noticed until the box sat flush with the bottom of
    the photo: the tail of a "y" or "g" then landed on the white content below,
    in white, and vanished."""
    page = at_width(1280, path=path)
    metrics = page.evaluate("""() => {
        var h1 = document.querySelector('#hero h1');
        var s = getComputedStyle(h1);
        var c = document.createElement('canvas').getContext('2d');
        c.font = s.fontWeight + ' ' + s.fontSize + ' ' + s.fontFamily;
        var m = c.measureText(h1.textContent.trim());
        return {fontSize: parseFloat(s.fontSize),
                lineHeight: parseFloat(s.lineHeight),
                fontDescent: m.fontBoundingBoxDescent,
                fontAscent: m.fontBoundingBoxAscent};
    }""")
    needed = metrics["fontAscent"] + metrics["fontDescent"]
    assert metrics["lineHeight"] >= needed, \
        "the line box is %.0fpx but the font needs %.0fpx on %s" % (
            metrics["lineHeight"], needed, path)

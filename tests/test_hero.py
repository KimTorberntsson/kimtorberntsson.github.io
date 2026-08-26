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
    assert band < height * 0.6, "band takes %dpx of a %dpx viewport" % (band, height)
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
        .map(r => r.cssText).filter(t => t.includes('padding-bottom')).join(' ')""")
    assert "svh" in css, "the band is not using svh: %s" % css[:300]

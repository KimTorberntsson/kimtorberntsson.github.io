"""The header hero photo.

Its size and position live in css/main.sass; head.html contributes only which
photo. That split matters: as a `background:` shorthand the per-page rule reset
background-position to top left on every page, which is what cropped the
subject off wide screens.
"""

import pytest

PHOTO_ASPECT = 1631 / 1080   # the backgrounds are all roughly 3:2
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


def visible_fraction(state):
    """How much of the photo's height survives background-size: cover."""
    box = state["width"] / state["height"]
    return min(1, PHOTO_ASPECT / box)


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
    """A 3:2 photo in a 2.8:1 box loses nearly half its height."""
    state = hero(at_width(width))
    assert state["width"] == CAP_PX, "hero is %dpx wide at %dpx" % (state["width"], width)
    assert abs(state["left"] - state["right"]) <= 2, \
        "hero is off centre: %d vs %d" % (state["left"], state["right"])
    assert visible_fraction(state) > 0.8, \
        "only %.0f%% of the photo survives at %dpx" % (visible_fraction(state) * 100, width)


def test_capping_does_not_step(at_width):
    """The breakpoint equals the cap, so the hero stops rather than jumping."""
    just_under = visible_fraction(hero(at_width(CAP_PX - 1)))
    just_over = visible_fraction(hero(at_width(CAP_PX + 40)))
    assert abs(just_under - just_over) < 0.02, \
        "visible fraction jumps at the breakpoint: %.2f -> %.2f" % (just_under, just_over)


@pytest.mark.parametrize("width", [390, 1440, 2560, 3440])
def test_no_horizontal_overflow(at_width, width):
    assert not hero(at_width(width))["overflow"], "page scrolls sideways at %dpx" % width


def test_the_full_bleed_case_would_have_been_much_worse(at_width):
    """Guards the reasoning behind the cap, so it is not undone by accident."""
    state = hero(at_width(2560))
    uncapped = {"width": 2560, "height": state["height"]}
    assert visible_fraction(uncapped) < 0.6, "the cap is no longer earning its place"

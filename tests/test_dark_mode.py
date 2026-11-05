"""Dark mode.

The palette lives in css/main.sass as custom properties on :root, restated by a
single `prefers-color-scheme: dark` block. There is no toggle and no script:
the page follows the reader's system setting.

Two things are worth holding still. The light rendering must not drift now that
every colour is reached through var(), so the first test pins the literals that
were in the stylesheets before. And the accents must stay legible once the
ground flips, which is not automatic: purple and dark blue measure 2.8:1 and
1.6:1 at their light values on a dark page.
"""

import pytest

from conftest import sample_pixels

POST = "/2026/11/05/halloween-at-kolmarden.html"

# The literals that were in css/main.sass and css/text.sass before the palette
# moved into custom properties. Light must render exactly as it always has.
LIGHT_PALETTE = [
    (POST, "article", "background-color", "rgb(255, 255, 255)"),
    (POST, "main", "background-color", "rgb(255, 255, 255)"),
    (POST, "header nav", "background-color", "rgb(255, 255, 255)"),
    (POST, "footer", "background-color", "rgb(211, 211, 211)"),
    (POST, "body", "color", "rgb(51, 51, 51)"),
    (POST, ".colophon", "color", "rgb(79, 79, 79)"),
    (POST, ".post-nav-label", "color", "rgb(106, 106, 106)"),
    ("/archive/", ".date-link", "color", "rgb(95, 95, 95)"),
    ("/archive/", ".year-heading", "color", "rgb(106, 106, 106)"),
    ("/2019/04/24/astrid.html", "blockquote small", "color", "rgb(111, 111, 111)"),
    ("/subscribe/", ".feed-address", "background-color", "rgb(244, 244, 242)"),
    ("/subscribe/", ".feed-address button", "background-color", "rgb(255, 255, 255)"),
    ("/subscribe/", ".feed-address button", "border-top-color", "rgba(0, 0, 0, 0.2)"),
    ("/subscribe/", ".feed-address button", "color", "rgba(0, 0, 0, 0.6)"),
]

ACCENTS = ["--blue", "--purple", "--orange", "--red", "--green", "--pink",
           "--dark-blue"]


@pytest.fixture
def scheme(browser, base_url):
    """Open a page with the system set to light or to dark."""
    made = []

    def open_at(colour_scheme, path=POST):
        context = browser.new_context(color_scheme=colour_scheme,
                                      viewport={"width": 1100, "height": 900})
        made.append(context)
        page = context.new_page()
        page.goto(base_url + path, wait_until="load")
        return page

    yield open_at
    for context in made:
        context.close()


def luminance(rgb):
    def channel(value):
        value = value / 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse(colour):
    """'#B061FF' or 'rgb(1, 2, 3)' to a tuple."""
    colour = colour.strip()
    if colour.startswith("#"):
        colour = colour.lstrip("#")
        return tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))
    inside = colour[colour.index("(") + 1:colour.index(")")]
    return tuple(int(float(part)) for part in inside.replace(",", " ").split()[:3])


def test_light_palette_is_unchanged(scheme):
    page, current, wrong = None, None, []
    for path, selector, prop, expected in LIGHT_PALETTE:
        if path != current:
            page = scheme("light", path)
            current = path
        got = page.eval_on_selector(
            selector, "(el, p) => getComputedStyle(el).getPropertyValue(p)", prop)
        if got != expected:
            wrong.append("%s %s: %s, want %s" % (selector, prop, got, expected))
    assert not wrong, "light rendering drifted: %s" % wrong


def test_color_scheme_follows_the_system(scheme):
    """Without this the canvas behind an elastic overscroll stays white, and
    form controls keep their light styling on a dark page."""
    for want in ("light", "dark"):
        page = scheme(want)
        got = page.evaluate(
            "getComputedStyle(document.documentElement).colorScheme")
        assert got == want, "color-scheme is %s with the system set to %s" % (got, want)


@pytest.mark.parametrize("selector", ["article", "main", "header nav", "footer"])
def test_dark_surfaces_are_dark(scheme, selector):
    page = scheme("dark")
    rgb = parse(page.eval_on_selector(
        selector, "el => getComputedStyle(el).backgroundColor"))
    assert luminance(rgb) < 0.05, "%s is %s on a dark page" % (selector, rgb)


def test_dark_ink_reads_against_the_page(scheme):
    page = scheme("dark")
    ink = parse(page.eval_on_selector("body", "el => getComputedStyle(el).color"))
    ground = parse(page.eval_on_selector(
        "article", "el => getComputedStyle(el).backgroundColor"))
    assert contrast(ink, ground) >= 7.0, \
        "body text is %.2f:1 on the article" % contrast(ink, ground)


def test_dark_accents_clear_aa(scheme):
    """Only dark is asserted. On white, blue and green sit near 2.3:1 and
    orange at 2.9:1 -- that predates this work and is inherent to the brand
    colours, so pinning it here would fail for a reason dark mode did not
    cause."""
    page = scheme("dark")
    ground = parse(page.eval_on_selector(
        "article", "el => getComputedStyle(el).backgroundColor"))
    weak = {}
    for name in ACCENTS:
        value = page.evaluate(
            "n => getComputedStyle(document.documentElement).getPropertyValue(n)",
            name)
        ratio = contrast(parse(value), ground)
        if ratio < 4.5:
            weak[name] = "%s at %.2f:1" % (value.strip(), ratio)
    assert not weak, "accents below AA on the dark page: %s" % weak


def test_no_light_panel_survives_in_dark(scheme):
    """A paint-level check, not a computed one. Anything the palette missed
    shows up as a bright rectangle whatever its rules say."""
    page = scheme("dark", "/subscribe/")
    box = page.eval_on_selector(".feed-address", """el => {
        var r = el.getBoundingClientRect();
        return {x: r.x, y: r.y, width: r.width, height: r.height};
    }""")
    rgb = sample_pixels(page, box)
    assert luminance(rgb) < 0.15, "the feed address panel paints %s in dark" % (rgb,)

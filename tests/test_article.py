"""Content inside a post: inline images and code blocks."""

import pytest

IMAGE_POSTS = [
    "/2015/12/04/five-short-movie-reviews.html",
    "/2015/11/01/sublime-setup-for-latex.html",
    "/2015/09/06/this-blog-is-built-using-jekyll.html",
    "/2015/09/09/about-the-chromecast.html",
]
CODE_POST = "/2015/11/01/sublime-setup-for-latex.html"
WIDTHS = [390, 768, 1280]


@pytest.fixture
def at_width(browser, base_url):
    made = []

    def open_at(path, width, height=900):
        context = browser.new_context(viewport={"width": width, "height": height})
        made.append(context)
        page = context.new_page()
        page.goto(base_url + path, wait_until="load")
        page.wait_for_timeout(900)
        return page

    yield open_at
    for context in made:
        context.close()


IMAGES = """() => [...document.querySelectorAll('p img')].map(i => {
    var r = i.getBoundingClientRect();
    var col = i.closest('p').getBoundingClientRect();
    var style = getComputedStyle(i.closest('p'));
    var inner = col.width - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    return {src: i.src.split('/').pop(), natural: i.naturalWidth,
            shown: r.width, column: inner};
})"""


@pytest.mark.parametrize("path", IMAGE_POSTS)
@pytest.mark.parametrize("width", WIDTHS)
def test_inline_images_are_never_stretched(at_width, path, width):
    """min-width: 80% forced every image to 80% of the column, whether or not it
    had the pixels for it."""
    images = at_width(path, width).evaluate(IMAGES)
    if not images:
        pytest.skip("no inline images on %s" % path)
    stretched = [i for i in images
                 if i["natural"] and i["shown"] / i["natural"] > 1.02]
    assert not stretched, "upscaled: %s" % [
        (i["src"], "%d -> %d" % (i["natural"], i["shown"])) for i in stretched]


@pytest.mark.parametrize("width", WIDTHS)
def test_a_large_image_fills_the_column(at_width, width):
    """The old 10% margins sat on top of the paragraph's own 5% padding, so
    images used 281px of a 390px phone column."""
    images = at_width(IMAGE_POSTS[0], width).evaluate(IMAGES)
    big = [i for i in images if i["natural"] > i["column"]]
    assert big, "expected an image wider than the column at %dpx" % width
    for image in big:
        assert image["shown"] == pytest.approx(image["column"], abs=2), \
            "%s uses %.0f of a %.0f column" % (image["src"], image["shown"], image["column"])


@pytest.mark.parametrize("width", WIDTHS)
def test_a_small_image_keeps_its_own_size(at_width, width):
    images = at_width("/2015/09/06/this-blog-is-built-using-jekyll.html", width).evaluate(IMAGES)
    small = [i for i in images if i["natural"] and i["natural"] < i["column"]]
    if not small:
        pytest.skip("no image narrower than the column at %dpx" % width)
    for image in small:
        assert image["shown"] == pytest.approx(image["natural"], abs=2), \
            "%s is %.0f wide but its source is %d" % (
                image["src"], image["shown"], image["natural"])


@pytest.mark.parametrize("width", WIDTHS)
def test_code_blocks_only_scroll_when_they_need_to(at_width, width):
    """overflow: scroll reserves a scrollbar gutter unconditionally."""
    page = at_width(CODE_POST, width)
    state = page.evaluate("""() => {
        var h = document.querySelector('.highlight');
        if (!h) return null;
        var s = getComputedStyle(h);
        return {overflowX: s.overflowX, overflowY: s.overflowY};
    }""")
    if state is None:
        pytest.skip("no code block on %s" % CODE_POST)
    assert state["overflowX"] == "auto", state


@pytest.mark.parametrize("width", WIDTHS)
def test_code_blocks_do_not_push_the_page_sideways(at_width, width):
    page = at_width(CODE_POST, width)
    assert not page.evaluate(
        "document.documentElement.scrollWidth > window.innerWidth"), \
        "the page scrolls sideways at %dpx" % width


def test_gallery_thumbnails_describe_themselves(at_width):
    """The captions were already in the front matter for the viewer."""
    page = at_width("/2019/04/24/astrid.html", 1280)
    alts = page.evaluate(
        "[...document.querySelectorAll('.thumb')].map(i => i.getAttribute('alt'))")
    assert alts, "no thumbnails on that post"
    assert all(a and a.strip() for a in alts), "thumbnails without alt text: %s" % alts

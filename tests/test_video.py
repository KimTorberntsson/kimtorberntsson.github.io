"""Embedded videos.

The iframes carry width="560" height="315" -- a true 16:9 -- but with CSS
`width: 80%` the width shrank with the column while the height stayed at 315px.
On a phone that produced a 286x315 box, taller than wide, so YouTube letterboxed
the video into a strip.
"""

import pytest

POSTS = ["/2015/11/15/radical-face.html", "/2016/01/24/when-the-ship-comes-in.html"]
SIXTEEN_NINE = 16 / 9


@pytest.fixture
def at_width(browser, base_url):
    made = []

    def open_at(width, path, height=900):
        context = browser.new_context(viewport={"width": width, "height": height})
        made.append(context)
        page = context.new_page()
        page.goto(base_url + path, wait_until="domcontentloaded")
        page.wait_for_timeout(700)
        return page

    yield open_at
    for context in made:
        context.close()


def frames(page):
    return page.evaluate("""() => [...document.querySelectorAll('.video iframe')].map(f => {
        var r = f.getBoundingClientRect();
        return {width: r.width, height: r.height,
                loading: f.loading, title: f.title,
                border: getComputedStyle(f).borderTopWidth};
    })""")


@pytest.mark.parametrize("path", POSTS)
@pytest.mark.parametrize("width", [390, 414, 768, 1024, 1440])
def test_videos_keep_a_16_9_box(at_width, path, width):
    found = frames(at_width(width, path))
    assert found, "no video iframes on %s" % path
    for i, f in enumerate(found):
        ratio = f["width"] / f["height"]
        assert ratio == pytest.approx(SIXTEEN_NINE, abs=0.03), \
            "video %d is %.0fx%.0f (aspect %.2f) at %dpx" \
            % (i, f["width"], f["height"], ratio, width)


@pytest.mark.parametrize("path", POSTS)
def test_videos_are_not_taller_than_wide_on_a_phone(at_width, path):
    """The symptom that made this obvious."""
    for f in frames(at_width(390, path)):
        assert f["width"] > f["height"], "video is portrait: %.0fx%.0f" % (f["width"], f["height"])


def test_videos_use_the_column_width(at_width):
    page = at_width(1440, POSTS[0])
    used = page.evaluate("""() => {
        var f = document.querySelector('.video iframe').getBoundingClientRect();
        var a = document.querySelector('article').getBoundingClientRect();
        return f.width / a.width;
    }""")
    assert used > 0.9, "video only uses %.0f%% of the column" % (used * 100)


def test_videos_are_deferred_and_labelled(at_width):
    """A YouTube embed is heavy, and an unlabelled iframe is invisible to a
    screen reader."""
    for f in frames(at_width(1440, POSTS[0])):
        assert f["loading"] == "lazy"
        assert f["title"], "iframe has no title"


def test_videos_have_no_default_border(at_width):
    for f in frames(at_width(1440, POSTS[0])):
        assert f["border"] == "0px", "iframe border is %s" % f["border"]

"""How the blog is navigated."""

import pytest


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.base = base_url
    yield page
    context.close()


# ---------------------------------------------------------------- stale anchors


@pytest.mark.parametrize("fragment", ["#main", "#header"])
def test_an_old_anchor_url_does_not_hide_the_top_of_the_page(page, fragment):
    """The skip-the-hero arrow linked to #main and the back-to-top arrow to
    #header. Both arrows are gone, but the targets remained, so any address
    still carrying #main -- anyone's history, a shared link -- scrolled 552px
    down on load and the nav and the hero were simply not there."""
    page.goto(page.base + "/" + fragment, wait_until="load")
    page.wait_for_timeout(1500)
    state = page.evaluate("""() => {
        var nav = document.querySelector('header nav').getBoundingClientRect();
        return {scrollY: Math.round(window.scrollY),
                navTop: Math.round(nav.top)};
    }""")
    assert state["scrollY"] == 0, \
        "%s scrolled the page %dpx on load" % (fragment, state["scrollY"])
    assert state["navTop"] == 0, "the nav is at %dpx" % state["navTop"]

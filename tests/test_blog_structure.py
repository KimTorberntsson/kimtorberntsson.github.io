"""How the blog is navigated.

There used to be two overlapping ways in: paging the front page five posts at a
time through eight pages, and the archive. The paging gave no sense of position,
cost 5.9 screens to show 5 posts, and duplicated the archive's job badly.

Each surface has one job now: the front page carries the newest posts in full,
and the archive is the complete list.
"""

import pytest

FRONT_PAGE_POSTS = 10


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


# ----------------------------------------------------------------- front page


def test_the_front_page_carries_several_posts_in_full(page):
    """"Nice to see more than one entry without clicking too much"."""
    page.goto(page.base + "/", wait_until="load")
    page.wait_for_timeout(1500)
    state = page.evaluate("""() => ({
        posts: document.querySelectorAll('.post').length,
        withPhotos: [...document.querySelectorAll('.post')]
            .filter(p => p.querySelector('.photo-gallery')).length,
        bodyText: [...document.querySelectorAll('.post p')].length,
    })""")
    assert state["posts"] == FRONT_PAGE_POSTS, \
        "the front page shows %d posts" % state["posts"]
    assert state["withPhotos"] >= 5, "the posts should carry their photo galleries"
    assert state["bodyText"] > 20, "the posts should carry their text, not summaries"


def test_the_front_page_hands_off_to_the_archive(page):
    page.goto(page.base + "/", wait_until="load")
    page.wait_for_timeout(1200)
    link = page.evaluate("""() => {
        var a = document.querySelector('.see-all a');
        if (!a) return null;
        var r = a.getBoundingClientRect();
        return {href: a.getAttribute('href'), text: a.textContent.trim(),
                hasIcon: !!a.querySelector('svg'),
                width: Math.round(r.width), height: Math.round(r.height)};
    }""")
    assert link, "no hand-off link at the end of the front page"
    assert link["href"] == "/archive/", link["href"]
    assert link["hasIcon"], "the link should carry the archive icon"
    assert min(link["width"], link["height"]) >= 44, \
        "the link is a %dx%d tap target" % (link["width"], link["height"])


def test_there_is_no_pagination_left(production_site):
    """Eight pages of full posts with only unlabelled arrows to move between
    them, and no way to tell where you were.

    Checked against a fresh build rather than the served site: jekyll does not
    delete output whose generator is gone, so a stale _site went on serving
    /blog/page2/ for a while after the plugin came out."""
    import os

    assert not os.path.isdir(os.path.join(production_site, "blog")), \
        "the paginated pages are still being generated"


def test_no_post_carries_two_links_to_itself(page):
    """Each entry had a "To post page" link under it as well as its title."""
    page.goto(page.base + "/", wait_until="load")
    page.wait_for_timeout(1200)
    duplicated = page.evaluate("""() => {
        var out = [];
        document.querySelectorAll('.post').forEach(post => {
            var hrefs = [...post.querySelectorAll('a')]
                .map(a => a.getAttribute('href'))
                .filter(h => h && /^\\/\\d{4}\\//.test(h));
            var counts = {};
            hrefs.forEach(h => { counts[h] = (counts[h] || 0) + 1; });
            Object.keys(counts).forEach(h => { if (counts[h] > 1) out.push(h); });
        });
        return out;
    }""")
    assert not duplicated, "posts linking to themselves twice: %s" % duplicated

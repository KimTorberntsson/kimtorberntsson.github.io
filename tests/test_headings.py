"""Page titles.

Every page title used to be a link to the page you were already on: a control
that announces itself, takes a tab stop, and does nothing. The
underline-on-hover animation existed only to decorate them.
"""

import pytest

PAGES = ["/", "/archive/", "/gallery/", "/about/", "/404.html",
         "/2019/04/24/astrid.html"]


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.base = base_url
    yield page
    context.close()


@pytest.mark.parametrize("path", PAGES)
def test_no_link_points_at_the_page_it_is_on(page, path):
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(300)
    selfish = page.evaluate("""() => {
        var here = location.pathname;
        return [...document.querySelectorAll('article a, h1 a')]
            .filter(a => {
                var href = a.getAttribute('href');
                return href === here || href === here.replace(/index\\.html$/, '');
            })
            .map(a => a.getAttribute('href') + ' :: ' + a.textContent.trim().slice(0, 30));
    }""")
    assert not selfish, "self-links on %s: %s" % (path, selfish)


@pytest.mark.parametrize("path", PAGES)
def test_the_title_is_plain_text(page, path):
    page.goto(page.base + path, wait_until="load")
    state = page.evaluate("""() => {
        var h = document.querySelector('article h1');
        return h ? {text: h.textContent.trim(), links: h.querySelectorAll('a').length} : null;
    }""")
    assert state, "no h1 on %s" % path
    assert state["text"], "empty title on %s" % path
    assert state["links"] == 0, "the title on %s is still a link" % path


def test_post_titles_on_listings_are_still_links(page):
    """Those are real navigation and keep the underline animation."""
    page.goto(page.base + "/", wait_until="load")
    page.wait_for_timeout(400)
    links = page.evaluate(
        "[...document.querySelectorAll('h2 a')].map(a => a.getAttribute('href'))")
    assert len(links) >= 3, "expected several post links on the index: %s" % links
    assert all(l and l != "/" for l in links), links


def test_the_underline_animation_survives_where_it_is_earned(page):
    page.goto(page.base + "/", wait_until="load")
    page.wait_for_timeout(400)
    width = page.evaluate("""() => {
        var a = document.querySelector('h2 a');
        return getComputedStyle(a, ':after').content !== 'none';
    }""")
    assert width, "h2 links lost their underline animation"


def test_the_dead_h1_animation_is_gone(page):
    """It only ever decorated the self-links."""
    page.goto(page.base + "/about/", wait_until="load")
    rules = page.evaluate("""() => [...document.styleSheets]
        .flatMap(s => { try { return [...s.cssRules]; } catch (e) { return []; } })
        .map(r => r.selectorText || '')
        .filter(sel => /(^|,\\s*)h1 a/.test(sel))""")
    assert not rules, "h1 anchor rules still present: %s" % rules


@pytest.mark.parametrize("path", PAGES)
def test_the_title_keeps_the_tone_it_had_as_a_link(page, path):
    """`a { color: black; opacity: 0.6 }` was tinting the title. Dropping the
    link would have turned every title solid black."""
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(300)
    shade = page.evaluate("""() => {
        var h = document.querySelector('article h1');
        var c = getComputedStyle(h).color;
        var m = c.match(/[\\d.]+/g).map(Number);
        var alpha = m.length > 3 ? m[3] : 1;
        // Flatten onto the white the article sits on.
        return Math.round(255 - (255 - m[0]) * alpha);
    }""")
    assert 90 <= shade <= 115, \
        "the title on %s renders as %d on white, expected about 102" % (path, shade)


def test_the_title_and_the_post_links_read_as_one_family(page):
    """They matched before, both being black at 0.6."""
    page.goto(page.base + "/", wait_until="load")
    page.wait_for_timeout(400)
    shades = page.evaluate("""() => {
        var flatten = el => {
            var s = getComputedStyle(el);
            var m = s.color.match(/[\\d.]+/g).map(Number);
            var alpha = (m.length > 3 ? m[3] : 1) * parseFloat(s.opacity);
            return Math.round(255 - (255 - m[0]) * alpha);
        };
        return {title: flatten(document.querySelector('article h1')),
                post: flatten(document.querySelector('h2 a'))};
    }""")
    assert abs(shades["title"] - shades["post"]) <= 8, \
        "title renders %d and post links %d" % (shades["title"], shades["post"])

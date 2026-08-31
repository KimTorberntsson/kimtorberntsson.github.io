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
        var h = document.querySelector('#hero h1');
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
def test_the_title_sits_on_the_photo(page, path):
    """The title is the hero's masthead now, not the first thing in the
    article."""
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(400)
    state = page.evaluate("""() => {
        var hero = document.querySelector('#hero h1');
        return {inHero: !!hero,
                text: hero ? hero.textContent.trim() : null,
                colour: hero ? getComputedStyle(hero).color : null,
                inArticle: document.querySelectorAll('article h1').length};
    }""")
    assert state["inHero"], "no title in the hero on %s" % path
    assert state["text"], "the hero title is empty on %s" % path
    assert state["colour"] == "rgb(255, 255, 255)", \
        "the hero title is %s, not white" % state["colour"]
    assert state["inArticle"] == 0, \
        "%s still has a title inside the article too" % path


def test_the_post_links_share_the_body_ink(page):
    """Post titles are links, so they must not drift from the body ink."""
    page.goto(page.base + "/", wait_until="load")
    page.wait_for_timeout(400)
    shades = page.evaluate("""() => {
        var flatten = el => {
            var s = getComputedStyle(el);
            var m = s.color.match(/[\\d.]+/g).map(Number);
            var alpha = (m.length > 3 ? m[3] : 1) * parseFloat(s.opacity);
            return Math.round(255 - (255 - m[0]) * alpha);
        };
        return {body: flatten(document.body),
                post: flatten(document.querySelector('h2 a'))};
    }""")
    assert abs(shades["body"] - shades["post"]) <= 8, \
        "body ink renders %d and post links %d" % (shades["body"], shades["post"])


CONTRAST_ROLES = [
    ("/2015/11/01/sublime-setup-for-latex.html", "body link", "article p a"),
    ("/", "post title", "h2 a"),
    ("/archive/", "archive title", ".list-posts p"),
    ("/archive/", "archive date", ".date-link"),
    ("/archive/", "year heading", ".year-heading"),
    ("/2015/11/15/radical-face.html", "blockquote cite", "blockquote small"),
]


def _contrast(page, selector):
    """WCAG contrast of a role against the white it sits on."""
    flat = page.evaluate("""sel => {
        var el = document.querySelector(sel);
        if (!el) return null;
        var s = getComputedStyle(el);
        var m = s.color.match(/[\\d.]+/g).map(Number);
        var alpha = m.length > 3 ? m[3] : 1;
        var chain = 1, node = el;
        while (node && node !== document.documentElement) {
            chain *= parseFloat(getComputedStyle(node).opacity);
            node = node.parentElement;
        }
        var eff = alpha * chain;
        return {rgb: [0, 1, 2].map(i => 255 - (255 - m[i]) * eff),
                size: parseFloat(s.fontSize), weight: parseInt(s.fontWeight, 10)};
    }""", selector)
    if flat is None:
        return None

    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = flat["rgb"]
    lum = 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
    flat["ratio"] = 1.05 / (lum + 0.05)
    return flat


@pytest.mark.parametrize("path,role,selector", CONTRAST_ROLES)
def test_every_text_role_meets_wcag_aa(page, path, role, selector):
    """The archive date was 3.04:1 and the year heading 3.35:1, both under the
    4.5:1 that AA asks of normal text."""
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(400)
    measured = _contrast(page, selector)
    if measured is None:
        pytest.skip("%s is not on %s" % (role, path))

    large = measured["size"] >= 24 or (measured["size"] >= 18.66
                                       and measured["weight"] >= 700)
    needed = 3.0 if large else 4.5
    assert measured["ratio"] >= needed, \
        "%s is %.2f:1 at %.0fpx, needs %.1f:1" % (
            role, measured["ratio"], measured["size"], needed)

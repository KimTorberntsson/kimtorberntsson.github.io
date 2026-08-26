"""Pull quotes.

They used to stack four devices at once: a grey box, a thick grey left rule, a
5em serif quote glyph absolutely positioned over the text, and Georgia italic --
none of which appears anywhere else on the site. Now it is a hairline in the
site's own accent colour and nothing else.
"""

import pytest

QUOTE_POSTS = ["/2019/04/24/astrid.html", "/2015/11/15/radical-face.html"]
ORANGE = "rgb(255, 102, 0)"


@pytest.fixture
def at_width(browser, base_url):
    made = []

    def open_at(path, width=900, height=800):
        context = browser.new_context(viewport={"width": width, "height": height})
        made.append(context)
        page = context.new_page()
        page.goto(base_url + path, wait_until="load")
        page.wait_for_timeout(600)
        return page

    yield open_at
    for context in made:
        context.close()


def style(page):
    return page.evaluate("""() => {
        var q = document.querySelector('blockquote');
        if (!q) return null;
        var s = getComputedStyle(q);
        var before = getComputedStyle(q, ':before');
        var para = q.querySelector('p');
        return {background: s.backgroundColor, borderLeft: s.borderLeftWidth,
                borderColour: s.borderLeftColor, family: s.fontFamily.split(',')[0],
                style: s.fontStyle, glyph: before.content,
                paraPaddingLeft: para ? getComputedStyle(para).paddingLeft : null,
                position: s.position};
    }""")


@pytest.mark.parametrize("path", QUOTE_POSTS)
def test_the_quote_is_a_hairline_in_the_accent_colour(at_width, path):
    s = style(at_width(path))
    assert s, "no blockquote on %s" % path
    assert s["borderColour"] == ORANGE, "the rule is %s" % s["borderColour"]
    assert s["borderLeft"] == "2px", "the rule is %s wide" % s["borderLeft"]


@pytest.mark.parametrize("path", QUOTE_POSTS)
def test_the_box_and_the_glyph_are_gone(at_width, path):
    s = style(at_width(path))
    assert s["background"] in ("rgba(0, 0, 0, 0)", "transparent"), \
        "the quote still has a panel: %s" % s["background"]
    assert s["glyph"] in ("none", "normal", '""'), \
        "the 5em quote glyph is back: %s" % s["glyph"]
    assert s["position"] == "static", \
        "position: relative was only there to hang the glyph off"


@pytest.mark.parametrize("path", QUOTE_POSTS)
def test_it_uses_the_site_typeface(at_width, path):
    s = style(at_width(path))
    assert "Helvetica" in s["family"] or "sans" in s["family"].lower(), \
        "the quote is set in %s" % s["family"]
    assert s["style"] == "italic", "italic is what marks it as a quotation"


@pytest.mark.parametrize("path", QUOTE_POSTS)
def test_the_text_is_not_indented_twice(at_width, path):
    """p carries 5% side padding globally, which would indent inside the rule."""
    s = style(at_width(path))
    assert s["paraPaddingLeft"] == "0px", \
        "paragraphs inside the quote are padded %s" % s["paraPaddingLeft"]


def test_the_citation_reads_as_secondary(at_width):
    page = at_width(QUOTE_POSTS[0])
    cite = page.evaluate("""() => {
        var el = document.querySelector('blockquote small');
        if (!el) return null;
        var s = getComputedStyle(el);
        return {display: s.display, style: s.fontStyle, colour: s.color,
                dash: getComputedStyle(el, ':before').content};
    }""")
    assert cite, "no citation in that quote"
    assert cite["display"] == "block", "the citation should sit on its own line"
    assert cite["style"] == "normal", "the citation should not also be italic"
    assert cite["colour"] != "rgb(51, 51, 51)", "the citation should be quieter"
    assert "\\u2014" in cite["dash"] or "—" in cite["dash"], \
        "the em dash before the citation is missing: %s" % cite["dash"]


@pytest.mark.parametrize("width", [390, 768, 1280])
def test_the_quote_holds_up_at_every_width(at_width, width):
    page = at_width(QUOTE_POSTS[0], width=width)
    box = page.evaluate("""() => {
        var q = document.querySelector('blockquote').getBoundingClientRect();
        var a = document.querySelector('article').getBoundingClientRect();
        return {overflows: q.right > a.right + 1 || q.left < a.left - 1,
                width: q.width};
    }""")
    assert not box["overflows"], "the quote breaks out of the column at %dpx" % width
    assert box["width"] > 100, "the quote collapsed to %.0fpx" % box["width"]

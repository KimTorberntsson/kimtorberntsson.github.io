"""Tap target sizes on a phone.

Lighthouse wants >=48x48; WCAG 2.5.5 asks for 44x44 and 2.5.8 requires 24x24,
exempting text links inline in a sentence.

Every failure had the same cause: the anchors were `display: inline`, so their
box was one line tall (18px) however large the icon inside was. The icon stayed
tappable, being a child, but the anchor's own padding applied to a box that was
not there, and an audit measures the box.
"""

import pytest

LIGHTHOUSE = 48
WCAG_AAA = 44

PAGES = ["/", "/gallery/", "/archive/", "/about/"]

MEASURE = """() => {
    var out = [];
    document.querySelectorAll('a, button').forEach(el => {
        var r = el.getBoundingClientRect();
        if (r.width < 1 || r.height < 1) return;
        var parent = el.parentElement;
        // WCAG 2.5.8 exempts a link sitting inline in a run of text.
        var inSentence = parent.tagName === 'P'
            && parent.textContent.trim().length > el.textContent.trim().length + 8;
        out.push({
            label: (el.getAttribute('aria-label') || el.textContent.trim()
                    || el.getAttribute('href') || '?').slice(0, 30),
            w: Math.round(r.width), h: Math.round(r.height),
            heading: /^H[1-6]$/.test(parent.tagName),
            inSentence: inSentence,
            region: el.closest('nav') ? 'nav'
                  : el.closest('footer') ? 'footer'
                  : el.closest('#blog-nav') ? 'blog-nav'
                  : el.closest('#posts') ? 'archive'
                  : el.closest('.photo-gallery') ? 'gallery' : 'other',
        });
    });
    return out;
}"""


@pytest.fixture
def phone(browser, base_url, playwright):
    context = browser.new_context(**playwright.devices["iPhone 13"])
    page = context.new_page()
    page.base = base_url
    yield page
    context.close()


def targets(page, path):
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(900)
    return page.evaluate(MEASURE)


@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("region", ["nav", "footer", "blog-nav", "archive"])
def test_chrome_targets_meet_the_48px_bar(phone, path, region):
    found = [t for t in targets(phone, path) if t["region"] == region]
    if not found:
        pytest.skip("no %s targets on %s" % (region, path))
    small = [t for t in found
             if min(t["w"], t["h"]) < LIGHTHOUSE]
    assert not small, "under %dpx: %s" % (
        LIGHTHOUSE, [(t["label"], "%dx%d" % (t["w"], t["h"])) for t in small])


@pytest.mark.parametrize("path", PAGES)
def test_nothing_outside_a_sentence_falls_below_44px(phone, path):
    """The looser WCAG 2.5.5 bar, applied to everything that is not prose."""
    small = [t for t in targets(phone, path)
             if not t["inSentence"] and min(t["w"], t["h"]) < WCAG_AAA]
    assert not small, "under %dpx: %s" % (
        WCAG_AAA, [(t["label"], "%dx%d" % (t["w"], t["h"]), t["region"]) for t in small])


@pytest.mark.parametrize("path", PAGES)
def test_the_anchors_wrap_their_icons(phone, path):
    """The root cause: an inline anchor's box ignores a taller child."""
    page = phone
    page.goto(page.base + path, wait_until="load")
    page.wait_for_timeout(600)
    bad = page.evaluate("""() => {
        var out = [];
        document.querySelectorAll('nav a, footer a, #blog-nav a').forEach(a => {
            var icon = a.querySelector('svg');
            if (!icon) return;
            var ar = a.getBoundingClientRect(), ir = icon.getBoundingClientRect();
            if (ir.height > ar.height + 1) {
                out.push({href: a.getAttribute('href'),
                          anchor: Math.round(ar.height), icon: Math.round(ir.height)});
            }
        });
        return out;
    }""")
    assert not bad, "anchors shorter than the icon inside them: %s" % bad


def test_footer_links_are_not_crowded_together(phone):
    """Lighthouse also wants breathing room between neighbouring targets."""
    phone.goto(phone.base + "/about/", wait_until="load")
    phone.wait_for_timeout(600)
    gaps = phone.evaluate("""() => {
        var links = [...document.querySelectorAll('footer a')]
            .map(a => a.getBoundingClientRect())
            .sort((x, y) => x.left - y.left);
        var out = [];
        for (var i = 1; i < links.length; i++) {
            if (Math.abs(links[i].top - links[i - 1].top) < 5) {
                out.push(Math.round(links[i].left - links[i - 1].right));
            }
        }
        return out;
    }""")
    assert gaps, "expected the footer links on one row"
    assert min(gaps) >= 0, "footer targets overlap: %s" % gaps

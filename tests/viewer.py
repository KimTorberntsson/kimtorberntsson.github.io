"""A small driver for the fullscreen photo viewer.

Wraps the fiddly parts: waiting for both fades to settle before asserting or
screenshotting, and synthesising the gestures the viewer listens for. Touch
gestures and trackpad pinches both need raw CDP, because Playwright's own input
API cannot express a multi-event swipe or a ctrl-modified wheel.
"""

PHOTO_READY = """
() => {
    var i = document.querySelector('.lb-image');
    return i && i.style.visibility === 'visible' && i.complete;
}
"""

FADES_DONE = """
() => {
    var o = document.querySelector('.lb-overlay');
    var i = document.querySelector('.lb-image');
    return o && i && getComputedStyle(o).opacity === '1'
        && getComputedStyle(i).opacity === '1';
}
"""

# Slide pitch is measured from the slides themselves rather than assuming the
# CSS gap, so changing the gutter does not silently invalidate these waits.
PITCH = """
    var slides = document.querySelectorAll('.lb-slide');
    var pitch = slides[2].getBoundingClientRect().left
              - slides[1].getBoundingClientRect().left;
"""

TRACK_CENTRED = """
() => {
    var t = document.querySelector('.lb-track');
    var slides = document.querySelectorAll('.lb-slide');
    if (!t || slides.length < 3) return false;
    var pitch = slides[2].getBoundingClientRect().left
              - slides[1].getBoundingClientRect().left;
    var m = new DOMMatrix(getComputedStyle(t).transform);
    return Math.abs(m.e + pitch) < 1.5;
}
"""

CTRL = 2  # CDP modifier bitmask: Alt 1, Ctrl 2, Meta 4, Shift 8


class Viewer:
    def __init__(self, page, cdp, base_url):
        self.page = page
        self.cdp = cdp
        self.base_url = base_url
        self.errors = []
        page.on("pageerror", lambda e: self.errors.append("pageerror: %s" % e))
        page.on(
            "console",
            lambda m: self.errors.append("console.error: %s" % m.text)
            if m.type == "error"
            else None,
        )

    # ------------------------------------------------------------- navigation

    def goto(self, path="/gallery/"):
        self.page.goto(self.base_url + path, wait_until="load")
        return self

    def albums(self):
        """Album names on the current page, in document order."""
        return self.page.evaluate(
            "[...new Set([...document.querySelectorAll('[data-lightbox]')]"
            ".map(a => a.dataset.lightbox))]"
        )

    def thumbs(self, album=None):
        if album is None:
            return self.page.locator("[data-lightbox]")
        # Album names come from post titles, so they contain apostrophes and
        # ampersands. A double quoted attribute selector copes with both.
        escaped = album.replace("\\", "\\\\").replace('"', '\\"')
        return self.page.locator('[data-lightbox="%s"]' % escaped)

    def count(self, album):
        return self.page.evaluate(
            "name => [...document.querySelectorAll('[data-lightbox]')]"
            ".filter(a => a.dataset.lightbox === name).length",
            album,
        )

    def open(self, album=None, nth=0):
        thumb = self.thumbs(album).nth(nth)
        thumb.scroll_into_view_if_needed()
        thumb.click()
        return self.settle()

    def settle(self):
        """Wait for the photo, both fades, and the track to come to rest."""
        self.page.wait_for_function(PHOTO_READY, timeout=20000)
        self.page.wait_for_function(FADES_DONE, timeout=5000)
        self.page.wait_for_function(TRACK_CENTRED, timeout=5000)
        self.page.wait_for_timeout(60)
        return self

    def wait_counter(self, text, timeout=6000):
        """Wait for a move to land. Moves animate, so the counter updates once
        the track has finished travelling, not on the keypress."""
        self.page.wait_for_function(
            "expected => {"
            " var c = document.querySelector('.lb-counter');"
            " return c && c.textContent === expected; }",
            arg=text,
            timeout=timeout,
        )
        return self.settle()

    # ------------------------------------------------------------------ state

    def is_open(self):
        return self.page.evaluate("!!document.querySelector('.lb-overlay.is-open')")

    def counter(self):
        return self.page.eval_on_selector(".lb-counter", "e => e.textContent")

    def caption(self):
        return self.page.eval_on_selector(".lb-caption", "e => e.textContent")

    def scale(self):
        return self.page.eval_on_selector(
            ".lb-image", "e => new DOMMatrix(getComputedStyle(e).transform).a"
        )

    def translation(self):
        return self.page.eval_on_selector(
            ".lb-image",
            "e => { var m = new DOMMatrix(getComputedStyle(e).transform);"
            " return [m.e, m.f]; }",
        )

    def photo_box(self):
        return self.page.eval_on_selector(
            ".lb-image",
            """e => {
                var r = e.getBoundingClientRect();
                return {w: r.width, h: r.height,
                        nw: e.naturalWidth, nh: e.naturalHeight,
                        sw: e.parentElement.clientWidth,
                        sh: e.parentElement.clientHeight};
            }""",
        )

    def locked(self):
        return self.page.evaluate(
            "document.documentElement.classList.contains('lb-lock')"
        )

    def viewport(self):
        return self.page.evaluate("[innerWidth, innerHeight]")

    def backdrop_point(self):
        """A point inside the stage but outside the photo.

        Computed rather than hardcoded: the stage is the full overlay height
        now, so how much bare backdrop is left depends on the photo's aspect
        ratio. Returns None when the photo fills the stage entirely.
        """
        return self.page.evaluate("""() => {
            var stage = document.querySelector('.lb-stage').getBoundingClientRect();
            var img = document.querySelector('.lb-image').getBoundingClientRect();
            // Not the vertical middle: the prev and next buttons live there.
            var clearY = Math.round(stage.top + stage.height * 0.2);
            if (img.left - stage.left > 12) {
                return {x: Math.round(stage.left + (img.left - stage.left) / 2),
                        y: clearY};
            }
            if (stage.bottom - img.bottom > 12) {
                return {x: Math.round(stage.left + stage.width / 2),
                        y: Math.round(img.bottom + (stage.bottom - img.bottom) / 2)};
            }
            return null;
        }""")

    def click_backdrop(self):
        spot = self.backdrop_point()
        assert spot, "the photo fills the stage, there is no backdrop to click"
        self.page.mouse.click(spot["x"], spot["y"])
        self.page.wait_for_timeout(350)
        return self

    def close_with_escape(self):
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(350)
        return self

    # --------------------------------------------------------------- gestures

    def swipe(self, dx, dy, x=None, y=None, steps=12, pause=12):
        w, h = self.viewport()
        x = w / 2 if x is None else x
        y = h / 2 if y is None else y
        self.cdp.send(
            "Input.dispatchTouchEvent",
            {"type": "touchStart", "touchPoints": [{"x": x, "y": y, "id": 1}]},
        )
        for i in range(1, steps + 1):
            self.cdp.send(
                "Input.dispatchTouchEvent",
                {
                    "type": "touchMove",
                    "touchPoints": [
                        {"x": x + dx * i / steps, "y": y + dy * i / steps, "id": 1}
                    ],
                },
            )
            self.page.wait_for_timeout(pause)
        self.cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        return self

    def drag_hold(self, dx, dy, x=None, y=None, steps=10, pause=12):
        """Start a drag and leave the finger down.

        Records the step size so callers can assert against the offset with a
        tolerance of one step: the last move may not have been processed yet.
        """
        w, h = self.viewport()
        x = w / 2 if x is None else x
        y = h / 2 if y is None else y
        self.drag_step = max(abs(dx), abs(dy)) / steps
        self.cdp.send(
            "Input.dispatchTouchEvent",
            {"type": "touchStart", "touchPoints": [{"x": x, "y": y, "id": 1}]},
        )
        for i in range(1, steps + 1):
            self.cdp.send(
                "Input.dispatchTouchEvent",
                {
                    "type": "touchMove",
                    "touchPoints": [
                        {"x": x + dx * i / steps, "y": y + dy * i / steps, "id": 1}
                    ],
                },
            )
            self.page.wait_for_timeout(pause)
        # Let the last move be handled before anything measures the track.
        self.page.wait_for_timeout(60)
        return self

    def release(self):
        self.cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        return self

    def slide_boxes(self):
        """Viewport rects of the three slides, left to right."""
        return self.page.evaluate(
            """() => [...document.querySelectorAll('.lb-slide')].map(s => {
                var r = s.getBoundingClientRect();
                return {left: Math.round(r.left), right: Math.round(r.right),
                        width: Math.round(r.width)};
            })"""
        )

    def track_offset(self):
        """How far the track has been dragged from centre, in px."""
        return self.page.evaluate(
            """() => {
                var t = document.querySelector('.lb-track');"""
            + PITCH
            + """
                var m = new DOMMatrix(getComputedStyle(t).transform);
                return m.e + pitch;
            }"""
        )

    def tap(self, x=None, y=None):
        w, h = self.viewport()
        x = w / 2 if x is None else x
        y = h / 2 if y is None else y
        self.cdp.send(
            "Input.dispatchTouchEvent",
            {"type": "touchStart", "touchPoints": [{"x": x, "y": y, "id": 1}]},
        )
        self.cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        return self

    def double_tap(self, x=None, y=None):
        self.tap(x, y)
        self.page.wait_for_timeout(80)
        self.tap(x, y)
        self.page.wait_for_timeout(400)
        return self

    def pinch(self, delta_y, x=None, y=None, times=1):
        """A macOS trackpad pinch: a wheel event with ctrl held."""
        w, h = self.viewport()
        x = w / 2 if x is None else x
        y = h / 2 if y is None else y
        for _ in range(times):
            self.cdp.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseWheel",
                    "x": x,
                    "y": y,
                    "deltaX": 0,
                    "deltaY": delta_y,
                    "modifiers": CTRL,
                },
            )
            self.page.wait_for_timeout(40)
        return self

    def wheel(self, delta_y, x=None, y=None):
        """An ordinary scroll, with no modifier. Must not be read as a pinch."""
        w, h = self.viewport()
        x = w / 2 if x is None else x
        y = h / 2 if y is None else y
        self.cdp.send(
            "Input.dispatchMouseEvent",
            {
                "type": "mouseWheel",
                "x": x,
                "y": y,
                "deltaX": 0,
                "deltaY": delta_y,
                "modifiers": 0,
            },
        )
        self.page.wait_for_timeout(120)
        return self

    def page_zoom(self):
        return self.page.evaluate("(window.visualViewport ? visualViewport.scale : 1)")

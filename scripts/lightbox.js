/*
 * Fullscreen photo viewer.
 *
 * Progressive replacement for lightbox2: no dependencies, fills the viewport,
 * drag to bring the next photo in, swipe down to dismiss, pinch and double tap
 * to zoom, arrow keys and escape on the desktop.
 *
 * The photos live on a three slide track -- previous, current, next -- which is
 * translated as a whole. Dragging moves the track, so the neighbouring photo is
 * genuinely on screen and follows the finger rather than appearing once the
 * gesture is over. The middle slide is always the current photo: committing a
 * move animates the track by one slide, then silently reassigns the three
 * sources and snaps the track back to centre.
 *
 * Markup contract is unchanged, so the Jekyll templates keep working:
 *   <a href="full.jpg" data-lightbox="group" data-title="caption">
 */

(function () {
	'use strict';

	var FADE = 160; // overlay fade, ms
	var SLIDE = 220; // track settle after a commit or a spring back, ms
	var SLIDE_KEY = 160; // arrow keys and the nav buttons, ms
	var SPINNER_DELAY = 150; // don't flash a spinner for cached photos
	var SWIPE_FRACTION = 0.22; // of the viewport before a drag commits
	var SWIPE_VELOCITY = 0.45; // px/ms, a flick counts even if it is short
	var FLICK_DISTANCE = 24; // px a flick must travel before it counts
	var DISMISS_DISTANCE = 110; // px of downward drag before closing
	var AXIS_LOCK = 10; // px before we decide the drag direction
	var TAP_SLOP = 10; // px of movement still counting as a tap
	var TAP_TIME = 300; // ms, both for taps and for double taps
	var MAX_SCALE = 4;
	var TAP_ZOOM = 2.5;
	var WHEEL_CLAMP = 50; // biggest wheel delta honoured in one event
	var WHEEL_DAMPING = 200; // bigger is a slower pinch

	var album = [];
	var index = 0;
	var loadToken = 0;
	var spinnerTimer = null;
	var settleTimer = null;
	var pending = null; // photo a move in flight is heading for
	var trigger = null;
	var pushedState = false;
	var opened = false;
	var els = null;

	var view = { scale: 1, x: 0, y: 0 };
	var pointers = {};
	var pointerCount = 0;
	var drag = null;
	var pinch = null;
	var gesture = null;
	var lastTap = 0;

	/* ---------------------------------------------------------------- setup */

	function svg(path) {
		return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + path + '"/></svg>';
	}

	function build() {
		var overlay = document.createElement('div');
		overlay.className = 'lb-overlay';
		overlay.setAttribute('role', 'dialog');
		overlay.setAttribute('aria-modal', 'true');
		overlay.setAttribute('aria-label', 'Photo viewer');
		overlay.innerHTML =
			'<div class="lb-stage">' +
			'<div class="lb-track">' +
			'<div class="lb-slide"><img alt="" decoding="async"></div>' +
			'<div class="lb-slide"><img class="lb-image" alt="" decoding="async"></div>' +
			'<div class="lb-slide"><img alt="" decoding="async"></div>' +
			'</div>' +
			'<div class="lb-spinner"></div>' +
			'</div>' +
			'<div class="lb-bar" aria-live="polite"><div class="lb-counter"></div><div class="lb-caption"></div></div>' +
			'<button type="button" class="lb-btn lb-close" aria-label="Close">' + svg('M5 5 L19 19 M19 5 L5 19') + '</button>' +
			'<button type="button" class="lb-btn lb-prev" aria-label="Previous photo">' + svg('M15 4 L7 12 L15 20') + '</button>' +
			'<button type="button" class="lb-btn lb-next" aria-label="Next photo">' + svg('M9 4 L17 12 L9 20') + '</button>';

		document.body.appendChild(overlay);

		var slides = overlay.querySelectorAll('.lb-slide img');
		els = {
			overlay: overlay,
			stage: overlay.querySelector('.lb-stage'),
			track: overlay.querySelector('.lb-track'),
			before: slides[0],
			img: slides[1],
			after: slides[2],
			spinner: overlay.querySelector('.lb-spinner'),
			caption: overlay.querySelector('.lb-caption'),
			counter: overlay.querySelector('.lb-counter'),
			close: overlay.querySelector('.lb-close'),
			prev: overlay.querySelector('.lb-prev'),
			next: overlay.querySelector('.lb-next')
		};

		els.close.addEventListener('click', function () { close(); });
		els.prev.addEventListener('click', function () { step(-1); });
		els.next.addEventListener('click', function () { step(1); });

		els.stage.addEventListener('pointerdown', onPointerDown);
		els.stage.addEventListener('pointermove', onPointerMove);
		els.stage.addEventListener('pointerup', onPointerUp);
		els.stage.addEventListener('pointercancel', onPointerUp);
		els.stage.addEventListener('dragstart', function (e) { e.preventDefault(); });

		// A trackpad pinch is not a touch gesture. Chrome reports it as a wheel
		// event with ctrlKey set, Safari as its own gesture events. Both are
		// bound on the overlay rather than the stage so that a pinch anywhere,
		// caption bar included, zooms the photo instead of the whole page.
		overlay.addEventListener('wheel', onWheel, { passive: false });
		overlay.addEventListener('gesturestart', onGestureStart);
		overlay.addEventListener('gesturechange', onGestureChange);
		overlay.addEventListener('gestureend', onGestureEnd);
	}

	function isOpen() {
		return opened;
	}

	/* ------------------------------------------------------- opening/closing */

	function open(list, start, from) {
		if (els === null) {
			build();
		}

		album = list;
		trigger = from || null;
		opened = true;

		document.documentElement.classList.add('lb-lock');
		document.body.classList.add('lb-lock');
		els.overlay.classList.add('is-visible');
		// One frame with display set but opacity still 0, so the fade runs.
		requestAnimationFrame(function () {
			els.overlay.classList.add('is-open');
		});

		document.addEventListener('keydown', onKeyDown);

		if (window.history && window.history.pushState) {
			window.history.pushState({ lightbox: true }, '');
			pushedState = true;
		}

		render(start);
		els.close.focus();
	}

	function close(fromHistory) {
		if (!isOpen()) {
			return;
		}

		opened = false;
		loadToken++;
		pending = null;
		stopSpinner();
		clearSettle();
		els.overlay.classList.remove('is-open');
		document.removeEventListener('keydown', onKeyDown);
		resetGestures();

		window.setTimeout(function () {
			// A new photo may have been opened during the fade.
			if (opened) {
				return;
			}
			els.overlay.classList.remove('is-visible');
			els.before.removeAttribute('src');
			els.img.removeAttribute('src');
			els.after.removeAttribute('src');
			document.documentElement.classList.remove('lb-lock');
			document.body.classList.remove('lb-lock');
		}, FADE);

		els.overlay.style.opacity = '';

		if (trigger) {
			trigger.focus();
			trigger = null;
		}

		if (!fromHistory && pushedState) {
			pushedState = false;
			window.history.back();
		} else {
			pushedState = false;
		}
	}

	/* ------------------------------------------------------------- the track */

	/* Distance from one slide to the next, measured rather than assumed: the
	   gutter is a CSS gap, and duplicating it here would let the two drift. Both
	   rects carry the track's transform, so the difference is unaffected by it. */
	function pitch() {
		var current = els.img.parentNode.getBoundingClientRect();
		var following = els.after.parentNode.getBoundingClientRect();
		return (following.left - current.left) || els.stage.clientWidth;
	}

	/* Offsets are relative to the centred position, so 0 means "current photo
	   centred" and a negative dx drags towards the next photo. */
	function setTrack(dx, dy, animate, duration) {
		els.track.style.transition = animate
			? 'transform ' + (duration || SLIDE) + 'ms cubic-bezier(0.22, 0.61, 0.36, 1)'
			: 'none';
		els.track.style.transform =
			'translate3d(' + (-pitch() + (dx || 0)) + 'px, ' + (dy || 0) + 'px, 0)';
	}

	function clearSettle() {
		if (settleTimer !== null) {
			window.clearTimeout(settleTimer);
			settleTimer = null;
		}
	}

	/* Finish a move that is still animating, right now. Called both by its own
	   timer and by anything that interrupts it, so a held arrow key or a hand
	   grabbing the track never loses a step. */
	function land() {
		if (pending === null) {
			return;
		}
		var target = pending;
		pending = null;
		clearSettle();
		render(target);
	}

	function at(i) {
		return album[(i % album.length + album.length) % album.length];
	}

	/* Load the three slides around `i` and centre the track on the middle one.
	   Called once a move has finished animating, so the swap is invisible. */
	function render(i) {
		index = (i % album.length + album.length) % album.length;

		var photo = at(index);
		var token = ++loadToken;

		pending = null;
		clearSettle();
		resetView(false);
		setTrack(0, 0, false);

		els.caption.textContent = photo.title;
		els.counter.textContent = album.length > 1
			? index + 1 + ' / ' + album.length
			: '';
		els.prev.hidden = els.next.hidden = album.length < 2;

		els.before.src = at(index - 1).href;
		els.after.src = at(index + 1).href;
		els.before.alt = els.after.alt = '';

		// Probing the cache first stops navigation from blinking: the photo has
		// usually just been on screen in a neighbouring slide.
		var probe = new Image();
		probe.src = photo.href;

		if (probe.complete && probe.naturalWidth > 0) {
			stopSpinner();
			els.img.src = photo.href;
			els.img.alt = photo.title;
			els.img.style.visibility = 'visible';
			return;
		}

		els.img.style.visibility = 'hidden';
		startSpinner();
		probe.onload = function () {
			if (token !== loadToken) {
				return;
			}
			stopSpinner();
			els.img.src = photo.href;
			els.img.alt = photo.title;
			els.img.style.visibility = 'visible';
		};
		probe.onerror = function () {
			if (token !== loadToken) {
				return;
			}
			stopSpinner();
			els.caption.textContent = 'Could not load this photo.';
		};
	}

	/* Animate one slide along, then re-centre on the new photo. A press arriving
	   mid-animation lands the previous move first rather than being dropped, so
	   holding an arrow key steps steadily instead of stalling. */
	function step(direction) {
		if (album.length < 2) {
			return;
		}
		land();
		pending = index + direction;
		setTrack(-direction * pitch(), 0, true, SLIDE_KEY);
		settleTimer = window.setTimeout(function () {
			settleTimer = null;
			land();
		}, SLIDE_KEY);
	}

	function springBack() {
		els.overlay.style.opacity = '';
		setTrack(0, 0, true);
	}

	function startSpinner() {
		stopSpinner();
		spinnerTimer = window.setTimeout(function () {
			els.spinner.classList.add('is-visible');
		}, SPINNER_DELAY);
	}

	function stopSpinner() {
		if (spinnerTimer !== null) {
			window.clearTimeout(spinnerTimer);
			spinnerTimer = null;
		}
		if (els !== null) {
			els.spinner.classList.remove('is-visible');
		}
	}

	/* -------------------------------------------------------------- zoom/pan */

	function setTransform(animate) {
		els.img.style.transition = animate ? 'transform ' + SLIDE + 'ms ease-out' : 'none';
		els.img.style.transform =
			'translate(' + view.x + 'px, ' + view.y + 'px) scale(' + view.scale + ')';
	}

	function resetView(animate) {
		view.scale = 1;
		view.x = 0;
		view.y = 0;
		els.img.style.cursor = '';
		setTransform(animate);
	}

	function clampPan() {
		var overflowX = Math.max(0, (els.img.offsetWidth * view.scale - els.stage.clientWidth) / 2);
		var overflowY = Math.max(0, (els.img.offsetHeight * view.scale - els.stage.clientHeight) / 2);
		view.x = Math.max(-overflowX, Math.min(overflowX, view.x));
		view.y = Math.max(-overflowY, Math.min(overflowY, view.y));
	}

	/* The photo is transformed as translate() scale(), so a point p in the
	   untransformed image maps to screen position O + t + s * p, where O is the
	   centre of the untransformed image. Inverting that keeps whatever is under
	   the fingers under the fingers while zooming. */

	function untransformedCentre() {
		var box = els.img.getBoundingClientRect();
		return {
			x: box.left + box.width / 2 - view.x,
			y: box.top + box.height / 2 - view.y
		};
	}

	function imagePointAt(centre, clientX, clientY) {
		return {
			x: (clientX - centre.x - view.x) / view.scale,
			y: (clientY - centre.y - view.y) / view.scale
		};
	}

	function zoomTo(scale, clientX, clientY, animate) {
		var centre = untransformedCentre();
		var point = imagePointAt(centre, clientX, clientY);

		view.scale = Math.max(1, Math.min(MAX_SCALE, scale));
		view.x = clientX - centre.x - view.scale * point.x;
		view.y = clientY - centre.y - view.scale * point.y;

		if (view.scale === 1) {
			view.x = 0;
			view.y = 0;
		}
		clampPan();
		setTransform(animate);
		els.img.style.cursor = view.scale > 1 ? 'grab' : '';
	}

	/* -------------------------------------------------------------- gestures */

	function resetGestures() {
		pointers = {};
		pointerCount = 0;
		drag = null;
		pinch = null;
		gesture = null;
	}

	/* Trackpad pinch. Zoom multiplicatively so a notch feels the same at every
	   scale, and always about the cursor. */

	function onWheel(e) {
		if (gesture !== null) {
			return; // Safari is already driving this through gesture events
		}
		if (!e.ctrlKey) {
			return; // an ordinary two finger scroll, not a pinch
		}
		// Without this the browser zooms the entire page.
		e.preventDefault();
		// A trackpad sends many small deltas, a mouse wheel one big notch per
		// click. Clamping keeps a notch from jumping most of the zoom range.
		var delta = Math.max(-WHEEL_CLAMP, Math.min(WHEEL_CLAMP, e.deltaY));
		zoomTo(view.scale * Math.exp(-delta / WHEEL_DAMPING), e.clientX, e.clientY, false);
	}

	function onGestureStart(e) {
		e.preventDefault();
		gesture = { scale: view.scale, x: e.clientX, y: e.clientY };
	}

	function onGestureChange(e) {
		e.preventDefault();
		if (gesture !== null) {
			zoomTo(gesture.scale * e.scale, gesture.x, gesture.y, false);
		}
	}

	function onGestureEnd(e) {
		e.preventDefault();
		gesture = null;
		if (view.scale <= 1.02) {
			resetView(true);
		}
	}

	function pointerList() {
		return Object.keys(pointers).map(function (id) { return pointers[id]; });
	}

	function onPointerDown(e) {
		if (e.pointerType === 'mouse' && e.button !== 0) {
			return;
		}
		e.preventDefault();

		if (!(e.pointerId in pointers)) {
			pointerCount++;
		}
		pointers[e.pointerId] = { x: e.clientX, y: e.clientY };

		if (els.stage.setPointerCapture) {
			els.stage.setPointerCapture(e.pointerId);
		}

		if (pointerCount === 1) {
			// Grabbing the track mid-animation takes over from a settled state.
			land();
			drag = {
				startX: e.clientX,
				startY: e.clientY,
				x: 0,
				y: 0,
				axis: null,
				onImage: e.target === els.img,
				time: Date.now(),
				fromX: view.x,
				fromY: view.y
			};
			pinch = null;
		} else if (pointerCount === 2) {
			beginPinch();
		}
	}

	function beginPinch() {
		var list = pointerList();
		var centre = untransformedCentre();
		var midX = (list[0].x + list[1].x) / 2;
		var midY = (list[0].y + list[1].y) / 2;

		pinch = {
			distance: Math.hypot(list[0].x - list[1].x, list[0].y - list[1].y) || 1,
			scale: view.scale,
			centre: centre,
			point: imagePointAt(centre, midX, midY)
		};
		drag = null;
		els.overlay.style.opacity = '';
		setTrack(0, 0, false);
	}

	function onPointerMove(e) {
		if (!(e.pointerId in pointers)) {
			return;
		}
		pointers[e.pointerId] = { x: e.clientX, y: e.clientY };

		if (pinch !== null && pointerCount >= 2) {
			var list = pointerList();
			var distance = Math.hypot(list[0].x - list[1].x, list[0].y - list[1].y);
			var midX = (list[0].x + list[1].x) / 2;
			var midY = (list[0].y + list[1].y) / 2;

			view.scale = Math.max(1, Math.min(MAX_SCALE, pinch.scale * (distance / pinch.distance)));
			view.x = midX - pinch.centre.x - view.scale * pinch.point.x;
			view.y = midY - pinch.centre.y - view.scale * pinch.point.y;
			clampPan();
			setTransform();
			return;
		}

		if (drag === null) {
			return;
		}

		drag.x = e.clientX - drag.startX;
		drag.y = e.clientY - drag.startY;

		if (view.scale > 1) {
			view.x = drag.fromX + drag.x;
			view.y = drag.fromY + drag.y;
			clampPan();
			setTransform();
			return;
		}

		if (drag.axis === null && Math.hypot(drag.x, drag.y) > AXIS_LOCK) {
			drag.axis = Math.abs(drag.x) > Math.abs(drag.y) ? 'x' : 'y';
		}

		if (drag.axis === 'x') {
			// A single photo album has nowhere to go, so resist the drag.
			setTrack(album.length > 1 ? drag.x : drag.x / 4, 0, false);
		} else if (drag.axis === 'y') {
			setTrack(0, drag.y, false);
			els.overlay.style.opacity = String(Math.max(0.25, 1 - Math.abs(drag.y) / 520));
		}
	}

	function onPointerUp(e) {
		if (!(e.pointerId in pointers)) {
			return;
		}
		delete pointers[e.pointerId];
		pointerCount = Math.max(0, pointerCount - 1);

		if (pinch !== null) {
			pinch = null;
			if (view.scale <= 1.02) {
				resetView(true);
			}
			if (pointerCount === 1) {
				// Carry on with a one finger pan from where the pinch left off.
				var remaining = pointerList()[0];
				drag = {
					startX: remaining.x,
					startY: remaining.y,
					x: 0,
					y: 0,
					axis: view.scale > 1 ? null : 'x',
					onImage: true,
					time: Date.now(),
					fromX: view.x,
					fromY: view.y
				};
			}
			return;
		}

		if (drag === null || pointerCount > 0) {
			return;
		}

		var moved = drag;
		var elapsed = Date.now() - moved.time;
		drag = null;

		if (moved.axis === null
			&& Math.hypot(moved.x, moved.y) <= TAP_SLOP
			&& elapsed < TAP_TIME) {
			onTap(moved, e);
			return;
		}

		if (view.scale > 1) {
			return; // panning while zoomed in, nothing to settle
		}

		if (moved.axis === 'x') {
			var threshold = els.stage.clientWidth * SWIPE_FRACTION;
			var flick = Math.abs(moved.x) > FLICK_DISTANCE
				&& Math.abs(moved.x) / Math.max(1, elapsed) > SWIPE_VELOCITY;
			if (album.length > 1 && (Math.abs(moved.x) > threshold || flick)) {
				commit(moved.x < 0 ? 1 : -1, moved.x);
			} else {
				springBack();
			}
		} else if (moved.axis === 'y') {
			var flung = moved.y > FLICK_DISTANCE
				&& moved.y / Math.max(1, elapsed) > SWIPE_VELOCITY;
			if (moved.y > DISMISS_DISTANCE || flung) {
				close();
			} else {
				springBack();
			}
		}
	}

	/* Finish a drag that has already carried the track part of the way, so the
	   photo continues from under the finger instead of restarting. */
	function commit(direction, from) {
		var target = index + direction;
		var remaining = Math.max(0, pitch() - Math.abs(from));
		var duration = Math.max(90, Math.round(SLIDE * remaining / pitch()));

		els.track.style.transition =
			'transform ' + duration + 'ms cubic-bezier(0.22, 0.61, 0.36, 1)';
		els.track.style.transform =
			'translate3d(' + (-pitch() - direction * pitch()) + 'px, 0px, 0)';

		clearSettle();
		pending = target;
		settleTimer = window.setTimeout(function () {
			settleTimer = null;
			land();
		}, duration);
	}

	function onTap(moved, e) {
		var now = Date.now();

		if (moved.onImage && now - lastTap < TAP_TIME) {
			lastTap = 0;
			zoomTo(view.scale > 1 ? 1 : TAP_ZOOM, e.clientX, e.clientY, true);
			return;
		}
		lastTap = now;

		// Tapping the backdrop closes; tapping the photo itself does not, so a
		// misplaced thumb does not throw you out of the album.
		if (!moved.onImage && view.scale === 1) {
			close();
		}
	}

	/* ------------------------------------------------------- document wiring */

	/* aria-modal says focus is confined to the dialog, so Tab has to cycle the
	   viewer's own controls rather than wander into the page behind it. */
	function trapTab(e) {
		var stops = [els.close, els.prev, els.next].filter(function (button) {
			return !button.hidden && button.offsetParent !== null;
		});
		e.preventDefault();
		if (stops.length === 0) {
			return;
		}
		var at = stops.indexOf(document.activeElement);
		var next = (at + (e.shiftKey ? -1 : 1) + stops.length + 1) % stops.length;
		stops[next].focus();
	}

	function onKeyDown(e) {
		if (e.key === 'Tab') {
			trapTab(e);
			return;
		}
		if (e.key === 'Escape') {
			close();
		} else if (e.key === 'ArrowRight') {
			step(1);
		} else if (e.key === 'ArrowLeft') {
			step(-1);
		} else if (e.key === 'Home') {
			pending = null;
			render(0);
		} else if (e.key === 'End') {
			pending = null;
			render(album.length - 1);
		} else {
			return;
		}
		e.preventDefault();
	}

	function linkFor(node) {
		while (node && node !== document) {
			if (node.nodeType === 1 && node.hasAttribute('data-lightbox')) {
				return node;
			}
			node = node.parentNode;
		}
		return null;
	}

	document.addEventListener('click', function (e) {
		if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) {
			return; // let the browser open the photo in a new tab
		}

		var link = linkFor(e.target);
		if (link === null) {
			return;
		}
		e.preventDefault();

		// Group by the data-lightbox value rather than by selector, since the
		// post titles used as group names contain quotes and ampersands.
		var group = link.getAttribute('data-lightbox');
		var links = [].filter.call(document.querySelectorAll('[data-lightbox]'), function (a) {
			return a.getAttribute('data-lightbox') === group;
		});

		open(links.map(function (a) {
			return { href: a.getAttribute('href'), title: a.getAttribute('data-title') || '' };
		}), links.indexOf(link), link);
	});

	window.addEventListener('popstate', function () {
		if (isOpen()) {
			close(true);
		}
	});

	window.addEventListener('resize', function () {
		if (!isOpen()) {
			return;
		}
		// A move in flight has to be finished, not abandoned: dropping only its
		// timer would leave `pending` set and jump on the next keypress.
		land();
		setTrack(0, 0, false);
		if (view.scale > 1) {
			clampPan();
			setTransform();
		}
	});
}());

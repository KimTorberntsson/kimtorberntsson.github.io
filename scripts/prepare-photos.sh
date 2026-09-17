#!/bin/bash
# Prepare the photos for a post: a full-size copy capped at 1920px on the long
# edge, and a square 200px thumbnail, both at quality 80 like the rest of the
# library. Pass the post title and the source images, newest ordering first --
# they become img1, img2 and so on.
#
#   scripts/prepare-photos.sh "Tage" ~/Pictures/tage/*.jpg
#
# The background photo is separate. It is cropped to 1920x1280, and the hero
# band then shows the middle of that, so a subject high in the frame loses the
# top of its head. --offset moves the crop down from the top edge of the
# resized photo; leave it out for the middle.
#
#   scripts/prepare-photos.sh --background "Tage" hero.jpg
#   scripts/prepare-photos.sh --background --offset 1 "Tage" hero.jpg

set -euo pipefail

background=false
offset=""
while true; do
	case "${1:-}" in
		--background) background=true; shift ;;
		# sips reads 0 as "unset" and centres the crop anyway, so the top of the
		# photo is --offset 1.
		--offset) offset=$2; shift 2 ;;
		*) break ;;
	esac
done

title=${1:?usage: prepare-photos.sh [--background [--offset N]] "Post Title" image...}
shift

root=$(cd "$(dirname "$0")/.." && pwd)

quality () { sips -s format jpeg -s formatOptions 80 "$@" >/dev/null; }

if $background; then
	# The hero is a 3:2 band, 1920 wide.
	out="$root/assets/backgrounds/$title.jpg"
	cp "$1" "$out"
	sips --resampleWidth 1920 "$out" >/dev/null
	if [ -n "$offset" ]; then
		sips -c 1280 1920 --cropOffset "$offset" 0 "$out" >/dev/null
	else
		sips -c 1280 1920 "$out" >/dev/null
	fi
	quality "$out"
	echo "backgrounds/$title.jpg  $(sips -g pixelWidth -g pixelHeight "$out" | tail -2 | tr -d ' \n')"
	exit 0
fi

full="$root/assets/photos/$title/full-size"
thumbs="$root/assets/photos/$title/thumbs"
mkdir -p "$full" "$thumbs"

n=0
for src in "$@"; do
	n=$((n + 1))
	cp "$src" "$full/img$n.jpg"
	sips --resampleHeightWidthMax 1920 "$full/img$n.jpg" >/dev/null
	quality "$full/img$n.jpg"

	# Fit the short edge to 200 and take the middle square.
	cp "$src" "$thumbs/img$n.jpg"
	read -r w h < <(sips -g pixelWidth -g pixelHeight "$src" | awk '/pixel/ {printf "%s ", $2} END {print ""}')
	if [ "$w" -lt "$h" ]; then
		sips --resampleWidth 200 "$thumbs/img$n.jpg" >/dev/null
	else
		sips --resampleHeight 200 "$thumbs/img$n.jpg" >/dev/null
	fi
	sips -c 200 200 "$thumbs/img$n.jpg" >/dev/null
	quality "$thumbs/img$n.jpg"

	echo "img$n.jpg  $(du -h "$full/img$n.jpg" | cut -f1)"
done

echo
echo "$n photos. Front matter:"
for i in $(seq 1 $n); do printf -- '- nr: %s\n  title: ""\n' "$i"; done

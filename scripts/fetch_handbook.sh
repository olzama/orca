#!/bin/bash
# Fetch the chapters of the HPSG Handbook (Mueller, Abeille, Borsley & Koenig 2021,
# Language Science Press, CC-BY 4.0) from Zenodo and convert them to text.
# Usage: scripts/fetch_handbook.sh <catalog-page.html> <output-dir>
set -u
page="$1"; out="$2"
grep -oE 'https://zenodo.org/record/[0-9]+/files/259-[^"]*-2021-[0-9]+\.pdf\?download=1' "$page" | sort -u |
while read -r url; do
  n=$(echo "$url" | sed -E 's/.*-([0-9]+)\.pdf.*/\1/')
  f=$(printf '%s/pdf/ch%02d.pdf' "$out" "$n")
  [ -s "$f" ] || curl -sL -m 300 -A "Mozilla/5.0 (research-client)" "$url" -o "$f"
  pdftotext -layout "$f" "$(printf '%s/txt/ch%02d.txt' "$out" "$n")"
  sleep 1
done

#!/usr/bin/env bash
# Rebuild the self-hosted basemap in static/basemap/ from Natural Earth (public domain).
# Needs: curl, and mapshaper (npm i -g mapshaper). Run from the repo root.
set -euo pipefail
NE=https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson
TMP=$(mktemp -d)
for f in ne_50m_land ne_50m_lakes ne_50m_rivers_lake_centerlines ne_110m_land; do
  curl -sSL -o "$TMP/$f.geojson" "$NE/$f.geojson"
done
mapshaper "$TMP/ne_50m_land.geojson" -simplify 25% keep-shapes -filter-fields -o static/basemap/land.json precision=0.01 format=geojson
mapshaper "$TMP/ne_50m_lakes.geojson" -filter 'scalerank <= 4' -simplify 30% keep-shapes -filter-fields name -o static/basemap/lakes.json precision=0.01 format=geojson
mapshaper "$TMP/ne_50m_rivers_lake_centerlines.geojson" -filter 'scalerank <= 5' -simplify 30% -filter-fields name -o static/basemap/rivers.json precision=0.01 format=geojson
cp "$TMP/ne_110m_land.geojson" generator/ne_110m_land.geojson   # outline for the small record-page maps
rm -rf "$TMP"
echo "basemap rebuilt"

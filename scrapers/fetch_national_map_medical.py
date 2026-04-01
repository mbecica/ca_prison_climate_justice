"""
Download Medical & Emergency Response facilities from the USGS National Map
Structures layer for California.

Queries three sublayers of:
  https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer

  Layer 14 — Hospitals / Medical Centers  (FCODE 80012)
  Layer 15 — Ambulance Services
  Layer 16 — Fire Stations / EMS Stations (FCODE 74026)

Paginates in chunks of 1000 until all features are retrieved.

Output: data_sources/national_map_medical_emergency.csv
Columns: layer, name, fcode, address, city, state, longitude, latitude
"""

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = 'https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer'
LAYERS = {
    14: 'Hospitals/Medical Centers',
    15: 'Ambulance Services',
    16: 'Fire Stations/EMS Stations',
}
OUT_FIELDS = 'NAME,FCODE,ADDRESS,CITY,STATE'
PAGE_SIZE = 1000


def fetch_page(layer_id: int, offset: int) -> dict:
    params = urllib.parse.urlencode({
        'where': "STATE='CA'",
        'outFields': OUT_FIELDS,
        'returnGeometry': 'true',
        'outSR': '4326',
        'resultOffset': offset,
        'resultRecordCount': PAGE_SIZE,
        'f': 'json',
    })
    url = f'{BASE_URL}/{layer_id}/query?{params}'
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def fetch_layer(layer_id: int, label: str) -> list[dict]:
    rows = []
    offset = 0
    while True:
        data = fetch_page(layer_id, offset)
        features = data.get('features', [])
        for feat in features:
            attrs = feat.get('attributes', {})
            geom = feat.get('geometry', {})
            rows.append({
                'layer':     label,
                'name':      (attrs.get('NAME') or '').strip(),
                'fcode':     attrs.get('FCODE', ''),
                'address':   (attrs.get('ADDRESS') or '').strip(),
                'city':      (attrs.get('CITY') or '').strip(),
                'state':     (attrs.get('STATE') or '').strip(),
                'longitude': geom.get('x', ''),
                'latitude':  geom.get('y', ''),
            })
        print(f'  Layer {layer_id} ({label}): offset {offset}, got {len(features)} features')
        if len(features) < PAGE_SIZE or not data.get('exceededTransferLimit', False):
            break
        offset += PAGE_SIZE
        time.sleep(0.25)
    return rows


def main():
    out = Path(__file__).parent.parent / 'data_sources' / 'national_map_medical_emergency.csv'
    all_rows = []

    for layer_id, label in LAYERS.items():
        print(f'Fetching layer {layer_id}: {label}')
        rows = fetch_layer(layer_id, label)
        all_rows.extend(rows)
        print(f'  → {len(rows)} total features')

    fieldnames = ['layer', 'name', 'fcode', 'address', 'city', 'state', 'longitude', 'latitude']
    with open(out, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f'\nWrote {len(all_rows)} rows → {out.relative_to(out.parent.parent)}')


if __name__ == '__main__':
    main()

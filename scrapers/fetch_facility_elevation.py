"""
Look up ground elevation at each facility's centroid from the USGS Elevation
Point Query Service (EPQS, 3DEP 1/3 arc-second).

  https://epqs.nationalmap.gov/v1/json

Input:  data_sources/facilities/ca_facilities.csv (facilityid, latitude, longitude)
Output: data_sources/facilities/facility_elevation.csv
Columns: facilityid, latitude, longitude, elevation_m
"""

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FACILITIES = REPO / 'data_sources' / 'facilities' / 'ca_facilities.csv'
OUT = REPO / 'data_sources' / 'facilities' / 'facility_elevation.csv'
URL = 'https://epqs.nationalmap.gov/v1/json'

csv.field_size_limit(sys.maxsize)  # ca_facilities.csv carries WKT geometry


def query(lon, lat, retries=4):
    params = urllib.parse.urlencode({
        'x': lon, 'y': lat, 'wkid': 4326, 'units': 'Meters', 'includeDate': 'false',
    })
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(f'{URL}?{params}', timeout=30) as r:
                return float(json.load(r)['value'])
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def main():
    with open(FACILITIES, newline='') as f:
        rows = list(csv.DictReader(f))

    out = []
    for i, r in enumerate(rows, 1):
        elev = query(r['longitude'], r['latitude'])
        out.append({
            'facilityid': r['facilityid'],
            'latitude': r['latitude'],
            'longitude': r['longitude'],
            'elevation_m': round(elev, 1),
        })
        if i % 50 == 0:
            print(f'  {i}/{len(rows)}')

    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['facilityid', 'latitude', 'longitude', 'elevation_m'])
        w.writeheader()
        w.writerows(out)
    print(f'Wrote {len(out)} facilities to {OUT.relative_to(REPO)}')


if __name__ == '__main__':
    main()

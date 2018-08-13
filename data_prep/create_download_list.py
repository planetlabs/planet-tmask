#
# Copyright 2018, Planet Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json
import os
import requests
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse

from data_prep.activate import check_response


class CreateDownloadList(object):
    def __init__(self, location):
        self.location = location
        self.ps_list_path = os.path.join(self.location, 'ps-list.txt')
        self.re_list_path = os.path.join(self.location, 're-list.txt')
        self.aoi_geojson_path = os.path.join(self.location, 'aoi.geojson')

    def get_search_endpoint_request(self, lat, lon, bufferval, cc):

        miny = lat - bufferval
        maxy = lat + bufferval
        minx = lon - bufferval
        maxx = lon + bufferval

        geo_json_geometry = {
            "type": "Polygon",
            "coordinates": [
                [
                    [
                        minx,
                        miny
                    ],
                    [
                        minx,
                        maxy
                    ],
                    [
                        maxx,
                        maxy
                    ],
                    [
                        maxx,
                        miny
                    ],
                    [
                        minx,
                        miny
                    ]
                ]
            ]
        }

        # filter for items that overlap with the chosen geometry
        geometry_filter = {
            "type": "GeometryFilter",
            "field_name": "geometry",
            "config": geo_json_geometry
        }

        # filter images acquired in a certain date range
        date_range_filter = {
            "type": "DateRangeFilter",
            "field_name": "acquired",
            "config": {
                "gte": "2010-01-01T00:00:00.000Z"  # ,
                # "lte": "2018-01-01T00:00:00.000Z"
            }
        }

        # filter any images which are more than x% clouds
        cloud_cover_filter = {
            "type": "RangeFilter",
            "field_name": "cloud_cover",
            "config": {
                "lte": cc
            }
        }

        # create a filter that combines the geo and date filters
        filter_comb = {
            "type": "AndFilter",
            "config": [geometry_filter, date_range_filter, cloud_cover_filter]
        }

        # creates the .geojson file to store in the disk (will be needed later)
        aoi = {
            "features": [
                {
                    "geometry": geo_json_geometry,
                    "properties": {},
                    "type": "Feature"
                }
            ],
            "type": "FeatureCollection"
        }
        with open(self.aoi_geojson_path, 'w') as f:
            json.dump(aoi, f, indent=4)

        # Stats API request object
        search_endpoint_request = {
            "interval": "year",
            "item_types": ["REOrthoTile", "PSOrthoTile"],
            "filter": filter_comb
        }

        return search_endpoint_request

    def create_list(self, lat, lon, bufferval, cloud_cover):
        response = \
            requests.post(
                'https://api.planet.com/data/v1/quick-search',
                auth=HTTPBasicAuth(os.environ['PLANET_API_KEY'], ''),
                json=self.get_search_endpoint_request(lat, lon, bufferval, cc=cloud_cover))

        # Handling pagination
        embed_url = urlparse(response.json()["_links"]["_self"])
        response_id = embed_url.path.split("/")[4]

        first_page = \
            ("https://api.planet.com/data/v1/searches/{}" +
             "/results?_page_size={}").format(response_id, 250)

        # kick off the pagination
        self.fetch_page(first_page)

    def handle_page(self, page):
        for item in page["features"]:
            print(item["id"])
        with open(self.ps_list_path, mode='a') as ps_file:
            with open(self.re_list_path, mode='a') as re_file:
                for item in page['features']:
                    if str(item['properties']['item_type']) == 'REOrthoTile':
                        re_file.write(str(item['id']) + '\n')
                    if str(item['properties']['item_type']) == 'PSOrthoTile':
                        ps_file.write(str(item['id']) + '\n')

    def fetch_page(self, search_url):
        page = requests.get(search_url, auth=HTTPBasicAuth(os.environ['PLANET_API_KEY'], ''))
        check_response(page)
        page_json = page.json()
        self.handle_page(page_json)
        next_url = page_json["_links"]["_next"]
        if next_url:
            self.fetch_page(next_url)

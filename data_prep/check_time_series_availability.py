#!/usr/bin/env python3

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

import argparse
import numpy as np
import os
import osgeo.ogr as ogr
import osgeo.osr as osr

import requests
from requests.auth import HTTPBasicAuth

from tools.logger import logger


def get_stats_endpoint_request(lat, lon, cc=0.8):
    """
    Creates a json request for a specified point

    :param lat: latitude
    :param lon: longitude
    :param cc: minimum cloud cover
    :return: json request object

    """

    bufferval = 0.0001

    miny = lat - bufferval
    maxy = lat + bufferval
    minx = lon - bufferval
    maxx = lon + bufferval

    if minx < -180: minx = -180.0
    if maxx > 180: maxx = 180.0
    if miny < -90: miny = -90.0
    if maxy > 90: maxy = 90.0

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

    logger.debug(geo_json_geometry)

    # filter for items the overlap with the chosen geometry
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
            "gte": "2010-01-01T00:00:00.000Z",
            "lte": "2018-01-01T00:00:00.000Z"
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

    # Stats API request object
    stats_endpoint_request = {
        "interval": "year",
        "item_types": ["REOrthoTile", "PSOrthoTile"],
        "filter": filter_comb
    }

    return stats_endpoint_request


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--density',
                        type=float,
                        default=500,
                        help='density of grid defined by distance between two points in km')
    parser.add_argument('--cloud_cover',
                        type=float,
                        default=80,
                        help='maximum cloud cover to be included (percentage)')
    parser.add_argument('--file_name',
                        type=str,
                        default='data_grid',
                        help='output (shape) file name')

    args = parser.parse_args()
    density = args.density
    cloud_cover = args.cloud_cover / 100.0
    file_name = args.file_name

    # Create shape file with all info as attributes

    # set up the shapefile driver
    driver = ogr.GetDriverByName("ESRI Shapefile")

    # create the data source
    data_source = driver.CreateDataSource("{}.shp".format(file_name))

    # create the spatial reference, WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    # create the layer
    layer = data_source.CreateLayer("data_grid", srs, ogr.wkbPoint)

    layer.CreateField(ogr.FieldDefn("Latitude", ogr.OFTReal))
    layer.CreateField(ogr.FieldDefn("Longitude", ogr.OFTReal))

    for year in range(2010, 2018):
        layer.CreateField(ogr.FieldDefn(str(year), ogr.OFTInteger))

    # convert density (distance) into number of needed points
    deg_dist_lat = density / 111.320
    deg_dist_lon = density / 78.71

    num_points_lat = int(152 / deg_dist_lat)
    num_points_lon = int(360 / deg_dist_lon)

    # Create grid of query points (~20 km from each other)
    for lat in list(np.linspace(-68, 84, num_points_lat)):
        for lon in list(np.linspace(-180, 180, num_points_lon)):

            request_json = get_stats_endpoint_request(lat, lon, cloud_cover / 100.0)

            # fire off the POST request
            result = \
                requests.post(
                    'https://api.planet.com/data/v1/stats',
                    auth=HTTPBasicAuth(os.environ['PLANET_API_KEY'], ''),
                    json=request_json)

            try:
                resjson = result.json()
            except Exception as exc:
                logger.error('Some error happened')
                logger.error(exc)

            num_years = len(resjson['buckets'])
            logger.info('{}/{} number of years: {}'.format(lat, lon, num_years))

            if num_years > 2:

                # Create feature
                feature = ogr.Feature(layer.GetLayerDefn())

                # Set attributes
                feature.SetField("Latitude", lat)
                feature.SetField("Longitude", lon)
                for year in range(num_years):
                    cur_year = int(str(resjson['buckets'][year]['start_time'])[:4])
                    feature.SetField(str(cur_year), resjson['buckets'][year]['count'])

                # create WKT geometry for the feature
                wkt = "POINT(%f %f)" % (lon, lat)

                # Create the point from the Well Known Txt
                point = ogr.CreateGeometryFromWkt(wkt)

                # Set the feature geometry using the point
                feature.SetGeometry(point)

                # Create the feature in the layer (shapefile)
                layer.CreateFeature(feature)

                # Dereference the feature
                feature = None

    # Save and close the data source
    data_source = None

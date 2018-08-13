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

import glob
import os
from osgeo import gdal
import requests
from retrying import retry
from requests.auth import HTTPBasicAuth
from multiprocessing.dummy import Pool as ThreadPool

from tools.logger import logger
from data_prep.requests_utils import check_response, retry_if_rate_limit_error, THREADS


class AoiDownload(object):
    """
    Download all PlanetScope and RapidEye analytic assets for a specified AOI and clip them to the AOI
    """
    def __init__(self, indir):
        self.indir = indir
        self.item_type = ["PSOrthoTile", "REOrthoTile"]
        self.asset_type = ["analytic", "analytic_xml", "udm"]
        self.id_files = [os.path.join(self.indir, 'ps-list.txt'), os.path.join(self.indir, 're-list.txt')]
        self.aoi_geojson = os.path.join(self.indir, 'aoi.geojson')
        self.thread_pool = ThreadPool(THREADS)

    @retry(
        wait_exponential_multiplier=1000,
        wait_exponential_max=10000,
        retry_on_exception=retry_if_rate_limit_error,
        stop_max_attempt_number=5)
    def download_xml(self, download_url, item_id):
        response = requests.get(download_url, auth=HTTPBasicAuth(os.environ['PLANET_API_KEY'], ''))
        status = check_response(response)

        output_file = os.path.join(self.indir, item_id.rstrip() + '_metadata.xml')
        logger.debug(output_file)
        if not "<?xml" in response.text:
            status = False

        with open(output_file, 'w') as f:
            f.write(response.text)

        return status

    def download_image(self, download_url, item_id):
        vsicurl_url = '/vsicurl/' + download_url
        logger.debug(vsicurl_url)
        output_file = os.path.join(self.indir, item_id.rstrip() + '_subarea.tif')
        logger.debug(output_file)
        status = True
        try:
            warp_options = ['-r', 'cubic']
            # GDAL Warp crops the image by our AOI, and saves it
            gdal.Warp(output_file, vsicurl_url, dstSRS='EPSG:4326', cutlineDSName=self.aoi_geojson,
                      cropToCutline=True, options=warp_options)
        except Exception as exc:
            logger.error(exc)
            status = False
        return status

    def download_udm(self, download_url, item_id):
        vsicurl_url = '/vsicurl/' + download_url
        logger.debug(vsicurl_url)
        output_file = os.path.join(self.indir, item_id.rstrip() + '_subarea_udm.tif')
        logger.debug(output_file)
        status = True
        try:
            # GDAL Warp crops the image by our AOI, and saves it
            gdal.Warp(output_file, vsicurl_url, dstSRS='EPSG:4326', cutlineDSName=self.aoi_geojson,
                      cropToCutline=True)
        except Exception as exc:
            logger.error(exc)
            status = False
        return status

    def get_download_url(self, asset_list, asset_type):
        download_url = None
        try:
            download_url = asset_list[asset_type]['location']
        except KeyError:
            logger.error('analytic not available')
        except Exception as exc:
            logger.error(exc)
        status = (download_url is not None)
        return download_url, status

    def download_asset(self, asset_list, asset_type, item_id):
        download_url, status = self.get_download_url(asset_list, asset_type)

        if not status:
            return status
        if asset_type == 'analytic':
            status = self.download_image(download_url, item_id)
        elif asset_type == 'udm':
            status = self.download_udm(download_url, item_id)
        else:
            status = self.download_xml(download_url, item_id)
        return status

    def get_asset_list(self, item_id, item_type):
        logger.info(item_id)
        item_url = 'https://api.planet.com/data/v1/item-types/{}/items/{}/assets'.format(item_type,
                                                                                         item_id.rstrip())
        logger.info(item_url)
        # Request a new download URL
        result = requests.get(item_url, auth=HTTPBasicAuth(os.environ['PLANET_API_KEY'], ''))
        logger.info(result)
        return result.json()

    def download_image_and_metadata(self, item_info):
        (item_id, item_type) = item_info
        asset_list = self.get_asset_list(item_id, item_type)
        status = False
        for asset_type in self.asset_type:
            status |= self.download_asset(asset_list, asset_type, item_id)
        return status

    def download_aoi(self):
        for i, id_list in enumerate(self.id_files):
            with open(id_list) as id_file:
                items = [(item_id, self.item_type[i]) for item_id in id_file]
                self.thread_pool.map(self.download_image_and_metadata, items)

    def get_resolution(self, ps_image):
        datafile = gdal.Open(ps_image)
        cols = datafile.RasterXSize
        rows = datafile.RasterYSize
        datafile = None
        return cols, rows

    def resample_re(self, clean_it=True):
        re_filelist = glob.glob(os.path.join(self.indir, '*RapidEye*.tif'))
        ps_list_file = self.id_files[0]

        with open(ps_list_file) as ps:
            ps_list_content = ps.readlines()

        found = False
        for line in ps_list_content:
            ps_file = line.strip('\n')
            ps_image = os.path.join(self.indir, ps_file + '_subarea.tif')
            if os.path.exists(ps_image):
                found = True
                break

        if found:
            cols, rows = self.get_resolution(ps_image)
        else:
            return

        for fn in re_filelist:
            if '_resampled.tif' in fn:
                raise Exception("File was already resampled")
            outfn = fn[:-4] + '_resampled.tif'
            cmd = 'gdalwarp -r cubic -ts %s %s %s %s' % (cols, rows, fn, outfn)
            logger.info(cmd)
            os.system(cmd)

        if clean_it:
            old_files = glob.glob(os.path.join(self.indir, '*RapidEye*subarea.tif'))
            old_udm_files = glob.glob(os.path.join(self.indir, '*RapidEye*subarea_udm.tif'))
            old_files += old_udm_files
            for f in old_files:
                os.remove(f)

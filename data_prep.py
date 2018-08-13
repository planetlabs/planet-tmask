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
import os

from data_prep.create_download_list import CreateDownloadList
from data_prep.create_filelists import CreateFileLists
from data_prep.activate import ActivateAssets
from data_prep.download_aoi import AoiDownload
from data_prep.convert_radiance_to_toar import TOARConverter
from tools.logger import logger
from tools.folders_handle import create_or_clean_folder

INDIR = '/home/{}/data/input'.format(os.environ['USER'])
OUTDIR = '/home/{}/data/toar_images'.format(os.environ['USER'])
PS_LIST_FILE = os.path.join(INDIR, 'ps-list.txt')
RE_LIST_FILE = os.path.join(INDIR, 're-list.txt')


def create_download_list():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lat',
                        type=float,
                        help='latitude of query point')
    parser.add_argument('--lon',
                        type=float,
                        help='longitude of query point')
    parser.add_argument('--bufferval',
                        type=float,
                        default=0.001,  # should be as small as possible
                        help='box size around coordinates point')
    parser.add_argument('--cloud_cover',
                        type=float,
                        default=80,
                        help='maximum cloud cover to be included (percentage)')

    args = parser.parse_args()

    lat = args.lat
    lon = args.lon
    cloud_cover = args.cloud_cover / 100.0

    bufferval = args.bufferval

    if not args.lat and not args.lon:
        parser.error('Error: please specify coordinates')

    cdl = CreateDownloadList(INDIR)
    cdl.create_list(lat, lon, bufferval, cloud_cover)


def download_assets():
    ad = AoiDownload(INDIR)
    ad.download_aoi()
    ad.resample_re()


def create_file_lists():
    cfl = CreateFileLists(OUTDIR)
    imagelist, datelist = cfl.create_file_lists()
    msg = 'Successfully created {} and {} lists to supply to TMASK algorithm'
    logger.info(msg.format(imagelist, datelist))


def activate_assets():
    ActivateAssets().activate_assets(RE_LIST_FILE, 'REOrthoTile', 'analytic')
    ActivateAssets().activate_assets(PS_LIST_FILE, 'PSOrthoTile', 'analytic')


def apply_toar_correction():
    TOARConverter(INDIR, OUTDIR).process_all()


def prepare_folders():
    create_or_clean_folder(INDIR)
    create_or_clean_folder(OUTDIR)


if __name__ == '__main__':
    prepare_folders()
    create_download_list()
    activate_assets()
    download_assets()
    apply_toar_correction()
    create_file_lists()

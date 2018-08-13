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

import os

user = os.environ['USER']
DATA_FOLDER = '/home/{}/data/'.format(user)
ANALYTIC_LIST_FILE = os.path.join(DATA_FOLDER, 'toar_images/image_list.txt')
DATE_LIST_FILE = os.path.join(DATA_FOLDER, 'toar_images/juliandate_list.txt')
COEFFICIENTS_FOLDER = os.path.join(DATA_FOLDER, 'coeffs')
RESULTS_FOLDER = os.path.join(DATA_FOLDER, 'results')
PLOTS_FOLDER = os.path.join(DATA_FOLDER, 'plots')


def create_or_clean_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    else:
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as exc:
                print(exc)
                raise

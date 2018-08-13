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

import os

import requests
from retrying import retry
from multiprocessing.dummy import Pool as ThreadPool

from tools.logger import logger
from data_prep.requests_utils import (check_response,
                                      retry_if_rate_limit_error,
                                      retry_cases,
                                      StillActivatingException,
                                      THREADS)


class ActivateAssets(object):
    def __init__(self):
        self.session = requests.Session()
        self.session.auth = (os.environ.get('PLANET_API_KEY'), '')
        self.asset_url = 'https://api.planet.com/data/v1/item-types/{}/items/{}/assets/'
        self.thread_pool = ThreadPool(THREADS)

    def get_activation_status(self, response, asset_type):
        try:
            return response.json()[asset_type]['status']
        except KeyError as exc:
            return

    def get_activation_url(self, response, asset_type):
        return response.json()[asset_type]['_links']['activate']

    @retry(
        wait_exponential_multiplier=1000,
        wait_exponential_max=10000,
        retry_on_exception=retry_if_rate_limit_error,
        stop_max_attempt_number=5)
    def trigger_activation(self, data):
        item_id, item_type, asset_type = data

        url = self.asset_url.format(item_type, item_id)
        logger.info('Request: {}'.format(url))

        response = self.session.get(url)
        check_response(response)

        activation_status = self.get_activation_status(response, asset_type)

        if activation_status is None:
            pass
        elif activation_status == 'active':
            logger.info('{} {} {}: already active'.format(item_id, asset_type, item_type))
        else:
            url = self.get_activation_url(response, asset_type)
            response = self.session.post(url)
            msg = '{} {} {}: started activation'.format(item_id, item_type, asset_type)
            check_response(response, msg)

    @retry(
        wait_exponential_multiplier=5000,
        wait_exponential_max=50000,
        retry_on_exception=retry_cases,
        stop_max_attempt_number=50)
    def check_activation(self, data):
        item_id, item_type, asset_type = data

        url = self.asset_url.format(item_type, item_id)
        logger.info('Request: {}'.format(url))
        response = self.session.get(url)

        check_response(response)

        activation_status = self.get_activation_status(response, asset_type)
        logger.info('{} {} {}: {}'.format(item_id, item_type, asset_type, activation_status))
        if activation_status == 'active':
            return
        elif activation_status == 'activating':
            raise StillActivatingException()

    def process_activation(self, func, id_list, item_type, asset_type):
        item_list = [(item_id, item_type, asset_type) for item_id in id_list]
        return self.thread_pool.map(func, item_list)

    def activate_assets(self, idlist_file, item, asset):
        with open(idlist_file) as f:
            id_list = [i.strip() for i in f.readlines()]
        logger.info('%d available %s images' % (len(id_list), item))

        self.process_activation(self.trigger_activation, id_list, item, asset)
        self.process_activation(self.check_activation, id_list, item, asset)

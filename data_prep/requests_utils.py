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

import sys

from tools.logger import logger

THREADS = 5


class RateLimitException(Exception):
    pass


class StillActivatingException(Exception):
    pass


def retry_if_rate_limit_error(exception):
    return isinstance(exception, RateLimitException)


def retry_cases(exception):
    return isinstance(exception, RateLimitException) or isinstance(exception, StillActivatingException)


def check_response(response, msg=None, text=False):
    successful = False
    if text:
        logger.info('Response: {} - {}'.format(response.status_code, response.text))
    else:
        logger.info('Response: {}'.format(response.status_code))
    if response.status_code == 429:
        error_msg = 'Error code 429: rate limit exceeded - retrying'
        logger.error(error_msg)
        raise RateLimitException('Rate limit error')
    elif response.status_code == 401:
        error_msg = "Error code 401: the API Key you provided is invalid, or does not have the required permissions " \
                    "for this AOI or TOI.\n 1. Ensure your API key is stored in your *nix environment " \
                    "('export PLANET_API_KEY=Your_API_Key'), or passed as an argument in the command " \
                    "('--key Your_API_Key')\n 2. Check that it is correct at http://planet.com/account\n " \
                    "3. Confirm you have the right permissions to access this AOI and TOI with your Account Manager"
        logger.error(error_msg)
        sys.exit(1)
    elif response.status_code == 400:
        error_msg = 'Error code {}: {}'.format(response.status_code, response.text)
        logger.error(error_msg)
        sys.exit(1)
    else:
        if msg:
            logger.info(msg)
        successful = True
    return successful

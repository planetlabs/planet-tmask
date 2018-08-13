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

import glob
import os
from datetime import datetime


class CreateFileLists(object):
    def __init__(self, outdir):
        self.outdir = outdir

    def date_to_julian_day(self, my_date):
        """
        Returns the Julian day number of a date.
        """

        a = (14 - my_date.month) // 12
        y = my_date.year + 4800 - a
        m = my_date.month + 12 * a - 3

        return my_date.day + ((153 * m + 2) // 5) + 365 * y + y // 4 - y // 100 + y // 400 - 32045

    def create_file_lists(self):

        infilelist = glob.glob(os.path.join(self.outdir, '*.tif'))

        filelist_name = os.path.join(self.outdir, 'image_list.txt')
        datelist_name = os.path.join(self.outdir, 'juliandate_list.txt')

        juldatelist = []

        for fn in infilelist:
            if "RapidEye" in fn:
                my_date = os.path.basename(fn).split('_')[0]
                jul_date = self.date_to_julian_day(datetime.strptime(my_date, "%Y%m%d"))
            else:
                my_date = os.path.basename(fn).split('_')[2]
                jul_date = self.date_to_julian_day(datetime.strptime(my_date, "%Y-%m-%d"))
            juldatelist.append(jul_date)

        ziplist = zip(juldatelist, infilelist)
        ziplist = list(ziplist)
        ziplist.sort()

        with open(datelist_name, mode='w') as date_file:
            with open(filelist_name, mode='w') as list_file:
                for jd, fn in ziplist:
                    date_file.write(str(jd) + '\n')
                    list_file.write(fn + '\n')

        return filelist_name, datelist_name

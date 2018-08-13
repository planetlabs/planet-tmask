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

"""
Script to create time series plots visualising the tmask analysis for the corner pixels of the AOI

"""
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

from tools.folders_handle import PLOTS_FOLDER, COEFFICIENTS_FOLDER


def draw_plots(plots_folder, coeff_folder):

    pixels = ['ul', 'll', 'ur', 'lr']

    for pixel in pixels:

        d = np.load(os.path.join(coeff_folder, 'tmask_date.npy'))
        co = np.load(os.path.join(coeff_folder, 'tmask_coeffs_plot_%s.npy') %(pixel))
        r = np.load(os.path.join(coeff_folder, 'tmask_analytic_plot_%s.npy') %(pixel))

        juldate_start = int(d[0])
        juldate_end = int(d[-1])
        juldate = np.linspace(juldate_start, juldate_end, juldate_end - juldate_start)
        num_days = juldate_end - juldate_start
        daysPerYear = 365

        constant = np.ones(juldate.shape)
        cosT = np.cos(2.0 * np.pi * juldate / daysPerYear)
        sinT = np.sin(2.0 * np.pi * juldate / daysPerYear)
        cosNT = np.cos(2.0 * np.pi * juldate / num_days)
        sinNT = np.sin(2.0 * np.pi * juldate / num_days)

        y = []
        ref = []

        bands = 4
        for band in range(bands):
            constant_fitted = constant * co[band][0]
            cosT_fitted = cosT * co[band][1]
            sinT_fitted = sinT * co[band][2]
            cosNT_fitted = cosNT * co[band][3]
            sinNT_fitted = sinNT * co[band][4]

            y.append(constant_fitted + cosT_fitted + sinT_fitted + cosNT_fitted + sinNT_fitted)

            refc = r[:,band]

            ref.append(refc)

        df = pd.DataFrame({'julian':juldate})
        df['date'] = pd.to_datetime(df['julian'], unit='D', origin='julian')
        df2 = pd.DataFrame({'coef_date':d})
        df2['coeff_date'] = pd.to_datetime(df2['coef_date'], unit='D', origin='julian')

        fig = plt.figure(figsize=(18.0, 7.0))
        fig.suptitle("Robust Iteratively Reweighted Least Squares (RIRLS) - %s pixel" %(pixel.upper()))

        sp = 4
        axes1 = fig.add_subplot(1, sp, 1)
        axes2 = fig.add_subplot(1, sp, 2)
        axes3 = fig.add_subplot(1, sp, 3)
        axes4 = fig.add_subplot(1, sp, 4)

        fig.subplots_adjust(wspace=0.4)

        axes1.set_xlim([min(df.date), max(df.date)])
        axes2.set_xlim([min(df.date), max(df.date)])
        axes3.set_xlim([min(df.date), max(df.date)])
        axes4.set_xlim([min(df.date), max(df.date)])

        axes1.plot(df.date,y[0], 'k-', df2.coeff_date, ref[0], 'bo')
        axes1.set_xlabel('\nDate')
        axes1.set_ylabel('Band 1 (Blue) Top of Atmosphere Reflectance (X 10^4)')

        axes2.plot(df.date,y[1], 'k-', df2.coeff_date, ref[1], 'go')
        axes2.set_xlabel('\nDate')
        axes2.set_ylabel('Band 2 (Green) Top of Atmosphere Reflectance (X 10^4)')

        axes3.plot(df.date,y[2], 'k-', df2.coeff_date, ref[2], 'ro')
        axes3.set_xlabel('\nDate')
        axes3.set_ylabel('Band 3 (Red) Top of Atmosphere Reflectance (X 10^4)')

        axes4.plot(df.date,y[3], 'k-', df2.coeff_date, ref[3], 'mo')
        axes4.set_xlabel('\nDate')
        axes4.set_ylabel('Band 4 (NIR) Top of Atmosphere Reflectance (X 10^4)')

        fn ='tmask_%s.png' %(pixel)
        plotfn = os.path.join(plots_folder, fn)
        plt.savefig(plotfn,dpi=72)


if __name__ == "__main__":
    draw_plots(PLOTS_FOLDER, COEFFICIENTS_FOLDER)

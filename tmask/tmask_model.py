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

import numpy
import os
import time
import argparse
from osgeo import gdal

from tmask import robustregression
from tmask.create_plot import draw_plots
from tools.folders_handle import (create_or_clean_folder,
                                  ANALYTIC_LIST_FILE,
                                  DATE_LIST_FILE,
                                  COEFFICIENTS_FOLDER,
                                  PLOTS_FOLDER)


def array_shape(fname, numBands=4):
    print (fname)
    with open(fname) as f:
        for i, li in enumerate(f):
            pass

        img = gdal.Open(li.rstrip(), gdal.GA_ReadOnly)
        print (li.rstrip())
        xsize = img.RasterXSize
        ysize = img.RasterYSize
        print (xsize)
        print (ysize)
        img = None

    return (i + 1, numBands, ysize, xsize)


def tmask(args, analyticlist, datelist, basepath, nodataval=0, coeffs_file=""):

    # Open all input files and create a data stack
    bands = 4
    numDates, numBands, numRows, numCols = array_shape(analyticlist, numBands=bands)
    analyticStack = numpy.empty((numDates, numBands, numRows, numCols), dtype=numpy.uint16, order='C')

    # We need to keep a copy of the unaltered analytic stack in case we use UDMs
    if args.use_udm:
        analyticStackOrig = numpy.empty((numDates, numBands, numRows, numCols), dtype=numpy.uint16, order='C')

    with open(analyticlist) as an_file:
        for i, fn in enumerate(an_file):

            print(i, fn)
            img = gdal.Open(fn.rstrip(), gdal.GA_ReadOnly)

            for band in range(1, bands+1):
                # Read raster as arrays
                if 'RapidEye' in fn and band >= 4:
                    print ('RE case')
                    banddataraster = img.GetRasterBand(band + 1)
                else:
                    banddataraster = img.GetRasterBand(band)

                dataraster = banddataraster.ReadAsArray()
                analyticStack[i, band - 1] = dataraster

            img = None

            if args.use_udm:
                print ('Excluding cloud pixels from UDM')

                # construct UDM file name
                udm_fn = fn.replace('_resampled_toar', '_udm_resampled')
                udm_fn = udm_fn.replace('_toar', '_udm')

                udm_fn = udm_fn.replace('toar_images', 'input')

                # Open UDM and extract cloud bit
                udm = gdal.Open(udm_fn.rstrip(), gdal.GA_ReadOnly)
                udm_band = udm.GetRasterBand(1)
                udmraster = udm_band.ReadAsArray()

                # Extract cloud bit in a boolean array
                cloud_mask = (numpy.bitwise_and(udmraster, 2)).astype(numpy.bool)

                # mask cloud pixels in analytic image
                analyticStackOrig[i, :] = analyticStack[i, :]
                analyticStack[i, :] = analyticStack[i, :] * numpy.invert(cloud_mask)

                udm = None

    juldatelist = []
    with open(datelist) as da_file:
        for da in da_file:
            juldatelist.append(float(da.rstrip()))

    juldate = numpy.array(juldatelist)

    juldate_start = int(juldate[0])
    juldate_end = int(juldate[-1])

    num_days = juldate_end - juldate_start

    daysPerYear = 365

    # Fit the model for each band.

    # Set up the independant variables for the robust regression. These are functions of date.
    constant = numpy.ones(juldate.shape, order='C')
    cosT = numpy.cos(2.0 * numpy.pi * juldate / daysPerYear)
    sinT = numpy.sin(2.0 * numpy.pi * juldate / daysPerYear)
    cosNT = numpy.cos(2.0 * numpy.pi * juldate / num_days)
    sinNT = numpy.sin(2.0 * numpy.pi * juldate / num_days)

    x = numpy.array([constant, cosT, sinT, cosNT, sinNT], order='C')
    numParams = len(x)

    # Now fit for each band. The c array is the coeefficients of the fits.
    c = numpy.zeros((numBands, numParams, numRows, numCols), dtype=numpy.float32, order='C')
    rmse = numpy.zeros((numBands, numRows, numCols), dtype=numpy.float32, order='C')
    for bandNdx in range(numBands):
        print('Fitting band %d' % bandNdx)
        y = numpy.ascontiguousarray(
            analyticStack[:, bandNdx, :, :],
            dtype=numpy.double)
        regObj = robustregression.gsl_multifit_robust(x, y, method=robustregression.GSL_METHOD_BISQUARE,
                                                      nullVal=0)
        c[bandNdx, :, :, :] = regObj.coeffs
        rmse[bandNdx, :, :] = regObj.rmse

    # Write coefficents to disk for one pixel (for creating plots) as well as
    # the whole array (for further analysis)
    writeToFile = True
    if writeToFile:
        if not os.path.exists(basepath):
            os.mkdir(basepath)

        outCoeffile = os.path.join(basepath, "tmask_coeffs_plot_ul")
        numpy.save(outCoeffile, c[:, :, 0, 0])
        outCoeffile = os.path.join(basepath, "tmask_coeffs_plot_ll")
        numpy.save(outCoeffile, c[:, :, 0, -1])
        outCoeffile = os.path.join(basepath, "tmask_coeffs_plot_lr")
        numpy.save(outCoeffile, c[:, :, -1, 0])
        outCoeffile = os.path.join(basepath, "tmask_coeffs_plot_ur")
        numpy.save(outCoeffile, c[:, :, -1, -1])
        outCoeffile = os.path.join(basepath, "tmask_coeffs_complete")
        numpy.save(outCoeffile, c[:, :, :, :])

        outDatefile = os.path.join(basepath, "tmask_date")
        numpy.save(outDatefile, juldate)

        outRMSEfile = os.path.join(basepath, "tmask_rmse")
        numpy.save(outRMSEfile, rmse)

        if args.use_udm:
            analyticStack = analyticStackOrig

        outAnfile = os.path.join(basepath, "tmask_analytic_plot_ul")
        numpy.save(outAnfile, analyticStack[:,:,0,0])
        outAnfile = os.path.join(basepath, "tmask_analytic_plot_ll")
        numpy.save(outAnfile, analyticStack[:, :, 0, -1])
        outAnfile = os.path.join(basepath, "tmask_analytic_plot_lr")
        numpy.save(outAnfile, analyticStack[:, :, -1, 0])
        outAnfile = os.path.join(basepath, "tmask_analytic_plot_ur")
        numpy.save(outAnfile, analyticStack[:, :, -1, -1])
        outAnfile = os.path.join(basepath, "tmask_analytic_complete")
        numpy.save(outAnfile, analyticStack[:, :, :, :])


def parse_params():
    parser = argparse.ArgumentParser()
    parser.add_argument('--use-udm',
                        action='store_true',
                        help='use UDM to exclude cloud pixels for training',
                        default=False)

    return parser.parse_args()


if __name__ == "__main__":
    start = time.time()

    args = parse_params()
    create_or_clean_folder(COEFFICIENTS_FOLDER)
    tmask(args, ANALYTIC_LIST_FILE, DATE_LIST_FILE, COEFFICIENTS_FOLDER)

    elapsed = time.time() - start
    print('Elapsed time (tmask): %g seconds' % (elapsed))

    create_or_clean_folder(PLOTS_FOLDER)
    draw_plots(PLOTS_FOLDER, COEFFICIENTS_FOLDER)


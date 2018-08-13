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
import time
import argparse

from osgeo import gdal
import numpy as np
import scipy.ndimage.filters as filters

from tools.folders_handle import (create_or_clean_folder,
                                  COEFFICIENTS_FOLDER,
                                  ANALYTIC_LIST_FILE,
                                  RESULTS_FOLDER)


def calculate_tmask_model(juldates, coeffs):
    fits = []
    num_days = int(juldates[-1] - juldates[0])
    constant_fitted = coeffs[:, 0]

    for juldate in juldates:
        cosT_fitted = np.multiply(np.cos(2.0 * np.pi * juldate / 365), coeffs[:, 1])
        sinT_fitted = np.multiply(np.sin(2.0 * np.pi * juldate / 365), coeffs[:, 2])
        cosNT_fitted = np.multiply(np.cos(2.0 * np.pi * juldate / num_days), coeffs[:, 3])
        sinNT_fitted = np.multiply(np.sin(2.0 * np.pi * juldate / num_days), coeffs[:, 4])
        val = constant_fitted + cosT_fitted + sinT_fitted + cosNT_fitted + sinNT_fitted
        fits += [val]

    return np.array(fits)


def get_fitted_curve(coefficients_folder):
    outDatefile = os.path.join(coefficients_folder, "tmask_date.npy")
    juldates = np.load(outDatefile)
    outCoeffile = os.path.join(coefficients_folder, "tmask_coeffs_complete.npy")
    coeffs = np.load(outCoeffile)

    return calculate_tmask_model(juldates, coeffs)


def get_analytic_img_filelist(analytic_list_file):
    """
    Read analytic image file list from disk and return as list object

    :param analytic_list_file: textfile with input file names
    :return: list object of all input (TOAR) files

    """

    with open(analytic_list_file, 'r') as images:
        img_files = images.readlines()

    return [fn.rstrip() for fn in img_files]


def get_threshold_info(args, coef_folder, default_threshold=0.04):
    outRMSEfile = os.path.join(coef_folder, "tmask_rmse.npy")
    rmse = np.load(outRMSEfile)

    # Start thresholding
    if args.dynamic_threshold:
        thresholds_cloud = rmse
    else:
        # need to multiply by 10000 because of scaling of TOAR
        thresholds_cloud = np.ones_like(rmse) * default_threshold * 10000

    return (thresholds_cloud, args.dynamic_threshold)


def get_projection_data(ref_img):
    ref_ds = gdal.Open(ref_img)
    projection, geotransform = ref_ds.GetProjection(), ref_ds.GetGeoTransform()
    del ref_ds
    return projection, geotransform


def get_filename(folder, prefix, img_file):
    return os.path.join(folder, prefix.join(os.path.splitext(os.path.split(img_file)[1])))


def write_image(fn, img_info, datatype, image, bands):
    """
    Write an image to disk

    :param fn: filename
    :param img_info: tuple with all necessary image information
    :param datatype: image datatype
    :param image: numpy array with image values
    :param bands: number of bands
    :return: no return value

    """
    drv, height, width, projection, geotransform = img_info
    print('Writing file "%s"' % fn)
    ds = drv.Create(fn, height, width, bands, datatype)
    ds.SetProjection(projection)
    ds.SetGeoTransform(geotransform)
    if bands == 1:
        outband = ds.GetRasterBand(bands)
        outband.WriteArray(image)
    else:
        for band in range(bands):
            outband = ds.GetRasterBand(band + 1)
            outband.WriteArray(image[band])
    del ds


def create_cloud_masks(img_files, threshold_info, coefficients_folder, results_folder):
    """
    Create synthetic prediction images and cloud/cloud shadow masks

    :param img_files: list of input TOAR images
    :param threshold_info: tuple containing array of threshold value and flat if dynamic thresholding is used
    :param coefficients_folder: Folder where coefficients were stored by the TMASK model
    :param results_folder: Folder where result images are stored
    :return: no return value

    """

    # Dims like image slices, bands, pix X, pix Y
    outAnfile = os.path.join(coefficients_folder, "tmask_analytic_complete.npy")
    analytic_stack = np.load(outAnfile)
    num_imgs, bands, width, height = analytic_stack.shape
    gtiff_drv = gdal.GetDriverByName('GTiff')
    projection, geotransform = get_projection_data(img_files[0])

    image_info = (gtiff_drv, height, width, projection, geotransform)

    # Write out prediction images for visualisation/debugging purposes
    predicted_stack = get_fitted_curve(coefficients_folder)
    for i, image in enumerate(predicted_stack):
        fn = get_filename(results_folder, '_pred', img_files[i])
        write_image(fn, image_info, gdal.GDT_Float32, image, bands)

    band1_above_t = np.zeros((num_imgs, 1, width, height), dtype=bool)
    band2_above_t = np.zeros((num_imgs, 1, width, height), dtype=bool)
    band3_above_t = np.zeros((num_imgs, 1, width, height), dtype=bool)
    band4_above_t = np.zeros((num_imgs, 1, width, height), dtype=bool)
    band1_below_minus_t = np.zeros((num_imgs, 1, width, height), dtype=bool)
    band2_below_minus_t = np.zeros((num_imgs, 1, width, height), dtype=bool)
    band3_below_minus_t = np.zeros((num_imgs, 1, width, height), dtype=bool)
    band4_below_minus_t = np.zeros((num_imgs, 1, width, height), dtype=bool)

    thresholds_cloud, dynamic = threshold_info
    # Apply thresholds therefore creating eight boolean arrays
    for i in range(num_imgs):
        band1_above_t[i][0] = (analytic_stack[i][0] - predicted_stack[i][0]) > thresholds_cloud[0]
        band2_above_t[i][0] = (analytic_stack[i][1] - predicted_stack[i][1]) > thresholds_cloud[1]
        band3_above_t[i][0] = (analytic_stack[i][2] - predicted_stack[i][2]) > thresholds_cloud[2]
        band4_above_t[i][0] = (analytic_stack[i][3] - predicted_stack[i][3]) > thresholds_cloud[3]

        band1_below_minus_t[i][0] = (analytic_stack[i][0] - predicted_stack[i][0]) < -thresholds_cloud[0]
        band2_below_minus_t[i][0] = (analytic_stack[i][1] - predicted_stack[i][1]) < -thresholds_cloud[1]
        band3_below_minus_t[i][0] = (analytic_stack[i][2] - predicted_stack[i][2]) < -thresholds_cloud[2]
        band4_below_minus_t[i][0] = (analytic_stack[i][3] - predicted_stack[i][3]) < -thresholds_cloud[3]

    # Combine boolean arrays
    if dynamic:
        # for PlanetScope it often seems to work better using a dynamic threshold to all bands
        # 1- clouds if the values are above the threshold for all bands in one image
        # 2- cloud shadows if the values are below the threshold for all bands in one image
        clouds = band1_above_t * band2_above_t * band3_above_t * band4_above_t
        cloud_shadows = band1_below_minus_t * band2_below_minus_t * band3_below_minus_t * band4_below_minus_t
    else:
        # Here we follow the original TMASK paper
        # We can't compute the snow index as we don't have a SWIR band therefore we omit the whole cloud vs snow check
        clouds = band2_above_t
        cloud_shadows = np.logical_and(np.logical_not(band2_above_t), band4_below_minus_t)

    # create output mask images
    for i in range(num_imgs):
        # set all values in clouds to 2, and cloud_shadows to 1
        # use a median filter to get rid of very small clumps
        cloud_byte = filters.median_filter(clouds[i][0], size=(3,3)).astype(np.byte) \
                     * 2 + filters.median_filter(cloud_shadows[i][0], size=(3,3)).astype(np.byte)

        # only write cloud/shadow masks if anything is detected
        if np.any(cloud_byte):
            fn = get_filename(results_folder, '_cloud', img_files[i])
            write_image(fn, image_info, gdal.GDT_Byte, cloud_byte, 1)


def parse_params():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dynamic-threshold',
                        action='store_true',
                        help='use a dynamic threshold based on RMSE instead of static ones',
                        default=False)

    return parser.parse_args()


if __name__ == "__main__":
    start = time.time()
    args = parse_params()
    create_or_clean_folder(RESULTS_FOLDER)
    analytic_img_filelist = get_analytic_img_filelist(ANALYTIC_LIST_FILE)
    threshold_info = get_threshold_info(args, COEFFICIENTS_FOLDER)
    create_cloud_masks(analytic_img_filelist, threshold_info, COEFFICIENTS_FOLDER, RESULTS_FOLDER)

    elapsed = time.time() - start
    print('Elapsed time (cloud mask creation): %g seconds' % (elapsed))
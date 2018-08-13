/**
 *
 * Copyright 2018, Planet Labs, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include <stdio.h>

#include <gsl/gsl_matrix.h>
#include <gsl/gsl_multifit.h>
#include <math.h>


/*  A wrapper around the GSL multi-variate robust regression routine.

    This routine should only ever be called from the Python wrapper function, so if the
    parameters need to be changed, only these two files have to be changed.

    The array variables are given as pointers to doubles, and are referenced as
    1-d arrays. However, the indexes are calculated as though they were multi-dimensional
    arrays, and the dimensions are described below.

    Input Variables
    ***************

    numParams is the number of parameters to be fitted, also equal
        to the number of independent variables
    numImages is the number of images in the stack, and corresponds to the number
        of points in each fit (before removing nulls)
    numRows is the number of rows in the image
    numCols is the number of columns in the image

    The x parameter contains the values of all the independent variables.
    It comes in one of two flavours, depending on the value of the
    perPixelX parameter. If perPixelX is 1, then the x parameter is a 4-dimensional
    array of doubles, with shape
        (numParams, numImages, numRows, numCols)
    otherwise it is a 2-dimensional array with shape
        (numParams, numImages)
    and it is assumed that the independent variables are constant over all pixels.
    This latter is the most likely case.

    The Y variable is notionally a 3-dimensional array of doubles.
    The shape should be
        (numImages, numRows, numCols)
    It contains the values of the dependent variable.

    The nullVal parameter is a scalar double value. Any occurrence of this value in the
    y array will exclude that point from the fit.

    Output Variables
    ****************

    The following variables are calculated within this routine, and passed back via the
    pointers in the parameter list.

    The c array is a 3-dimensional array of doubles. It corresponds to an image
    stack of the fitted coefficients, and its shape is
        (numParams, numRows, numCols)

    The adj_Rsqrd array stores the adjusted R^2 coefficient of determination
        statistic.

*/
void wrap_gsl_multifit_robust(double *x, double *y, double *c, double *adj_Rsqrd,
        int *numIter, double *rmse, int method, int perPixelX,
        int numRows, int numCols, int numImages, int numParams,
        int numRowsX, int numColsX, double nullVal) {
    int row, col, img, param, n, xNdx, yNdx, pixNdx;
    gsl_matrix *gslX, *gslCov;
    gsl_vector *gslY, *gslC;
    gsl_multifit_robust_workspace *workspace;
    gsl_multifit_robust_type *regressionType;
    gsl_multifit_robust_stats stats;
    int gslErrorCode;

    /* Turn off the default error handler, which aborts at the first error. */
    gsl_set_error_handler_off();

    /* Translate the integer type given into the corresponding GSL pointer */
    switch (method) {
        case 1: regressionType = gsl_multifit_robust_bisquare; break;
        case 2: regressionType = gsl_multifit_robust_cauchy; break;
        case 3: regressionType = gsl_multifit_robust_fair; break;
        case 4: regressionType = gsl_multifit_robust_huber; break;
        case 5: regressionType = gsl_multifit_robust_ols; break;
        case 6: regressionType = gsl_multifit_robust_welsch; break;
    }

    /* These structures can be allocated outside the pixel loop */
    gslCov = gsl_matrix_calloc(numParams, numParams);
    gslC = gsl_vector_calloc(numParams);

    /* Loop over all pixels */
    for (row=0; row<numRows; row++) {
        for (col=0; col<numCols; col++) {
            /* Count how many non-null y values we have. */
            n = 0;
            for (img=0; img<numImages; img++) {
                if (y[img*numRows*numCols+row*numCols+col] != nullVal) n++;
            }

            /* Allocate various structures, now we know how many non-nulls */
            if (n >= numParams) {
                workspace = gsl_multifit_robust_alloc(regressionType, n, numParams);
                gslX = gsl_matrix_calloc(n, numParams);
                gslY = gsl_vector_calloc(n);

                /* Copy the data from this pixel into the relevant GSL structures. Note
                   that we skip over null values, based on nulls in the y variable.
                */
                n = 0;
                for (img=0; img<numImages; img++) {
                    yNdx = img*numRows*numCols+row*numCols+col;
                    if (y[yNdx] != nullVal) {
                        gslY->data[n*gslY->stride] = y[yNdx];
                        for (param=0; param<numParams; param++) {
                            if (perPixelX == 0) {
                                xNdx = param * numImages + img;
                            } else {
                                xNdx = param * numRowsX * numColsX * numImages +
                                    img * numRowsX * numColsX + row * numColsX + col;
                            }
                            gslX->data[n*gslX->tda + param] = x[xNdx];
                        }
                        n++;
                    }
                }

                /* Do the regression fit */
                gslErrorCode = gsl_multifit_robust(gslX, gslY, gslC, gslCov, workspace);

                if (gslErrorCode == 0) {
                    /* Copy the coefficients back into the image stack of coefficients */
                    for (param=0; param<numParams; param++) {
                        c[param*numRows*numCols + row*numCols + col] = gslC->data[param*gslC->stride];
                    }

                    /* Copy some useful statistics into their arrays */
                    stats = gsl_multifit_robust_statistics(workspace);
                    pixNdx = row*numCols + col;
                    adj_Rsqrd[pixNdx] = stats.adj_Rsq;
                    numIter[pixNdx] = stats.numit;
                    rmse[pixNdx] = stats.rmse;
                }

                /* Free per-pixel structures */
                gsl_matrix_free(gslX);
                gsl_vector_free(gslY);
                gsl_multifit_robust_free(workspace);
            }
        }
    }


    /* Free the other structures */
    gsl_vector_free(gslC);
    gsl_matrix_free(gslCov);
}

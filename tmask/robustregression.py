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

import robreg
import numpy


class RegressionError(Exception):
    """
    Generic object raised by regression errors.
    """
    pass


REGSTATS_MINIMAL = 0
REGSTATS_PARTIAL = 1
REGSTATS_FULL = 2

GSL_METHOD_BISQUARE = 1
GSL_METHOD_CAUCHY = 2
GSL_METHOD_FAIR = 3
GSL_METHOD_HUBER = 4
GSL_METHOD_OLS = 5
GSL_METHOD_WELSCH = 6


class GslRegressionResults(object):
    """
    Hold results from a call to a GSL robust regression routine.

    Attributes:
        coeffs          Coefficients of final fit, shape (numParams, numRows, numCols)
        adj_Rsqrd       Adjusted R-squared of fit, shape (numRows, numCols)
        numIter         Number of iterations required, shape (numRows, numCols)
        rmse            Root mean square residual, shape (numRows, numCols)

    """


def gsl_multifit_robust(x, y, method=GSL_METHOD_BISQUARE, nullVal=None, perPixelX=False):
    """
    This is a wrapper around the GSL routine for multivariate robust regression
        gsl_multifit_robust()
    See http://www.gnu.org/software/gsl/manual/html_node/Robust-linear-regression.html#Robust-linear-regression
    for details

    The wrapper is set up for working on image stacks, fitting regressions through the stack, on a per-pixel basis.

    The y variable is the dependant variable, and should be a 3-d numpy array of shape
        (numImages, numRows, numCols)
    Conceptually, for each pixel (i, j), a separate regression is fitted to the y values
        y[:, i, j]

    The x parameter is a numpy array holding all the values of all the independent
    variables. Its shape depends on the value of the perPixelX flag. If perPixelX is False,
    then the independent variables are assumed to be constant for all pixels, and the shape
    of x is
        (numParams, numImages)
    If perPixelX is True, then the values of x are distinct for each pixel, and the shape
    of x is
        (numParams, numImages, numRows, numCols)

    The equation being fitted is
        y = c0 * x0 + c1 * x1 + ..... + cn * xn
    where n = (numParams-1)
          c = GslRegressionResults.coeffs

    The method parameter selects which method is used for selecting weights in the
    iterative re-fitting procedure. The options are those supplied by the gsl routine, and
    constants are given in this module for these options, as GSL_METHOD_*.

    The nullVal, if given, will be removed from the data for that pixel before fitting.

    The return value is an instance of the GslRegressionResults class.

    """
    # Some basic error checking on the shape of the arrays
    if len(y.shape) != 3:
        raise RegressionError("Y variable has shape %s. It should be 3-d" % str(y.shape))
    if perPixelX and (len(x.shape) != 4):
        raise RegressionError("X variable has shape %s, but perPixelX is True. It should be 4-d" % str(x.shape))
    elif (not perPixelX) and (len(x.shape) != 2):
        raise RegressionError("X variable has shape %s, but perPixelX is False. It should be 2-d" % str(y.shape))

    # Don't assume Python's boolean equates to C's int
    perPixelX_asInt = 1 if perPixelX else 0

    # If not using perPixelX, then we need to at least make the number of dimensions match.
    # The row and col dimensions will both be 1
    if not perPixelX:
        x = numpy.ascontiguousarray(
            x[..., None, None],
            dtype=numpy.double)

    # If no nullVal given, then make one which does not appear in the data. This is
    # a bit inefficient, but mostly won't happen, as we ought to be giving a null val
    if nullVal is None:
        nullVal = y.max() + 1

    (coeffs, adj_Rsqrd, numIter, rmse) = robreg.wrap_gsl_multifit_robust_func(x, y, method, perPixelX_asInt, nullVal)

    # Assemble an object of the various pieces of output
    regObj = GslRegressionResults()
    regObj.coeffs = coeffs
    regObj.adj_Rsqrd = adj_Rsqrd
    regObj.numIter = numIter
    regObj.rmse = rmse

    return regObj

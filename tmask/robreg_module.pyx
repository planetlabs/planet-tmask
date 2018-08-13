# cimport the Cython declarations for numpy
cimport numpy as np
import numpy as np

# if you want to use the Numpy-C-API from Cython
# (not strictly necessary for this example, but good practice)
np.import_array()

# cdefine the signature of our c function
cdef extern from "robreg.h":
    void wrap_gsl_multifit_robust(
            double *x,
            double *y,
            double *c,
            double *adj_Rsqrd,
            int *numIter,
            double *rmse,
            int method,
            int perPixelX,
            int numRows,
            int numCols,
            int numImages,
            int numParams,
            int numRowsX,
            int numColsX,
            double nullVal)

# input: x, y, method, perPixelX_asInt, nullVal
# output: (c, adj_Rsqrd, numIter, rmse)

def wrap_gsl_multifit_robust_func(
        np.ndarray[double, ndim=4, mode="c"] x not None,
        np.ndarray[double, ndim=3, mode="c"] y not None,
        int method,
        int perPixelX,
        double nullVal
):
    cdef numParams = x.shape[0];
    cdef numImages = x.shape[1];
    cdef numRows = y.shape[1];
    cdef numCols = y.shape[2];
    cdef numRowsX = x.shape[2];
    cdef numColsX = x.shape[3];

    cdef np.ndarray[double, ndim=3, mode="c"] c = np.zeros([numParams, numRows, numCols], dtype=np.double);
    cdef np.ndarray[int, ndim=2, mode="c"] numIter = np.zeros([numRows, numCols], dtype=np.int32);
    cdef np.ndarray[double, ndim=2, mode="c"] rmse = np.zeros([numRows, numCols], dtype=np.double);
    cdef np.ndarray[double, ndim=2, mode="c"] adj_Rsqrd = np.zeros([numRows, numCols], dtype=np.double);

    wrap_gsl_multifit_robust(
        <double*> np.PyArray_DATA(x),
        <double*> np.PyArray_DATA(y),
        <double*> np.PyArray_DATA(c),
        <double*> np.PyArray_DATA(adj_Rsqrd),
        <int*> np.PyArray_DATA(numIter),
        <double*> np.PyArray_DATA(rmse),
        method,
        perPixelX,
        numRows,
        numCols,
        numImages,
        numParams,
        numRowsX,
        numColsX,
        nullVal
    )
    return c, adj_Rsqrd, numIter, rmse
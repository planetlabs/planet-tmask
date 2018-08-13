# Cloud and Cloud Shadow detection for multitemporal PlanetScope and RapidEye Data

## Idea

The general idea is to wrap the [gsl_multifit_robust](https://www.gnu.org/software/gsl/doc/html/lls.html#robust-linear-regression) regression method using
`python3` to allow us to do `per-pixel time series analysis`. The original paper
(https://www.sciencedirect.com/science/article/pii/S0034425714002259,
https://www.sciencedirect.com/science/article/pii/S0034425714002259) uses
three Landsat TOAR bands, so the hypothesis is that the same can be achieved using
PlanetScope (PS) and RapidEye (RE) data. Some aspects of the algorithm cannot be implemented though
as no SWIR band is available.

The data is accessed via the [Planet API](https://www.planet.com/docs/api-quickstart-examples/) which allows us to work on just the
AOIs that we are interested in, without excessive downloads or pre-processing.

For running the code we use [Docker](https://docs.docker.com/develop/).
To have the API_KEY in the docker environment just create a `.env` file
in the project's root dir with content similar to example below.

```
export PLANET_API_KEY=8495833b993f9c6f04cad87491bd7f61
```
It will be used automatically when loading /bin/bash.

You can find your key at https://www.planet.com/account/#/

## Installation

All dependencies and the code run in docker using this command:

```
./launch_docker.sh
```

This will do several things:

1. builds the image based on the Dockerfile
2. runs an interactive container
3. executes installation tests
4. installs required python modules
5. builds the Cython script
6. launches a shell and waits for more commands from the user
7. makes a clean on exit
8. stops the running docker container.

If you see: `"Ready for new commands"` all went well and you can proceed.

## Optional step before pre-processing

Prior to pre-pocessing, `check_time_series_availability.py` in data_prep
folder creates a shapefile with a world raster of points where PS and RE data
(analytic orthotiles) are available for at leat 3 years. This can help to find
areas that have sufficient data for time series analysis.

The creation of a dense grid is rather time-intensive so I used so far a sample of
all available UTM grid tiles. The shapefiles includes the number of available data
sets per year for a certain sampling point. Example call:

```
python3 data_prep/check_time_series_availability.py --density 200 --file_name data_grid_200
```

# Data preparation

Based on the information found at https://www.planet.com/docs/api-quickstart-examples/
scripts are provided in order to access data for small AOIs using the Planet API.

The necessary preprocessing steps are run as follows:

```
python3 data_prep.py --lat <latitude> --lon <longitude> [--bufferval <box size>] [--cloud_cover <percentage>]
```

It creates lists of all PS and RE Orthotiles for an AOI (provided by its
center coordinate and an optional buffer value) and activates the assets.
It then downloads the data covering the AOI and resamples RapidEye data to the
same resolution as the PS data. Finally it creates a list of the files to be
used as input for the TMASK algorithm.


# Running the TMASK algorithm

The TMASK model can be run on the generated files with:

```
python3 tmask/tmask_model.py [--use-udm]
```

when using `--use-udm` pixels marked as clouds by the supplied UDM are excluded from the
training phase. This is not recommended for areas with major land cover changes (e.g. 
deforestation). Results are stored in `data/coeffs`.

Then the actual cloud and cloud shadow masks can be created via:

```
python3 tmask/create_cloud_masks.py [--dynamic-threshold]
```

Default behaviour is to use thresholds based on the original TMASK paper, when using
`--dynamic-threshold` RMSE is used instead, but applied to all four bands.

The resulting cloud masks can be found in the `data/results` folder.

The cloud masks are encoded as follows:

0: clean pixel

1: cloud shadow

2: cloud

## Repository content

This repository consists of four folders, that you will also encounter inside
the docker container:

* `tmask`: the cloud detection code
* `data_prep`: data preparation scripts using the Planet API
* `tools`: modules with logging and some utility functions
* `data`: contains the images, the intermediary files and plots
* `installation_tests`: test for gsl installation



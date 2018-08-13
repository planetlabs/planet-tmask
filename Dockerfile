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

FROM ubuntu:16.04
RUN \
apt-get update && \
apt-get -y upgrade && \
apt-get install -y software-properties-common && \
add-apt-repository -y ppa:ubuntugis/ubuntugis-unstable && \
apt-get update && \
apt-get -y upgrade && \
apt-get install -y gsl-bin libgsl-dev libgsl-dbg gsl-doc-info \
    python3.5 python3-pip python3-requests curl vim devscripts build-essential libncurses5 \
    git debhelper libgeos-dev gdal-bin libgdal-dev python3-gdal libspatialindex-dev \
    python3-numpy python3-scipy python3-nose python3-pandas python3-retrying cython3 ipython3 && \
apt-get -y autoremove && \
apt-get -y clean

ENV USER planet

RUN useradd -ms /bin/bash $USER

# Copy the current directory contents into the container at /app
#ADD .  /home/$USER

#RUN chown -R $USER.$USER /home/$USER
USER $USER

# Set the working directory to /app
WORKDIR /home/$USER

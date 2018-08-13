#!/bin/bash

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

USER_HOME="/home/planet"
IMAGE_NAME="planet/tmask"

IMAGE_ID=$(docker images -f "reference=$IMAGE_NAME" -q)

if [ -d .local ]; then rm -Rf .local; fi

if [ -z "$IMAGE_ID" ]
then
    echo "Be patient while image is built, it will take aprox. 10 minutes"
    IMAGE_ID=$(docker build --no-cache -t ${IMAGE_NAME} -q `pwd`)
fi

echo "Starting a container based on the image ID: $IMAGE_ID"
CONTAINER_ID=$(docker run --rm -t -d -v `pwd`:$USER_HOME $IMAGE_ID)
echo "Running container ID is: $CONTAINER_ID"
echo "Checking gsl installation"
docker exec -it $CONTAINER_ID make test_gsl
echo "Preparing environment"
docker exec -it $CONTAINER_ID make build
echo "Ready for new commands"
docker exec -it $CONTAINER_ID /bin/bash
echo "Cleaning and closing"
docker exec -it $CONTAINER_ID make clean
docker stop $CONTAINER_ID
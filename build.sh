#!/bin/bash

if [ ! -d "./federated-grandforest-R" ]; then
    git clone https://github.com/felicious-fe/federated-grandforest-R

    if [ $? -eq 0 ]
    then
	echo "Successfully cloned the federated-grandforest-R repository from GitHub."
    else
	echo "Script failed! Clould not clone the federated-grandforest-R repository from GitHub. Exiting..." >&2
	exit 1
    fi
fi

echo "Building docker image..."
docker build . --tag featurecloud.ai/fc_grandforest



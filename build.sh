#!/bin/bash

if [ ! -d "./grandforest-federalizable" ]; then
    git clone git@gitlab.com:felicious-fe/grandforest-federalizable

    if [ $? -eq 0 ]
    then
	echo "Successfully cloned the grandforest repository."
    else
	echo "Script failed! Clould not clone the grandforest federalizable repository. Exiting..." >&2
	exit 1
    fi
fi

echo "Building docker image..."
docker build . --tag fc_grandforest


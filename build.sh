#!/bin/bash

echo "Building docker image..."
docker build . --tag fc_cox_model_flask

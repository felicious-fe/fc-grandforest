import numpy as np
from flask import current_app

from redis_util import redis_set, redis_get

from fc_app.GrandForestR import GrandForestR


def compute_grandforest_model(local_data, network):
    """
    Compute the local model and number of samples
    :param local_data: Local expression data
    :param network: Interaction Network (should be the same over the whole experiment)
    :return: The local model and number of samples
    """
    grandforest = GrandForestR(network)
    grandforest.fit(local_data)
    local_model = grandforest.forest
    nr_samples = len(local_data)
    current_app.logger.info(
        f'[API] Local computation of client {redis_get("id")}: {local_model} with {nr_samples} samples')

    return local_model, nr_samples


def aggregate_grandforest_models(global_data):
    """
    Aggregate the local models to a global model
    :param global_data: List of local models and local number of samples
    :return: Global model
    """
    grandforest = GrandForestR()
    model = global_data[0][0]
    for i in range(1, len(global_data)):
        model = grandforest.sum_forest(model, global_data[i][0])

    return model


def global_aggregation():
    """
    Aggregate the local models to a global model
    :return: None
    """
    current_app.logger.info('[API] Calculate Global Aggregation')
    global_data = redis_get('global_data')

    global_result = aggregate_grandforest_models(global_data)

    current_app.logger.info(f'[API] Global Result: {global_result}')
    redis_set('global_result', str(global_result))


def local_computation():
    """
    Compute the local model.
    :return: The local model/result and the number of samples
    """
    current_app.logger.info('[API] Calculate Local Results')

    local_result, nr_samples = compute_grandforest_model(redis_get('expression_data'), redis_get('interaction_network'))

    return local_result, nr_samples

import numpy as np
from flask import current_app

from redis_util import redis_set, redis_get


def compute_mean(local_data):
    """
    Compute the local mean and number of samples
    :param local_data: Local data
    :return: The local mean and number of samples
    """
    local_mean = np.mean(local_data)
    nr_samples = len(local_data)
    current_app.logger.info(
        f'[API] Local computation of client {redis_get("id")}: {local_mean} with {nr_samples} samples')

    return local_mean, nr_samples


def aggregate_means(global_data):
    """
    Aggregate the local means to a global mean
    :param global_data: List of local means and local number of samples
    :return: Global mean
    """
    mean = 0
    number_samples = 1
    sum = 0
    counter = 0
    for i in global_data:
        sum += i[mean] * i[number_samples]
        counter += i[number_samples]
    global_mean = sum / counter

    return global_mean


def global_aggregation():
    """
    Aggregate the local models to a global model
    :return: None
    """
    current_app.logger.info('[API] Calculate Global Aggregation')
    global_data = redis_get('global_data')

    global_result = aggregate_means(global_data)

    current_app.logger.info(f'[API] Global Result: {global_result}')
    redis_set('global_result', str(global_result))


def local_computation():
    """
    Compute the local model.
    :return: The local model/result and the number of samples
    """
    current_app.logger.info('[API] Calculate Local Results')
    data = redis_get('data')

    local_result, nr_samples = compute_mean(data)

    return local_result, nr_samples

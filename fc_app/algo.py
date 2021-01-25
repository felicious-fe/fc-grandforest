from flask import current_app
from redis_util import redis_set, redis_get
import numpy as np


def compute_local(local_data):
    local_result = np.mean(local_data)
    nr_samples = len(local_data)
    current_app.logger.info(f'[API] Local mean of client {redis_get("id")}: {local_result} with {nr_samples} samples')

    return local_result, nr_samples


def compute_aggregation(global_data: []):
    mean = 0
    number_samples = 1
    sum = 0
    counter = 0
    for i in global_data:
        sum += i[mean] * i[number_samples]
        counter += i[number_samples]
    global_result = sum / counter

    return global_result


# This function does usually not need to be changed. Please change compute_aggregation instead
def global_aggregation():
    current_app.logger.info('[API] Calculate Global Aggregation')
    global_data = redis_get('global_data')

    global_result = compute_aggregation(global_data)

    current_app.logger.info(f'[API] Global Result: {global_result}')
    redis_set('global_result', str(global_result))


# This function does usually not need to be changed. Please change compute_local instead
def local_computation():
    current_app.logger.info('[API] Calculate Local Results')
    data = redis_get('data')

    local_result, nr_samples = compute_local(data)

    return local_result, nr_samples

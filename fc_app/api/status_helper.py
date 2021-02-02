from flask import current_app

from fc_app.algo import local_computation, global_aggregation
from fc_app.api.data_helper import has_client_data_arrived, have_clients_finished
from fc_app.io import read_config, read_input, write_results
from redis_util import redis_set, redis_get, set_step


def init():
    """
    Read in the config and input files
    :return: None
    """
    read_config()
    expression_data = read_input('expression_data_filename')
    interaction_network = read_input('interaction_network_filename')
    current_app.logger.info('[STATUS] compute local results')
    redis_set('expression_data', expression_data)
    redis_set('interaction_network', interaction_network)


def local_calculation():
    """
    Calculate the local model
    :return: None
    """
    current_app.logger.info('[STEP] local_calculation')
    local_result, nr_samples = local_computation()
    if redis_get('is_coordinator'):
        # if this is the coordinator, directly add the local result and number of samples to the global_data list
        global_data = redis_get('global_data')
        global_data.append([local_result, nr_samples])
        redis_set('global_data', global_data)
        current_app.logger.info('[STEP] : waiting_for_clients')
    else:
        # if this is a client, set the local result and number of samples to local_data and set available to true
        redis_set('local_data', [local_result, nr_samples])
        current_app.logger.info('[STEP] waiting_for_coordinator')
        redis_set('available', True)


def waiting():
    """
    As a controller, wait until the data of all clients has arrived.
    As a client, wait for the coordinator to finish the global aggregation.
    :return: None
    """
    if redis_get('is_coordinator'):
        current_app.logger.info('[STATUS] Coordinator checks if data of all clients has arrived')
        # check if all clients have sent their data already
        has_client_data_arrived()
    else:
        # the clients wait for the coordinator to finish
        current_app.logger.info('[STATUS] Client waiting for coordinator to finish')


def global_calculation():
    """
    As a controller, aggregate the local models to a global model
    :return: None
    """
    global_aggregation()


def broadcast_results():
    """
    As a controller, broadcast the global model to all other clients
    :return: None
    """
    current_app.logger.info('[STATUS] Share global results with clients')
    redis_set('available', True)


def write_output():
    """
    Write the global results to the output directory.
    :return: None
    """
    write_results(redis_get('global_result'))
    current_app.logger.info('[STATUS] Finalize client')
    if redis_get('is_coordinator'):
        # The coordinator is already finished now
        redis_set('finished', [True])


def finalize():
    """
    As a controller, wait for all clients to be finished.
    As a client, tell the controller that the results were written to the output directory.
    :return: None
    """
    if redis_get('is_coordinator'):
        # The coordinator waits until all clients have finished
        if have_clients_finished():
            current_app.logger.info('[STATUS] All clients have finished. Finalize coordinator.')
            set_step('finished')
        else:
            current_app.logger.info('[STATUS] Wait for clients to be finished.')
    else:
        # The clients set available true to signal the coordinator that they have written the results.
        redis_set('available', True)

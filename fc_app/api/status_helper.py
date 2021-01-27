from flask import current_app

from fc_app.algo import local_computation, global_aggregation
from fc_app.api.data_helper import has_client_data_arrived, have_clients_finished
from fc_app.io import read_config, read_input, write_results
from redis_util import redis_set, redis_get, set_step


def start():
    current_app.logger.info('[STEP] start')
    current_app.logger.info('[API] Federated Mean App')


def init():
    read_config()
    files = read_input()
    current_app.logger.info('[API] Data: ' + str(files) + ' found in ' + str(len(files)) + ' files.')
    current_app.logger.info('[API] compute local results of ' + str(files))
    redis_set('data', files)


def local_calculation():
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
    if redis_get('is_coordinator'):
        current_app.logger.info('[API] Coordinator checks if data of all clients has arrived')
        # check if all clients have sent their data already
        has_client_data_arrived()
    else:
        # the clients wait for the coordinator to finish
        current_app.logger.info('[API] Client waiting for coordinator to finish')


def global_calculation():
    global_aggregation()


def broadcast_results():
    current_app.logger.info('[API] Share global results with clients')
    redis_set('available', True)


def write_output():
    write_results(redis_get('global_result'))
    current_app.logger.info('[API] Finalize client')
    if redis_get('is_coordinator'):
        # The coordinator is already finished now
        redis_set('finished', [True])


def finalize():
    current_app.logger.info("[API] Finalize")
    if redis_get('is_coordinator'):
        # The coordinator waits until all clients have finished
        if have_clients_finished():
            current_app.logger.info('[API] Finalize coordinator.')
            set_step('finished')
        else:
            current_app.logger.info('[API] Not all clients have finished yet.')
    else:
        # The clients set available true to signal the coordinator that they have written the results.
        redis_set('available', True)

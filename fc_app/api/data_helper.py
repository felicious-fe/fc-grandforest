from flask import current_app

from redis_util import redis_set, redis_get, set_step, get_step


def receive_client_data(client_data):
    """
    As a controller, receive client data from request and process it.
    :param client_data: Data that has been received from the client
    :return: None
    """
    # Get data from clients (as coordinator)
    current_app.logger.info('[DATA] Receive data from client')
    if get_step() != 'finalize':
        # Get local result of the clients
        global_data = redis_get('global_data')
        global_data.append(client_data['data'])
        redis_set('global_data', global_data)
        current_app.logger.info('[DATA] ' + str(global_data))
    else:
        # Get Finished flags of the clients
        finish = redis_get('finished')
        finish.append(client_data['finished'])
        redis_set('finished', finish)


def receive_coordinator_data(coordinator_data):
    """
    As a client, receive data from the coordinator and process it
    :param coordinator_data: Data received from the coordinator
    :return: None
    """
    # Get global result from coordinator (as client)
    current_app.logger.info('[DATA] Receive data from coordinator')
    redis_set('global_result', coordinator_data['global_result'])
    current_app.logger.info('[DATA] ' + str(redis_get('global_result')))
    set_step('write_output')


def broadcast_data_to_clients():
    """
    As a coordinator, after aggregating the local models to a global one, broadcast the global model to the clients
    :return: Global result
    """
    # broadcast data to clients (as coordinator)
    current_app.logger.info('[DATA] broadcast data from coordinator to clients')
    redis_set('available', False)
    global_result = redis_get('global_result')

    return global_result


def send_data_to_coordinator():
    """
    As a client, send local data to the coordinator. ATTENTION: Only send non-sensitive data here
    :return: local data
    """
    # send data to coordinator (as client)
    current_app.logger.info('[DATA] send data to coordinator')
    redis_set('available', False)
    local_data = redis_get('local_data')

    return local_data


def send_finished_flag_to_coordinator():
    """
    As a client, send the finished flag to the coordinator to show that the site is finished.
    :return: True
    """
    # Send finish flag to the coordinator
    current_app.logger.info('[DATA] send finish flag to coordinator')
    redis_set('available', False)
    set_step('finished')

    return True


def has_client_data_arrived():
    """
    As a coordinator, check if the local data of all clients has arrived to start the global calculation
    :return: None
    """
    global_data = redis_get('global_data')
    nr_clients = redis_get('nr_clients')
    current_app.logger.info('[DATA] ' + str(len(global_data)) + "/" + str(nr_clients) + " data arrived.")
    if len(global_data) == nr_clients:
        current_app.logger.info('[DATA] Data of all clients has arrived')
        set_step('global_calculation')
    else:
        pass


def have_clients_finished():
    """
    As a coordinator, check if all clients have finished yet.
    :return: True if clients have finished, else False
    """
    finish = redis_get('finished')
    nr_clients = redis_get('nr_clients')
    if len(finish) == nr_clients:
        current_app.logger.info('[DATA] All clients have finished.')
        return True
    else:
        return False

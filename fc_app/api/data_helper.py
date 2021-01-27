from flask import current_app

from redis_util import redis_set, redis_get, set_step, get_step


def receive_client_data(client_data):
    # Get data from clients (as coordinator)
    current_app.logger.info('[API] Receive data from client')
    if get_step() != 'finalize':
        # Get local result of the clients
        global_data = redis_get('global_data')
        global_data.append(client_data['data'])
        redis_set('global_data', global_data)
        current_app.logger.info('[API] ' + str(global_data))
    else:
        # Get Finished flags of the clients
        finish = redis_get('finished')
        finish.append(client_data['finished'])
        redis_set('finished', finish)


def receive_coordinator_data(coordinator_data):
    # Get global result from coordinator (as client)
    current_app.logger.info('[API] Receive data from coordinator')
    redis_set('global_result', coordinator_data['global_result'])
    current_app.logger.info('[API] ' + str(redis_get('global_result')))
    set_step('write_output')


def broadcast_data_to_clients():
    # broadcast data to clients (as coordinator)
    current_app.logger.info('[API] broadcast data from coordinator to clients')
    redis_set('available', False)
    global_result = redis_get('global_result')

    return global_result


def send_data_to_coordinator():
    # send data to coordinator (as client)
    current_app.logger.info('[API] send data to coordinator')
    redis_set('available', False)
    local_data = redis_get('local_data')
    current_app.logger.info(local_data)

    return local_data


def send_finished_flag_to_coordinator():
    # Send finish flag to the coordinator
    current_app.logger.info('[API] send finish flag to coordinator')
    redis_set('available', False)
    set_step('finished')

    return True


def has_client_data_arrived():
    current_app.logger.info('[API] Coordinator checks if data of all clients has arrived')
    global_data = redis_get('global_data')
    nr_clients = redis_get('nr_clients')
    current_app.logger.info('[API] ' + str(len(global_data)) + "/" + str(nr_clients) + " clients have sent their data.")
    if len(global_data) == nr_clients:
        current_app.logger.info('[API] Data of all clients has arrived')
        set_step('global_calculation')
    else:
        current_app.logger.info('[API] Data of at least one client is still missing')


def have_clients_finished():
    current_app.logger.info('[API] Coordinator checks if all clients have finished')
    finish = redis_get('finished')
    nr_clients = redis_get('nr_clients')
    current_app.logger.info('[API] ' + str(len(finish)) + "/" + str(nr_clients) + " clients have finished already.")
    if len(finish) == nr_clients:
        current_app.logger.info('[API] All clients have finished.')
        return True
    else:
        current_app.logger.info('[API] At least one client did not finish yet.')
        return False

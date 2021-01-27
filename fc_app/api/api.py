import queue as q

import redis
import rq
from flask import Blueprint, jsonify, request, current_app

from fc_app.api.data_helper import receive_client_data, receive_coordinator_data, broadcast_data_to_clients, \
    send_data_to_coordinator, send_finished_flag_to_coordinator
from fc_app.api.status_helper import init, local_calculation, waiting, global_calculation, broadcast_results, \
    write_output, finalize
from redis_util import redis_set, redis_get, get_step, set_step

pool = redis.BlockingConnectionPool(host='localhost', port=6379, db=0, queue_class=q.Queue)
r = redis.Redis(connection_pool=pool)

# setting 'available' to False --> no data will be send around.
# Change it to True later to send data from the coordinator to the clients or vice versa.
redis_set('available', False)

# The various steps of the app. This list is not really used and only an overview.
STEPS = ['start', 'init', 'local_calculation', 'waiting', 'global_calculation', 'broadcast_results', 'write_output',
         'finalize', 'finished']

# Initializes the app with the first step
set_step('start')
# Initialize the local and global data
redis_set('local_data', None)
redis_set('global_data', [])

api_bp = Blueprint('api', __name__)
tasks = rq.Queue('fc_tasks', connection=r)


@api_bp.route('/status', methods=['GET'])
def status():
    """
    GET request to /status, if True is returned a GET data request will be send
    :return: JSON with key 'available' and value True or False and 'finished' value True or False
    """
    available = redis_get('available')
    current_app.logger.info('[API] /status GET request ' + str(available) + ' - [STEP]: ' + str(get_step()))

    if get_step() == 'start':
        current_app.logger.info('[STEP] start')
        current_app.logger.info('[API] Federated Mean App')
    elif get_step() == 'init':
        init()
        set_step("local_calculation")
    elif get_step() == 'local_calculation':
        local_calculation()
        set_step('waiting')
    elif get_step() == 'waiting':
        current_app.logger.info('[STEP] waiting')
        waiting()
    elif get_step() == 'global_calculation':
        # as soon as all data has arrived the global calculation starts
        current_app.logger.info('[STEP] global_calculation')
        global_calculation()
        set_step("broadcast_results")
    elif get_step() == 'broadcast_results':
        # as soon as the global result was calculated, the result is broadcasted to the clients
        current_app.logger.info('[STEP] broadcast_results')
        broadcast_results()
        set_step('write_output')
    elif get_step() == 'write_output':
        # The global result is written to the output directory
        current_app.logger.info('[STEP] write_output')
        write_output()
        set_step("finalize")
    elif get_step() == 'finalize':
        current_app.logger.info('[STEP] finalize')
        finalize()
    elif get_step() == 'finished':
        # All clients and the coordinator set available to False and finished to True and the computation is done
        current_app.logger.info('[STEP] finished')
        return jsonify({'available': False, 'finished': True})

    return jsonify({'available': True if available else False, 'finished': False})


@api_bp.route('/data', methods=['GET', 'POST'])
def data():
    """
    GET request to /data sends data to coordinator or clients
    POST request to /data pulls data from coordinator or clients
    :return: GET request: JSON with key 'data' and value data
             POST request: JSON True
    """
    if request.method == 'POST':
        current_app.logger.info('[API] /data POST request')
        if redis_get('is_coordinator'):
            receive_client_data(request.get_json(True))
        else:
            receive_coordinator_data(request.get_json(True))
        return jsonify(True)

    elif request.method == 'GET':
        current_app.logger.info('[API] /data GET request')
        if redis_get('is_coordinator'):
            global_result = broadcast_data_to_clients()
            return jsonify({'global_result': global_result})
        else:
            if get_step() != 'finalize':
                local_data = send_data_to_coordinator()
                return jsonify({'data': local_data})
            else:
                local_finished_flag = send_finished_flag_to_coordinator()
                return jsonify({'finished': local_finished_flag})

    else:
        current_app.logger.info('[API] Wrong request type, only GET and POST allowed')
        return jsonify(True)


@api_bp.route('/setup', methods=['POST'])
def setup():
    """
    set setup params
    - id is the id of the client
    - coordinator is True if the client is the coordinator,
    - in global_data the data from all clients (including the coordinator) will be aggregated
    - clients is a list of all ids from all clients
    - nr_clients is the number of clients involved in the app
    :return: JSON True
    """
    current_app.logger.info('[STEP] setup')
    current_app.logger.info('[API] Retrieve Setup Parameters')
    setup_params = request.get_json()
    redis_set('id', setup_params['id'])
    is_coordinator = setup_params['master']
    redis_set('is_coordinator', is_coordinator)
    if is_coordinator:
        redis_set('global_data', [])
        redis_set('finished', [])
        redis_set('clients', setup_params['clients'])
        redis_set('nr_clients', len(setup_params['clients']))
    set_step('init')
    return jsonify(True)

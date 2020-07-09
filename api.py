import pickle
import rq
from flask import Blueprint, jsonify, request

from redis import r, redis_get, redis_set

r.set('available', pickle.dumps(False))
r.set('step', pickle.dumps('start'))
r.set('step_id', pickle.dumps(0))
r.set('local_data', pickle.dumps(True))
r.set('global_data', pickle.dumps(True))

api_bp = Blueprint('api', __name__)
tasks = rq.Queue('fc_tasks', connection=r)


@api_bp.route('/status', methods=['GET'])
def status():
    """
    GET request to /status, if True is returned a GET data request will be send
    :return: JSON with key 'available' and value True or False
    """
    available = redis_get('available')
    return jsonify({'available': True if available else False})


@api_bp.route('/data', methods=['GET', 'POST'])
def data():
    """
    GET request to /data sends data to global server
    POST request to /data pulls data from global server
    :return: GET request: JSON with key 'data' and value data
             POST request: JSON True
    """

    # Data will be pulled from flask object request in json format
    if request.method == 'POST':
        data_received = request.get_json(True)['data']

        global_data = redis_get('global_data').append(data_received)
        redis_set('global_data', global_data)

        nr_clients = redis_get('nr_clients')

        if len(global_data) == nr_clients:
            mean = 0
            number_samples = 1
            sum = 0
            counter = 0

            for i in global_data:
                sum += i[mean] * i[number_samples]
                counter += i[number_samples]

            result = str(sum / counter)
            redis_set('result', result)

        return jsonify(True)

    # Data will be sent to the master
    elif request.method == 'GET':
        redis_set('available', False)
        local_data = redis_get('local_data')
        return jsonify({'data': local_data})


@api_bp.route('/setup', methods=['POST'])
def setup():
    """
    set setup params, id is the id of the client, master is True if the client is the master,
    in global_data the data from all clients (including the master) will be aggregated,
    clients is a list of all ids from all clients, nr_clients is the number of clients involved in the app
    :return: JSON True
    """
    setup_params = request.get_json()
    redis_set('id', setup_params['id'])
    master = setup_params['master']
    redis_set('master', master)
    if master:
        redis_set('global_data', [])
    redis_set('clients', setup_params['clients'])
    redis_set('nr_clients', len(setup_params['clients']))
    redis_set('step', 'start')
    return jsonify(True)

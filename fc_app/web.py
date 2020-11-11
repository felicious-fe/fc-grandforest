import redis
import rq
from flask import Blueprint, current_app
from redis_util import redis_get, get_step


r = redis.Redis(host='localhost', port=6379, db=0)
tasks = rq.Queue('fc_tasks', connection=r)
web_bp = Blueprint('web', __name__)
STEPS = ['start', 'setup', 'local_calculation', 'waiting', 'global_calculation', 'broadcast_results', 'write_results',
         'finalize', 'finished']


@web_bp.route('/', methods=['GET'])
def root():
    """
    decides which HTML page content will be shown to the user
    :return: HTML content
    """
    step = get_step()
    if step == 'start':
        current_app.logger.info('[WEB] Initializing')
        return 'Initializing'
    elif step == 'setup':
        current_app.logger.info('[WEB] Setup')
        return 'Setup'
    elif step == 'local_calculation':
        current_app.logger.info('[WEB] Calculating local mean')
        return 'Calculating local mean...'
    elif step == 'waiting':
        if redis_get('is_coordinator'):
            current_app.logger.info('[WEB] Waiting for client data...')
            return 'Waiting fo client data...'
        else:
            current_app.logger.info('[WEB] Send local results to coordinator')
            return 'Send results to coordinator'
    elif step == 'global_calculation':
        current_app.logger.info('[WEB] Aggregate local results and compute global mean')
        return 'Aggregate local results and compute global mean...'
    elif step == 'broadcast_results':
        if not redis_get('coordinator'):
            current_app.logger.info('[WEB] Receiving global mean from coordinator')
            return 'Receiving global mean from coordinator...'
        else:
            current_app.logger.info('[WEB] Broadcasting global mean to other clients')
            return 'Broadcasting global mean to other clients...'
    elif step == 'write_results':
        current_app.logger.info('[WEB] Write Results')
        return 'Write results to output file....'
    elif step == 'finished':
        current_app.logger.info('[WEB] Finished')
        return 'Computation finished...'
    else:
        return 'Something went wrong.'


@web_bp.route('/params', methods=['GET'])
def params():
    """
    :return: current parameter values as a HTML page
    """
    is_coordinator = redis_get('is_coordinator')
    step = redis_get('step')
    local_data = redis_get('local_data')
    global_data = redis_get('global_data')
    data = redis_get('data')
    available = redis_get('available')
    return f"""
        is_coordinator: {is_coordinator}
        step: {step}
        local data: {local_data}
        global data: {global_data}
        data: {data}
        available: {available}
        """

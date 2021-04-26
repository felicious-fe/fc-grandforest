import os

import bottle

from app import config

from .logic import logic
from .io import read_config_from_frontend

web_server = bottle.Bottle()
bottle.BaseTemplate.defaults['get_url'] = web_server.get_url  # reference to function
bottle.TEMPLATE_PATH.insert(0, '/home/niedermaierfelix/workspace/fc_grandforest/app/templates')
bottle.TEMPLATE_PATH.insert(0, '/app/app/templates')


# CAREFUL: Do NOT perform any computation-related tasks inside these methods, nor inside functions called from them!
# Otherwise your app does not respond to calls made by the FeatureCloud system quickly enough
# Use the threaded loop in the app_flow function inside the file logic.py instead

# Possible Progress Strings:
#   'not started yet'
#   'initializing'
#   'parsing config file'
#   'parsing config frontend'
#   'sending config'
#   'gathering config'
#   'computing'
#   'gathering models'
#   'gathering global model'
#   'writing results'
#   'finishing'

status_ui = {'not started yet': 'The workflow has not been started yet. Waiting for other clients...',
		'initializing': 'GrandForest initializing...',
		'parsing config file': 'Parsing the config file...',
		'parsing config frontend': 'Parsing the FrontEnd config...',
		'sending config': 'Reading Interaction Network file(s) and sending configuration to clients...',
		'gathering config': 'Gathering configuration from the coordinator...',
		'computing': 'Computing the model...',
		'gathering models': 'Gathering models from all clients...',
		'gathering global model': 'Gathering model from coordinator...',
		'writing results': 'Writing results...',
		'finishing': 'Finishing the workflow...'}

@web_server.route('/')
def index():
	print(f'[WEB] GET /', flush=True)
	if logic.progress == "getting config frontend":
		return bottle.static_file("input.html", root='/app/app/templates')
	else:
		return bottle.template('loading', status=status_ui[logic.progress])


@web_server.post('/')
def process_config_form():
	print(f'[WEB] POST /', flush=True)
	result = bottle.request.forms.decode()

	logic.progress = 'parsing config frontend'
	config.add_option('input_form', result)

	return bottle.static_file("input_accepted.html", root='/app/app/templates')

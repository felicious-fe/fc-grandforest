from flask import current_app

from redis_util import redis_set, redis_get

import os
import sys

from fc_app.RSubprocess import RSubprocess


def compute_grandforest_model(expression_data, interaction_network):
	"""
	Compute the local model and number of samples
	:param expression_data: Local expression data
	:param interaction_network: Interaction Network
	:return: The local model and number of samples
	"""

	open('/app/temp/expression_data.RData', 'wb').write(expression_data)
	open('/app/temp/interaction_network.RData', 'wb').write(interaction_network)

	if redis_get('grandforest_method') == 'supervised':
		command = ["/app/fc_app/R/grandforest.train_model.supervised.R",
				   '/app/temp/expression_data.RData',
				   '/app/temp/interaction_network.RData',
				   str(redis_get('number_of_trees')),
				   str(redis_get('expression_data_dependent_variable_name')),
				   '/app/temp/local_model.RData']
	else:
		command = ["/app/fc_app/R/grandforest.train_model.unsupervised.R",
				   '/app/temp/expression_data.RData',
				   '/app/temp/interaction_network.RData',
				   str(redis_get('number_of_trees')),
				   '/app/temp/local_model.RData']

	local_computation_subprocess = RSubprocess(command)
	current_app.logger.info('[ALGO] Starting RSubprocess to calculate local GrandForest model...')
	local_computation_subprocess.start()
	current_app.logger.info('[ALGO] Started RSubprocess to calculate local GrandForest model')
	local_computation_subprocess.join()
	current_app.logger.info('[ALGO] Finished RSubprocess to calculate local GrandForest model')

	os.remove('/app/temp/expression_data.RData')
	os.remove('/app/temp/interaction_network.RData')

	local_model = open('/app/temp/local_model.RData', 'rb').read().hex()
	nr_samples = 0  # TODO
	current_app.logger.info(f'[API] Local computation of client {redis_get("id")}: {sys.getsizeof(local_model)} Bytes with {nr_samples} samples written to local_model.RData')

	return local_model, nr_samples


def aggregate_grandforest_models(global_data):
	"""
	Aggregate the local models to a global model
	:param global_data: List of local models and local number of samples
	:return: global result
	"""

	open('/app/temp/global_model', 'wb').write(bytes.fromhex(global_data[0][0]))
	current_app.logger.info('[ALGO] Starting RSubprocesses to aggregate the GrandForest models...')
	for i in range(1, len(global_data)):
		open('/app/temp/temp_model', 'wb').write(bytes.fromhex(global_data[i][0]))
		command = ["/app/fc_app/R/grandforest.sum_models.R", '/app/temp/global_model', '/app/temp/temp_model', '/app/temp/global_model']
		model_aggregation_subprocess = RSubprocess(command)
		model_aggregation_subprocess.start()
		model_aggregation_subprocess.join()

		os.remove('/app/temp/temp_model')

	current_app.logger.info('[ALGO] Finished RSubprocesses to aggregate the GrandForest models')

	global_result = open('/app/temp/global_model', 'rb').read().hex()
	os.remove('/app/temp/global_model')

	return global_result


def global_aggregation():
	"""
	Aggregate the local models to a global model
	:return: None
	"""
	current_app.logger.info('[API] Calculate Global Aggregation')
	global_data = redis_get('global_data')

	global_model = aggregate_grandforest_models(global_data)

	current_app.logger.info(f'[API] Global Result: {sys.getsizeof(global_model)} Bytes written to global_model.RData')
	redis_set('global_result', global_model)


def local_computation():
	"""
	Compute the local model.
	:return: The local model/result and the number of samples
	"""
	current_app.logger.info('[API] Calculate Local Results')

	local_model, nr_samples = compute_grandforest_model(redis_get('expression_data'), redis_get('interaction_network'))

	return local_model, nr_samples

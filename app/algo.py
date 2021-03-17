import base64
import os
import sys
from uuid import uuid4

from app import config
from app.RSubprocess import RSubprocess
from app.io import write_output


def __compute_local_grandforest_model(expression_data, interaction_network, split):
	"""
	Compute the local model and number of samples
	:param expression_data: Local expression data as binary RData
	:param interaction_network: Interaction Network as binary RData
	:return: The local model as base64 encoded binary RData string and number of samples
	"""
	temp_path = config.get_option('TEMP_DIR') + '/' + str(uuid4())
	os.makedirs(temp_path)

	open(temp_path + '/' + 'expression_data.RData', 'wb').write(base64.decodebytes(expression_data.encode('utf-8')))
	open(config.get_option('TEMP_DIR') + '/' + 'interaction_network.RData', 'wb').write(base64.decodebytes(interaction_network.encode('utf-8')))

	if config.get_option('grandforest_method') == 'supervised':
		command = ["/app/app/R/grandforest.train_model.supervised.R",
				   temp_path + '/' + 'expression_data.RData',
				   config.get_option('TEMP_DIR') + '/' + 'interaction_network.RData',
				   str(config.get_option('number_of_trees')),
				   str(config.get_option('seed')),
				   str(config.get_option('grandforest_treetype')),
				   str(config.get_option('expression_data_dependent_variable_name')),
				   str(config.get_option('expression_data_survival_event')),
				   str(config.get_option('expression_data_survival_time')),
				   temp_path + '/' + 'local_model.RData']
	else:
		command = ["/app/app/R/grandforest.train_model.unsupervised.R",
				   temp_path + '/' + 'expression_data.RData',
				   config.get_option('TEMP_DIR') + '/' + 'interaction_network.RData',
				   str(config.get_option('number_of_trees')),
				   str(config.get_option('seed')),
				   str(config.get_option('grandforest_treetype')),
				   str(config.get_option('expression_data_survival_event')),
				   str(config.get_option('expression_data_survival_time')),
				   temp_path + '/' + 'local_model.RData']

	local_computation_subprocess = RSubprocess(command)
	print('[ALGO] Starting RSubprocess to calculate local GrandForest model...')
	local_computation_subprocess.start()
	print('[ALGO] Started RSubprocess to calculate local GrandForest model')
	local_computation_subprocess.join()
	print('[ALGO] Finished RSubprocess to calculate local GrandForest model')

	# save local model as base64 encoded string
	local_model = base64.b64encode(open(temp_path + '/' + 'local_model.RData', 'rb').read()).decode('utf-8')

	# save amount of lines - 1 (header line) as weighting constant
	with open(split + '/' + config.get_option('expression_data_filename')) as expression_data_file:
		nr_samples = sum(1 for line in expression_data_file) - 1

	print(f'[ALGO] Local computation of client {config.get_option("id")}: {sys.getsizeof(local_model)} Bytes with {nr_samples} samples successful')

	return local_model, nr_samples


def __aggregate_grandforest_models(global_data):
	"""
	Aggregate the local models to a global model
	:param global_data: List of local models and local number of samples
	:return: The global model as base64 encoded binary RData string
	"""
	temp_path = config.get_option('TEMP_DIR') + '/' + str(uuid4())
	os.makedirs(temp_path)

	open(temp_path + '/' + 'forest1.RData', 'wb').write(
		base64.decodebytes(global_data[0].encode('utf-8')))
	print('[ALGO] Starting RSubprocesses to aggregate the GrandForest models...')
	for i in range(1, len(global_data)):
		open(temp_path + '/' + 'forest2.RData', 'wb').write(
			base64.decodebytes(global_data[i].encode('utf-8')))
		command = ["/app/app/R/grandforest.sum_models.R",
				   temp_path + '/' + 'forest1.RData',
				   temp_path + '/' + 'forest2.RData',
				   temp_path + '/' + 'forest1.RData']
		model_aggregation_subprocess = RSubprocess(command)
		model_aggregation_subprocess.start()
		model_aggregation_subprocess.join()

		os.remove(temp_path + '/' + 'forest2.RData')
	print('[ALGO] Finished RSubprocesses to aggregate the GrandForest models')

	global_model = base64.b64encode(open(temp_path + '/' + 'forest1.RData', 'rb').read()).decode('utf-8')
	os.remove(temp_path + '/' + 'forest1.RData')
	print(
		f'[ALGO] Global Aggregation on client {config.get_option("id")}: {sys.getsizeof(global_model)} Bytes successful')

	return global_model


def __predict_with_grandforest_model(global_model, expression_data, split):
	temp_path = config.get_option('TEMP_DIR') + '/' + str(uuid4())
	os.makedirs(temp_path)
	open(temp_path + '/' + 'global_model.RData', 'wb').write(
		base64.decodebytes(global_model.encode('utf-8')))
	open(temp_path + '/' + 'expression_data.RData', 'wb').write(
		base64.decodebytes(expression_data.encode('utf-8')))

	if config.get_option('grandforest_method') == 'supervised':
		command = ["/app/app/R/grandforest.predict.supervised.R",
				   temp_path + '/' + 'global_model.RData',
				   temp_path + '/' + 'expression_data.RData',
				   str(config.get_option('expression_data_dependent_variable_name')),
				   split + '/']
	else:
		command = ["/app/app/R/grandforest.predict.unsupervised.R",
				   temp_path + '/' + 'global_model.RData',
				   temp_path + '/' + 'expression_data.RData',
				   split + '/']

	local_prediction_subprocess = RSubprocess(command)
	print('[ALGO] Starting RSubprocess to predict local expression data with the global GrandForest model...')
	local_prediction_subprocess.start()
	print('[ALGO] Started RSubprocess to predict local expression data with the global GrandForest model')
	local_prediction_subprocess.join()
	print('[ALGO] Finished RSubprocess to predict local expression data with the global GrandForest model')


# Functions exposed to AppLogic

def local_computation(expression_data, interaction_network, split):
	local_model, nr_samples = __compute_local_grandforest_model(expression_data, interaction_network, split)
	return local_model


def global_aggregation(global_data):
	global_model = __aggregate_grandforest_models(global_data)
	return global_model


def local_prediction(local_model, expression_data, split):
	__predict_with_grandforest_model(local_model, expression_data, split)


def write_results(local_model, global_model, split):
	"""
	Write the results to the output directory and delete the TEMP directory.
	:return: None
	"""
	write_output(local_model, split, 'local_model')
	write_output(global_model, split, 'global_model')

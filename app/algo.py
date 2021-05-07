import base64
import os
import sys
import errno
from uuid import uuid4

from app import config
from app.RSubprocess import RSubprocess
from app.io import write_output


def __compute_local_grandforest_model(expression_data, interaction_network, split):
	"""
	Private Method.
	Executes the RScript 'grandforest.train_model.supervised.R' or 'grandforest.train_model.unsupervised.R'
	to train a local GrandForest model.
	:param expression_data: Local expression data as base64 encoded RData file with "data" object inside
	:param interaction_network: Interaction Network as base64 encoded RData file with "data" object inside
	:param split: current split as path to the output directory
	:return: base64 encoded RData file with the local model as "model" object inside
	"""
	temp_path = config.get_option('TEMP_DIR') + '/' + str(uuid4())
	os.makedirs(temp_path)

	open(temp_path + '/' + 'expression_data.RData', 'wb').write(base64.decodebytes(expression_data.encode('utf-8')))
	open(temp_path + '/' + 'interaction_network.RData', 'wb').write(base64.decodebytes(interaction_network.encode('utf-8')))

	if config.get_option('grandforest_method') == 'supervised':
		command = ["/app/app/R/grandforest.train_model.supervised.R",
				   temp_path + '/' + 'expression_data.RData',
				   temp_path + '/' + 'interaction_network.RData',
				   str(config.get_option('number_of_trees_per_split')[split]),
				   str(config.get_option('minimal_node_size')),
				   str(config.get_option('seed')),
				   str(config.get_option('grandforest_treetype')),
				   str(config.get_option('expression_data_dependent_variable_name')),
				   str(config.get_option('expression_data_survival_event')),
				   str(config.get_option('expression_data_survival_time')),
				   temp_path + '/' + 'local_model.RData']
	else:
		command = ["/app/app/R/grandforest.train_model.unsupervised.R",
				   temp_path + '/' + 'expression_data.RData',
				   temp_path + '/' + 'interaction_network.RData',
				   str(config.get_option('number_of_trees_per_split')[split]),
				   str(config.get_option('minimal_node_size')),
				   str(config.get_option('seed')),
				   temp_path + '/' + 'local_model.RData']

	local_computation_subprocess = RSubprocess(command)
	print('[ALGO] Starting RSubprocess to calculate local GrandForest model...')
	local_computation_subprocess.start()
	print('[ALGO] Started RSubprocess to calculate local GrandForest model')
	local_computation_subprocess.join()
	print('[ALGO] Finished RSubprocess to calculate local GrandForest model')

	# save local model as base64 encoded string
	local_model = base64.b64encode(open(temp_path + '/' + 'local_model.RData', 'rb').read()).decode('utf-8')

	print(f'[ALGO] Local computation of client {config.get_option("id")}: {sys.getsizeof(local_model)} Bytes successful')

	return local_model


def __aggregate_grandforest_models(global_data):
	"""
	Private Method.
	Executes the RScript 'grandforest.sum_models.R' to sum all the local models to a global model.
	:param global_data: Local models as a list of base64 encoded RData files with one "model" object per file inside
	:return: base64 encoded RData file with the aggregated global model as "model" object inside
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

	# save global model as base64 encoded string
	global_model = base64.b64encode(open(temp_path + '/' + 'forest1.RData', 'rb').read()).decode('utf-8')
	os.remove(temp_path + '/' + 'forest1.RData')
	print(
		f'[ALGO] Global Aggregation on client {config.get_option("id")}: {sys.getsizeof(global_model)} Bytes successful')

	return global_model


def __predict_with_grandforest_model(global_model, expression_data, split):
	"""
	Private Method.
	Executes the RScript 'grandforest.predict.supervised.R' or 'grandforest.predict.unsupervised.R'
	to predict the local expression data with the global model and write the results to the split
	output directory.
	:param global_model: global model as base64 encoded RData file
	:param expression_data: Local expression data as base64 encoded RData file
	:param split: current split as path to the output directory
	:return: None
	"""
	temp_path = config.get_option('TEMP_DIR') + '/' + str(uuid4())
	os.makedirs(temp_path)

	open(temp_path + '/' + 'global_model.RData', 'wb').write(
		base64.decodebytes(global_model.encode('utf-8')))
	open(temp_path + '/' + 'expression_data.RData', 'wb').write(
		base64.decodebytes(expression_data.encode('utf-8')))

	try:
		os.makedirs(split)
	except OSError as e:
		if e.errno != errno.EEXIST:
			raise

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


def __analyze_results(model, model_name, interaction_network, expression_data, split):
	"""
	Private Method.
	Executes the RScript 'grandforest.analyze_results.R' to create the plots and tables
	of the feature importance and endophenotyping analyses in the split output directory.
	:param interaction_network: Interaction Network as base64 encoded RData file with "data" object inside
	:param expression_data: Local expression data as base64 encoded RData file with "data" object inside
	:param split: current split as path to the output directory
	:return: None
	"""
	temp_path = config.get_option('TEMP_DIR') + '/' + str(uuid4())
	os.makedirs(temp_path)

	open(temp_path + '/' + 'interaction_network.RData', 'wb').write(
		base64.decodebytes(interaction_network.encode('utf-8')))
	open(temp_path + '/' + 'expression_data.RData', 'wb').write(base64.decodebytes(expression_data.encode('utf-8')))
	open(temp_path + '/' + 'model.RData', 'wb').write(
		base64.decodebytes(model.encode('utf-8')))

	try:
		os.makedirs(split + '/' + model_name)
	except OSError as e:
		if e.errno != errno.EEXIST:
			raise

	if config.get_option('grandforest_treetype') == 'survival':
		command = ["/app/app/R/grandforest.analyze_results.R",
				   temp_path + '/' + 'model' + '.RData',
				   temp_path + '/' + 'interaction_network.RData',
				   temp_path + '/' + 'expression_data.RData',
				   str(config.get_option('expression_data_survival_event')),
				   str(config.get_option('expression_data_survival_time')),
				   split + '/' + model_name + '/']
	else:
		command = ["/app/app/R/grandforest.analyze_results.R",
				   temp_path + '/' + 'model' + '.RData',
				   temp_path + '/' + 'interaction_network.RData',
				   temp_path + '/' + 'expression_data.RData',
				   'None',
				   'None',
				   split + '/' + model_name + '/']

	print('[IO] Starting RSubprocess to analyze the ' + model_name + '...')
	analyzing_results_subprocess = RSubprocess(command)
	analyzing_results_subprocess.start()
	print('[IO] Started RSubprocess to analyze the ' + model_name)
	analyzing_results_subprocess.join()
	print('[IO] Finished RSubprocess to analyze the ' + model_name)


# Functions exposed to AppLogic

def local_computation(expression_data, interaction_network, split):
	"""
	This method is exposed to AppLogic.
	Computes the local model.
	:param expression_data: Local expression data as base64 encoded RData file with "data" object inside
	:param interaction_network: Interaction Network as base64 encoded RData file with "data" object inside
	:param split: current split as path to the output directory
	:return: base64 encoded RData file with the local model as "model" object inside
	"""
	local_model = __compute_local_grandforest_model(expression_data, interaction_network, split)
	return local_model


def global_aggregation(global_data):
	"""
	This method is exposed to AppLogic.
	Aggregates the local models.
	:param global_data: Local models as a list of base64 encoded RData files with one "model" object per file inside
	:return: base64 encoded RData file with the aggregated global model as "model" object inside
	"""
	global_model = __aggregate_grandforest_models(global_data)
	return global_model


def local_prediction(global_model, expression_data, split):
	"""
	This method is exposed to AppLogic.
	Predicts local data with the global model and writes the results to the split output directory.
	:param global_model: base64 encoded RData file with the global model as "model" object inside
	:param expression_data: Local expression data as base64 encoded RData file with "data" object inside
	:return: None
	"""
	__predict_with_grandforest_model(global_model, expression_data, split)


def result_analysis(local_model, global_model, interaction_network, expression_data, split):
	"""
	This method is exposed to AppLogic.
	Executes the result analysis and writes the results to the split output directory.
	:param local_model: base64 encoded RData file with the local model as "model" object inside
	:param global_model: base64 encoded RData file with the global model as "model" object inside
	:param expression_data: Local expression data as base64 encoded RData file with "data" object inside
	:param interaction_network: Interaction Network as base64 encoded RData file with "data" object inside
	:param split: current split as path to the output directory
	:return: None
	"""
	__analyze_results(local_model, 'local_model', interaction_network, expression_data, split)
	__analyze_results(global_model, 'global_model', interaction_network, expression_data, split)


def write_results(local_model, global_model, split):
	"""
	This method is exposed to AppLogic.
	Writes the local_model and global_model to the split output directory.
	:param local_model: base64 encoded RData file with the local model as "model" object inside
	:param global_model: base64 encoded RData file with the global model as "model" object inside
	:param split: current split as path to the output directory
	:return: None
	"""
	write_output(local_model, 'local_model', split)
	write_output(global_model, 'global_model', split)

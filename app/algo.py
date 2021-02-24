import base64
import os
import sys
import shutil

from app import config
from app.io import read_input, write_output
from app.RSubprocess import RSubprocess


def compute_local_grandforest_model(expression_data, interaction_network):
	"""
	Compute the local model and number of samples
	:param expression_data: Local expression data as binary RData
	:param interaction_network: Interaction Network as binary RData
	:return: The local model as base64 encoded binary RData string and number of samples
	"""

	open(config.get_option('TEMP_DIR') + '/' + 'expression_data.RData', 'wb').write(expression_data)
	open(config.get_option('TEMP_DIR') + '/' + 'interaction_network.RData', 'wb').write(interaction_network)

	if config.get_option('grandforest_method') == 'supervised':
		command = ["/app/app/R/grandforest.train_model.supervised.R",
				   config.get_option('TEMP_DIR') + '/' + 'expression_data.RData',
				   config.get_option('TEMP_DIR') + '/' + 'interaction_network.RData',
				   str(config.get_option('number_of_trees')),
				   str(config.get_option('expression_data_dependent_variable_name')),
				   config.get_option('TEMP_DIR') + '/' + 'local_model.RData']
	else:
		command = ["/app/app/R/grandforest.train_model.unsupervised.R",
				   config.get_option('TEMP_DIR') + '/' + 'expression_data.RData',
				   config.get_option('TEMP_DIR') + '/' + 'interaction_network.RData',
				   str(config.get_option('number_of_trees')),
				   config.get_option('TEMP_DIR') + '/' + 'local_model.RData']

	local_computation_subprocess = RSubprocess(command)
	print('[ALGO] Starting RSubprocess to calculate local GrandForest model...')
	local_computation_subprocess.start()
	print('[ALGO] Started RSubprocess to calculate local GrandForest model')
	local_computation_subprocess.join()
	print('[ALGO] Finished RSubprocess to calculate local GrandForest model')

	# save local model as base64 encoded string
	local_model = base64.b64encode(open(config.get_option('TEMP_DIR') + '/' + 'local_model.RData', 'rb').read()).decode('utf-8')

	# save amount of lines - 1 (header line) as weighting constant
	with open(config.get_option('INPUT_DIR') + '/' + config.get_option('expression_data_filename')) as expression_data_file:
		nr_samples = sum(1 for line in expression_data_file) - 1

	print(f'[ALGO] Local computation of client {config.get_option("id")}: {sys.getsizeof(local_model)} Bytes with {nr_samples} samples successful')

	return local_model, nr_samples


def aggregate_grandforest_models(global_data):
	"""
	Aggregate the local models to a global model
	:param global_data: List of local models and local number of samples
	:return: The global model as base64 encoded binary RData string
	"""

	open(config.get_option('TEMP_DIR') + '/' + 'forest1.RData', 'wb').write(base64.decodebytes(global_data[0].encode('utf-8')))
	print('[ALGO] Starting RSubprocesses to aggregate the GrandForest models...')
	for i in range(1, len(global_data)):
		open(config.get_option('TEMP_DIR') + '/' + 'forest2.RData', 'wb').write(base64.decodebytes(global_data[i].encode('utf-8')))
		command = ["/app/app/R/grandforest.sum_models.R",
				   config.get_option('TEMP_DIR') + '/' + 'forest1.RData',
				   config.get_option('TEMP_DIR') + '/' + 'forest2.RData',
				   config.get_option('TEMP_DIR') + '/' + 'forest1.RData']
		model_aggregation_subprocess = RSubprocess(command)
		model_aggregation_subprocess.start()
		model_aggregation_subprocess.join()

		os.remove(config.get_option('TEMP_DIR') + '/' + 'forest2.RData')
	print('[ALGO] Finished RSubprocesses to aggregate the GrandForest models')

	global_model = base64.b64encode(open(config.get_option('TEMP_DIR') + '/' + 'forest1.RData', 'rb').read()).decode('utf-8')
	os.remove(config.get_option('TEMP_DIR') + '/' + 'forest1.RData')
	print(f'[ALGO] Global Aggregation on client {config.get_option("id")}: {sys.getsizeof(global_model)} Bytes successful')

	return global_model


def local_computation():
	expression_data = read_input(config.get_option('expression_data_filepath'), config.get_option('expression_data_filename'), config.get_option('expression_data_separator'))
	interaction_network = read_input(config.get_option('interaction_network_filepath'), config.get_option('interaction_network_filename'), config.get_option('interaction_network_separator'))
	local_model, nr_samples = compute_local_grandforest_model(expression_data, interaction_network)
	return local_model


def global_aggregation(global_data):
	global_model = aggregate_grandforest_models(global_data)
	return global_model


def write_results(local_model, global_model):
	"""
	Write the results to the output directory and delete the TEMP directory.
	:return: None
	"""
	write_output(local_model, 'local_model')
	write_output(global_model, 'global_model')

	shutil.rmtree(config.get_option('TEMP_DIR'))

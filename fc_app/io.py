import yaml
from flask import current_app
import sys

import subprocess

from redis_util import redis_get, redis_set

INPUT_DIR = "/mnt/input"
TEMP_DIR = "/app/temp"
OUTPUT_DIR = "/mnt/output"


def read_input(redis_identifier):
	"""
	Read in the input data from the input directory
	:return: Data or None if File could not be read
	"""
	input_filename = redis_get(redis_identifier + "_filename")
	input_separator = redis_get(redis_identifier + "_separator")
	try:
		current_app.logger.info('[IO] Parsing data of ' + INPUT_DIR)
		current_app.logger.info('[IO] ' + input_filename)

		command = ["/app/fc_app/R/grandforest.read_data_frame.R",
				   INPUT_DIR + "/" + input_filename,
				   str(input_separator),
				   TEMP_DIR + "/" + input_filename + ".RData"]

		subprocess_result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
		current_app.logger.info(subprocess_result.stdout)

		if subprocess_result.returncode != 0:
			current_app.logger.info(subprocess_result.stderr)
			current_app.logger.error('[IO] could not read file',
									 ChildProcessError("Subprocess returned " + str(subprocess_result.returncode)))
			raise ChildProcessError("Subprocess returned " + str(subprocess_result.returncode))

		data = open(TEMP_DIR + "/" + input_filename + ".RData", 'rb').read()

		current_app.logger.info(
			'[IO] Read R Dataframe with size ' + str(sys.getsizeof(data)) + 'Bytes')

		return data
	except Exception as e:
		current_app.logger.error('[IO] could not read file', e)

		return None


def write_results(local_model, global_model):
	"""
	Write the results to the output directory
	:param local_model: locally trained model result to be written as RData File
	:param global_model: globally aggregated model result to be written as RData File
	:return: None
	"""
	try:
		current_app.logger.info("[IO] Write results to output folder.")
		output_file_writer1 = open(OUTPUT_DIR + '/' + redis_get("local_model_output_filename"), 'xb')
		output_file_writer1.write(local_model)
		output_file_writer1.close()

		output_file_writer2 = open(OUTPUT_DIR + '/' + redis_get("global_model_output_filename"), 'xb')
		output_file_writer2.write(global_model)
		output_file_writer2.close()
	except Exception as e:
		current_app.logger.error('[IO] Could not write result files.', e)


def read_config():
	"""
	Read in the config.yml in the input directory. Save the parameters in redis.
	:return: None
	"""
	current_app.logger.info('[IO] Read config file.')
	with open(INPUT_DIR + '/config.yml') as f:
		config = yaml.load(f, Loader=yaml.FullLoader)['fc_grandforest']

		redis_set('grandforest_method', config['options']['grandforest_method'])
		if not redis_get('grandforest_method') == 'supervised' or redis_get('grandforest_method') == 'unsupervised':
			current_app.logger.error('[IO] Config File Error.',
									 ValueError("grandforest_method can either be 'supervised' or 'unsupervised'"))
		redis_set('number_of_trees', config['options']['number_of_trees'])
		redis_set('expression_data_dependent_variable_name', config['options']['expression_data_dependent_variable_name'])
		redis_set('expression_data_separator', config['options']['expression_data_separator'])
		redis_set('interaction_network_separator', config['options']['interaction_network_separator'])

		redis_set('expression_data_filename', config['files']['expression_data'])
		redis_set('interaction_network_filename', config['files']['interaction_network'])
		redis_set('local_model_output_filename', config['files']['local_model_output'])
		redis_set('global_model_output_filename', config['files']['global_model_output'])

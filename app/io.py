import errno
import yaml
import sys
import os

from app.RSubprocess import RSubprocess
from app import config

INPUT_DIR = "/mnt/input"
TEMP_DIR = "/app/temp"
OUTPUT_DIR = "/mnt/output"


def read_input(input_filename, input_separator):
	"""
	Read in the input data from the input directory
	:return: Data or None if File could not be read
	"""

	try:
		os.makedirs(TEMP_DIR)
	except OSError as e:
		if e.errno != errno.EEXIST:
			raise

	try:
		print('[IO] Parsing data of ' + INPUT_DIR + '/' + input_filename)

		command = ["/app/app/R/grandforest.read_data_frame.R",
				   INPUT_DIR + "/" + input_filename,
				   str(input_separator),
				   TEMP_DIR + "/" + input_filename + ".RData"]

		input_reader_subprocess = RSubprocess(command)
		print('[IO] Starting RSubprocess to read ' + input_filename + '...')
		input_reader_subprocess.start()
		print('[IO] Started RSubprocess to read ' + input_filename)
		input_reader_subprocess.join()
		print('[IO] Finished RSubprocess to read ' + input_filename)

		data = open(TEMP_DIR + "/" + input_filename + ".RData", 'rb').read()
		print('[IO] Converted RSubprocess Result to a python binary object')

		print('[IO] Read R Dataframe with size ' + str(sys.getsizeof(data)) + 'Bytes')

		return data
	except Exception as e:
		print('[IO] could not read file', e)

		return None


def write_binary_file(data, filename):
	"""
	Write the results to the output directory
	:param data: binary data to be written as RData File
	:param filename: output filename
	:return: None
	"""
	output_filepath = OUTPUT_DIR + '/' + filename

	try:
		print("[IO] Writing results to output folder.")
		output_file_writer = open(output_filepath, 'wb')
		output_file_writer.write(data)
		output_file_writer.close()
	except Exception as e:
		print('[ERROR] Could not write result file ', filename, '.', e)


def read_config(is_coordinator):
	"""
	Read in the config.yml in the input directory. Save the parameters in redis.
	:return: None
	"""

	print('[IO] Read config file.')
	with open(INPUT_DIR + '/config.yml') as f:
		config_file = yaml.load(f, Loader=yaml.FullLoader)['fc_grandforest']

		config.add_option('INPUT_DIR', INPUT_DIR)
		config.add_option('TEMP_DIR', TEMP_DIR)
		config.add_option('OUTPUT_DIR', OUTPUT_DIR)

		# TODO set global options
		if True:
			config.add_option('grandforest_method', config_file['global_options']['grandforest_method'])
			config.add_option('number_of_trees', config_file['global_options']['number_of_trees'])
			config.add_option('interaction_network_filename', config_file['global_options']['interaction_network'])
			config.add_option('interaction_network_separator',
							  config_file['global_options']['interaction_network_separator'])

		config.add_option('expression_data_dependent_variable_name',
						  config_file['local_options']['expression_data_dependent_variable_name'])
		config.add_option('expression_data_separator', config_file['local_options']['expression_data_separator'])

		config.add_option('expression_data_filename', config_file['local_files']['expression_data'])
		config.add_option('local_result_output_filename', config_file['local_files']['local_result_output_filename'])
		config.add_option('global_result_output_filename', config_file['local_files']['global_result_output_filename'])

		# Check if config options are set correctly
		if not config.get_option('grandforest_method') == 'supervised' or config.get_option(
				'grandforest_method') == 'unsupervised':
			print('[IO] Config File Error.')
			raise ValueError("grandforest_method can either be 'supervised' or 'unsupervised'")

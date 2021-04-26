# This config dictionary represents the config yaml file.
# Variables stored in the config dictionary:
# Global Variables:
# 	sync 'grandforest_method': either 'supervised' or 'unsupervised'
# 	sync 'number_of_trees': each local model should have the same amount of trees
# 	'interaction_network_filename'
# 	'interaction_network_filepath'
# 	'interaction_network_separator'
# Local Variables:
# 	'INPUT_DIR'
# 	'TEMP_DIR'
# 	'OUTPUT_DIR'
# 	'expression_data_filename'
# 	'expression_data_filepath'
# 	'expression_data_separator'
# 	'expression_data_dependent_variable_name'


def init():
	global config_dict
	config_dict = dict()


def is_initialized():
	return config_dict is not None


def add_option(key, value):
	config_dict[key] = value


def get_option(key):
	return config_dict[key]


def print_config():
	print(config_dict)

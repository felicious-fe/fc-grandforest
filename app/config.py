# This config dictionary represents the config yaml file.
# Variables stored in the config dictionary:
# Global Variables:
# 	sync 'grandforest_method': either 'supervised' or 'unsupervised'
# 	sync 'number_of_trees_per_split': Dictionary of the amount of trees per split, specific to a Client
#   sync 'minimal_node_size'
#   sync 'seed'
# 	'interaction_network_filename'
# 	'interaction_network_filepath'
# 	'interaction_network_separator'
#		(these options are not synced, since the whole interaction network RData file is synced)
# Local Variables:
# 	'INPUT_DIR'
# 	'TEMP_DIR'
# 	'OUTPUT_DIR'
# 	'expression_data_filename'
# 	'expression_data_filepath'
# 	'expression_data_separator'
# 	'expression_data_dependent_variable_name'
# 	'expression_data_survival_time'
# 	'expression_data_survival_event'


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

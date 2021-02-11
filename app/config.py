def init():
	global config_dict
	config_dict = dict()


def add_option(key, value):
	config_dict[key] = value


def get_option(key):
	return config_dict[key]

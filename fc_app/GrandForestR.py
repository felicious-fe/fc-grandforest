import pandas
import rpy2.robjects as robjects
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr


class GrandForestR(object):

	def __init__(self, feature_graph=None):
		self.forest = None

		self.base = importr('base')
		self.utils = importr('utils')
		self.stats = importr('stats')
		self.tibble = importr('tibble')
		self.r = robjects.r

		try:
			self.grandforest = importr("grandforest")
		except robjects.packages.PackageNotInstalledError:
			self.utils.chooseCRANmirror(ind=1)
			# dependencies: gcc/clang, openssl-devel, libcurl-devel
			self.utils.install_packages("devtools")
			devtools = importr("devtools")
			devtools.install_github("SimonLarsen/grandforest")
			self.grandforest = importr("grandforest")

		self.r['source']('/app/fc_app/R/grandforest.sum_models.R')

		d = {'a': robjects.StrVector(feature_graph['gene1']), 'b': robjects.StrVector(feature_graph['gene2'])}
		self.r_feature_graph = robjects.DataFrame(d)

	def fit(self, data, labels=None, n_trees=1000, min_node_size=1):
		pandas2ri.activate()  # this is implicitly enabled for the whole project now (or until its explicitly disabled)!!!!
		r_data = self.tibble.tibble(data)

		# Supervised Survival Analysis
		# r_grandforest_args = {'data': r_data,
		# 	'graph_data': self.r_feature_graph,
		# 	'dependent_variable_name': 'os_time',
		# 	'status_variable_name': 'os_event',
		# 	'num_trees': n_trees
		# )
		# self.forest = self.r['grandforest'](**r_grandforest_args)
		# pandas2ri.deactivate()

		# Unsupervised Endophenotyping
		r_grandforest_args = {'data': r_data,
							'graph_data': self.r_feature_graph,
							'num.trees': n_trees}

		self.forest = self.r['grandforest_unsupervised'](**r_grandforest_args)
		pandas2ri.deactivate()

	def predict(self, data):
		pandas2ri.activate()
		prediction = self.stats.predict(self.forest, data=data)
		print(prediction)
		pandas2ri.deactivate()
		return prediction

	def sum_forests(self, forests: list):
		summed_forest = forests[0]
		for i in range(1, len(forests)):
			summed_forest = self.r['grandforest.sum_models'](summed_forest, forests[i])
		self.forest = summed_forest

	def sum_forest(self, forest1, forest2):
		return self.r['grandforest.sum_models'](forest1, forest2)

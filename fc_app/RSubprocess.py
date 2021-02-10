import threading
import subprocess
from flask import current_app


class RSubprocess(threading.Thread):
	def __init__(self, command):
		self.stdout = None
		self.stderr = None
		self.command = command
		threading.Thread.__init__(self)

	def run(self, verbose=False):
		subprocess_result = subprocess.run(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
		self.stdout = subprocess_result.stdout
		self.stderr = subprocess_result.stderr

		if verbose:
			current_app.logger.info(self.stdout)

		if subprocess_result.returncode != 0:
			current_app.logger.error(self.stderr)
			current_app.logger.error('[IO] could not read file',
									 ChildProcessError("Subprocess returned " + str(subprocess_result.returncode)))
			raise ChildProcessError("Subprocess returned " + str(subprocess_result.returncode))

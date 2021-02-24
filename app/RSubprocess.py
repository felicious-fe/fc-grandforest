import threading
import subprocess


class RSubprocess(threading.Thread):
	def __init__(self, command):
		self.stdout = None
		self.stderr = None
		self.command = command
		threading.Thread.__init__(self)

	def run(self):
		subprocess_result = subprocess.run(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
		self.stdout = subprocess_result.stdout
		self.stderr = subprocess_result.stderr

		if subprocess_result.returncode != 0:
			print(f'[R] STDOUT:', flush=True)
			print(f'{self.stdout}\n\n', flush=True)
			print(f'[R] STDERR:{self.stderr}', flush=True)
			print(f'{self.stderr}\n\n', flush=True)
			print(f'[R] Subprocess returned non 0 exit code', flush=True)
			raise ChildProcessError(str(subprocess_result.returncode))

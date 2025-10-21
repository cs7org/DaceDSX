import os
import hashlib


class UpdateGenerator:
	"""
	@brief Update Generator
	@author Michael Niebisch
	@bug No known bugs

	Class defining the Update Generator. Used to generate an update.

	"""

	def generate_update(self, filename: str, size: int, chunk_size: int, due_date: float) -> None:
		"""
		Generate an update with given filename and size and generate corresponding metadata file.
		Can be changed to generate a actual file to be transmitted, uses random content otherwise.
		@param filename File name of update
		@param size The size of the update
		@param chunk_size Size of a chunk
		@param due_date Due date of update
		"""
		content = ""
		#with open(f'{filename}.dat', 'wb') as file_out:
		content = os.urandom(size)
		#	file_out.write(content)
		update_hash = hashlib.sha224(content).hexdigest()
		number_of_chunks = int(size / chunk_size)
		if size % chunk_size != 0:
			number_of_chunks += 1
		with open('%s.datmeta' % filename, 'w') as file_out:
			file_out.write("%s\n" % size)
			file_out.write("%s\n" % number_of_chunks)
			file_out.write("%s\n" % filename)
			file_out.write("%s\n" % due_date)
			file_out.write("%s\n" % update_hash)
		self.__allUpdates.append(filename)
		del content

	def __init__(self) -> None:
		"""
		Create an update generator.
		"""
		self.__allUpdates = []

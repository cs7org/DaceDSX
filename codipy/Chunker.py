
class Chunker:
	"""
	@brief Chunker
	@author Michael Niebisch
	@bug No known bugs

	Class defining a chunker used to divide the update into chunks.

	"""
	def get_chunks(self, update_name: str) -> dict:
		"""
		Get all chunks of the update
		@param update_name: Name of the update
		@return Dict containing the update chunks
		"""
		with open('%s.datmeta' % update_name, 'r') as fin:
			size = int(fin.readline())
		number_of_chunks = int(size / self.__chunkSize)
		if self.__chunkSize % size != 0:
			number_of_chunks += 1
		chunk_dict = {}
		counter = 0
		if False: # omit reading the file, as it stays in the RAM
			with open('%s.dat' % update_name, 'rb') as updateFile:
				file_bytes = updateFile.read(self.__chunkSize)
				while file_bytes != b"":
					chunk_dict[counter] = file_bytes
					counter += 1
					file_bytes = updateFile.read(self.__chunkSize)
		else:
			for i in range(number_of_chunks):
				chunk_dict[i] = 1
		return chunk_dict

	def set_seeder(self, seeder) -> None:
		"""
		Set the seeder
		@param seeder A BackendSeeder
		"""
		self.__seeder = seeder

	def __init__(self, chunk_size: int) -> None:
		"""
		Initialize a chunker object
		@param chunk_size Size of a chunk in byte
		"""
		self.__seeder = None
		self.__chunkSize = chunk_size

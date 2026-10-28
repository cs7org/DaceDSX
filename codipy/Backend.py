import BackendManager
import BackendManager as backendManager
import UpdateGenerator as updateGenerator
import BackendSeeder as BackendSeeder
import Chunker as Chunker
import time
from Vehicle import Vehicle


class Backend:
    """
    @brief Server backend
    @author Michael Niebisch
    @bug No known bugs

    Class defining a backend used for coordination of updates and vehicles.

    """

    def __str__(self) -> str:
        """
        String representation of backend object
        @return Backend
        """
        return "Backend"

    def initial_seed_for_update(self, veh: Vehicle, update_name: str, seed_number: int = 0) -> int:
        """
        Initially seeds the update to the vehicle.
        @param veh A Vehicle
        @param update_name Name of the update
        @param seed_number Number of seeds to be seeded
        """
        if seed_number != 0:
            self.__seeder.initial_seed(veh, update_name, seed_number, self.__seeding_strategy)
            return seed_number
        else:
            self.__seeder.initial_seed(veh, update_name, self.__seed_number, self.__seeding_strategy)
            return self.__seed_number

    def generate_update(self, size: int = 1000 * 1000) -> str:
        """
        Generates an update with given size in bytes

        @param size Byte size of update
        @return  filename of update

        """
        t = time.time()
        filename = time.strftime("%d%m%Y%H_%M_%S") + "_" + str(int(round(t * 1000)))
        self.__updateGenerator.generate_update(filename, size, self.__chunkSize, t + 60 * 60 * 3)
        self.__backendManager.insert_new_update(filename)
        return filename

    def register(self, veh: Vehicle) -> None:
        """
        Register the Vehicle at the BackendManager
        @param veh A Vehicle
        """
        self.__backendManager.register(veh)

    def get_backend_manager(self) -> BackendManager:
        """
        Get the BackendManager of the Backend
        @return The BackendManager
        """
        return self.__backendManager

    def get_chunk_size(self) -> int:
        """
        Get the used chunk size.
        @return Size of a chunk
        """
        return self.__chunkSize

    def seed_for_update(self, veh: Vehicle, update_name: str, seed_number) -> int:
        """
        Initially seeds the update to the vehicle.
        @param seed_number Number of chunks to seed
        @param veh A Vehicle
        @param update_name Name of the update
        @param seed_number Number of chunks to seed
        @return Number of seeded chunks
        """
        return self.__seeder.seeding(veh, update_name, seed_number)

    def __init__(self, chunk_size: int, seed_number: int, number_vehicles: int,
                 seeding_strategy: str = "random") -> None:
        """
        Initialize a Backend object
        @param chunk_size: Size of a chunk
        @param seed_number: Number of chunks to seed initially
        @param number_vehicles: Number of vehicles
        @param seeding_strategy: Seeding strategy to be used
        """
        self.__backendManager = backendManager.BackendManager(self)
        self.__updateGenerator = updateGenerator.UpdateGenerator()
        self.__seeder = BackendSeeder.BackendSeeder(number_vehicles)
        self.__chunkSize = chunk_size  # 1411 #1500
        self.__chunker = Chunker.Chunker(self.__chunkSize)
        self.__seeder.set_chunker(self.__chunker)
        self.__chunker.set_seeder(self.__seeder)
        self.__seed_number = seed_number
        self.__number_vehicles = number_vehicles
        self.__seeding_strategy = seeding_strategy

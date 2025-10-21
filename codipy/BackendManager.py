import random
from typing import List

import bitarray
import V2VHeartbeatMsg
import UpdateInitMsg as updateMsg
from Vehicle import Vehicle


class BackendManager:
    """
        @brief Backend Manager
        @author Michael Niebisch
        @bug No known bugs

        Class defining a backend manager used to manage updates.

    """

    def get_number_of_updates(self) -> int:
        """
        Get number of updates
        @return Number of updates
        """
        return self.__numberOfUpdates

    def register(self, veh) -> None:
        """
        Registers a vehicle
        @param veh Vehicle to register
        """
        self.__registeredVehicles.append(veh)

    def insert_new_update(self, name: str) -> None:
        """
        Inserts a new update
        @param name Name of the update
        """
        self.__updates.append(name)
        self.__numberOfUpdates = len(self.__updates)

    def send_meta_data(self, update: str, veh: Vehicle) -> None:
        """
        Sends meta data of the update to the vehicle
        @param update: Name of the update
        @param veh: A Vehicle
        """
        with open('%s.datmeta' % update, 'r') as fin:
            size = int(fin.readline())
            number_of_chunks = int(fin.readline())
            update_name = str(fin.readline()[:-1])
            due_date = float(fin.readline())
            update_hash = str(fin.readline()[:-1]).encode('utf-8')
            self.create_bitmap(update_name, number_of_chunks)

        update_message = updateMsg.encode(update_name, size, due_date, update_hash)
        veh.receive_meta_data(update_message)

    def create_bitmap(self, update_name: str, number_of_chunks: int) -> None:
        """
        Create a bitmask for an update
        @param update_name Name of update
        @param number_of_chunks Length of update in chunks
        """
        self.__update_bitmaps[update_name] = bitarray.bitarray(number_of_chunks)
        self.__update_bitmaps[update_name].setall(1)

    def check_for_new_updates(self, last_updates: list, veh: Vehicle, seed_number: int) -> int:
        """
        Checks if there are new updates available for the vehicle
        @param last_updates List of last updates from the Vehicle
        @param veh A Vehicle
        @param seed_number Number of seeds
        @return Number of seeded chunks
        """
        for entry in self.__updates:
            if len(last_updates) == 0 or entry not in last_updates:
                self.send_meta_data(entry, veh)
                return self.__backend.initial_seed_for_update(veh, entry, seed_number)
        return 0

    def seeder(self, veh: Vehicle, seed_number: int) -> int:
        """
        Checks if there are new updates available for the vehicle
        @param veh A Vehicle
        @param seed_number Number of seeds to be seeded
        @return Number of seeded chunks
        """
        for entry in self.__updates:
            return self.__backend.seed_for_update(veh, entry, seed_number)

    def get_updates(self):
        """
        Get list of all updates
        @return List of updates
        """
        return self.__updates

    def get_chunks(self, update: str, vehicle_bitmask: bitarray, number_of_chunks_to_send: int) -> List:
        """
        Return number_of_chunks_to_send many indices, that can be sent to the vehicle
        @param update The update
        @param vehicle_bitmask Bitmask of the current update state in the vehicle
        @param number_of_chunks_to_send Number of chunks requested
        @return List of indices
        """
        indices = V2VHeartbeatMsg.data_indices_to_send(vehicle_bitmask, self.__update_bitmaps[update], 0)
        return random.sample(indices, number_of_chunks_to_send)


    @staticmethod
    def get_number_of_chunks(update: str) -> int:
        """
        Get the number of chunks in a given update
        @param update The update to check
        @return Number of chunks
        """
        with open('%s.datmeta' % update, 'r') as fin:
            size = int(fin.readline())
            number_of_chunks = int(fin.readline())
        return number_of_chunks

    def __init__(self, backend, number_of_initial_update: int = 1) -> None:
        """
        Initialize a BackendManager object
        @param backend A Backend
        @param number_of_initial_update Number of initial updates
        """
        self.__backend = backend
        self.__registeredVehicles = []
        self.__updates = []
        self.__numberOfUpdates = len(self.__updates)
        self.__update_bitmaps = {}

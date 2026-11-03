import math
import random
import sys

from Chunker import Chunker
from Vehicle import Vehicle


class BackendSeeder:
    """
    @brief Backend Seeder
    @author Michael Niebisch
    @bug No known bugs

    Class defining a backend seeder used to seed updates.

    """

    def initial_seed(self, veh: Vehicle, update_name: str, seed_number: int, strategy: str) -> None:
        """
        Initially seeds the update randomly to the vehicle
        @param veh A Vehicle
        @param update_name Name of the update
        @param seed_number Number of initial seeds
        @param strategy Strategy to be used for seeding
        """
        chunk_dict = self.__chunker.get_chunks(update_name)
        if not update_name in self.__update_dict:
            self.__update_dict[update_name] = chunk_dict.keys()
        # select random chunks from full update
        if strategy == "random":
            random_chunks = random.sample(list(chunk_dict.keys()), seed_number)
            message_list = []
            for chunkKey in random_chunks:
               message_list.append((update_name, chunkKey, chunk_dict[chunkKey]))
               #veh.receive_chunk(update_name, chunkKey, chunk_dict[chunkKey], True)
            veh.save_received_data_bulk(message_list, True)
        # every vehicle is seeded, ensure every chunk is in the simulation at least once
        elif strategy == "at least once":
            chunks = set(random.sample(list(self.__update_dict[update_name]), min(math.ceil(len(chunk_dict.keys()) * 1.0/float(self.__number_vehicles)), len(self.__update_dict[update_name]))))

            self.__update_dict[update_name] = [x for x in self.__update_dict[update_name] if x not in chunks]
            additional_chunks = []
            if len(chunks) < seed_number:
                additional_chunks = random.sample(list(chunk_dict.keys()), seed_number - len(chunks))
            chunks.update(additional_chunks)
            message_list = []
            print(veh.get_veh_id(), len(chunks), len(self.__update_dict[update_name]))
            for chunk in chunks:
                message_list.append((update_name, chunk, chunk_dict[chunk]))
            veh.save_received_data_bulk(message_list, True)
        # every vehicle is seeded, all seeded chunks are consecutive
        elif strategy == "blocks":
            block_number = int(veh.get_veh_id()[7:])
            chunk_list = list(chunk_dict.keys())
            start = (block_number * seed_number) % len(chunk_list)
            end = ((block_number + 1) * seed_number) % len(chunk_list)
            if start < end:
                chunks = chunk_list[start:end]
            else:
                chunks = chunk_list[start:]
                chunks.extend(chunk_list[:end])
            message_list = []
            for chunkKey in chunks:
                message_list.append((update_name, chunkKey, chunk_dict[chunkKey]))
            veh.save_received_data_bulk(message_list, True)
        # 50% of all vehicles is seeded, with every chunk contained at least once
        elif strategy == "at least once 50":
            block_number = int(veh.get_veh_id()[7:])
            if int(math.ceil(self.__number_vehicles * 0.5)) > block_number:
                chunks = set(random.sample(list(self.__update_dict[update_name]), min(math.ceil(len(chunk_dict.keys()) * 1.0/(math.ceil(float(self.__number_vehicles) * 0.5))), len(self.__update_dict[update_name]))))
                self.__update_dict[update_name] = [x for x in self.__update_dict[update_name] if x not in chunks]
                additional_chunks = []
                if len(chunks) < seed_number:
                    additional_chunks = random.sample(list(chunk_dict.keys()), seed_number - len(chunks))
                chunks.update(additional_chunks)
                message_list = []
                print(veh.get_veh_id(), len(chunks), len(self.__update_dict[update_name]))
                for chunk in chunks:
                    message_list.append((update_name, chunk, chunk_dict[chunk]))
                veh.save_received_data_bulk(message_list, True)
        # 10% of all vehicles is seeded, with every chunk contained at least once
        elif strategy == "at least once 10":
            block_number = int(veh.get_veh_id()[7:])
            if int(math.ceil(self.__number_vehicles * 0.1)) > block_number:
                chunks = set(random.sample(self.__update_dict[update_name], min(math.ceil(len(chunk_dict.keys()) * 1.0/(math.ceil(float(self.__number_vehicles) * 0.1))), len(self.__update_dict[update_name]))))
                self.__update_dict[update_name] = [x for x in self.__update_dict[update_name] if x not in chunks]
                additional_chunks = []
                if len(chunks) < seed_number:
                    additional_chunks = random.sample(list(chunk_dict.keys()), seed_number - len(chunks))
                chunks.update(additional_chunks)
                message_list = []
                print(veh.get_veh_id(), len(chunks), len(self.__update_dict[update_name]))
                for chunk in chunks:
                    message_list.append((update_name, chunk, chunk_dict[chunk]))
                veh.save_received_data_bulk(message_list, True)
        # 1% of all vehicles is seeded, with every chunk contained at least once
        elif strategy == "at least once 1":
            block_number = int(veh.get_veh_id()[7:])
            if int(math.ceil(self.__number_vehicles * 0.01)) > block_number:
                chunks = set(random.sample(list(self.__update_dict[update_name]), min(math.ceil(
                    len(chunk_dict.keys()) * 1.0 / (math.ceil(float(self.__number_vehicles) * 0.01))),
                                                                            len(self.__update_dict[update_name]))))
                self.__update_dict[update_name] = [x for x in self.__update_dict[update_name] if x not in chunks]
                additional_chunks = []
                if len(chunks) < seed_number:
                    additional_chunks = random.sample(chunk_dict.keys(), seed_number - len(chunks))
                chunks.update(additional_chunks)
                message_list = []
                print(veh.get_veh_id(), len(chunks), len(self.__update_dict[update_name]))
                for chunk in chunks:
                    message_list.append((update_name, chunk, chunk_dict[chunk]))
                veh.save_received_data_bulk(message_list, True)
        elif strategy == "none":
            pass


    def set_chunker(self, chunker: Chunker) -> None:
        """
        Set the Chunker
        @param chunker A Chunker
        """
        self.__chunker = chunker

    def seeding(self, veh: Vehicle, update_name: str, seed_number: int) -> int:
        """
        Seeds an update randomly to the vehicle
        @param veh A Vehicle
        @param update_name Name of the update
        @param seed_number Number of chunks to be seeded
        @return Number of actually seeded chunks
        """
        remaining_chunks = veh.get_remaining_chunks(update_name)
        chunk_dict = self.__chunker.get_chunks(update_name)
        #chunk_dict = remaining_chunks
        if not update_name in self.__update_dict:
            self.__update_dict[update_name] = chunk_dict.keys()
        # select random chunks from full update
        loaded_chunks = min(seed_number, len(remaining_chunks))
        if seed_number > len(remaining_chunks):
            random_chunks = remaining_chunks
        else:
            random_chunks = random.sample(remaining_chunks, seed_number) #random.choices
        message_list = []
        for chunkKey in random_chunks:
            message_list.append((update_name, chunkKey, chunk_dict[chunkKey]))
            #veh.receive_chunk(update_name, chunkKey, chunk_dict[chunkKey], True)
        veh.save_received_data_bulk(message_list, True)
        return loaded_chunks

    def __init__(self, number_vehicles) -> None:
        """
        Initialize a BackendSeeder object
        @param number_vehicles Number of Vehicles
        """
        self.__chunker = None
        self.__number_vehicles = number_vehicles
        self.__update_dict = {}

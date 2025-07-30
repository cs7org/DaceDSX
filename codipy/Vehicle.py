import random
from typing import List, Set, Dict
import bitarray
import matplotlib as mpl
import DataMsg
import V2VHeartbeatMsg
from MessageType import *
import copy
import hashlib
import UpdateInitMsg as UpdateInitMsg
import csv
import WLANModuleVehicle
import V2VModuleVehicle
from collections import Counter


class Vehicle:
    """
    @brief Vehicle
    @author Michael Niebisch
    @bug No known bugs

    Class defining all functionalities of a Vehicle
    """

    def __hash__(self):
        return hash(self.__vehID)

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __str__(self):
        return "%s" % self.__vehID

    def get_wlan_module(self):
        """
        Get the WLAN module
        @return The WLAN module
        """
        return self.__wlan_module

    def get_v2v_module(self):
        """
        Get the V2V module
        @return The V2V module
        """
        return self.__v2v_module

    def calculate_data_to_send(self, current_time: float, packet_rate: float, step_length: float,
                               index_list_to_send: List[tuple], replace_send_data: bool = False) -> None:
        """
        Generates data messages that are to be sent next.

        @bug Currently schedules enough packets for 10 seconds (implicitly the heartbeat interval)
        @param current_time The current simulation time
        @param packet_rate The packet rate
        @param step_length The simulation step length
        @param index_list_to_send Update and chunk indices to be sent
        @param replace_send_data Replace the send list
        """
        time_step_between_packets = step_length / packet_rate
        packets_to_send = self.__heartbeat_interval / time_step_between_packets
        self.__is_sending_data = True
        packet_storage = []
        send_time = current_time
        for info in index_list_to_send:
            update = info[0]
            indices = set(info[1])
            if update not in self.__updates:
                continue

            number = min(int(packets_to_send), len(indices))
            random_chunks = random.sample(sorted(indices), number)
            for chunk in random_chunks:
                if not replace_send_data:
                    self.__v2v_module.add_send_message(
                        (round(send_time, 6), DataMsg.generate_message(self.__updates, update, chunk)))
                else:
                    packet_storage.append((send_time, DataMsg.generate_message(self.__updates, update, chunk)))
                self.__last_scheduled_data_packet = send_time
                send_time += time_step_between_packets
            if replace_send_data:
                self.__v2v_module.replace_send_messages(packet_storage)

    def calculate_data_to_send_new(self, current_time: float, packet_rate: float, step_length: float,
                                   index_list_to_send: List[tuple], replace_send_data: str = False) -> None:
        """
        Generates data messages that are to be sent next.

        @bug Currently schedules enough packets for 10 seconds (implicitly the heartbeat interval)
        @param current_time The current simulation time
        @param packet_rate The packet rate
        @param step_length The simulation step length
        @param index_list_to_send Update and chunk indices to be sent
        @param replace_send_data Replace the send list
        """
        time_step_between_packets = step_length / packet_rate
        packets_to_send = self.__heartbeat_interval / time_step_between_packets
        self.__is_sending_data = True
        counter = 0
        packet_storage = []
        send_time = current_time
        update_sets = {}
        messages_to_send = []
        for info in index_list_to_send:
            update = info[0]
            if update not in self.__updates:
                continue
            chunk = info[1]
            if update not in update_sets:
                update_sets[update] = set(self.__updates[update])

            if chunk in update_sets[update]:
                if counter >= packets_to_send:
                    break
                messages_to_send.append((round(send_time, 6), DataMsg.generate_message(self.__updates, update, chunk)))
                self.__last_scheduled_data_packet = send_time
                send_time += time_step_between_packets
                index_list_to_send.remove(info)
                counter += 1
        self.__v2v_module.replace_send_messages(messages_to_send)

    @staticmethod
    def check_received_message(msg: bytearray) -> (bool, MessageType):
        """
        Check if the hash value of the received message is correct and return the message type

        @param msg bytearray of the received message
        @return True if the hash value is correct, False otherwise and the MessageType
        """
        return True, MessageType(int.from_bytes(msg[:1], byteorder='big'))

    def make_index_list(self, message: tuple) -> List[tuple]:
        """
        Makes index_list out of received heartbeat message
        @param message the received heartbeat
        @return index_list consisting of updates and chunks to send
        """
        reception_time = message[0]
        relevance = message[2]
        message = message[1]
        # Only use valid messages
        valid, type_name = self.check_received_message(message)
        update_list_received = V2VHeartbeatMsg.decode_message(message,
                                                              True if type_name is MessageType.HEARTBEAT_BITMAP else False)
        if len(update_list_received) == 0:
            return []
        index_list_to_send = []
        for received_update in update_list_received:
            update_hash = received_update[0]
            update_name = ''
            found = False
            for update in self.__updates:
                update_name_hash = hashlib.sha224(str.encode(update)).digest()[:8]
                if update_hash == update_name_hash:
                    update_name = update
                    found = True
                    break
            if found:
                index_list_to_send.append((update_name, V2VHeartbeatMsg.data_indices_to_send(
                    received_update[3], self.__updates_bitmap[update_name], received_update[1]), relevance,
                                           reception_time))
        return index_list_to_send

    def calculate_behaviour_last_time_step(self, current_time: float, step_length: float, packet_rate: float) -> None:
        """
        Calculate the behaviour in the last time step, especially after receiving messages from other vehicles

        @bug After receiving one heartbeat message from a vehicle, up tp 10 seconds of packets are scheduled to be sent.
            However, all other heartbeat messages from other vehicles are ignored.
        @param current_time The current simulation time
        @param step_length The simulation step length
        @param packet_rate The packet rate
        """

        log_data = {}

        # WLAN
        if self.__wlan_module is not None:
            received_wlan_messages = self.__wlan_module.retrieve_received_messages()

            received_message_list = []
            if len(received_wlan_messages) > 0:
                for message in received_wlan_messages[0][0]:

                    reception_time = message[0]
                    message = message[1]
                    # Only use valid messages
                    valid, type_name = self.check_received_message(message)
                    if not valid:
                        continue
                    if type_name is MessageType.DATA:
                        received_message_list.append(message)
                if len(received_message_list) > 0:
                    log_time, data_dict = self.save_received_data_bulk(received_message_list)
                    for file_name in data_dict.keys():
                        if file_name not in set(log_data):
                            log_data[file_name] = []
                        for chunk_index in data_dict[file_name]:
                            log_data[file_name].append((log_time, chunk_index))

        # V2V
        if self.__v2v_module is not None:
            received_messages = self.__v2v_module.get_received_messages()
            if current_time > self.__last_scheduled_data_packet:
                self.__is_sending_data = False
                self.__v2v_most_relevant_heartbeat_strategy = None
            received_message_list = []
            for r_message in received_messages:
                reception_time = r_message[0]
                message = r_message[1]
                relevance = r_message[2]
                sending_vehicle = r_message[3]
                # Only use valid messages
                valid, type_name = self.check_received_message(message)

                if not valid:
                    continue

                if type_name is MessageType.HEARTBEAT or type_name is MessageType.HEARTBEAT_BITMAP:

                    update_list_received = V2VHeartbeatMsg.decode_message(message,
                                                                          True if type_name is MessageType.HEARTBEAT_BITMAP else False)
                    self.__received_v2v_heartbeat_messages.append((reception_time, message, relevance))
                    if len(update_list_received) == 0:
                        continue
                    index_list_to_send = []
                    for received_update in update_list_received:
                        update_hash = received_update[0]
                        update_name = ''
                        found = False
                        for update in self.__updates:
                            update_name_hash = hashlib.sha224(str.encode(update)).digest()[:8]
                            if update_hash == update_name_hash:
                                update_name = update
                                found = True
                                break
                        if found:
                            # Valid heartbeat received via V2V
                            if self.__wlan_heartbeat_strategy == 1:  # counter
                                for counter, index in enumerate(received_update[3]):
                                    chunk_index = 0
                                    if counter + received_update[1] >= self.__updateMetaData[update]['numberOfChunks']:
                                        chunk_index = counter + received_update[1] - self.__updateMetaData[update][
                                            'numberOfChunks']
                                    else:
                                        chunk_index = counter + received_update[1]
                                    if not index and chunk_index in self.__counter_strategy_dict[update_name]:
                                        self.__counter_strategy_dict[update_name][chunk_index] += 1
                            elif self.__wlan_heartbeat_strategy == 2:  # weighted counter

                                for counter, index in enumerate(received_update[3]):
                                    chunk_index = 0
                                    if counter + received_update[1] >= self.__updateMetaData[update]['numberOfChunks']:
                                        chunk_index = counter + received_update[1] - self.__updateMetaData[update][
                                            'numberOfChunks']
                                    else:
                                        chunk_index = counter + received_update[1]
                                    if not index and chunk_index in self.__weighted_counter_strategy_dict[update_name]:
                                        sum2 = self.__weighted_counter_strategy_dict[update_name][chunk_index]["avg"] * \
                                               self.__weighted_counter_strategy_dict[update_name][chunk_index][
                                                   "counter"] + current_time
                                        self.__weighted_counter_strategy_dict[update_name][chunk_index]["counter"] += 1
                                        self.__weighted_counter_strategy_dict[update_name][chunk_index]["avg"] = sum2 / \
                                                                                                                 self.__weighted_counter_strategy_dict[
                                                                                                                     update_name][
                                                                                                                     chunk_index][
                                                                                                                     "counter"]
                            elif self.__wlan_heartbeat_strategy == 3:  # most recent
                                heartbeat_list = []
                                for counter, value in enumerate(received_update[3]):
                                    chunk_index = 0
                                    if counter + received_update[1] >= self.__updateMetaData[update]['numberOfChunks']:
                                        chunk_index = counter + received_update[1] - self.__updateMetaData[update][
                                            'numberOfChunks']
                                    else:
                                        chunk_index = counter + received_update[1]
                                    if not value:
                                        heartbeat_list.append(chunk_index)
                                self.__most_recent_heartbeat_strategy_dict[update_name].append(heartbeat_list)

                # If the message is a heartbeat message, and the vehicle is not currently sending scheduled data
                if self.__v2v_heartbeat_strategy == 0 and (
                        type_name is MessageType.HEARTBEAT or type_name is MessageType.HEARTBEAT_BITMAP) and not self.__is_sending_data:
                    update_list_received = V2VHeartbeatMsg.decode_message(message,
                                                                          True if type_name is MessageType.HEARTBEAT_BITMAP else False)
                    if len(update_list_received) == 0:
                        continue
                    index_list_to_send = []
                    for received_update in update_list_received:
                        found, update_name = self.validate_update_hash(received_update)
                        if found:
                            # Valid heartbeat received via V2V
                            index_list_to_send.append((update_name, V2VHeartbeatMsg.data_indices_to_send(
                                received_update[3], self.__updates_bitmap[update_name], received_update[1])))
                    self.calculate_data_to_send(current_time, packet_rate, step_length, index_list_to_send)
                elif self.__v2v_heartbeat_strategy == 1 and (
                        type_name is MessageType.HEARTBEAT or type_name is MessageType.HEARTBEAT_BITMAP):  # counter

                    all_index_lists = []
                    for message in self.__received_v2v_heartbeat_messages:
                        index_list_to_send = self.make_index_list(message)
                        if len(index_list_to_send) != 0:
                            all_index_lists += index_list_to_send

                    # save all chunk lists to corresponding update
                    update_dict = {info[0]: [] for info in all_index_lists}
                    for info in all_index_lists:
                        update = info[0]
                        chunks = info[1]
                        update_dict[update].extend(chunks)
                    # count total occurences of chunks in received heartbeats
                    occurrence_list = []
                    for update in update_dict:
                        all_counts = Counter(update_dict[update])
                        for chunk, count_value in all_counts.most_common():
                            occurrence_list.append([update, chunk, count_value])
                    occurrence_list.sort(key=lambda x: x[2], reverse=True)
                    self.calculate_data_to_send_new(current_time, packet_rate, step_length, occurrence_list)
                    remaining_heartbeats = []
                    for heartbeat in self.__received_v2v_heartbeat_messages:
                        if heartbeat[0] < current_time - (1.0 * self.__heartbeat_interval):
                            continue
                        remaining_heartbeats.append(heartbeat)
                    self.__received_v2v_heartbeat_messages = remaining_heartbeats

                elif self.__v2v_heartbeat_strategy == 2 and (
                        type_name is MessageType.HEARTBEAT or type_name is MessageType.HEARTBEAT_BITMAP):
                    all_index_lists = []
                    for message in self.__received_v2v_heartbeat_messages:
                        index_list_to_send = self.make_index_list(message)
                        if len(index_list_to_send) != 0:
                            all_index_lists += index_list_to_send

                    # save heartbeat relevances for every update-chunk pair
                    relevance_dict = {info[0]: {} for info in all_index_lists}
                    for info in all_index_lists:
                        update = info[0]
                        for chunk in info[1]:
                            relevance_dict[update][chunk] = []
                    for info in all_index_lists:
                        relevance = info[2]
                        update = info[0]
                        for chunk in info[1]:
                            relevance_dict[update][chunk] += [relevance]

                    # save all chunk lists to corresponding update
                    update_dict = {info[0]: [] for info in all_index_lists}
                    for info in all_index_lists:
                        update = info[0]
                        chunks = info[1]
                        update_dict[update].extend(chunks)
                    # count total occurrences of chunks in received heartbeats
                    occurrence_list = []
                    for update in update_dict:
                        all_counts = Counter(update_dict[update])
                        for chunk, count_value in all_counts.most_common():
                            relevance_total = sum(relevance_dict[update][chunk]) / len(
                                relevance_dict[update][chunk])  # self.add_probabilities(relevance_dict[update][chunk])
                            occurrence_list.append([update, chunk, count_value, relevance_total])
                    occurrence_list.sort(key=lambda x: x[3], reverse=True)
                    self.calculate_data_to_send_new(current_time, packet_rate, step_length, occurrence_list)
                    remaining_heartbeats = []
                    for heartbeat in self.__received_v2v_heartbeat_messages:
                        if heartbeat[0] < current_time - (1.0 * self.__heartbeat_interval):
                            continue
                        remaining_heartbeats.append(heartbeat)
                    self.__received_v2v_heartbeat_messages = remaining_heartbeats

                elif self.__v2v_heartbeat_strategy == 3 and (
                        type_name is MessageType.HEARTBEAT or type_name is MessageType.HEARTBEAT_BITMAP):

                    all_index_lists = []
                    for message in self.__received_v2v_heartbeat_messages:
                        index_list_to_send = self.make_index_list(message)
                        if len(index_list_to_send) != 0:
                            all_index_lists += index_list_to_send

                    # save heartbeat relevance for every update-chunk pair
                    relevance_dict = {info[0]: {} for info in all_index_lists}
                    for info in all_index_lists:
                        update = info[0]
                        for chunk in info[1]:
                            relevance_dict[update][chunk] = []
                    for info in all_index_lists:
                        time = info[3]
                        update = info[0]
                        for chunk in info[1]:
                            relevance_dict[update][chunk] += [time]

                    # save all chunk lists to corresponding update
                    update_dict = {info[0]: [] for info in all_index_lists}
                    for info in all_index_lists:
                        update = info[0]
                        chunks = info[1]
                        update_dict[update].extend(chunks)
                    # count total occurrences of chunks in received heartbeats
                    occurrence_list = []
                    for update in update_dict:
                        all_counts = Counter(update_dict[update])
                        for chunk, count_value in all_counts.most_common():
                            relevance_total = sum(relevance_dict[update][chunk]) / len(
                                relevance_dict[update][chunk])  # self.add_probabilities(relevance_dict[update][chunk])
                            occurrence_list.append([update, chunk, count_value, relevance_total])
                    occurrence_list.sort(key=lambda x: x[3], reverse=False)
                    self.calculate_data_to_send_new(current_time, packet_rate, step_length, occurrence_list)
                    remaining_heartbeats = []
                    for heartbeat in self.__received_v2v_heartbeat_messages:
                        if heartbeat[0] < current_time - (1.0 * self.__heartbeat_interval):
                            continue
                        remaining_heartbeats.append(heartbeat)
                    self.__received_v2v_heartbeat_messages = remaining_heartbeats

                elif self.__v2v_heartbeat_strategy == 4 and (
                        type_name is MessageType.HEARTBEAT or type_name is MessageType.HEARTBEAT_BITMAP) and not self.__is_sending_data:
                    index_list_to_send = []
                    for update in self.__updates:
                        index_list_to_send.append((update, self.__updates[update].keys()))
                    self.calculate_data_to_send(current_time, packet_rate, step_length, index_list_to_send)

                elif self.__v2v_heartbeat_strategy == 5 and (
                        type_name is MessageType.HEARTBEAT or type_name is MessageType.HEARTBEAT_BITMAP):
                    if self.__v2v_most_relevant_heartbeat_strategy is None or (
                            self.__v2v_most_relevant_heartbeat_strategy is not None and relevance < self.__v2v_most_relevant_heartbeat_strategy):
                        self.__v2v_most_relevant_heartbeat_strategy = relevance
                        update_list_received = V2VHeartbeatMsg.decode_message(message,
                                                                              True if type_name is MessageType.HEARTBEAT_BITMAP else False)
                        if len(update_list_received) == 0:
                            continue
                        index_list_to_send = []
                        for received_update in update_list_received:
                            found, update_name = self.validate_update_hash(received_update)
                            if found:
                                # Valid heartbeat received via V2V
                                index_list_to_send.append((update_name, V2VHeartbeatMsg.data_indices_to_send(
                                    received_update[3], self.__updates_bitmap[update_name], received_update[1])))
                        self.calculate_data_to_send(current_time, packet_rate, step_length, index_list_to_send, True)
                elif self.__v2v_heartbeat_strategy == 6 and (
                        type_name is MessageType.HEARTBEAT or type_name is MessageType.HEARTBEAT_BITMAP):

                    update_list_received = V2VHeartbeatMsg.decode_message(message,
                                                                          True if type_name is MessageType.HEARTBEAT_BITMAP else False)
                    if len(update_list_received) == 0:
                        continue
                    index_list_to_send = []
                    for received_update in update_list_received:
                        found, update_name = self.validate_update_hash(received_update)
                        if found:
                            # Valid heartbeat received via V2V
                            index_list_to_send.append((update_name, V2VHeartbeatMsg.data_indices_to_send(
                                received_update[3], self.__updates_bitmap[update_name], received_update[1])))

                    self.calculate_data_to_send(current_time, packet_rate, step_length, index_list_to_send, True)

                elif type_name is MessageType.DATA:
                    received_message_list.append(message)

            if len(received_message_list) > 0:
                log_time, data_dict = self.save_received_data_bulk(received_message_list)
                for file_name in data_dict.keys():
                    if file_name not in set(log_data):
                        log_data[file_name] = []
                    for chunk_index in data_dict[file_name]:
                        log_data[file_name].append((log_time, chunk_index))
        # Use this code to save debug/result data into files
        # for file_name in log_data.keys():
        #    if file_name not in self.__files_io:
        #        self.__files_io[file_name] = open(file_name, 'a', newline='')
        # with open(file_name, 'a', newline='') as file:
        #    writer = csv.writer(self.__files_io[file_name])
        #    writer.writerows(log_data[file_name])
        # for entry in log_data[file_name]:
        #    writer.writerow(entry)

    def validate_update_hash(self, received_update: Dict) -> (bool, str):
        """
        Validate the update hash
        @param received_update Received update
        @return True if the update is contained, False otherwise and the update name
        """
        update_hash = received_update[0]
        update_name = ''
        found = False
        for update in self.__updates:
            update_name_hash = hashlib.sha224(str.encode(update)).digest()[:8]
            if update_hash == update_name_hash:
                update_name = update
                return True, update_name
        return False, None

    def __heartbeat_strategy(self, strategy: int) -> (bytearray, bool):
        """
        Generate a Heartbeat message, depending on the current Strategy
        @param strategy The integer encoded strategy
        @return byte representation of message and if the full update is encoded
        """
        byte_list = None
        update_dict = {}
        seed_index_dict = {}
        valid = True
        if strategy == 0:
            byte_list, valid = (V2VHeartbeatMsg.generate_message(self.__updates, self.__updateMetaData,
                                                                 self.__update_next_heartbeat_chunk_index,
                                                                 self.__updates_bitmap, {}, 0, "",
                                                                 self.__fleetManager.get_heartbeat_encoding()))
        elif strategy == 1 or strategy == 2 or strategy == 3 or strategy == 4:
            for update in self.__updates:
                if strategy == 1:
                    seed_index_dict[update] = 0
                    byte_list, valid = (
                        V2VHeartbeatMsg.generate_message(self.__updates, self.__updateMetaData, seed_index_dict,
                                                         self.__updates_bitmap,
                                                         self.__counter_strategy_dict, strategy, self.__vehID,
                                                         self.__fleetManager.get_heartbeat_encoding()))
                elif strategy == 2:
                    seed_index_dict[update] = 0
                    byte_list, valid = (
                        V2VHeartbeatMsg.generate_message(self.__updates, self.__updateMetaData, seed_index_dict,
                                                         self.__updates_bitmap,
                                                         self.__weighted_counter_strategy_dict, strategy, self.__vehID,
                                                         self.__fleetManager.get_heartbeat_encoding()))
                elif strategy == 3:
                    if len(self.__most_recent_heartbeat_strategy_dict[update]) == 0:
                        return self.__heartbeat_strategy(0)
                    last_heartbeat = self.__most_recent_heartbeat_strategy_dict[update].pop()
                    update_dict[update] = {}
                    seed_is_set = False
                    heartbeat_set = set(last_heartbeat)
                    update_set = set(self.__updates[update])
                    for index in range(self.__updateMetaData[update]['numberOfChunks']):
                        if not (index in heartbeat_set and index not in update_set):
                            update_dict[update][index] = 1
                        elif index in heartbeat_set and index not in update_set and not seed_is_set:
                            seed_index_dict[update] = index
                            seed_is_set = True

                    byte_list, valid = (V2VHeartbeatMsg.generate_message(update_dict, self.__updateMetaData,
                                                                         seed_index_dict, self.__updates_bitmap, {}, 0,
                                                                         "",
                                                                         self.__fleetManager.get_heartbeat_encoding()))
                elif strategy == 4:
                    seed_index_dict[update] = 0
                    byte_list, valid = (
                        V2VHeartbeatMsg.generate_message(self.__updates, self.__updateMetaData, seed_index_dict,
                                                         self.__updates_bitmap,
                                                         self.__most_requested_dict, strategy, self.__vehID,
                                                         self.__fleetManager.get_heartbeat_encoding()))

        return byte_list, valid

    def simulation_step(self, current_time: float) -> None:
        """
        Progress the Vehicle for one simulation step
        @param current_time Current time in simulation
        """
        if self.__wlan_module is not None:
            self.__wlan_module.simulation_step(current_time)
        if self.__time_last_simulation_step is None:
            self.__time_last_simulation_step = current_time
        if self.__v2v_module is not None and (current_time >= (self.__lastv2vHeartbeat + self.__heartbeat_interval)):
            self.__lastv2vHeartbeat = current_time - (
                    (current_time - self.__lastv2vHeartbeat) % self.__heartbeat_interval)
            name = self.__file_name + '_' + self.__vehID + '_' + 'heartbeat'
            if name not in self.__used_file_names:
                self.__used_file_names.add(name)
            #   Use this code to save debug/result data in files
            #   if name not in self.__files_io:
            #        self.__files_io[name] = open(name, 'a', newline='')
            # with open(name, 'a', newline='') as file:
            #    writer = csv.writer(self.__files_io[name])
            #    writer.writerow([current_time, self.__lastv2vHeartbeat])

            # Generate a new V2VHeartbeat Message
            byte_list, valid = V2VHeartbeatMsg.generate_message(self.__updates, self.__updateMetaData,
                                                                self.__update_next_heartbeat_chunk_index,
                                                                self.__updates_bitmap, {}, 0, "",
                                                                self.__fleetManager.get_heartbeat_encoding())
            if self.__wlan_heartbeat_strategy == 4 and valid:
                valid, type_name = self.check_received_message(byte_list)
                update_list_received = V2VHeartbeatMsg.decode_message(byte_list,
                                                                      True if type_name is MessageType.HEARTBEAT_BITMAP else False)
                for received_update in update_list_received:
                    update_hash = received_update[0]
                    update_name = ''
                    for update in self.__updates:
                        update_name_hash = hashlib.sha224(str.encode(update)).digest()[:8]
                        if update_hash == update_name_hash:
                            update_name = update
                            break
                for received_update in update_list_received:
                    for counter, index in enumerate(received_update[3]):
                        if counter + received_update[1] >= self.__updateMetaData[update]['numberOfChunks']:
                            chunk_index = counter + received_update[1] - self.__updateMetaData[update]['numberOfChunks']
                        else:
                            chunk_index = counter + received_update[1]
                    if not index and chunk_index in self.__most_requested_dict[update_name]:
                        self.__most_requested_dict[update_name][chunk_index] += 1
            if valid:
                self.__v2v_module.add_send_message((round(current_time, 6), byte_list), True)
            self.__backendServer.get_backend_manager().check_for_new_updates(self.__updates.keys(), self, 0)

        association = False
        if self.__wlan_module is not None and self.__wlan_module.association_triggered():
            association = True

        if self.__wlan_module is not None and (association or current_time >= (
                self.__lastwlanHeartbeat + self.__heartbeat_interval)) and current_time >= self.__last_allowed_heartbeat:

            if association:
                self.__lastwlanHeartbeat = current_time
            else:
                self.__lastwlanHeartbeat = current_time - (
                        (current_time - self.__lastwlanHeartbeat) % self.__heartbeat_interval)
            if self.__wlan_module.is_associated():
                self.__last_allowed_heartbeat = current_time + 0.0
                byte_list, valid = self.__heartbeat_strategy(self.__wlan_heartbeat_strategy)
                if valid:
                    self.__wlan_module.send_to_layer_3((current_time, byte_list))

        if not self.__initial_update_check:
            self.__backendServer.get_backend_manager().check_for_new_updates(self.__updates.keys(), self, 0)
            self.__initial_update_check = True

        self.calculate_behaviour_last_time_step(current_time, self.__step_length, self.__packet_rate)
        x = 0.0
        for update in self.__updates:
            self.__updates[update].keys()
            x = len(self.__updates[update].keys()) / self.__updateMetaData[update]['numberOfChunks']
        cmap = mpl.cm.get_cmap('hsv')
        rgba1 = cmap(0.33 * x)
        colors = [round(i * 255) for i in rgba1]
        if x == 1.0:
            colors = [0, 0, 255, 255]
        self.__sumo_interface.vehicle.setColor(self.__vehID, colors)

    def save_received_data_bulk(self, msg_list: List, backend=False) -> tuple:
        """
        Save information about multiple messages received
        For logging purposes, the behavior differs for Backend and others
        @param msg_list List of messages received
        @param backend Whether the messages were received from the backend
        @return list of messages saved
        """
        message_dict = {}
        for message in msg_list:
            if backend:
                update_name, chunk_index, update_content = message
                update_name_hash = hashlib.sha224(str.encode(update_name)).digest()[:8]
            else:
                update_name_hash, chunk_index, update_content = DataMsg.decode_message(message)
            if tuple(update_name_hash) not in message_dict:
                message_dict[tuple(update_name_hash)] = []
            message_dict[tuple(update_name_hash)].append((chunk_index, update_content))
        return_dict = {}
        for update in self.__updates:
            if update in self.__fully_received_update:
                continue
            update_hash = hashlib.sha224(str.encode(update)).digest()[:8]
            if tuple(update_hash) in message_dict.keys():
                name = self.__file_name + '_' + self.__vehID + '_' + 'update_progress' + '_' + update
                if name not in self.__used_file_names:
                    self.__used_file_names.add(name)

                indices_to_save = []
                for msg in message_dict[tuple(update_hash)]:
                    chunk_index, update_content = msg
                    self.__updates[update][chunk_index] = 1
                    self.__updates_bitmap[update][chunk_index] = 1

                    if self.__wlan_heartbeat_strategy == 1:
                        self.__counter_strategy_dict[update].pop(chunk_index, None)
                    elif self.__wlan_heartbeat_strategy == 2:
                        self.__weighted_counter_strategy_dict[update].pop(chunk_index, None)
                    elif self.__wlan_heartbeat_strategy == 4:
                        self.__most_requested_dict[update].pop(chunk_index, None)
                    indices_to_save.append(chunk_index)

                    del update_content
                if backend:
                    current_time = self.__fleetManager.get_current_time()
                    #   Use this code to save debug/result data in files
                    #  if name not in self.__files_io:
                    #      self.__files_io[name] = open(name, 'a', newline='')
                    # with open(name, 'a', newline='') as file:
                    #    writer = csv.writer(self.__files_io[name])
                    #    for chunk_index in indices_to_save:
                    #        writer.writerow([current_time, chunk_index])
                else:
                    return_dict[name] = indices_to_save

            all_keys = self.__updates[update].keys()
            if len(all_keys) == self.__updateMetaData[update]['numberOfChunks']:
                self.__fully_received_update.add(update)

            for index in range(self.__updateMetaData[update]['numberOfChunks']):
                if index not in all_keys:
                    self.__update_next_heartbeat_chunk_index[update] = index
                    break
        if not backend:
            return self.__fleetManager.get_current_time(), return_dict

    def save_message_by_index(self, msg_list):
        """
        Save messages by providing an index list
        @param msg_list: Indices of messages to save
        @return:
        """
        for update in self.__updates:
            if update in self.__fully_received_update:
                continue
            if True:  # tuple(update_hash) in message_dict_set:
                name = self.__file_name + '_' + self.__vehID + '_' + 'update_progress' + '_' + update
                if name not in self.__used_file_names:
                    self.__used_file_names.add(name)

                indices_to_save = []

                for msg in msg_list:
                    chunk_index = msg
                    self.__updates[update][chunk_index] = 1  # chunk
                    self.__updates_bitmap[update][chunk_index] = 1

                    if self.__wlan_heartbeat_strategy == 1:
                        self.__counter_strategy_dict[update].pop(chunk_index, None)
                    elif self.__wlan_heartbeat_strategy == 2:
                        self.__weighted_counter_strategy_dict[update].pop(chunk_index, None)
                    elif self.__wlan_heartbeat_strategy == 4:
                        self.__most_requested_dict[update].pop(chunk_index, None)
                    indices_to_save.append(chunk_index)
                    # del update_content

                current_time = self.__fleetManager.get_current_time()
                #   Use this code to save debug/result data in files
                #   if name not in self.__files_io:
                #       self.__files_io[name] = open(name, 'a', newline='')
                # with open(name, 'a', newline='') as file:
                #    writer = csv.writer(self.__files_io[name])
                save = [[current_time, chunk_index] for chunk_index in indices_to_save]
            #    writer.writerows(save)
            # for chunk_index in indices_to_save:
            #    writer.writerow([current_time, chunk_index])

            all_keys = self.__updates[update].keys()
            if len(all_keys) == self.__updateMetaData[update]['numberOfChunks']:
                self.__fully_received_update.add(update)
            for index in range(self.__updateMetaData[update]['numberOfChunks']):
                if index not in all_keys:  # self.__updates[update].keys():
                    self.__update_next_heartbeat_chunk_index[update] = index
                    break

    def receive_meta_data(self, update_message: bytearray) -> None:
        """
        Receive meta data message aka Update Initialization Message
        @param update_message Update Message Bytes
        """
        update_name, update_size, due_date, update_hash = UpdateInitMsg.decode(update_message)
        data = dict()
        data['size'] = update_size
        number_of_chunks = int(update_size / self.__chunkSize)
        if update_size % self.__chunkSize != 0:
            number_of_chunks += 1
        data['numberOfChunks'] = number_of_chunks
        data['update_name'] = update_name
        data['due_date'] = due_date
        data['update_hash'] = update_hash
        self.__updates[update_name] = {}
        tmp = bitarray.bitarray(number_of_chunks)
        tmp.setall(0)
        self.__updates_bitmap[update_name] = tmp
        self.__update_next_heartbeat_chunk_index[update_name] = 0

        self.__updateMetaData[update_name] = data
        if self.__wlan_heartbeat_strategy == 1:
            self.__counter_strategy_dict[update_name] = {}
        elif self.__wlan_heartbeat_strategy == 2:
            self.__weighted_counter_strategy_dict[update_name] = {}
        elif self.__wlan_heartbeat_strategy == 3:
            self.__most_recent_heartbeat_strategy_dict[update_name] = []
        elif self.__wlan_heartbeat_strategy == 4:
            self.__most_requested_dict[update_name] = {}
        for index in range(number_of_chunks):
            if self.__wlan_heartbeat_strategy == 1:
                self.__counter_strategy_dict[update_name][index] = 0
            elif self.__wlan_heartbeat_strategy == 2:
                self.__weighted_counter_strategy_dict[update_name][index] = {"counter": 0, "avg": 0}
            elif self.__wlan_heartbeat_strategy == 4:
                self.__most_requested_dict[update_name][index] = 0

    def set_backend_server(self, backend_server: object) -> None:
        """
        Set the Backend
        @param backend_server  server instance
        """
        self.__backendServer = backend_server

    def set_routes(self, route_list: List[str]) -> None:
        """
        Set the route list as route list of Vehicle
        @param route_list List of routes
        """
        self.__routes = route_list
        self.__currentRoute = route_list[0]
        self.__remainingRouteList = route_list[1:]

    def get_current_route(self) -> str:
        """
        Get the current route
        @return Name of current route
        """
        return self.__currentRoute

    def get_veh_id(self) -> str:
        """
        Get Vehicle ID
        @return Vehicle ID
        """
        return self.__vehID

    def is_on_road(self) -> bool:
        """
        Is the vehicle currently on the road in the simulation
        @return True if the Vehicle is in the simulation, False otherwise
        """
        return self.__onRoad

    def register_at_backend(self) -> None:
        """
        Register the Vehicle at the Backend.
        """
        self.__backendServer.register(self)

    def set_departed(self, current_time: float) -> None:
        """
        Set the status of the Vehicle as departed if it started driving in the simulation.
        @param current_time The current simulation time
        """
        self.__onRoad = True
        name = self.__file_name + '_' + self.__vehID + '_' + 'simulation_departed'
        if name not in self.__used_file_names:
            self.__used_file_names.add(name)
        #   Use this code to save debug/result data in files
        #  if name not in self.__files_io:
        #      self.__files_io[name] = open(name, 'a', newline='')
        #  with open(name, 'a', newline='') as file:
        #      writer = csv.writer(self.__files_io[name])
        #      writer.writerow([current_time])
        if self.__firstAdd:
            self.__firstAdd = False
            self.register_at_backend()

    def set_scheduled(self) -> None:
        """
        Set the Vehicle status as scheduled for departure.
        """
        self.__scheduled = True

    def is_scheduled(self) -> bool:
        """
        Is the Vehicle scheduled for departure.
        @return True if the Vehicle is scheduled for departure, False otherwise
        """
        return self.__scheduled

    def set_arrived(self, current_time: float) -> None:
        """
        Set the vehicle status as arrived.
        @param current_time The current simulation time
        """
        self.__onRoad = False
        self.__scheduled = False
        if self.__wlan_module is not None:
            self.__wlan_module.reset()
        name = self.__file_name + '_' + self.__vehID + '_' + 'simulation_arrived'
        if name not in self.__used_file_names:
            self.__used_file_names.add(name)
        #   Use this code to save debug/result data in files
        #   if name not in self.__files_io:
        #       self.__files_io[name] =  open(name, 'a', newline='')
        #    with open(name, 'a', newline='') as file:
        #       writer = csv.writer(self.__files_io[name])
        #       writer.writerow([current_time])
        if self.has_next_route():
            self.__nextRouteStart = current_time
            print(self.__nextRouteStart, current_time)
        for update in self.__updates:
            print(self.__vehID, "Update", update, "Number of chunks", len(self.__updates[update].keys()),
                  len(self.__updates[update].keys()) / self.__updateMetaData[update]['numberOfChunks'] * 100,
                  'Percent Routes remaining:', len(self.__remainingRouteList))

    def has_next_route(self) -> bool:
        """
        Check if the Vehicle has next route.
        @return True if the Vehicle has next route, False otherwise
        """
        return True if len(self.__remainingRouteList) > 0 else False

    def update_route(self) -> str:
        """
        Update the route of the Vehicle
        @return The current route of the Vehicle
        """
        if self.has_next_route():
            self.__currentRoute = self.__remainingRouteList[0]
            if len(self.__remainingRouteList) > 1:
                self.__remainingRouteList = self.__remainingRouteList[1:]
            else:
                self.__remainingRouteList = []
        return self.__currentRoute

    def get_next_route_start(self) -> float:
        """
        Get the time of the next route start.
        @return Time of route start
        """
        return self.__nextRouteStart

    def get_used_file_names(self) -> Set[str]:
        """
        Get the used file names for the Vehicle
        @return List of used file names
        """
        return self.__used_file_names

    def set_used_file_names(self, file_names: List) -> None:
        """
        Set the list of used file names
        @param file_names List of file names
        """
        self.__used_file_names = file_names

    def progress_rate(self) -> float:
        """
        Calculate the current downloading progress
        """
        for update in self.__updates:
            all_keys = self.__updates[update].keys()
            return len(all_keys) / self.__updateMetaData[update]['numberOfChunks']

    def getUpdate(self):
        """
        Get all updates
        @return List of all updates
        """
        return self.__updates

    def getMetaUpdate(self):
        """
        Get all update meta data
        @return List of all update meta data
        """
        return self.__updateMetaData

    def get_fleet_manager(self):
        """
        Get fleet manager of vehicle
        @return Fleet manager
        """
        return self.__fleetManager

    def get_packet_rate(self):
        """
        Get data rate
        @return Data rate
        """
        return self.__packet_rate

    def compute_observation(self):
        """
        Calculates the observation for RL
        @return Current time
        """

        return int(self.__fleetManager.get_current_time() * 10.0)

    def compute_reward(self) -> float:
        """
        Calculate the reward
        @return Reward of last action
        """
        return self.__reward_last_action

    def apply_action(self, action: int) -> None:
        """
        Applies an action in RL
        @param action The action to take
        """
        action = action * 100

        for update in self.__updates:
            given_action = action
            if action > self.__updates_bitmap[update].count(0):
                action = self.__updates_bitmap[update].count(0)

            chunk_indices = self.__backendServer.get_backend_manager().get_chunks(update, self.__updates_bitmap[update],
                                                                                  action)

            self.__reward_last_action = given_action * -1
            self.save_message_by_index(chunk_indices)

    def remaining_chunks(self) -> (int, int):
        """
        Returns the progress of the update
        @return Length of update and count of non-available chunks
        """
        for update in self.__updates:
            return len(self.__updates_bitmap[update]), self.__updates_bitmap[update].count(0)

    def get_remaining_chunks(self, update: str) -> List:
        """
        Retrieves the remaining chunks
        @param update The update name
        @return List of remaining chunk indices
        """
        return list(
            set(range(self.__updateMetaData[update]['numberOfChunks'])).difference(set(self.__updates[update].keys())))

    def update_done(self):
        """
        Returns whether the update is done
        @return True if the update is fully received, False otherwise
        """
        return True if len(self.__fully_received_update) > 0 else False

    def seeding_step(self, current_time: float, seed_number: int) -> int:
        """
        Progress the Vehicle for one simulation step with seeding, HELPER for RL
        @param current_time Current time in simulation
        @param seed_number Number of chunks that get seeded
        @return Number of seeded chunks
        """
        if self.__time_last_simulation_step is None:
            self.__time_last_simulation_step = current_time
        if self.__v2v_module is not None and (current_time >= (self.__lastv2vHeartbeat + self.__heartbeat_interval)):
            self.__lastv2vHeartbeat = current_time - (
                        (current_time - self.__lastv2vHeartbeat) % self.__heartbeat_interval)
            name = self.__file_name + '_' + self.__vehID + '_' + 'heartbeat'
            if name not in self.__used_file_names:
                self.__used_file_names.add(name)
            #   Use this code to save debug/result data in files
            # with open(name, 'a', newline='') as file:
            #    writer = csv.writer(file)
            #    writer.writerow([current_time, self.__lastv2vHeartbeat])
            # Generate a new V2VHeartbeat Message
            byte_list, valid = V2VHeartbeatMsg.generate_message(self.__updates, self.__updateMetaData,
                                                                self.__update_next_heartbeat_chunk_index,
                                                                self.__updates_bitmap, {}, 0, "",
                                                                self.__fleetManager.get_heartbeat_encoding())
            if self.__fleetManager.get_v2v_heartbeat_strategy() == 4 and valid:
                valid, type_name = self.check_received_message(byte_list)
                update_list_received = V2VHeartbeatMsg.decode_message(byte_list,
                                                                      True if type_name is MessageType.HEARTBEAT_BITMAP else False)
                for received_update in update_list_received:
                    update_hash = received_update[0]
                    update_name = ''
                    for update in self.__updates:
                        update_name_hash = hashlib.sha224(str.encode(update)).digest()[:8]
                        if update_hash == update_name_hash:
                            update_name = update
                            break
                for received_update in update_list_received:
                    for counter, index in enumerate(received_update[3]):
                        if counter + received_update[1] >= self.__updateMetaData[update]['numberOfChunks']:
                            chunk_index = counter + received_update[1] - self.__updateMetaData[update]['numberOfChunks']
                        else:
                            chunk_index = counter + received_update[1]
                    if not index and chunk_index in self.__most_requested_dict[update_name]:
                        self.__most_requested_dict[update_name][chunk_index] += 1
            if valid:
                self.__v2v_module.add_send_message((round(current_time, 6), byte_list), True)
        print(self.__initial_update_check, "seeding_step")
        if not self.__initial_update_check:
            loaded_chunks = self.__backendServer.get_backend_manager().check_for_new_updates(self.__updates.keys(),
                                                                                             self, seed_number)
            self.__initial_update_check = True
        else:
            loaded_chunks = self.__backendServer.get_backend_manager().seeder(self, seed_number)

        self.calculate_behaviour_last_time_step(current_time, self.__step_length, self.__packet_rate)
        return loaded_chunks

    def __init__(self, veh_id: str, fleet_manager: object, file_name: str) -> None:
        """
        Generate a new Vehicle
        @param veh_id Vehicle ID
        @param fleet_manager Fleet Manager
        @param file_name File name of simulation
        """
        self.__v2v_most_relevant_heartbeat_strategy = None
        self.__routes = []
        self.__vehID = veh_id
        self.__file_name = file_name
        self.__updates = {}
        self.__updates_bitmap = {}
        self.__fully_received_update = set()
        self.__routeList = []
        self.__currentTravelEdges = ()
        self.__currentRoute = None
        self.__onRoad = False
        self.__remainingRouteList = []
        self.__nextRouteStart = 0.0
        self.__scheduled = False
        self.__backendServer = None
        self.__firstAdd = True
        self.__fleetManager = fleet_manager
        self.__lastBackendHeartbeat = None
        self.__updateMetaData = {}
        self.__lastwlanHeartbeat = 0.0
        self.__time_last_simulation_step = None
        self.__is_sending_data = False
        self.__last_scheduled_data_packet = 0.0
        self.__received_v2v_heartbeat_messages = []
        self.__update_next_heartbeat_chunk_index = {}
        self.__chunkSize = self.__fleetManager.get_backend_server().get_chunk_size()
        self.__used_file_names = set()
        self.__initial_update_check = False
        self.__current_wlan_ap = None
        self.__sumo_interface = fleet_manager.get_traci()
        self.__step_length = self.__sumo_interface.simulation.getDeltaT()
        self.__packet_size = 1500  # byte
        self.__heartbeat_interval = self.__fleetManager.get_v2v_heartbeat_interval()  # 10.0  # seconds
        self.__lastv2vHeartbeat = - (random.random() * self.__heartbeat_interval)
        self.__data_rate = self.__fleetManager.get_v2v_data_rate()  # Byte/s
        self.__packet_rate = (self.__data_rate * self.__step_length) / self.__packet_size
        self.__packets_per_heartbeat_interval = (self.__data_rate / self.__packet_size) * self.__heartbeat_interval
        self.__wlan_module = WLANModuleVehicle.WLANModuleVehicle(self.__vehID, self.__file_name,
                                                                 self) if self.__fleetManager.get_wlan_device(
            veh_id) else None
        self.__v2v_module = V2VModuleVehicle.V2VModuleVehicle(self.__vehID, self.__file_name,
                                                              self,
                                                              self.__packets_per_heartbeat_interval) if self.__fleetManager.get_v2v_device(
            veh_id) else None
        self.__v2v_heartbeat_strategy = self.__fleetManager.get_v2v_heartbeat_strategy()
        self.__wlan_heartbeat_strategy = self.__fleetManager.get_wlan_heartbeat_strategy()
        if self.__wlan_heartbeat_strategy == 1:
            self.__counter_strategy_dict = {}
        elif self.__wlan_heartbeat_strategy == 2:
            self.__weighted_counter_strategy_dict = {}
        elif self.__wlan_heartbeat_strategy == 3:
            self.__most_recent_heartbeat_strategy_dict = {}
        elif self.__wlan_heartbeat_strategy == 4:
            self.__most_requested_dict = {}
            self.__most_requested_dict = {}
        self.__last_allowed_heartbeat = 0.0
        self.__reward_last_action = 0
        self.__last_done_progress = False
        self.__files_io = {}
        self.__remaining_update_list = {}

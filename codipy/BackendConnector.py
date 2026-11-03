import struct
from typing import List
import V2VHeartbeatMsg
import hashlib
from bitarray import bitarray
import DataMsg
import copy
import random
import sys

from MessageType import MessageType


class BackendConnector:
    """
    @brief BackendConnector for WLAN APs
    @author Michael Niebisch
    @bug No known bugs

    Class defining a backend connector for WLAN APs.
    Is ONLY needed for WLAN communication

    """

    def incoming_messages(self, msg) -> None:
        """
        Adds an incoming message
        @param msg Message to be added
        """
        self.__incoming_messages.append(msg)

    def get_send_queue(self, current_time: float, time_step: float) -> List:
        """
        Returns the current send queue
        @param current_time Current time in simulation
        @param time_step Time step in simulation
        @return List of next messages to be sent
        """
        result_list = []
        counter = 0

        for entry in sorted(self.__outgoing_messages, key=lambda x: x[0]):
            counter += 1
            if current_time >= entry[0] >= current_time - time_step:
                result_list.append(copy.copy(entry))
                self.__outgoing_messages.remove(entry)
            elif entry[0] < current_time - time_step:
                self.__outgoing_messages.remove(entry)

        return result_list

    def calculate_data_to_send(self, current_time: float, packet_rate: float, step_length: float,
                               index_list_to_send: List[tuple]) -> None:
        """
        Generates data messages that are to be sent next.

        @bug Currently schedules enough packets for 10 seconds (implicitly the heartbeat interval)
        @param current_time: The current simulation time
        @param packet_rate: The packet rate
        @param step_length: The simulation step length
        @param index_list_to_send: Update and chunk indices to be sent
        """
        time_step_between_packets = step_length / packet_rate
        packets_to_send = int(10.0 / time_step_between_packets)
        send_time = current_time
        updates = set(self.__backend.get_backend_manager().get_updates())
        for info in index_list_to_send:
            update = info[0]
            indices = set(info[1])
            if update not in updates:
                continue
            number = min(int(packets_to_send), len(indices))
            random_chunks = random.sample(sorted(indices), number)
            for chunk in random_chunks:
                self.__outgoing_messages.append(
                    (send_time, DataMsg.generate_message(updates, update, chunk), self.__input))
                send_time += time_step_between_packets

    @staticmethod
    def check_received_message(msg: bytearray) -> (bool, MessageType):
        """
        Check if the hash value of the received message is correct and return the message type

        @bug Hash check is removed for faster calculation times, as hash is currently always correct.
        @param msg: bytearray of the received message
        @return True if the hash value is correct, False otherwise and the MessageType
        """
        # As the hash is never altered, the calculation time is reduced
        # if msg[-28:] != hashlib.sha224(msg[:-28]).digest():
        #    return False, None
        return True, MessageType(struct.unpack('<I', msg[:1] + struct.pack('<I', 1)[1:])[0])

    def simulation_step(self, current_time: int) -> None:
        """
        Performs one simulation step in the BackendConnector

        @bug Currently no WLAN Heartbeat strategies are used, to enable them, change this function.
        @param current_time Current time in the simulation
        """
        for msg in self.__incoming_messages:
            valid, type_name = self.check_received_message(msg[1])
            if not valid:
                continue
            update_list_received = V2VHeartbeatMsg.decode_message(msg[1], True if type_name is MessageType.HEARTBEAT_BITMAP else False)
            if len(update_list_received) == 0:
                continue
            index_list_to_send = []
            index_list_to_send_test = []
            for received_update in update_list_received:
                update_hash = received_update[0]
                update_name = ''
                found = False
                updates = self.__backend.get_backend_manager().get_updates()
                for update in updates:
                    update_name_hash = hashlib.sha224(str.encode(update)).digest()[:8]
                    if update_hash == update_name_hash:
                        update_name = update
                        found = True
                        break
                if found:
                    number_of_chunks = self.__backend.get_backend_manager().get_number_of_chunks(update_name)
                    #wlan_heartbeat_strategy = self.__backend.get_wlan_heartbeat_strategy()
                    bitmask = bitarray(number_of_chunks)
                    bitmask.setall(1)
                    # change if wlan strategies are to be used
                    if True: #wlan_heartbeat_strategy == 0:
                        index_list_to_send.append((update_name, V2VHeartbeatMsg.data_indices_to_send(
                            received_update[3], bitmask, received_update[1])))
                    elif wlan_heartbeat_strategy == 1 or wlan_heartbeat_strategy == 2 or wlan_heartbeat_strategy == 3 or wlan_heartbeat_strategy == 4:
                        heartbeat_length = len(received_update[3])
                        vehicle_length = len(bitmask)
                        remaining_length = len(bitmask[received_update[1]:])

                        if remaining_length >= heartbeat_length:
                            temp_1 = received_update[3] ^ bitmask[
                                                         received_update[1]:received_update[1] + len(received_update[3])]
                            #print("Temp_1", temp_1)
                            bitmask_zero = bitarray(number_of_chunks)
                            bitmask_zero.setall(0)
                            final_bitmask = bitmask_zero[:received_update[1]]
                            final_bitmask.extend(temp_1)
                            final_bitmask.extend(bitmask_zero[received_update[1] + len(received_update[3]):])
                            #print(len(temp_1), len(final_bitmask), received_update[1])
                            index_list_to_send_test.append((update_name, V2VHeartbeatMsg.data_indices_to_send(
                                received_update[3], bitmask, received_update[1])))
                            index_list_to_send.append((update_name, V2VHeartbeatMsg.data_indices_to_send(
                                received_update[3], final_bitmask, received_update[1])))
                            if len(set(index_list_to_send[0][1]) ^ set(index_list_to_send_test[0][1])) > 0:
                                print("case 1")
                                print("random list", index_list_to_send_test)
                                print("alternative list", index_list_to_send)
                                print("Heartbeat", received_update[3])
                                print("final", final_bitmask)
                                print(set(index_list_to_send[0][1]) ^ set(index_list_to_send_test[0][1]))
                        else:
                            bitmask2 = bitmask[received_update[1]:]
                            left_length = heartbeat_length - len(bitmask2)
                            bitmask2.extend(bitmask[:left_length])
                            temp_1 = received_update[3] ^ bitmask2
                            final_bitmask = temp_1[-left_length:]
                            bitmask_zero = bitarray(number_of_chunks)
                            bitmask_zero.setall(0)
                            #final_bitmask = bitmask_zero[:received_update[1]]
                            final_bitmask.extend(bitmask_zero[left_length:received_update[1]])
                            final_bitmask.extend(temp_1[:-left_length])
                            index_list_to_send_test.append((update_name, V2VHeartbeatMsg.data_indices_to_send(
                                received_update[3], bitmask, received_update[1])))
                            index_list_to_send.append((update_name, V2VHeartbeatMsg.data_indices_to_send(
                                received_update[3], final_bitmask, received_update[1])))

            self.calculate_data_to_send(current_time, self.__rate, self.__step_length, index_list_to_send)
        self.__incoming_messages = []


    def __init__(self, backend, input, rate, step_length):
        """
        Initializes the BackendConnector
        @param backend Backend to connect to
        @param input Source of input
        @param rate Send rate to be used
        @param step_length Length of one simulation step
        """
        self.__backend = backend
        self.__input = input
        self.__rate = rate
        self.__step_length = step_length
        self.__incoming_messages = []
        self.__outgoing_messages = []

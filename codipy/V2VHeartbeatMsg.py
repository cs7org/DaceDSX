import math
import random
from typing import List
import rle_generation
import bitarray
import bitarray.util as bitutil
import hashlib
import struct


def generate_message(update_dict: dict, update_metadata_dict: dict, update_next_heartbeat_chunk_index_dict: dict,
                     update_bitmap, metric_dict: dict = {}, heartbeat_strategy=0, veh="", bitmask=0) -> (
        bytearray, bool):
    """
    Generate a V2V Heartbeat Message
    @param update_dict Dict of all updates
    @param update_metadata_dict Metadata dict of updates
    @param update_next_heartbeat_chunk_index_dict Dict of smallest index of chunks per update
    @param update_bitmap Bitmask of update
    @param metric_dict Metric
    @param heartbeat_strategy Heartbeat Strategy
    @param veh Name of Vehicle
    @param bitmask The Bitmask
    @return The encoded heartbeat message, boolean if the full update was already received
    """
    message_length = 1452  # remaining length of 1500 byte packet with 40 byte IPv6 and 8 byte UDP Header
    hash_value_length = 28
    length_field = 2
    message_type_length = 1
    update_name_hash_length = 8
    initial_chunk_index_length = 4
    # calculate the length left for data
    remaining_length = message_length - message_type_length - update_name_hash_length \
                       - initial_chunk_index_length - length_field - hash_value_length
    message_bytes = bytearray()
    if bitmask == 2:
        for update in update_dict:
            a = float(update_metadata_dict[update]['numberOfChunks'])
            lower_switching_point = 0.25 * (2 * a - math.sqrt(3) * a)
            higher_switching_point = 0.25 * (2 * a + math.sqrt(3) * a)
            available_chunk_number = len(update_dict[update].keys())
            epsilon = 0.1 * a
            if available_chunk_number < (lower_switching_point - epsilon) or available_chunk_number > (
                    higher_switching_point + epsilon):
                # only rle
                bitmask = 0
            elif available_chunk_number > (lower_switching_point + epsilon) and available_chunk_number < (
                    higher_switching_point - epsilon):
                # only bitmask
                bitmask = 1
            else:
                # both
                bitmask = 2

    if bitmask == 0:
        message_type = struct.pack('<I', 1)[:1]
        message_bytes.extend(message_type)
    elif bitmask == 1:
        message_type = struct.pack('<I', 4)[:1]
        message_bytes.extend(message_type)

    counter = 0
    full_update_counter = 0
    # if we have more than one update, we can still use one message
    for update in update_dict:
        counter += 1
        # check if we have already received the full update
        if len(update_dict[update].keys()) == update_metadata_dict[update]['numberOfChunks'] or \
                update_next_heartbeat_chunk_index_dict[update] == -1:  # full update received
            full_update_counter += 1
            continue
        update_name_hash = hashlib.sha224(str.encode(update)).digest()[:8]
        if bitmask == 0 or bitmask == 1:
            message_bytes.extend(update_name_hash)
        if bitmask == 1:
            run_length_encoded_bitmask, starting_chunk, number_missing = get_random_range_of_bitarray(
                update_bitmap[update], min(remaining_length * 8, update_metadata_dict[update]['numberOfChunks']),
                update_metadata_dict[update]['numberOfChunks'])
        elif bitmask == 0:
            # Generate the run length encoded bitmask
            if heartbeat_strategy != 0:
                run_length_encoded_bitmask, starting_chunk = generate_rle_metric(update_dict, update,
                                                                                 update_metadata_dict[update][
                                                                                     'numberOfChunks'],
                                                                                 remaining_length,
                                                                                 update_next_heartbeat_chunk_index_dict[
                                                                                     update],
                                                                                 set(), metric_dict[update],
                                                                                 heartbeat_strategy, veh)
            else:
                run_length_encoded_bitmask, starting_chunk, number_missing = rle_generation.generate_rle(
                    update_bitmap[update], update_metadata_dict[update]['numberOfChunks'],
                    remaining_length)
        elif bitmask == 2:

            run_length_encoded_bitmask_b, starting_chunk_b, number_missing_b = get_random_range_of_bitarray(
                update_bitmap[update], min(remaining_length * 8, update_metadata_dict[update]['numberOfChunks']),
                update_metadata_dict[update]['numberOfChunks'])
            run_length_encoded_bitmask_r, starting_chunk_r, number_missing_r = rle_generation.generate_rle(
                update_bitmap[update], update_metadata_dict[update]['numberOfChunks'], remaining_length)

            if number_missing_b > number_missing_r:
                message_type = struct.pack('<I', 4)[:1]
                message_bytes.extend(message_type)
                message_bytes.extend(update_name_hash)
                run_length_encoded_bitmask, starting_chunk = run_length_encoded_bitmask_b, starting_chunk_b
            else:
                message_type = struct.pack('<I', 1)[:1]
                message_bytes.extend(message_type)
                message_bytes.extend(update_name_hash)
                run_length_encoded_bitmask, starting_chunk = run_length_encoded_bitmask_r, starting_chunk_r

        initial_chunk_index = struct.pack('<I', starting_chunk)
        message_bytes.extend(initial_chunk_index)
        # More encoded data left, than space. Simply cut the length and finish
        if len(run_length_encoded_bitmask) > remaining_length:
            run_length_encoded_bitmask = run_length_encoded_bitmask[:remaining_length]
            message_bytes.extend(struct.pack('<H', len(run_length_encoded_bitmask)))
            message_bytes.extend(run_length_encoded_bitmask)
            break
        # The encoded data fits into the remaining space
        elif len(run_length_encoded_bitmask) <= remaining_length:
            message_bytes.extend(struct.pack('<H', len(run_length_encoded_bitmask)))
            message_bytes.extend(run_length_encoded_bitmask)
            remaining_length = remaining_length - len(
                run_length_encoded_bitmask) - update_name_hash_length - initial_chunk_index_length - length_field
            # add info of another update if enough space is left
            if len(message_bytes) + 15 <= (message_length - hash_value_length):
                continue
            else:
                break
    # Add null bytes to always use the same message length
    if len(message_bytes) < (message_length - hash_value_length):
        diff = (message_length - hash_value_length) - len(message_bytes)
        for i in range(diff):
            message_bytes.extend(struct.pack('<B', 0))
    # Calculate the hash value of the message
    hash_value = hashlib.sha224(message_bytes).digest()
    message_bytes.extend(hash_value)
    return message_bytes, True if full_update_counter != len(update_dict.keys()) else False


def get_random_range_of_bitarray(update: bitarray, number_bits: int, len_update: int) -> bitarray:
    """
    Get a random range of length number_bits from the update bitarray
    @param update The bitarray representation of the update
    @param number_bits The size of the range
    @param len_update The full length of the update
    @return A number_bits long range of the full update with random starting point
    """
    bitarray_input = update
    start_index = int(random.random() * len_update)
    while number_bits % 8 != 0:
        number_bits -= 1
    if start_index + number_bits > len_update:
        return_value = bitarray_input[start_index:]
        return_value.extend(bitarray_input[:number_bits - len(return_value)])
        return bytearray.fromhex(bitutil.ba2hex(return_value)), start_index, return_value.count(0)
    else:
        return bytearray.fromhex(
            bitutil.ba2hex(bitarray_input[start_index:start_index + number_bits])), start_index, bitarray_input[
                                                                                                 start_index:start_index + number_bits].count(
            0)


def generate_rle_metric(update_dict: dict, update_name: str, number_of_chunks: int, remaining_length: int,
                        seed: int = 0, missing_chunks: set = {}, strategy_metric=dict, heartbeat_strategy=0,
                        veh="") -> (bytearray, int):
    """
    Use Run Length Encoding to encode the status of update chunks.
    The first bit in a byte is used as MSB. A MSB == 1 indicates a sequence of available chunks, a MSB == 0 indicates
        a sequence of missing chunks. The 7 remaining bits are used to save a number between 0 and 127, corresponding to
        a length of 1 to 128 chunks.
    @bug This method is only used, when other heartbeat strategies are used. If this is desired, the use of this method
    should be re-done as the performance is low
    @param update_dict Dict of all updates
    @param update_name Name of update
    @param number_of_chunks number of chunks
    @param remaining_length number of bytes left in message
    @param seed starting chunk
    @param missing_chunks Set of missing chunks
    @param strategy_metric The strategy metric dictionary
    @param heartbeat_strategy The heartbeat strategy
    @param veh The Vehicle
    @return encoded data in bytearray, index of starting chunk
    """
    sequence = set(update_dict[update_name].keys())
    encoded_bytes2 = bytearray()
    running_available, running_missing = False, False
    current_counter = 0
    starting_chunk = 0  # starting_chunk = seed #int(random.choice(list(missing_chunks)))
    chunk = starting_chunk
    index = 0
    metric_list = []
    metric_index_list = []
    tmp_metric_list = []
    current_weight = 0.0
    tmp_dict = {}
    if heartbeat_strategy == 2:
        for index in strategy_metric:
            tmp_dict[index] = strategy_metric[index]["avg"]
        strategy_metric = tmp_dict
    while True:

        if chunk in sequence:

            if running_available:
                current_counter += 1
                tmp_metric_list.append(0.0)
            else:
                number_of_full_bytes, remaining_number = divmod(current_counter, 128)

                for j in range(number_of_full_bytes):
                    metric_list.append(sum(tmp_metric_list[j * 128:(j + 1) * 128]))
                    metric_index_list.append(chunk - current_counter + j * 128)
                    encoded_bytes2.append(127)
                if remaining_number != 0:
                    metric_list.append(sum(tmp_metric_list[number_of_full_bytes * 128:]))
                    metric_index_list.append(chunk - remaining_number)
                    encoded_bytes2.append((remaining_number - 1) + 0)

                tmp_metric_list = [0.0]
                running_available = True
                running_missing = False
                current_counter = 1
        else:
            if running_missing:
                current_counter += 1
                tmp_metric_list.append(strategy_metric[chunk])
            else:
                number_of_full_bytes, remaining_number = divmod(current_counter, 128)
                for j in range(number_of_full_bytes):
                    metric_list.append(sum(tmp_metric_list[j * 128:(j + 1) * 128]))
                    metric_index_list.append(chunk - current_counter + j * 128)
                    encoded_bytes2.append(255)
                if remaining_number != 0:
                    metric_list.append(sum(tmp_metric_list[number_of_full_bytes * 128:]))
                    metric_index_list.append(chunk - remaining_number)
                    encoded_bytes2.append((remaining_number - 1) + 128)
                tmp_metric_list = [strategy_metric[chunk]]
                running_missing = True
                running_available = False
                current_counter = 1
        chunk += 1
        if chunk >= number_of_chunks:
            break

    number_of_full_bytes, remaining_number = divmod(current_counter, 128)
    for j in range(number_of_full_bytes):
        metric_list.append(sum(tmp_metric_list[j * 128:(j + 1) * 128]))
        metric_index_list.append(chunk - current_counter + j * 128)
        encoded_bytes2.append(127 if not running_available else 255)
    if remaining_number != 0:
        metric_list.append(sum(tmp_metric_list[number_of_full_bytes * 128:]))
        metric_index_list.append(chunk - remaining_number)
        encoded_bytes2.append((remaining_number - 1) + (128 if running_available else 0))

    current_sum = 0.0
    max_sum = 0.0
    max_sum_index = 0
    additional = min(remaining_length, len(metric_list))
    for i in range(len(metric_list) + additional):
        if i < additional:
            current_sum += metric_list[i]
        elif i >= additional and i < len(metric_list):
            current_sum += metric_list[i]
            current_sum -= metric_list[i - additional]
        else:
            current_sum += metric_list[i % len(metric_list)]
            current_sum -= metric_list[i - additional]

        if current_sum >= max_sum:
            max_sum = current_sum
            max_sum_index = (i - additional) % len(metric_list)

    if max_sum_index + additional <= len(encoded_bytes2):
        return encoded_bytes2[max_sum_index:max_sum_index + additional], metric_index_list[max_sum_index]
    else:
        res = encoded_bytes2[max_sum_index:]
        res.extend(encoded_bytes2[:additional - (len(encoded_bytes2) - max_sum_index)])
        return res, metric_index_list[max_sum_index]


def decode_update(message_bytes: bytearray) -> (bytearray, int, int, bytearray):
    """
    Decode an update
    @param message_bytes The message bytes
    @return Decoded hash, starting chunk index, length field value and data
    """
    update_hash = message_bytes[:8]  # hashlib.sha224(str.encode(update)).digest()[:16]
    chunk_index = message_bytes[8:12]
    len_field = message_bytes[12:14]
    rle_data = message_bytes[14:14 + struct.unpack('<H', len_field)[0]]
    return update_hash, struct.unpack('<I', chunk_index)[0], struct.unpack('<H', len_field)[0], rle_data


def decode_message(message_bytes: bytearray, bitmask=False) -> List:
    """
    Decode a Heartbeat message
    @param message_bytes The byte representation of the message
    @param bitmask Flag if the Heartbeat message is bitmask encoded
    @return list of all update infos with content
    """
    if message_bytes[-28:] != hashlib.sha224(message_bytes[:-28]).digest():
        return
    message_bytes = message_bytes[1:]
    offset = 0

    update_list = []
    while True:
        len_field = struct.unpack('<H', message_bytes[12 + offset:14 + offset])[0]

        if len_field != 0:
            update, index, length, rle_data = decode_update(message_bytes[0 + offset: 14 + len_field + offset])
            if not bitmask:
                update_list.append((update, index, length, decode_message_to_bitmask(rle_data)))
            else:
                update_list.append((update, index, length, bitutil.hex2ba(bytearray.hex(rle_data))))
        else:
            break
        if len(message_bytes[14 + offset + len_field: -28]) < 14:
            break
        offset += (len_field + 14)

    return update_list


def decode_message_to_bitmask(message_bytes: bytearray) -> bitarray:
    """
    Decode the message bitmask
    @param message_bytes bytearray of the Run Length Encoded data
    @return Bitmask of message
    """

    return rle_generation.decode_message_to_bitmask(message_bytes)


def generate_update_bitmask(update_dict: dict, update_name: str, number_of_chunks: int) -> bitarray:
    """
    Generate the update bitmask
    @param update_dict Dict of the updates
    @param update_name Name of the update
    @param number_of_chunks Number of chunks
    @return Bitmask of the update
    """
    sequence = set(update_dict[update_name].keys())
    bitmask = bitarray.bitarray()
    for chunk in range(0, number_of_chunks):
        if chunk in sequence:
            bitmask.append(True)
        else:
            bitmask.append(False)
    return bitmask


def data_indices_to_send(bitmask_heartbeat: bitarray, bitmask_vehicle: bitarray, index_begin: int = 0) -> List[int]:
    """
    Calculate the chunk indices to send, depending on the received heartbeat bitmask and the vehicle bitmask
    @param bitmask_heartbeat Received bitmask of the heartbeat
    @param bitmask_vehicle Bitmask of the vehicle
    @param index_begin Index of the first chunk
    @return List of all chunk indices that should be sent
    """
    return rle_generation.data_indices_to_send(bitmask_heartbeat, bitmask_vehicle, index_begin)

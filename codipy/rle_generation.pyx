import math
import random
cimport numpy as cnp
import numpy as np
from cython cimport boundscheck, wraparound
from numpy.random import default_rng
import bitarray

@boundscheck(False)
@wraparound(False)
cpdef decode_message_to_bitmask(bytearray message_bytes):
    """
    Calculate the expanded bitmask of a run-length encoded bytearray
    @param message_bytes The byte representation of the message indices
    @return The bitmask encoded message indices
    """
    cdef int available_mask = 0x80
    cdef int number_mask = 0x7f
    cdef cnp.ndarray[cnp.uint8_t, ndim=1] available = np.array([(byte & available_mask) != 0 for byte in message_bytes], dtype=np.uint8)
    cdef cnp.ndarray[cnp.uint8_t, ndim=1] number = np.array([(byte & number_mask) + 1 for byte in message_bytes], dtype=np.uint8)
    cdef cnp.ndarray[cnp.int8_t, ndim=1] bitmask_n = np.repeat(available, number).astype(np.int8)
    b = bitarray.bitarray()
    b.pack(bitmask_n)
    return b


@boundscheck(False)
@wraparound(False)
cpdef data_indices_to_send( bitmask_heartbeat,  bitmask_vehicle, int index_begin=0):
    """
    Calculate the chunk indices to send, depending on the received heartbeat bitmask and the vehicle bitmask
    @param bitmask_heartbeat Received bitmask of the heartbeat
    @param bitmask_vehicle Bitmask of the vehicle
    @param index_begin Index of the first chunk
    @return List of all chunk indices that should be sent
    """
    cdef int heartbeat_length = len(bitmask_heartbeat)
    cdef int vehicle_length = len(bitmask_vehicle)
    cdef int left_length
    cdef int remaining_length = len(bitmask_vehicle[index_begin:])
    if remaining_length >= heartbeat_length:
        temp_1 = bitmask_heartbeat ^ bitmask_vehicle[index_begin:index_begin + heartbeat_length]
        res = temp_1 & bitmask_vehicle[index_begin:index_begin + heartbeat_length]
        np_array = np.unpackbits(res, count=len(res))
        data_index_array = np.nonzero(np_array)[0] + index_begin
        return data_index_array
    else:
        bitmask = bitmask_vehicle[index_begin:]
        left_length = heartbeat_length - len(bitmask)
        bitmask.extend(bitmask_vehicle[:left_length])
        temp_1 = bitmask_heartbeat ^ bitmask
        res = temp_1 & bitmask
        res_np = np.unpackbits(res, count=len(res))
        non_zero_indices = np.nonzero(res_np)[0]
        data_index_list = np.mod(non_zero_indices + index_begin, vehicle_length)
        return data_index_list


cpdef generate_rle(update, int number_of_chunks, int remaining_length):
    """
    Use Run Length Encoding to encode the status of update chunks.
    The first bit in a byte is used as MSB. A MSB == 1 indicates a sequence of available chunks, a MSB == 0 indicates
        a sequence of missing chunks. The 7 remaining bits are used to save a number between 0 and 127, corresponding to
        a length of 1 to 128 chunks.
    @param update The update
    @param number_of_chunks The number of chunks
    @param remaining_length The Number of bytes left in message
    @return encoded data in bytearray, index of starting chunk, number of missing chunks
    """
    cdef bytearray encoded_bytes2 = bytearray()
    cdef bint running_available = False
    cdef bint running_missing = False
    cdef int current_counter = 0
    number_of_chunks_list = range(number_of_chunks)
    cdef int starting_chunk = random.choice(number_of_chunks_list)
    while update[starting_chunk] == 1:
        starting_chunk = random.choice(number_of_chunks_list)
    cdef int chunk = starting_chunk

    cdef int number_missing = 0
    cdef int encoded_bytes2_len = 0

    while chunk != starting_chunk or current_counter == 0:
        if encoded_bytes2_len >= remaining_length:
            return encoded_bytes2, starting_chunk, number_missing
        if update[chunk] == 1:
            if running_available:
                current_counter += 1
            else:
                number_of_full_bytes, remaining_number = divmod(current_counter, 128)
                encoded_bytes2.extend([127] * number_of_full_bytes)
                encoded_bytes2_len += number_of_full_bytes

                if remaining_number != 0:
                    encoded_bytes2.append((remaining_number - 1) + 0)
                    encoded_bytes2_len += 1
                running_available = True
                running_missing = False
                number_missing += current_counter
                current_counter = 1
        else:
            if running_missing:
                current_counter += 1
            else:
                number_of_full_bytes, remaining_number = divmod(current_counter, 128)
                encoded_bytes2.extend([255] * number_of_full_bytes)
                encoded_bytes2_len += number_of_full_bytes
                if remaining_number != 0:
                    encoded_bytes2.append((remaining_number - 1) + 128)
                    encoded_bytes2_len += 1
                running_missing = True
                running_available = False
                current_counter = 1

        chunk = (chunk + 1) % number_of_chunks

    number_of_full_bytes, remaining_number = divmod(current_counter, 128)
    for j in range(number_of_full_bytes):
        encoded_bytes2.append(127 if not running_available else 255)
    if remaining_number != 0:
        encoded_bytes2.append((remaining_number - 1) + (128 if running_available else 0))
    if running_missing:
        number_missing += current_counter

    return encoded_bytes2, starting_chunk, number_missing

cpdef calculate_packet_reception_probability(float inter_vehicle_distance, float transmission_power, float gain, float pathloss, float loss_exponent, float distance, bint log_shadow, bint shadow_slope,
                                             float sigma, bint two_ray, float antenna_height, float loss_exponent2, float sigma2, int nak_param= 2):
    """
    Calculates Packet Reception Probability either via fixed value or nakagami distribution
    @param inter_vehicle_distance The actual distance between sending and receiving vehicle
    @param transmission_power The transmission power
    @param gain The gain value
    @param pathloss The pathloss
    @param loss_exponent The loss exponent
    @param distance The communication distance
    @param log_shadow The log shadowing model
    @param shadow_slope The shadow slope
    @param sigma The sigma
    @param two_ray The two-ray ground interference model
    @param antenna_height The antenna height
    @param loss_exponent2 The second loss exponent
    @param sigma2 The second sigma value
    @param nak_param 1 for severe, 3 for medium, 5 for low fading conditions
    @return packet reception probability as float in [0, 1]
    """
    cdef float wavelength = 5.08 * 10 ** -2
    cdef float reception_threshold
    cdef float omega
    cdef float crossover_distance = 102.0
    cdef float packet_recept_prob
    if nak_param is not None:
        # use nakagami distribution as small scale fading model

        reception_threshold = transmission_power + 2.0 * gain - pathloss \
                             - 10.0 * loss_exponent * math.log(distance, 10)
        reception_threshold = 10.0 ** (round(reception_threshold) / 10)
        if log_shadow or shadow_slope:
            rng = default_rng()
        omega = transmission_power + 2.0 * gain - pathloss \
                - 10.0 * loss_exponent * math.log(inter_vehicle_distance, 10)
        if log_shadow or shadow_slope:
            omega += rng.normal(0, sigma)

        nak_param = 5

        if two_ray:
            crossover_distance = (4.0 * math.pi * antenna_height ** 2.0) / wavelength
        if two_ray or log_shadow or shadow_slope:
            if inter_vehicle_distance > crossover_distance:
                if log_shadow or shadow_slope:
                    omega = transmission_power + 2.0 * gain - pathloss \
                            - 10.0 * loss_exponent * math.log(crossover_distance, 10) \
                            - 10.0 * loss_exponent2 * math.log(inter_vehicle_distance / crossover_distance, 10) + rng.normal(0, sigma2)
                elif two_ray:
                    omega = transmission_power + 2.0 * gain \
                            + 40.0 * math.log(antenna_height, 10) - 40.0 * math.log(inter_vehicle_distance, 10)
        omega = 10.0 ** (omega / 10.0)
        if omega <= reception_threshold:
            return 0.0
        nak_list = []

        nak_list.extend([math.pow(nak_param * reception_threshold / omega, i - 1) / math.factorial(i - 1) for i in range(1, nak_param + 1)])
        return math.exp(-nak_param * reception_threshold / omega) * sum(nak_list)

    # use packet recept probability of 90 % for every occasion
    else:
        # Use a 10 percent packet loss
        return  0.9

@boundscheck(False)
@wraparound(False)
cpdef distance_calculation(float x1, float y1, float x2, float y2):
    """
    Calculate the distance between two (x, y) tuples
    @param x1 x value of point 1
    @param y1 y value of point 1
    @param x2 x value of point 2
    @param y2 y value of point 2
    @return The euclidian distance between both points
    """
    return np.linalg.norm(np.array((x1,y1)) - np.array((x2,y2)))
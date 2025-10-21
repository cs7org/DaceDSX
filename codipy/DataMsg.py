import struct
import hashlib


def generate_message(update_dict: dict, update_name: str, chunk_index: int) -> bytearray:
    """
    @bug For simulation purposes an empty bytearray is sent

    Generate a data message for an update chunk
    @param update_dict Dict of all updates
    @param update_name Name of update
    @param chunk_index Index of chunk in update
    @return bytearray of the data message
    """
    msg = bytearray()
    message_type = struct.pack('<I', 2)[:1]
    msg.extend(message_type)
    update_name_hash = hashlib.sha224(str.encode(update_name)).digest()[:8]
    msg.extend(update_name_hash)
    initial_chunk_index = struct.pack('<I', chunk_index)
    msg.extend(initial_chunk_index)
    msg.extend(bytearray(1411))  # dict[update_name][chunk_index]
    hash_value = hashlib.sha224(msg).digest()
    msg.extend(hash_value)
    return msg


def decode_message(msg: bytearray) -> (bytearray, int, bytearray):
    """
    @bug Hash calculation is omitted, as only paket errors are currently possible
    Decode a data message of an update chunk
    @param msg message bytes
    @return: Hash of update name, chunk index, update content
    """
    #if msg[-28:] != hashlib.sha224(msg[:-28]).digest():
    #    return None, None, None
    message_type_length = 1
    update_name_hash_length = 8
    chunk_index_length = 4
    hash_value_length = 28
    update_name_hash = msg[message_type_length:message_type_length + update_name_hash_length]
    chunk_index = struct.unpack('<I', msg[message_type_length + update_name_hash_length:message_type_length +
                                                                                        update_name_hash_length +
                                                                                        chunk_index_length])[0]
    update_content = bytes(msg[message_type_length + update_name_hash_length + chunk_index_length: -hash_value_length])
    return update_name_hash, chunk_index, update_content

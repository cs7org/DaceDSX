import struct
import hashlib


def encode(update_name: str, update_size: float, due_date: float, update_hash: str) -> bytearray:
    """
    Encode data for Update Initialization Message.
    @param update_name Name of update
    @param update_size Size of update
    @param due_date Due date of update
    @param update_hash Hash of update name
    @return Encoded message as bytearray
    """
    msg = bytearray()
    update_name_length = struct.pack('<H', len(update_name))
    msg.extend(update_name_length)
    tmp = struct.pack('<' + str(len(bytes(update_name, 'utf-8'))) + 's', bytes(update_name, 'utf-8'))
    msg.extend(struct.pack('<' + str(len(bytes(update_name, 'utf-8'))) + 's', bytes(update_name, 'utf-8')))
    msg.extend(struct.pack('<d', update_size))
    msg.extend(struct.pack('<d', due_date))
    msg.extend(update_hash)
    hash_value = hashlib.sha224(msg).digest()
    msg.extend(hash_value)
    return msg


def decode(msg: bytearray) -> (str, float, float, str):
    """
    Decode data of Update Initialization Message
    @param msg Encoded message as bytearray
    @return Update name, update size, due date, update hash
    """
    if msg[-28:] != hashlib.sha224(msg[:-28]).digest():
        return None, None, None, None
    update_name_length = int(struct.unpack('<H', msg[:2])[0])
    offset = 2
    update_name = (
        struct.unpack('<' + str(update_name_length) + 's', msg[offset: offset + update_name_length])[0]).decode("utf-8")
    offset += update_name_length
    update_size = int(struct.unpack('<d', msg[offset: offset + 8])[0])
    offset += 8
    due_date = float(struct.unpack('<d', msg[offset: offset + 8])[0])
    offset += 8
    update_hash = bytes(msg[offset: offset + 28])
    return update_name, update_size, due_date, update_hash

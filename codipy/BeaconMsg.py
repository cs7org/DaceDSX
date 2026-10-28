import struct
import hashlib
from MessageType import *


def generate_message(timestamp: float, beacon_interval: float, beacon_name: str) -> bytearray:
    """
    @bug For simulation purposes an empty bytearray is sent

    Generate a WlanAP Beacon Message
    @param timestamp Message timestamp
    @param beacon_interval Interval of BeaconMsg
    @param beacon_name Name of WlanAP
    @return bytearray
    """
    msg = bytearray()
    message_type = struct.pack('<I', 3)[:1]
    msg.extend(message_type)
    timestamp_bytes = struct.pack('<f', timestamp)
    msg.extend(timestamp_bytes)
    beacon_interval_bytes = struct.pack('<f', beacon_interval)
    msg.extend(beacon_interval_bytes)
    test = bytes(beacon_name, 'utf-8')
    #beacon_name_bytes = struct.pack('<s', beacon_name)
    msg.extend(test)
    #msg.extend(bytearray(1411))  # dict[update_name][chunk_index]
    #hash_value = hashlib.sha224(msg).digest()
    #msg.extend(hash_value)
    return msg


def decode_message(msg: bytearray) -> (float, float, str):
    """
    Decode a Beacon message of an WlanAP
    @param msg message bytes
    @return Timestamp, Beacon Interval, WlanAP name
    """
    message_type_length = 1
    timestamp_length = 4
    beacon_interval_length = 4
    timestamp = struct.unpack('<f', msg[message_type_length:message_type_length + timestamp_length])[0]
    beacon_interval = struct.unpack('<f', msg[message_type_length + timestamp_length:message_type_length + timestamp_length + beacon_interval_length])[0]
    beacon_name = msg[message_type_length + timestamp_length + beacon_interval_length:].decode('utf-8')
    return timestamp, beacon_interval, beacon_name


def is_beacon_message(msg: bytearray) -> bool:
    """
    Returns True if Message is of MessageType Beacon
    @param msg Message
    @return bool of MessageType check
    """
    msg_type = MessageType(struct.unpack('<I', msg[:1] + struct.pack('<I', 1)[1:])[0]).name is MessageType.BEACON.name
    return msg_type

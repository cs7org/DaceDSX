"""Stubs confluent_kafka (no broker/package on the host) and puts the base wrapper
modules on sys.path the same way the wrappers do. Import before TimeSync/Kafka*."""
import os
import sys
import types
from unittest.mock import MagicMock


class _Producer:
    def __init__(self, *args, **kwargs):
        pass

    def produce(self, *args, **kwargs):
        pass

    def flush(self, *args, **kwargs):
        pass


class _Consumer:
    def __init__(self, *args, **kwargs):
        pass

    def subscribe(self, *args, **kwargs):
        pass

    def poll(self, *args, **kwargs):
        return None

    def close(self):
        pass


class SerializerError(Exception):
    pass


_root = types.ModuleType('confluent_kafka')
_root.Producer = _Producer
_root.Consumer = _Consumer
_root.KafkaError = MagicMock()
_root.avro = MagicMock()
_serializer = types.ModuleType('confluent_kafka.avro.serializer')
_serializer.SerializerError = SerializerError
_serializer.KeySerializerError = SerializerError
_serializer.ValueSerializerError = SerializerError

sys.modules.update({
    'confluent_kafka': _root,
    'confluent_kafka.avro': _root.avro,
    'confluent_kafka.avro.serializer': _serializer,
    'confluent_kafka.avro.serializer.message_serializer': MagicMock(),
    'confluent_kafka.avro.error': MagicMock(),
    'confluent_kafka.avro.load': MagicMock(),
    'confluent_kafka.avro.cached_schema_registry_client': MagicMock(),
    'confluent_kafka.serialization': MagicMock(),
    'confluent_kafka.admin': MagicMock(),
})

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.append(_src + '/logic')
sys.path.append(_src + '/communication')

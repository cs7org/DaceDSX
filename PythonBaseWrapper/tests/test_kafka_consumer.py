import sys
import unittest
from unittest.mock import MagicMock, patch

import kafka_stub  # noqa: F401  must precede the wrapper imports
from KafkaConsumer import KafkaConsumer


class SubscribeTest(unittest.TestCase):
    def test_restart_after_error_keeps_later_subscriptions(self):
        consumer = KafkaConsumer('broker', 'registry', ['a'], 'id')
        consumer.subscribe(['a', 'b'])
        consumer.consumer.poll = MagicMock(side_effect=RuntimeError('broken'))
        with patch.object(sys.modules['KafkaConsumer'], 'AvroConsumerStrKey') as newConsumer:
            consumer.poll(0.1)
        newConsumer.return_value.subscribe.assert_called_once_with(['a', 'b'])


if __name__ == '__main__':
    unittest.main()

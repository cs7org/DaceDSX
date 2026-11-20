import unittest
from unittest.mock import MagicMock

import kafka_stub  # noqa: F401  must precede the wrapper imports
from TimeSync import TimeSync
from KafkaProducer import KafkaProducer


def syncMsg(sender, action, time=0, messages=None):
    return {'Sender': sender, 'Action': action, 'Time': time, 'Epoch': 0, 'Messages': messages or {}}


class SentMessageCountingTest(unittest.TestCase):
    def test_producer_hook_defaults_to_none(self):
        self.assertIsNone(KafkaProducer('broker', 'registry', 'id', useAvro=False).on_sent)

    def test_hooked_producer_messages_are_announced(self):
        timeSync = TimeSync('broker', 'registry', 'sync', 'me', logging=False)
        producer = KafkaProducer('broker', 'registry', 'me', useAvro=True, schemaPath='bus.avsc')
        producer.on_sent = timeSync.notifiyAboutSentMessage
        producer.produce('data.topic', {'v': 1})
        producer.produce('data.topic', {'v': 2})
        self.assertEqual(timeSync.getSentMsgDiff(), {'data.topic': 2})

    def test_hook_also_fires_with_delivery_timeout(self):
        producer = KafkaProducer('broker', 'registry', 'me', useAvro=False, deliveryTimeout=1)
        producer.on_sent = MagicMock()
        producer.produce('data.topic', b'payload')
        producer.on_sent.assert_called_once_with('data.topic')

    def test_sync_producer_is_not_counted(self):
        timeSync = TimeSync('broker', 'registry', 'sync', 'me', initNoParticipants=0, logging=False)
        timeSync.joinTiming()
        self.assertEqual(timeSync.getSentMsgDiff(), {})


class ProcessSyncMsgTest(unittest.TestCase):
    def test_every_announced_topic_matching_pattern_is_expected(self):
        timeSync = TimeSync('broker', 'registry', 'sync', 'me', logging=False)
        timeSync.addExpectedPattern(r'^data\.')
        timeSync.processSyncMsg(syncMsg('peer', 'join'))
        timeSync.processSyncMsg(syncMsg('peer', 'request', time=10,
                                        messages={'data.a': 1, 'other': 1, 'data.b': 2}))
        self.assertEqual(timeSync.expectedReceiveCount, {'data.a': 1, 'data.b': 2})
        self.assertEqual(timeSync.lbts, 10)

class MsgCountOKTest(unittest.TestCase):

    def setUp(self):
        self.ts = TimeSync('broker', 'registry', 'sync', 'me', logging=False)
        self.ts.max_error_count = 2
        self.ts.timeoutHandler = MagicMock()
        self.ts.processSyncMsg(syncMsg('peer', 'join'))

    def announce(self, topic='grid.power', count=3):
        self.ts.addExpectedTopic(topic)
        self.ts.processSyncMsg(syncMsg('peer', 'request', time=10, messages={topic: count}))

    def test_missing_messages_triggers_timeout_handler(self):
        ts = self.ts
        ts.addExpectedTopic('grid.voltage')
        self.announce()
        self.assertEqual(ts.expectedReceiveCount, {'grid.voltage': 0, 'grid.power': 3})
        self.assertNotIn('grid.power', ts.actualReceivedMsgCount)
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 1)
        ts.timeoutHandler.assert_not_called()
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 2)
        ts.timeoutHandler.assert_called_once_with()
        self.assertNotIn('grid.voltage', ts.receiveCountErrors)

    def test_partial_delivery_triggers_timeout_handler(self):
        ts = self.ts
        self.announce()
        ts.notifiyAboutReceivedMessage('grid.power', count=2)
        self.assertEqual(ts.actualReceivedMsgCount['grid.power'], 2)
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 1)
        ts.timeoutHandler.assert_not_called()
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 2)
        ts.timeoutHandler.assert_called_once_with()

    def test_progress_resets_counter_and_stall_triggers_timeout(self):
        ts = self.ts
        self.announce(count=4)
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 1)
        ts.notifiyAboutReceivedMessage('grid.power')
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 0)
        ts.notifiyAboutReceivedMessage('grid.power')
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 0)
        ts.timeoutHandler.assert_not_called()
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 1)
        ts.timeoutHandler.assert_not_called()
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 2)
        ts.timeoutHandler.assert_called_once_with()

    def test_complete_delivery_clears_error_state(self):
        ts = self.ts
        self.announce()
        self.assertFalse(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors['grid.power'], 1)
        ts.notifiyAboutReceivedMessage('grid.power', count=3)
        self.assertTrue(ts.msgCountOK())
        self.assertEqual(ts.receiveCountErrors.get('grid.power', 0), 0)
        ts.timeoutHandler.assert_not_called()

    def test_multiple_topics_require_complete_delivery(self):
        ts = self.ts
        self.announce(topic='grid.power', count=2)
        self.announce(topic='grid.voltage', count=3)
        self.assertEqual(ts.expectedReceiveCount, {'grid.power': 2, 'grid.voltage': 3})
        ts.notifiyAboutReceivedMessage('grid.power', count=2)
        ts.notifiyAboutReceivedMessage('grid.voltage', count=1)
        self.assertFalse(ts.msgCountOK())
        ts.notifiyAboutReceivedMessage('grid.voltage', count=2)
        self.assertTrue(ts.msgCountOK())

    def test_multiple_participants_accumulate_expected_messages(self):
        ts = self.ts
        self.announce(topic='grid.power', count=2)
        ts.processSyncMsg(syncMsg('peer2', 'join'))
        ts.processSyncMsg(syncMsg('peer2', 'request', time=10, messages={'grid.power': 3}))
        self.assertEqual(ts.expectedReceiveCount['grid.power'], 5)
        ts.notifiyAboutReceivedMessage('grid.power', count=2)
        self.assertFalse(ts.msgCountOK())
        ts.notifiyAboutReceivedMessage('grid.power', count=3)
        self.assertTrue(ts.msgCountOK())

class SafeTimeAdvancementTest(unittest.TestCase):
    def setUp(self):
        self.ts = TimeSync('broker', 'registry', 'sync', 'me', initNoParticipants=2, logging=False, waitTimeout=1.0)
        self.ts.processSyncMsg(syncMsg('me', 'join'))
        self.ts.processSyncMsg(syncMsg('peer', 'join'))
        self.ts.addExpectedTopic('grid.power')

    def announce(self, peer_time=10, expected_messages=1, received_messages=1):
        self.ts.processSyncMsg(syncMsg('me', 'request', time=10))
        self.ts.processSyncMsg(syncMsg('peer', 'request', time=peer_time, messages={'grid.power': expected_messages}))
        if received_messages:
            self.ts.notifiyAboutReceivedMessage('grid.power', received_messages)

    def test_advance_when_time_and_messages_are_ready(self):
        self.announce()
        self.ts.producer.produce = MagicMock()
        self.ts.timeAdvance(10)
        sent = self.ts.producer.produce.call_args.kwargs['value']
        self.assertEqual((sent['Sender'], sent['Action'], sent['Time']), ('me', 'request', 10))
        self.assertEqual(self.ts.currentLocalTime, 10)

    def test_advance_blocked_when_lbts_insufficient(self):
        self.ts.waitTimeout = 0.1
        self.announce(peer_time=5)
        with self.assertRaises(TimeoutError):
            self.ts.timeAdvance(10)
        self.assertEqual(self.ts.currentLocalTime, 0)

    def test_advance_blocked_when_no_messages_received(self):
        self.ts.waitTimeout = 0.1
        self.announce(received_messages=0)
        with self.assertRaisesRegex(TimeoutError, "announced messages"):
            self.ts.timeAdvance(10)
        self.assertEqual(self.ts.currentLocalTime, 0)
        self.assertGreater(self.ts.receiveCountErrors['grid.power'], 0)

    def test_advance_blocked_when_messages_incomplete(self):
        self.ts.waitTimeout = 0.1
        self.announce(expected_messages=2)
        with self.assertRaises(TimeoutError):
            self.ts.timeAdvance(10)
        self.assertEqual(self.ts.currentLocalTime, 0)

    def test_advance_blocked_when_both_conditions_unsatisfied(self):
        self.ts.waitTimeout = 0.1
        self.announce(peer_time=5, expected_messages=2)
        incoming = MagicMock()
        incoming.value.return_value = syncMsg('peer', 'request', time=10)
        self.ts.consumer.poll = MagicMock(return_value=incoming)
        with self.assertRaises(TimeoutError):
            self.ts.timeAdvance(10)
        self.assertEqual(self.ts.lbts, 10)
        self.assertEqual(self.ts.currentLocalTime, 0)

    def test_advance_after_peer_makes_progress(self):
        self.announce(peer_time=5)
        incoming = MagicMock()
        incoming.value.return_value = syncMsg('peer', 'request', time=10)
        self.ts.consumer.poll = MagicMock(return_value=incoming)
        self.ts.timeAdvance(10)
        self.ts.consumer.poll.assert_called()
        self.assertEqual(self.ts.currentLocalTime, 10)


class SynchronizationBoundTest(unittest.TestCase):
    def test_lbts_reflects_earliest_announced_time(self):
        test_cases = [(10, 10, 10, 10), (10, 5, 15, 5), (20, 15, 30, 15), (10, 20, 30, 10)]
        for time_a, time_b, time_c, expected_lbts in test_cases:
            with self.subTest(times=(time_a, time_b, time_c)):
                ts = TimeSync('broker', 'registry', 'sync', 'me', initNoParticipants=3, logging=False)
                for participant in ('A', 'B', 'C'):
                    ts.processSyncMsg(syncMsg(participant, 'join'))
                ts.processSyncMsg(syncMsg('A', 'request', time=time_a))
                ts.processSyncMsg(syncMsg('B', 'request', time=time_b))
                ts.processSyncMsg(syncMsg('C', 'request', time=time_c))
                self.assertEqual(ts.lbts, expected_lbts)

    def test_lbts_blocked_until_participant_leaves(self):
        ts = TimeSync('broker', 'registry', 'sync', 'me', initNoParticipants=3, logging=False)
        for participant in ('A', 'B', 'C'):
            ts.processSyncMsg(syncMsg(participant, 'join'))
        ts.processSyncMsg(syncMsg('A', 'request', time=10))
        ts.processSyncMsg(syncMsg('B', 'request', time=20))
        self.assertEqual(ts.lbts, 0)
        self.assertFalse(ts.timeOK(10))
        ts.processSyncMsg(syncMsg('C', 'leave'))
        self.assertEqual(ts.lbts, 10)
        self.assertTrue(ts.timeOK(10))

if __name__ == '__main__':
    unittest.main()

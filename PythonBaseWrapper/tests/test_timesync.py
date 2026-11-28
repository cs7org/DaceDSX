import unittest
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

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

    def test_stall_in_later_step_triggers_timeout_handler(self):
        ts = self.ts
        self.announce()
        ts.notifiyAboutReceivedMessage('grid.power', count=3)
        self.assertTrue(ts.msgCountOK())
        ts.processSyncMsg(syncMsg('peer', 'request', time=20, messages={'grid.power': 2}))
        self.assertFalse(ts.msgCountOK())
        ts.timeoutHandler.assert_not_called()
        self.assertFalse(ts.msgCountOK())
        ts.timeoutHandler.assert_called_once_with()

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

    def test_lbts_decreases_on_earlier_request(self):
        ts = TimeSync('broker', 'registry', 'sync', 'me', logging=False)
        ts.processSyncMsg(syncMsg('A', 'join'))
        ts.processSyncMsg(syncMsg('B', 'join'))
        ts.processSyncMsg(syncMsg('A', 'request', time=10))
        ts.processSyncMsg(syncMsg('B', 'request', time=10))
        self.assertTrue(ts.timeOK(10))
        ts.processSyncMsg(syncMsg('A', 'request', time=5))
        self.assertEqual(ts.participants['A'], 5)
        self.assertEqual(ts.participants['B'], 10)
        self.assertEqual(ts.lbts, 5)
        self.assertFalse(ts.timeOK(10))


class DifferentTimeStepTest(unittest.TestCase):
    def setUp(self):
        self.a_step = 3
        self.b_step = 5
        self.stop_time = 15
        self.a = TimeSync('broker', 'registry', 'sync', 'A', logging=False, waitTimeout=3.0)
        self.b = TimeSync('broker', 'registry', 'sync', 'B', logging=False, waitTimeout=3.0)
        for ts in (self.a, self.b):
            ts.processSyncMsg(syncMsg('A', 'join'))
            ts.processSyncMsg(syncMsg('B', 'join'))
        lock = Lock()

        def deliver(topic, value):
            with lock:
                self.a.processSyncMsg(value)
                self.b.processSyncMsg(value)
        self.a.producer.produce = MagicMock(side_effect=deliver)
        self.b.producer.produce = MagicMock(side_effect=deliver)

    def test_non_divisible_time_steps(self):
        grants = []
        def advance(ts, step):
            while ts.currentLocalTime < self.stop_time:
                previous_time = ts.currentLocalTime
                ts.timeAdvance(step)
                self.assertEqual(ts.currentLocalTime, previous_time + step)
                grants.append((ts.myID, ts.currentLocalTime))
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_a = executor.submit(advance, self.a, self.a_step)
            future_b = executor.submit(advance, self.b, self.b_step)
            for future in as_completed([future_a, future_b]):
                future.result()
        self.assertEqual(grants[:6], [('A', 3), ('B', 5), ('A', 6), ('A', 9), ('B', 10), ('A', 12)])
        self.assertCountEqual(grants[6:], [('A', 15), ('B', 15)])
        self.assertEqual(self.a.lbts, self.stop_time)
        self.assertEqual(self.b.lbts, self.stop_time)


class SynchronizationParticipationTest(unittest.TestCase):
    def test_join_timing_waits_for_required_participants(self):
        ts = TimeSync('broker', 'registry', 'sync', 'me', initNoParticipants=2, logging=False, waitTimeout=1.0)
        messages = [syncMsg('me', 'join'), syncMsg('me', 'join', time=10), syncMsg('X', 'join')]
        incoming = []
        for msg in messages:
            record = MagicMock()
            record.value.return_value = msg
            incoming.append(record)
        ts.producer.produce = MagicMock()
        ts.consumer.poll = MagicMock(side_effect=incoming)
        ts.joinTiming()
        ts.producer.produce.assert_called_once_with(topic='sync', value=syncMsg('me', 'join'))
        self.assertEqual(ts.consumer.poll.call_count, 3)
        self.assertEqual(ts.participants, {'me': 0, 'X': 0})
        self.assertEqual(ts.lbts, 0)

    def test_join_timing_times_out_when_participant_missing(self):
        ts = TimeSync('broker', 'registry', 'sync', 'me', initNoParticipants=2, logging=False, waitTimeout=1.0)
        ts.processSyncMsg(syncMsg('me', 'join'))
        ts.producer.produce = MagicMock()
        ts.consumer.poll = MagicMock(return_value=None)
        with patch('TimeSync.time.monotonic', side_effect=[0.0, 1.0]):
            with self.assertRaisesRegex(TimeoutError, "participants to join"):
                ts.joinTiming()
        ts.producer.produce.assert_called_once_with(topic='sync', value=syncMsg('me', 'join'))
        self.assertEqual(ts.participants, {'me': 0})

    def test_only_registered_participants_can_update_sync_time(self):
        ts = TimeSync('broker', 'registry', 'sync', 'me', logging=False)
        ts.addExpectedTopic('grid.power')
        ts.processSyncMsg(syncMsg('A', 'join'))
        ts.processSyncMsg(syncMsg('A', 'request', time=10))
        ts.processSyncMsg(syncMsg('B', 'request', time=20, messages={'grid.power': 3}))
        self.assertEqual(ts.participants, {'A': 10})
        self.assertEqual(ts.lbts, 10)
        self.assertEqual(ts.expectedReceiveCount['grid.power'], 0)

    def test_leave_timing_announces_departure(self):
        ts = TimeSync('broker', 'registry', 'sync', 'me', logging=False)
        ts.producer.produce = MagicMock()
        ts.leaveTiming()
        ts.producer.produce.assert_called_once_with(topic='sync', value=syncMsg('me', 'leave', time=-1))

    def test_late_joining_participant_reduces_lbts(self):
        ts = TimeSync('broker', 'registry', 'sync', 'A', initNoParticipants=2, logging=False, waitTimeout=1.0)
        ts.processSyncMsg(syncMsg('A', 'join'))
        ts.processSyncMsg(syncMsg('B', 'join'))
        ts.processSyncMsg(syncMsg('A', 'request', time=20))
        ts.processSyncMsg(syncMsg('B', 'request', time=20))
        ts.producer.produce = MagicMock()
        ts.timeAdvance(20)
        self.assertEqual(ts.currentLocalTime, 20)
        self.assertEqual(ts.lbts, 20)
        ts.processSyncMsg(syncMsg('C', 'join'))
        self.assertEqual(ts.participants, {'A': 20, 'B': 20, 'C': 0})
        self.assertEqual(ts.lbts, 0)
        self.assertEqual(ts.currentLocalTime, 20)
        self.assertFalse(ts.timeOK(20))

if __name__ == '__main__':
    unittest.main()

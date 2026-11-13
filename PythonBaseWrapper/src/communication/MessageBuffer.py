#!/usr/bin/env python3

import threading
import time
from struct import unpack


def getMsgTime(msg):
    """Simulation time a message was sent at (header 'time' set by KafkaProducer), -1 if unknown."""
    for key, value in (msg.headers() or []):
        if key == "time":
            return unpack('!q', value)[0]
    return -1


def getMsgSender(msg):
    """Producer ID a message was sent by (header 'sender' set by KafkaProducer), "" if unknown."""
    for key, value in (msg.headers() or []):
        if key == "sender":
            return value.decode() if isinstance(value, bytes) else str(value)
    return ""


def collectPeerMsgs(consumer, now, timeout, quiet=1.0, expected=()):
    """
    Latest message per topic among those sent at simulation time `now` or later; older ones are
    left over from an earlier step and dropped. Waits up to `timeout` s for a message on every
    topic in `expected` (for any first message if empty), then takes what else arrives until
    nothing came for `quiet` s.
    """
    latest = {}
    deadline = time.monotonic() + timeout
    while True:
        waiting = not latest or any(t not in latest for t in expected)
        wait = deadline - time.monotonic() if waiting else quiet
        if wait <= 0:
            break
        msg = consumer.poll(wait)
        if msg is None:
            if waiting:
                continue
            break
        if getMsgTime(msg) >= now:
            latest[msg.topic()] = msg
    return list(latest.values())


class MessageBuffer():
    """
    Thread-safe hand-over between a background consumer and the simulation loop.

    A message sent at simulation time t is announced with the sender's next time request,
    so TimeSync only guarantees that it has arrived once the receiver advanced past t.
    take(before) therefore only releases messages that were sent before the receiver's
    current time. Messages sent "concurrently" in the current step stay buffered for the
    next one, which makes the result independent of wall-clock timing.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.msgs = []

    def add(self, msg):
        with self.lock:
            self.msgs.append(msg)

    def take(self, before, topic=None):
        """Remove and return all messages sent before sim time `before` (optionally only on `topic`), oldest first."""
        with self.lock:
            ready, keep = [], []
            for m in self.msgs:
                if getMsgTime(m) < before and (topic is None or m.topic() == topic):
                    ready.append(m)
                else:
                    keep.append(m)
            self.msgs = keep
        # stable sort keeps the arrival order of messages with the same timestamp
        ready.sort(key=getMsgTime)
        return ready

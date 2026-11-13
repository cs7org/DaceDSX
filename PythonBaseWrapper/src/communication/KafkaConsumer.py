#!/usr/bin/env python3
#
# Copyright 2021 Moritz Gütlein
# 
# This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
# In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
#
# 

from confluent_kafka import avro
import csv
from confluent_kafka.avro.serializer import SerializerError
import json
from confluent_kafka import KafkaError
from AvroProducerConsumer import AvroConsumerStrKey
from confluent_kafka import Consumer
import threading
import traceback
import math


class KafkaConsumer():

    def __init__(self, broker, registry, topics, consumerID, avro=True, cb=0, strict=False, requestTimeout=None):
        if requestTimeout is not None and (not math.isfinite(requestTimeout) or requestTimeout <= 0):
            raise ValueError("requestTimeout must be finite and positive")
        self.strict = strict
        self.consumerID = consumerID
        self.broker = broker
        self.registry = registry
        self.topics = topics
        self.cb = cb
        self.avro = avro

        # regex subscriptions only see topics created later after a metadata refresh (default 5 min)
        if (self.avro):
            self.consumerConf = {'bootstrap.servers': broker, 'schema.registry.url': registry, 'group.id': consumerID,
                                 'client.id': consumerID, 'auto.offset.reset': "earliest",
                                 'max.poll.interval.ms': 3000000, 'topic.metadata.refresh.interval.ms': 1000}
            if requestTimeout is not None:
                self.consumerConf['schema.registry.request.timeout'] = requestTimeout
            self.consumer = AvroConsumerStrKey(self.consumerConf)
        else:
            self.consumerConf = {'bootstrap.servers': broker, 'group.id': consumerID, 'client.id': consumerID,
                                 'auto.offset.reset': "earliest", 'max.poll.interval.ms': 3000000,
                                 'topic.metadata.refresh.interval.ms': 1000}
            self.consumer = Consumer(self.consumerConf)
        self.running = True
        self.lastOffsets = {}

        self._subscribe(topics)
        self.th = None

    def translate_to_topic_notation(edge_id):
        edge_id_copy = edge_id
        conform_edge_id = ""
        while edge_id_copy.find("---") != -1:
            conform_edge_id = conform_edge_id + edge_id_copy[:edge_id_copy.find("---")] + "---" + format(ord("-"),
                                                                                                         "x") + "---" + format(
                ord("-"), "x") + "---" + format(ord("-"), "x")
            edge_id_copy = edge_id_copy[edge_id_copy.find("---") + 3:]

        conform_edge_id = conform_edge_id + edge_id_copy

        return conform_edge_id.translate({ord(sign): "---" + format(ord(sign), "x") for sign in conform_edge_id if
                                          sign.isalnum() is False and sign != "-"})

    def run(self):
        # short poll timeout so that stop() can join this thread quickly
        while (self.running):
            inMsg = self.poll(1)
            if inMsg is not None and self.cb:
                # an exception in the callback must not kill the listener thread, otherwise
                # TimeSync waits forever for messages that are never counted
                try:
                    self.cb(inMsg)
                except Exception:
                    print("callback failed for message on", inMsg.topic(), flush=True)
                    traceback.print_exc()
        self.consumer.close()

    def listenInBG(self):
        self.th = threading.Thread(target=self.run)
        self.th.start()

    # def listen(self):
    #     self.consumer.subscribe(self.topics)
    #     while(self.running):
    #         try:
    #             inMsg = self.consumer.poll(10)
    #             if inMsg != None and not(inMsg.error()):
    #                 if(self.cb):
    #                     self.cb(inMsg)
    #                 else:
    #                     print("> > > received msg! topic =", inMsg.topic(), ", time =", inMsg.timestamp()[1],", key =", inMsg.key(), ", value =", inMsg.value(), flush=True)

    #         except SerializerError as e:
    #             print("Message deserialization failed for {}: {}".format(inMsg, e), flush=True)

    def poll(self, timeout):
        if self.strict:
            msg = self.consumer.poll(timeout)
            if msg is not None and msg.error():
                # SimService starts the wrapper before the sender creates its
                # resource topic. Kafka retries metadata; the caller's deadline
                # still bounds the wait if the topic is never created.
                if msg.error().code() in (KafkaError.UNKNOWN_TOPIC_OR_PART, KafkaError._PARTITION_EOF):
                    return None
                raise RuntimeError(str(msg.error()))
            return msg
        try:
            msg = self.consumer.poll(timeout)
            if msg is None:
                return None
            if (msg.error()):
                # non-fatal errors (e.g. topic not yet created) are retried by librdkafka itself
                if not msg.error().fatal():
                    print("consumer error (ignored):", msg.error(), flush=True)
                    return None
                print("got a fatal error, restarting consumers", msg.error(), flush=True)
                self._restart()
                return None
            # after a restart the consumer resumes at the last committed offset, so messages
            # may be delivered twice -> drop them, otherwise TimeSync counts them twice
            key = (msg.topic(), msg.partition())
            if msg.offset() <= self.lastOffsets.get(key, -1):
                return None
            self.lastOffsets[key] = msg.offset()
            return msg
        except SerializerError as e:
            # the broken message is already consumed, restarting would only deliver it again
            print("Message deserialization failed:", e, flush=True)
            return None
        except Exception as e:
            print("got an exception, restarting consumers", e, flush=True)
            self._restart()
            return None

    def _restart(self):
        try:
            self.consumer.close()
        except Exception:
            pass
        if (self.avro):
            self.consumer = AvroConsumerStrKey(self.consumerConf)
        else:
            self.consumer = Consumer(self.consumerConf)
        self._subscribe(self.topics)

    def _subscribe(self, topics):
        self.consumer.subscribe(topics)
        print("subscribed to:")
        for t in topics:
            print(t)

    def subscribe(self, topics):
        if topics:
            # remember the subscription, a restart would fall back to the old topics otherwise
            self.topics = topics
            self._subscribe(topics)

    def stop(self):
        self.running = False
        if self.th is not None and self.th.is_alive():
            # the listener thread closes the consumer itself, closing it here while it polls is unsafe
            if threading.current_thread() is not self.th:
                self.th.join()
        else:
            self.consumer.close()

    def list_topics(self):
        return self.consumer.list_topics().topics


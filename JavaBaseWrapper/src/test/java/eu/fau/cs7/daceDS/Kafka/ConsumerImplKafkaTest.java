package eu.fau.cs7.daceDS.Kafka;

import static org.junit.Assert.assertEquals;

import java.nio.charset.StandardCharsets;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.Test;

public class ConsumerImplKafkaTest {

	@Test
	public void getSenderDecodesHeaderBytes() {
		ConsumerRecord<String, String> r = new ConsumerRecord<String, String>("topic", 0, 0L, "key", "value");
		r.headers().add("sender", "inst1".getBytes(StandardCharsets.UTF_8));

		assertEquals("inst1", ConsumerImplKafka.getSender(r));
	}

	@Test
	public void getSenderWithoutHeaderIsEmpty() {
		ConsumerRecord<String, String> r = new ConsumerRecord<String, String>("topic", 0, 0L, "key", "value");

		assertEquals("", ConsumerImplKafka.getSender(r));
	}
}

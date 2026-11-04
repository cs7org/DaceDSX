package eu.fau.cs7.daceDS.Component;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.nio.charset.StandardCharsets;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.Test;

public class ConsumerRecordComparatorTest {

	private final ConsumerRecordComparator comparator = new ConsumerRecordComparator();

	private static ConsumerRecord<String, String> record(String key, String sender) {
		ConsumerRecord<String, String> r = new ConsumerRecord<String, String>("topic", 0, 0L, key, "value");
		r.headers().add("sender", sender.getBytes(StandardCharsets.UTF_8));
		return r;
	}

	@Test
	public void getSenderDecodesHeaderBytes() {
		assertEquals("inst1", comparator.getSender(record("k", "inst1")));
	}

	@Test
	public void differentKeysOrderConsistently() {
		ConsumerRecord<String, String> a = record("a", "s");
		ConsumerRecord<String, String> b = record("b", "s");

		assertTrue(comparator.compare(a, b) < 0);
		assertTrue(comparator.compare(b, a) > 0);
	}

	@Test
	public void equalSendersCompareEqual() {
		assertEquals(0, comparator.compare(record("k", "s"), record("k", "s")));
	}

	@Test
	public void differentSendersCompareUnequal() {
		assertTrue(comparator.compare(record("k", "s1"), record("k", "s2")) != 0);
	}
}

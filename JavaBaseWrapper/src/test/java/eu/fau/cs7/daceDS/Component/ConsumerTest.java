package eu.fau.cs7.daceDS.Component;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.util.concurrent.ConcurrentMap;

import org.junit.Test;

public class ConsumerTest {

	@Test
	public void receivedCountingIsThreadSafe() {
		assertTrue(Consumer.getReceivedCounting() instanceof ConcurrentMap);
	}

	@Test
	public void concurrentMergesLoseNoUpdates() throws InterruptedException {
		final String topic = "ConsumerTest.concurrentMerges";
		final int threads = 8;
		final int perThread = 100000;

		Thread[] workers = new Thread[threads];
		for (int i = 0; i < threads; i++) {
			workers[i] = new Thread(() -> {
				for (int j = 0; j < perThread; j++) {
					Consumer.getReceivedCounting().merge(topic, 1L, Long::sum);
				}
			});
			workers[i].start();
		}
		for (Thread w : workers) {
			w.join();
		}

		assertEquals(Long.valueOf((long) threads * perThread), Consumer.getReceivedCounting().get(topic));
	}
}

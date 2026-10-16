package eu.fau.cs7.daceDS.SimService;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public class SimulationServiceTest {

	@Test
	public void ignoredRequestsAreNotRejected() {
		assertFalse(SimulationService.isAddRejected(0));
		assertFalse("request too old", SimulationService.isAddRejected(1));
		assertFalse("scenario id already known", SimulationService.isAddRejected(2));
	}

	@Test
	public void failedInstantiationIsRejected() {
		assertTrue(SimulationService.isAddRejected(3));
	}
}

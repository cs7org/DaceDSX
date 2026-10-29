package eu.fau.cs7.daceDS.SimService;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import java.util.ArrayList;
import java.util.List;

import org.junit.Test;

import eu.fau.cs7.daceDS.datamodel.BB;
import eu.fau.cs7.daceDS.datamodel.Projector;
import eu.fau.cs7.daceDS.datamodel.Scenario;

public class ScenarioManagerTest {

	static Scenario scenario(String sceID, String instanceID, String type) {
		Scenario s = new Scenario();
		s.setScenarioID(sceID);
		BB bb = new BB();
		bb.setInstanceID(instanceID);
		bb.setType(type);
		s.setBuildingBlocks(new ArrayList<>(List.of(bb)));
		s.setProjectors(new ArrayList<>());
		s.setTranslators(new ArrayList<>());
		return s;
	}

	@Test
	public void rejectsUnsafeIdsAndTypes() {
		long now = System.currentTimeMillis();
		assertEquals(4, ScenarioManager.addScenarioRun(scenario("sce", "sim0", "Sumo; rm -rf /"), now));
		assertEquals(4, ScenarioManager.addScenarioRun(scenario("sce", "sim 0", "Sumo"), now));
		assertEquals(4, ScenarioManager.addScenarioRun(scenario("sce/../x", "sim0", "Sumo"), now));
		assertEquals(4, ScenarioManager.addScenarioRun(scenario("", "sim0", "Sumo"), now));

		Scenario s = scenario("sce", "sim0", "Sumo");
		Projector p = new Projector();
		p.setProjectorID("proj0");
		p.setType("$(id)");
		s.getProjectors().add(p);
		assertEquals(4, ScenarioManager.addScenarioRun(s, now));
	}

	@Test
	public void acceptsSafeIdsAndTypes() {
		assertNull(ScenarioManager.findInvalidID(scenario("sce_1.a-b", "sim0", "SumoWrapper")));
	}
}

package eu.fau.cs7.daceDS.SimService;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

import org.junit.After;
import org.junit.Test;

import eu.fau.cs7.daceDS.Component.Config;
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

	static Properties configProps() throws Exception {
		Field f = Config.class.getDeclaredField("prop");
		f.setAccessible(true);
		return (Properties) f.get(null);
	}

	@After
	public void clearMaxAge() throws Exception {
		configProps().remove(Config.SCENARIO_MAX_AGE);
	}

	@Test
	public void maxAgeComesFromConfigWithDefault() throws Exception {
		assertEquals(Config.DEFAULT_SCENARIO_MAX_AGE_MS, ScenarioManager.getMaxAge());

		configProps().setProperty(Config.SCENARIO_MAX_AGE, "7200000");
		assertEquals(7200000L, ScenarioManager.getMaxAge());

		configProps().setProperty(Config.SCENARIO_MAX_AGE, "abc");
		assertEquals(Config.DEFAULT_SCENARIO_MAX_AGE_MS, ScenarioManager.getMaxAge());
	}
}

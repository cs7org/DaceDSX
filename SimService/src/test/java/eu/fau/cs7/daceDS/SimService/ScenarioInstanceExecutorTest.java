package eu.fau.cs7.daceDS.SimService;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Properties;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import eu.fau.cs7.daceDS.Component.Config;
import eu.fau.cs7.daceDS.datamodel.BB;
import eu.fau.cs7.daceDS.datamodel.Scenario;

public class ScenarioInstanceExecutorTest {

	@Rule
	public TemporaryFolder tmp = new TemporaryFolder();

	File root;

	@Before
	public void configureDirs() throws Exception {
		root = tmp.newFolder("root");
		setStatic(Config.class, "prop", Properties.class).setProperty(Config.EXECUTABLES_ROOT, root.getPath());
		setStatic(Config.class, "prop", Properties.class).setProperty(Config.LOG_DIR, tmp.newFolder("logs").getPath());
	}

	/** Tests run without config.properties; reach the package-private static state instead. */
	static <T> T setStatic(Class<?> owner, String field, Class<T> type) throws Exception {
		Field f = owner.getDeclaredField(field);
		f.setAccessible(true);
		return type.cast(f.get(null));
	}

	/** Scenario "sce" with building blocks given as instanceID/type pairs. */
	static Scenario scenario(String... instanceAndType) {
		Scenario s = new Scenario();
		s.setScenarioID("sce");
		List<BB> bbs = new ArrayList<>();
		for (int i = 0; i < instanceAndType.length; i += 2) {
			BB bb = new BB();
			bb.setInstanceID(instanceAndType[i]);
			bb.setType(instanceAndType[i + 1]);
			bbs.add(bb);
		}
		s.setBuildingBlocks(bbs);
		s.setProjectors(new ArrayList<>());
		s.setTranslators(new ArrayList<>());
		return s;
	}

	@Test
	public void missingLauncherAbortsScenarioAndTerminatesOthers() throws Exception {
		ExecutorThreadTest.fakeLauncher(root, "ok", "exec sleep 30\n");
		ScenarioInstanceExecutor exec = new ScenarioInstanceExecutor(scenario("ok0", "ok", "bad0", "missing"), false);

		assertFalse("scenario must not be acked", exec.instantiateScenario());

		assertTrue(exec.threads.get("bad0").hasStartFailed());
		ExecutorThread ok = exec.threads.get("ok0");
		ok.join(10000);
		assertFalse("running instance was not terminated", ok.isAlive());
	}

	@Test
	public void earlyNonZeroExitAbortsScenario() throws Exception {
		ExecutorThreadTest.fakeLauncher(root, "ok", "exec sleep 30\n");
		ExecutorThreadTest.fakeLauncher(root, "crash", "exit 127\n");
		ScenarioInstanceExecutor exec = new ScenarioInstanceExecutor(scenario("ok0", "ok", "crash0", "crash"), false);

		assertFalse("scenario must not be acked", exec.instantiateScenario());

		ExecutorThread ok = exec.threads.get("ok0");
		ok.join(10000);
		assertFalse("running instance was not terminated", ok.isAlive());
	}

	@Test
	public void terminationStatusNamesFailedInstances() throws Exception {
		ExecutorThreadTest.fakeLauncher(root, "ok", "exit 0\n");
		ExecutorThreadTest.fakeLauncher(root, "bad", "exit 3\n");
		Scenario sce = scenario("ok0", "ok", "bad0", "bad", "none0", "missing");
		ScenarioInstanceExecutor exec = new ScenarioInstanceExecutor(sce, false);

		exec.threads = exec.executeInstances(sce, false);
		exec.run();

		String status = exec.getTerminationStatus();
		assertTrue(status, status.startsWith("sce was terminated. Failed instances: "));
		assertTrue(status, status.contains("bad0 (exit 3)"));
		assertTrue(status, status.contains("none0 (start failed)"));
		assertFalse(status, status.contains("ok0"));
	}

	@Test
	public void terminationStatusIsPlainWhenAllInstancesSucceed() throws Exception {
		ExecutorThreadTest.fakeLauncher(root, "ok", "exit 0\n");
		Scenario sce = scenario("ok0", "ok", "ok1", "ok");
		ScenarioInstanceExecutor exec = new ScenarioInstanceExecutor(sce, false);

		exec.threads = exec.executeInstances(sce, false);
		exec.run();

		assertEquals("sce was terminated.", exec.getTerminationStatus());
	}

	@Test
	@SuppressWarnings("unchecked")
	public void managerKeepsTerminationStatusOfCleanedScenario() throws Exception {
		ExecutorThreadTest.fakeLauncher(root, "bad", "exit 3\n");
		Scenario sce = scenario("bad0", "bad");
		ScenarioInstanceExecutor exec = new ScenarioInstanceExecutor(sce, false);
		exec.threads = exec.executeInstances(sce, false);
		exec.run();
		setStatic(ScenarioManager.class, "runningScenarioThreads", HashMap.class).put("sce", exec);

		assertEquals(List.of("sce"), ScenarioManager.cleanTerminatedScenarios());
		assertEquals("sce was terminated. Failed instances: bad0 (exit 3)", ScenarioManager.getTerminationStatus("sce"));
	}
}

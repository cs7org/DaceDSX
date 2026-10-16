package eu.fau.cs7.daceDS.SimService;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.nio.file.Files;
import java.util.List;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import eu.fau.cs7.daceDS.datamodel.Scenario;

public class ExecutorThreadTest {

	@Rule
	public TemporaryFolder tmp = new TemporaryFolder();

	static Scenario scenario(String id) {
		Scenario s = new Scenario();
		s.setScenarioID(id);
		return s;
	}

	/** Creates &lt;root&gt;/&lt;type&gt;/run.sh with the given bash body. */
	static void fakeLauncher(File root, String type, String body) throws Exception {
		File dir = new File(root, type);
		dir.mkdirs();
		File run = new File(dir, "run.sh");
		Files.writeString(run.toPath(), "#!/bin/bash\n" + body);
		run.setExecutable(true);
	}

	@Test
	public void argumentsAndRootWithSpacesArePassedVerbatim() throws Exception {
		File root = tmp.newFolder("root with space");
		File argv = new File(root, "argv.txt");
		fakeLauncher(root, "sim", "printf '%s\\n' \"$#\" \"$1\" \"$2\" > \"" + argv + "\"\n");

		ExecutorThread t = new ExecutorThread(root.getPath(), tmp.newFolder("logs").getPath(), "sim", "my id", scenario("sce 1"));
		t.start();
		t.join(10000);

		assertEquals(0, t.getExitVal());
		assertEquals(List.of("2", "sce 1", "my id"), Files.readAllLines(argv.toPath()));
	}

	@Test
	public void largeOutputDoesNotBlockAndIsWrittenToLogFile() throws Exception {
		File root = tmp.newFolder("root");
		fakeLauncher(root, "sim", "head -c 200000 /dev/zero | tr '\\0' x; echo oops >&2\n");
		File logDir = new File(tmp.getRoot(), "logs/nested");

		ExecutorThread t = new ExecutorThread(root.getPath(), logDir.getPath(), "sim", "sim0", scenario("sce"));
		t.start();
		t.join(10000);

		assertFalse("process blocked on unread output", t.isAlive());
		assertEquals(0, t.getExitVal());
		File log = new File(logDir, "sce_sim0.run.log");
		assertTrue(log.length() >= 200000);
		assertTrue(Files.readString(log.toPath()).endsWith("oops\n"));
	}
}

/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.SimService;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;
import org.apache.log4j.Logger;

import eu.fau.cs7.daceDS.Component.Config;
import eu.fau.cs7.daceDS.datamodel.Scenario;


/**
 * Used for the execution of a process (i.e. simulator).
 * 
 * @author guetlein
 */
public class ExecutorThread extends Thread{

	Scenario scenario;
	String basePath;
	File logFile;
	List<String> callCmd;
	List<String> killCmd;
	String type;
	String id;
	Process proc = null;
	long pid = -1;
	boolean running = false;
	boolean startFailed = false;
	int exitVal = -1;

	Logger logger = Logger.getLogger(ExecutorThread.class.getName());
	
	ExecutorThread(String basePath, String logDir, String type, String id, Scenario scenario){
		this.basePath  = basePath;
		this.logFile  = new File(logDir, scenario.getScenarioID() + "_" + id + ".run.log");
		this.scenario  = scenario;
		this.type = type;
		this.id = id;
		logger  = Logger.getLogger(ExecutorThread.class.getName()+"."+type+"."+id);		
		callCmd = Arrays.asList(basePath+"/"+type+"/"+Config.EXECUTABLE, scenario.getScenarioID().toString(), id);
		killCmd = Arrays.asList(basePath+"/"+type+"/"+Config.EXECUTABLE_KILL, scenario.getScenarioID().toString(), id);
	}
	
	
	public void runKillScript() {
		logger.info("Killstring is: " + killCmd);
		Process proc = null;
		try {
			proc = new ProcessBuilder(killCmd).redirectErrorStream(true).redirectOutput(ProcessBuilder.Redirect.appendTo(logFile)).start();
			long exitVal = proc.waitFor();
			logger.info(id + ": Exit value: " + exitVal);
		} catch (IOException | InterruptedException e) {
			if(proc != null) proc.destroyForcibly();
		}
	}
	
	//todo: very prototypical
	public void run() {
		logger.info("Callstring is: " + callCmd);
		try {
			running = true;
			//child output is never read, so send it to a file instead of a pipe that fills up
			Files.createDirectories(logFile.getParentFile().toPath());
			proc = new ProcessBuilder(callCmd).redirectErrorStream(true).redirectOutput(logFile).start();
			pid = proc.pid();
			
			exitVal = proc.waitFor();
			
			running = false;
			logger.info(id + ": Exit value: " + exitVal);
		} catch (IOException | InterruptedException e) {
			if(proc == null) startFailed = true;
			else proc.destroyForcibly();
			logger.error(callCmd + " --> Process exception: " + e.getLocalizedMessage());
			running = false;
		}
		runKillScript();
	}

	public void terminate() {
		if(proc == null || !running) return;
		proc.destroy();
		try {
			if(proc.waitFor(5, TimeUnit.SECONDS)) return;
		} catch (InterruptedException e) {
			logger.error(e.getLocalizedMessage());
		}
		logger.warn(id + ": did not exit after SIGTERM, killing");
		proc.destroyForcibly();
	}
	
	public long getPID(){
		return pid;
	}
	public long getExitVal(){
		return exitVal;
	}
	public boolean hasStartFailed(){
		return startFailed;
	}
	public boolean isRunning(){
		return running;
	}
}

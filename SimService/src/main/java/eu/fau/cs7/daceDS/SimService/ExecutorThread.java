/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.SimService;

import java.io.IOException;
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
	String callString;
	String killString;
	String type;
	String id;
	Process proc = null;
	long pid = -1;
	boolean running = false;
	int exitVal = -1;

	Logger logger = Logger.getLogger(ExecutorThread.class.getName());
	
	ExecutorThread(String basePath, String type, String id, Scenario scenario){
		this.basePath  = basePath;
		this.scenario  = scenario;
		this.type = type;
		this.id = id;
		logger  = Logger.getLogger(ExecutorThread.class.getName()+"."+type+"."+id);		
		callString = basePath+"/"+type+"/"+Config.EXECUTABLE;
		callString += " " + scenario.getScenarioID() + " " + id;
		
		killString = basePath+"/"+type+"/"+Config.EXECUTABLE_KILL;
		killString += " " + scenario.getScenarioID() + " " + id;
	}
	
	
	public void runKillScript() {
		logger.info("Killstring is: " + killString);
		Runtime rt = null;
		Process proc = null;
		try {
			rt = Runtime.getRuntime();
			proc = rt.exec(killString);
			long exitVal = proc.waitFor();
			logger.info(id + ": Exit value: " + exitVal);
		} catch (IOException | InterruptedException e) {
			if(proc != null) proc.destroyForcibly();
		}
	}
	
	//todo: very prototypical
	public void run() {
		logger.info("Callstring is: " + callString);
		Runtime rt = null;
		try {
			running = true;
			rt = Runtime.getRuntime();
			proc = rt.exec(callString);
			pid = proc.pid();
			
			exitVal = proc.waitFor();
			
			running = false;
			logger.info(id + ": Exit value: " + exitVal);
		} catch (IOException | InterruptedException e) {
			if(proc != null) proc.destroyForcibly();
			logger.error(callString + " --> Process exception: " + e.getLocalizedMessage());
			running = false;
		}
		runKillScript();
	}

	public void terminate() {
		if(proc != null && running) {
			proc.destroy();
		}
	}
	
	public long getPID(){
		return pid;
	}
	public long getExitVal(){
		return exitVal;
	}
	public boolean isRunning(){
		return running;
	}
}

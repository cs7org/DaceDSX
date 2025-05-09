/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.SimService;
import java.io.Serializable;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;

import org.apache.log4j.Logger;

import eu.fau.cs7.daceDS.Component.Config;
import eu.fau.cs7.daceDS.datamodel.BB;
import eu.fau.cs7.daceDS.datamodel.Observer;
import eu.fau.cs7.daceDS.datamodel.Scenario;



/**
 * This class manages the execution of threads that are used to spawn executables,
 * in order to run simulations of scenarios.
 * 
 * @author guetlein
 *
 */
public class ScenarioManager {

	private static HashMap<String, ScenarioInstanceExecutor> runningScenarioThreads= new HashMap<String,ScenarioInstanceExecutor>();
	private static ArrayList<String> terminatedScenarioThreads= new ArrayList<String>();
	static Logger logger  = Logger.getLogger(ScenarioManager.class.getName());
	private static final long MAX_AGE = 60*60000;
	private static ArrayList<String> knownSCEIDs = new ArrayList<String>();
	
	public ScenarioManager() {
	}

	public static int getNoRunningScenarios(){
		return runningScenarioThreads.size();
	}
	public static int getNoTerminatedScenarios(){
		return terminatedScenarioThreads.size();
	}
	
	public static int monitorRunningScenarios() {
		//logger.info("There are "+runningScenarioThreads.size()+" running scenarios");
		int killCount = 0;
		for(Entry<String, ScenarioInstanceExecutor> entry : runningScenarioThreads.entrySet()) {
			//entry.getValue().printStatus();
			long age = entry.getValue().getAge();
			if(age > MAX_AGE) {
				logger.info(entry.getKey() + " is running for too long ("+age+") --> killing all related threads and spawned processes");
				killScenario(entry.getKey());
				killCount++;
			}
		}
		return killCount;
		
	}
	public static void killScenario(String scenario) {
		
		if(!runningScenarioThreads.containsKey(scenario)) {
			logger.info("ScenarioRunner:No thread list found for "+scenario);
			return;
		}
		
		ScenarioInstanceExecutor t = runningScenarioThreads.get(scenario);
			t.kill();
			t.interrupt();
			try {
				t.join();
			} catch (InterruptedException e) {
				logger.error(e.getLocalizedMessage());
			}
			logger.info("ScenarioRunner:killed thread for "+scenario);
		//terminatedScenarioThreads.add(scenario);
		//runningScenarioThreads.remove(scenario);
	}

	public void waitForScenario(String scenario) {
		if(!runningScenarioThreads.containsKey(scenario)) {
			logger.info("ScenarioRunner:No thread list found for "+scenario);
			return;
		}		
		
		ScenarioInstanceExecutor t = runningScenarioThreads.get(scenario);
		logger.info("ScenarioRunner: waitForScenario="+scenario);
			try {
				t.join();
			} catch (InterruptedException e) {
				logger.error(e.getLocalizedMessage());
			}
			
			logger.info("ScenarioRunner: waiting finished for  "+scenario);

		terminatedScenarioThreads.add(scenario);
		runningScenarioThreads.remove(scenario);
	}
	
	public static ArrayList<String> cleanTerminatedScenarios() {

		ArrayList<String> newlyTerminated = new ArrayList<String>();	
		for(Map.Entry<String, ScenarioInstanceExecutor> entry : runningScenarioThreads.entrySet()) {
			
				String scenario = entry.getKey();
				Thread t = entry.getValue();
				if(!t.isAlive())
				{
					logger.info(t.getName()+" terminated, ending sim #"+scenario);
					newlyTerminated.add(scenario);
				}
		}
		
		for(String scenario : newlyTerminated) {
			ScenarioInstanceExecutor r = runningScenarioThreads.get(scenario);
			runningScenarioThreads.remove(scenario);
			//todo: cleanup, delete files, topics
			//Orphaned sim instances need to get informed, so they can stop waiting. they could also use the timeoutLimit to die
		}

		terminatedScenarioThreads.addAll(newlyTerminated);
		
		return newlyTerminated;
	}


	public static int addScenarioRun(Scenario scenario, long timestamp) {

		//check if request contains old sce id
		if(knownSCEIDs.contains(scenario.getScenarioID().toString()))  {
			logger.info("RunSimFromKafka: Ignoring Scenario " + scenario.getScenarioID()+" request. SCE id is already known");
			return 2; //everything is good, we are just ignoring
		}
		
		//check if request is too old
		if(( (new Date()).getTime() - timestamp) > Config.getLong(Config.REQUEST_MAX_AGE))  {
			logger.info("RunSimFromKafka: Ignoring Scenario " + scenario.getScenarioID()+" request. Too old (record is from "+timestamp+", diff is "+((new Date()).getTime() - timestamp)/1000+" seconds)");
			return 1; //everything is good, we are just ignoring
		}

		//room for other checks
		//e.g., check state of computing cluster
		

		logger.info("Handing Scenario " + scenario.getScenarioID()+" to ScenarioRunner");
		//ScenarioManager.printScenario(scenario);
		ScenarioInstanceExecutor runner = new ScenarioInstanceExecutor(scenario, false);
		
		//prepare
		if(!runner.instantiateScenario()) {
			logger.info("Init ScenarioRunnerThread failed for " + scenario.getScenarioID());
			return 3;
		}
		
		//run
		runner.start();
		runningScenarioThreads.put(scenario.getScenarioID().toString(),runner);
		logger.info("RunSimFromKafka: Scenario " + scenario.getScenarioID()+" started. Currently there are "+runningScenarioThreads.size()+" scenarios running.");

		knownSCEIDs.add(scenario.getScenarioID().toString());
		
		return 0;
	}
	

	public static void printScenario(Scenario scenario) {
		logger.info("");
		logger.info("");
		logger.info("Scenario ID: " + scenario.getScenarioID());
		logger.info("Start      : " + scenario.getSimulationStart());
		logger.info("End        : " + scenario.getSimulationEnd());
		logger.info("---------------------------");
	

		logger.info("RandomSeed : " + scenario.getExecution().getRandomSeed());
		logger.info("Priority   : " + scenario.getExecution().getPriority());
		logger.info("NumSynced  : " + scenario.getExecution().getSyncedParticipants());
		logger.info("Constraints: " + scenario.getExecution().getConstraints());

		for(BB t : scenario.getBuildingBlocks()) {
			logger.info("---------------------------");
			logger.info("--SimID       : " + t.getInstanceID());
			logger.info("--StepLength  : " + t.getStepLength());
			logger.info("--Domain      : " + t.getDomain());
			logger.info("--Layer       : " + t.getLayer());
			// for(Map.Entry<String,String> lp : t.getLayerParams().entrySet()) {
			for(Map.Entry<CharSequence,CharSequence> lp : t.getParameters().entrySet()) {
				logger.info("----LayerParam: " + lp.getKey() + ":" + lp.getValue());
			}
			// for(Map.Entry<String,String> lp : t.getResources().entrySet()) {
				for(Map.Entry<CharSequence,CharSequence> lp : t.getResources().entrySet()) {
				logger.info("----Resources: " + lp.getKey() + ":" + lp.getValue());
			}
			// for(Map.Entry<String,String> lp :t.getResults().entrySet()) {
				for(Map.Entry<CharSequence,CharSequence> lp :t.getResults().entrySet()) {
				logger.info("----Results: " + lp.getKey() + ":" + lp.getValue());
			}
			logger.info("--Synchronized: " + t.getSynchronized$());
			for(CharSequence r : t.getResponsibilities()) {
				logger.info("----Resp      : " + r);
			}
			for(Observer o : t.getObservers()) {
				logger.info("----Observer  : Task=" + o.getTask() + ", Element=" + o.getElement() +", Period="+o.getPeriod()+",Trigger="+o.getTrigger()+",Type="+o.getType());
			}
		}

		logger.info("");
		logger.info("");
	}

}

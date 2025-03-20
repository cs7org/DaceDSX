*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.Component;

import org.apache.log4j.Logger;


public abstract class Projector extends Instance{

	Logger logger = Logger.getLogger("Projector");

	protected eu.fau.cs7.daceDS.datamodel.Projector projectorDescription;
	
	
	protected int epoch;
	protected int t;
	
	public Projector(String scenarioID, String instanceID, String demoScenario){
		this.scenarioID = scenarioID;
		this.instanceID = instanceID;
		this.demoScenario = demoScenario;
	}
	
	public void init() {		

	}
	
	protected void preLoopEvent() {};
	protected void preStepEvent(int t) {};
	protected void stepEvent(int t) {};
	protected void processStepEvent(int t) {};
	protected void postStepEvent(int t) {};
	protected void postLoopEvent() {};

	public void close(){		
		super.close();
	}

}
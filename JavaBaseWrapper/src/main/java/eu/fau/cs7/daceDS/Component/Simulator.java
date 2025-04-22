/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.Component;


import java.util.ArrayList;
import java.util.List;
import org.apache.log4j.Logger;

import eu.fau.cs7.daceDS.datamodel.BB;
import eu.fau.cs7.daceDS.datamodel.Observer;

/*
 * 
 * Abstract simulator skeleton.
 * 
 */

public abstract class Simulator<T> extends Instance{

	protected BB simulator;

	static Logger logger = Logger.getLogger("Simulator");

	protected ProvisionHandler<T> provisionHandler;
	protected OrchestrationHandler orchestrationHandler;
	protected int instanceNumber;
	private String provisionPrePattern;
	private String provisionPostPattern;

	protected List<Observer> observers = new ArrayList<Observer>();

	
	public Simulator(String scenarioID, String instanceID, String provisionPrePattern, String provisionPostPattern, String demoScenario){
		this.provisionPrePattern=provisionPrePattern;
		this.provisionPostPattern=provisionPostPattern;
		this.scenarioID = scenarioID;
		this.instanceID = instanceID;
		this.demoScenario = demoScenario;
		this.orchestrationHandler = new OrchestrationHandler(scenarioID, instanceID);
	}
	
	
	protected void preInit() {	

		log("preInit");
	}
	
	public void init() {

		log("Initializing Simulator Base");
		
		if(scenario == null) {
			log("Scenario must be instantiated before simulator.init()!");
			System.exit(1);
		}
		
		if(simulator == null) {
			log("Simulator must be instantiated before simulator.init()!");
			System.exit(1);
		}
		
		if(domainHelper == null) {
			log("DomainHelper must be instantiated before simulator.init()!");
			System.exit(1);
		}

		stepLengthInMs = simulator.getStepLength();
		synchronizing = simulator.getSynchronized$();
		
		log("creating provision handler");
		provisionHandler = new ProvisionHandler<T>(scenario, simulator, provisionPrePattern, provisionPostPattern, domainHelper);
		log("init provision handler");
		provisionHandler.init();
		log("done with provision handler");
		

		if (simulator.getObservers() != null){
		
			for(Observer o : simulator.getObservers()) {
				observers.add(o);		
				log("Added Observer: " +o.getTask()+ " " + o.getElement() + " " + " " + o.getFilter());
			}		
		}
		
		orchestrationHandler.listenForCtrlMsgs();

	}

	public abstract void preLoopEvent();
	

	protected abstract void preStepEvent(int t);
	
	/*
	 * Let's calculate the next step.
	 */
	protected abstract void stepEvent(int t);
	
	/*
	 * The sim step is calculated and we can check if we have to send out NDMs.
	 */
	protected abstract void processStepEvent(int t);
	
	/*
	 * Here we have a look at the existing state and run observers.
	 */
	protected abstract void postStepEvent(int t);
	
	
	public void synchronizeEvent(int t){
		super.synchronizeEvent(t);
		
		//now we can sort and process all incoming data (sorting gets done already done every time a msg is appended)
		//we will process all messages that are OLDER than t+1, in order to be able to modify our sate for time=t
//		System.out.println("sim sync event");
		provisionHandler.processBuffer(t+stepLengthInMs, this);
		
	}
	
	public void close(){
		super.close();
		provisionHandler.close();
		orchestrationHandler.close();
	}
	

}
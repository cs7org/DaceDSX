/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.Component;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map.Entry;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.log4j.Logger;

import eu.fau.cs7.daceDS.Kafka.ConsumerImplKafka;
import eu.fau.cs7.daceDS.Kafka.ConsumerCallbackImplKafka;
import eu.fau.cs7.daceDS.Kafka.ProducerImplKafka;
import eu.fau.cs7.daceDS.datamodel.BB;
import eu.fau.cs7.daceDS.datamodel.Scenario;
import eu.fau.cs7.daceDS.datamodel.Projector;


public class InteractionHandler implements ConsumerCallbackImplKafka{

	private final boolean AUTO_POLL = true;
	private final boolean FETCH_LATEST = false;
	Logger logger = Logger.getLogger(this.getClass());

	private final String scenarioID;
	private final String instanceID;
	private final String layer;
	private final String domain;
	private final String consumingTopic;
	private final String producingTopic;

	private ConsumerImplKafka<String> interactionReader;
	private ProducerImplKafka<String> writerCounting;
	private HashMap<Long, ArrayList<ConsumerRecord>> buffer = new HashMap<Long, ArrayList<ConsumerRecord>>();
	private boolean requesting;


	public InteractionHandler(Scenario scenarioDescription, BB sim, boolean requesting) {
		this.scenarioID = scenarioDescription.getScenarioID().toString();
		this.instanceID = sim.getInstanceID().toString();
		this.layer = sim.getLayer().toString();
		this.domain = sim.getDomain().toString();
		this.consumingTopic = "interaction.simulation."+scenarioID+"."+domain+"."+layer + "." + (requesting?"reply":"request");
		this.producingTopic = "interaction.simulation."+scenarioID+"."+domain+"."+layer + "." + (requesting?"request":"reply");
		this.requesting = requesting;
	}

	public InteractionHandler(Scenario scenarioDescription, Projector projector, String domain, String layer, boolean requesting) {
		this.scenarioID = scenarioDescription.getScenarioID().toString();
		this.instanceID = projector.getProjectorID().toString();
		this.layer = layer;
		this.domain = domain;
		this.consumingTopic = "interaction.simulation."+scenarioID+"."+domain+"."+layer + "." + (requesting?"reply":"request");
		this.producingTopic = "interaction.simulation."+scenarioID+"."+domain+"."+layer + "." + (requesting?"request":"reply");
		this.requesting = requesting;
	}

	
	public void init() {

		writerCounting = new ProducerImplKafka<String>(scenarioID+"_"+instanceID+"_countingWriter", true);
		logger.info("INIT writerCounting");
		writerCounting.initPlainString();
		
		interactionReader = new ConsumerImplKafka<String>(scenarioID+"_"+instanceID+"_patternReader", true);
		interactionReader.init(Collections.singletonList(consumingTopic), (ConsumerCallback) this, FETCH_LATEST, AUTO_POLL, true);					
		logger.info("subscribing to "+consumingTopic);
				
	}


	public void send(String msg, long time) {
		send(msg, time, 0);
	}
	
	public void send(String msg, long time, int epoch) {
		logger.info("Sending '"+msg+"' to "+producingTopic);
		writerCounting.publish(producingTopic, "key", msg, time, epoch, instanceID); 
	}

	@Override
	public void receive(ConsumerRecord r, long time, int epoch, String sender) { 
		logger.info("CB Received object in "+r.topic()+ " with key="+r.key());
		
		if(sender.equals(instanceID)){
			logger.info("skipping own message");
			return;
		}
		
		Long timeepoch = ((long) (1000*time))+epoch;
		logger.info("CB Received object time is "+timeepoch);
		synchronized(buffer) {
			if(!buffer.containsKey(timeepoch)) {
				ArrayList<ConsumerRecord> l = new ArrayList<ConsumerRecord>();
				buffer.put(timeepoch, l);
			}
			buffer.get(timeepoch).add(r); 
		}
	}

	public void processBuffer(long time, Instance instance) {
		processBuffer(time, 0, instance);
	}
	
	/*process everything that is older than time.epoch*/
	public void processBuffer(long time, int epoch, Instance instance) {
		Long timeepoch = ((long) (1000*time))+epoch;

		logger.debug("processing buffer for timeepoch " + timeepoch);
		synchronized(buffer) {
			ArrayList<Long> toRemove = new ArrayList<Long>();
			for(Entry<Long, ArrayList<ConsumerRecord>> e : buffer.entrySet()) {
				logger.info(e.getKey() +"?");
				if(e.getKey() < timeepoch) {	
					ArrayList<ConsumerRecord> msgs = e.getValue();
			        Collections.sort(msgs, new ConsumerRecordComparator());
					for(ConsumerRecord r : msgs) {
						logger.debug("processing " + r.topic() + ", "+ r.key()+ ", "+ r.timestamp());
						instance.processInteraction(r);
					}
					toRemove.add(e.getKey());
				}
			}
			
			for(Long key : toRemove) {
				buffer.remove(key);
			}
		}
	}	

	public int getBufferCount(long time) {
		return getBufferCount(time, 0);
	}
	
	public int getBufferCount(long time, int epoch) {
		String timeepoch = time+"_"+epoch;
		synchronized(buffer) {
			if(!buffer.containsKey(timeepoch)) return 0;
			return buffer.get(timeepoch).size();
		}
	}
	
	public void close(){

		if(interactionReader!=null){
			try{
				interactionReader.close();
			}catch(Exception e){ 
				logger.error("failed to close patternReader");
			}
		}
		
		try{
			writerCounting.close();
		}catch(Exception e){ 
			logger.error("failed to close writers");
		}

	}

}

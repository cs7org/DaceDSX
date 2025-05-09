/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.SimService;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.Properties;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.Pattern;

import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.common.errors.TimeoutException;
import org.apache.log4j.Level;
import org.apache.log4j.Logger;

import eu.fau.cs7.daceDS.Component.Config;
import eu.fau.cs7.daceDS.Kafka.ConsumerImplKafka;
import eu.fau.cs7.daceDS.Kafka.ProducerImplKafka;
import eu.fau.cs7.daceDS.Kafka.ConsumerCallbackImplKafka;


/**
 * The simulation service main loop. Listens for new requests and triggers the
 * execution of a simulation scenario by calling the ScenarioManager.
 * 
 * @author guetlein
 *
 */
public class KeepAlive implements ConsumerCallbackImplKafka
{

	private static ProducerImplKafka<String> kAProducer;
	private static ConsumerImplKafka<String> kAConsumer;
	private static int keepAliveCounter = 600;
    private static String kATopic = "orchestration.simulation.keepAlive";
    private static String kAMessage = "Hello!";
	private static int roundLimit = 600;
    private static volatile boolean gotResponse = false;
	private static int noResponseCounter = 0;
	private static final int noResponseLimit = 10;

	static Logger logger = Logger.getLogger(KeepAlive.class.getName());
	private String timestamp;

    public KeepAlive(String timestamp){
        this.timestamp = timestamp;
    }
	public void init()
	{
		kAProducer = new ProducerImplKafka<String>("keepAliveWriter"+timestamp);  
		kAProducer.initPlainString();
		kAConsumer = new ConsumerImplKafka<String>("keepAliveReader"+timestamp);  
		kAConsumer.initPlainString(Arrays.asList(kATopic), this);
	}
	public void close()
	{
		if(kAProducer != null) {
			kAProducer.close();
		}
		if(kAConsumer != null) {
			kAConsumer.close();
		}
	}

	public boolean keepAlive() {
		keepAliveCounter++;
		if(keepAliveCounter<roundLimit){
			return true;
		}
		keepAliveCounter = 0;
		
		//do some action and check if everything is working        
        gotResponse = false;
		String msg = kAMessage + " It is " + (new Date()).toString();
		logger.info("Publishing: "+msg);	
		boolean s = kAProducer.publish(kATopic, msg,0);
		if(!s){
			logger.error("Sending keep alive msg failed!");	
			return false;
		}

		logger.info("Waiting...");	
		try {
			Thread.sleep(1000);
		} catch (InterruptedException e) {
		}
		
        if(!gotResponse){
			noResponseCounter++;
			logger.info("No Response after 10 seconds... (#"+noResponseCounter+")");	

			if(noResponseCounter > noResponseLimit){
				return false;
			}
		}

        return true;
		
	}

	@Override
	public <T> void receive(ConsumerRecord r, long time, int epoch, String sender) {
        gotResponse = true;
        logger.info("Got response: "+((String)r.value()));	
	}

}

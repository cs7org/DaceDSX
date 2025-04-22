/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.Kafka;

import java.util.HashMap;
import java.util.Properties;
import java.util.ArrayList;
import java.util.List;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.header.Header;
import org.apache.kafka.common.header.internals.RecordHeader;
import org.apache.kafka.clients.admin.AdminClient;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.log4j.Logger;

import eu.fau.cs7.daceDS.Component.Config;
import eu.fau.cs7.daceDS.Component.Producer;
import eu.fau.cs7.daceDS.Component.ScenarioUtils;
import io.confluent.kafka.serializers.subject.TopicNameStrategy;
import io.confluent.kafka.serializers.AbstractKafkaSchemaSerDeConfig;

/**
 * A Kafka producer class.
 *  
 * @author guetlein
 *
 * @param <T>
 */
public class  ProducerImplKafka<T> extends Producer<T>
{

    public final static Logger logger = Logger.getLogger(ProducerImplKafka.class.getName());
	private KafkaProducer<String, T> producer;
	Properties kafkaProducerProps;


	public ProducerImplKafka(String id){
		super(id);
	}

	public ProducerImplKafka(String id, boolean counting){
		super(id, counting);
	}


	public void init()
	{
	    kafkaProducerProps =  Config.getProducerProperties(id, exactlyOnce);
	    producer = new KafkaProducer<String, T>(kafkaProducerProps);
	    logger.info("Producer will connect to "+eu.fau.cs7.daceDS.Component.Config.get(Config.KAFKA_BROKER)+" and "+eu.fau.cs7.daceDS.Component.Config.get(Config.SCHEMA_REGISTRY));
	    
	    if(exactlyOnce) {
	    	producer.initTransactions();
	    }
	}	
	
	public void initPlainString()
	{
	    kafkaProducerProps =  Config.getProducerProperties(id, exactlyOnce, plainStringValue);
	    producer = new KafkaProducer<String, T>(kafkaProducerProps);
	    logger.info("Producer will connect to "+eu.fau.cs7.daceDS.Component.Config.get(Config.KAFKA_BROKER)+" and "+eu.fau.cs7.daceDS.Component.Config.get(Config.SCHEMA_REGISTRY));
	    
	    if(exactlyOnce) {
	    	producer.initTransactions();
	    }
	}

	public void initTopicNamingStrategy()
	{
	    kafkaProducerProps =  Config.getProducerProperties(id, exactlyOnce);
		kafkaProducerProps.put(AbstractKafkaSchemaSerDeConfig.VALUE_SUBJECT_NAME_STRATEGY, TopicNameStrategy.class.getName()); //libserdes does not support anything else
	    producer = new KafkaProducer<String, T>(kafkaProducerProps);
	    logger.info("Producer will connect to "+eu.fau.cs7.daceDS.Component.Config.get(Config.KAFKA_BROKER)+" and "+eu.fau.cs7.daceDS.Component.Config.get(Config.SCHEMA_REGISTRY));
	    
	    if(exactlyOnce) {
	    	producer.initTransactions();
	    }
	}

	public void createTopics(List<String> topicNames){
	    System.out.println("Creating Topics " + topicNames);
		AdminClient adminClient = AdminClient.create(kafkaProducerProps);
		List<NewTopic> newTopics = new ArrayList<NewTopic>();
		for(String topicName : topicNames){
			NewTopic newTopic = new NewTopic(topicName, 1, (short)1); //new NewTopic(topicName, numPartitions, replicationFactor)
			newTopics.add(newTopic);
		}
		adminClient.createTopics(newTopics);
		adminClient.close();
	}

	public boolean publish(String topic, T payload, long time){
		return publish(topic, "", payload, time, 0, "unkown");
	}

	public boolean publish(String topic, String key, T payload, long time, int epoch, String sender){

	    ProducerRecord<String, T> recordToSend = new ProducerRecord<>(topic, key, payload);
	    
	    if (time > -1) {
	    	Header t = new RecordHeader("time", ScenarioUtils.longToBytes(time));
	    	recordToSend.headers().add(t);
	    	Header e = new RecordHeader("epoch", ScenarioUtils.intToBytes(epoch));
	    	recordToSend.headers().add(e);
	    	Header s = new RecordHeader("sender", sender.getBytes());
	    	recordToSend.headers().add(s);
	    }
	    
	    if(exactlyOnce) {
	    	producer.beginTransaction();
	    }  
	    
	    if (producer == null) {
	    	logger.error("producer is null");
	    	System.exit(-1);
	    }
	    
	    try {
		    producer.send(recordToSend);
	    } catch (Exception ex) {
	    	logger.error(ex.toString());
	    	logger.error(ex.getLocalizedMessage());
	    	return false;
	    }
        
		producer.flush();
	    
	    if(exactlyOnce) {
	    	producer.commitTransaction();
		}
		

		if(countingProducer){
			sentCounting.merge(topic, 1L, Long::sum);   
		}
		
		return true;
        	    
	}
	


	public void close()
	{
	    System.out.println("Closing Producer");
		producer.flush();
	    producer.close();
	     
	}
}

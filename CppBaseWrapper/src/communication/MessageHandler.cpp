*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/

#include "MessageHandler.h"
using namespace daceDS;

std::mutex bufmutex;

bool MessageHandler::bufferConsumedMessage(ConsumedMessage* msg) {
    // std::unique_lock<std::mutex> lock(bufmutex);
    buffer.insert(msg);
    // lock.unlock();
    return true;
}

/*process everything that is older than time.epoch*/
void MessageHandler::processBuffer(int time, int epoch){

        // std::unique_lock<std::mutex> lock(bufmutex);
    	int64_t t = ((int64_t)1000)*time+epoch;

		KDBGCB("processing buffer for timeepoch " << t);

		for (std::set<ConsumedMessage*>::iterator it = buffer.begin(); it != buffer.end(); ){

            ConsumedMessage* msg = *it;
            
            //msg is old enough
            if(msg->st < t){
                //handle msg
		        KDBGCB("processing message on " << msg->topic << " at " << msg->st);
                handle(msg);
                //and remove it
                //free(msg->payload);
                //delete msg;
                
                delete msg;
                it = buffer.erase(it);
            } 
            //skip newer messages
            else {
                //todo: since the buffer is sorted, can we safely quit at this point?
                it++;
            }
        }	
        
    // lock.unlock();	
}


*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.Component;

import eu.fau.cs7.daceDS.datamodel.BB;
import eu.fau.cs7.daceDS.datamodel.Observer;

/*
 * Has logic to extract information from simulators and provides kafka writers to publish these infos. 
 */
public abstract class ObserverI {
	protected String scenarioID = "";
	protected String instanceID = "";
	protected BB instance;
	
	protected ObserverI(String scenarioID, BB instance){
		this.scenarioID = scenarioID;
		this.instance = instance;
		this.instanceID = instance.getInstanceID().toString();
	}
	protected abstract void processObserver(Observer o);
}

/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.Component;
import java.util.ArrayList;
import java.util.List;


public class DomainHelper {

	protected List<String> externalResponsibilities = new ArrayList<String>(); //e.g., nodes
	protected List<String> internalResponsibilities = new ArrayList<String>(); //e.g., edges
	
	public void setInternalResponsibilities(List<String> internalResponsibilities) {
		this.internalResponsibilities = internalResponsibilities;
	}

	public List<String> getInternalResponsibilities(){
		return internalResponsibilities;
	}
	
	public boolean isResponsibleExternal(String toNode) {
		for(CharSequence node : getExternalResponsibilities()) {
			if(node.toString().equals(toNode)) {
				return true;
			}
		}
		return false;
	}	
	
	public boolean isResponsibleInternal(String toNode) {
		for(CharSequence node : internalResponsibilities) {
			if(node.toString().equals(toNode)) {
				return true;
			}
		}
		return false;
	}

	public List<String> getExternalResponsibilities() {
		return externalResponsibilities;
	}

	public void setExternalResponsibilities(List<String> externalResponsibilities) {
		this.externalResponsibilities = externalResponsibilities;
	}

}
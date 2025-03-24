*/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.Component;

public class Starter {

	public static void main(String[] args) {
	    String scenarioID = args[0];
	    String instanceID = args[1];
		String demoScenario = "";
		String provisionPrePattern = "link\\.";
		String provisionPostPattern = "\\.vehicles";

		if(args.length == 3) {
			demoScenario = args[2];
		}
		//Simulator simulator = new Simulator(scenarioID, instanceID, provisionPrePattern, provisionPostPattern, demoScenario);
		//simulator.log("running preperations! \n\n\n\n\n");
		//simulator.loadConfig();
		//simulator.preInit();

		//simulator.log("running matsim! \n\n\n\n\n");
		//simulator.init();

		//simulator.log("Sim is over, returning results!");


		//simulator.close();

	}

}

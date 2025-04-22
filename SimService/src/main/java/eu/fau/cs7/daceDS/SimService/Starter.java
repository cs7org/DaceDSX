/*
MIT License

Copyright 2021 Moritz Gütlein

This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
*/
package eu.fau.cs7.daceDS.SimService;
import java.text.SimpleDateFormat;
import java.util.Calendar;

import eu.fau.cs7.daceDS.Component.Config;


public class Starter{

	public static void main(String[] args) {

		SimpleDateFormat dfDate  = new SimpleDateFormat("yyyy.MM.dd_HH:mm:ss");
		Calendar c = Calendar.getInstance(); 
		String date=dfDate.format(c.getTime());
		System.setProperty(Config.LOG_FILE, "/tmp/SimulationService_"+date+".txt");
		Config.readConfig();
		System.setProperty(Config.LOG_DIR, Config.get(Config.LOG_DIR));
		System.setProperty(Config.LOG_FILE, Config.get(Config.LOG_DIR)+"/SimulationService_"+date+".txt");
		
		SimulationService.main(args);

	}
}

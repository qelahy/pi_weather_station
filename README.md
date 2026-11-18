# Raspberry Pi Weather Station

**Name:** A.S.S.M.Q-E-Elahy  
**Student ID:** C00329379

This project uses a Raspberry Pi and Sense HAT to collect temperature, humidity, and pressure readings. It checks the sensor data and saves it locally in SQLite.

The station can send readings to a central PC through MQTT. If the network is unavailable, it keeps collecting data and stores readings for replay later.

It also calculates recent sensor trends, displays the station status, and runs a small temperature forecasting model. A web dashboard shows the latest readings and clearly identifies old or unavailable data.

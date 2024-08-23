#include "FastIMU.h"
#include <Wire.h>
#include "WiFi.h"
#include "AsyncUDP.h"
#include <ESPmDNS.h>
#include "IPAddress.h"

#define IMU_ADDRESS 0x68    //Change to the address of the IMU
#define PERFORM_CALIBRATION //Comment to disable startup calibration
IMU_Generic IMU;               //Change to the name of any supported IMU! 
const char* ssid = "Data";
const char* password =  "1234567890";
String position = "RKM";
AsyncUDP udp;
IPAddress server_ip;
uint16_t server_port;

// Currently supported IMUS: MPU9255 MPU9250 MPU6886 MPU6500 MPU6050 ICM20689 ICM20690 BMI055 BMX055 BMI160 LSM6DS3 LSM6DSL

calData calib = { 0 };  //Calibration data
AccelData accelData;    //Sensor data
GyroData gyroData;
MagData magData;
int i = 0;


void setup() {
  Wire.begin(23, 19); //SDA | SCL
  Wire.setClock(400000); //400khz clock
  Serial.begin(115200);
  while (!Serial) {
    ;
  }

  int err = IMU.init(calib, IMU_ADDRESS);
  if (err != 0) {
    Serial.print("Error initializing IMU: ");
    Serial.println(err);
    while (true) {
      ;
    }
  }
  
#ifdef PERFORM_CALIBRATION
  Serial.println("FastIMU calibration & data example");
  Serial.println("Keep IMU level.");
  delay(3000);
  IMU.calibrateAccelGyro(&calib);
  Serial.println("Calibration done!");
  Serial.println("Accel biases X/Y/Z: ");
  Serial.print(calib.accelBias[0]);
  Serial.print(", ");
  Serial.print(calib.accelBias[1]);
  Serial.print(", ");
  Serial.println(calib.accelBias[2]);
  Serial.println("Gyro biases X/Y/Z: ");
  Serial.print(calib.gyroBias[0]);
  Serial.print(", ");
  Serial.print(calib.gyroBias[1]);
  Serial.print(", ");
  Serial.println(calib.gyroBias[2]);
  if (IMU.hasMagnetometer()) {
    Serial.println("Mag biases X/Y/Z: ");
    Serial.print(calib.magBias[0]);
    Serial.print(", ");
    Serial.print(calib.magBias[1]);
    Serial.print(", ");
    Serial.println(calib.magBias[2]);
    Serial.println("Mag Scale X/Y/Z: ");
    Serial.print(calib.magScale[0]);
    Serial.print(", ");
    Serial.print(calib.magScale[1]);
    Serial.print(", ");
    Serial.println(calib.magScale[2]);
  }
  delay(1000);
  IMU.init(calib, IMU_ADDRESS);
#endif

  //err = IMU.setGyroRange(500);      //USE THESE TO SET THE RANGE, IF AN INVALID RANGE IS SET IT WILL RETURN -1
  //err = IMU.setAccelRange(2);       //THESE TWO SET THE GYRO RANGE TO ±500 DPS AND THE ACCELEROMETER RANGE TO ±2g
  
  if (err != 0) {
    Serial.print("Error Setting range: ");
    Serial.println(err);
    while (true) {
      ;
    }
  }
  WiFi.begin(ssid, password);
 
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi..");
  }
  Serial.println("Connected to the WiFi network");
  if (!MDNS.begin("ESP32_Browser")) {
        Serial.println("Error setting up MDNS responder!");
        while(1){
            delay(1000);
        }
    }
  int service_found = 0;
  while (service_found == 0){
    int n = MDNS.queryService("spirit", "udp");
    if (n == 0) {
        Serial.println("no services found");
        delay(1000);
    } else {
        Serial.print(n);
        Serial.println(" service(s) found");
        for (i = 0; i < n; i++){
          Serial.println(MDNS.hostname(i));
          Serial.println(MDNS.IP(i));
        }
        //Serial.println(MDNS.hostname(0));
        //Serial.println(MDNS.IP(0));
        server_ip.fromString(MDNS.hostname(0));
        Serial.println(server_ip);
        Serial.println(MDNS.port(0));
        server_port = MDNS.port(0);
        service_found = 1;        
    }
    Serial.println();
  }
  int udp_connected = 0;
  while (udp_connected == 0){
    if(udp.connect(server_ip, server_port)) {
      Serial.println("UDP connected");
      udp_connected = 1;
    }
    else {
      Serial.println("No server connection");
      delay(1000);
    }
  }    

  
  

}

void loop() {


  
  IMU.update();
  IMU.getAccel(&accelData);
  IMU.getGyro(&gyroData);
  String message = "{\"position\":\"" + position + "\", \"index\":\"" + i + "\", \"data\":[" + accelData.accelX + "," + accelData.accelY + "," + accelData.accelZ + "," + gyroData.gyroX + "," + gyroData.gyroY + "," + gyroData.gyroZ + "]}";
  Serial.println(message);
  udp.print(message);
  //udp.broadcastTo(message.c_str(), 1234);
  i = i + 1;
  /*accelx[i] = accelData.accelX;
  accely[i] = accelData.accelY;
  accelz[i] = accelData.accelZ;
  gyrox[i] = gyroData.gyroX;
  gyroy[i] = gyroData.gyroY;
  gyroz[i] = gyroData.gyroZ;

  i = i + 1;
  if (i==25) {
    String message = "{\"data\":[";
    message = message + JSON.stringify(accelx);
    message = message + ",";
    message = message + JSON.stringify(accely);
    message = message + ",";
    message = message + JSON.stringify(accelz);
    message = message + ",";
    message = message + JSON.stringify(gyrox);
    message = message + ",";
    message = message + JSON.stringify(gyroy);
    message = message + ",";
    message = message + JSON.stringify(gyroz);
    message = message + "]}";
    udp.broadcastTo(message.c_str(), 1234);
    i = 0;
  } */
  
  //delay(15);
}

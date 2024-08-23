use std::time::Duration;
use mpu6050::*;
use esp_idf_hal::gpio::{AnyIOPin};
use esp_idf_hal::i2c::{I2c, I2cConfig, I2cDriver, I2cError};
use esp_idf_hal::peripheral::Peripheral;
use esp_idf_hal::peripherals::Peripherals;
use esp_idf_hal::prelude::*;
use esp_idf_hal::units::Hertz;
use std::net::{Ipv4Addr, UdpSocket};
use esp_idf_svc::{
    nvs::EspDefaultNvsPartition,
    eventloop::EspSystemEventLoop,
    };
use esp_idf_svc::wifi::{EspWifi};
use embedded_svc::wifi::{ClientConfiguration, Configuration};
use esp_idf_svc::mdns;
use esp_idf_sys::EspError;
use heapless::String;
const WIFI_SSID: &str = "Data";
const WIFI_PASS: &str = "1234567890";

fn i2c_master_init<'d>(
    i2c: impl Peripheral<P = impl I2c> + 'd,
    sda: AnyIOPin,
    scl: AnyIOPin,
    baudrate: Hertz,
) -> anyhow::Result<I2cDriver<'d>> {
    let config = I2cConfig::new().baudrate(baudrate);
    let driver = I2cDriver::new(i2c, sda, scl, &config)?;
    Ok(driver)
}
struct DelayCompat {
    delay: esp_idf_hal::delay::Delay,
}
impl embedded_hal::blocking::delay::DelayUs<u16> for DelayCompat {
    fn delay_us(&mut self, us: u16) {
        self.delay.delay_us(us as u32);
    }
}
impl embedded_hal::blocking::delay::DelayMs<u8> for DelayCompat {
    fn delay_ms(&mut self, ms: u8) {
        self.delay.delay_ms(ms as u32);
    }
}
fn main() {
    // It is necessary to call this function once. Otherwise some patches to the runtime
    // implemented by esp-idf-sys might not link properly. See https://github.com/esp-rs/esp-idf-template/issues/71
    esp_idf_svc::sys::link_patches();

    // Bind the log crate to the ESP Logging facilities
    esp_idf_svc::log::EspLogger::initialize_default();

    log::info!("Equimetrics ver. 0.1");
    let peripherals = Peripherals::take().unwrap();
    // Setting up I2C Communication
    let i2c_master = i2c_master_init(
        peripherals.i2c0,
        peripherals.pins.gpio19.into(),
        peripherals.pins.gpio23.into(),
        100.kHz().into(),
    ).unwrap();
    //Initialising MPU Driver
    let mut mpu = Mpu6050::new(i2c_master);
    //Instantiating Custom Delay Adaptor because the std Delay doesnt implement DelayUs
    let mut delay = DelayCompat {
        delay: esp_idf_hal::delay::Delay::new_default(),
    };
    let mpu_init = mpu.init(&mut delay);
    match mpu_init {
        Ok(_) => {}
        Err(e) => {log::info!("{:?}" ,e);}
    }
    let sys_loop = EspSystemEventLoop::take().unwrap();
    let nvs = EspDefaultNvsPartition::take().unwrap();
    // Starting Wifi in SysLoop
   let mut wifi_driver = EspWifi::new(
        peripherals.modem,
        sys_loop,
        Some(nvs)
    ).unwrap();
    let ss: String<32> = String::try_from(WIFI_SSID).unwrap();
    let pa: String<64> = String::try_from(WIFI_PASS).unwrap();
    wifi_driver.set_configuration(&Configuration::Client(ClientConfiguration{
        ssid: ss.into(),
        password: pa.into(),
        ..Default::default()
    })).unwrap();
    wifi_driver.start().unwrap();
    wifi_driver.connect().unwrap();
    while !wifi_driver.is_connected().unwrap(){
        let config = wifi_driver.get_configuration().unwrap();
        log::info!("Waiting for station {:?}", config);
    }
    log::info!("Should be connected now");
    //Initiating MDNS Service and Searching for Server IP :: BROKEN
    //Search is needed otherwise WIFI IP is not ready
    let mdns = mdns::EspMdns::take().unwrap();
    let server_ip = mdns.query_a("_spirit", Duration::new(10, 0));
    match server_ip {
        Ok(ip) => {log::info!("Found IP: {:?}" ,ip);}
        Err(e) => {log::info!("{:?}", e);}
    }
    //Binding to UDP Socket Port doenst realy matter
    let udp_socket = UdpSocket::bind("0.0.0.0:1234").expect("couldn't bind to address");
    let mut index = 0;
    log::info!("Running....");
    loop {
        index = index + 1;
        let gyro = mpu.get_gyro().unwrap();
        let acc = mpu.get_acc().unwrap();
        {
            let buffer = format!("{{\"position\": \"RBL\", \"index\": {:?}, \"data\":[{:?},{:?},{:?},{:?},{:?},{:?}]}}", index, acc[0], acc[1], acc[2], gyro[0], gyro[1], gyro[2]);
            let buffer_bytes = buffer.into_bytes();
            let socket_result = udp_socket.send_to(&buffer_bytes, "192.168.189.245:1234");
            match socket_result {
                Ok(_) => {}
                Err(e) => {log::info!("{:?}", e);}
            }
            drop(buffer_bytes);
        }

    }

}

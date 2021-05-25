#!/usr/bin/env python

import bme680
import time
import tsys01
import json
import socket
import csv
import os
import logging
from decouple import config
import sys
import psutil
from PIL import Image,ImageDraw,ImageFont
import mysql.connector

curr_dir = os.getcwd()
print(curr_dir)
sys.path.insert(1, curr_dir + '/build/lib/waveshare_epd/')

import epd2in13b_V3


picdir = curr_dir + "/pic"
libdir = curr_dir + "/build/lib/"


if os.path.exists(libdir):
    sys.path.append(libdir)

time.sleep(15)
verbose = config('VERBOSE')
if verbose is None:
    verbose = 0
if __name__ == "__main__":
    if verbose:
        logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
mydb = mysql.connector.connect(
host=config('MYSQL_SERVER_IP'),
user=config('MYSQL_SERVER_USERNAME'),
password=config('MYSQL_SERVER_PASSWORD'),
database=config('MYSQL_SERVER_DATABASE'),
auth_plugin='mysql_native_password'
)
varTempValue = 0.0
varHumidValue = 0.0
duration = int(config('DURATION')) # seconds
firstRun = True
hostName = socket.gethostname()
startTime = time.time()
cursor = mydb.cursor()
cursor.execute(f"SELECT * FROM sensor_settings WHERE sensor='{hostName}'")
myresult = cursor.fetchall()


font20 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
font18 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 18)
font16 = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 16)


UDP_IP = str(config('SERVER_IP'))
UDP_PORT = int(config("PORT"))
print("UDP target IP: %s" % UDP_IP)
print("UDP target port: %s" % UDP_PORT)
sock = socket.socket(socket.AF_INET, # Internet
		  socket.SOCK_DGRAM) # UDP
sock.connect(("8.8.8.8", 80))
ip_addr = sock.getsockname()[0]

# a Python object (dict):
jsonData = {
	"SERVER": hostName,
	"TEMP": 0,
	"HUMID": 0,
	"TIME" : 0
}

def temp_read():
    sensor = tsys01.TSYS01(3)

    if not sensor.init():
        print("Error initializing sensor")
        exit(1)

    if not sensor.read():
        print("Error reading sensor")
        exit(1)
    return sensor.temperature()

def hum_read():
    #Henter luftfuktighet fra Bme Sensor
    try:
        sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
    except IOError:
        sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

    sensor.set_humidity_oversample(bme680.OS_2X)

    if sensor.get_sensor_data():
                output = sensor.data.humidity
                return output

def collect_data():
    varTempValue = temp_read()
    varHumidValue = hum_read()

    jsonData['TEMP'] = varTempValue
    jsonData['HUMID'] = varHumidValue
    jsonData['TIME'] = int(time.time())
    jsonString = json.dumps(jsonData)
    print(jsonString)
    try:
        sock.sendto (bytes(jsonString, 'utf-8'), (UDP_IP, UDP_PORT))
    except Exception as e: 
        print("Error :", e)
        pass

def createWriteCsv():
    from datetime import datetime
    import os.path


    today = datetime.today().strftime('%m%d%y')
    fileName = today + hostName + ".csv"

    sensor = hostName
    temp = temp_read()
    hum = hum_read()
    tidsangivelse = int(time.time())

    directory = r"/home/pi/bin/csv/"
    if not os.path.exists(directory):
        os.mkdir(directory)

    if os.path.isfile(os.path.join(directory, fileName)):
        print('Todays file is created')
    else:
        f = open(os.path.join(directory, fileName), mode="w")
        writer = csv.DictWriter(
        f, fieldnames=[hostName, "temp", "hum", "tidsangivelse"])
        writer.writeheader()
        f.close()

    fieldsWrite=[sensor, temp, hum, tidsangivelse]
    with open(os.path.join(directory, fileName), mode='a') as f:
        writer = csv.writer(f)
        writer.writerow(fieldsWrite)
        print(fieldsWrite)


def ip_address_text():
    try:
        result = "IP Addresse: " + str(ip_addr) + "\nPORT: " + str(UDP_PORT) + "\nRom: " + myresult[0][1]
        return result
    except:
        result = "Ip addresse feil"
        return result

def temp_text():
    try:
        result = "Temperatur: %.2f °C" % temp_read()
        return result
    except:
        result = "Klima variabel feil"
        return result

def hum_text():
    try:
        result = "Luftfuktighet: %.2f" % hum_read() + "%"
        return result
    except:
        result = "Klima variabel feil"
        return result

def show_text(epd, top_text='', middle_text='', bottom_text=''):
    sensor_settings = {
        "alias": myresult[0][1],
        "tempUpper": myresult[0][2],
        "tempLower": myresult[0][3],
        "humidUpper": myresult[0][4],
        "humidLower": myresult[0][5]
    }
    temp = temp_read()
    hum = hum_read()

    HBlackImage = Image.new('1', (epd2in13b_V3.EPD_HEIGHT, epd2in13b_V3.EPD_WIDTH), 255)
    HRedImage = Image.new('1', (epd2in13b_V3.EPD_HEIGHT, epd2in13b_V3.EPD_WIDTH), 255)

    # render the black section
    black_draw = ImageDraw.Draw(HBlackImage)
    black_draw.text((1, 1), top_text, font=font16, fill=0)

    # calculate the depth of the black section
    top_depth = black_draw.textsize(top_text, font=font16)[1] + 5

    # render the red section under the black section
    if(temp > sensor_settings["tempUpper"] or temp < sensor_settings["tempLower"]):
        red_draw = ImageDraw.Draw(HRedImage)
        red_draw.text((1, top_depth), middle_text, font=font20, fill=0)
    else:
        black_draw.text((1, top_depth), middle_text, font=font20, fill=0)

    if(hum > sensor_settings["humidUpper"] or hum < sensor_settings["humidLower"]):
        red_draw = ImageDraw.Draw(HRedImage)
        red_draw.text((1, top_depth + 20), bottom_text, font=font20, fill=0)
    else:
        black_draw.text((1, top_depth + 20), bottom_text, font=font20, fill=0)


    epd.display(epd.getbuffer(HBlackImage), epd.getbuffer(HRedImage))


def main_display():
    try:
        epd = epd2in13b_V3.EPD()
        logging.info("init and Clear")
        epd.init()
        epd.Clear()
        time.sleep(1)

        show_text(epd, top_text=ip_address_text(), middle_text=temp_text(), bottom_text=hum_text())

        epd.sleep()
            
    except IOError as e:
        logging.info(e)
        sys.exit()
        
    except KeyboardInterrupt:    
        logging.info("ctrl + c:")
        epd2in13b_V3.epdconfig.module_exit()
        sys.exit()


while (True):
    if firstRun:
        collect_data()
        createWriteCsv()
        main_display()
        firstRun = False

    if time.time() - startTime >= duration:
        startTime = time.time()
        collect_data()
        createWriteCsv()
        main_display()

    time.sleep(1)


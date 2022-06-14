#Kundenauftrag "Bankfiliale"
#Tammo Baum, ETS2021, 14.06.2022

#Eine Lichtschranke steuert als Bewegungsmelder die Beleuchtung einer Bankfiliale und zaehlt die Anzahl der Personen in der Bank
#Das Licht wird durch eine gelbe LED symbolisiert. 
#Die Temperatur der Filiale soll auf einer Matrixanzeige ausgegeben werden und bei überschreiten einer gewissen Temperatur soll ein Luefter, 
#durch eine rote LED symbolisiert, eingeschaltet werden und die Temperatur runterkühlen. Bei Erreichen der WunschTemperatur geht der Luefter wieder aus.
#Die Daten sollen in einer HandyApp abrufbar sein. So steht die Personenanzahl auf dem Display und auch welchen Zustand der Luefter oder die Beleuchtung hat. 
#Zusaetzlich sollen die Daten in eine Datenbank geschrieben und gespeichert werden. 


#Hardware: BMP180(scl=Pin22,sda=Pin21), ESP32TTG0, rote_Led=Pin25, gelbe_Led=Pin27, 
#          Matrix Anzeige(CLK=Pin15,DIN=Pin13,CS=Pin2), Lichtschranke E3F-R2NK=Pin26

#Bibliotheken: bmp.py -> in der ReadMe Datei

#-----------------------Initialisierung Start------------------------------------------------------------------

from bmp180 import BMP180                       
from machine import SoftI2C, Pin, SPI       # Pin (BMP180, TFT) - SoftSPI (TFT) - SoftI2C (BMP180)
from umqtt.simple import MQTTClient
import time     
import max7219      
import network
import json

#MQTT_SERVER = "192.168.1.237"  #IP IoT                 #Aufsetzen des MQTT Servers 
MQTT_SERVER = "192.168.0.2"     #IP Privat
CLIENT_ID = "MQTT_BAUM"
MQTT_TOPIC_TEMP_DATA = "Oldenburg/BankX/Daten"

i2c = SoftI2C(scl=Pin(22), sda=Pin(21))                 #i2c bmp180
bmp = BMP180(i2c)

lichtschranke = Pin(26, Pin.IN)                         #Pinbelegung definieren
led_Beleuchtung = Pin(27, Pin.OUT)
led_Luefter = Pin(25, Pin.OUT)

spi = SPI(1, baudrate=100000, polarity=1, phase=0, sck=Pin(15), mosi=Pin(13))    #sck=CLK mosi=DIN ss=cs
cs = Pin(2)

pers_count = 0                                          #Variabeln für Zaehler und Beleuchtung 
was_off_before = True
led_beleuchtung_an = False

display = max7219.Matrix8x8(spi,cs,4)                   #Display aufsetzen
display.brightness(10)

#-----------------------Initialisierung Ende-------------------------------------------------------------------

#-----------------------Netzwerkkonfigurierung Start-----------------------------------------------------------

wlan = network.WLAN(network.STA_IF)     

wlan.active(True)                       

if not wlan.isconnected():              

    wlan.connect("LAN Boehmermann", "FestundFlauschig2022")    #Netzwerk Privat
#    wlan.connect("BZTG-IoT", "WerderBremen24")                  #Netzwerk IoT

    while not wlan.isconnected():                   

        pass

    print("Netzwerkkonfiguration: ", wlan.ifconfig())       #Netzwerkinfos ausgeben (IP Adresse, Subnetzmaske, Gateway, DNS-Server)

#-----------------------Netzwerkkonfigurierung Ende-------------------------------------------------------

#-----------------------Endlosschleife Start--------------------------------------------------------------
while True:
    mqtt_Baum = MQTTClient(CLIENT_ID, MQTT_SERVER)          #MQTT Server verbinden
    mqtt_Baum.connect()
   
    eingang = lichtschranke.value()                         #Abfrage Lichtschrankensignal 1 -> 0 da Oeffnersignal
    if eingang and was_off_before:                          
        was_off_before = False                              
        time.sleep(0.5)                                            
    if not eingang:                                         
        pers_count += 1                                     #Zaehlvorgang Kunden
        was_off_before = True

    print("personen_Anzahl einfach", pers_count)
    int(pers_count)
    pers_countEnd = int(pers_count / 2)                     #Zaehlvorgang Kunden durch 2 dividieren um Ein und Austritt zu beruecksichtigen

    print("Personenanzahl Ganz :", pers_countEnd)

    
    if pers_count % 2 != 0 or pers_count == 1:              #Anzeige Beleuchtung gelbe LED bei Betreten = 1, Verlassen = 0
        led_Beleuchtung.value(1)
    else:
        led_Beleuchtung.value(0)

#-----------Auswertung Temperatur Messwerte Start------------------------

    display.fill(0)
    messwerte_bmp = []
    temp_bmp = int(bmp.temperature)

    for i in range(0,5):
        messwerte = round(bmp.temperature,2)
        messwerte_bmp.append(messwerte)

    messwerte_bmp.sort()
    del messwerte_bmp[0]
    messwerte_bmp.pop

    ausgabe = round((sum(messwerte_bmp) / len(messwerte_bmp)),2)
    ausgabe_matrix = int(ausgabe)
    print("DurchschnittsTemp:",ausgabe_matrix)

#-----------Auswertung Temperatur Messwerte Ende------------------------

    display.fill(0)                                    #Ausgabe Temperatur LED-Matrix
    display.text(str(ausgabe_matrix) +" C",0,0,1)       
    display.fill_rect(19,0,2,2,1)                       
    display.show()                                      
 
    if  ausgabe_matrix >= 24:                          #Anzeige Luefter rote LED
        led_Luefter.value(1)                            
        print("Luefter an")                            
    elif ausgabe_matrix <= 22:                                              
        led_Luefter.value(0)                           
        print("Luefter aus")                           
 

    data_Werte = {                                     #Ausgabe der Daten in JSON Format
       "BankX" :[
            {
                "Temperatur": temp_bmp,

                "Anzeige_Luefter": led_Luefter.value(),

                "led_Beleuchtung": led_Beleuchtung.value(),

                "Kunden_Zahl": pers_countEnd
            }
        ]    
    }


    print("MQTT verbunden!")

    mqtt_Baum.publish(MQTT_TOPIC_TEMP_DATA, json.dumps(data_Werte))          #Publishen der Daten
    mqtt_Baum.disconnect()

#-----------------------Endlosschleife Ende--------------------------------------------------------------




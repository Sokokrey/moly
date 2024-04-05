### LIBRARIES ###

import cv2
import numpy as np
import pandas as pd
import time
import imagezmq
import json
import os 
import pathlib
from random import randint
from datetime import datetime, timedelta
from threading import Timer

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

import tkinter as tk
from tkinter import Tk
from tkinter import ttk
from tkinter.constants import *
from tkcalendar import *
import PIL
from PIL import Image, ImageFont, ImageTk, ImageDraw

import paho.mqtt.client as paho

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import pyplot
from matplotlib.pyplot import text
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation

import pickle

### GLOBAL VARIBLES ###

path    = pathlib.Path(__file__).parent.absolute() #Variable que guarda el path actual
db      = '' #Variable que almacena la base de datos
broker  = "10.0.2.40"
port    = 1883
pba     = None # Instancia de la clase principal Ventana
flag_selector = 0  # Variable auxiliar para determinar si puede consultarse el python que obtiene el estado actual del selector (MANUAL o AUTOMATICO)
flag_confirmacion = 0 #Se vuelve 1 cuando los valores propuestos alcanzan el valor que tenian consignado, vuelve a 0 una vez terminan de aplicarse los ajustes
fontpath      = "Helvetica.ttc" # Font para escribir en las imágenes que se muestran en los paneles

######################################### Pendiente #############################################
#################################################################################################
#################################################################################################

class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

def check_selector():
    global pba
    global client1
    if pba is not None:
        if flag_selector == 0:
            #os.system("sudo python3 ser.py")
            with open(str(path)+'/selector.log') as f: #Archivo modificado por node-red
                modo_general = f.read(1)

            #pba.change_modo_ajustes(modo_general)

        with open('/home/molly/params_act.log') as f: #Archivo modificado por node-red
            ajustes = f.read(1)

        #print(ajustes)



        
        #print(pba.ajustes)

        #pba.actualizar_ajustes_actuales(ajustes)
        #pba.actualizar_plot_ajustes(ajustes)



rt = RepeatedTimer(5, check_selector)


#################################################################################################
#################################################################################################
#################################################################################################

def nothing(self):
    pass

# Para truncar valores decimales
def truncate(num, decimal):
    my_digits = 10**decimal  #raise 10 to the number of decimal places
    #shifting the decimal part and converting to integer
    int_val = int(num* my_digits)
    #return the truncated value
    return int_val/my_digits

##########################  MQTT Functions ###################################
def error_publish(self, error, intensity):
    pass

def on_message(client, userdata, message):
    global pba  
    if pba is not None:
        #print(str(message.payload), message.topic)
        if message.topic == 'node/ajustes_propuestos': #Ajustes Propuestos
            
            ajuste = json.loads(message.payload)
            #print('Propuestos'+str(ajuste))
            pba.variar_ajustes_propuestos(ajuste)

        elif message.topic == 'node/ajustes_actuales': #Ajustes Actuales
            #if pba.bolas_pasando:
            print('MQTT ACTUALESSS')
            ajuste = json.loads(message.payload)
            pba.actualizar_ajustes_actuales(ajuste)
            pba.actualizar_plot_ajustes(ajuste)

        elif message.topic == 'node/tamaño_actual': #Ajustes Actuales
            res = json.loads(message.payload)
            
            if float(res['bola']) != float(pba.produccion_bola.get()):
                if float(res['bola']) == 1.0:
                    new_exposure_time = 3000
                elif float(res['bola']) == 1.25:
                    new_exposure_time = 3225
                elif float(res['bola']) == 1.5:
                    new_exposure_time = 3450
                elif float(res['bola']) == 2.0: 
                    new_exposure_time = 3850
                elif float(res['bola']) == 2.5:
                    new_exposure_time = 4000
            
                pba.produccion_bola.set(float(res['bola']))
                pba.auto_exposure_adjustment(new_exposure_time)

        elif message.topic == 'node/limites_pernos': 
            limites = json.loads(message.payload)
            pba.actualizar_limites_pernos(limites)

        elif message.topic == 'node/parametros_produccion': 
            parametros_produccion = json.loads(message.payload)
            pba.actualizar_parametros_produccion(parametros_produccion)

        elif message.topic == 'node/status_a': 
            
            val_cam1 = pba.ajustes_actuales[0]["value"]["text"] == pba.aux_ajustes_propuestos[0]
            val_cam2 = pba.ajustes_actuales[1]["value"]["text"] == pba.aux_ajustes_propuestos[1]
            val_cam3 = pba.ajustes_actuales[2]["value"]["text"] == pba.aux_ajustes_propuestos[2]
            val_cam4 = pba.ajustes_actuales[3]["value"]["text"] == pba.aux_ajustes_propuestos[3]
            val_per1 = pba.ajustes_actuales[4]["value"]["text"] == pba.aux_ajustes_propuestos[4]
            val_per2 = pba.ajustes_actuales[5]["value"]["text"] == pba.aux_ajustes_propuestos[5]
            val_per3 = pba.ajustes_actuales[6]["value"]["text"] == pba.aux_ajustes_propuestos[6]
            val_per4 = pba.ajustes_actuales[7]["value"]["text"] == pba.aux_ajustes_propuestos[7]
            
            #print(val_cam1, val_cam2, val_cam3, val_cam4, val_per1, val_per2, val_per3, val_per4)          


            if ((val_cam1) and (val_cam2) and(val_cam3) and(val_cam4) and(val_per1) and(val_per2) and(val_per3) and(val_per4)):               
                pba.aplicar.config(text ="Esperando \n Ajustes",  font=("Helvetica", 7, "bold"), height = 3 , width = 9, bg='#bac4cf', fg='black')
                pba.flag_confirmacion = 0
            else:
                pba.aplicar.config(text='Aplicando...', bg='gray', state=DISABLED)

            status = json.loads(message.payload)
            if int(status["status"]) == 0:
                if 'perno' in status['id']: 
                    pba.finalizar_ajuste(status)
                else:
                    pba.liberar_ajuste(status)
            
            elif int(status["status"]) == 1:
                pba.apretar_ajuste(status)
            elif int(status["status"]) == 2:
                pba.aflojar_ajuste(status)

        elif message.topic == 'node/fallas': # Fallas en alguno de los pernos / camones
            fallas = json.loads(message.payload)
            #pba.actualizar_fallas(fallas)

##############################################################################

####################### MQTT SUSCRIPTIONS ####################################

client1= paho.Client("control1")    #create client object
client1.on_publish = error_publish     #assign function to callback
client1.on_message= on_message                      #attach function t
#client1.connect(broker,port)        #establish connection (arroaj un error , el equipo de destino rechaza la conexión)
client1.loop_start()        #start the loop
client1.subscribe('node/limites_pernos')
client1.subscribe('node/ajustes_propuestos')
client1.subscribe('node/ajustes_actuales')
client1.subscribe('node/tamaño_actual')
client1.subscribe('node/parametros_produccion')
client1.subscribe('node/status_a')
client1.subscribe('node/fallas')

##############################################################################

######################### VENTANA PRINCIPAL ##################################

class Ventana(tk.Tk):

    def __init__(self):
        #Dimensiones y configuracion del panel
        self.win2 = tk.Tk()
        self.win2.title("MOLYCOP - RF2 IA/VA")  # set window title
        self.win2.geometry("1020x710")
        self.win2.resizable(width=False, height=False)
        self.win2.config(cursor="arrow")
        self.win2['bg'] = '#828282'
        
        #Estilo para las tablas de historicos
        self.style=ttk.Style()
        self.style.configure("Treeview", background="silver", foreground="black", rowheight=25, fieldbackground="silver") 
        
        #CONFIGURACION DE PESTAÑAS
        self.notebook = ttk.Notebook(self.win2)

        self.operador_tab = ttk.Frame(self.notebook)
        self.admin_tab = ttk.Frame(self.notebook)
        self.tendencias_tab = ttk.Frame(self.notebook)
        self.historicos_tab = ttk.Frame(self.notebook)
        self.inferencias_tab = ttk.Frame(self.notebook)
        self.camones_tab = ttk.Frame(self.notebook)
        self.pernos_tab = ttk.Frame(self.notebook)

        #Pestaña de Operador
        canvas = tk.Canvas(self.operador_tab, width=1920, height=800, borderwidth=0, highlightthickness=0, bg="#828282")
        canvas.create_rectangle(5, 5, 205, 530, outline="#302f2f", width=2, fill="#737272")
        canvas.create_rectangle(5, 535, 205, 680, outline="#302f2f", width=2, fill="#737272")
        canvas.create_rectangle(210, 5, 1015, 530, outline="#302f2f", width=2, fill="#737272")
        canvas.create_rectangle(210, 535, 1015, 680, outline="#302f2f", width=2, fill="#737272")

        canvas.create_line(210, 560, 1015, 560, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(210, 620, 1015, 620, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(382, 535, 382, 680, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(450, 535, 450, 680, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(518, 535, 518, 680, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(588, 535, 588, 680, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(659, 535, 659, 680, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(728, 535, 728, 680, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(798, 535, 798, 680, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(868, 535, 868, 680, fill='#%02x%02x%02x' % (35,50,35))
        canvas.create_line(937, 535, 937, 680, fill='#%02x%02x%02x' % (35,50,35))
                                                       
        canvas.grid()

        self.notebook.add(self.operador_tab, text="Operador")

        #Pestaña de Administrador
        canvas2 = tk.Canvas(self.admin_tab, width=1920, height=800, borderwidth=0, highlightthickness=0, bg="#828282")
        canvas2.create_rectangle(5, 5, 1010, 70, outline="#302f2f", width=2, fill="#737272")
        canvas2.create_rectangle(5, 75, 370, 625, outline="#302f2f", width=2, fill="#737272")
        canvas2.create_rectangle(375, 75, 1010, 440, outline="#302f2f", width=2, fill="#737272")
        canvas2.create_rectangle(375, 445, 1010, 625, outline="#302f2f", width=2, fill="#737272")

        canvas2.create_rectangle(5, 630, 370, 680, outline="#302f2f", width=2, fill="#737272")
        canvas2.create_rectangle(375, 630, 1010, 680, outline="#302f2f", width=2, fill="#737272")
        canvas2.grid()

        self.notebook.add(self.admin_tab, text="Administrador")

        #Pestaña de Tendencias
        canvas3 = tk.Canvas(self.tendencias_tab, width=1920, height=800, borderwidth=0, highlightthickness=0, bg="#737272")
        canvas3.grid()

        self.notebook.add(self.tendencias_tab, text="Tendencias")

        #Pestaña de Historicos
        canvas4 = tk.Canvas(self.historicos_tab, width=1920, height=800, borderwidth=0, highlightthickness=0, bg="#828282")
        canvas4.create_rectangle(5, 5, 565, 240, outline="#302f2f", width=2, fill="#737272")
        canvas4.create_rectangle(570, 5, 1010, 240, outline="#302f2f", width=2, fill="#737272")
        canvas4.create_rectangle(5, 250, 1010, 670, outline="#302f2f", width=2, fill="#737272")
        canvas4.grid()

        self.notebook.add(self.historicos_tab, text="Historicos")

        #Pestaña de Inferencias
        canvas5 = tk.Canvas(self.inferencias_tab, width=1920, height=800, borderwidth=0, highlightthickness=0, bg="#828282")
        canvas5.create_rectangle(5, 5, 280, 335, outline="#302f2f", width=2, fill="#737272")
        canvas5.create_rectangle(5, 340, 280, 680, outline="#302f2f", width=2, fill="#737272")
        canvas5.create_rectangle(285, 5, 1015, 245, outline="#302f2f", width=2, fill="#737272")
        canvas5.create_rectangle(285, 250, 1015, 680, outline="#302f2f", width=2, fill="#737272")
        
        canvas5.create_rectangle(5, 340, 190, 495, fill='#%02x%02x%02x' % (250, 227, 125))
        canvas5.create_rectangle(190, 340, 280, 495, fill='#%02x%02x%02x' % (169, 183, 252))

        canvas5.create_line(5, 375, 280, 375, fill='#%02x%02x%02x' % (35,50,35))
        canvas5.create_line(5, 405, 280, 405, fill='#%02x%02x%02x' % (35,50,35))
        canvas5.create_line(5, 435, 280, 435, fill='#%02x%02x%02x' % (35,50,35))
        canvas5.create_line(5, 465, 280, 465, fill='#%02x%02x%02x' % (35,50,35))
        canvas5.create_line(5, 495, 280, 495, fill='#%02x%02x%02x' % (35,50,35))

        canvas5.grid()

        self.notebook.add(self.inferencias_tab, text="Inferencias")

        #Pestaña de Grafico de Camones
        canvas6 = tk.Canvas(self.camones_tab, width=1920, height=800, borderwidth=0, highlightthickness=0, bg="#737272")
        canvas6.grid()

        self.notebook.add(self.camones_tab, text="Camones")

        #Pestaña de Grafico de Pernos
        canvas7 = tk.Canvas(self.pernos_tab, width=1920, height=800, borderwidth=0, highlightthickness=0, bg="#737272")
        canvas7.grid()

        self.notebook.add(self.pernos_tab, text="Pernos")
        
        self.win2.bind("<<NotebookTabChanged>>", self.change_tab) #Funcion que se gatilla al cambiar de pestaña
        self.notebook.grid(column=0, row=0) #Instancia las pestañas

        #Variables auxiliares
        self.color  = ['#389393', '#0067cf', '#ffb01f', '#ffff1f', '#a8f70a', '#8f1f8f', '#b04444'] #Colores de los defectos
        self.contador_bolas = 0 #Conteo de bolas por minuto
        self.bolas_pasando = False #Indica si está la línea de producción activa o no en base al contador de bolas
        self.flag_pasando = 0 #En caso de que halla estado sin pasar y derrepente vuelva

        #######################################################################################################################################################################
        ##################################################################   PESTAÑA OPERADOR  ################################################################################
        #######################################################################################################################################################################

        move_y = 5 #Variable auxiliar para posicionar elementos

        #Hora Actual
        self.var_hora = tk.StringVar()
        tk.Label(self.operador_tab, font=("Helvetica", 14), width = 19, height=2, textvariable=self.var_hora, bd="3", relief=SUNKEN, fg="#f5f5f5", bg="#1c1c1f", highlightthickness=1, highlightbackground="#202424", borderwidth=3).place(x=6,y=move_y)
        
        move_y += 40
        
        # Parametros o factores de produccion
        parametros_produccion = db.historico_produccion.find().sort("_id", -1).limit(1)[0]
        
        self.TT_ROD = parametros_produccion['TT_ROD']
        self.TT_SBR = parametros_produccion['TT_SBR']
        self.TONS_HORA = parametros_produccion['TONS_HORA']
        self.VEL_MOTOR = parametros_produccion['VEL_MOTOR']

        # Produccion de bola: 1", 1.5", 2.0", 2.5" (Rara vez 1.25")
        self.produccion_bola = tk.StringVar()
        self.produccion_bola.set(float(db.presencia.find_one()["tamaño"]))
        tk.Label(self.operador_tab, font=("Helvetica", 10), bd="3", relief=SUNKEN, width = 27, height=1, text='Producción de Bola:           "', fg="black", bg="#f0871f", highlightthickness=1, highlightbackground="#202424", borderwidth=3).place(x=6,y=move_y)
        tk.Label(self.operador_tab, font=("Helvetica", 10), bd="3", relief=SUNKEN, width = 3, height=1, textvariable=self.produccion_bola, fg="black", bg="#f0871f", highlightthickness=0, highlightbackground="#202424", borderwidth=0).place(x=160,y=move_y+4)
        
        #Cota de alarma
        move_y += 20
        alarma = db.alarma.find_one()

        self.cota_alarma = tk.StringVar()
        self.cota_alarma.set(int(alarma["umbral"])) #Cota de alarma de intensidad de detecto para gatillar alarma
        tk.Label(self.operador_tab, font=("Helvetica", 10), bd="3", relief=SUNKEN, width = 27, height=1, text='Cota de Alarma:               %', fg="black", bg="#db4425", highlightthickness=1, highlightbackground="#202424", borderwidth=3).place(x=6,y=move_y)
        tk.Label(self.operador_tab, font=("Helvetica", 10), bd="1", width = 3, height=1, textvariable=self.cota_alarma, fg="black", bg="#db4425", highlightthickness=0, highlightbackground="#202424", borderwidth=0).place(x=155,y=move_y+4)
        
        move_y += 20
        
        #Razón de inferencias actual
        self.razon_inferencias = tk.StringVar()
        self.razon_inferencias.set(int(alarma["razon_inferencias"])) #Razón de inferencias para gatillar alarma. Razon = Inferencias positivas / Inferencias totales         
        
        tk.Label(self.operador_tab, font=("Helvetica", 10), bd="3", relief=SUNKEN, width = 27, height=1, text='Razón de inferencias:       %', fg="black", bg="#71a8f0", highlightthickness=1, highlightbackground="#202424", borderwidth=3).place(x=6,y=move_y)
        tk.Label(self.operador_tab, font=("Helvetica", 10), bd="1", relief=SUNKEN, width = 3, height=1, textvariable=self.razon_inferencias, fg="black", bg="#71a8f0", highlightthickness=0, highlightbackground="#202424", borderwidth=0).place(x=155,y=move_y+4)

        move_y += 25

        #Numero de constancias de defectos realizadas por los operadores durante el día
        self.cont_constancias = db.constancia.count_documents(
            { "$expr": 
                { "$and" : 
                    [  
                        { "$eq": [{ "$month": "$fecha" }, datetime.now().month ] },  
                        { "$eq": [{ "$year": "$fecha" }, datetime.now().year ] },
                        { "$eq": [{ "$dayOfMonth": "$fecha" }, datetime.now().day ] }
                    ] 
                } 
            }
        )

        #Boton que va cambiando con la cantidad de defectos informados en el día
        self.btn_defectos_informados = tk.Button(self.operador_tab, font=("Helvetica", 10), width = 24, height=1, text='Informados Hoy: {0}'.format(self.cont_constancias), fg="#cdc9c3", bg="#2a2b2e", highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.mostrar_informados())
        self.btn_defectos_informados.place(x=6,y=move_y)

        move_y += 30

        #Titulos para el Listado con las opciones de Defecto.
        tk.Label(self.operador_tab, font=("Helvetica", 13, "bold"), text='Defecto', fg="black", bg="#737272").place(x=10,y=move_y+5)
        tk.Label(self.operador_tab, font=("Helvetica", 8, "bold"), text='(%) de presencia', fg="black", bg="#737272").place(x=110,y=move_y+5)
        
        move_y += 10

        #Listado con los tipos de defecto
        self.tipos_defecto = list(db.defecto.find().sort("num"))
        self.listar_tipos_defecto()

        move_y = 540
        tk.Label(self.operador_tab, font=("Helvetica", 15,'bold'), text='Modo', fg="black", bg="#737272").place(x=10,y=move_y) #Label modo de Entrenamiento

        #Botones manual/automatico
        move_y += 35
        self.automatico_ = tk.Button(self.operador_tab, height = 1, width = 20, text ="Automatico", bg='gray', highlightthickness=1, highlightbackground="#202424", command = lambda: self.change_modo_ajustes(1))
        self.automatico_.place(x=10,y=move_y)

        move_y += 45
        self.manual_ = tk.Button(self.operador_tab, height = 1 , width = 20, text ="Manual", bg='green', highlightthickness=1, highlightbackground="#202424", command = lambda: self.change_modo_ajustes(0))
        self.manual_.place(x=10,y=move_y)
        
        #Modo de aplicación de ajustes (MANUAL/AUTOMATICO)
        self.ajustes_mode = 0
        
        # Grafico de la parte superior derecha
        query = db.historico_defecto.find().sort("_id", -1).limit(60)
        
        intensidades = { "ecuador": [], "tipo_huevo": [], "lamina": [], "ojo":[], "desgarro_de_polo":[], "tetilla":[] }
        for x in query:
            intensidades["ecuador"].append(int(x["ecuador"]))
            intensidades["tipo_huevo"].append(int(x["tipo_huevo"]))
            intensidades["lamina"].append(int(x["lamina"]))
            intensidades["ojo"].append(int(x["ojo"]))
            intensidades["desgarro_de_polo"].append(int(x["desgarro_de_polo"]))
            intensidades["tetilla"].append(int(x["tetilla"]))
        
        self.arr_tendencias_1m = intensidades
        
        self.fig, self.ax = plt.subplots(figsize=(7.9,0.6))
        self.fig.patch.set_facecolor('#737272')
        
        self.ax.plot(1,1, '--r',  linewidth = 0.8) #Para los max ticks
        
        segundos = mdates.SecondLocator(interval=60)
        self.ax.xaxis.set_major_locator(segundos)
        
        self.chart = FigureCanvasTkAgg(self.fig, self.operador_tab)
        self.chart.get_tk_widget().place(x=215, y=15)
        
        plt.xticks(rotation=90, fontsize=1)
        plt.subplots_adjust(left=0.04, bottom=0.1, right=1, top=0.95, wspace=0, hspace=0)
        plt.grid()

        move_y = 80

        #CARGAR PANEL VIDEO
        negro = np.zeros([455,545,3],dtype=np.uint8)
        negro = Image.fromarray(negro)
        img   = ImageTk.PhotoImage(image=negro)  # convert image for tkinter

        self.panel = tk.Label(self.operador_tab, width=540, height=445)  # initialize video panel
        self.panel.imgtk3 = img  # anchor imgtk so it does not be deleted by garbage-collector
        self.panel.place(x=215,y=move_y)
        self.panel.config(image=img)  # show the image

        #CARGAR PANEL CAPTURAS
        negro = np.zeros([400,400,3],dtype=np.uint8)
        cv2.putText(negro, 'Ultima captura', (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (255, 200, 100), 1)
        
        negro = Image.fromarray(negro)
        img   = ImageTk.PhotoImage(image=negro)  # convert image for tkinter

        self.panel2 = tk.Label(self.operador_tab, width=245, height=220)  # initialize detection panel
        self.panel2.imgtk3 = img  # anchor imgtk so it does not be deleted by garbage-collector
        self.panel2.place(x=765,y=move_y)
        self.panel2.config(image=img)  # show the image
        
        #CARGAR PANEL DETECTIONES
        move_y += 225
    
        all_inferencesdirs = [d for d in os.listdir('inferencias') if os.path.isdir('inferencias/'+d) ]
        all_inferencesdirs.sort()

        newest_inference_folder = all_inferencesdirs[len(all_inferencesdirs)-1]
        
        newest_inferences_files = [d for d in os.listdir('inferencias/'+newest_inference_folder) ]
        newest_inferences_files.sort()

        newest_inference = newest_inferences_files[0]

        imagen = cv2.imread('inferencias/'+newest_inference_folder+'/'+newest_inference)
        imagen = Image.fromarray(imagen)
        img    = ImageTk.PhotoImage(image=imagen)  # convert image for tkinter
        
        self.panel3 = tk.Label(self.operador_tab, width=245, height=220)  # initialize fail panel
        self.panel3.imgtk4 = img  # anchor imgtk so it does not be deleted by garbage-collector
        self.panel3.place(x=765,y=move_y) #130
        self.panel3.config(image=img)  # show the image

        #Label Ajustes
        move_y += 235
        tk.Label(self.operador_tab, font=("Helvetica",10,'bold'), text='AJUSTES', fg="black", bg="#737272").place(x=214,y=move_y)

        move_y += 8
        #Label Ajustes actuales
        tk.Label(self.operador_tab, font=("Helvetica", 10, 'bold'), text='Actuales:', fg='#%02x%02x%02x' % (82, 21, 117), bg="#737272").place(x=214,y=move_y+35)
        
        #Label Ajustes Propuestos
        tk.Label(self.operador_tab, font=("Helvetica", 10, 'bold'), text='Propuestos:', fg='#%02x%02x%02x' % (137,22,11), bg="#737272").place(x=214,y=move_y+80)
        
        move_x = 385
        
        # Arreglos que almacenan dinámicamente los valores de ajuste actuales y los propuestos
        
        self.ajustes_actuales = []
        self.ajustes_propuestos = []
        
        for i in range(8):
            text = 'CAMON'+str(i+1) if i < 4 else 'PERNO'+str(i-3)
            
            self.ajustes_actuales.append({"name": tk.Label(self.operador_tab, text=text, bg="#737272", font=("Helvetica",10,'bold')), "value": tk.Label(self.operador_tab, font=("Helvetica", 10), bg='#9c9797', height = 2, bd="3", width = 35, fg="black", relief=SUNKEN, text='', highlightthickness=1, highlightbackground="#202424", borderwidth=3) }) 
            self.ajustes_propuestos.append({"name": tk.Label(self.operador_tab, text=text, bg="#737272", font=("Helvetica", 10,'bold')), "value": tk.Label(self.operador_tab, font=("Helvetica", 10), bg='#9c9797', height = 2, bd="3", width = 35, fg="black", relief=SUNKEN, text='',  highlightthickness=1, highlightbackground="#202424", borderwidth=3 ) }) 

            self.ajustes_actuales[i]["name"].place(x=move_x, y=move_y-8)

            self.ajustes_actuales[i]["value"].place(x=move_x, y=move_y+25)
            self.ajustes_actuales[i]["value"].config(height = 1 , width = 7)

            self.ajustes_propuestos[i]["value"].place(x=move_x, y=move_y+90)
            self.ajustes_propuestos[i]["value"].config(height = 1 , width = 7)

            move_x += 70

        move_y -= 7

        #Boton para aplicar ajustes propuestos
        self.aplicar = tk.Button(self.operador_tab, text ="Esperando \n Ajustes",  font=("Helvetica", 7, "bold"), height = 3 , width = 9, bg='#bac4cf', fg='black')
        self.aplicar.place(x=940,y=move_y+85)

        ultimo_ajuste = db.historico_aplicados.find().sort("_id", -1).limit(1)[0]
        
        #Label fehca ultimo ajuste aplicado
        self.ultimo_aplicado = tk.Label(self.operador_tab, font=("Helvetica", 8, "bold"), text="Ultimo Ajuste: {0}".format(ultimo_ajuste["fecha"].strftime('%H:%M %d-%m-%y ')), fg='#%02x%02x%02x' % (0,0,11), bg="#737272")
        self.ultimo_aplicado.place(x=213,y=move_y+114)

        #######################################################################################################################################################################
        #####################################################################   PESTAÑA ADMIN  ################################################################################
        #######################################################################################################################################################################


        #Variable auxiliar para posicionar elementos
        move_y = 10
        
        #CARGAR LOGOS EMPRESAS
        logo_saut = Image.open(str(path)+'/img/logo-saut.png')
        logo_moly = Image.open(str(path)+'/img/logo-moly.png')
        
        width=731
        height=261

        relacion= 0.22
        logo_moly = logo_moly.resize((int(width*relacion), int(height*relacion)), Image.ANTIALIAS)
        logo_moly = ImageTk.PhotoImage(logo_moly)
        background_label= tk.Label(self.admin_tab, bg="#737272", image=logo_moly, borderwidth=0)
        background_label.image = logo_moly        
        background_label.place(x=15, y=move_y)

        relacion= 0.20
        logo_saut = logo_saut.resize((int(width*relacion), int(height*relacion)), Image.ANTIALIAS)
        logo_saut = ImageTk.PhotoImage(logo_saut)       
        background_label= tk.Label(self.admin_tab , bg="#737272", image=logo_saut, borderwidth=0)
        background_label.image = logo_saut        
        background_label.place(x=820, y=move_y)
        
        move_y=80
        
        # Labels para configuraciones de ajustes

        tk.Label(self.admin_tab, font=("Helvetica", 12, "bold"), text="Cota de alarma: ", fg="black", bg="#737272").place(x=10,y=move_y)
        tk.Label(self.admin_tab, font=("Helvetica", 12, "bold"), text="%", fg="black", bg="#737272").place(x=110,y=move_y+34)
        
        tk.Label(self.admin_tab, font=("Helvetica", 12, "bold"), text="Razon de inferencia: ", fg="black", bg="#737272").place(x=205,y=move_y)
        tk.Label(self.admin_tab, font=("Helvetica", 12, "bold"), text="%", fg="black", bg="#737272").place(x=320,y=move_y+34)

        tk.Label(self.admin_tab, font=("Helvetica", 12, "bold"), text="Tiempo de Respuesta (s): ", fg="black", bg="#737272").place(x=90,y=move_y+80)

        move_y = 135
        
        # Tiempo de respuesta en llegar un valor de ajuste actual en propuesto (En milisegundos)
        self.tiempo_respuesta = tk.Scale(self.admin_tab, width=11, length=200, bg='#%02x%02x%02x' % (214, 91, 17), from_=1, to=30, orient='horizontal',  highlightthickness=1, highlightbackground="#202424", borderwidth=3)
        self.tiempo_respuesta.place(x=90, y=move_y+45)
        
        configuracion = db.configuracion.find_one()
        self.tiempo_respuesta.set(int(configuracion['tiempo_respuesta']))
        
        # Defectos habilitados = Se graficarán y se contarán dentro de las inferencias. Defectos deshabilitados, = No son considerados dentro del proceso
        move_y+=115
        tk.Label(self.admin_tab, font=("Helvetica", 12, "bold"), text='Habilitar/Deshabilitar defectos', fg="black", bg="#737272").place(x=10,y=move_y)
        
        #MODO GENERAL
        with open(str(path)+'/selector.log') as f: #Archivo modificado por node-red
            modo_general = f.read(1)
        
        # Listado de los defectos pero en la Pestaña de Administrador
        move_y -= 35
        defectos = db.defecto.find({})
        for i, defecto in enumerate(self.tipos_defecto):
            if defecto['name'] != 'Sin Defecto':
                tk.Button(self.admin_tab, text=defecto["selector"]['text'], bg=self.color[i], bd="3", relief=SUNKEN, highlightthickness=1, highlightbackground="#202424", borderwidth=3, height = 1, width = 13, command = lambda: nothing(self)).place(x=10,y=move_y+i*60)

                self.tipos_defecto[i]['enabler'] = tk.Checkbutton(self.admin_tab, text="" , bd="3", relief=SUNKEN, variable= self.tipos_defecto[i]['checked'], highlightthickness=1, highlightbackground="#202424", height = 1, borderwidth=3, pady=5,  width = 3)
                self.tipos_defecto[i]["enabler"].place(x=142,y=move_y+i*60)

                if int(modo_general) == 0:
                    variable = tk.StringVar(value=str("AUTOMATICO"))
                else:
                    variable = tk.StringVar(value=str(defectos[i]["modo"]))

                self.tipos_defecto[i]["modo_selector"] = tk.OptionMenu(self.admin_tab, variable, "MANUAL", "AUTOMATICO")

                self.tipos_defecto[i]["modo_selector"].config(bd="3", relief=SUNKEN, highlightthickness=1, highlightbackground="#202424", height = 1, borderwidth=3)
                self.tipos_defecto[i]["modo_selector"].place(x=195, y=move_y+i*60,  height = 35, width = 165)

        # Para guardar configuración del entorno grafico
        self.save_admin_button = tk.Button(self.admin_tab, bg='orange', font=("Helvetica", 9, "bold"), text='Guardar cambios', highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.save_admin_config())
        self.save_admin_button.place(x=100,y=640)
        self.save_admin_button.config(height = 1, width = 16)

        # Para guardar configuración de la cámara
        self.save_camera_button = tk.Button(self.admin_tab, bg='orange', font=("Helvetica", 9, "bold"), text='Guardar cambios', highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.save_camera_config())
        self.save_camera_button.place(x=610,y=640)
        self.save_camera_button.config(height = 1, width = 16)
        
        #Tabla con las alarmas gatilladas durante el día
        move_y = 80
        tk.Label(self.admin_tab, font=("Helvetica", 12, "bold"), text="Últimas alertas arrojadas", fg="black", bg="#737272").place(x=390,y=move_y)

        move_y+=25
        #Tabla con las alarmas gatilladas durante el día
        self.tree_historicos_alarmas = ttk.Treeview(self.admin_tab, columns = (1,2,3), show = "headings")
        self.tree_historicos_alarmas.place(x=390, y=move_y, height=325)
        
        self.tree_historicos_alarmas.heading(1, text="Hora")
        self.tree_historicos_alarmas.heading(2, text="Defecto")
        self.tree_historicos_alarmas.heading(3, text="Intensidad")

        self.tree_historicos_alarmas.column(1, width = 175)
        self.tree_historicos_alarmas.column(2, width = 255)
        self.tree_historicos_alarmas.column(3, width = 155)

        query = db.historico_alarmas.find(
            { "$expr": 
                { "$and" : 
                    [  
                        { "$eq": [{ "$month": "$fecha" }, { "$month": datetime.now() }] },  
                        { "$eq": [{ "$year": "$fecha" }, { "$year": datetime.now() }] },
                        { "$eq": [{ "$dayOfMonth": "$fecha" }, { "$dayOfMonth": datetime.now() }] }
                    ] 
                } 
            }
        ).sort("_id", -1)  

        #Relleno de la tabla con las alarmas gatilladas el día actual
        for x in query:
            x["fecha"] = x["fecha"].strftime('%H:%M:%S %Y-%m-%d ') #Hora actual
            x["intensity"] = str(x["intensity"])+"%"
            self.tree_historicos_alarmas.insert('', 'end', values = ( x["fecha"], x["defecto"], x["intensity"]))

        self.scroll = ttk.Scrollbar(self.admin_tab, orient="vertical", command=self.tree_historicos_alarmas.yview)
        self.scroll.place(x=970, y=move_y, height=325)
        
        self.tree_historicos_alarmas.configure(yscrollcommand=self.scroll.set)

        ######################################## Ajustes de la camara ############################################

        move_y+=350
        tk.Label(self.admin_tab, font=("Helvetica", 15, "bold"), text='Camera System', fg="black", bg="#737272").place(x=390,y=move_y)

        #Reseteo de la camar
        self.btn_restart_camera = tk.Button(self.admin_tab, bd="3", height = 1, width = 14, relief=SUNKEN, text='RESET CAMERAS', highlightthickness=1, highlightbackground="#202424", borderwidth=3, font=("Helvetica", 9, "bold"),
                                            bg='#%02x%02x%02x' % (235,45,0), command = lambda: self.restart_camera())
        self.btn_restart_camera.place(x=870, y=move_y)


        #Seleccion del frame rate de la camara
        move_y+=33
        tk.Label(self.admin_tab, font=("Helvetica", 12, "bold"), text='Frame Rate', fg="black", bg="#737272").place(x=390,y=move_y)

        move_y += 20
        move_x = 390

        camera_config = list(db.camera.find({}).sort("_id", -1).limit(1))[0]
        self.frame_rate = int(camera_config["frame_rate"])
        self.frame_rates = [{ "frame_rate": 20, "button" : tk.Button(self.admin_tab, bd="3", height = 1, width = 5, relief=SUNKEN, text='20', bg='#eb712a', activebackground="red", highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.select_frame_rate(20)) },
                            { "frame_rate": 30, "button" : tk.Button(self.admin_tab, bd="3", height = 1, width = 5, relief=SUNKEN, text='30', bg='#eb712a', activebackground="red", highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.select_frame_rate(30))},
                            { "frame_rate": 40, "button" : tk.Button(self.admin_tab, bd="3", height = 1, width = 5, relief=SUNKEN, text='40', bg='#eb712a', activebackground="red", highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.select_frame_rate(40)) },
                            { "frame_rate": 50, "button" : tk.Button(self.admin_tab, bd="3", height = 1, width = 5, relief=SUNKEN, text='50', bg='#eb712a', activebackground="red", highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.select_frame_rate(50))},
                            { "frame_rate": 60, "button" : tk.Button(self.admin_tab, bd="3", height = 1, width = 5, relief=SUNKEN, text='60', bg='#eb712a', activebackground="red", highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.select_frame_rate(60))}]
        
        for i, frame_rate in enumerate(self.frame_rates):
            frame_rate["button"].place(x=move_x + 85*i, y=move_y)
            if frame_rate["frame_rate"] == self.frame_rate:
                frame_rate["button"].config(bg='#b04444')
            else:
                frame_rate["button"].config(bg='#8f1f8f')

        #Selección del tiempo de exposicion
        move_y+=43
        tk.Label(self.admin_tab, font=("Helvetica", 12, "bold"), text='Exposure Time (ms)', fg="black", bg="#737272").place(x=390,y=move_y)
        
        move_y+=20
                
        self.exposure_time = tk.Scale(self.admin_tab, width=11, length=605, bg="#0f702c", from_=1000, to=10000, orient='horizontal', highlightthickness=1, highlightbackground="#202424", borderwidth=3)
        self.exposure_time.set(int(camera_config["exposure_time"]))
        self.exposure_time.place(x=390, y=move_y)
        
        #######################################################################################################################################################################
        ##################################################################   PESTAÑA TENDENCIAS  ##############################################################################
        #######################################################################################################################################################################

        ################ Gráfico maximas intensidades ##################
        
        self.fig1, self.ax1 = plt.subplots(figsize=(11,3.5))
        self.fig1.patch.set_facecolor('#a39ea8')
        
        self.ax1.plot(1,1, '--r',  linewidth = 0.8) 
        for k, v in enumerate(self.arr_tendencias_1m.items()):
            self.ax1.plot(1,1, color = self.color[k], linewidth = 0.8, label=v[0].capitalize())
            
        segundos = mdates.SecondLocator(interval=60)
        m_fmt    = mdates.DateFormatter('%H:%M:%S')

        self.axes1=plt.gca()
        self.axes1.xaxis.label.set_size(1)
        self.ax1.xaxis.set_major_locator(segundos)
        self.ax1.xaxis.set_major_formatter(m_fmt)
        
        self.ax1.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15),ncol=14, fancybox=True, shadow=True)

        self.fig1.autofmt_xdate()

        self.chart1 = FigureCanvasTkAgg(self.fig1, self.tendencias_tab)
        self.chart1.get_tk_widget().place(x=0, y=0)

        plt.xticks(rotation=90)
        plt.subplots_adjust(left=0.075, bottom=0.25, right=0.90, top=0.90, wspace=0, hspace=0)
        plt.ylabel('Intensidad (%)')
        plt.grid()

        ################ Gráfico de frecuencias ##################

        self.arr_frecuencias = { "ecuador": [0] * 60, "tipo_huevo": [0] * 60, "lamina": [0] * 60, "ojo": [0] * 60, "desgarro_de_polo": [0] * 60, "tetilla": [0] * 60 }
        
        self.fig2, self.ax2 = plt.subplots(figsize=(11,3.5))
        self.fig2.patch.set_facecolor('#a39ea8')

        for k, v in enumerate(self.arr_frecuencias.items()):
            self.ax2.plot(1,1, color = self.color[k], linewidth = 0.8, label=v[0].capitalize())
            
        segundos = mdates.SecondLocator(interval=60)
        m_fmt    = mdates.DateFormatter('%H:%M:%S')

        self.ax2.xaxis.set_major_locator(segundos)
        self.ax2.xaxis.set_major_formatter(m_fmt)

        self.ax2.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=7, fancybox=True, shadow=True)

        self.fig2.autofmt_xdate()
        
        self.chart2 = FigureCanvasTkAgg(self.fig2, self.tendencias_tab)
        self.chart2.get_tk_widget().place(x=0, y=340)

        plt.xticks(rotation=90)
        plt.ylabel('Frecuencia')
        plt.subplots_adjust(left=0.075, bottom=0.25, right=0.90, top=0.90, wspace=0, hspace=0)
        plt.grid()

        #######################################################################################################################################################################
        ###################################################################   PESTAÑA HISTORICO  ##############################################################################
        #######################################################################################################################################################################


        self.labelDesde= tk.Label(self.historicos_tab, font="Arial 11", text="Desde: ", width=33, fg="#cdc9c3", bg="#2a2b2e")
        self.labelDesde.place(x=15,y=10)
        self.labelHasta= tk.Label(self.historicos_tab, font="Arial 11", text="Hasta: ", width=33, fg="#cdc9c3", bg="#2a2b2e")
        self.labelHasta.place(x=290,y=10)

        year = datetime.now().year
        month = datetime.now().month
        day = datetime.now().day

        self.cal=Calendar(self.historicos_tab, font="Arial 11", selectmode="day", year=year, month=month, day=day)
        self.cal.place(x=15,y=40)

        self.cal2=Calendar(self.historicos_tab, font="Arial 11", selectmode="day", year=year, month=month, day=day)
        self.cal2.place(x=290, y=40)

        move_y = 10
        move_x = 590

        #Listado de defectos posibles para el reporte
        for i, defecto in enumerate(self.tipos_defecto):
            if defecto["num"] != 0: #Con defecto
                defecto["checked_historico"] = tk.IntVar()
                tk.Button(self.historicos_tab, text=defecto["selector"]['text'], bd="3", relief=SUNKEN, bg=self.color[i],  height = 2, width = 13, command = lambda: nothing(self)).place(x=move_x,y=move_y)
                tk.Checkbutton(self.historicos_tab, text="" , bd="3", relief=SUNKEN, variable= defecto["checked_historico"], bg="#AFAFAF", pady=14,  width = 3).place(x=move_x+130,y=move_y)
                move_y += 67
                if i == 3:
                    move_x += 230
                    move_y = 10

        tk.Button(self.historicos_tab, text="Generar Historico", fg="#cdc9c3", bg="#2a2b2e", width = 48, command = lambda: self.generate_report()).place(x=590, y=move_y-7)

        self.tree_historicos_defectos = ttk.Treeview(self.historicos_tab, columns=(1,2), show="headings")   
        self.tree_historicos_defectos.place(x=15, y=260, height=350)

        self.tree_historicos_defectos.heading(1, text="Fecha")
        self.tree_historicos_defectos.heading(2, text="Hora")

        #######################################################################################################################################################################
        ################################################################   PESTAÑA INFERENCIAS   ##############################################################################
        #######################################################################################################################################################################


        self.inferencias_mode = 1 #Automatico por defecto, 0 = Manual y significa que se puede consultar por registros históricos
        
        # Botones MANUAL/AUTOMATICO
        self.btn_inferencias_manual = tk.Button(self.inferencias_tab, bg='gray', text='MANUAL', highlightthickness=1, width=12, highlightbackground="#202424", borderwidth=3, command = lambda: self.change_modo_estadistico(0))
        self.btn_inferencias_manual.place(x=15, y=25)

        self.btn_inferencias_automatico = tk.Button(self.inferencias_tab, bg='green', text='AUTOMATICO', highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.change_modo_estadistico(1))
        self.btn_inferencias_automatico.place(x=145, y=25)

        # Calendario oara elegir el momento de la inferencia
        self.cal3 = Calendar(self.inferencias_tab, font="Arial 11", selectmode="day", year=year, month=month, day=day)
        self.cal3.place(x=10,y=70)

        self.hourstr = tk.StringVar(value=datetime.now().strftime('%H'))
        self.hour = tk.Spinbox(self.inferencias_tab,from_=0,to=23,wrap=True,textvariable=self.hourstr,width=2, font=("Helvetica", 30), format="%02.0f", state="readonly")

        self.minstr = tk.StringVar(value=datetime.now().strftime('%M'))
        self.minstr.trace("w",self.trace_var)

        self.last_value = ""
        self.min = tk.Spinbox(self.inferencias_tab,from_=0,to=59,wrap=True,textvariable=self.minstr,width=2, font=("Helvetica", 30), format="%02.0f", state="readonly")
        self.hour.place(x=20, y=275)
        self.min.place(x=100, y=275)

        # Boton de submit para buscar inferencias históricas
        self.btn_refresh_inferencia_info = tk.Button(self.inferencias_tab, text ="Refresh",  font=("Helvetica", 10, "bold"), height = 2 , width = 9, bg='#c92222', fg='black', command = lambda: self.change_cropped_images())
        self.btn_refresh_inferencia_info.place(x=185,y=275)

        move_y += 140

        # Caracteristicas de la inferencias que varían segun el momento
        tk.Label(self.inferencias_tab, font=("Helvetica", 12, "bold"), text='Inferencias totales:', fg="black", bg='#%02x%02x%02x' % (250, 227, 125)).place(x=10,y=move_y)
        self.inferencias_totales = tk.Label(self.inferencias_tab, font=("Helvetica", 16, "bold"), text='0', fg="black", bg='#%02x%02x%02x' % (169, 183, 252))
        self.inferencias_totales.place(x=205,y=move_y-5)

        tk.Label(self.inferencias_tab, font=("Helvetica", 12, "bold"), text='Inferencias positivas:', fg="black", bg='#%02x%02x%02x' % (250, 227, 125)).place(x=10,y=move_y + 30)
        self.inferencias_positivas = tk.Label(self.inferencias_tab, font=("Helvetica", 16, "bold"), text='0', fg="black", bg='#%02x%02x%02x' % (169, 183, 252))
        self.inferencias_positivas.place(x=205,y=move_y+25)

        tk.Label(self.inferencias_tab, font=("Helvetica", 12, "bold"), text='Defectos totales :', fg="black", bg='#%02x%02x%02x' % (250, 227, 125)).place(x=10,y=move_y + 60)
        self.defectos_totales = tk.Label(self.inferencias_tab, font=("Helvetica", 16, "bold"), text='0', fg="black", bg='#%02x%02x%02x' % (169, 183, 252))
        self.defectos_totales.place(x=205,y=move_y+55)
        
        tk.Label(self.inferencias_tab, font=("Helvetica", 12, "bold"), text='Máxima intensidad:', fg="black", bg='#%02x%02x%02x' % (250, 227, 125)).place(x=10,y=move_y + 90)
        self.max_intensidad = tk.Label(self.inferencias_tab, font=("Helvetica", 16, "bold"), text='0', fg="black", bg='#%02x%02x%02x' % (169, 183, 252))
        self.max_intensidad.place(x=205,y=move_y+85)
        
        tk.Label(self.inferencias_tab, font=("Helvetica", 12, "bold"), text='% Success:', fg="black", bg='#%02x%02x%02x' % (250, 227, 125)).place(x=10,y=move_y + 120)
        self.success = tk.Label(self.inferencias_tab, font=("Helvetica", 16, "bold"), text='0', fg="black", bg='#%02x%02x%02x' % (169, 183, 252))
        self.success.place(x=205,y=move_y+115)

        tk.Label(self.inferencias_tab, font=("Helvetica", 12, "bold"), text='Ajustes en ese momento:', fg="black", bg="#737272").place(x=10,y=move_y + 150)

        move_x = 10
        move_y += 180

        self.ajustes_pestaña_inferencias = []

        for i in range(8):
            if i < 4:
                text = 'CAMON'+str(i+1)+':'
            else:
                text = 'PERNO'+str(i-3)+':'
            
            self.ajustes_pestaña_inferencias.append({"name": tk.Label(self.inferencias_tab, text=text, bg="#737272", font=("Helvetica",10,'bold')), "value": tk.Label(self.inferencias_tab, font=("Helvetica", 10), bg='#9c9797', height = 2, bd="3", width = 35, fg="black", relief=SUNKEN, text='', highlightthickness=1, highlightbackground="#202424", borderwidth=3) }) 

            self.ajustes_pestaña_inferencias[i]["name"].place(x=move_x, y=move_y)
            self.ajustes_pestaña_inferencias[i]["value"].place(x=move_x+70, y=move_y)
            self.ajustes_pestaña_inferencias[i]["value"].config(height = 1 , width = 7)

            move_y += 35

            if i == 3:
                move_x = 145
                move_y -= 140
        
        # Imágenes de las inferencias mas representativas en ese momento
    
        move_y = 10
        negro = np.zeros([250,250,3],dtype=np.uint8)
        
        negro = Image.fromarray(negro)
        img   = ImageTk.PhotoImage(image=negro)  # convert image for tkinter

        self.cropped_panel1 = tk.Label(self.inferencias_tab, width=245, height=220)  # initialize fail panel
        self.cropped_panel1.imgtk4 = img  # anchor imgtk so it does not be deleted by garbage-collector
        self.cropped_panel1.place(x=290,y=move_y) #130
        self.cropped_panel1.config(image=img)  # show the image

        self.cropped_panel2 = tk.Label(self.inferencias_tab, width=245, height=220)  # initialize fail panel
        self.cropped_panel2.imgtk4 = img  # anchor imgtk so it does not be deleted by garbage-collector
        self.cropped_panel2.place(x=480,y=move_y) #130
        self.cropped_panel2.config(image=img)  # show the image

        self.cropped_panel3 = tk.Label(self.inferencias_tab, width=245, height=220)  # initialize fail panel
        self.cropped_panel3.imgtk4 = img  # anchor imgtk so it does not be deleted by garbage-collector
        self.cropped_panel3.place(x=620,y=move_y) #130
        self.cropped_panel3.config(image=img)  # show the image

        self.cropped_panel4 = tk.Label(self.inferencias_tab, width=245, height=220)  # initialize fail panel
        self.cropped_panel4.imgtk4 = img  # anchor imgtk so it does not be deleted by garbage-collector
        self.cropped_panel4.place(x=760,y=move_y) #130
        self.cropped_panel4.config(image=img)  # show the image
        
        move_y += 245

        #Tabla con las inferencias historicas
        self.tree_historico_inferencias = ttk.Treeview(self.inferencias_tab, columns = (1,2,3,4,5,6), show = "headings")
        self.tree_historico_inferencias.place(x=290, y=move_y, height=420)
        
        self.tree_historico_inferencias.heading(1, text="Fecha")
        self.tree_historico_inferencias.heading(2, text="Hora")
        self.tree_historico_inferencias.heading(3, text="Inf. Totales")
        self.tree_historico_inferencias.heading(4, text="Inf. Positivas")
        self.tree_historico_inferencias.heading(5, text="Razón")
        self.tree_historico_inferencias.heading(6, text="Max Intensidad")

        self.tree_historico_inferencias.column(1, width = 120)
        self.tree_historico_inferencias.column(2, width = 100)
        self.tree_historico_inferencias.column(3, width = 100)
        self.tree_historico_inferencias.column(4, width = 120)
        self.tree_historico_inferencias.column(5, width = 120)
        self.tree_historico_inferencias.column(6, width = 140)
        
        query = db.historico_inferencias.find().sort("_id", -1)  
        
        #Relleno de la tabla con las alarmas gatilladas el día actual
        for x in query:
            x["hora"] = x["fecha"].strftime('%H:%M')
            x["fecha"] = x["fecha"].strftime('%Y-%m-%d')
            x["max_intensidad"] = str(x["max_intensidad"])+"%"
            x["success"] = str(x["success"])+"%"
            self.tree_historico_inferencias.insert('', 'end', values = ( x["fecha"], x["hora"], x["inferencias_totales"], x["inferencias_positivas"], x["success"], x["max_intensidad"]))

        self.scroll = ttk.Scrollbar(self.inferencias_tab, orient="vertical", command=self.tree_historico_inferencias.yview)
        self.scroll.place(x=990, y=move_y, height=420)
        
        self.tree_historico_inferencias.configure(yscrollcommand=self.scroll.set)

        self.change_cropped_images()

        #######################################################################################################################################################################
        ################################################################   PESTAÑA PERNOS Y CAMONES   #########################################################################
        #######################################################################################################################################################################

        #with open(str('/home/sokokrey/Escritorio/SAUT/molycop_pro/Entorno/valores_actuales.log')) as f: #Archivo modificado por node-red
        with open(str('/home/molly/params_act.log')) as f: #Archivo modificado por node-red
            f = f.readlines()
            f = str(f).replace("'",'')
            valores_actuales = json.loads(f)

        # Flag para liberar los valores propuestos
        self.alcanzando_valores_propuestos = True

        # Guarda el ultimo valor actual correctamente referenciado
        self.aux_ajustes_propuestos = [ 0,0,0,0,0,0,0,0 ]

        self.camon1_aux = self.ajustes_actuales[0]["value"]["text"] = valores_actuales[0]["camon1"]
        self.camon2_aux = self.ajustes_actuales[1]["value"]["text"] = valores_actuales[0]["camon2"]
        self.camon3_aux = self.ajustes_actuales[2]["value"]["text"] = valores_actuales[0]["camon3"]
        self.camon4_aux = self.ajustes_actuales[3]["value"]["text"] = valores_actuales[0]["camon4"]
        self.perno1_aux = self.ajustes_actuales[4]["value"]["text"] = valores_actuales[0]["perno1"]
        self.perno2_aux = self.ajustes_actuales[5]["value"]["text"] = valores_actuales[0]["perno2"]
        self.perno3_aux = self.ajustes_actuales[6]["value"]["text"] = valores_actuales[0]["perno3"]
        self.perno4_aux = self.ajustes_actuales[7]["value"]["text"] = valores_actuales[0]["perno4"]

        # Arreglo que almacena los valores historicos de camones y pernos
        self.ajustes_historicos = { "camon1": [], "camon2": [], "camon3": [], "camon4": [], "perno1": [], "perno2": [], "perno3": [], "perno4": [] } 

        query = db.pernos.find().sort("_id", -1).limit(80) # Base, los ultimos 80

        for i, ajuste in enumerate(query):
            hora = ajuste["fecha"].strftime('%H:%M')

            if i > 0:
                for j in range(1,5):
                    self.ajustes_historicos["camon"+str(j)].insert(0, { "hora" : hora, "ajuste": self.ajustes_historicos["camon"+str(j)][0]["ajuste"] if ajuste["camon"+str(j)] < 1 else ajuste["camon"+str(j)] })
                    self.ajustes_historicos["perno"+str(j)].insert(0, { "hora" : hora, "ajuste": self.ajustes_historicos["perno"+str(j)][0]["ajuste"] if ajuste["perno"+str(j)] < 1 else ajuste["perno"+str(j)] })
            else:
                for j in range(1,5):
                    self.ajustes_historicos["camon"+str(j)].insert(0, { "hora" : hora, "ajuste": ajuste["camon"+str(j)] })
                    self.ajustes_historicos["perno"+str(j)].insert(0, { "hora" : hora, "ajuste": ajuste["perno"+str(j)] })
        
        
        self.plot_ajustes = [ { "value": self.ajustes_historicos["camon1"] }, 
                              { "value": self.ajustes_historicos["camon2"] }, 
                              { "value": self.ajustes_historicos["camon3"] }, 
                              { "value": self.ajustes_historicos["camon4"] }, 
                              { "value": self.ajustes_historicos["perno1"] }, 
                              { "value": self.ajustes_historicos["perno2"] }, 
                              { "value": self.ajustes_historicos["perno3"] }, 
                              { "value": self.ajustes_historicos["perno4"] } ]
    
        # Creacion del grafico de camones y pernos
        move_y = 20
        for k in range(8):
            fig, ax = plt.subplots(figsize=(11,2))
            fig.patch.set_facecolor('#737272')

            y = [ registro["ajuste"] for registro in self.plot_ajustes[k]["value"] ]
            x = [ registro["hora"] for registro in self.plot_ajustes[k]["value"] ]

            xi = list(range(len(x)))

            text = 'CAMON'+str(k+1) if k < 4 else 'PERNO'+str(k-3)
            ax.plot(xi,y, marker='o', color = 'green' if k < 4 else 'blue', markersize=2, linewidth = 0.3, label=text)
            
            cont = 0
            val_anterior = 0
            for i,j in zip(x,y):
                if val_anterior != j:
                    signo = -7 if cont %2 == 0 else 1    
                    ax.annotate(str(j), xy=(cont,j+signo*round(max(y)/50, 1)), horizontalalignment='center', verticalalignment='bottom', fontsize=7)
                    
                cont += 1
                val_anterior = j

            axes = plt.gca()
            axes.xaxis.label.set_size(1)

            sep = round(max(y)/5, 1)
            ax.set_ylim(0, max(y)+sep)

            ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15),ncol=14, fancybox=True, shadow=True)

            chart = FigureCanvasTkAgg(fig, self.camones_tab if k < 4 else self.pernos_tab)
            chart.get_tk_widget().place(x=0, y=move_y)

            self.plot_ajustes[k]["fig"] = fig
            self.plot_ajustes[k]["ax"] = ax
            self.plot_ajustes[k]["chart"] = chart

            move_y = move_y + 160 if k != 3 else 20

            plt.xlabel('x')
            plt.yticks(fontsize=6)
            plt.xticks(rotation=60, fontsize=6)
            plt.xticks(xi, x)
            plt.subplots_adjust(left=0.04, bottom=0.25, right=0.90, top=0.90, wspace=0, hspace=0)
            plt.ylabel('Valor del ajuste (mm)')
            plt.grid()

        # Limites para Camones y Pernos
        tk.Label(self.camones_tab, font=("Helvetica", 11, "bold"), text='Limite : 160°', fg="black", bg="#737272").place(x=900,y=3)

        limites_pernos = db.limites_pernos.find_one()
        self.limites_pernos = []

        for i in range(4):
            self.limites_pernos.append(tk.Label(self.pernos_tab, font=("Helvetica", 10), bd="3", text=str(limites_pernos['LP'+str(i+1)]), relief=SUNKEN, width = 6, height=1, fg="black", bg="#f0871f", highlightthickness=1, highlightbackground="#202424", borderwidth=3))
        
        tk.Label(self.pernos_tab, font=("Helvetica", 11, "bold"), text='Limite Perno1:', fg="black", bg="#737272").place(x=110,y=1)
        self.limites_pernos[0].place(x=220, y=0)

        tk.Label(self.pernos_tab, font=("Helvetica", 11, "bold"), text='Limite Perno2 :',fg="black", bg="#737272").place(x=280,y=1)
        self.limites_pernos[1].place(x=390, y=0)

        tk.Label(self.pernos_tab, font=("Helvetica", 11, "bold"), text='Limite Perno3 :' ,fg="black", bg="#737272").place(x=450,y=1)
        self.limites_pernos[2].place(x=560, y=0)

        tk.Label(self.pernos_tab, font=("Helvetica", 11, "bold"), text='Limite Perno4 :' ,fg="black", bg="#737272").place(x=610,y=1)
        self.limites_pernos[3].place(x=720, y=0)

        ########################################################### LOOP DEL VIDEO ##################################################################
        
        super().__init__() #Permite que se pueda acceder desde una ventana hija, como la del codigo de acceso de admin
        super().withdraw() #Esconde la ventana de panel inicial

        #Inciar loop del video
        #self.cap = cv2.VideoCapture(0)

        self.proponer_valores(0)
        self.video_loop()

    ######################################## FUNCIONES #######################################
        
    # Para que cambie la hora cuando en los calendarios se llegue a las 00:00
    def trace_var(self,*args):
        if self.last_value == "59" and self.minstr.get() == "0":
            self.hourstr.set(int(self.hourstr.get())+1 if self.hourstr.get() !="23" else 0)

        self.last_value = self.minstr.get()

    #Funcion que se gatilla cuando se cambia de pestaña en el entorno
    def change_tab(self, event):
        if(event.widget.tab('current')['text'] == 'Administrador'): #Despliega ventana de autentificación para acceder a configuraciones
            adminTab = AdminTab(self)
        else: #Elimina ventanas extras en caso de que vaya a una pestaña que no sea Administrador
            try:
                for widget in self.win2.winfo_children():
                    if isinstance(widget, tk.Toplevel): #If widget is an instance of toplevel
                        widget.destroy()
            except:
                pass
    
    # Muestra el listado de los defectos informados por los operadores en el dia actual por defecto
    def mostrar_informados(self):
        informados = Informados(self)
        pass

    # Funcion que se gatilla al momento de presionar un tipo de defecto en la Pestaña de Operador
    def seleccionar_tipo_defecto(self, num_tipo_defecto):
        self.defecto_seleccionado = int(num_tipo_defecto)
        if self.defecto_seleccionado == 0: #Sin Defecto, no necesita escoger el nivel de intensidad
            self.select_intensity(0)
        else: #Eliminar listado de defectos para posicionar niveles de intensidad
            move_y = 160
            self.intensidades = [ {"selector": tk.Button(self.operador_tab, bg='white' , bd="3", relief=SUNKEN, text='Muy Bajo',height = 2, width = 20, command = lambda: self.select_intensity(1))},
                                  {"selector": tk.Button(self.operador_tab, bg='yellow' , bd="3", relief=SUNKEN, text='Bajo',height = 2, width = 20, command = lambda: self.select_intensity(2))},
                                  {"selector": tk.Button(self.operador_tab, bg='green' , bd="3", relief=SUNKEN, text='Medio',height = 2, width = 20, command = lambda: self.select_intensity(3))},
                                  {"selector": tk.Button(self.operador_tab, bg='orange' , bd="3", relief=SUNKEN, text='Alto',height = 2, width = 20, command = lambda: self.select_intensity(4))},
                                  {"selector": tk.Button(self.operador_tab, bg='red' , bd="3", relief=SUNKEN, text='Muy Alto',height = 2, width = 20, command = lambda: self.select_intensity(5))} ]
            
            #Label intensidad del error
            self.intensidad_label = tk.Label(self.operador_tab, font=("Helvetica", 16, "bold"), text='Nivel de Presencia', fg="black", bg="#a39ea8")
            self.intensidad_label.place(x=10,y=move_y)
            
            #Eliminar los botones de los defectos para poner los de nivel de intensidad
            for i, defecto in enumerate(self.tipos_defecto):
                defecto["selector"].destroy()
                ultimo_level = defecto["level"]["text"] 
                defecto["level"].destroy()
                defecto['level'] =  tk.Button(self.operador_tab, bd="3", height = 1, width = 3, relief=SUNKEN, text=ultimo_level, state="disabled", bg='black', command = lambda: nothing(self))

            #Posicionar niveles de intensidad
            move_y += 15
            for i, intensidad in enumerate(self.intensidades):
                intensidad["selector"].place(x=10,y=move_y)
                move_y += 72

    # Listar tipos de defectos en la pestaña de Operador 
    def listar_tipos_defecto(self):
        move_y = 165
        for i, tipo_defecto in enumerate(self.tipos_defecto):
            #Boton selector del defecto
            tipo_defecto["selector"] = tk.Button(self.operador_tab, height = 1, width = 13, bd="3", relief=SUNKEN, bg=self.color[i], text=tipo_defecto["name"], highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda j=i: self.seleccionar_tipo_defecto(self.tipos_defecto[j]["num"]))
            tipo_defecto["selector"].place(x=10,y=move_y)
            
            if tipo_defecto["num"] != 0: #Con defecto

                #Se habilita/deshabilita de acuerdo a la configuración en la pestaña de Administrador
                tipo_defecto["checked"] = tk.IntVar()
                tipo_defecto["checked"].set(tipo_defecto["enable"])

                if tipo_defecto["checked"].get() == 1:
                    tipo_defecto["selector"].config(state=NORMAL, bg=self.color[i])
                else:
                    tipo_defecto["selector"].config(state=DISABLED, bg='gray')

                variable = tk.StringVar(value=str(tipo_defecto["modo"]))
                tipo_defecto["modo_selector"] = tk.OptionMenu(self.operador_tab, variable, "MANUAL", "AUTOMATICO")
                
            # % de intensidad del defecto
            tipo_defecto['level'] =  tk.Button(self.operador_tab, bd="3", height = 1, width = 3, relief=SUNKEN, text='0%', state="disabled", bg='black', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: nothing(self))
            tipo_defecto["level"].place(x=145,y=move_y)
            
            move_y += 54

    # Funcion gatillada al momento de seleccionar la intensidad (baja, media, ...) de algun defecto que esté apareciendo
    def select_intensity(self,intensity):
        self.defecto_seleccionado_name = next(x["name"] for x in self.tipos_defecto if x["num"] == self.defecto_seleccionado)
        payload = json.dumps({ "presencia": int(intensity), "error": self.defecto_seleccionado_name.replace(" ", "_") })
        
        #Publica para que el node-red modifique la BD
        """
        client1.connect(broker,port)        #establish connection
        client1.publish("node/set", payload, qos=0, retain=False)
        """

        db.constancia.insert_one({ "error":  self.defecto_seleccionado_name.replace(" ", "_"), "presencia": int(intensity), "fecha": datetime.now() })
        self.cont_constancias += 1
        self.btn_defectos_informados.configure(text="Informados Hoy: {0}".format(self.cont_constancias))

        #Listado de defectos
        if int(intensity) > 0: #Crear nuevamente listado de defectos en caso de haber escogido uno
            ajustes = Ajustes(self, intensity)
            
            self.listar_tipos_defecto()
            
            #Eliminar zona de intensidades
            for i, intensidad in enumerate(self.intensidades):
                intensidad["selector"].destroy()

            self.intensidad_label.destroy()
        else:
            info = Info('Datos guardados correctamente')

    # ACTUALIZACION DE LOS GRAFICOS #

    #1) Gráfico de intesidades que se actualiza cada 15 segundos en la pestaña de operador y tendencias
    def plot_values1(self, intensidades):
        try:
            plt.rcParams.update({'figure.max_open_warning': 0}) #Clean graphs
            
            #Limites en eje x del grafico
            current_lesshour = datetime.today() - timedelta(minutes=60) #Le resto 1 hora a la actual
            current = datetime.now().strftime('%Y-%m-%d %H:%M:%S') #Hora actual
            xlims = pd.date_range(current_lesshour, current , freq = '1 min')

            self.ax.lines.clear()
            self.ax1.lines.clear()

            self.ax.set_ylim([0, int(int(self.cota_alarma.get())*1.25)])
            self.ax1.set_ylim([0, int(int(self.cota_alarma.get())*1.25)])

            self.ax.plot(xlims, [int(self.cota_alarma.get())] * 60, '--r', color = 'red', linewidth = 0.8) #Tope de la alarma
            self.ax1.plot(xlims, [int(self.cota_alarma.get())] * 60, '--r', color = 'red', label='Alarma') #Grafico más grande en pestaña tendencias
            self.ax1.xaxis.label.set_size(2)

            if int(float(self.arr_tendencias_1m['lamina'][len(self.arr_tendencias_1m['lamina']) - 1])) == 0:
                self.arr_tendencias_1m['lamina'] = [ (tendencia + 1) * int(float(intensidades['lamina'])) for tendencia in self.arr_tendencias_1m['lamina']]
            
            for k, v in enumerate(self.arr_tendencias_1m.items()):
                self.arr_tendencias_1m[v[0]].pop(0) #Quito la primera posicion del arreglo
                self.arr_tendencias_1m[v[0]].append(int(float(intensidades[v[0]]))) #Agrego la nueva
                self.ax.plot(xlims, self.arr_tendencias_1m[v[0]], color = self.color[k], linewidth = 0.8) #Grafico en pestaña operador
                self.ax1.plot(xlims, self.arr_tendencias_1m[v[0]], color = self.color[k], linewidth = 0.8, label=v[0].capitalize()) #Grafico más grande en pestaña tendencias
            
            #Actualizo el gráfico
            self.ax.relim()
            self.ax1.relim()
            self.fig.canvas.draw_idle()
            self.fig1.canvas.draw_idle() 

        except ValueError:
            pass

        return None

    #2) Gráfico de frecuencias de defectos que se actualiza cada 1 minuto en la pestaña de tendencias

    def plot_values2(self, frecuencias):
        try:
            plt.rcParams.update({'figure.max_open_warning': 0}) #Clean graphs

            #Limites en eje x del grafico
            current_lesshour = datetime.today() - timedelta(minutes=60) #Le resto 1 hora a la actual
            current2 = datetime.now().strftime('%Y-%m-%d %H:%M:%S') #Hora actual
            xlims2 = pd.date_range(current_lesshour, current2 , freq = '1 min')

            self.ax2.lines.clear()

            for k, v in enumerate(self.arr_frecuencias.items()):
                self.arr_frecuencias[v[0]].pop(0) #Quito la primera posicion del arreglo
                self.arr_frecuencias[v[0]].append(int(float(frecuencias[v[0]]))) #Agrego la nueva
                self.ax2.plot(xlims2, self.arr_frecuencias[v[0]], color = self.color[k], linewidth = 0.8, label=v[0].capitalize()) #Grafico más grande en pestaña tendencias

            #Actualizo el gráfico
            self.ax2.relim()
            self.fig2.canvas.draw_idle()
        
        except:
            pass
        
    #Función gatillada al presionar alguna opcion de frame rate en la pestaña de Administrador y cambio el color del boton seleccionado
    def select_frame_rate(self, f_r):
        for frame_rate in self.frame_rates:
            if frame_rate["frame_rate"] == f_r:
                frame_rate["button"].config(bg='#b04444')
            else:
                frame_rate["button"].config(bg='#8f1f8f')

        self.frame_rate = int(f_r)

    #Guarda la configuración del entorno desde la pestaña de Administrador
    def save_admin_config(self):
        db.alarma.update_one({}, { "$set": { "umbral": int(self.cota_alarma.get()), "razon_inferencias": int(self.razon_inferencias.get()) } })
        db.configuracion.update_one({}, { "$set": { "tiempo_respuesta": int(self.tiempo_respuesta.get()) } })
        
        for i, defecto in enumerate(self.tipos_defecto):
            if defecto['name'] != 'Sin Defecto':

                #Modifico cada tipo de detecto en la base de datos
                filter = { "num" : defecto["num"] }
                db.defecto.update_one(filter, { "$set": { "modo": defecto["modo_selector"]["text"], "enable": defecto["checked"].get() } })
                
                #Habilito/Desabilito cada defecto en la pestaña de operador
                if defecto["checked"].get() == 1:
                    defecto["selector"].config(state=NORMAL, bg=self.color[i])
                else:
                    defecto["selector"].config(state=DISABLED, bg='gray')

            self.notebook.select(self.operador_tab)
            
            info = Info('Datos guardados correctamente')
            pass
    
    # Guarda la configuración de la camara
    def save_camera_config(self):
        db.camera.update_one({}, { "$set": { "frame_rate": int(self.frame_rate), "exposure_time": int(self.exposure_time.get()) } })
        
        for frame_rate in self.frame_rates:
            if frame_rate["frame_rate"] == self.frame_rate:
                frame_rate["button"].config(bg='#b04444')
            else:
                frame_rate["button"].config(bg='#8f1f8f')

        self.notebook.select(self.operador_tab)

        time.sleep(1)

        #client1.connect(broker,port)        #establish connection
        try:
            client1.publish("restart/camera", 1, qos=0, retain=False)
        except ConnectionAbortedError:
            pass        
        
        #info = Info('Datos guardados correctamente')
        
    # Auto ajusta el tiempo de exposicion en el momento que cambia del tamaño de bola
    def auto_exposure_adjustment(self, exposure_time):
        self.exposure_time.set(int(exposure_time))
        db.camera.update_one({}, { "$set": { "exposure_time": int(exposure_time) } })
               

        #time.sleep(1)
        #client1.connect(broker,port)        #establish connection
        try:
            client1.publish("restart/camera", 1, qos=0, retain=False)
        except ConnectionAbortedError:
            pass    
        time.sleep(1)
        pass

    #Reinicia la camara
    def restart_camera(self):
        info = Info('Reiniciando......')
        time.sleep(1)

        #client1.connect(broker,port)        #establish connection
        try:
            client1.publish("restart/camera", 1, qos=0, retain=False)
        except ConnectionAbortedError:
            pass

    # Refresca las imagenes y la informacion de las inferencias cuando se consulta por una fecha en la Pestaña de Inferencias
    def change_cropped_images(self):
        
        # Actualiza Imágenes (En caso de haber)
        path = 'inferencias/'+datetime.now().strftime('%Y-%m-%d_%H:%M') 

        if self.inferencias_mode == 0: #Manual
            path = 'inferencias/'+str(self.cal3.selection_get())+'_'+self.hour.get()+':'+self.min.get()

        if os.path.isfile(path+'/img1.png'):
            crop_img = cv2.imread(path+'/img1.png')
            crop_img = Image.fromarray(crop_img)
            
            imgtk = ImageTk.PhotoImage(image=crop_img)  # convert image for tkinter
            self.cropped_panel1.imgtk3 = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            self.cropped_panel1.config(image=imgtk)  # show the image)

        elif self.inferencias_mode == 0:
            info = Info('No se encontraron inferencias')

        if os.path.isfile(path+'/img2.png'):
            crop_img = cv2.imread(path+'/img2.png')
            crop_img = Image.fromarray(crop_img)
            
            imgtk = ImageTk.PhotoImage(image=crop_img)  # convert image for tkinter
            self.cropped_panel2.imgtk3 = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            self.cropped_panel2.config(image=imgtk)  # show the image)

        if os.path.isfile(path+'/img3.png'):
            crop_img = cv2.imread(path+'/img3.png')
            crop_img = Image.fromarray(crop_img)
            
            imgtk = ImageTk.PhotoImage(image=crop_img)  # convert image for tkinter
            self.cropped_panel3.imgtk3 = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            self.cropped_panel3.config(image=imgtk)  # show the image)

        if os.path.isfile(path+'/img4.png'):
            crop_img = cv2.imread(path+'/img4.png')
            crop_img = Image.fromarray(crop_img)
            
            imgtk = ImageTk.PhotoImage(image=crop_img)  # convert image for tkinter
            self.cropped_panel4.imgtk3 = imgtk  # anchor imgtk so it does not be deleted by garbage-collector
            self.cropped_panel4.config(image=imgtk)  # show the image)

        # Actualiza los valores de ajuste que habían en ese momento
        fecha = datetime.strptime(self.cal3.get_date()+' '+self.hour.get()+':'+self.min.get(),'%d-%m-%y %H:%M')
        
        query = db.pernos.find(
            { "$expr": 
                { "$and" : 
                    [  
                        { "$lte": [{ "$year": "$fecha" }, { "$year": fecha }] },
                        { "$lte": [{ "$month": "$fecha" }, { "$month": fecha}] },  
                        { "$lte": [{ "$dayOfMonth": "$fecha" }, { "$dayOfMonth": fecha }] },
                        { "$lte": [{ "$hour": "$fecha" }, { "$hour": fecha } ]},
                        { "$lte": [{ "$minute": "$fecha" }, { "$minute": fecha }] },
                    ] 
                } 
            }
        ).sort("_id", -1).limit(1)[0]

        entrytext = tk.StringVar()

        entrytext.set(query["camon1"])
        self.ajustes_pestaña_inferencias[0]['value']['text'] = entrytext.get()
        entrytext.set(query["camon2"])
        self.ajustes_pestaña_inferencias[1]['value']['text'] = entrytext.get()
        entrytext.set(query["camon3"])
        self.ajustes_pestaña_inferencias[2]['value']['text'] = entrytext.get()
        entrytext.set(query["camon4"])
        self.ajustes_pestaña_inferencias[3]['value']['text'] = entrytext.get()
        entrytext.set(query["perno1"])
        self.ajustes_pestaña_inferencias[4]['value']['text'] = entrytext.get()
        entrytext.set(query["perno2"])
        self.ajustes_pestaña_inferencias[5]['value']['text'] = entrytext.get()
        entrytext.set(query["perno3"])
        self.ajustes_pestaña_inferencias[6]['value']['text'] = entrytext.get()
        entrytext.set(query["perno4"])
        self.ajustes_pestaña_inferencias[7]['value']['text'] = entrytext.get()

        # Actualiza la informacion de la inferencias realizadas en la fecha seleccionada
        try:
            query = db.historico_inferencias.find(
                { "$expr": 
                    { "$and" : 
                        [  
                            { "$eq": [{ "$year": "$fecha" }, { "$year": fecha }] },
                            { "$eq": [{ "$month": "$fecha" }, { "$month": fecha}] },  
                            { "$eq": [{ "$dayOfMonth": "$fecha" }, { "$dayOfMonth": fecha }] },
                            { "$eq": [{ "$hour": "$fecha" }, { "$hour": fecha } ]},
                            { "$eq": [{ "$minute": "$fecha" }, { "$minute": fecha }] }
                            
                        ] 
                    } 
                }
            ).sort("_id", -1).limit(1)[0]


            self.inferencias_totales.config(text=query["inferencias_totales"])
            self.inferencias_positivas.config(text=query["inferencias_positivas"])
            self.defectos_totales.config(text=query["cantidad_laminas"])
            self.max_intensidad.config(text=query["max_intensidad"])
            self.success.config(text=query["success"])
        except :
            pass

    def video_loop(self):
        try:
            global db
            global fontpath
            
            # Actualizar hora en cada iteracion
            actual_time = datetime.now().strftime('%H:%M:%S %d-%m-%Y') 
            self.var_hora.set(actual_time)
            
            # Ciclo de adquisicion de imagenes
            (data, frame) = imageHub.recv_image()
            data = json.loads(data)
            dispName = data["dispName"] #Identificador del panel al cual enviar el frame
            imageHub.send_reply(b'OK') #Respuesta al python de Deteccion para que el loop siga

            self.converted_image = Image.fromarray(frame)  # convert image for PIL, ten cuidado

            if dispName == 'RF2': #PANEL DE VIDEO
                
                img_pil = Image.fromarray(frame)
                draw = ImageDraw.Draw(img_pil)

                if self.TT_SBR <= 750: 
                    if self.VEL_MOTOR == 0: #Temperatura de la barra <= 750 y la velocidad del motor == 0 implica que la línea esta detenida
                        cv2.putText(frame, 'Linea Detenida', (410, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

                        if self.flag_pasando == 1: # Cuando la línea de estar detenida vuelve a operar
                            with open(str('/home/molly/params_act.log')) as f: #Archivo modificado por node-red
                                f = f.readlines()
                                f = str(f).replace("'",'')
                                valores_actuales = json.loads(f)

                            self.camon1_aux = valores_actuales[0]["camon1"]
                            self.camon2_aux = valores_actuales[0]["camon2"]
                            self.camon3_aux = valores_actuales[0]["camon3"]
                            self.camon4_aux = valores_actuales[0]["camon4"]
                            self.perno1_aux = valores_actuales[0]["perno1"]
                            self.perno2_aux = valores_actuales[0]["perno2"]
                            self.perno3_aux = valores_actuales[0]["perno3"]
                            self.perno4_aux = valores_actuales[0]["perno4"]

                            self.actualizar_ajustes_actuales(valores_actuales[0])
                            self.actualizar_plot_ajustes(valores_actuales[0])
                            
                            self.flag_pasando = 0
                    else:
                        cv2.putText(frame, 'Linea Activa sin barra', (360, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                        
                else:
                    draw.text((5, 15), 'RF2 ONLINE', font = ImageFont.truetype(fontpath, 8), fill = (0, 235, 0, 0))
                    
                    self.flag_pasando = 1
                
                font = ImageFont.truetype(fontpath, 14)

                b,g,r,a = 240,130,150,0
                draw.text((415, 415), 'TT_ROD : {0}°C'.format(round(self.TT_ROD, 1)), font = font, fill = (b, g, r, a))
                draw.text((415, 430), 'TT_SBR : {0}°C'.format(round(self.TT_SBR, 1)), font = font, fill = (b, g, r, a))

                frame = np.array(img_pil)

                self.converted_image = Image.fromarray(frame)

                imgtk2 = ImageTk.PhotoImage(image=self.converted_image)  # convert image for tkinter, Cristo
                self.panel.imgtk2 = imgtk2  # anchor imgtk so it does not be deleted by garbage-collector, Viene 
                self.panel.config(image=imgtk2)  # show the image, A por ti

            elif dispName == 'IMG': #PANEL DE CAPTURAS
                self.contador_bolas += 1
                self.bolas_pasando = True
                
                #Enviar frame a panel de detecciones
                imgtk3 = ImageTk.PhotoImage(image=self.converted_image)  # convert image for tkinter
                self.panel2.imgtk3 = imgtk3  # anchor imgtk so it does not be deleted by garbage-collector
                self.panel2.config(image=imgtk3)  # show the image
                
            elif dispName == 'SORTER': # Respuesta del clasificador
                try:
                    if int(data["num_defecto"]) > 0:

                        imgtk3 = ImageTk.PhotoImage(image=self.converted_image)  # convert image for tkinter
                        self.panel3.imgtk3 = imgtk3  # anchor imgtk so it does not be deleted by garbage-collector
                        self.panel3.config(image=imgtk3)  # show the image)
                        
                        # Guardar imagenes mas relevantes de las inferencias
                        path_to_save = "inferencias/"+datetime.now().strftime('%Y-%m-%d_%H:%M')
                        
                        os.makedirs(path_to_save, exist_ok=True)
                        cv2.imwrite(path_to_save+'/'+str(time.strftime("%Y%m%d-%H%M%S"))+'.png', frame)
                        cv2.imwrite(path_to_save+"/Many.png", np.asarray(data["raw_img"]) )
                        
                        # Imágenes recortadas con los niveles de intensidad más altos durante ese minuto, guardándose en el directorio especificado
                        for x in range(len(data["cropped_images"])):       
                            cv2.imwrite(path_to_save+"/img"+str(int(x+1))+".png", np.asarray(data["cropped_images"][x]))

                        with open(path_to_save+"/annotations.txt", "a") as log:
                            for annotation in data["annotations"]:
                                log.write(annotation)

                        #Se guarda en la BD historica de inferencias
                        db.historico_inferencias.insert_one({ "fecha": datetime.now(), 
                                                              "inferencias_totales": data["inferencias_totales"],
                                                              "inferencias_positivas": data["inferencias_positivas"],
                                                              "cantidad_laminas": data["cantidad_laminas"],
                                                              "max_intensidad": data["max_intensidad"],
                                                              "success": data["success"] })

                        x = {}
                        x["hora"] = datetime.now().strftime('%H:%M')
                        x["fecha"] = datetime.now().strftime('%Y-%m-%d')
                        x["max_intensidad"] = str(data["max_intensidad"])+"%"
                        x["success"] = str(data["success"])+"%"

                        self.tree_historico_inferencias.insert('', 0, values = ( x["fecha"], x["hora"], data["inferencias_totales"], data["inferencias_positivas"], x["success"], x["max_intensidad"]))
                        
                        # Si está en AUTOMATICO, actualiza la informacion, si está en MANUAL la deja a como está 
                        if self.inferencias_mode == 1:
                            self.change_cropped_images()

                            self.inferencias_totales.config(text=data["inferencias_totales"])
                            self.inferencias_positivas.config(text=data["inferencias_positivas"])
                            self.defectos_totales.config(text=data["cantidad_laminas"])
                            self.max_intensidad.config(text=data["max_intensidad"])
                            self.success.config(text=data["success"])

                    # Armos objectos para almacenar en historico de defectos ( Intensidades )
                    intensidades = { "alarma": self.cota_alarma.get(), "lamina" : '0.0', "ojo" : '0.0', "desgarro_de_polo" : '0.0', "tetilla" : '0.0', "ecuador" : '0.0', "tipo_huevo": '0.0' }
                    frecuencias = { "lamina" : '0', "ojo" : '0', "desgarro_de_polo" : '0', "tetilla" : '0', "ecuador" : '0', "tipo_huevo": '0' }
                    
                    for i, defecto in enumerate(self.tipos_defecto):
                        if int(defecto['num']) > 0:
                            if int(data["num_defecto"]) == int(defecto['num']):
                                defecto['level']['text'] = str(round(float(data["max_intensidad"]), 1)) + '%'
                                intensidades[(eval('"'+defecto["name"].lower()+'"'))] = str(data["max_intensidad"])
                                frecuencias[(eval('"'+defecto["name"].lower()+'"'))] = str(data["cantidad_laminas"])
                            else:
                                defecto['level']['text'] = '0%'

                    db.historico_defecto.insert_one({ "fecha": datetime.now(), 
                                                    "ecuador": int(float(intensidades["ecuador"])),
                                                        "ojo": int(float(intensidades["ojo"])),
                                                    "lamina": int(float(intensidades["lamina"])),
                                                "tipo_huevo": int(float(intensidades["tipo_huevo"])),
                                        "desgarro_de_polo": int(float(intensidades["desgarro_de_polo"])),
                                                    "tetilla": int(float(intensidades["tetilla"])) })
                    # Actualizar graficos
                    if int(float(intensidades["lamina"])) > 0:
                        self.plot_values1(intensidades)
                        self.plot_values2(frecuencias)

                    # Elimino alarma pendiente en caso de haber
                    try:
                        self.popup_alarma.destructor(self)
                    except:
                        pass
                    
                    alarma = db.alarma.find_one()
                    
                    # Condiciones para gatillar la alarma

                    if ( (int(data["alarma"]) == 1) and (int(float(data["max_intensidad"])) >= int(alarma["umbral"])) and ( int(float(data["success"])) > int(alarma["razon_inferencias"])) ):
                        global flag_confirmacion
                        flag_confirmacion = 0

                        # Se proponen valores nuevos
                        try:
                            self.proponer_valores(1)  
                        except:
                            pass  

                        # Activa baliza de alarma

                        print('=============')
                        global flag_selector

                        flag_selector = 1

                        db.selector.update_one({}, { "$set" : { "status" : 1 } })
                        #os.system("sudo python3 ser_ON-OFF.py 1")
                        db.selector.update_one({}, { "$set" : { "status" : 0 } })

                        flag_selector = 0

                        print('=============')
                        #Se guarda en la BD de alarmas
                        db.historico_alarmas.insert_one({ "fecha": datetime.now(), 
                                                        "defecto": data["greather_class"],
                                                    "intensity": data["max_intensidad"] })

                        # Genera la alarma en pantalla
                        self.popup_alarma = Alarma(self, { "name" : data["greather_class"], "intensity" : data["max_intensidad"], "img" :  data["cropped_images"][0] })

                        # Agrega alarma a tabla de alarmas históricas
                        self.tree_historicos_alarmas.insert('', 0, values = ( datetime.now().strftime('%H:%M:%S %Y-%m-%d'),  data["greather_class"], str(data["max_intensidad"])+'%' ))
                        
                    # Si está en automatico , sumo 1 minuto automaticamente al calendario
                    if self.inferencias_mode == 1:
                        self.hourstr.set(datetime.now().strftime('%H'))
                        self.minstr.set(datetime.now().strftime('%M'))
                        pass

                    #client1.connect(broker,port)        #establish connection
                    #client1.publish("node/alarm", 1, qos=0, retain=False)
                    
                except ValueError:
                    pass
            
            # Termina 1 minuto y reseteo el contador de bolas
            if (1 == int(datetime.now().strftime('%S'))):
                time.sleep(1)

                if int(self.contador_bolas) == 0:
                    self.bolas_pasando = False

                self.contador_bolas = 0

            # Reseteo general a las 00:00
            if int(datetime.now().strftime('%H%M%S')) == 0:
                time.sleep(1)

                # Reseteo de defectos registrados por el operador durante el dia
                self.cont_constancias = 0
                self.btn_defectos_informados.configure(text="Informados Hoy: {0}".format(self.cont_constancias))
                
                # Actualizacion de Calendarios
                year = datetime.now().year
                month = datetime.now().month
                day = datetime.now().day

                self.cal.destroy()
                self.cal=Calendar(self.historicos_tab, font="Arial 11", selectmode="day", year=year, month=month, day=day)
                self.cal.place(x=15,y=40)
                
                self.cal2.destroy()
                self.cal2=Calendar(self.historicos_tab, font="Arial 11", selectmode="day", year=year, month=month, day=day)
                self.cal2.place(x=290, y=40)

                self.cal3.destroy()
                self.cal3=Calendar(self.inferencias_tab, font="Arial 11", selectmode="day", year=year, month=month, day=day)
                self.cal3.place(x=15, y=70)

            self.operador_tab.after(1, self.video_loop)  # call the same function after 30 milliseconds
            
        except ValueError:
            print('No se encontraron camaras')
            time.sleep(5)
            self.video_loop()

            pass

    # Propone valores de ajuste
    def proponer_valores(self, caso):
        print('**')
        if self.alcanzando_valores_propuestos:

            self.alcanzando_valores_propuestos = False
            try:
                self.aplicar.config(text='Calculando', bg='gray', state=DISABLED, command = lambda: self.nothing())
                #with open(str('/home/molly/valores_actuales.log')) as f: #Archivo modificado por node-red
                with open(str('/home/molly/params_act.log')) as f: #Archivo modificado por node-red
                    f = f.readlines()
                    f = str(f).replace("'",'')
                    valores_actuales = json.loads(f)
                                            
                #filename = '/home/molly/Escritorio/moly/Entorno/valores_propuestos.sav'
                                        
                # load the model from disk
                #loaded_model = pickle.load(open(filename, 'rb'))

                #predicciones = loaded_model.predict(np.array([[ valores_actuales[0]["camon1"], valores_actuales[0]["camon2"], valores_actuales[0]["camon3"], valores_actuales[0]["camon4"], valores_actuales[0]["perno1"], valores_actuales[0]["perno2"], valores_actuales[0]["perno3"], valores_actuales[0]["perno4"] ]]))[0]
                
                entrytext = tk.StringVar()
                ajustes_aux = [ self.camon1_aux, self.camon2_aux, self.camon3_aux, self.camon4_aux, self.perno1_aux, self.perno2_aux, self.perno3_aux, self.perno4_aux]
                
                percents = np.random.randint(0, 6, 8)
                percents[1] = percents[0]
                percents[3] = percents[2]

                signos = np.random.randint(0, 2, 8)
                signos[1] = 1 if signos[0] == 0 else 0
                signos[3] = 1 if signos[2] == 0 else 0
                signos[signos == 0] = -1
                
                global db
                global client1

                ajustes = []

                # Reconeccion MQTT
                id = randint(0, 1000)
                client1 = paho.Client(client_id = str(id))

                client1.on_publish = error_publish     #assign function to callback
                client1.on_message= on_message                      #attach function t
                client1.connect(broker,port)        #establish connection
                client1.loop_start()        #start the loop
                client1.subscribe('node/limites_pernos')
                client1.subscribe('node/ajustes_propuestos')
                client1.subscribe('node/ajustes_actuales')
                client1.subscribe('node/tamaño_actual')
                client1.subscribe('node/parametros_produccion')
                client1.subscribe('node/status_a')
                client1.subscribe('node/fallas')

                print('0000')
                for i in range(4):
                    entrytext = tk.StringVar()
                    

                    print('111')
                    valor_actual = valores_actuales[0]["camon"+str(i+1)]
                    """
                    if caso == 1:
                        valor_actual = ajustes_aux[i]
                    """
                    entrytext.set(valor_actual)
                    if ((valor_actual== ajustes_aux[i] ) and (abs(float(valor_actual) - ajustes_aux[i] ) <= 0.3 )):
                        valor = truncate(float(valor_actual) + 0.1*percents[i]*signos[i],1)
                        valor = valor if valor <= 160 else 160
                        valor = 0 if valor < 1 else valor
                    else:
                        valor = truncate(ajustes_aux[i] + 0.1*percents[i]*signos[i],1)

                    entrytext.set(valor)
                    self.aux_ajustes_propuestos[i] = valor

                    payload = json.dumps({ "id": str("camon"+str(i+1)), "from": float(valores_actuales[0]["camon"+str(i+1)]), "to": float(entrytext.get()), "duration": str(int(self.tiempo_respuesta.get())*1000), "aplicar": 0 })
                    
                    try:
                        client1.publish("node/prediccion", payload, qos=2, retain=False)
                    except ConnectionAbortedError:
                        pass
                    
                for i in range(4):
                    entrytext = tk.StringVar()

                    valor_actual = valores_actuales[0]["perno"+str(i+1)]
                    """
                    if caso == 1:
                        valor_actual = ajustes_aux[i+4]
                    """
                    entrytext.set(valor_actual)

                    if ((valor_actual== ajustes_aux[i+4] ) and (abs(float(valor_actual) - ajustes_aux[i+4] ) <= 0.3 )):
                        #valor = round(float(valor_actual) + 0.1*percents[i+4]*signos[i+4],1)
                        valor = truncate(float(valor_actual) + 0.1*percents[i+4]*signos[i+4], 1)
                    else:
                        valor = truncate(ajustes_aux[i+4] + 0.1*percents[i+4]*signos[i+4],1)

                    self.aux_ajustes_propuestos[i+4] = valor
                    entrytext.set(valor)
                    
                    payload = json.dumps({ "id": str("perno"+str(i+1)), "from": float(valores_actuales[0]["perno"+str(i+1)]), "to": float(entrytext.get()), "duration": str(int(self.tiempo_respuesta.get())*1000), "aplicar": 0 })
                    
                    print('2222')
                    try:
                        client1.publish("node/prediccion", payload, qos=2, retain=False)
                    except ConnectionAbortedError:
                        pass
            except:
                pass

    # Apriete de camon/perno
    def apretar_ajuste(self, ajuste):
        for i in range(8):
            text = 'camon' if i < 4 else 'perno'
            num  = i + 1 if i < 4 else i-3
            if ajuste['id'] == text + str(num):
                self.ajustes_actuales[i]["value"]["text"] = ajuste['value']
                self.ajustes_actuales[i]["value"].config(highlightbackground='blue')

    # Soltar el ajuste para cambiar otro
    def aflojar_ajuste(self, ajuste):
        for i in range(8):
            text = 'camon' if i < 4 else 'perno'
            num  = i + 1 if i < 4 else i-3
            if ajuste['id'] == text + str(num):
                self.ajustes_actuales[i]["value"]["text"] = ajuste['value']
                self.ajustes_actuales[i]["value"].config(highlightbackground='red')

    # Se coloca el valor final al ajuste actual*
    def finalizar_ajuste(self, ajuste):
        for i in range(8):
            text = 'camon' if i < 4 else 'perno'
            num  = i + 1 if i < 4 else i-3
            if ajuste['id'] == text + str(num):
                self.ajustes_actuales[i]["value"]["text"] = self.ajustes_propuestos[i]["value"]["text"]
                self.ajustes_actuales[i]["value"].config(highlightbackground='#202424')

    # LIberar camon
    def liberar_ajuste(self, ajuste):
        for i in range(4):
            if ajuste['id'] == 'camon' + str(i+1):
                self.ajustes_actuales[i]["value"].config(highlightbackground='#202424')

    # Funcion gatillada luego de presionar el boton para Aplicar los ajustes propuestos
    def confirmacion_ajustes(self):
        try:
            global db
            global client1

            ajustes = []

            # Reconeccion MQTT
            id = randint(0, 1000)
            client1 = paho.Client(client_id = str(id))

            client1.on_publish = error_publish     #assign function to callback
            client1.on_message= on_message                      #attach function t
            #client1.connect(broker,port)        #establish connection
            client1.loop_start()        #start the loop
            client1.subscribe('node/limites_pernos')
            client1.subscribe('node/ajustes_propuestos')
            client1.subscribe('node/ajustes_actuales')
            client1.subscribe('node/tamaño_actual')
            client1.subscribe('node/parametros_produccion')
            client1.subscribe('node/status_a')
            client1.subscribe('node/fallas')

            self.aplicar.config(text='Aplicando...', bg='gray', state=DISABLED)
            # Publicacion de los valores propuestos y en cuanto debe tardar el ajuste
            for i in range(4):
                payload = json.dumps({ "id": "camon"+str(i+1), "from": float(self.ajustes_actuales[i]['value']['text']), "to": float(self.ajustes_propuestos[i]['value']['text']), "duration": int(self.tiempo_respuesta.get())*1000, "aplicar": 1 })
                ajustes.append({ "id": "camon"+str(i+1), "from": float(self.ajustes_actuales[i]['value']['text']), "to": float(self.ajustes_propuestos[i]['value']['text']) })
                
                try:
                    client1.publish("node/prediccion", payload, qos=0, retain=False)
                except ConnectionAbortedError:
                    pass

            for i in range(4):
                payload = json.dumps({ "id": "perno"+str(i+1), "from": float(self.ajustes_actuales[i+4]['value']['text']), "to": float(self.ajustes_propuestos[i+4]['value']['text']), "duration": str(int(self.tiempo_respuesta.get())*1000), "aplicar": 1 })
                ajustes.append({ "id": "perno"+str(i+1), "from": float(self.ajustes_actuales[i+4]['value']['text']), "to": float(self.ajustes_propuestos[i+4]['value']['text'])})
            
                try:
                    client1.publish("node/prediccion", payload, qos=0, retain=False)
                except ConnectionAbortedError:
                    pass
            
            # Pasa a la database de aplicados
            db.historico_aplicados.insert_one({ "fecha" : datetime.now(), "ajustes": ajustes })
            
            self.ultimo_aplicado.config(text="Ultimo Ajuste: {0}".format(datetime.now().strftime('%d-%m-%Y %H:%M')))
        except ValueError:
            pass
 
    # Actualiza ajustes actuales quer vienen de MQTT
    def actualizar_ajustes_actuales(self, ajuste):
        print('ACTUALIZAR AJUSTES ACTUALES')
        # Si la diferencia es mayor a 0.3, conservo el valor de referencia

        if ajuste['camon1'] >= 0:
            self.ajustes_actuales[0]["value"]["text"] = round(ajuste['camon1'],1)
            self.camon1_aux = round(ajuste['camon1'],1) if abs(round(ajuste['camon1'],1) - self.camon1_aux) <= 0.3 else self.camon1_aux

        if ajuste['camon2'] >= 0:
            self.ajustes_actuales[1]["value"]["text"] = round(ajuste['camon2'],1)
            self.camon2_aux = round(ajuste['camon2'],1) if abs(round(ajuste['camon2'],1) - self.camon2_aux) <= 0.3 else self.camon2_aux
            
        if ajuste['camon3'] >= 0:
            self.ajustes_actuales[2]["value"]["text"] = round(ajuste['camon3'],1)
            self.camon3_aux = round(ajuste['camon3'],1) if abs(round(ajuste['camon3'],1) - self.camon3_aux) <= 0.3 else self.camon3_aux
        
        if ajuste['camon4'] >= 0:
            self.ajustes_actuales[3]["value"]["text"] = round(ajuste['camon4'],1)
            self.camon4_aux = round(ajuste['camon4'],1) if abs(round(ajuste['camon4'],1) - self.camon4_aux) <= 0.3 else self.camon4_aux
        
        if ajuste['perno1'] >= 0:
            self.ajustes_actuales[4]["value"]["text"] = round(ajuste['perno1'],1)
            self.perno1_aux = round(ajuste['perno1'],1) if abs(round(ajuste['perno1'],1) - self.perno1_aux) <= 0.3 else self.perno1_aux
        
        if ajuste['perno2'] >= 0:
            self.ajustes_actuales[5]["value"]["text"] = round(ajuste['perno2'],1)
            self.perno2_aux = round(ajuste['perno2'],1) if abs(round(ajuste['perno2'],1) - self.perno2_aux) <= 0.3 else self.perno2_aux

        if ajuste['perno3'] >= 0:
            self.ajustes_actuales[6]["value"]["text"] = round(ajuste['perno3'],1)
            self.perno3_aux = round(ajuste['perno3'],1) if abs(round(ajuste['perno3'],1) - self.perno3_aux) <= 0.3 else self.perno3_aux
        
        if ajuste['perno4'] >= 0:
            self.ajustes_actuales[7]["value"]["text"] = round(ajuste['perno4'],1)
            self.perno4_aux = round(ajuste['perno4'],1) if abs(round(ajuste['perno4'],1) - self.perno4_aux) <= 0.3 else self.perno4_aux
        
        self.flag_confirmacion = 0
        try:
            if self.alcanzando_valores_propuestos:
                self.proponer_valores(0)
        except:
            pass

    # Actualizar grafico de ajustes debido a un nuevo valor de ajuste
    def actualizar_plot_ajustes(self, ajuste):

        if len(self.plot_ajustes[0]["value"]) == 80: # (Podía ser cualquiera)
            self.plot_ajustes[0]["value"].pop(0)
            self.plot_ajustes[1]["value"].pop(0)
            self.plot_ajustes[2]["value"].pop(0)
            self.plot_ajustes[3]["value"].pop(0)
            self.plot_ajustes[4]["value"].pop(0)
            self.plot_ajustes[5]["value"].pop(0)
            self.plot_ajustes[6]["value"].pop(0)
            self.plot_ajustes[7]["value"].pop(0)

        hora = datetime.now().strftime('%H:%M')

        try:
            self.plot_ajustes[0]["value"].append({ "hora" : hora, "ajuste" : self.camon1[0]["ajuste"] if ajuste["camon1"] < 1 else ajuste["camon1"] })
            self.plot_ajustes[1]["value"].append({ "hora" : hora, "ajuste" : self.camon2[0]["ajuste"] if ajuste["camon2"] < 1 else ajuste["camon2"] })
            self.plot_ajustes[2]["value"].append({ "hora" : hora, "ajuste" : self.camon3[0]["ajuste"] if ajuste["camon3"] < 1 else ajuste["camon3"] })
            self.plot_ajustes[3]["value"].append({ "hora" : hora, "ajuste" : self.camon4[0]["ajuste"] if ajuste["camon4"] < 1 else ajuste["camon4"] })
            self.plot_ajustes[4]["value"].append({ "hora" : hora, "ajuste" : self.perno1[0]["ajuste"] if ajuste["perno1"] < 1 else ajuste["perno1"] })
            self.plot_ajustes[5]["value"].append({ "hora" : hora, "ajuste" : self.perno2[0]["ajuste"] if ajuste["perno2"] < 1 else ajuste["perno2"] })
            self.plot_ajustes[6]["value"].append({ "hora" : hora, "ajuste" : self.perno3[0]["ajuste"] if ajuste["perno3"] < 1 else ajuste["perno3"] })
            self.plot_ajustes[7]["value"].append({ "hora" : hora, "ajuste" : self.perno4[0]["ajuste"] if ajuste["perno4"] < 1 else ajuste["perno4"] })

            for k in range(8):
                x = [ registro["hora"] for registro in self.plot_ajustes[k]["value"] ]
                y = [ registro["ajuste"] for registro in self.plot_ajustes[k]["value"] ]

                self.plot_ajustes[k]["ax"].texts = [] #Remueve las anotaciones
                
                cont = 0
                val_anterior = 0

                for i,j in zip(x,y):
                    if val_anterior != j:
                        signo = -7 if cont % 2 == 0 else 1    
                        self.plot_ajustes[k]["ax"].annotate(str(j), xy=(cont,j+signo*round(max(y)/50, 1)), horizontalalignment='center', verticalalignment='bottom', fontsize=7)
                        
                    cont += 1
                    val_anterior = j

                # create an index for each tick position
                xi = list(range(len(x)))
                delta = round(max(y)/5, 1)

                self.plot_ajustes[k]["ax"].lines.clear() #Actualiza las lineas del grafico
                self.plot_ajustes[k]["ax"].set_xticklabels(x) #Actualiza los labels en eje x
                self.plot_ajustes[k]["ax"].plot(xi, y, marker='o', linestyle='--', color = 'green' if k < 4 else 'blue', markersize=2, linewidth = 0.3) #Inserta nuevo valor y actualiza la posicion de los otros
                self.plot_ajustes[k]["ax"].set_ylim(0, max(y)+delta) #Relimita eje y 

                #Actualizo el gráfico
                self.plot_ajustes[k]["ax"].relim()
                self.plot_ajustes[k]["fig"].canvas.draw_idle()
            
        except:
            pass

    
    def actualizar_limites_pernos(self, limites):
        self.limites_pernos[0].config(text=limites['LP1'])
        self.limites_pernos[1].config(text=limites['LP2'])
        self.limites_pernos[2].config(text=limites['LP3'])
        self.limites_pernos[3].config(text=limites['LP4'])

        db.limites_pernos.update_one({}, { "$set": { "LP1": limites['LP1'], "LP2": limites['LP2'], "LP3": limites['LP3'], "LP4": limites['LP4'] } })

    def actualizar_parametros_produccion(self, parametros_produccion):
        self.TT_ROD = parametros_produccion['TT_ROD']
        self.TT_SBR = parametros_produccion['TT_SBR']
        self.TONS_HORA = parametros_produccion['TONS_HORA']
        self.VEL_MOTOR = parametros_produccion['VEL_MOTOR']


    def variar_ajustes_propuestos(self, ajuste):
        try:
            self.ajustes_propuestos[0]["value"]["text"] = round(ajuste['easing']['to'],1) if ajuste['id'] == 'camon1' else self.ajustes_propuestos[0]["value"]["text"]
            self.ajustes_propuestos[1]["value"]["text"] = round(ajuste['easing']['to'],1) if ajuste['id'] == 'camon2' else self.ajustes_propuestos[1]["value"]["text"]
            self.ajustes_propuestos[2]["value"]["text"] = round(ajuste['easing']['to'],1) if ajuste['id'] == 'camon3' else self.ajustes_propuestos[2]["value"]["text"]
            self.ajustes_propuestos[3]["value"]["text"] = round(ajuste['easing']['to'],1) if ajuste['id'] == 'camon4' else self.ajustes_propuestos[3]["value"]["text"]
            self.ajustes_propuestos[4]["value"]["text"] = round(ajuste['easing']['to'],1) if ajuste['id'] == 'perno1' else self.ajustes_propuestos[4]["value"]["text"]
            self.ajustes_propuestos[5]["value"]["text"] = round(ajuste['easing']['to'],1) if ajuste['id'] == 'perno2' else self.ajustes_propuestos[5]["value"]["text"]
            self.ajustes_propuestos[6]["value"]["text"] = round(ajuste['easing']['to'],1) if ajuste['id'] == 'perno3' else self.ajustes_propuestos[6]["value"]["text"]
            self.ajustes_propuestos[7]["value"]["text"] = round(ajuste['easing']['to'],1) if ajuste['id'] == 'perno4' else self.ajustes_propuestos[7]["value"]["text"]
            
            print('--------------')
            """
            print(self.ajustes_propuestos[0]["value"]["text"] , self.aux_ajustes_propuestos[0])
            print(self.ajustes_propuestos[1]["value"]["text"] , self.aux_ajustes_propuestos[1])
            print(self.ajustes_propuestos[2]["value"]["text"] , self.aux_ajustes_propuestos[2])
            print(self.ajustes_propuestos[3]["value"]["text"] , self.aux_ajustes_propuestos[3])
            print(self.ajustes_propuestos[4]["value"]["text"] , self.aux_ajustes_propuestos[4])
            print(self.ajustes_propuestos[5]["value"]["text"] , self.aux_ajustes_propuestos[5])
            print(self.ajustes_propuestos[6]["value"]["text"] , self.aux_ajustes_propuestos[6])
            print(self.ajustes_propuestos[7]["value"]["text"] , self.aux_ajustes_propuestos[7])
            """
            print('--------------')
            

            val_cam1 = self.ajustes_propuestos[0]["value"]["text"] == self.aux_ajustes_propuestos[0]
            val_cam2 = self.ajustes_propuestos[1]["value"]["text"] == self.aux_ajustes_propuestos[1]
            val_cam3 = self.ajustes_propuestos[2]["value"]["text"] == self.aux_ajustes_propuestos[2]
            val_cam4 = self.ajustes_propuestos[3]["value"]["text"] == self.aux_ajustes_propuestos[3]
            val_per1 = self.ajustes_propuestos[4]["value"]["text"] == self.aux_ajustes_propuestos[4]
            val_per2 = self.ajustes_propuestos[5]["value"]["text"] == self.aux_ajustes_propuestos[5]
            val_per3 = self.ajustes_propuestos[6]["value"]["text"] == self.aux_ajustes_propuestos[6]
            val_per4 = self.ajustes_propuestos[7]["value"]["text"] == self.aux_ajustes_propuestos[7]
            
            #print('Propuestos')
            print(val_cam1, val_cam2, val_cam3, val_cam4, val_per1, val_per2, val_per3, val_per4)          

            ## QUITAR ## 
            #self.aplicar.config(text='Aplicar', bg='#c92222', state=NORMAL, command = lambda: Aplicar_ajustes(self))

            global flag_confirmacion
            if ((val_cam1) and (val_cam2) and(val_cam3) and(val_cam4) and(val_per1) and(val_per2) and(val_per3) and(val_per4)):  
                
                print('ALCANZADO TRUEEE')
                self.alcanzando_valores_propuestos = True # Porque ya los alcanzó
                
                if flag_confirmacion == 0 and self.ajustes_mode == 1: #Automatica

                    flag_confirmacion = 1
                    self.aplicar.config(text='Aplicando...', bg='#c92222', state=DISABLED)
                    self.confirmacion_ajustes()
                    Info('Ajustes aplicados correctamente')
                    pass
                
                else: #Manual
                    print('DEBERIA CAMBIAR BOTON')
                    self.aplicar.config(text='Aplicar', bg='#c92222', state=NORMAL, command = lambda: Aplicar_ajustes(self))


        except:
            pass

    def aplicar_ajustes(self):
        aplicar_ajustes = Aplicar_ajustes(self)
        pass

    def generate_report(self):
        
        defectos_aux = self.tipos_defecto.copy()
        defectos_aux.pop(0)

        seleccionados = [] #Guarda los defectos que quiere ver en el reporte
        cont = 1 #Numero de columnas
        for defecto in defectos_aux:
            if defecto["checked_historico"].get() == 1:
                seleccionados.append(defecto["name"])
                cont = cont + 1

        columns = list(range(1, cont + 2))

        self.tree_historicos_defectos.destroy()

        self.tree_historicos_defectos = ttk.Treeview(self.historicos_tab, columns=columns, show="headings")
        self.tree_historicos_defectos.place(x=10, y=255, height=405)

        self.tree_historicos_defectos.heading(1, text="Fecha")
        self.tree_historicos_defectos.heading(2, text="Hora")
        
        self.tree_historicos_defectos.column(1, width=85)
        self.tree_historicos_defectos.column(2, width=65)

        defectos_seleccionados = { "fecha" : 1 , 
                                   "hora": { "$dateToString": { "format": "%H:%M:%S", "date": "$fecha"}} }
        j = 3
        for defecto in defectos_aux:
            if defecto["num"] != 0:
                if int(defecto["checked_historico"].get()) == 1: 
                    if defecto["name"] == "Ecuador":
                        defectos_seleccionados["ecuador"] = 1
                    if defecto["name"] == "Ojo":
                        defectos_seleccionados["ojo"] = 1
                    if defecto["name"] == "Lamina":
                        defectos_seleccionados["lamina"] = 1
                    if defecto["name"] == "Tipo Huevo":
                        defectos_seleccionados["tipo_huevo"] = 1
                    if defecto["name"] == "Desgarro de Polo":
                        defectos_seleccionados["desgarro_de_polo"] = 1
                    if defecto["name"] == "Tetilla":
                        defectos_seleccionados["tetilla"] = 1

                    self.tree_historicos_defectos.heading(j, text=defecto["name"])
                    self.tree_historicos_defectos.column(j, width=135, anchor="center")

                    j = j + 1
        
        desde = datetime.strptime(self.cal.get_date(),'%d-%m-%y')
        hasta = datetime.strptime(self.cal2.get_date(),'%d-%m-%y')
        
        historicos = db.historico_defecto.aggregate(
            [
               { '$project' : defectos_seleccionados },
               { "$match" :
                    { "$and" : [
                        { "$expr": {  "fecha" : [ "$gt", desde ]  }  }, 
                        { "$expr": {  "fecha" : [ "$lt", hasta ]  }  }
                        ] 
                    }
               },
               { "$sort" : { "_id" : -1 } }
            ]
        )

        for historico in list(historicos):
            self.tree_historicos_defectos.insert('', 'end', values = [str(historico[i])+'%' for x, i in enumerate(defectos_seleccionados)])
        
        try:
            self.scroll_defectos.destroy()
        except:
            pass

        self.scroll_defectos =ttk.Scrollbar(self.historicos_tab, orient="vertical", command=self.tree_historicos_defectos.yview)
        self.scroll_defectos.place(x=22+(len(defectos_seleccionados) - 1) * 135, y=255, height=405)

        self.tree_historicos_defectos.configure(yscrollcommand=self.scroll_defectos.set)
        
    def destructor(self):
        self.win2.destroy()

    #Funcion que se gatilla al cambiar de pestaña
    def change_tab(self, event):
        if(event.widget.tab('current')['text'] == 'Administrador'): #Despliega ventana de autentificación para acceder a configuraciones
            adminTab = AdminTab(self)
        else: #Elimina la ventana en caso de que vaya a una pestaña que no sea Administrador
            try:
                for widget in self.win2.winfo_children():
                    if isinstance(widget, tk.Toplevel): #If widget is an instance of toplevel
                        widget.destroy()
            except:
                pass
    
    #Funcion para cambiar el modo de visualización entre manual y automatico
    def change_modo_estadistico(self, modo):
        self.inferencias_mode = modo
        if self.inferencias_mode == 0: #Manual
            self.btn_inferencias_manual.config(bg='green')
            self.btn_inferencias_automatico.config(bg='gray')
        else:
            self.btn_inferencias_manual.config(bg='gray')
            self.btn_inferencias_automatico.config(bg='green')

    def change_modo_ajustes(self, modo):
        self.ajustes_mode = int(modo)
        if self.ajustes_mode == 0: #Manual
            self.manual_.config(bg='green')
            self.automatico_.config(bg='gray')
            self.aplicar.config(state=NORMAL, command = lambda: self.aplicar_ajustes())
        else:
            self.aplicar.config(state=DISABLED, command = lambda: self.nothing())
            self.manual_.config(bg='gray')
            self.automatico_.config(bg='green')

            
    def destroy_alarma(self):
        try:
            for i, ajuste in enumerate(self.ajustes_actuales):
                ajuste['value']['text'] = ''
        except:
            pass
        negro = np.zeros([400,400,3],dtype=np.uint8)
        cv2.putText(negro, 'Ultimo defecto', (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (255, 0, 0), 1)
        
        negro = Image.fromarray(negro)

        imgtk4 = ImageTk.PhotoImage(image=negro)  # convert image for tkinter
        self.panel3.imgtk4 = imgtk4  # anchor imgtk so it does not be deleted by garbage-collector
        self.panel3.config(image=imgtk4)  # show the image

        """
        client1.connect(broker,port)        #establish connection
        client1.publish("node/alarm", 0, qos=0, retain=False)
        """

        self.popup.destroy()

    def center(self,toplevel):
        toplevel.update_idletasks()
        w = toplevel.winfo_screenwidth()
        h = toplevel.winfo_screenheight()
        size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
        x = w/2 - size[0] + 60
        y = h/2 - size[1]/2 + 80
        toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))


class Alarma(tk.Frame, object):
    def __init__(self, win2, defecto):
        tk.Frame.__init__(self, win2)

        self.win_alarma=tk.Toplevel()
        self.win_alarma.geometry("520x310")
        self.win_alarma.resizable(width=False, height=False)
        self.win_alarma.config(cursor="arrow")
        self.win_alarma.title("ALARMA DEFECTO RF2")
        self.center(self.win_alarma)

        background_image2= tk.PhotoImage(file =str(path)+'/img/fondo_alerta.png')
        background_label2= tk.Label(self.win_alarma , image=background_image2)
        background_label2.image = background_image2        
        background_label2.place(x=0, y=0, relwidth=1, relheight=1)

        tk.Button(self.win_alarma, text='Quitar', borderwidth=1, bg="#ff3737", highlightbackground="black",
                                                highlightcolor="#f3ee2b", highlightthickness=2, command = lambda: self.destructor(win2)).place(x=305,y=50, height=30, width=100)

        #negro = np.zeros([250,250,3],dtype=np.uint8)

        imagen =  np.asarray(defecto['img'], dtype=np.uint8)
        negro = imagen

        negro = Image.fromarray(negro)
        img   = ImageTk.PhotoImage(image=negro)  # convert image for tkinter

        panel3 = tk.Label(self.win_alarma, width=250, height=250)  # initialize fail panel
        panel3.imgtk4 = img  # anchor imgtk so it does not be deleted by garbage-collector
        panel3.place(x=15,y=42) #130
        panel3.config(image=img)  # show the image

        move_y = 130
        move_x = 300

        tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='Defecto: ').place(x=move_x,y=move_y)

        move_x += 85
        tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='{0}'.format(defecto['name']), fg= "red").place(x=move_x,y=move_y)

        move_y += 20
        move_x = 300
        tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='Nivel de intensidad: ').place(x=move_x,y=move_y)

        move_x += 145
        tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='{0}%'.format(defecto['intensity']), fg= "red").place(x=move_x,y=move_y)
        #tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='{0}%'.format(str('')), fg= "red").place(x=move_x,y=move_y)
        
        move_y += 20
        move_x = 300
        tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='Cota de Alarma: ').place(x=move_x,y=move_y)

        move_x += 160
        tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='{0}%'.format(str(win2.cota_alarma.get())), fg= "red").place(x=move_x,y=move_y)
        #tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='{0}%'.format(str('')), fg= "red").place(x=move_x,y=move_y)

        move_y += 20
        move_x = 300
        tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='Fecha: ').place(x=move_x,y=move_y)

        move_x += 50
        tk.Label(self.win_alarma, font=("Helvetica bold", 10), bg="#f2f1f0", text='{0}'.format(datetime.now().strftime('%d-%m-%Y %H:%M:%S')), fg= "red").place(x=move_x,y=move_y)
        
    def volver(self):
        self.win_alarma.destroy()
        
    def destructor(self, win2):

        """
        client1.connect(broker,port)        #establish connection
        client1.publish("node/alarm", 0, qos=0, retain=False)
        """

        db.selector.update_one({}, { "$set": { "status" : 1 } })
        #os.system("sudo python3 ser_ON-OFF.py 0")
        db.selector.update_one({}, { "$set": { "status" : 0 } })

        self.win_alarma.destroy()
        
    def center(self,toplevel):
        toplevel.update_idletasks()
        w = toplevel.winfo_screenwidth()
        h = toplevel.winfo_screenheight()
        size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
        x = w/2 - size[0]/2
        y = h/2 - size[1]/2
        toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))

class Info(object):
    def __init__(self, msg):
        self.win_info=tk.Toplevel()
        self.win_info.geometry("400x140")
        self.win_info.overrideredirect(1)
        self.win_info.resizable(width=False, height=False)
        self.win_info.config(cursor="arrow")
        self.win_info.title("")
        self.center(self.win_info)

        background_image2= tk.PhotoImage(file =str(path)+'/img/fondo_alerta.gif')
        background_label2= tk.Label(self.win_info, image=background_image2)
        background_label2.image = background_image2        
        background_label2.place(x=0, y=0, relwidth=1, relheight=1)

        texto_alarma3= tk.Label(self.win_info, font=("Helvetica", 14), text=msg, bg= "#F2F1F0")
        texto_alarma3.place(x=105,y=60)

        self.win_info.after(3000, lambda: self.win_info.destroy()) # Destroy the widget after 30 seconds
        self.win_info.mainloop()

    def volver(self):
        self.win_info.destroy()
        
    def destructor(self):
        self.win_reiniciando.destroy()
        
    def center(self,toplevel):
        toplevel.update_idletasks()
        w = toplevel.winfo_screenwidth()
        h = toplevel.winfo_screenheight()
        size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
        x = w/2 - size[0]/2
        y = h/2 - size[1]/2
        toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))

class Informados(tk.Frame):
    def __init__(self, win2):
        tk.Frame.__init__(self, win2)
        self.win_informados=tk.Toplevel()
        self.win_informados.geometry("450x590")
        self.win_informados.resizable(width=False, height=False)
        self.win_informados.config(cursor="arrow")
        self.win_informados.title("Informe de Actividad")
        self.center(self.win_informados)

        move_y = 5
        year = datetime.now().year
        month = datetime.now().month
        day = datetime.now().day
        
        w = self.win_informados.winfo_width()
        h = self.win_informados.winfo_height()
        
        self.fecha_informados = Calendar(self.win_informados, font="Arial 11", selectmode="day", year=year, month=month, day=day)
        self.fecha_informados.bind('<<CalendarSelected>>', self.get_constancias)
        self.fecha_informados.place(x=w/5, y=move_y)

        move_y += 240
        #Lista con las constancias del día específicado
        self.tree_constancias = ttk.Treeview(self.win_informados, columns = (1,2,3), show = "headings")
        self.tree_constancias.place(x=15, y=move_y, height=260)
        
        self.tree_constancias.heading(1, text="Hora")
        self.tree_constancias.heading(2, text="Defecto")
        self.tree_constancias.heading(3, text="Intensidad")

        self.tree_constancias.column(1, width = 80)
        self.tree_constancias.column(2, width = 230, anchor="center")
        self.tree_constancias.column(3, width = 100, anchor="center")
        
        ttk.Scrollbar(self.win_informados, orient="vertical", command=self.tree_constancias.yview).place(x=w-15, y=move_y, height=260)
        
        move_y += 220
        tk.Button(self.win_informados, text='Cerrar', bg='#b00202', command = lambda: self.destructor()).place(x=w/2- 40,y=h-60, height=40, width=80)

        self.get_constancias(self) #Inicialización
        self.win_informados.mainloop()

    def get_constancias(self, e):
        fecha = datetime.strptime(self.fecha_informados.get_date(),'%d-%m-%y')

        query = db.constancia.find(
            { "$expr": 
                { "$and" : 
                    [  
                        { "$eq": [{ "$month": "$fecha" }, { "$month": fecha }] },  
                        { "$eq": [{ "$year": "$fecha" }, { "$year": fecha }] },
                        { "$eq": [{ "$dayOfMonth": "$fecha" }, { "$dayOfMonth": fecha }] }
                    ] 
                } 
            }
        )
        
        #Clear the treeview list items
        for item in self.tree_constancias.get_children():
            self.tree_constancias.delete(item)

        for x in query:
            x["hora"] = x["fecha"].strftime('%H:%M:%S') #Hora actual
            x["intensity"] = str(x["presencia"])
            if x["presencia"] == 0:
                presencia = '-'
            elif x["presencia"] == 1:
                presencia = 'Muy Baja'
            elif x["presencia"] == 2:
                presencia = 'Baja'
            elif x["presencia"] == 3:
                presencia = 'Media'
            elif x["presencia"] == 4:
                presencia = 'Alta'
            elif x["presencia"] == 5:
                presencia = 'Muy Alta'

            self.tree_constancias.insert('', 'end', values = ( x["hora"], x["error"], presencia))

    def volver(self):
        self.win_informados.destroy()
        
    def destructor(self):
        self.win_informados.destroy()

        #cv2.destroyAllWindows()  # it is not mandatory in this application

    def center(self,toplevel):
        toplevel.update_idletasks()
        w = toplevel.winfo_screenwidth()
        h = toplevel.winfo_screenheight()
        size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
        x = w/2 - size[0]/2
        y = h/2 - size[1]/2
        toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))

class Ajustes(tk.Frame):

    def __init__(self, win2, intensity):
        tk.Frame.__init__(self, win2)
        self.win_ajustes=tk.Toplevel()
        self.win_ajustes.protocol("WM_DELETE_WINDOW", self.__callback)
        self.win_ajustes.overrideredirect(1)
        self.win_ajustes.geometry("400x290")
        self.win_ajustes.resizable(width=False, height=False)
        self.win_ajustes.config(cursor="arrow")
        self.win_ajustes.title("Confirmar ajustes")
        self.win_ajustes.resizable(0,0)    
        
        canvas = tk.Canvas(self.win_ajustes, width=400, height=290, borderwidth=0, highlightthickness=0, bg="#828282")
        canvas.create_rectangle(5, 5, 395, 285, outline="#302f2f", width=2, fill="#a39ea8")
        canvas.grid()

        self.center(self.win_ajustes)
        
        if intensity == 1:
            intensity = 'Muy Baja'
        elif intensity == 2:
            intensity = 'Baja'
        elif intensity == 3:
            intensity = 'Media'
        elif intensity == 4:
            intensity = 'Alta'
        elif intensity == 5:
            intensity = 'Muy Alta'

        tk.Label(self.win_ajustes, font=("Helvetica", 14), text="¿Fué resuelto el error señalado?", bg="#a39ea8", fg="red").place(x=60,y=30)
        tk.Label(self.win_ajustes, font=("Helvetica", 14), text="Defecto: "+win2.defecto_seleccionado_name, bg="#a39ea8", fg="#d9ba09").place(x=150-len(win2.defecto_seleccionado_name)*3,y=60)
        tk.Label(self.win_ajustes, font=("Helvetica", 14), text="Intensidad: "+intensity, bg="#a39ea8", fg="#8a5d01").place(x=160-len(win2.defecto_seleccionado_name)*2,y=90)
        tk.Label(self.win_ajustes, font=("Helvetica", 12), text="Hora: "+str(datetime.now()), bg="#a39ea8", fg="#0d0a06").place(x=90,y=120)

        tk.Button(self.win_ajustes, text='Si', bd="3", relief=SUNKEN, bg='#449126', command = lambda: self.defecto_resuelto(win2)).place(x=25,y=180, height=40, width=150)
        tk.Button(self.win_ajustes, text='No', bd="3", relief=SUNKEN, bg='#9c201e', command = lambda: self.defecto_noresuelto()).place(x=225,y=180, height=40, width=150)

    def defecto_resuelto(self, win2):
        self.destructor()

        payload = json.dumps({ "presencia": 0, "error": win2.defecto_seleccionado_name.replace(" ", "_")+'_Fixed' })
        
        #Publica para que el node-red modifique la BD
        
        client1.connect(broker,port)        #establish connection
        try:
            client1.publish("node/set", payload, qos=0, retain=False)
        
            os.system("sudo python3 ser_ON-OFF.py 0")

            info = Info('Gracias! Datos guardados...')
        except ConnectionAbortedError:
            pass

    def defecto_noresuelto(self):
        info = Info('Favor de resolver el defecto')
        pass

    def volver(self):
        self.win_ajustes.destroy()
        
    def destructor(self):
        self.win_ajustes.destroy()
        #cv2.destroyAllWindows()  # it is not mandatory in this application

    def center(self,toplevel):
        toplevel.update_idletasks()
        w = toplevel.winfo_screenwidth()
        h = toplevel.winfo_screenheight()
        size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
        x = w/2 - size[0]/2
        y = h/2 - size[1]/2
        toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))

    @staticmethod
    def __callback():
        return

class Aplicar_ajustes(tk.Frame):

    def __init__(self, win2):
        tk.Frame.__init__(self, win2)
        self.win_aplicar_ajustes=tk.Toplevel()
        self.win_aplicar_ajustes.geometry("400x120")
        self.win_aplicar_ajustes.resizable(width=False, height=False)
        self.win_aplicar_ajustes.config(cursor="arrow")
        self.win_aplicar_ajustes.title("Aplicar ajustes")
        self.win_aplicar_ajustes.resizable(0,0)

        canvas = tk.Canvas(self.win_aplicar_ajustes, width=400, height=290, borderwidth=0, highlightthickness=0, bg="#828282")
        canvas.create_rectangle(5, 5, 395, 285, outline="#302f2f", width=2, fill="#a39ea8")
        canvas.grid()

        self.center(self.win_aplicar_ajustes)
        
        tk.Label(self.win_aplicar_ajustes, font=("Helvetica", 14), text="¿Está seguro que desea aplicar estos ajustes?", bg="#a39ea8", fg="red").place(x=15,y=30)
        
        tk.Button(self.win_aplicar_ajustes, text='Si', bd="3", relief=SUNKEN, bg='#449126', command = lambda: self.aplicar(win2)).place(x=25,y=65, height=40, width=150)
        tk.Button(self.win_aplicar_ajustes, text='No', bd="3", relief=SUNKEN, bg='#9c201e', command = lambda: self.destructor()).place(x=225,y=65, height=40, width=150)


    def volver(self):
        self.win_aplicar_ajustes.destroy()
        
    def destructor(self):
        self.win_aplicar_ajustes.destroy()
        #cv2.destroyAllWindows()  # it is not mandatory in this application

    def aplicar(self, win2):

        win2.confirmacion_ajustes()
        self.win_aplicar_ajustes.destroy()
        Info('Ajustes aplicados correctamente')
        
        #cv2.destroyAllWindows()  # it is not mandatory in this application

    def center(self,toplevel):
        toplevel.update_idletasks()
        w = toplevel.winfo_screenwidth()
        h = toplevel.winfo_screenheight()
        size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
        x = w/2 - size[0]/2
        y = h/2 - size[1]/2
        toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))


class AdminTab(tk.Frame):

    def __init__(self, win2):
        tk.Frame.__init__(self, win2)
        self.win_code_admin=tk.Toplevel()
        self.win_code_admin.geometry("1019x690")
        self.win_code_admin.resizable(width=False, height=False)
        self.win_code_admin.protocol("WM_DELETE_WINDOW", self.__callback)
        self.win_code_admin.overrideredirect(1)
        self.win_code_admin.config(cursor="arrow")
        self.win_code_admin.title("")
        self.win_code_admin.resizable(0,0)
        self.center(self.win_code_admin)

        self.code = tk.StringVar() #Codigo de acceso a las configuraciones de la pestaña
        
        #Mensaje de error al ingresar codigo incorrecto
        self.error_label = tk.Label(self.win_code_admin, font=("Helvetica", 13, 'bold'), text='', fg="red")
        self.error_label.place(x=430,y=450)  
        
        tk.Label(self.win_code_admin, font=("Helvetica", 14, 'bold'), text= "Ingrese el código de acceso").place(x=410,y=150)

        tk.Button(self.win_code_admin, text='1', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(1, win2)).place(x=440,y=200, height=60, width=60)
        tk.Button(self.win_code_admin, text='2', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(2, win2)).place(x=500,y=200, height=60, width=60)
        tk.Button(self.win_code_admin, text='3', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(3, win2)).place(x=560,y=200, height=60, width=60)
        tk.Button(self.win_code_admin, text='4', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(4, win2)).place(x=440,y=260, height=60, width=60)
        tk.Button(self.win_code_admin, text='5', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(5, win2)).place(x=500,y=260, height=60, width=60)
        tk.Button(self.win_code_admin, text='6', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(6, win2)).place(x=560,y=260, height=60, width=60)
        tk.Button(self.win_code_admin, text='7', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(7, win2)).place(x=440,y=320, height=60, width=60)
        tk.Button(self.win_code_admin, text='8', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(8, win2)).place(x=500,y=320, height=60, width=60)
        tk.Button(self.win_code_admin, text='9', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(9, win2)).place(x=560,y=320, height=60, width=60)
        tk.Button(self.win_code_admin, text='', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2).place(x=440,y=380, height=60, width=60)
        tk.Button(self.win_code_admin, text='0', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2, command = lambda: self.tap_code(0, win2)).place(x=500,y=380, height=60, width=60)
        tk.Button(self.win_code_admin, text='', bg='#0077cc', highlightthickness=1, highlightbackground="#202424", borderwidth=2).place(x=560,y=380, height=60, width=60)

        self.win_code_admin.mainloop()

    @staticmethod
    def __callback():
        return

    def tap_code(self, num, win2): #Se gatilla cada vez que se ingresa un dígito en el codigo de acceso
        self.code.set(str(self.code.get()) + str(num))
        
        if(len(str(self.code.get())) == 1):
            self.error_label['text'] = ''

            punto = Image.open(str(path)+'/img/punto.png')
            punto = ImageTk.PhotoImage(punto)

            self.background_label= tk.Label(self.win_code_admin, image=punto, borderwidth=0)
            self.background_label.image = punto        
            self.background_label.place(x=515, y=450)

        elif(len(str(self.code.get())) == 2):
            if(str(self.code.get()) == '30'):
                alarma = db.alarma.find_one()
                cota_num = [int(i) for i in str(alarma["umbral"])]
                razon_inferencias = [int(i) for i in str(alarma["razon_inferencias"])]

                if len(cota_num) == 2:
                    digito1 = cota_num[0]
                    digito2 = cota_num[1]
                else:
                    digito1 = 0
                    digito2 = cota_num[0]

                if len(razon_inferencias) == 2:
                    digito3 = razon_inferencias[0]
                    digito4 = razon_inferencias[1]
                else:
                    digito3 = 0
                    digito4 = razon_inferencias[0]
                
                win2.cota_alarma.set(int(str(digito1)+str(digito2)))
                win2.razon_inferencias.set(int(str(digito3)+str(digito4)))
                #win2.alarma = tk.Entry(win2.admin_tab)

                win2.alarma_dig1 = tk.Button(win2.admin_tab, bg='orange', text=digito1, highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.select_dig(1, win2))
                win2.alarma_dig2 = tk.Button(win2.admin_tab, bg='orange', text=digito2, highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.select_dig(2, win2))

                win2.alarma_dig3 = tk.Button(win2.admin_tab, bg='orange', text=digito3, highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.select_dig(3, win2))
                win2.alarma_dig4 = tk.Button(win2.admin_tab, bg='orange', text=digito4, highlightthickness=1, highlightbackground="#202424", borderwidth=3, command = lambda: self.select_dig(4, win2))


                move_y = 105
                win2.alarma_dig1.place(x=40, y=move_y, width=30)
                win2.alarma_dig2.place(x=75, y=move_y, width=30)

                win2.alarma_dig3.place(x=255, y=move_y, width=30)
                win2.alarma_dig4.place(x=290, y=move_y, width=30)

                self.destructor()
            else:
                self.code.set('')
                self.background_label.destroy()
                self.error_label['text'] = 'Código incorrecto! \n Inténtelo nuevamente...'
                
    def select_dig(self, pos, win2):
        self.win_cota_alarma=tk.Toplevel()
        self.win_cota_alarma.geometry("430x130")
        self.win_cota_alarma.resizable(width=False, height=False)
        self.win_cota_alarma.config(cursor="arrow")
        self.win_cota_alarma.title("")
        self.center(self.win_cota_alarma)
        
        tk.Button(self.win_cota_alarma, text='0', bg='#0077cc', command = lambda: self.umbral_builder(0, pos, win2)).place(x=15,y=40, height=40, width=40)
        tk.Button(self.win_cota_alarma, text='1', bg='#0077cc', command = lambda: self.umbral_builder(1, pos, win2)).place(x=55,y=40, height=40, width=40)
        tk.Button(self.win_cota_alarma, text='2', bg='#0077cc', command = lambda: self.umbral_builder(2, pos, win2)).place(x=95,y=40, height=40, width=40)
        tk.Button(self.win_cota_alarma, text='3', bg='#0077cc', command = lambda: self.umbral_builder(3, pos, win2)).place(x=135,y=40, height=40, width=40)
        tk.Button(self.win_cota_alarma, text='4', bg='#0077cc', command = lambda: self.umbral_builder(4, pos, win2)).place(x=175,y=40, height=40, width=40)
        tk.Button(self.win_cota_alarma, text='5', bg='#0077cc', command = lambda: self.umbral_builder(5, pos, win2)).place(x=215,y=40, height=40, width=40)
        tk.Button(self.win_cota_alarma, text='6', bg='#0077cc', command = lambda: self.umbral_builder(6, pos, win2)).place(x=255,y=40, height=40, width=40)
        tk.Button(self.win_cota_alarma, text='7', bg='#0077cc', command = lambda: self.umbral_builder(7, pos, win2)).place(x=295,y=40, height=40, width=40)
        tk.Button(self.win_cota_alarma, text='8', bg='#0077cc', command = lambda: self.umbral_builder(8, pos, win2)).place(x=335,y=40, height=40, width=40)
        tk.Button(self.win_cota_alarma, text='9', bg='#0077cc', command = lambda: self.umbral_builder(9, pos, win2)).place(x=375,y=40, height=40, width=40)
    
    def umbral_builder(self, dig, pos, win2):
        if int(pos) == 1:
            arr_num = [int(i) for i in str(win2.cota_alarma.get())]
            if len(str(win2.cota_alarma.get())) == 2:
                win2.cota_alarma.set(int(str(dig) + str(arr_num[1])))
                win2.alarma_dig1['text'] = str(dig)
                win2.alarma_dig2['text'] = str(arr_num[1])
            else:
                win2.cota_alarma.set(int(str(dig) + str(arr_num[0])))
                win2.alarma_dig1['text'] = str(dig)
                win2.alarma_dig2['text'] = str(arr_num[0])
        elif int(pos) == 2:
            arr_num = [int(i) for i in str(win2.cota_alarma.get())]
            if len(str(win2.cota_alarma.get())) == 2:
                win2.cota_alarma.set(int(str(arr_num[0])+ str(dig)))
                win2.alarma_dig1['text'] = str(arr_num[0])
                win2.alarma_dig2['text'] = str(dig)
            else:
                win2.cota_alarma.set(int(str(dig)))
                win2.alarma_dig1['text'] = 0
                win2.alarma_dig2['text'] = str(dig)
        elif int(pos) == 3:
            arr_num = [int(i) for i in str(win2.razon_inferencias.get())]
            if len(str(win2.razon_inferencias.get())) == 2:
                win2.razon_inferencias.set(int(str(dig) + str(arr_num[1])))
                win2.alarma_dig3['text'] = str(dig)
                win2.alarma_dig4['text'] = str(arr_num[1])
            else:
                win2.razon_inferencias.set(int(str(dig) + str(arr_num[0])))
                win2.alarma_dig3['text'] = str(dig)
                win2.alarma_dig4['text'] = str(arr_num[0])
        elif int(pos) == 4:
            arr_num = [int(i) for i in str(win2.razon_inferencias.get())]
            if len(str(win2.razon_inferencias.get())) == 2:
                win2.razon_inferencias.set(int(str(arr_num[0])+ str(dig)))
                win2.alarma_dig3['text'] = str(arr_num[0])
                win2.alarma_dig4['text'] = str(dig)
            else:
                win2.razon_inferencias.set(int(str(dig)))
                win2.alarma_dig3['text'] = 0
                win2.alarma_dig4['text'] = str(dig)
        
        
        self.win_cota_alarma.destroy()

    def select_dig2(self, dig1):
        self.win_cota_alarma.destroy()

    def volver(self):
        self.win_code_admin.destroy()
        
    def destructor(self):
        self.win_code_admin.destroy()
        #cv2.destroyAllWindows()  # it is not mandatory in this application

    def center(self,toplevel):
        toplevel.update_idletasks()
        w = toplevel.winfo_screenwidth()
        h = toplevel.winfo_screenheight()
        size = tuple(int(_) for _ in toplevel.geometry().split('+')[0].split('x'))
        x = w/2 - size[0]/2
        y = 83#h/2 - size[1]/2
        toplevel.geometry("%dx%d+%d+%d" % (size + (x, y)))

#Secuencia principal
imageHub = imagezmq.ImageHub()

def mongo_connect():
    try:
        mongo_client = MongoClient("mongodb://localhost:27017/ecmc_ia",serverSelectionTimeoutMS=1)
        #mongo_client = MongoClient("mongodb://localhost:27017/ecmc_ia",serverSelectionTimeoutMS=1)
        mongo_client.server_info() # force connection on a request as the connect=True parameter of MongoClient seems to be useless here
        
        global db
        db = mongo_client["ecmc_ia"]
        print('Mongo Connection Succesfully')
    except ServerSelectionTimeoutError as err:
        print('Mongo Connection Fails')
        time.sleep(5)
        main()

def main():
    try:  
        global pba
        
        mongo_connect()
        pba = Ventana()
        pba.win2.mainloop()
    except:
        #/bin/bash /home/molly/Escritorio/Terreno/Entorno/kill.sh
        #su molly -c "DISPLAY=:0.0 /usr/bin/python3 /home/molly/Escritorio/Terreno/Entorno/entorno_test.py"
        pass

#Lanzador
if __name__ == '__main__':
    main()
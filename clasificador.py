íimport imagezmq
import json
import cv2
import subprocess
from datetime import datetime
import numpy as np
import math
import time
from threading import Timer

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

server_ip             = ('10.0.2.2') #IP del entorno al que se envían los frames 
sender                = imagezmq.ImageSender(connect_to="tcp://{}:5555".format(server_ip)) #Instancia del enviador de imágenes
db                    = ''
arr_inferencias_positivas  = [] #Almacena las inferencias en un minuto y se limpia al final del minuto

inferencias_totales        = 0 
inferencias_positivas      = 0
cant_laminas_medias        = 0 
cant_laminas_bajas         = 0         

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

fifo = 1

def reset_counter():
    global db

    moly_ocupado = db.moly_ocupado.find_one()
    if moly_ocupado["status"] == 0:
        global arr_inferencias_positivas
        global inferencias_totales
        global inferencias_positivas
        global cant_laminas_medias
        global cant_laminas_bajas
        
        sorted_inferencias = arr_inferencias_positivas.copy() #Ordena inferencias segun intensidad
        sorted_inferencias.sort(key=lambda x: x["max_intensity"], reverse=True)
        sorted_inferencias = sorted_inferencias[:4] #4 inferencias con mayores intensidades

        print('\n****************************')
        print('Inferencias totales: ', inferencias_totales, '\n')
        print('Inferencias con positivos: ', inferencias_positivas, '\n')
        print('Laminas totales: ', str(cant_laminas_bajas+cant_laminas_medias))
        print('Laminas medias: ', cant_laminas_medias)
        print('Laminas bajas: ', cant_laminas_bajas)
        print('\n****************************')

        final_obj = {}
        final_obj["dispName"] = "SORTER"
        final_obj["alarma"]   = 0
        final_obj["num_defecto"]   = 3
        final_obj["inferencias_totales"] = inferencias_totales
        final_obj["inferencias_positivas"] = inferencias_positivas
        final_obj["max_intensidad"] = 0
        final_obj["raw_img"] = []
        final_obj["annotations"] = []
        final_obj["cantidad_laminas"] = cant_laminas_bajas
        final_obj["success"] = 0 if inferencias_totales == 0 else round(inferencias_positivas*100/inferencias_totales, 1) #Porcentaje de inferencias con positivos respecto al total
        final_obj["cropped_images"] = [ inferencia["cropped_images"][0]["img"] for inferencia in sorted_inferencias ]
        final_obj["greather_class"] = ''
        
        # Open inferences log
        with open("inferences.log", "a") as log:
            log.write("\n"+str(datetime.now().strftime('%H:%M:%S %d-%m-%Y'))+ " IT: "+str(inferencias_totales)+ " IP: "+str(inferencias_positivas)+" L_M: "+str(cant_laminas_medias)+ " L_B: "+str(cant_laminas_bajas))

        cant_laminas = cant_laminas_bajas + cant_laminas_medias
        
        greather_cropped_image = np.zeros((250, 250), np.uint8)
        greather_cropped_class = ''
        greather_cropped_intensity = 0

        try:
            greather_cropped_image = np.asarray(sorted_inferencias[0]["cropped_images"][0]["img"], dtype=np.uint8) #Inferencia con la prediccion de más alta intensidad
            greather_cropped_class = sorted_inferencias[0]["cropped_images"][0]["class"]
            greather_cropped_intensity = sorted_inferencias[0]["cropped_images"][0]["intensity"]

            final_obj["max_intensidad"] = sorted_inferencias[0]["cropped_images"][0]["intensity"]
            final_obj["greather_class"] = sorted_inferencias[0]["cropped_images"][0]["class"]

            final_obj["raw_img"] = sorted_inferencias[0]["raw_img"].tolist() #Imagen que resulto con la intensidad de defecto mas alta
            
            final_obj["annotations"] = sorted_inferencias[0]["annotations"] #Con sus respectivas anotaciones
            
        except:
            pass

        

        cv2.putText(greather_cropped_image, greather_cropped_class+' : '+str(greather_cropped_intensity)+'%', (5, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (150, 50, 10), 1)        
            
        cv2.putText(greather_cropped_image, 'Ultimo defecto', (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (100, 0, 255), 1)        
        cv2.putText(greather_cropped_image, datetime.now().strftime('%H:%M:%S %d-%m-%Y'), (150, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (255, 255, 255), 1)
        cv2.putText(greather_cropped_image, "Esperando calculo de ajustes..", (118, 215), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (130, 50, 70), 1)     

        print('Razón: {}% ({}/{})'.format(final_obj["success"], final_obj["inferencias_positivas"], final_obj["inferencias_totales"] ))
        cv2.putText(greather_cropped_image, 'Razon: {}% ({}/{})'.format(final_obj["success"], final_obj["inferencias_positivas"], final_obj["inferencias_totales"] ), (5, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (190, 170, 110), 1)        
        
        alarma = db.alarma.find_one()

        #final_obj["success"] = 10
        #final_obj["max_intensidad"] = 20

        if final_obj["success"] > int(alarma["umbral"]): # 25% de inferencias positivas para gatillar la alarma
            
            ocupado = 1
            cv2.putText(greather_cropped_image, 'CONDICION: CRITICA', (5, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (190, 170, 110), 1)        
            
            final_obj["alarma"] = 1
            try:
                response = sender.send_image_reqrep(json.dumps(final_obj), greather_cropped_image)
            except:
                pass
        else:
            
            if cant_laminas > 0:
                cv2.putText(greather_cropped_image, 'CONDICION: NORMAL', (5, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (40, 170, 25), 1)             
                try:
                    response = sender.send_image_reqrep(json.dumps(final_obj), greather_cropped_image)
                except:
                    pass
            else:
                try:
                    final_obj["num_defecto"] = 0
                    response = sender.send_image_reqrep(json.dumps(final_obj), np.zeros((250, 250),np.uint8))
                except:
                    pass

        cant_laminas_medias = 0
        cant_laminas_bajas = 0
        
        inferencias_positivas = 0
        inferencias_totales = 0
        arr_inferencias_positivas = []
    
    else:
        print('MOLY OCUPADO - Cambiar flag a 0 en coleccion moly_ocupado')

rt = RepeatedTimer(60, reset_counter) # it auto-starts, no need of rt.start()
def smart_prediction():
    global arr_inferencias_positivas
    global inferencias_positivas
    global inferencias_totales
    global cant_laminas_medias
    global cant_laminas_bajas

    try:
        while True:  
            #Ciclo de adquisicion de imagenes
            try:
                (data, img) = imageHub.recv_image()
                imageHub.send_reply(b'OK') #Respuesta al python de Deteccion para que el loop siga
                data = json.loads(data)
            except:
                return smart_prediction()
                
            cv2.imwrite("img.png", img)
            output = subprocess.check_output('base64 img.png | curl -d @- "http://localhost:9001/laminar_defects_global/4?api_key=d3AnhKSrN2QxAFLUsr0y"', shell=True)
            res = json.loads(output)

            if len(res["predictions"]) > 0: #Inferencia con positivo(s)
                """
                try:
                    cv2.imwrite('/media/nano/UBUNTU 18_0/Laminas/images/'+str(time.strftime("%Y%m%d-%H%M%S"))+'.png', img)
                    anotaciones = open('/media/nano/UBUNTU 18_0/Laminas/annotations/'+str(time.strftime("%Y%m%d-%H%M%S"))+".txt", "w") 
                except:
                    pass
                """

                inference_info = { "raw_img": img.copy(), "annotations" : [], "cropped_images": [], "max_intensity": 0 }
                
                for prediccion in res["predictions"]:

                    x1 = int(prediccion["x"]) - int(prediccion["width"]/2)
                    y1 = int(prediccion["y"]) - int(prediccion["height"]/2)
                    x2 = int(prediccion["x"]) + int(prediccion["width"]/2)
                    y2 = int(prediccion["y"]) + int(prediccion["height"]/2)

                intensity = round((math.hypot(x2 - x1, y2 - y1)),1)

                num_class = 1
                if prediccion["class"] == "Lamina_media":
                    cv2.rectangle(img, (x1,y1), (x2,y2), (0, 0, 255), thickness=1)
                    num_class = 2
                    cant_laminas_medias += 1
                    intensity *= 0.30                        
                else:
                    intensity *= 0.15
                    cv2.rectangle(img, (x1,y1), (x2,y2), (255, 100, 0), thickness=1)
                    cant_laminas_bajas += 1
                    
                annotation = str(num_class)+' '+str(prediccion["x"])+' '+str(prediccion["y"])+' '+str(prediccion["width"])+' '+str(prediccion["height"])
                inference_info["annotations"].append(annotation)

                try:
                    y1 = 0 if int(prediccion["x"]) < 125 else prediccion["x"] - 125
                    y2 = img.shape[1] if int(prediccion["x"]) + 125 > img.shape[1] else prediccion["x"] + 125
                    x1 = 0 if int(prediccion["y"]) < 125 else prediccion["y"] - 125
                    x2 = img.shape[0] if int(prediccion["y"]) + 125 > img.shape[0] else prediccion["y"] + 125
                    
                    crop_img = img[int(x1):int(x2), int(y1):int(y2)]

                    mask = np.zeros([250,250,3],dtype=np.uint8)
                    w, h = crop_img.shape[:2]
                    mask[ 0:w, 0:h ] = crop_img
                    
                    inference_info["cropped_images"].append({ "img" : mask.tolist(), "intensity" : round(intensity,1), "class": prediccion["class"] })

                except ValueError:
                    pass    
                    
                inference_info["cropped_images"].sort(key=lambda x: x["intensity"], reverse=True)
                inference_info["max_intensity"] = inference_info["cropped_images"][0]["intensity"]
                
                arr_inferencias_positivas.append(inference_info)
                inferencias_positivas += 1
                
            inferencias_totales += 1

    except ValueError:
        return smart_prediction()
        pass


def mongo_connect():
    try:
        mongo_client = MongoClient("mongodb://ecmc:ecmc2011@10.0.2.2:27017/ecmc_ia",serverSelectionTimeoutMS=1)
        #mongo_client = MongoClient("mongodb://localhost:27017/ecmc_ia",serverSelectionTimeoutMS=1)
        mongo_client.server_info() # force connection on a request as the connect=True parameter of MongoClient seems to be useless here
        
        global db
        db = mongo_client["ecmc_ia"]
        print('Mongo Connection Succesfully')
    except ServerSelectionTimeoutError as err:
        print('Mongo Connection Fails')
        time.sleep(5)
        mongo_connect()
#Secuencia principal
imageHub = imagezmq.ImageHub()

#Lanzador
if __name__ == '__main__':
    mongo_connect()
    smart_prediction()
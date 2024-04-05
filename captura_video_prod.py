import cv2
from cv2 import VideoWriter
import numpy as np
import time
import imutils
import socket
from math import pi, sqrt
import logging
#import PySpin
import imagezmq
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import pathlib

from threading import Timer
from time import sleep

from pypylon import pylon

#Global vars
logger                = logging.getLogger(__name__)
interface_server      = socket.gethostname() #IP del entorno al que se envían los frames 
#classificator_server  = ('10.0.2.5') #IP del Tegra
classificator_server  = ('10.0.2.4') #IP del nano
sender                = imagezmq.ImageSender(connect_to="tcp://{}:5555".format(interface_server)) #Enviador de imágenes al entorno
sender2               = imagezmq.ImageSender(connect_to="tcp://{}:5555".format(classificator_server)) #Enviador de imágenes al python de clasificacion
dispName              = 'RF2' #socket.gethostname()
db                    = '' #Mongo Database
path                  = pathlib.Path(__file__).parent.absolute()
capture               = True #Flag para tomar capturas
tamaño_bola           = 1

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

def reset_counter():
    global capture
    global tamaño_bola

    capture = True

    tamaño_bola = float(db.presencia.find_one()["tamaño"])

def run():
    global path
    global tamaño_bola
    
    try:
        #logger.debug('Streaming')
        
        print(__doc__)

        #INCIAL VALUES
        lowThreshold = 0
        highThreshold = 255
        maxThreshold = 255
        apertureSizes = [3, 5, 7]
        maxapertureIndex = 2
        apertureIndex = 0
        blurAmount = 0
        maxBlurAmount = 20
        low_threshold=0
        high_threshold=255
        max_threshold=255
        
        camera_filters = str(path)+"/camera_filters.log" #Log que se modifica en el entorno
        ratio    = 1 #Radio escalar para las bolas
        fourcc   = cv2.VideoWriter_fourcc(*'XVID') #Formato para los videos
        
        out      = cv2.VideoWriter(str(path)+"/videos/", fourcc, 25.0, (1024,1280))
        
        grabando          = False
        error             = 'Sin_Defecto'
        balls_cont        = 0 #Contador de bolas
        capturas_cont     = 0 #Conteo de capturas        

        global db
        tamaño_bola       = float(db.presencia.find_one()["tamaño"])
        camera_config      = db.camera.find_one()
        frame_rate         = camera_config["frame_rate"]
        exposure_time      = camera_config["exposure_time"]

        cap  = cv2.VideoCapture('/home/vision-ia/Escritorio/moly/viodeo.avi')

        # Filtros de rango HSV para los frames
        l_h = 0
        l_s = 0
        l_v = 81

        u_h = 219
        u_s = 238
        u_v = 255

        l_b = np.array([l_h, l_s, l_v])
        u_b = np.array([u_h, u_s, u_v])

        rt   = RepeatedTimer(20, reset_counter) # it auto-starts, no need of rt.start()
        
        if socket.gethostname() == "10.0.2.2": #Produccion
            camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            camera.Open()
            camera.AcquisitionFrameRateEnable.SetValue(True)
            camera.AcquisitionFrameRateAbs.SetValue(frame_rate)
            camera.ExposureTimeAbs.SetValue(exposure_time)  
            camera.StartGrabbing(pylon.GrabStrategy_OneByOne)

            converter = pylon.ImageFormatConverter()

            # converting to opencv bgr format
            converter.OutputPixelFormat = pylon.PixelType_BGR8packed
            #converter.OutputPixelFormat = pylon.PixelType_BGR16packed
                
            converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned
            video_validator = camera.IsGrabbing()
        else:
            video_validator = True

        while video_validator:    
            try:
                if socket.gethostname() == "10.0.2.2": #Produccion
                    grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                    video_result = grabResult.GrabSucceeded()
                    img = grabResult.Array
                    img_conv = converter.Convert(grabResult)

                    frame_ori = frame = img_conv.GetArray() # or img.GetData().tobytes() for pushing into gstreamer buffers
                else:
                    try:
                        video_result = True
                        _, frame = cap.read()
                        
                        if frame is None:
                            cap = cv2.VideoCapture('/home/vision-ia/Escritorio/moly/video.avi')
                            _, frame = cap.read()
                    except:
                        print('NO hay ningun video de prueba')
                        exit
                        
                if video_result:
                    
                    w = int(frame.shape[1] / 2)
                    h = int(frame.shape[0] / 2)

                    frame = cv2.pyrDown(frame, dstsize=(w,h))
                    
                    #Filtro por color HSV
                    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    mask = cv2.inRange(hsv, l_b, u_b)
                    
                    res = cv2.bitwise_and(frame, frame, mask=mask)
                    frame_hsv= res

                    #cv2.imshow("Filtro hsv",final_imagen)
            
                    # Convert it to grayscale, blur it slightly
                    h, s, v1 = cv2.split(res)
                    gray=v1

                    #blurred = cv2.GaussianBlur(gray, (5, 5), 0)

                    # perform a series of erosions and dilations to remove
                    # any small blobs of noise from the thresholded image
                    gray = cv2.erode(gray, None, iterations=1)
                    gray = cv2.dilate(gray, None, iterations=1)
                    frame_ero_dil= gray

                    medianSrc = cv2.medianBlur(gray, 5)
                    thresh_mean = cv2.adaptiveThreshold(medianSrc, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,9,2)    

                    #Filtro Gaussiano - Canny
                    if (blurAmount > 0):
                        blurredSrc = cv2.GaussianBlur(gray, (2 * blurAmount + 1, 2 * blurAmount + 1), 0)
                    else:
                        blurredSrc = gray.copy()

                    #cv2.imshow("blurredSrc",blurredSrc)
                    frame_blurredSrc= blurredSrc

                    # Canny requires aperture size to be odd
                    apertureSize = apertureSizes[apertureIndex]

                    # Apply canny to detect the images
                    #blurredSrc = cv2.bilateralFilter(blurredSrc, 11, 17, 17)
                    edges = cv2.Canny(blurredSrc, lowThreshold, highThreshold, apertureSize = apertureSize)
                    #cv2.imshow("Canny",edges)

                    frame_edges= edges

                    #threshold_low_value  = cv2.getTrackbarPos("Threshold Binary Low", name_of_windows)
                    #threshold_high_value = cv2.getTrackbarPos("Threshold Binary High", name_of_windows)

                    thresh = cv2.threshold(edges, 0, 255, cv2.THRESH_BINARY)[1]
                    #cv2.imshow("thresh",thresh)
                    frame_thresh= thresh

                    # find contours in the thresholded imageq
                    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    #cnts = cv2.findContours(thresh.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                    #cnts = cv2.findContours(thresh.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                    cnts = imutils.grab_contours(cnts)
                    center = None


                    many_balls = frame.copy()
                    #cv2.imwrite(str(path)+'/capturas_many/Many_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', frame)

                    for i, c in enumerate(cnts):
                        #Calculo del Momemtum
                        M = cv2.moments(c)
                        
                        #Obtener radio minimo
                        ((x, y), radius) = cv2.minEnclosingCircle(c)

                        center = (int(x),int(y))
                        if (M["m00"] != 0): # and (radius>10) and (radius<50):
                            #Obtener centroides
                            cX = int(M["m10"] / M["m00"])
                            cY = int(M["m01"] / M["m00"])
                            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

                            #Area y perimetro real del objeto detectado
                            area = cv2.contourArea(c)
                            perimeter = cv2.arcLength(c,True)

                            #Area circulo del area minima
                            area_circulo= pi * radius ** 2

                            #Calcular diferencia porcentual entre una y otra
                            diferencia = (area_circulo-area)*100/area
                            
                            #print(str(tamaño_bola), str(area_circulo))
                            
                            area_validation_1    = tamaño_bola == 1.0 and (area_circulo > 700 and area_circulo < 2400)
                            area_validation_1_25 = tamaño_bola == 1.25 and (area_circulo > 1100 and area_circulo < 5000)
                            area_validation_1_5  = tamaño_bola == 1.5 and (area_circulo > 3000 and area_circulo < 5800)
                            area_validation_2    = tamaño_bola == 2.0 and (area_circulo > 5000 and area_circulo < 10200)
                            area_validation_2_5  = tamaño_bola == 2.5 and (area_circulo > 8000 and area_circulo < 17000)
                            
                            #print('Area: '+str(area_circulo))
                            if ((area_validation_1) or (area_validation_1_25) or (area_validation_1_5) or (area_validation_2) or (area_validation_2_5)):
                                
                                #cv2.imwrite(str(path)+'/capturas/Many_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', frame)
                                
                                # multiply the contour (x, y)-coordinates by the resize ratio,
                                c = c.astype("float")
                                c *= ratio
                                c = c.astype("int")

                                #Dibujar contorno real del objeto
                                #cv2.drawContours(frame, [c], -1, (0, 255, 0), 1)

                                # Dibujar circunferencia de radio igual al radio minimo. 
                                if radius < 40:
                                    aux_radius = int(radius - 7)
                                else:
                                    aux_radius = int(radius - 5)

                                frame_copy = frame.copy()

                                #cv2.circle(frame, (int(x), int(y)), int(aux_radius), (0, 255, 255), 1)
                                #cv2.circle(frame, center, 5, (0, 0, 255), -1)
                                
                                # Imprimir info de radio detectado
                                radius_ = ("Radio min: {0} px".format(round(radius,2)))
                                #cv2.putText(frame, radius_, (cX - 20, cY - 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                                # Imprimir info de radio detectado
                                area_circulo_ = ("Area: {0} px2".format(round(area_circulo,2)))
                                #cv2.putText(frame, area_circulo_, (cX - 80, cY - 90), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

                                # Imprimir info de radio detectado
                                area_ = ("Area Real: {0} px2".format(round(area,2)))
                                #cv2.putText(frame, area_, (cX - 80, cY - 75), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

                                # Imprimir info de radio detectado
                                diferencia_ = ("Diferencia: {0} %".format(round(diferencia,2)))
                                #cv2.putText(frame, diferencia_, (cX - 80, cY + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                                # Imprimir hora en el frame
                                #cv2.putText(frame, datetime.now().strftime('%H:%M:%S %d-%m-%Y'), (cX - 10, cY + 105), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

                                try:
                                    # Radio Circulo
                                    #cv2.putText(new_frame, bf_area_circulo, (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255),1)

                                    # Radio Real
                                    #cv2.putText(new_frame, bf_area, (40, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

                                    # Diferencia total
                                    #cv2.putText(new_frame, bf_diferencia, (115, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

                                    # Imprimir hora en el frame
                                    #cv2.putText(send_frame, datetime.now().strftime('%H:%M:%S %d-%m-%Y'), (145, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (255, 255, 255), 1)

                                    #print(new_frame.shape)
                                    #new_frame = new_frame.resize(new_frame, (300,300))
                                    
                                       
                                    

                                    send_frame = np.zeros((250,250,3), np.uint8)
                                    """
                                    global capture 
                                    #CAPTURA IMÁGENES
                                    if ((presencia['error'] != "") and (not grabando)): #Un operador seleccionó un defecto en el entorno
                                        error = presencia['error']
                                        grabando = True
                                        capturas_cont = 0
                                    
                                    if error == 'Sin_Defecto':
                                        if capture:
                                            cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                            capture = False
                                    else: #Toma capturas corrientes, limitadas por la variable capturas_por_minuto
                                        if capturas_cont == 1500: #Al alcanzar 1500 capturas, deja de tomarlas.
                                            grabando = False
                                            capturas_cont = 0
                                            error = 'Sin_Defecto'

                                    if grabando:
                                        capturas_cont += 1
                                        #cv2.imwrite(str(path)+'/capturas/'+error+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                        cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
        
                                    """
                                    error = ''
                                    flag = False

                                    global capture

                                    capture = False
                                    grabando = True
                                    if (area_validation_1):
                                        if ((int(y)-35 >  0) and (int(y)+35 < frame_copy.shape[0])):   
                                            if ((int(x)-35 >  0) and (int(x)+35 < frame_copy.shape[1])):
                                                new_frame = frame_copy[int(y)-35:int(y)+35, int(x)-35:int(x)+35]
                                                send_frame[70:140, 70:140] = new_frame
                                                #cv2.imwrite(str(path)+'/capturas/Sin_Defecto_0_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                """
                                                if grabando:
                                                    capturas_cont += 1
                                                    #cv2.imwrite(str(path)+'/capturas/'+error+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                                
                                                if capture:
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                                    capture = False
                                                """
                                                flag = True
                                                balls_cont += 1         

                                    if (area_validation_1_25):
                                        if ((int(y)-40 >  0) and (int(y)+40 < frame_copy.shape[0])):   
                                            if ((int(x)-40 >  0) and (int(x)+40 < frame_copy.shape[1])):
                                                new_frame = frame_copy[int(y)-40:int(y)+40, int(x)-40:int(x)+40]
                                                send_frame[60:140, 60:140] = new_frame
                                                #cv2.imwrite(str(path)+'/capturas/Sin_Defecto_0_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                """
                                                if grabando:
                                                    capturas_cont += 1
                                                    #cv2.imwrite(str(path)+'/capturas/'+error+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                                
                                                if capture:
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                                    capture = False
                                                """
                                                flag = True
                                                balls_cont += 1                                                  

                                    elif area_validation_1_5:
                                        if ((int(y)-45 >  0) and (int(y)+45 < frame_copy.shape[0])):   
                                            if ((int(x)-45 >  0) and (int(x)+45 < frame_copy.shape[1])):
                                                new_frame = frame_copy[int(y)-45:int(y)+45, int(x)-45:int(x)+45]
                                                send_frame[55:145, 55:145] = new_frame
                                                #cv2.imwrite(str(path)+'/capturas/Sin_Defecto_0_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                """
                                                if grabando:
                                                    capturas_cont += 1
                                                    #cv2.imwrite(str(path)+'/capturas/'+error+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                                """

                                                if capture:
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                                    capture = False
                                                
                                                flag = True
                                                balls_cont += 1
                                    
                                    elif area_validation_2:
                                        if ((int(y)-75 >  0) and (int(y)+75 < frame_copy.shape[0])):   
                                            if ((int(x)-75 >  0) and (int(x)+75 < frame_copy.shape[1])):
                                                new_frame = frame_copy[int(y)-75:int(y)+75, int(x)-75:int(x)+75]
                                                send_frame[50:200, 50:200] = new_frame
                                                #cv2.imwrite(str(path)+'/capturas/Sin_Defecto_0_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                """
                                                if grabando:
                                                    capturas_cont += 1
                                                    #cv2.imwrite(str(path)+'/capturas/'+error+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                                """

                                                if capture:
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                                    capture = False

                                                flag = True
                                                balls_cont += 1

                                    elif area_validation_2_5:
                                        if ((int(y)-100 >  0) and (int(y)+100 < frame_copy.shape[0])):   
                                            if ((int(x)-100 >  0) and (int(x)+100 < frame_copy.shape[1])):
                                                new_frame = frame_copy[int(y)-100:int(y)+100, int(x)-100:int(x)+100]
                                                send_frame[25:225, 25:225] = new_frame
                                                #cv2.imwrite(str(path)+'/capturas/Sin_Defecto_'+str(presencia["presencia"])+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                """
                                                if grabando:
                                                    capturas_cont += 1
                                                    #cv2.imwrite(str(path)+'/capturas/'+error+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', new_frame)
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_bals)
                                                """

                                                if capture:
                                                    cv2.imwrite(str(path)+'/capturas_many/Many_'+str(error)+'_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', many_balls)
                                                    capture = False
                                                
                                                flag = True
                                                balls_cont += 1                                            
                                    
                                    print(balls_cont)
                                    if balls_cont > 5 and socket.gethostname() == "10.0.2.2":
                                        if flag:
                                            h, s, v = cv2.split(new_frame)
                                            response3  = sender2.send_image_reqrep('{"dispName": "CALCULA", "tamaño_bola": '+str(tamaño_bola)+' }', frame_copy)
                                            print('*')
                                        balls_cont = 0
                                        

                                    elif balls_cont % 4 == 0:
                                        if np.any(send_frame):     
                                            cv2.putText(send_frame, 'Ultima captura', (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (255, 200, 100), 1)
                                            cv2.putText(send_frame, datetime.now().strftime('%H:%M:%S %d-%m-%Y'), (150, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (255, 255, 255), 1)
                                            
                                            response2 = sender.send_image_reqrep('{"dispName": "IMG", "tamaño_bola": '+str(tamaño_bola)+' }', send_frame)
                                            print('-')

                                except ValueError:
                                    pass    
                                  
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    cv2.putText(frame, 'RF2 ONLINE', (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.25, (0, 255, 0), 1)
                    
                    #cv2.imwrite(str(path)+'/capturas/Many_'+str(tamaño_bola)+'_'+str(time.strftime("%Y%m%d-%H%M%S"))+'.jpg', frame)

                    response= sender.send_image_reqrep('{"dispName": "'+str(dispName)+'"}', frame)
                    
                    #Tiempo espera final
                    cv2.waitKey(1)
                
                try:
                    grabResult.Release()
                except:
                    pass
            except:
                print('Sin Camaras')
                no_cameras = cv2.imread(str(path)+'/img/no_cameras.png')

                scale_percent = 75 # percent of original size
                width = int(no_cameras.shape[1] * scale_percent / 100)
                height = int(no_cameras.shape[0] * scale_percent / 125)
                dim = (width, height)
                no_cameras = cv2.resize(no_cameras, dim, interpolation = cv2.INTER_AREA)
                
                response= sender.send_image_reqrep('{"dispName": "'+str(dispName)+'"}', no_cameras)
                time.sleep(5)
                run()
 
        camera.Close()   
        
    except:
        print('Sin Camaras')
        no_cameras = cv2.imread(str(path)+'/img/no_cameras.png')

        scale_percent = 75 # percent of original size
        width = int(no_cameras.shape[1] * scale_percent / 100)
        height = int(no_cameras.shape[0] * scale_percent / 125)
        dim = (width, height)
        no_cameras = cv2.resize(no_cameras, dim, interpolation = cv2.INTER_AREA)
        
        response = sender.send_image_reqrep('{"dispName": "'+str(dispName)+'"}', no_cameras)
        
        time.sleep(5)
        run()
        pass

def mongo_connect():
    try:
        if socket.gethostname() == "10.0.2.2": # Produccion, requiere autenticación
            mongo_client = MongoClient("mongodb://ecmc:ecmc2011@10.0.2.2:27017/ecmc_ia",serverSelectionTimeoutMS=1)
        else:  # Local
            mongo_client = MongoClient("mongodb://localhost:27017/ecmc_ia",serverSelectionTimeoutMS=1)

        mongo_client.server_info() # force connection on a request as the connect=True parameter of MongoClient seems to be useless here
        
        global db
        db = mongo_client["ecmc_ia"]
        print('Mongo Connection Succesfully')
        
    except ServerSelectionTimeoutError as err:
        print('¡¡ Mongo Connection Fails !!')
        time.sleep(5)
        main()

def main():
    #Configuracion del sistema de cámaras
    logging.basicConfig(level=logging.DEBUG)
    #system = PySpin.System.GetInstance()
    #version = system.GetLibraryVersion()
    
    #Listado de cámaras e instanciación    

    #Coneccion con servidor de Mongo
    mongo_connect()

    try:
        run() #Iniciación del stream de la cámara
        
    except: 
        run()
        pass
    finally:
        pass
    
if __name__ == '__main__':
    main()

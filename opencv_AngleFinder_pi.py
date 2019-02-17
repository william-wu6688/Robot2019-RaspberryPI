import cv2
from networktables import *
from grip import TapeRecognitionCode
import threading
from ctypes import *
import sys
from hatchDetect import isHatch

def extra_processing(pipeline):
    """
    Performs extra processing on the pipeline's outputs and publishes data to NetworkTables.
    :param pipeline: the pipeline that just processed an image
    :return: None
    """
    center_x_positions = []
    center_y_positions = []
    widths = []
    heights = []
    angle = 0
    frame_width_midpt = 80
    distanceFromTarget = 0
    # Find the bounding boxes of the contours to get x, y, width, and height
    for contour in pipeline.filter_contours_output:
        x, y, w, h = cv2.boundingRect(contour)
        center_x_positions.append(x + w / 2)  # X and Y are coordinates of the top-left corner of the bounding box
        center_y_positions.append(y + h / 2)
        widths.append(w)
        heights.append(h)

    #Only calculates angle if 2 boxes are found

    if len(heights) == 2:

        if widths[0] > widths[1]:
            biggerWidth = widths[0]
        else:
            biggerWidth = widths[1]

        midpoint = ((center_x_positions[0] + center_x_positions[1])/2.0)
        distance = abs(midpoint - (frame_width_midpt * pipeline._TapeRecognitionCode__cv_resize_fx))

        #Distance from the reflective tape in inches
        if  abs(widths[0] - widths[1]) <= (0.3 * biggerWidth):
            averageWidth = (widths[0] + widths[1])/2.0
            distanceFromTarget = 12.0 * (4.6 - ((2.0/15.0) * averageWidth))
        else:
            distanceFromTarget = sys.maxint

        angle = 35 * distance / (frame_width_midpt * pipeline._TapeRecognitionCode__cv_resize_fx)

        if midpoint < (frame_width_midpt * pipeline._TapeRecognitionCode__cv_resize_fx):
            angle = angle * -1
        have_angle = True
    else:
        distanceFromTarget = sys.maxint
        angle = sys.maxint
        have_angle = False
    
    return angle, have_angle, distanceFromTarget 

def main():

    turning_angle = 0 
    haveAngle = False
    distance_from_target = 0
    frame_print = 1
    firing_range_hatch = False
    firing_range_cargo = False
    cargoRange = 24
    hatchRange = 24
    IsHatch = False

    cond = threading.Condition()
    notified = [False]

    def connectionListener(connected, info):
        with cond:
            notified[0] = True
            cond.notify()


    #Initializing and connecting to network tables
    NetworkTables.initialize(server='10.4.67.23')
    NetworkTables.addConnectionListener(connectionListener, immediateNotify=True)

    with cond:
        if not notified[0]:
            cond.wait()

    table = NetworkTables.getTable('vision')
    
    #Creating video capture
    while True:
        try:
            cap = cv2.VideoCapture('http://localhost:1181/stream.mjpg')
            break
        except:
            pass

   

    frame_number = 0
    pipeline = TapeRecognitionCode()

    cap.open('http://localhost:1181/stream.mjpg')


    #Putting angle and haveAngle to network tables is camera is opened and it gets a frame
    while cap.isOpened():
        
        frame_number = frame_number + 1
        have_frame, frame = cap.read()
        if have_frame:
            
            pipeline.process(frame)
            if pipeline is not None:
                turning_angle, haveAngle, distance_from_target = extra_processing(pipeline)

                table.putBoolean('haveAngle', haveAngle)
                table.putNumber('angle', turning_angle)

                if distance_from_target < hatchRange:
                    firing_range_hatch = True
                    table.putBoolean('FiringRange_Hatch', firing_range_hatch)
                else:
                    firing_range_hatch = False
                    table.putBoolean('FiringRange_Hatch', firing_range_hatch)

                if distance_from_target < cargoRange:
                    firing_range_cargo = True
                    table.putBoolean('FiringRange_Cargo', firing_range_cargo)
                else:
                    firing_range_cargo = False
                    table.putBoolean('FiringRange_Cargo', firing_range_cargo)

        if frame_number%60 == 0:
            IsHatch = isHatch(frame)
            print (IsHatch)

        table.putBoolean('hatch', IsHatch)

    cap.release()

if __name__ == '__main__':
    main()
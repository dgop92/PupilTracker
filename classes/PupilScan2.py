import dlib
import cv2
import os
import pickle
import numpy as np

# This class is in charge of analyzing the frame

class PupilScan:

    def __init__(self):

        self.frame = None
        self.face = None
        self.gray = None
        self.landmarks = None

        self.center_value = None
        self.new_frame = None
        self.eye_ratio = None

        self.pos = ""
        self.blink = "False"

        # Variables used to know if the eye is closed for a specific time
        self.blink_time = 0
        self.scan_blink = True
        self.blink_errors = 0

        # Get Frontal Face
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("ShapePredictor/shape_predictor_68_face_landmarks.dat")

        parent = os.path.abspath(os.path.join('frames', os.pardir))
        self.data_settings = pickle.loads(open(parent + "/data/settings.pickle", "rb").read())

        self.thresh_value_c = self.data_settings['thresh_value']

    def refresh_data(self):

        parent = os.path.abspath(os.path.join('frames', os.pardir))
        self.data_settings = pickle.loads(open(parent + "/data/settings.pickle", "rb").read())

    def get_numpy_of_left_eye(self):

        p1 = [self.landmarks.part(36).x, self.landmarks.part(36).y]
        p2 = [self.landmarks.part(37).x, self.landmarks.part(37).y]
        p3 = [self.landmarks.part(38).x, self.landmarks.part(38).y]
        p4 = [self.landmarks.part(39).x, self.landmarks.part(39).y]
        p5 = [self.landmarks.part(40).x, self.landmarks.part(40).y]
        p6 = [self.landmarks.part(41).x, self.landmarks.part(41).y]

        return np.asarray([p1, p2, p3, p4, p5, p6])

    def get_numpy_of_right_eye(self):

        p1 = [self.landmarks.part(42).x, self.landmarks.part(42).y]
        p2 = [self.landmarks.part(43).x, self.landmarks.part(43).y]
        p3 = [self.landmarks.part(44).x, self.landmarks.part(44).y]
        p4 = [self.landmarks.part(45).x, self.landmarks.part(45).y]
        p5 = [self.landmarks.part(46).x, self.landmarks.part(46).y]
        p6 = [self.landmarks.part(47).x, self.landmarks.part(47).y]

        return np.asarray([p1, p2, p3, p4, p5, p6])

    def analyze_frame(self):
        self.center_value = (100, 50)
        self.new_frame = self.frame.copy()
        self.new_frame[:, :, :] = 0

        # Get the specific points to create a rectangular roi of the eye
        # Get the ratio of the specific eye

        self.landmarks = self.predictor(self.gray, self.face)
        if self.data_settings['eye_value'] == 0:
            left_side = (self.landmarks.part(36).x, self.landmarks.part(36).y)
            right_side = (self.landmarks.part(39).x, self.landmarks.part(39).y)
            top_side = mid_point(self.landmarks.part(37), self.landmarks.part(38))
            bottom_side = mid_point(self.landmarks.part(41), self.landmarks.part(40))
            self.eye_ratio = own_eye_distance(self.get_numpy_of_left_eye())
        else:
            left_side = (self.landmarks.part(42).x, self.landmarks.part(42).y)
            right_side = (self.landmarks.part(45).x, self.landmarks.part(45).y)
            top_side = mid_point(self.landmarks.part(43), self.landmarks.part(44))
            bottom_side = mid_point(self.landmarks.part(47), self.landmarks.part(46))
            self.eye_ratio = own_eye_distance(self.get_numpy_of_right_eye())

        # Create the roi using the previously points

        eye_roi = self.frame[top_side[1] - 10:bottom_side[1] + 10, left_side[0] - 10:right_side[0] + 10].copy()
        roi_resize = cv2.resize(eye_roi, (200, 100))

        gray_eye = cv2.cvtColor(roi_resize, cv2.COLOR_BGR2GRAY)

        ret, mask = cv2.threshold(gray_eye, self.thresh_value_c, 255, cv2.THRESH_BINARY_INV)

        cv2.imshow('mask', mask)

        # Create a square by searching the areas with the darkest color. it depends on the thresh given

        try:
            contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contour_sizes = [(cv2.contourArea(contour), contour) for contour in contours]
            biggest_contour = max(contour_sizes, key=lambda x: x[0])[1]
            x, y, w, h = cv2.boundingRect(biggest_contour)

            # cv2.rectangle(roi_resize, (x, y), (x + w, y + h), (0, 255, 0), 2)
            self.center_value = (x + (int(w / 2)), y + (int(h / 2)))  # The center of the square
            cv2.circle(roi_resize, self.center_value, 2, (12, 150, 100), 2)

        except:

            self.center_value = (0, 0)

        self.new_frame[100:200, 200:400] = roi_resize

    def values_to_words(self):

        # According to the positions it returns a a command. we have to put others conditionals to avoid errors

        if self.center_value[0] == 0:
            self.pos = "ERROR"
        elif self.center_value[0] <= 75 and self.eye_ratio >= self.data_settings['eye_ratio_value'] + 1 and self.blink_time <= 1:
            self.pos = "Left"
        elif self.center_value[0] <= 118 and self.eye_ratio >= self.data_settings['eye_ratio_value'] + 1 and self.blink_time <= 1:
            self.pos = "Neutro"
        elif self.center_value[0] <= 125 and self.eye_ratio >= self.data_settings['eye_ratio_value'] + 1 and self.blink_time <= 1:
            self.pos = "Slight Right"
        elif self.center_value[0] > 125 and self.eye_ratio >= self.data_settings['eye_ratio_value'] + 1 and self.blink_time <= 1:
            self.pos = "Strong Right"
        else:
            self.pos = "ERROR"

        # eye_ratio give us the average distance between the top and bottom point of the eye
        # we create a algorithm to detect how much time the eye has been closed. we have to be aware of slight-errors
        # that the eye_ratio could give us to avoid stopping the count of the eye time

        if self.scan_blink:

            self.blink = "False"

            if self.eye_ratio <= self.data_settings['eye_ratio_value']:
                self.blink_time += 1
            else:
                self.blink_errors += 1

            if self.blink_errors == 7:
                self.scan_blink = False
                self.blink_errors = 0

            if self.blink_time == self.data_settings['bk_time_eye']:
                self.blink = "True"
                self.scan_blink = False
                print("eye closed!")
                self.blink_errors = 0

            print(self.blink_time,"----",self.blink_errors,"--------","-")
        else:
            self.blink_time = 0
            self.scan_blink = True

        print(self.eye_ratio)

    def scanning(self, frame):

        self.frame = frame
        self.gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector(self.gray)

        if len(faces) != 0:
            self.face = faces[0]  # get the first face of a list of frontal faces in the frame
            self.analyze_frame()
            self.values_to_words()

            return self.new_frame, self.eye_ratio, self.blink, self.pos, self.center_value
        else:
            return self.frame, 0, False, "NoFace", (0, 0)

    def change_thresh_type(self, thresh_valu):
        self.thresh_value_c = thresh_valu


def mid_point(p1, p2):
    return int((p1.x + p2.x) / 2), int((p1.y + p2.y) / 2)


def own_eye_distance(eye):
    dist_p26 = np.linalg.norm(eye[1] - eye[5])
    dist_p35 = np.linalg.norm(eye[2] - eye[4])

    average = (dist_p26 + dist_p35) / 2

    return average
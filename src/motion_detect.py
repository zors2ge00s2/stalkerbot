#!/usr/bin/env python

import rospy
import math
import os
import yaml
import tf2_ros
import copy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, Time, Float32

from collections import deque
from statistics import mean

class Detect():

    def _vel_cb(self, msg):
        self._twist = msg  
    
    def _interval_cb(self, msg):
        self._interval = msg

    def _update_transform(self):
        tf = self._tfBuffer.lookup_transform(self._FRAME_ROBOT, self._FRAME_TARGET, rospy.Time())
        if self._current_location is not None:
            self._last_location = self._current_location
        self._current_location = tf

        if self._last_location is not None:
            _dist = self._distance()
            _threshold = \
                self._DETECTION_DISTANCE_TRIGGER_BASE * (1 + \
                    1.5 * abs(self._twist.linear.x) / self._MAXIMUM_LINEAR_VELOCITY + \
                    2 * abs(self._twist.angular.x) / self._MAXIMUM_ROTATIONAL_VELOCITY) * \
                    (self._last_location.transform.translation.x ** 2)
            if _dist != 0:
                _ratio = _dist / _threshold
                self._results.append(_ratio)
        
    def _distance(self):
        '''compute 3D distance between two points'''
        x1, x2 = self._last_location.transform.translation.x, self._current_location.transform.translation.x
        y1, y2 = self._last_location.transform.translation.y, self._current_location.transform.translation.y
        z1, z2 = self._last_location.transform.translation.z, self._current_location.transform.translation.z
        distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)
        return distance

    def _get_moving_average(self):
        temp = copy.copy(self._results)
        # temp.remove(max(temp))
        # temp.remove(min(temp))
        _mean = mean(temp)
        #Rostopic echo to debug
        print _mean * 100
        self._motion_debugger_publisher.publish(_mean * 100)
        return _mean

    def __init__(self):
        '''class variables'''
        self._interval = None
        self._last_location = None
        self._current_location = None
        self._linger = 0
        self._twist = Twist()

        self._tfBuffer = tf2_ros.Buffer()
        self._listener = tf2_ros.TransformListener(self._tfBuffer)
        motion_publisher = rospy.Publisher('/stalkerbot/motion', Bool, queue_size = 1)
        self._motion_debugger_publisher = rospy.Publisher('/stalkerbot/motion_debug', Float32, queue_size = 1)
        vel_subscriber = rospy.Subscriber('cmd_vel', Twist, self._vel_cb, queue_size=1)
        interval_subscriber = rospy.Subscriber('/stalkerbot/fiducial/interval', Time, self._interval_cb, queue_size=1)

        '''class constants'''
        self._DETECTION_DISTANCE_TRIGGER_BASE = 0
        self._MAXIMUM_LINEAR_VELOCITY = 0
        self._MAXIMUM_ROTATIONAL_VELOCITY = 0
        self._FREQUENCY = 0
        self._LINGER_MAXIMUM = 0
        self._DEQUE_SIZE = 0
        self._FRAME_ROBOT = ''
        self._FRAME_TARGET = ''
        self._MOTION_DETECT_BUFFER_SEC = 0

        with open(os.path.dirname(__file__) + '/../config.yaml','r') as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
            self._DETECTION_DISTANCE_TRIGGER_BASE = config['core']['distance']['detection']['trigger_base']
            self._FREQUENCY = config['core']['frequency']['motion_detect']
            self._LINGER_MAXIMUM = config['core']['frequency']['motion_detect_linger']
            self._DEQUE_SIZE = config['core']['size']['detection_deque']
            self._MAXIMUM_LINEAR_VELOCITY = config['core']['velocity']['linear']['maximum']
            self._MAXIMUM_ROTATIONAL_VELOCITY = config['core']['velocity']['rotational']['maximum']
            self._FRAME_ROBOT = config['tf']['frame_name']['robot']
            self._FRAME_TARGET = config['tf']['frame_name']['target']
            self._MOTION_DETECT_BUFFER_SEC = config['core']['buffer']['motion_detect']['sec']

        '''create a deque as part of the moving average algorithm
        in order to minimize the effect of sensor noise'''
        self._results = deque([], maxlen=self._DEQUE_SIZE)
        self._rate = rospy.Rate(self._FREQUENCY)
        while not rospy.is_shutdown():

            try:
                self._update_transform()
            except (tf2_ros.LookupException, tf2_ros.ConnectivityException,tf2_ros.ExtrapolationException):
                motion_publisher.publish(False)
                self._rate.sleep()
                continue

            if self._interval is None or self._interval.data.secs >= self._MOTION_DETECT_BUFFER_SEC:
                motion_publisher.publish(False)
                self._results.clear()
                self._rate.sleep()
                continue

            elif len(self._results) < self._DEQUE_SIZE:
                motion_publisher.publish(False)
                self._rate.sleep()
                continue
            
            detected = False
            _moving_average = self._get_moving_average()

            if _moving_average > 1:
                detected = True

            if detected == True:
                self._linger = self._LINGER_MAXIMUM
                motion_publisher.publish(True)
            elif detected == False and self._linger == 0:
                motion_publisher.publish(False)
            else:
                self._linger = self._linger - 1
                motion_publisher.publish(True)
            self._rate.sleep()

if __name__ == '__main__':
    rospy.init_node('motion_detect')
    try:
        detect = Detect()
    except rospy.ROSInterruptException:  pass
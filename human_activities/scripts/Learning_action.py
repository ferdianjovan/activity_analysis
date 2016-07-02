#! /usr/bin/env python

import sys
import rospy
import actionlib
from learn_activities import Offline_ActivityLearning
from human_activities.msg import LearningAction, LearningResult

class Learning_server(object):
    def __init__(self):

        # Start server
        rospy.loginfo("Learning Human ACtivites action server")
        self._as = actionlib.SimpleActionServer("LearningHumanActivities", LearningHumanActivitiesAction,
            execute_cb=self.execute, auto_start=False)
        self._as.start()


    def execute(self, goal):
        rerun = 1
        parallel = 0

        while not self._as.is_preempt_requested():
            o = Offline_ActivityLearning(rerun_all=rerun)

            """get SOMA2 Objects""""
            ol.get_soma_objects()

            """load skeleton detections over all frames"""
            ol.get_events()

            """encode all the observations using QSRs"""
            ol.encode_qsrs(parallel)

            """create histograms with global code book"""
            ol.make_temp_histograms_sequentially()

            o.make_term_doc_matrix()

            """create tf-idf and LSA classes"""
            ol.learn()


        self._as.set_succeeded(LearningResult())


if __name__ == "__main__":
    rospy.init_node('LearningHumanActivities_server')

    Learning_server()
    rospy.spin()

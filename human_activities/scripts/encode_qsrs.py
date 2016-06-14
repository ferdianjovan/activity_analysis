#!/usr/bin/env python
__author__ = 'p_duckworth'
import os, sys, csv
import time
import cPickle as pickle
import numpy as np
import multiprocessing as mp
from create_events import *

from qsrlib.qsrlib import QSRlib, QSRlib_Request_Message
from qsrlib_io.world_qsr_trace import World_QSR_Trace
from qsrlib_utils.utils import merge_world_qsr_traces
from qsrlib_qstag.qstag import Activity_Graph
from qsrlib_qstag.utils import *


def get_map_frame_qsrs(file, world_trace, dynamic_args):

    qsrs_for = [('robot', 'torso')]
    dynamic_args['qtcbs'] = {"qsrs_for": qsrs_for, "quantisation_factor": 0.0, "validate": False, "no_collapse": True}
    dynamic_args["qstag"] = {"params": {"min_rows": 1, "max_rows": 1, "max_eps": 3}}

    qsrlib = QSRlib()
    req = QSRlib_Request_Message(which_qsr="qtcbs", input_data=world_trace, dynamic_args=dynamic_args)
    qsr_map_frame = qsrlib.request_qsrs(req_msg=req)
    print "    ", file, "episodes = "
    for i in qsr_map_frame.qstag.episodes:
        print i
    return qsr_map_frame


def get_object_frame_qsrs(file, world_trace, objects, joint_types, dynamic_args):

    qsrs_for=[]
    for ob in objects:
        qsrs_for.append((str(ob), 'left_hand'))
        qsrs_for.append((str(ob), 'right_hand'))
        qsrs_for.append((str(ob), 'torso'))

    dynamic_args['argd'] = {"qsrs_for": qsrs_for, "qsr_relations_and_values": {'Touch': 0.25, 'Near': 0.5,  'Away': 1.0, 'Ignore': 10}}
    # dynamic_args['argd'] = {"qsrs_for": qsrs_for, "qsr_relations_and_values": {'Touch': 0.2, 'Ignore': 10}}
    dynamic_args['qtcbs'] = {"qsrs_for": qsrs_for, "quantisation_factor": 0.01, "validate": False, "no_collapse": True}
    dynamic_args["qstag"] = {"object_types": joint_types, "params": {"min_rows": 1, "max_rows": 2, "max_eps": 3}}
    # dynamic_args["qstag"] = {"object_types": joint_types, "params": {"min_rows": 1, "max_rows": 1, "max_eps": 3}}

    qsrlib = QSRlib()
    req = QSRlib_Request_Message(which_qsr=["argd", "qtcbs"], input_data=world_trace, dynamic_args=dynamic_args)
    # req = QSRlib_Request_Message(which_qsr="argd", input_data=world_trace, dynamic_args=dynamic_args)
    qsr_object_frame = qsrlib.request_qsrs(req_msg=req)

    # for i in qsr_object_frame.qstag.episodes:
    #     print i
    return qsr_object_frame


def get_joint_frame_qsrs(file, world_trace, joint_types, dynamic_args):

    qsrs_for = [('head', 'torso', ob) if ob not in ['head', 'torso'] and ob != 'head-torso' else () for ob in joint_types.keys()]
    dynamic_args['tpcc'] = {"qsrs_for": qsrs_for}
    dynamic_args["qstag"] = {"object_types": joint_types, "params": {"min_rows": 1, "max_rows": 1, "max_eps": 3}}

    qsrlib = QSRlib()
    req = QSRlib_Request_Message(which_qsr="tpcc", input_data=world_trace, dynamic_args=dynamic_args)
    qsr_joints_frame = qsrlib.request_qsrs(req_msg=req)

    # for i in qsr_joints_frame.qstag.episodes:
    #     print i
    return qsr_joints_frame



def worker_qsrs(chunk):
    (file, directory) = chunk
    e = load_e(directory, file)

    # joint_types = {'head' : 'head', 'neck' : 'neck', 'torso': 'torso','left_foot' : 'foot', 'right_foot' : 'foot',
    #  'left_shoulder' : 'shoulder', 'right_shoulder' : 'shoulder', 'left_hand' : 'hand', 'right_hand' : 'hand',
    #  'left_knee' : 'knee', 'right_knee': 'knee',  'right_elbow' : 'elbow', 'left_elbow' : 'elbow',  'right_hip' : 'hip', 'left_hip': 'hip'}
    # all_joints = ['head', 'neck', 'torso', 'left_foot', 'right_foot', 'left_shoulder', 'right_shoulder', 'left_hand', 'right_hand',
    # 'left_knee', 'right_knee',  'right_elbow', 'left_elbow',  'right_hip', 'left_hip']

    dynamic_args = {}
    dynamic_args['filters'] = {"median_filter": {"window": 10}}

    # # Robot - Person QTC Features
    # e.qsr_map_frame = get_map_frame_qsrs(file, e.map_world, dynamic_args)

    #todo: experiment if head-torso is better than neck-torso :)

    joint_types = {'head': 'head', 'torso': 'torso', 'left_hand': 'hand', 'right_hand': 'hand', 'left_knee': 'knee', 'right_knee': 'knee',
                   'left_shoulder': 'shoulder', 'right_shoulder': 'shoulder', 'head-torso': 'tpcc-plane'}

    # joint_types = {'head': 'head', 'torso': 'torso', 'left_hand': 'hand', 'right_hand': 'hand',  'head-torso': 'tpcc-plane'}

    joint_types_plus_objects = joint_types.copy()
    soma_objects = create_soma_objects(e.region).keys()
    for object in soma_objects:
        generic_object = "_".join(object.split("_")[:-1])
        joint_types_plus_objects[object] = generic_object

    # # Key joints - Object
    e.qsr_object_frame = get_object_frame_qsrs(file, e.map_world, soma_objects, joint_types_plus_objects, dynamic_args)

    # # Person Joints TPCC Features
    e.qsr_joint_frame = get_joint_frame_qsrs(file, e.camera_world, joint_types, dynamic_args)

    save_event(e, "QSR_Worlds")


def call_qsrlib(path, dirs):

    for dir_ in dirs:
        list_of_events = []
        directory = os.path.join(path, dir_)
        for i in sorted(os.listdir(directory)):
            # if "_".join(i.split("_")[:-3]) in ['making_tea', 'washing_up', 'take_paper_towel', 'use_water_cooler', 'openning_double_doors', 'take_from_fridge']: continue
            if "_".join(i.split("_")[:-3]) in ['making_tea']: continue
            # if "making_tea" in i: continue
            list_of_events.append((i, directory))

        num_procs = mp.cpu_count()
        pool = mp.Pool(num_procs)
        chunk_size = int(np.ceil(len(os.listdir(directory))/float(num_procs)))
        pool.map(worker_qsrs, list_of_events, chunk_size)
        pool.close()
        pool.join()

        # for cnt, i in enumerate(list_of_events):
        #     print i
        #     worker_qsrs(i)

if __name__ == "__main__":
    """	Read events files,
    call QSRLib with parameters
    create QSR World Trace
    save event with QSR World Trace
    """

    ##DEFAULTS:
    path = '/home/' + getpass.getuser() + '/Datasets/Lucie_skeletons/Events'
    dirs = [f for f in os.listdir(path)]

    # dirs = [ '2016-04-05_ki', '2016-04-11_vi', '2016-04-08_vi', '2016-04-07_vi', '2016-04-05_me', '2016-04-06_ki']
    call_qsrlib(path, dirs)

# -*- coding: utf-8 -*-
"""
Created on Tue Jun  9 11:11:12 2020

@author: eliot

v14 :
    - goal to add a feature to destroy unwanted rows
    - new "end of simulation criterion" --> we re-evaluate the InterYdist. If
    there is no evolution in the number of RALs after it, we stop the simulation.

v15 :
    - Add the exploration behaviour to cover the edges of the rows and make up
    for the bad predictions of the FT in this area. It is basically the extensive 
    approach but only on hte edges.

v16 :
    - Extended fusing condition to the case where to RALs are into each others
    scanning zones
    - p value for Row analysis changed from 0.05 to 0.0001

v17 :
    -Implement a growing algorithm more efficient for the plant agents.
    -Implement a way to measure the surface of the white surfaces inside the 
    plant agent's scanning zone.

v18 :
    -new agent plant growing policy Square based. Every borders moves the same way
    -cleaning MAS_Simulation_Class

v19 :
    - new agent plant growing policy. individual based. RAs can move independently

v20 :
    - adaptations to the new input format of the labelling files generated with
    Unity Perception
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import time
import json
from sklearn.cluster import KMeans
from scipy.stats import ttest_ind

os.chdir("../Utility")
import general_IO as gIO

# =============================================================================
# Utility Functions
# =============================================================================

def rotation_matrix(_theta):
    """
    Counter clock wise rotation matrix
    """
    return np.array([[np.cos(_theta), -np.sin(_theta)],
                     [np.sin(_theta),  np.cos(_theta)]])

def rotate_coord(_p, _pivot, _R):
    """
    gives the rotated coordinates of the point _p relatively to the _pivot point
    based on the rotation matrix _R.
    _p, _pivot and _R must be numpy arrays
    """
    _r_new_point = np.dot(_R, _p - _pivot) + _pivot
    
    return _r_new_point

# =============================================================================
# Agents Definition
# =============================================================================
class ReactiveAgent(object):
    """
    Agents pixels
    
    _RAL_x (int):
        leader column index in the image array
    _RAL_y (int):
        leader line index in the image array
    _local_x (int):
        column index relatively to the RAL
    _local_y (int):
        line index relatively to the RAL
    _img_array (numpy.array):
        array containing the image on which the Multi Agent System is working
    """
    
    def __init__(self,
                 _RAL_x, _RAL_y,
                 _local_x, _local_y,
                 _img_array):
        
        
        self.Fixed = False
        self.Set_Local_coords(_local_x, _local_y)
        
        self.outside_frame = False
        
        self.img_array = _img_array
        
        self.decision = False
        
        self.Move_Based_On_RAL(_RAL_x, _RAL_y)
        
    
    def Otsu_decision(self):
        """
        Returns True if the pixel where the RA is present is white
        """
        self.Is_Inside_Image_Frame()
        
        if (self.outside_frame):
            self.decision = False
        else:
            self.decision = self.img_array[self.global_y, self.global_x][0] > 220
        
        return self.decision
    
    def Set_Local_coords(self, _x, _y):
        """
        Sets local_x and local_y
        """
        if (not self.Fixed):
            self.local_x = _x
            self.local_y = _y
    
    def Set_Global_Coord(self, _x, _y):
        """
        Sets global_x and global_y
        """
        if (not self.Fixed):
            self.global_x = _x
            self.global_y = _y
    
    def Update_Global_coords(self, _RAL_x, _RAL_y):
        """
        Update global position based on local and RAL positions
        """
        self.Set_Global_Coord(_RAL_x + self.local_x, _RAL_y + self.local_y)
    
    def Update_All_coords(self, _dir_x, _dir_y):
        """
        Update both local and global coordinates by applying the modificators
        _dir_x and _dir_y.
        _dir_x and _dir_y are the coordinates of the new point relatively to
        the current coordinates.
        """
        self.Set_Local_coords(self.local_x + _dir_x, self.local_y +_dir_y)
        self.Set_Global_Coord(self.global_x + _dir_x, self.global_y + _dir_y)
    
    def Move_Based_On_RAL(self, _RAL_x, _RAL_y):
        """
        Update the position of the RAL based on the order given by the AD (agent
        director).
        _ADO_x (int):
            X coordinate of the target point (column of the image array)
        
        _ADO_y (int):
            Y coordinate of the target point (line of the image array)
        """
        self.Update_Global_coords(_RAL_x, _RAL_y)
        
        self.Is_Inside_Image_Frame()
        
    def Is_Inside_Image_Frame(self):
        
        if (self.global_x < 0 or
            self.global_x >= self.img_array.shape[1] or
            self.global_y < 0 or
            self.global_y >= self.img_array.shape[0]):
            
            self.outside_frame = True
            
        else:
            self.outside_frame = False
    
    def Explore_Pixel(self, _x, _y):
        """
        Returns True is the pixel is white.
        Returns False if the pixel is black or outside of the image frame
        """
        
        _activity = False
        if (0<= _y <self.img_array.shape[0] and
            0<= _x <self.img_array.shape[1]):
            
            if (self.img_array[_y, _x][0] > 220):
                _activity = True
                
        return _activity
    
    def Exploration_Report(self, _x_dir, _y_dir,
                           _exploration_factor, _shrinking_factor):
        """
        (_x_dir, _y_dir) gives the direction of exploration
        """
        
        _exploration_score = 0
        if (not self.outside_frame):
            for _inc in range (1, _exploration_factor+1):
                x_dir_global = self.global_x + _inc * _x_dir
                y_dir_global = self.global_y + _inc * _y_dir
            
                if (0<= y_dir_global < self.img_array.shape[0] and
                    0<= x_dir_global < self.img_array.shape[1]):
                    
                    if (self.img_array[y_dir_global, x_dir_global][0] > 220):
                        _exploration_score += 1
                        
        _score = 0
        if (_exploration_score > 0):
            _score = _exploration_score
        elif _exploration_score == 0:
            _shrinking_score = 0
            for _inc in range (-_shrinking_factor, 0):
                x_dir_global = self.global_x + _inc * _x_dir
                y_dir_global = self.global_y + _inc * _y_dir
            
                if (0<= y_dir_global < self.img_array.shape[0] and
                    0<= x_dir_global < self.img_array.shape[1]):
                    
                    if (self.img_array[y_dir_global, x_dir_global][0] < 220):
                        _shrinking_score += 1
            _score = -_shrinking_score
        
        return _score

class ReactiveAgent_Leader(object):
    """
    Agent Plante
    
    _x (int):
        column index in the image array
    _y (int):
        lign index in the image array
    _img_array (numpy.array):
        array containing the image on which the Multi Agent System is working
    _group_size (int, optional with default value = 50):
        distance to the farthest layer of reactive agents from the RAL
    
    _group_step (int, optional with default value = 5):
        distance between two consecutive reactive agents
    
    _field_offset (list size 2, optional with default value [0, 0]):
        the offset to apply to all the positioned agents of the simulation to
        be coherent at the field level.
    
    """
    def __init__(self, _x, _y, _img_array, _group_size = 50, _group_step = 5,
                 _field_offset = [0,0]):
        
# =============================================================================
#         print()
#         print("Initializing Reactive Agent Leader at position [{0},{1}]...".format(_x, _y), end = " ")
# =============================================================================
        
        self.x = int(_x)
        self.y = int(_y)
        self.img_array = _img_array
        self.group_size = _group_size
        self.group_step = _group_step
        self.correct_RAL_position()
        self.nb_RAs = 0
        self.nb_RAs_card = [0,0,0,0]
        
        self.nb_contiguous_white_pixel = 0
        self.white_contigous_surface = 0
        
        self.field_offset = _field_offset
        
        self.active_RA_Point = np.array([self.x, self.y])
        self.movement_vector = np.zeros(2)
        
        self.recorded_positions = [[self.x, self.y]]
        self.field_recorded_positions = [[self.x + int(self.field_offset[0]),
                                          self.y + int(self.field_offset[1])]]
        
        self.used_as_filling_bound = False
        
# =============================================================================
#         print("Done")
#         print("Initializing the Reactive Agents under the RAL supervision...", end = " ")
# =============================================================================
        self.Borders_Distance = [self.group_size,
                                 -self.group_size,
                                 self.group_size,
                                 -self.group_size]
        self.Fixed = False
        self.nb_RAs_Fixed = 0
        self.With_Neighbour_Overlap = [False, False, False, False]
        self.exploration_factor = 4
        self.shrinking_factor = 2
        
        self.RAs_square_init()
        #self.RAs_border_init()
        
        self.Get_RAs_Otsu_Prop()
        self.recorded_Decision_Score = [self.decision_score]
        
# =============================================================================
#         print("Done")
# =============================================================================
    
    def correct_RAL_position(self):
        """
        adapt the self.x and self.y values (position of the RAL on the image)
        to avoid the instanciation of RAs outside the frame of the image
        """
        if (self.x-self.group_size < 0):
            self.x = self.group_size
            
        if (self.y-self.group_size < 0):
            self.y = self.group_size
            
        if (self.x+self.group_size > self.img_array.shape[1]):
            self.x = self.img_array.shape[1]-self.group_size
        
        if (self.y+self.group_size > self.img_array.shape[0]):
            self.y = self.img_array.shape[0]-self.group_size
    
    def RAs_square_init(self):
        """
        Instanciate the RAs
        """
        self.nb_RAs = 0
        self.RA_list = []
        for i in range (-self.group_size,
                        self.group_size+self.group_step,
                        self.group_step):
            
            for j in range (-self.group_size,
                            self.group_size+self.group_step,
                            self.group_step):
                
                _RA = ReactiveAgent(self.x, self.y, i, j, self.img_array)
                self.RA_list += [_RA]
                self.nb_RAs += 1
    
    def Get_RAs_Otsu_Prop(self):
        """
        Computing the proportion of subordinates RAs that are positive
        """
        nb_true_votes = 0
        nb_outside_frame_RAs = 0
        for _RA in self.RA_list:
            if not _RA.outside_frame:
                if (_RA.Otsu_decision()):
                    nb_true_votes+=1
            else:
                nb_outside_frame_RAs += 1
        
        self.decision_score = nb_true_votes/(self.nb_RAs-nb_outside_frame_RAs)
    
    def Add_One_Line_of_RAs(self, _x0, _y0, _xy1, _horizontal):
        """
        instanciates RAs on a line
        
        _x0 and _yo are the coordinates of the beginning point
        
        _xy1 is the coordinate of the last point. it should an x if _horizontal
        is true and a y, otherwise
        
        _horizontal (bool) if True the line is horizaontal. It is vertical, otherwise.
        """
        
        if (_horizontal):
            return [ReactiveAgent(
                    self.x, self.y,
                    i, _y0, self.img_array) for i in range(_x0,
                                                           _xy1+self.group_step,
                                                           self.group_step)]
        else:
            return [ReactiveAgent(
                    self.x, self.y,
                    _x0, i, self.img_array) for i in range(_y0,
                                                           _xy1+self.group_step,
                                                           self.group_step)]
    
    def Add_One_Layer_of_RAs(self, _distance_list):
        """
        Add one complete laryer of RAs. The layer is square shaped and initialized
        based on _distance_list.
        
        _distance_list is a list of size 4 with distances of the layer respectively
        the center of the RAL. in the order of North, South, East, West.
        """
        
        _layer = []
        
        #Adding North part
        _layer += [self.Add_One_Line_of_RAs(_distance_list[3],#_x0 is the distance to the west
                                            _distance_list[0],#_y0 is the distance to the North
                                            _distance_list[2],#_xy1 is the distance to the East
                                            _horizontal=True)]
        
        #Adding South part
        _layer += [self.Add_One_Line_of_RAs(_distance_list[3],#_x0 is the distance to the west
                                            _distance_list[1],#_y0 is the distance to the South
                                            _distance_list[2],#_xy1 is the distance to the East
                                            _horizontal=True)]
        
        #Adding East part
        _layer += [self.Add_One_Line_of_RAs(_distance_list[2],#_x0 is the distance to the East
                                            _distance_list[1],#_y0 is the distance to the South
                                            _distance_list[0],#_xy1 is the distance to the North
                                            _horizontal=False)]
        
        #Adding West part
        _layer += [self.Add_One_Line_of_RAs(_distance_list[3],#_x0 is the distance to the West
                                            _distance_list[1],#_y0 is the distance to the South
                                            _distance_list[0],#_xy1 is the distance to the North
                                            _horizontal=False)]
        return _layer
    
    def Flatten_Layer(self, _list):
        """
        returns the list of the RAS with out the lists separations of the North,
        South, East and West borders.
        """
        return _list[0]+_list[1]+_list[2]+_list[3]
    
    def RAs_border_init(self):
        """
        Instanciation strategy on the border of the group size.
        Added to accomodate the new growing strategy of the RAL
        """
        
        self.RA_list_card = self.Add_One_Layer_of_RAs([self.group_size,
                                                         -self.group_size,
                                                         self.group_size,
                                                         -self.group_size])
                
        self.RA_list = self.Flatten_Layer(self.RA_list_card)
        
        for i in range (4):
            self.nb_RAs_card[i] = len(self.RA_list_card[i])
            self.nb_RAs += self.nb_RAs_card[i]
    
    def Get_RAs_Mean_Point(self):
        """
        compute the mean point of the RAs that gave a positive answer to the 
        stimuli
        """
        active_RA_counter = 0
        mean_x = 0
        mean_y = 0
        
        nb_outside_frame_RAs = 0
        for _RA in self.RA_list:
            if not _RA.outside_frame:
                if (_RA.Otsu_decision()):
                    mean_x += _RA.global_x
                    mean_y += _RA.global_y
                    active_RA_counter += 1
            else:
                nb_outside_frame_RAs += 1
                
        self.recorded_Decision_Score += [active_RA_counter/(self.nb_RAs-nb_outside_frame_RAs)]
        
        if (active_RA_counter != 0):
            self.active_RA_Point[0] = mean_x/active_RA_counter
            self.active_RA_Point[1] = mean_y/active_RA_counter
    
    def Get_RAs_Mean_Point_3(self):
        """
        Scans the inner part of the RAL. We use the RAs on the North border and
        move down.
        """
        mean_x = 0
        mean_y = 0
        
        for _RA in self.RA_list:
            mean_x += _RA.global_x
            mean_y += _RA.global_y
            
        self.active_RA_Point[0] = mean_x/self.nb_RAs
        self.active_RA_Point[1] = mean_y/self.nb_RAs
    
    def Move_Based_on_AD_Order(self, _ADO_x, _ADO_y):
        """
        Update the position of the RAL based on the order given by the AD (agent
        director).
        _ADO_x (int):
            X coordinate of the target point (column of the image array)
        
        _ADO_y (int):
            Y coordinate of the target point (line of the image array)
        """
        self.x = _ADO_x
        self.y = _ADO_y
        
        self.recorded_positions += [[int(self.x), int(self.y)]]
        self.field_recorded_positions += [[int(self.x + self.field_offset[0]),
                                           int(self.y + self.field_offset[1])]]
        
        for _RA in self.RA_list:
            _RA.Move_Based_On_RAL(self.x, self.y)
    
    def Manage_RAs_distribution(self):
        """
        Moves the RAs individually
        """
        if (not self.Fixed):
            self.All_Border_Movement()
            
            self.All_Border_Growth()
            
            for i in range (4):
                self.Check_Border_Distance(i)
            
            self.Is_Fixed()
            
            self.RA_list = self.Flatten_Layer(self.RA_list_card)
            
            self.nb_RAs = sum(self.nb_RAs_card)
        
        
    def All_Border_Movement(self):
        """
        Individual movements or RAs for all 4 borders
        """
        
# =============================================================================
#         print("All_Border_Movement")
# =============================================================================
        self.all_end_score = []
        
        #North
# =============================================================================
#         print("North")
# =============================================================================
        self.Border_movement(0, 0, 1)
        
        #South
# =============================================================================
#         print("South")
# =============================================================================
        self.Border_movement(1, 0, -1)
        
        #East
# =============================================================================
#         print("East")
# =============================================================================
        self.Border_movement(2, 1, 0)
        
        #West
# =============================================================================
#         print("West")
# =============================================================================
        self.Border_movement(3, -1, 0)
    
    def Border_movement(self, _border_index, _x_dir, _y_dir):
        
        nb_RAs_in_Border = len(self.RA_list_card[_border_index])
        _border_scores = self.Individual_Movement_Scores(_border_index, _x_dir, _y_dir, nb_RAs_in_Border)
        
        self.Comparison_To_Fixed_Points(_border_index, _x_dir, _y_dir, _border_scores)
        
        _propagated_score = self.Propagated_Movement_Scores(_border_scores, nb_RAs_in_Border)
        
        end_score = _border_scores + _propagated_score
        self.all_end_score += [end_score]
        
        for i in range (nb_RAs_in_Border):
            if (_border_scores[i] == 0 and _propagated_score[i] == 0):
                self.RA_list_card[_border_index][i].Fixed = True
                self.nb_RAs_Fixed += 1
            
            else:
                self.Check_And_Apply_Movement(_border_index, _x_dir, _y_dir, i, end_score)
            
        
# =============================================================================
#         print("_border_scores", _border_scores)
#         print("_propagated_score", _propagated_score)
#         print("_sum_scores", end_score)
# =============================================================================
    def Check_Border_Distance(self, _border_index):#, _farthest_RAs):
        """
        Keeps track of the RAs (one per border) of each RAL that are the
        farthest away in its exploration.
        """
        #_res = _farthest_RAs
        
        if (_border_index == 0):#North
            _y_list = []
            for _RA in self.RA_list_card[_border_index]:
                _y_list += [_RA.local_y]
            self.Borders_Distance[0] = max(_y_list)
                
        if (_border_index == 1):#South
            _y_list = []
            for _RA in self.RA_list_card[_border_index]:
                _y_list += [_RA.local_y]
            self.Borders_Distance[1] = min(_y_list)
        
        if (_border_index == 2):#East
            _x_list = []
            for _RA in self.RA_list_card[_border_index]:
                _x_list += [_RA.local_x]
            self.Borders_Distance[2] = max(_x_list)
                
        if (_border_index == 3):#West
            _x_list = []
            for _RA in self.RA_list_card[_border_index]:
                _x_list += [_RA.local_x]
            self.Borders_Distance[3] = min(_x_list)

    def Individual_Movement_Scores(self, _border_index, _x_dir, _y_dir, _nb_RAs):
        
        _border_scores = np.zeros(_nb_RAs, dtype=np.int_)
        
        for i in range (_nb_RAs):
            _border_scores[i] = self.RA_list_card[_border_index][i].Exploration_Report(_x_dir, _y_dir,
                                                                                      self.exploration_factor,
                                                                                      self.shrinking_factor)
        return _border_scores
    
    def Propagated_Movement_Scores(self, _border_scores, _nb_RAs):
        """
        We only propagate the exploration score
        """
        
        _propagation_score = np.zeros(_nb_RAs, dtype = np.int_)
        for i in range (_nb_RAs):
            _score = _border_scores[i]
            _reach = abs(_score)
            
            for j in range (1, _reach):
                k = i+j
                if 0 <= k < _nb_RAs:
                    if _score > 0:
                        _propagation_score[k] += _score - j
                        
                k = i-j
                if 0 <= k < _nb_RAs:
                    if _score > 0:
                        _propagation_score[k] += _score - j
                        
        return _propagation_score
    
    def Check_And_Apply_Movement(self, _border_index, _x_dir, _y_dir, _RA_index, _score):
        """
        Directly applies the movement score only if border overlap has not been
        detected with a neighbour.
        otherwise, it applies a correction to the score so that the pixel
        agent do not go beyond the other pixel agents that is the source of the
        overlap.
        
        It also makes sure that a RA do not shrink beyond half the center
        of the RAL
        """
        if (self.With_Neighbour_Overlap[_border_index]):
            if (_border_index == 0):
                if (self.RA_list_card[_border_index][_RA_index].local_y + _y_dir * _score[_RA_index] > self.Borders_Distance[_border_index]):
                    _y_diff = self.RA_list_card[_border_index][_RA_index].local_y + _y_dir * _score[_RA_index] - self.Borders_Distance[_border_index]
                    _score[_RA_index] -= _y_diff
                    
            if (_border_index == 1):

                if (self.RA_list_card[_border_index][_RA_index].local_y + _y_dir * _score[_RA_index] < self.Borders_Distance[_border_index]):
                    _y_diff = self.RA_list_card[_border_index][_RA_index].local_y + _y_dir * _score[_RA_index] - self.Borders_Distance[_border_index]
                    _score[_RA_index] += _y_diff
                    
            if (_border_index == 2):
                if (self.RA_list_card[_border_index][_RA_index].local_x + _x_dir * _score[_RA_index] > self.Borders_Distance[_border_index]):
                    _x_diff = self.RA_list_card[_border_index][_RA_index].local_x + _x_dir * _score[_RA_index] - self.Borders_Distance[_border_index]
                    _score[_RA_index] -= _x_diff
                    
            if (_border_index == 3):
                if (self.RA_list_card[_border_index][_RA_index].local_x + _x_dir * _score[_RA_index] < self.Borders_Distance[_border_index]):
                    _x_diff = self.RA_list_card[_border_index][_RA_index].local_x + _x_dir * _score[_RA_index] - self.Borders_Distance[_border_index]
                    _score[_RA_index] += _x_diff
        
        if (_border_index == 0):
            if (self.RA_list_card[_border_index][_RA_index].local_y + _y_dir * _score[_RA_index] <= 0):
                print("North, beyond half correction")
                _score[_RA_index] = 0
                    
        if (_border_index == 1):
            if (self.RA_list_card[_border_index][_RA_index].local_y + _y_dir * _score[_RA_index] >= 0):
                print("South, beyond half correction")
                _score[_RA_index] = 0
                
        if (_border_index == 2):
            if (self.RA_list_card[_border_index][_RA_index].local_x + _x_dir * _score[_RA_index] <= 0):
                print("East, beyond half correction")
                _score[_RA_index] = 0
                
        if (_border_index == 3):
            if (self.RA_list_card[_border_index][_RA_index].local_x + _x_dir * _score[_RA_index] >= 0):
                print("West, beyond half correction")
                _score[_RA_index] = 0
        
        
        self.RA_list_card[_border_index][_RA_index].Update_All_coords(_x_dir*_score[_RA_index],
                                                                          _y_dir*_score[_RA_index])
        
    
    def Comparison_To_Fixed_Points(self,
                                   _border_index,
                                   _x_dir, _y_dir,
                                   _border_scores):
        """
        Fixed points are points that have found edges of the target structure.
        We want to use them as references to guide the points that have not
        found anything.
        We will take the movement_scores and force a RA to move in the direction
        of its neighbour if that one is fixed.
        """
# =============================================================================
#         print("self.nb_RAs_card[_border_index]", self.nb_RAs_card[_border_index])
# =============================================================================
        for i in range (self.nb_RAs_card[_border_index]):#for every RA
            if (self.RA_list_card[_border_index][i].Fixed or
                self.RA_list_card[_border_index][i].Otsu_decision()):#if RA is fixed or on a white pixel
                for k in [i-1, i+1]:#for left & right neighbours
                    if (0<=k<self.nb_RAs_card[_border_index]):#if such neighbour exists
                        if (_border_scores[k]==-self.shrinking_factor):#If the neighbour is not exploring
                            if (_x_dir == 0 ):#border movement on the Y axis
                                _y_dir_to_fixed = (self.RA_list_card[_border_index][i].global_y-
                                                   self.RA_list_card[_border_index][k].global_y)
                                
                                if (_y_dir_to_fixed > 0):#the neighbour is going the opposite direction
# =============================================================================
#                                     print( k, _border_scores[k], _y_dir, _y_dir_to_fixed)
# =============================================================================
                                    _border_scores[k] = _y_dir*self.exploration_factor
                                elif (_y_dir_to_fixed < 0):
                                    _border_scores[k] = -_y_dir*self.exploration_factor
                                
                            elif(_y_dir == 0):#border movement on the Y axis
                                _x_dir_to_fixed = (self.RA_list_card[_border_index][i].global_x-
                                                        self.RA_list_card[_border_index][k].global_x)
                                if (_x_dir_to_fixed > 0):#the neighbour is going the opposite direction
# =============================================================================
#                                     print( k, _border_scores[k], _x_dir, _x_dir_to_fixed)
# =============================================================================
                                    _border_scores[k] = _x_dir*self.exploration_factor
                                
                                elif(_x_dir_to_fixed < 0):
                                    _border_scores[k] = -_x_dir*self.exploration_factor
                                
    
    def All_Border_Growth(self):
        """
        Cutting or adding RAs at the extremeties of the borders based on their
        movements computed beforehand (with All_Border_Movement)
        """
        #North - West
        self.Border_Growth(0, 0, 3, -1)
        
        #North - East
        self.Border_Growth(0, -1, 2, -1)
        
        #South - West
        self.Border_Growth(1, 0, 3, 0)
        
        #South - East
        self.Border_Growth(1, -1, 2, 0) 
    
    def Border_Growth(self,
                      _border_index_1, _extreme_index_1,
                      _border_index_2, _extreme_index_2,
                      _limit_size_factor = 0.25):
        
        _limit_size = int(_limit_size_factor * self.group_size)        
            
        if (_border_index_1 == 0):
            if (self.all_end_score[_border_index_1][_extreme_index_1] < 0 and
                self.all_end_score[_border_index_2][_extreme_index_2] < 0):
            
                if (self.nb_RAs_card[_border_index_1] > _limit_size):
                    if (_border_index_2 == 3): #we truncate from the West
                        self.RA_list_card[_border_index_1] = self.RA_list_card[_border_index_1][1:]
                    elif(_border_index_2 == 2): #we truncate fromt he East
                        self.RA_list_card[_border_index_1] = self.RA_list_card[_border_index_1][:-1]
                    self.nb_RAs_card[_border_index_1] -= 1
                    
                if (self.nb_RAs_card[_border_index_2] > _limit_size):
                    self.RA_list_card[_border_index_2] = self.RA_list_card[_border_index_2][:-1]
                    self.nb_RAs_card[_border_index_2] -= 1
                    
            else:
                _y_RAs = []
                _x_RAs = []
                if self.all_end_score[_border_index_1][_extreme_index_1] > 0: #with North we add at the end of West and East
                    _y_diff = abs(self.RA_list_card[_border_index_1][_extreme_index_1].local_y - \
                                self.RA_list_card[_border_index_2][_extreme_index_2].local_y)
                    _y_RAs = [ReactiveAgent(self.x, self.y,
                                          self.RA_list_card[_border_index_2][_extreme_index_2].local_x,
                                          self.RA_list_card[_border_index_1][_extreme_index_1].local_y - k,
                                          self.img_array) for k in range(0, _y_diff, self.group_step)][::-1]
                    
                    self.nb_RAs_card[_border_index_2] += len(_y_RAs)
                    
                if self.all_end_score[_border_index_2][_extreme_index_2] > 0:
                    
                    _x_diff = abs(self.RA_list_card[_border_index_1][_extreme_index_1].local_x - \
                                    self.RA_list_card[_border_index_2][_extreme_index_2].local_x)
                    
                    if (_border_index_2 == 3): #with West we add at the beginning of North
                        _x_RAs = [ReactiveAgent(self.x, self.y,
                                              self.RA_list_card[_border_index_2][_extreme_index_2].local_x + k,
                                              self.RA_list_card[_border_index_1][_extreme_index_1].local_y,
                                              self.img_array) for k in range(0, _x_diff, self.group_step)]
            
                        self.RA_list_card[_border_index_1] = _x_RAs + self.RA_list_card[_border_index_1]
                        
                                              
                    elif (_border_index_2 == 2): #with East we add at the end of North
                        _x_RAs = [ReactiveAgent(self.x, self.y,
                                              self.RA_list_card[_border_index_2][_extreme_index_2].local_x - k,
                                              self.RA_list_card[_border_index_1][_extreme_index_1].local_y,
                                              self.img_array) for k in range(0, _x_diff, self.group_step)][::-1]
            
                        self.RA_list_card[_border_index_1] += _x_RAs     
                        
                    self.nb_RAs_card[_border_index_1] += len(_x_RAs)
                
                self.RA_list_card[_border_index_2] += _y_RAs
        
        
        if (_border_index_1 == 1):
            if (self.all_end_score[_border_index_1][_extreme_index_1] < 0 and
                self.all_end_score[_border_index_2][_extreme_index_2] < 0):
            
                if (self.nb_RAs_card[_border_index_1] > _limit_size):
                    if (_border_index_2 == 3): #we truncate from the West
                        self.RA_list_card[_border_index_1] = self.RA_list_card[_border_index_1][1:]
                    elif(_border_index_2 == 2): #we truncate fromt he East
                        self.RA_list_card[_border_index_1] = self.RA_list_card[_border_index_1][:-1]
                    self.nb_RAs_card[_border_index_1] -= 1
                    
                if (self.nb_RAs_card[_border_index_2] > _limit_size):
                    self.RA_list_card[_border_index_2] = self.RA_list_card[_border_index_2][1:]
                    self.nb_RAs_card[_border_index_2] -= 1
                    
            else:
                _y_RAs = []
                _x_RAs = []
                if self.all_end_score[_border_index_1][_extreme_index_1] > 0: #with North we add at the end of West and East
                    _y_diff = abs(self.RA_list_card[_border_index_1][_extreme_index_1].local_y - \
                                self.RA_list_card[_border_index_2][_extreme_index_2].local_y)
                    _y_RAs = [ReactiveAgent(self.x, self.y,
                                          self.RA_list_card[_border_index_2][_extreme_index_2].local_x,
                                          self.RA_list_card[_border_index_1][_extreme_index_1].local_y + k,
                                          self.img_array) for k in range(0, _y_diff, self.group_step)]
                    
                    self.nb_RAs_card[_border_index_2] += len(_y_RAs)
                
                if self.all_end_score[_border_index_2][_extreme_index_2] > 0:
                    
                    _x_diff = abs(self.RA_list_card[_border_index_1][_extreme_index_1].local_x - \
                                    self.RA_list_card[_border_index_2][_extreme_index_2].local_x)
                                        
                    if (_border_index_2 == 3): #with West we add at the beginning of South
                        _x_RAs = [ReactiveAgent(self.x, self.y,
                                              self.RA_list_card[_border_index_2][_extreme_index_2].local_x + k,
                                              self.RA_list_card[_border_index_1][_extreme_index_1].local_y,
                                              self.img_array) for k in range(0, _x_diff, self.group_step)]
            
                        self.RA_list_card[_border_index_1] = _x_RAs + self.RA_list_card[_border_index_1]
                        
                                              
                    elif (_border_index_2 == 2): #with East we add at the end of South
                        _x_RAs = [ReactiveAgent(self.x, self.y,
                                              self.RA_list_card[_border_index_2][_extreme_index_2].local_x - k,
                                              self.RA_list_card[_border_index_1][_extreme_index_1].local_y,
                                              self.img_array) for k in range(0, _x_diff, self.group_step)][::-1]
            
                        self.RA_list_card[_border_index_1] += _x_RAs     
                        
                    self.nb_RAs_card[_border_index_1] += len(_x_RAs)
                
                self.RA_list_card[_border_index_2] = _y_RAs + self.RA_list_card[_border_index_2]
    
# =============================================================================
#     def Compute_Surface(self):
#         """
#         Counts the number of white pixels in the area scanned by the RAL. The 
#         search of white pixels uses the Pixel agents as seeds.
#         """
#         self.nb_contiguous_white_pixel = 0 #reset
#         
#         #print("self.group_size", self.group_size)
#         square_height = self.Borders_Distance[0]+abs(self.Borders_Distance[1])-2
#         square_width = self.Borders_Distance[2]+abs(self.Borders_Distance[3])-2
# 
#         surface_print=np.zeros((square_height,square_width))
#         
#         directions = [(0,1), (0,-1), (1,0), (-1,0)] #(x, y)
#         
#         explorers = []
#         nb_explorers = 0
#         
#         for _RA in self.RA_list_card[0][1:-1]:
#             for k in range (-self.group_step,
#                             -self.Borders_Distance[0]+self.Borders_Distance[1],
#                             -self.group_step):
#                 explorers += [(_RA.local_x, k+abs(self.Borders_Distance[1]))]
#                 nb_explorers += 1
#         #print("nb_explorers", nb_explorers)
#         #nb_op = 0
#         while nb_explorers > 0:
#             print_row = explorers[0][1]+self.group_size#row coord in surface print array
#             print_col = explorers[0][0]+self.group_size#column coord in surface print array
#             
#             image_row = self.y+explorers[0][1]#row coord in image array
#             image_col = self.x+explorers[0][0]#col coord in image array
#             
#             if (image_row < self.img_array.shape[0] and 
#                 image_col < self.img_array.shape[1] and
#                 print_row < surface_print.shape[0] and 
#                 print_col < surface_print.shape[1]):
#                 if (self.img_array[image_row][image_col][0] > 220):#if the pixel is white
#                     surface_print[print_row][print_col]=2
#                     self.nb_contiguous_white_pixel +=1
#                     
#                     for _d in directions:
#                         if (0 <= print_row + _d[1] < square_height and
#                             0 <= print_col + _d[0] < square_width):#if in the bounds of the surface_print array size
#                             if (surface_print[print_row + _d[1]][print_col + _d[0]] == 0):#if the pixel has not an explorer already
#                                 
#                                 surface_print[print_row+_d[1]][print_col+_d[0]]=1#we indicate that we have added the coords to the explorers
#                                 
#                                 new_explorer_x = print_col-self.group_size + _d[0]
#                                 new_explorer_y = print_row-self.group_size + _d[1]
#                                 explorers += [(new_explorer_x, 
#                                                new_explorer_y)]
#                                 nb_explorers += 1
#             
#             explorers = explorers[1:]
#             nb_explorers -= 1
#             
#             #nb_op+=1
#         self.white_contigous_surface = self.nb_contiguous_white_pixel/(square_height*square_width)
# =============================================================================
# =============================================================================
#         print(surface_print)
#         print("nb_white_pixels", self.nb_contiguous_white_pixel)
#         print("surface_white_pixels", self.white_contigous_surface)
# =============================================================================
        
    def Is_Fixed(self):
        if (self.nb_RAs_Fixed/self.nb_RAs > 0.9):
            self.Fixed = True
                
    
    def Extract_RAs_Locals(self):
        """
        Stores the x and y coordinates of the RAs per borders
        """
        self.RAs_local_positions = []
        
        for _border_index in range (4):
            RAs_local_coords = []
            for _RA in self.RA_list_card[_border_index]:
                RAs_local_coords += [(int(_RA.local_x), int(_RA.local_y))]
            self.RAs_local_positions += [RAs_local_coords]
    
    def Compute_Surface(self):
        """
        Computes area of the polygon defined by the closing curve built by the
        RAs
        """
        self.Extract_RAs_Locals()
        
        total = self.RAs_local_positions[0]+self.RAs_local_positions[2][::-1]+\
                self.RAs_local_positions[1][::-1]+self.RAs_local_positions[3]
        
        self.area = 0
        for i in range (self.nb_RAs-1):
            self.area += 0.5*(total[i+1][1]+total[i][1])*(total[i+1][0]-total[i][0])
        
        self.area += 0.5*(total[1][1]+total[-1][1])*(total[0][0]-total[-1][0])
    
    def Initialize_Surface_Explorers(self, _border_index):
        """
        """
        explorers = []
        nb_explorers = 0
        if (_border_index == 0):
            for _RA in self.RA_list_card[0][1:-1]:
                for k in range (self.group_step,
                                self.Borders_Distance[0]-self.Borders_Distance[1],
                                self.group_step):
                    explorers += [(_RA.global_x, _RA.global_y - k)]
                    nb_explorers += 1
        
        if (_border_index == 1):
            for _RA in self.RA_list_card[1][1:-1]:
                for k in range (self.group_step,
                                self.Borders_Distance[0]-self.Borders_Distance[1],
                                self.group_step):
                    explorers += [(_RA.global_x, _RA.global_y + k)]
                    nb_explorers += 1
        
        if (_border_index == 2):
            for _RA in self.RA_list_card[2][1:-1]:
                for k in range (self.group_step,
                                self.Borders_Distance[2]-self.Borders_Distance[3],
                                self.group_step):
                    explorers += [(_RA.global_x - k, _RA.global_y)]
                    nb_explorers += 1
        
        if (_border_index == 3):
            for _RA in self.RA_list_card[3][1:-1]:
                for k in range (self.group_step,
                                self.Borders_Distance[2]-self.Borders_Distance[3],
                                self.group_step):
                    explorers += [(_RA.global_x + k, _RA.global_y)]
                    nb_explorers += 1
        
        return explorers, nb_explorers
                
    def Compute_Surface_2(self):
        """
        Computes the area as a number of white pixels within the polygone defined 
        by the RAs.
        """
        self.Extract_RAs_Locals()
        
        self.area = 0 #reset
        
        #print("self.group_size", self.group_size)
        square_height = self.Borders_Distance[0]-self.Borders_Distance[1]
        square_width = self.Borders_Distance[2]-self.Borders_Distance[3]
        
# =============================================================================
#         print(self.Borders_Distance,
#               "height:", square_height, "width:", square_width,
#               "x:", self.x, "y:", self.y)
# =============================================================================
        
        surface_print=np.zeros((square_height,square_width))
        
        directions = [(0,1), (0,-1), (1,0), (-1,0)] #(x, y)
        
        explorers = []
        nb_explorers = 0
        
        explorers, nb_explorers = self.Initialize_Surface_Explorers(np.argmax(self.nb_RAs_card))
        
        anchor_x = self.x+self.Borders_Distance[3]
        anchor_y = self.y+self.Borders_Distance[1]
        
        while nb_explorers > 0:
            
            print_row = explorers[0][1]-anchor_y#row coord in surface print array
            print_col = explorers[0][0]-anchor_x#column coord in surface print array
            
            image_row = explorers[0][1]#row coord in image array
            image_col = explorers[0][0]#col coord in image array
            
            inside_double_check = (self.Is_Inside_Polygon((anchor_x-1, anchor_y),(image_col, image_row)) or
                                   self.Is_Inside_Polygon((anchor_x, anchor_y-1),(image_col, image_row)))
            
            if (inside_double_check and
                0 <= image_row < self.img_array.shape[0] and 
                0 <= image_col < self.img_array.shape[1] and
                0 <= print_row < surface_print.shape[0] and 
                0 <= print_col < surface_print.shape[1]):
                if (self.img_array[image_row][image_col][0] > 220):#if the pixel is white
                    surface_print[print_row][print_col]=2
                    self.area +=1
                    
                    for _d in directions:
                        if (0 <= print_row + _d[1] < square_height and
                            0 <= print_col + _d[0] < square_width):#if in the bounds of the surface_print array size
                            if (surface_print[print_row + _d[1]][print_col + _d[0]] == 0):#if the pixel has not an explorer already
                                
                                surface_print[print_row+_d[1]][print_col+_d[0]]=1#we indicate that we have added the coords to the explorers
                                
                                new_explorer_x = image_col + _d[0]
                                new_explorer_y = image_row + _d[1]
                                explorers += [(new_explorer_x, 
                                               new_explorer_y)]
                                nb_explorers += 1
            
            explorers = explorers[1:]
            nb_explorers -= 1
        
# =============================================================================
#         print(surface_print)
#         print("nb_white_pixels", self.nb_contiguous_white_pixel)
#         print("surface_white_pixels", self.white_contigous_surface)
# =============================================================================
# =============================================================================
#         fig = plt.figure(figsize=(5,5),dpi=300)
#         ax = fig.add_subplot(111)
#         ax.imshow(surface_print)
#         print("nb_white_pixels", self.area)
# =============================================================================
    
    def Is_Inside_Polygon(self, _origin, _test_point):
        """
        Uses the raycasting method to check if the point is inside the polygon
        """
        inside = False
        total = self.RA_list_card[0]+self.RA_list_card[2][::-1]+\
                self.RA_list_card[1][::-1]+self.RA_list_card[3]
        for i in range (self.nb_RAs-1):
            if (self.Vector_Intersection(_origin[0], _origin[1],
                                         _test_point[0], _test_point[1],
                                         total[i].global_x, total[i].global_y,
                                         total[i+1].global_x, total[i+1].global_y)):
                inside = not inside
        
        if (self.Vector_Intersection(_origin[0], _origin[1],
                                         _test_point[0], _test_point[1],
                                         total[0].global_x, total[0].global_y,
                                         total[-1].global_x, total[-1].global_y)):
                inside = not inside
        return inside

    def Vector_Intersection(self,
                            v1x1, v1y1,
                            v1x2, v1y2,
                            v2x1, v2y1,
                            v2x2, v2y2):
        """
        Returns True is 2 vector intersects.
        This method helps computing if the raycasting crosses a bound
        
        taken_from: https://stackoverflow.com/questions/217578/how-can-i-determine-whether-a-2d-point-is-within-a-polygon
        """
        crossed = True
# =============================================================================
#     Convert vector 1 to a line (line 1) of infinite length.
#      We want the line in linear equation standard form: A*x + B*y + C = 0
#     See: http://en.wikipedia.org/wiki/Linear_equation
# =============================================================================
        a1 = v1y2 - v1y1;
        b1 = v1x1 - v1x2;
        c1 = (v1x2 * v1y1) - (v1x1 * v1y2);

# =============================================================================
#     Every point (x,y), that solves the equation above, is on the line,
#     every point that does not solve it, is not. The equation will have a
#     positive result if it is on one side of the line and a negative one 
#     if is on the other side of it. We insert (x1,y1) and (x2,y2) of vector
#     2 into the equation above.
# =============================================================================
        d1 = (a1 * v2x1) + (b1 * v2y1) + c1;
        d2 = (a1 * v2x2) + (b1 * v2y2) + c1;

# =============================================================================
#     If d1 and d2 both have the same sign, they are both on the same side
#     of our line 1 and in that case no intersection is possible. Careful, 
#     0 is a special case, that's why we don't test ">=" and "<=", 
#     but "<" and ">".
# =============================================================================
        if (d1 > 0 and d2 > 0) or (d1 < 0 and d2 < 0):
            crossed = False

# =============================================================================
#     The fact that vector 2 intersected the infinite line 1 above doesn't 
#     mean it also intersects the vector 1. Vector 1 is only a subset of that
#     infinite line 1, so it may have intersected that line before the vector
#     started or after it ended. To know for sure, we have to repeat the
#     the same test the other way round. We start by calculating the 
#     infinite line 2 in linear equation standard form.
# =============================================================================
        a2 = v2y2 - v2y1;
        b2 = v2x1 - v2x2;
        c2 = (v2x2 * v2y1) - (v2x1 * v2y2);

# =============================================================================
#   Calculate d1 and d2 again, this time using points of vector 1.
# =============================================================================
        d1 = (a2 * v1x1) + (b2 * v1y1) + c2;
        d2 = (a2 * v1x2) + (b2 * v1y2) + c2;

# =============================================================================
#     Again, if both have the same sign (and neither one is 0),
#     no intersection is possible.
# =============================================================================
        if (d1 > 0 and d2 > 0) or (d1 < 0 and d2 < 0):
            crossed = False

# =============================================================================
#     If we get here, only two possibilities are left. Either the two
#     vectors intersect in exactly one point or they are collinear, which
#     means they intersect in any number of points from zero to infinite.
# =============================================================================
# =============================================================================
#         if ((a1 * b2) - (a2 * b1) == 0):
#             crossed = True
# =============================================================================

# =============================================================================
#     If they are not collinear, they must intersect in exactly one point.
# =============================================================================
        return crossed;
    
class Row_Agent(object):
    """
    Agent rang de culture
    
    _plant_FT_pred_per_crop_rows (list of lists extracted for a JSON file):
        array containing the predicted position of plants organized by rows.
        The lists corresponding to rows contain other lists of length 2 giving 
        the predicted position of a plant under the convention [image_line, image_column]
    
    _OTSU_img_array (numpy.array):
        array containing the OSTU segmented image on which the Multi Agent System
        is working
    
    _group_size (int, optional with default value = 5):
        number of pixels layers around the leader on which we instanciate 
        reactive agents
    
    _group_step (int, optional with default value = 5):
        distance between two consecutive reactive agents
    
    _field_offset (list size 2, optional with default value [0, 0]):
        the offset to apply to all the positioned agents of the simulation to
        be coherent at the field level.
    
    """
    def __init__(self, _plant_FT_pred_in_crop_row, _OTSU_img_array,
                 _group_size = 50, _group_step = 5,
                 _field_offset = [0,0]):
        
# =============================================================================
#         print()
#         print("Initializing Row Agent class...", end = " ")
# =============================================================================
        
        self.plant_FT_pred_in_crop_row = _plant_FT_pred_in_crop_row
        
        self.OTSU_img_array = _OTSU_img_array
        
        self.group_size = _group_size
        self.group_step = _group_step
        
        self.field_offset = _field_offset
        
        self.RALs = []
        self.nb_RALs = 0
        self.nb_Fixed_RALs = 0
        
        self.extensive_init = False
        
# =============================================================================
#         print("Done")
# =============================================================================
        
        self.Initialize_RALs()
        
        self.Get_Row_Mean_X()


    def Initialize_RALs(self):
        """
        Go through the predicted coordinates of the plants in self.plant_FT_pred_par_crop_rows
        and initialize RALs at these places.
        """
# =============================================================================
#         print()
# =============================================================================
        
        for _plant_pred in self.plant_FT_pred_in_crop_row:
            RAL = ReactiveAgent_Leader(_x = _plant_pred[0],
                                       _y = _plant_pred[1], #self.OTSU_img_array.shape[0] - 
                                       _img_array = self.OTSU_img_array,
                                       _group_size = self.group_size,
                                       _group_step = self.group_step,
                                       _field_offset = self.field_offset)
            
            self.RALs += [RAL]
            self.nb_RALs += 1
        
    
    def Edge_Exploration(self, _filling_step):
        """
        Uses the first and last RALs in the self.RALs list to extensively instanciate
        RALs at the edges of the rows.
        """
        
        _RAL_ref_index = -1
        _RAL_ref = self.RALs[_RAL_ref_index]
        
        y_init = _RAL_ref.y
        while y_init + _filling_step < self.OTSU_img_array.shape[0]:
            new_RAL = ReactiveAgent_Leader(_x = self.Row_Mean_X,
                                           _y = int(y_init + _filling_step),
                                           _img_array = self.OTSU_img_array,
                                           _group_size = self.group_size,
                                           _group_step = self.group_step,
                                           _field_offset = self.field_offset)
            new_RAL.used_as_filling_bound = True
            y_init += _filling_step
            
            self.RALs += [new_RAL]
            self.nb_RALs += 1
                
        _RAL_ref_index = 0
        _RAL_ref = self.RALs[_RAL_ref_index]
        y_init = _RAL_ref.y
        new_RALs = []
        new_diffs = []
        while y_init - _filling_step > 0:
            new_RAL = ReactiveAgent_Leader(_x = self.Row_Mean_X,
                                           _y = int(y_init + _filling_step),
                                           _img_array = self.OTSU_img_array,
                                           _group_size = self.group_size,
                                           _group_step = self.group_step)
            new_RAL.used_as_filling_bound = True
            
            new_RALs += [new_RAL]
            self.nb_RALs +=1
            new_diffs += [_filling_step]
            
            y_init -= _filling_step
        
        self.RALs = new_RALs + self.RALs
        
        a = np.array([RAL.y for RAL in self.RALs])
        b = np.argsort(a)
        self.RALs = list(np.array(self.RALs)[b])
    
    def Fuse_RALs(self, _start, _stop):
        """
        _start and _stop are the indeces of the RALs to fuse so that they 
        correspond to the boundaries [_start _stop[
        """
        
# =============================================================================
#         print("Fusing procedure...")
# =============================================================================
        
        fusion_RAL_x = 0
        fusion_RAL_y = 0
        
        for _RAL in self.RALs[_start:_stop+1]:
            fusion_RAL_x += _RAL.x
            fusion_RAL_y += _RAL.y
            
        fusion_RAL = ReactiveAgent_Leader(_x = int(fusion_RAL_x/(_stop+1-_start)),
                                           _y = int(fusion_RAL_y/(_stop+1-_start)),
                                           _img_array = self.OTSU_img_array,
                                           _group_size = self.group_size,
                                           _group_step = self.group_step)
        
        if (self.RALs[_start].used_as_filling_bound and
            self.RALs[_stop].used_as_filling_bound):
                fusion_RAL.used_as_filling_bound = True
        
# =============================================================================
#         print("Fused", self.RALs[_start].y,
#               "and", self.RALs[_stop].y)
# =============================================================================
        newYdist = []
        new_diffs = []
        if (_start - 1 >= 0):
            new_diffs += [abs(fusion_RAL.y-self.RALs[_start-1].y)]
            newYdist = self.InterPlant_Diffs[:_start-1]
        
        tail_newRALs = []
        if (_stop+1<self.nb_RALs):
            new_diffs += [abs(fusion_RAL.y-self.RALs[_stop+1].y)]
            tail_newRALs = self.RALs[_stop+1:]
        
        newYdist += new_diffs
        
        
        if (_stop+1<len(self.InterPlant_Diffs)):
            newYdist += self.InterPlant_Diffs[_stop+1:]
        
        self.InterPlant_Diffs = newYdist
        
        self.RALs = self.RALs[:_start]+[fusion_RAL]+tail_newRALs
        self.nb_RALs -= 1
    
    def Fill_RALs(self, _RAL_1_index, _RAL_2_index, _filling_step):
        
        if (not self.RALs[_RAL_1_index].used_as_filling_bound or
            not self.RALs[_RAL_2_index].used_as_filling_bound):
# =============================================================================
#             print("Filling procedure...")
# =============================================================================
            y_init = self.RALs[_RAL_1_index].y
            new_RALs = []
            nb_new_RALs = 0
            new_diffs = []
            while y_init + _filling_step < self.RALs[_RAL_2_index].y:
                new_RAL = ReactiveAgent_Leader(_x = self.Row_Mean_X,
                                               _y = int(y_init + _filling_step),
                                               _img_array = self.OTSU_img_array,
                                               _group_size = self.group_size,
                                               _group_step = self.group_step)
                new_RAL.used_as_filling_bound = True
                
                new_RALs += [new_RAL]
                new_diffs += [_filling_step]
                
                y_init += _filling_step
                
                nb_new_RALs += 1
            
            self.RALs[_RAL_1_index].used_as_filling_bound = True
            self.RALs[_RAL_2_index].used_as_filling_bound = True
            
            if (nb_new_RALs > 0):
                new_diffs += [abs(new_RALs[-1].y-self.RALs[_RAL_2_index].y)]
                self.RALs = self.RALs[:_RAL_1_index+1]+new_RALs+self.RALs[_RAL_2_index:]
                
                self.InterPlant_Diffs = self.InterPlant_Diffs[:_RAL_1_index]+ \
                                    new_diffs+ \
                                    self.InterPlant_Diffs[_RAL_2_index:]
                self.nb_RALs += nb_new_RALs
            
    def Fill_or_Fuse_RALs(self, _crit_value, _fuse_factor = 0.5, _fill_factor = 1.5):
        i = 0
        while i < self.nb_RALs-1:
            
# =============================================================================
#             print(self.InterPlant_Diffs[i], _fuse_factor*_crit_value)
# =============================================================================
            min_size = min([self.RALs[i].group_size, self.RALs[i+1].group_size])
            
            if (self.InterPlant_Diffs[i] < _fuse_factor*_crit_value or
                (abs(self.RALs[i].x-self.RALs[i+1].x) < min_size and
                 abs(self.RALs[i].y-self.RALs[i+1].y) < min_size)):
                self.Fuse_RALs(i, i+1)
            
            if (not self.extensive_init):
                if (i<len(self.InterPlant_Diffs)):#in case we fused the last 2 RAL of the crop row
                    if self.InterPlant_Diffs[i] > _fill_factor*_crit_value:
                        self.Fill_RALs(i, i+1, int(1.1*_fuse_factor*_crit_value))
            
            i += 1
        
# =============================================================================
#         print("After fill and fuse procedure over all the crop row, the new RAls list is :", end = ", ")
#         for _RAL in self.RALs:
#             print([_RAL.x, _RAL.y], end=", ")
# =============================================================================
    
    def Check_RALs_Exploration(self):
        """
        Looks at the exploration status of the RALs: where are the farthest RAs
        under supervision of the RALs. Checks that neighbour RALs do not overlap
        with each other.
        If overlapping is detected (mainly North or South), the RAs of each are
        ordered to withdraw and are fixed.
        """
        
        for i in range (self.nb_RALs-1):
            if (not self.RALs[i].With_Neighbour_Overlap[0] and not self.RALs[i+1].With_Neighbour_Overlap[1]):
                _y_north_border = self.RALs[i].y + self.RALs[i].Borders_Distance[0]
                _y_south_border = self.RALs[i+1].y + self.RALs[i+1].Borders_Distance[1]
                
                if (_y_north_border > _y_south_border):
                    
# =============================================================================
#                     print(i, self.RALs[i].Borders_Distance[0], self.RALs[i].y, _y_north_border)
#                     print (i+1, self.RALs[i+1].Borders_Distance[1], self.RALs[i+1].y, _y_south_border)
# =============================================================================
                    
                    _candidate_north_update = []
                    _candidate_south_update = []
                    
                    for _RA in self.RALs[i].RA_list_card[0]:#North
# =============================================================================
#                         print("North RAs y", _RA.global_y, _y_south_border)
# =============================================================================
                        if (_RA.global_y > _y_south_border):
                            _half_y_overlap = int((_RA.global_y - _y_south_border)*0.5)+1
                            
                            if (_RA.Fixed):
                                _RA.Fixed = False
                            else:
                                self.RALs[i].nb_RAs_Fixed += 1
                                
                            _RA.Update_All_coords(0, -_half_y_overlap)
                            _RA.Fixed = True
                            _candidate_north_update += [_RA.local_y]
                        
                    for _RA in self.RALs[i+1].RA_list_card[1]:#South
# =============================================================================
#                         print("South RAs y", _RA.global_y, _y_north_border)
# =============================================================================
                        if (_RA.global_y < _y_north_border):
                            _half_y_overlap = int((_y_north_border - _RA.global_y)*0.5)+1
                            
                            if (_RA.Fixed):
                                _RA.Fixed = False
                            else:
                                self.RALs[i+1].nb_RAs_Fixed += 1
                                
                            _RA.Update_All_coords(0, _half_y_overlap)
                            _RA.Fixed = True
                            _candidate_south_update += [_RA.local_y]
                    
# =============================================================================
#                     print(_candidate_north_update)
# =============================================================================
                    self.RALs[i].Borders_Distance[0] = max(_candidate_north_update)
                    self.RALs[i].With_Neighbour_Overlap[0] = True
# =============================================================================
#                     print(_candidate_south_update)
# =============================================================================
                    self.RALs[i+1].Borders_Distance[1] = min(_candidate_south_update)
                    self.RALs[i+1].With_Neighbour_Overlap[1] = True
                    
# =============================================================================
#                     print(i, self.RALs[i].Borders_Distance[0], self.RALs[i].y, _y_north_border)
#                     print (i+1, self.RALs[i+1].Borders_Distance[1], self.RALs[i+1].y, _y_south_border)
# =============================================================================
            
    
    def Get_RALs_mean_points(self):
        for _RAL in self.RALs:
            _RAL.Get_RAs_Mean_Point()
            #_RAL.Get_RAs_Mean_Point_3()
    
    def Get_Row_Mean_X(self):
        RALs_X = []
        for _RAL in self.RALs:
            RALs_X += [_RAL.active_RA_Point[0]]
        self.Row_Mean_X = int(np.mean(RALs_X))
        
    def Get_Inter_Plant_Diffs(self):
        self.InterPlant_Diffs = []
        nb_RALs = len(self.RALs)
        if (nb_RALs > 1):
            for i in range(nb_RALs-1):
                self.InterPlant_Diffs += [abs(self.RALs[i].y - self.RALs[i+1].y)]
                
    def Get_Most_Frequent_InterPlant_Y(self):
        self.Get_Inter_Plant_Diffs()
        self.InterPlant_Y_Hist_Array = np.histogram(self.InterPlant_Diffs)
    
    def Is_RALs_majority_on_Left_to_Row_Mean(self):
        left_counter = 0
        for _RAL in self.RALs:
            if (_RAL.active_RA_Point[0] < self.Row_Mean_X):
                left_counter += 1
        
        return (left_counter/len(self.RALs) > 0.5)
    
    def Is_RALs_majority_going_up(self):
        up_counter = 0
        for _RAL in self.RALs:
            if (_RAL.active_RA_Point[1] - _RAL.y > 0):
                up_counter += 1
        
        return (up_counter/len(self.RALs) > 0.5)
    
    def ORDER_RALs_to_Correct_X(self):
        
        if (len(self.RALs)>0):
            self.Get_Row_Mean_X()
            
            majority_left = self.Is_RALs_majority_on_Left_to_Row_Mean()
        
        for _RAL in self.RALs:
            if (majority_left):
                if (_RAL.active_RA_Point[0] > self.Row_Mean_X):
                    _RAL.active_RA_Point[0] = self.Row_Mean_X
            else:
                if (_RAL.active_RA_Point[0] < self.Row_Mean_X):
                    _RAL.active_RA_Point[0] = self.Row_Mean_X
    
    def Get_Mean_Majority_Y_movement(self, _direction):
        """
        computes the average of the movement of the RALs moving in the
        majority direction.
        
        _direction (int):
            Gives the direction of the majority movement. If set to 1 then 
            majority of the RAls are going up. If set to -1 then majority of the
            RALs is going down.
        """
        majority_movement = 0
        majority_counter = 0
        for _RAL in self.RALs:
            if ( _direction * (_RAL.active_RA_Point[1] - _RAL.y) >= 0):
                majority_movement += (_RAL.active_RA_Point[1] - _RAL.y)
                majority_counter += 1
        
        self.Row_mean_Y = majority_movement/majority_counter
        
    def ORDER_RALs_to_Correct_Y(self):
        
        if (len(self.RALs)>0):
            majority_up = self.Is_RALs_majority_going_up()
            if (majority_up):
                self.Get_Mean_Majority_Y_movement(1)
            else:
                self.Get_Mean_Majority_Y_movement(-1)
        
        for _RAL in self.RALs:
            if (majority_up):
                if (_RAL.active_RA_Point[1] - _RAL.y < 0):
                    _RAL.active_RA_Point[1] = _RAL.y + self.Row_mean_Y
            else:
                if (_RAL.active_RA_Point[1] - _RAL.y > 0):
                    _RAL.active_RA_Point[1] = _RAL.y + self.Row_mean_Y
                
    def Move_RALs_to_active_points(self):
        for _RAL in self.RALs:
            _RAL.Move_Based_on_AD_Order(_RAL.active_RA_Point[0],
                                        _RAL.active_RA_Point[1])
    
    def Destroy_RALs(self, _start, _stop, _nb_RALs):
        """
        _start and stop are the indeces of the RALs to destroy so that they 
        correspond to the bounderies [_start _stop[
        """
        if (_stop < _nb_RALs):
            self.RALs = self.RALs[:_start]+self.RALs[_stop:]
        else:
            self.RALs = self.RALs[:_start]
    
    def Destroy_Low_Activity_RALs(self):
        
        i = 0
        while i < self.nb_RALs:
# =============================================================================
#             print(self.RALs[i].x, self.RALs[i].y, self.RALs[i].recorded_Decision_Score[-1])
# =============================================================================
            if (self.RALs[i].recorded_Decision_Score[-1] < 0.05):
# =============================================================================
#                 print(self.RALs[i].recorded_Decision_Score[-1])
# =============================================================================
                self.Destroy_RALs(i, i+1, self.nb_RALs)
                self.nb_RALs -= 1
            else:
                i += 1
        
    def Adapt_RALs_group_size_2(self):
        for _RAL in self.RALs:
            if (not _RAL.Fixed):
                _RAL.Manage_RAs_distribution()
                if (_RAL.Fixed):
                    self.nb_Fixed_RALs += 1
    
    def Get_RALs_Surface(self):
        for _RAL in self.RALs:
            _RAL.Compute_Surface_2()
    
    def Set_Up_RALs_Growth_Mode(self):
        for _RAL in self.RALs:
            _RAL.RAs_border_init()

class Agents_Director(object):
    """
    Agent directeur
    
    _plant_FT_pred_per_crop_rows (list of lists extracted for a JSON file):
        array containing the predicted position of plants organized by rows.
        The lists corresponding to rows contain other lists of length 2 giving 
        the predicted position of a plant under the convention [image_line, image_column]
    
    _OTSU_img_array (numpy.array):
        array containing the OSTU segmented image on which the Multi Agent System
        is working
    
    _group_size (int, optional with default value = 5):
        number of pixels layers around the leader on which we instanciate 
        reactive agents
    
    _group_step (int, optional with default value = 5):
        distance between two consecutive reactive agents
    
    _RALs_fuse_factor(float, optional with default value = 0.5):
        The proportion of the inter-plant Y distance under which we decide to
        fuse 2 RALs of a same Row Agent
    
    _RALs_fill_factor(float, optional with default value = 1.5):
        The proportion of the inter-plant Y distance above which we decide to
        fill the sapce between 2 RALs of a same Row Agent with new RALs.
    
    _field_offset (list size 2, optional with default value [0, 0]):
        the offset to apply to all the positioned agents of the simulation to
        be coherent at the field level.
    
    """
    def __init__(self, _plant_FT_pred_per_crop_rows, _OTSU_img_array,
                 _group_size = 50, _group_step = 5,
                 _RALs_fuse_factor = 0.5, _RALs_fill_factor = 1.5,
                 _field_offset = [0,0]):
        
# =============================================================================
#         print()
#         print("Initializing Agent Director class...", end = " ")
# =============================================================================
        
        self.plant_FT_pred_par_crop_rows = _plant_FT_pred_per_crop_rows
        
        self.OTSU_img_array = _OTSU_img_array
        
        self.group_size = _group_size
        self.group_step = _group_step
        
        self.RALs_fuse_factor = _RALs_fuse_factor
        self.RALs_fill_factor = _RALs_fill_factor
        
        self.field_offset = _field_offset
        
        self.RowAs = []
        
# =============================================================================
#         print("Done")
# =============================================================================

    def Initialize_RowAs(self):
        """
        Go through the predicted coordinates of the plants in self.plant_FT_pred_par_crop_rows
        and initialize the Row Agents
        """
        self.RowAs_start_x = []
        self.RowAs_start_nbRALs = []
        for _crop_row in self.plant_FT_pred_par_crop_rows:
            nb_RALs=len(_crop_row)
            if (nb_RALs > 0):
                self.RowAs_start_x += [_crop_row[0][0]]
                self.RowAs_start_nbRALs += [nb_RALs]
                RowA = Row_Agent(_crop_row, self.OTSU_img_array,
                                 self.group_size, self.group_step,
                                 self.field_offset)
                
                self.RowAs += [RowA]
    
    def Analyse_RowAs(self):
        """
        Go through the RowAs and check if some of them are not irregulars
        regarding the distance to their neighbours and the number of RALs
        """
        mean_nb_RALs = np.mean(self.RowAs_start_nbRALs)

        X_Diffs = np.diff(self.RowAs_start_x)
        X_Diffs_hist = np.histogram(X_Diffs, int(len(self.RowAs)/2))
        Low_Bounds = X_Diffs_hist[1][:2]
        print ("X_Diffs_hist", X_Diffs_hist)
        print ("Low_Bounds", Low_Bounds)
        print ("mean_nb_RALs", mean_nb_RALs)
        print ("self.RowAs_start_nbRALs", self.RowAs_start_nbRALs)
        
        nb_diffs = len(X_Diffs)
        to_delete=[]
        for i in range(nb_diffs):
            if (X_Diffs[i] >= Low_Bounds[0] and X_Diffs[i] <= Low_Bounds[1]):
                print("self.RowAs_start_nbRALs[i]", i, self.RowAs_start_nbRALs[i])
                if (self.RowAs_start_nbRALs[i]<0.5*mean_nb_RALs):
                    to_delete += [i]
                elif (self.RowAs_start_nbRALs[i+1]<0.5*mean_nb_RALs):
                    to_delete += [i+1]
        
        nb_to_delete = len(to_delete)
        for i in range(nb_to_delete):
            self.RowAs = self.RowAs[:to_delete[i]-i] + self.RowAs[to_delete[i]-i+1:]
        
        print("Rows at indeces", to_delete, "were removed")
    
    def Analyse_RowAs_Kmeans(self):
        """
        Go through the RowAs and check if some of them are not irregulars
        regarding the distance to their neighbours and the number of RALs
        """
        X_Diffs = np.diff(self.RowAs_start_x)
        print("X_Diffs",X_Diffs)
        X = np.array([[i,0] for i in X_Diffs])
# =============================================================================
#         print("X",X)
# =============================================================================
        kmeans = KMeans(n_clusters=2).fit(X)
        print("kmeans.labels_",kmeans.labels_)
        _indeces_grp0 = np.where(kmeans.labels_ == 0)
        _indeces_grp1 = np.where(kmeans.labels_ == 1)
        grp0 = X_Diffs[_indeces_grp0]
        grp1 = X_Diffs[_indeces_grp1]
# =============================================================================
#         print("grp0", grp0)
#         print("grp1", grp1)
# =============================================================================
        test_stat, p_value = ttest_ind(grp0, grp1)
        print("test_stat", test_stat, "p_value", p_value)
        means_grp = np.array([np.mean(grp0), np.mean(grp1)])
        print("mean_nb_RALs", means_grp)
        
        if (p_value < 0.0001):
            
            index_small_grp = list(np.array((_indeces_grp0,_indeces_grp1))[np.where(means_grp == min(means_grp))][0][0])
            print(index_small_grp)
            
            nb_indeces = len(index_small_grp)
            to_delete = []
            if (nb_indeces == 1):
                to_delete += [index_small_grp[0]]
            else:
                if not index_small_grp[0] == index_small_grp[1]-1:
                    to_delete += [index_small_grp[0]]
                    index_small_grp = index_small_grp[1:]
                    nb_indeces -= 1
            k = 0
            while k < nb_indeces:
                sub_indeces = []
                i = k
# =============================================================================
#                 print(index_small_grp[i], index_small_grp[i+1], index_small_grp[i] == index_small_grp[i+1]-1)
# =============================================================================
                while (i < nb_indeces-1 and 
                       index_small_grp[i] == index_small_grp[i+1]-1):
                    sub_indeces+=[index_small_grp[i], index_small_grp[i+1]]
                    i+=2
                    
                nb_sub_indeces = len(sub_indeces)               
                print("sub_indeces", sub_indeces)
                if (nb_sub_indeces%2 == 0):
                    for j in range (1,nb_sub_indeces,2):
                        to_delete += [sub_indeces[j]]
                else:
                    for j in range (0,nb_sub_indeces,2):
                        to_delete += [sub_indeces[j]]
                
                if (i>k):
                    k=i
                else:
                    k+=2
                
            print("Rows to_delete", to_delete)
            nb_to_delete = len(to_delete)
            for i in range(nb_to_delete):
                self.RowAs = self.RowAs[:to_delete[i]-i] + self.RowAs[to_delete[i]-i+1:]
            
    def ORDER_RowAs_for_RALs_mean_points(self):
        for _RowA in self.RowAs:#[10:11]:
            _RowA.Get_RALs_mean_points()
    
    def ORDER_RowAs_to_Correct_RALs_X(self):
        for _RowA in self.RowAs:#[10:11]:
            _RowA.ORDER_RALs_to_Correct_X()
    
    def ORDER_RowAs_to_Correct_RALs_Y(self):
        for _RowA in self.RowAs:
            _RowA.ORDER_RALs_to_Correct_Y()
    
    def ORDER_RowAs_to_Update_InterPlant_Y(self):
        for _RowA in self.RowAs:#[10:11]:
            _RowA.Get_Most_Frequent_InterPlant_Y()
                
    def ORDER_RowAs_for_Moving_RALs_to_active_points(self):
        for _RowA in self.RowAs:#[10:11]:
            _RowA.Move_RALs_to_active_points()
    
    def Summarize_RowAs_InterPlant_Y(self):
        SumNbs = np.zeros(10, dtype=np.int32)
        SumBins = np.zeros(11)
        for _RowA in self.RowAs:#[10:11]:
            SumNbs += _RowA.InterPlant_Y_Hist_Array[0]
            SumBins += _RowA.InterPlant_Y_Hist_Array[1]
        SumBins /= len(self.RowAs)#[10:11])
        
        print("max of SumNbs", SumNbs, np.max(SumNbs))
        print("index of max for SumBins", np.where(SumNbs == np.max(SumNbs)))
        print("SumBins", SumBins)
        max_index = np.where(SumNbs == np.max(SumNbs))[0]
        if(max_index.shape[0]>1):
            max_index = max_index[:1]
        print("max_index", max_index)
        self.InterPlant_Y = int(SumBins[max_index][0])
        print("InterPlant_Y before potential correction", self.InterPlant_Y)
        while (max_index < 10 and self.InterPlant_Y < 5):
            max_index += 1
            self.InterPlant_Y = int(SumBins[max_index])
            print("Correcting InterPlant_Y", self.InterPlant_Y)
    
    def ORDER_RowAs_Fill_or_Fuse_RALs(self):
        for _RowA in self.RowAs:
            _RowA.Fill_or_Fuse_RALs(self.InterPlant_Y,
                                    self.RALs_fuse_factor,
                                    self.RALs_fill_factor)
    
    def ORDER_RowAs_to_Destroy_Low_Activity_RALs(self):
        for _RowA in self.RowAs:#[10:11]:
            _RowA.Destroy_Low_Activity_RALs()
    
    def ORDER_RowAs_to_Adapt_RALs_sizes(self):
        for _RowA in self.RowAs:#[10:11]:
            #_RowA.Adapt_RALs_group_size()
            _RowA.Adapt_RALs_group_size_2()
    
    def ORDER_RowAs_for_Extensive_RALs_Init(self):
        for _RowA in self.RowAs:#[10:11]:
            _RowA.Extensive_Init(1.1*self.RALs_fuse_factor*self.InterPlant_Y)
    
    def ORDER_RowAs_for_Edges_Exploration(self):
        for _RowA in self.RowAs:#[10:11]:
            _RowA.Edge_Exploration(1.1*self.RALs_fuse_factor*self.InterPlant_Y)
    
    def Check_RowAs_Proximity(self):
        nb_Rows = len(self.RowAs)
        i=0
        while i < nb_Rows-1:
            if (abs(self.RowAs[i].Row_Mean_X-self.RowAs[i+1].Row_Mean_X) < self.group_size):
                
                new_plant_FT = self.RowAs[i].plant_FT_pred_in_crop_row + self.RowAs[i].plant_FT_pred_in_crop_row
                new_plant_FT.sort()
            
                RowA = Row_Agent(new_plant_FT,
                                 self.OTSU_img_array,
                                 self.group_size,
                                 self.group_step,
                                 self.field_offset)
                if (i<nb_Rows-2):
                    self.RowAs = self.RowAs[:i]+ [RowA] + self.RowAs[i+2:]
                else:
                    self.RowAs = self.RowAs[:i]+ [RowA]
                i+=2
                nb_Rows-=1
            else:
                i+=1
    
    def ORDER_RowAs_for_RALs_Surface_Compute(self):
        for _RowA in self.RowAs:
            _RowA.Get_RALs_Surface()
                
    def ORDER_Check_RALs_Exploration(self):
        for _RowA in self.RowAs:
            _RowA.Check_RALs_Exploration()
                
    def Count_nb_Fixed_RAL(self):
        nb_fixed = 0
        for _RowA in self.RowAs:
            nb_fixed += _RowA.nb_Fixed_RALs
        return nb_fixed
    
    def Switch_From_Search_To_Growth(self):
        for _RowA in self.RowAs:
            _RowA.Set_Up_RALs_Growth_Mode()
# =============================================================================
# Simulation Definition
# =============================================================================
class Simulation_MAS(object):
    """
    This class manages the multi agent simulation on an image.
    In particular, it instanciate the Agent Director of an image, controls the 
    flow of the simulation (start, stop, step), and rthe results visualization
    associated.
    
    _RAW_img_array (numpy.array):
        array containing the raw RGB image. This would be mostly used for results
        visualization.
    
    _plant_FT_pred_per_crop_rows (list of lists extracted for a JSON file):
        array containing the predicted position of plants organized by rows.
        The lists corresponding to rows contain other lists of length 2 giving 
        the predicted position of a plant under the convention [image_line, image_column]
    
    _OTSU_img_array (numpy.array):
        array containing the OSTU segmented image on which the Multi Agent System
        is working
    
    _group_size (int, optional with default value = 5):
        number of pixels layers around the leader on which we instanciate 
        reactive agents
    
    _group_step (int, optional with default value = 5):
        distance between two consecutive reactive agents
    
    _RALs_fuse_factor(float, optional with default value = 0.5):
        The proportion of the inter-plant Y distance under which we decide to
        fuse 2 RALs of a same Row Agent
    
    _RALs_fill_factor(float, optional with default value = 1.5):
        The proportion of the inter-plant Y distance above which we decide to
        fill the sapce between 2 RALs of a same Row Agent with new RALs.
    
    _field_offset (list size 2, optional with default value [0, 0]):
        the offset to apply to all the positioned agents of the simulation to
        be coherent at the field level.
    
    _ADJUSTED_img_plant_positions (list, optional with default value = None):
        The list containing the adjusted positions of the plants coming from
        the csv files. So the positions are still in the string format.
    
    _follow_simulation (bool, optional with default value = False):
        Generates the plot showing all RALs and target positions at every steps
        of the simulation to follow the movements and theevolution of the number
        RALs
    
    _follow_simulation_save_path(string, optional with default value ""):
        The path where the plots following the steps of the simulation will be 
        saved.
    
    _simulation_name (string, optional with default value = ""):
        Name given to the simulation. used as a prefix of the some saved files.
    
    """
    
    def __init__(self, _RAW_img_array,
                 _plant_FT_pred_per_crop_rows, _OTSU_img_array, 
                 _group_size = 50, _group_step = 5,
                 _RALs_fuse_factor = 0.5, _RALs_fill_factor = 1.5,
                 _field_offset = [0,0],
                 _ADJUSTED_img_plant_positions = None,
                 _follow_simulation = False,
                 _follow_simulation_save_path = "",
                 _simulation_name = ""):
        
        print("Initializing Simulation class...", end = " ")
        
        self.RAW_img_array = _RAW_img_array
        
        self.plant_FT_pred_par_crop_rows = _plant_FT_pred_per_crop_rows
        
        self.OTSU_img_array = _OTSU_img_array        
        
        self.group_size = _group_size
        self.group_step = _group_step
        
        self.RALs_fuse_factor = _RALs_fuse_factor
        self.RALs_fill_factor = _RALs_fill_factor
        
        self.ADJUSTED_img_plant_positions = _ADJUSTED_img_plant_positions
        if (self.ADJUSTED_img_plant_positions != None):
            self.Correct_Adjusted_plant_positions()
            self.labelled=True
        else:
            self.labelled=False
            
        self.field_offset = _field_offset
        
        self.simu_steps_times = []
        self.simu_steps_time_detailed=[]
        self.RALs_recorded_count = []
        self.nb_real_plants=0
        self.TP=0
        self.FP=0
        self.FN=0
        self.real_plant_detected_keys = []
        
        print("Done")
        
        self.follow_simulation = _follow_simulation
        if (_follow_simulation):
            self.follow_simulation_save_path = _follow_simulation_save_path
            gIO.check_make_directory(self.follow_simulation_save_path)
            
        self.simulation_name = _simulation_name
        
    def Initialize_AD(self):
        self.AD = Agents_Director(self.plant_FT_pred_par_crop_rows,
                             self.OTSU_img_array,
                             self.group_size, self.group_step,
                             self.RALs_fuse_factor, self.RALs_fill_factor,
                             self.field_offset)
        self.AD.Initialize_RowAs()
    
    def Perform_Search_Simulation(self, _steps = 10,
                                  _coerced_X = False,
                                  _coerced_Y = False,
                                  _analyse_and_remove_Rows = False,
                                  _edge_exploration = False):
        print()
        print("Starting Search Simulation:")
        self.steps = _steps
        self.max_steps_reached = False
        
        if (_analyse_and_remove_Rows):
            self.AD.Analyse_RowAs_Kmeans()
        
        self.AD.ORDER_RowAs_to_Update_InterPlant_Y()
        self.AD.Summarize_RowAs_InterPlant_Y()
        
        self.search_simulation = True
        self.growth_simulation = False
        
        if (self.follow_simulation):
                self.Show_Adjusted_And_RALs_positions(_save=True,
                                                      _save_name=self.simulation_name+"_A")
        
        if (_edge_exploration):
            self.AD.ORDER_RowAs_for_Edges_Exploration()
            if (self.follow_simulation):
                self.Show_Adjusted_And_RALs_positions(_save=True,
                                                      _save_name=self.simulation_name+"_B")
        
        self.AD.ORDER_RowAs_to_Update_InterPlant_Y()
        
        self.Count_RALs()
        
        stop_simu = False
        re_eval = False
        diff_nb_RALs = -1
        i = 0
        while i < self.steps and not stop_simu:
            print("Simulation step {0}/{1} (max)".format(i+1, _steps))
                        
            time_detailed=[]
            t0 = time.time()
            
            self.AD.ORDER_RowAs_for_RALs_mean_points()
            time_detailed += [time.time()-t0]
            
            if (_coerced_X):
                t0 = time.time()
                self.AD.ORDER_RowAs_to_Correct_RALs_X()
                time_detailed += [time.time()-t0]
            else:
                time_detailed += [0]
                
            if (_coerced_Y):
                t0 = time.time()
                self.AD.ORDER_RowAs_to_Correct_RALs_Y()
                time_detailed += [time.time()-t0]
            else:
                time_detailed += [0]
            
            t0 = time.time()
            self.AD.ORDER_RowAs_for_Moving_RALs_to_active_points()
            time_detailed += [time.time()-t0]
            
# =============================================================================
#             if (self.follow_simulation):
#                 self.Show_Adjusted_And_RALs_positions(_save=True,
#                                                       _save_name=self.simulation_name+"_C_{0}_1".format(i+1))
# =============================================================================
            
# =============================================================================
#             t0 = time.time()
#             self.AD.ORDER_RowAs_to_Adapt_RALs_sizes()
#             time_detailed += [time.time()-t0]
#             
#             if (self.follow_simulation):
#                 self.Show_Adjusted_And_RALs_positions(_save=True,
#                                                       _save_name=self.simulation_name+"_C_{0}_2".format(i+1))
# =============================================================================
            
            t0 = time.time()
            self.AD.ORDER_RowAs_Fill_or_Fuse_RALs()
            time_detailed += [time.time()-t0]
            
# =============================================================================
#             if (self.follow_simulation):
#                 self.Show_Adjusted_And_RALs_positions(_save=True,
#                                                       _save_name=self.simulation_name+"_C_{0}_3".format(i+1))
# =============================================================================
            
            t0 = time.time()
            self.AD.ORDER_RowAs_to_Destroy_Low_Activity_RALs()
            time_detailed += [time.time()-t0]
            
            if (self.follow_simulation):
                self.Show_Adjusted_And_RALs_positions(_save=True,
                                                      _save_name=self.simulation_name+"_C_{0}_4".format(i+1))
            
            t0 = time.time()
            self.AD.Check_RowAs_Proximity()
            time_detailed += [time.time()-t0]
            
            t0 = time.time()
            self.AD.ORDER_RowAs_to_Update_InterPlant_Y()
            time_detailed += [time.time()-t0]
            
            self.simu_steps_time_detailed += [time_detailed]
            self.simu_steps_times += [np.sum(time_detailed)]
            
            self.Count_RALs()
            
            diff_nb_RALs = self.RALs_recorded_count[-1] - self.RALs_recorded_count[-2]
            
            
            
            if (diff_nb_RALs == 0):
                if not re_eval:
                    self.AD.Summarize_RowAs_InterPlant_Y()
                    re_eval = True
                else:
                    stop_simu = True
            else:
                re_eval = False
            
            i += 1
        
        #self.AD.ORDER_RowAs_for_RALs_Surface_Compute()
        
        if (i == self.steps):
            self.max_steps_reached = True
            print("Search simulation Finished with max steps reached.")
        else:
            print("Search simulation Finished")
    
    def Perform_Growth_Simulation(self, _steps = 10,
                                      _coerced_X = False,
                                      _coerced_Y = False,
                                      _analyse_and_remove_Rows = False,
                                      _edge_exploration = False):
        print()
        print("Starting Growth Simulation:")
        self.AD.Switch_From_Search_To_Growth()
        
        self.steps = _steps
        self.max_steps_reached = False
        
        self.search_simulation = False
        self.growth_simulation = True
        
        if (self.follow_simulation):
                self.Show_Adjusted_And_RALs_positions(_save=True,
                                                      _save_name=self.simulation_name+"_D")
        
        stop_simu = False
        i = 0
        while i < self.steps and not stop_simu:
            print("Simulation step {0}/{1} (max)".format(i+1, _steps))
            
            self.AD.ORDER_RowAs_to_Adapt_RALs_sizes()
            
# =============================================================================
#             if (self.follow_simulation):
#                 self.Show_Adjusted_And_RALs_positions(_save=True,
#                                                       _save_name=self.simulation_name+"_E_{0}_2".format(i+1))
# =============================================================================
                
            self.AD.ORDER_Check_RALs_Exploration()
            
            if (self.follow_simulation):
                self.Show_Adjusted_And_RALs_positions(_save=True,
                                                      _save_name=self.simulation_name+"_E_{0}_3".format(i+1)) 
            
            nb_fixed = self.AD.Count_nb_Fixed_RAL()
            
            print("Proportion of fixed RAs:", nb_fixed/self.RALs_recorded_count[-1])
            if (nb_fixed/self.RALs_recorded_count[-1] == 1):
                stop_simu = True
            
            i += 1
        
        self.AD.ORDER_RowAs_for_RALs_Surface_Compute()
        
        if (i == self.steps):
            self.max_steps_reached = True
            print("Growth simulation Finished with max steps reached.")
        else:
            print("Growth simulation Finished")
    
    def Correct_Adjusted_plant_positions(self):
        """
        Transform the plants position at the string format to integer.
        Also correct the vertical positions relatively to the image ploting origin.
        """
        self.corrected_adjusted_plant_positions = []
        self.real_plant_keys = []
        for adj_pos_string in self.ADJUSTED_img_plant_positions:
            self.corrected_adjusted_plant_positions += [[int(adj_pos_string["rotated_x"]),
                                                        int(adj_pos_string["rotated_y"])]]#self.OTSU_img_array.shape[0]-
            self.real_plant_keys += [str(adj_pos_string["instance_id"])]
        
    def Count_RALs(self):
        RALs_Count = 0
        for _RowA in self.AD.RowAs:
            RALs_Count += _RowA.nb_RALs
        self.RALs_recorded_count += [RALs_Count]
    
    def Is_Plant_in_RAL_scanning_zone(self, _plant_pos, _RAL):
        """
        Computes if the position of a labelled plant is within the area of the 
        image where RAs are spawn under the RAL command.
        """
        res = False
        if (abs(_plant_pos[0] - _RAL.x) <= _RAL.group_size and
            abs(_plant_pos[1] - _RAL.y) <= _RAL.group_size):
                res = True
        return res
    
    def Get_RALs_infos(self):
        """
        Returns the dictionnay that will contains the information relative to 
        RALs
        """
        self.RALs_dict_infos = {}
        self.RALs_nested_positions=[]
        for _RowA in self.AD.RowAs:
            _row = []
            for _RAL in _RowA.RALs:          
                _row.append([int(_RAL.x), int(_RAL.y)])
                self.RALs_dict_infos[str(_RAL.x) + "_" + str(_RAL.y)] = {
                "field_recorded_positions" : _RAL.field_recorded_positions,
                 "recorded_positions" : _RAL.recorded_positions,
                 "RAs_Local_Positions" : _RAL.RAs_local_positions,
                 "detected_plant" : "",
                 "RAL_group_size": _RAL.group_size,
                 "RAL_area": _RAL.area}
            self.RALs_nested_positions+=[_row]
        print()
        
    def Compute_Scores(self):
        """
        Computes :
            True positives (labelled plants with a RAL near it)
            False positives (RAL positioned far from a labelled plant)
            False negatives (labelled plant with no RAL near it)
        """
        associated_RAL = 0
        self.nb_real_plants = len(self.corrected_adjusted_plant_positions)
        for i in range(self.nb_real_plants):
            
            TP_found = False
            for _RowA in self.AD.RowAs:
                for _RAL in _RowA.RALs:
                    if (self.Is_Plant_in_RAL_scanning_zone(self.corrected_adjusted_plant_positions[i], _RAL)):
                        if not TP_found:
                            self.TP += 1
                            TP_found = True
                            self.RALs_dict_infos[str(_RAL.x) + "_" + str(_RAL.y)][
                                    "detected_plant"]=self.real_plant_keys[i]
                            self.real_plant_detected_keys += [self.real_plant_keys[i]]
                        associated_RAL += 1
        
        self.FN = len(self.ADJUSTED_img_plant_positions) - self.TP
        self.FP = self.RALs_recorded_count[-1] - associated_RAL
    
    def Show_RALs_Position(self,
                           _ax = None,
                           _colors = 'g'):
        """
        Display the Otsu image with overlaying rectangles centered on RALs. The
        size of the rectangle corespond to the area covered by the RAs under the 
        RALs supervision.
        
        _ax (matplotlib.pyplot.axes, optional):
            The axes of an image on which we wish to draw the adjusted 
            position of the plants
        
        _recorded_position_indeces (optional,list of int):
            indeces of the recored positions of the RALs we wish to see. By defaullt,
            the first and last one
        
        _colors (optional,list of color references):
            Colors of the rectangles ordered indentically to the recorded positons
            of interest. By default red for the first and green for the last 
            recorded position.
        """
        
        if (_ax == None):
            fig, ax = plt.subplots(1)
            ax.imshow(self.OTSU_img_array)
        else:
            ax = _ax
        
        for _RowsA in self.AD.RowAs:
            
            for _RAL in _RowsA.RALs:
                
                if (self.search_simulation and not self.growth_simulation):
                    #coordinates are the upper left corner of the rectangle
                    rect = patches.Rectangle((_RAL.x+_RAL.Borders_Distance[3],
                                              _RAL.y+_RAL.Borders_Distance[1]),
                                             #2*_RAL.group_size,2*_RAL.group_size,
                                             _RAL.Borders_Distance[2]+abs(_RAL.Borders_Distance[3]),
                                             _RAL.Borders_Distance[0]+abs(_RAL.Borders_Distance[1]),
                                             linewidth=1,
                                             edgecolor=_colors,
                                             facecolor='none')
                    ax.add_patch(rect)
                
                if (not self.search_simulation and self.growth_simulation):
                    _c = ["red", "orange", "purple", "cyan"]
                    for i in range(4):
                        x = []
                        y = []
                        for _RA in _RAL.RA_list_card[i]:
                            x += [_RA.global_x]
                            y += [_RA.global_y]
                        plt.plot(x, y, color=_c[i], linewidth=1, markersize = 1)#, marker="o")
        
        plt.xlim(170, 270)
        plt.ylim(1350, 1450)
        
                
    def Show_Adjusted_Positions(self, _ax = None, _color = "b"):
        """
        Display the adjusted positions of the plants.
        This is considered as the ground truth.
        
        _ax (matplotlib.pyplot.axes, optional):
            The axes of an image on which we wish to draw the adjusted 
            position of the plants
        
        _color (string):
            color of the circles designating the plants
        """
        if (_ax == None):
            fig, ax = plt.subplots(1)
            ax.imshow(self.OTSU_img_array)
        else:
            ax = _ax
        
        for [x,y] in self.corrected_adjusted_plant_positions:
            circle = patches.Circle((x,y),
                                    radius = 10,
                                    linewidth = 2,
                                    edgecolor = None,
                                    facecolor = _color)
            ax.add_patch(circle)
    
    def Show_Adjusted_And_RALs_positions(self,
                                        _recorded_position_indeces = -1,
                                        _colors_recorded = 'g',
                                        _color_adjusted = "r",
                                        _save=False,
                                        _save_name=""):
        
        fig = plt.figure(figsize=(5,5),dpi=300)
        ax = fig.add_subplot(111)
        ax.imshow(self.OTSU_img_array)
        
        self.Show_RALs_Position(_ax = ax,
                                _colors = _colors_recorded)
# =============================================================================
#         self.Show_Adjusted_Positions(_ax = ax,
#                                      _color = _color_adjusted)
# =============================================================================
        
        if (_save):
            fig.savefig(self.follow_simulation_save_path+"/"+_save_name)
            plt.close()
            #pass
    
    def Show_RALs_Deicision_Scores(self):
        """
        Plot the Evolution of the decision score of each RALs in the simulation
        """
        
        fig = plt.figure()
        ax = fig.add_subplot(111)
        for _RowsA in self.AD.RowAs:
            for _RAL in _RowsA.RALs:
                ax.plot([i for i in range (len(_RAL.recorded_Decision_Score))],
                         _RAL.recorded_Decision_Score, marker = "o")
    
    def Show_nb_RALs(self):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot([i for i in range (len(self.RALs_recorded_count))],
                         self.RALs_recorded_count, marker = "o")

class MetaSimulation(object):
    """
    This class manages the multi agent simulations on a list of images.
    In particular, it concentrates the information needed to make batches of
    tests and compare the results.
    We want to be able to compare the time of the simulations, the confusion
    matrix
    
    _simu_name (string):
        Name of the meta simulation to be used for results files reference.
    
    _path_output (string):
        The root directory where the results associated to the Meta simulation
        will be saved.
    
    _names_input_raw(list):
        _names of the images loaded in the _data_input_raw list
    
    _data_input_raw (list):
        The list of arrays containing the raw RGB images.
        This would be mostly used for results visualization.
    
    _data_input_PLANT_FT_PRED (list):
        The list of arrays containing the predicted positions of plants
        organized by rows.
        The lists corresponding to rows contain other lists of length 2 giving 
        the predicted position of a plant under the convention
        [image_line, image_column].
    
    _data_input_OTSU (list):
        The list of arrays containing the OSTU segmented image on which the
        Multi Agent System is working.
    
    _group_size (int, optional with default value = 5):
        number of pixels layers around the leader on which we instanciate 
        reactive agents.
    
    _group_step (int, optional with default value = 5):
        distance between two consecutive reactive agents.
    
    _RALs_fuse_factor (float, optional with default value = 0.5):
        The proportion of the inter-plant Y distance under which we decide to
        fuse 2 RALs of a same Row Agent.
    
    _RALs_fill_factor (float, optional with default value = 1.5):
        The proportion of the inter-plant Y distance above which we decide to
        fill the sapce between 2 RALs of a same Row Agent with new RALs.
        
    _simulation_step (int, optional with default value = 10):
        Max number of steps for each MAS simulations.
    
    _data_position_files (list, optional with default value = None):
        The list containing the adjusted positions of the plants coming from
        the csv files. So the positions are still in the string format.
        
    _field_shape (tuple, optional with default value = (2,2)):
        defines the number of images per rows and columns (first and second
        position respectively) that the drone captured from the field 
    """
    
    def __init__(self,
                 _simu_name,
                 _path_output,
                 _names_input_raw,
                 _data_input_raw,
                 _data_input_PLANT_FT_PRED,
                 _data_input_OTSU,
                 _group_size, _group_step,
                 _RALs_fuse_factor, _RALs_fill_factor,
                 _simulation_step = 10,
                 _data_adjusted_position_files = None,
                 _field_shape = (2,2)):
        
        self.simu_name = _simu_name
        
        self.path_output = _path_output
        
        self.names_input_raw = _names_input_raw
        
        self.data_input_raw = _data_input_raw
        self.nb_images = len(self.data_input_raw)
        
        self.data_input_PLANT_FT_PRED = _data_input_PLANT_FT_PRED
        self.data_input_OTSU = _data_input_OTSU
        
        self.group_size = _group_size
        self.group_step = _group_step
        
        self.RALs_fuse_factor = _RALs_fuse_factor
        self.RALs_fill_factor = _RALs_fill_factor
        
        self.simulation_step = _simulation_step
        
        self.data_adjusted_position_files = _data_adjusted_position_files
        
        self.meta_simulation_results = {}
        self.whole_field_counted_plants = {}
        self.RALs_data = {}
        self.RALs_all_nested_positions=[]
        if (self.data_adjusted_position_files != None):
            self.Initialize_Whole_Field_Counted_Plants()
        
        self.field_shape = _field_shape
        
        self.check_data()
    
    def check_data(self):
        """
        Checks that the input data lists have the same length as the _data_input_raw
        
        """
        
        for _data in [self.data_input_OTSU,
                      self.data_input_PLANT_FT_PRED]:
            assert len(_data) == self.nb_images
    
        if (self.data_adjusted_position_files != None):
            assert len(self.data_adjusted_position_files) == self.nb_images
    
    def Get_Field_Assembling_Offsets(self):
        
        origin_shape = np.array([self.data_input_raw[0].shape[1],
                                  self.data_input_raw[0].shape[0]])
        Otsu_shape = np.array([self.data_input_OTSU[0].shape[1],
                                  self.data_input_OTSU[0].shape[0]])
        
        p1 = np.array([self.data_input_raw[0].shape[1],
                       0.5 * self.data_input_raw[0].shape[0]])
        p2 = np.array([0.5 * self.data_input_raw[0].shape[1],
                       self.data_input_raw[0].shape[0]])
        pivot = np.array([0.5 * self.data_input_raw[0].shape[1],
                          0.5 * self.data_input_raw[0].shape[0]])
        
        R = rotation_matrix(np.deg2rad(80))
        
        print(p1, p2, pivot, R)
            
        right_offset = rotate_coord(p1, pivot, R) - 0.5*origin_shape
        up_offset = rotate_coord(p2, pivot, R) - 0.5* origin_shape
        print(right_offset, up_offset)
        
        self.all_offsets = []
        forward=True
        for i in range (self.field_shape[0]):
            if (forward):
                _start = 0
                _stop = self.field_shape[1]
                _step = 1
            else:
                _start = self.field_shape[1]-1
                _stop = -1
                _step = -1
            
            for j in range (_start, _stop, _step):
                new_offset = i * right_offset + j * up_offset
                self.all_offsets.append([int(new_offset[0]),
                                         int(Otsu_shape[1]-new_offset[1])])
            
            forward = not forward
        
        print("all offsets=", self.all_offsets)       
    
    def Launch_Meta_Simu_Labels(self,
                             _coerced_X = False,
                             _coerced_Y = False,
                             _analyse_and_remove_Rows = False,
                             _rows_edges_exploration = False):

        """
        Launch an MAS simulation for each images. The raw images are labelled.
        """
        
        self.log = []
        
        self.coerced_X = _coerced_X
        self.coerced_Y = _coerced_Y
        self.analyse_and_remove_Rows = _analyse_and_remove_Rows
        self.rows_edges_exploration = _rows_edges_exploration
        
# =============================================================================
#         if (self.nb_images > 1):
#             self.Get_Field_Assembling_Offsets()
#         else:
#             self.all_offsets=[[0,0]]
# =============================================================================
        
        for i in range(self.nb_images):
            
            print()
            print("Simulation Definition for image {0}/{1}".format(i+1, self.nb_images) )
            
            try:
                MAS_Simulation = Simulation_MAS(
                                        self.data_input_raw[i],
                                        self.data_input_PLANT_FT_PRED[i],
                                        self.data_input_OTSU[i],
                                        self.group_size, self.group_step,
                                        self.RALs_fuse_factor, self.RALs_fill_factor,
                                        [0,0],
                                        self.data_adjusted_position_files[i])
                MAS_Simulation.Initialize_AD()
                
                MAS_Simulation.Perform_Search_Simulation(self.simulation_step,
                                                                  self.coerced_X,
                                                                  self.coerced_Y,
                                                                  self.analyse_and_remove_Rows,
                                                                  self.rows_edges_exploration)
                MAS_Simulation.Perform_Growth_Simulation(self.simulation_step,
                                                                  self.coerced_X,
                                                                  self.coerced_Y,
                                                                  self.analyse_and_remove_Rows,
                                                                  self.rows_edges_exploration)
                
                MAS_Simulation.Get_RALs_infos()
                self.Add_Simulation_Results(i, MAS_Simulation)
                self.Add_Whole_Field_Results(MAS_Simulation)
                if (MAS_Simulation.max_steps_reached):
                    self.log += ["Simulation for image {0}/{1}, named {2} reached max number of allowed steps".format(
                        i+1, self.nb_images, self.names_input_raw[i])]
            
            except:
                print("Failure")
                self.log += ["Simulation for image {0}/{1}, named {2} failed".format(
                        i+1, self.nb_images, self.names_input_raw[i])]
                raise
        
        self.Save_MetaSimulation_Results()
        self.Save_RALs_Infos()
        self.Save_Whole_Field_Results()
        self.Save_RALs_Nested_Positions()
        self.Save_Log()
        
    def Launch_Meta_Simu_NoLabels(self,
                             _coerced_X = False,
                             _coerced_Y = False,
                             _analyse_and_remove_Rows = False,
                             _rows_edges_exploration = False):

        """
        Launch an MAS simulation for each images. The raw images are NOT labelled.
,        """
        
        self.log = []
        
        self.coerced_X = _coerced_X
        self.coerced_Y = _coerced_Y
        self.analyse_and_remove_Rows = _analyse_and_remove_Rows
        self.rows_edges_exploration = _rows_edges_exploration
        
# =============================================================================
#         if (self.nb_images > 1):
#             self.Get_Field_Assembling_Offsets()
#         else:
#             self.all_offsets=[[0,0] for i in range(self.nb_images)]
# =============================================================================
        
        for i in range(self.nb_images):
            
            print()
            print("Simulation Definition for image {0}/{1}".format(i+1, self.nb_images))
            
            try:
                MAS_Simulation = Simulation_MAS(
                                        self.data_input_raw[i],
                                        self.data_input_PLANT_FT_PRED[i],
                                        self.data_input_OTSU[i],
                                        self.group_size, self.group_step,
                                        self.RALs_fuse_factor, self.RALs_fill_factor,
                                        [0,0],
                                        self.data_adjusted_position_files)
                MAS_Simulation.Initialize_AD()
                
                MAS_Simulation.Perform_Search_Simulation(self.simulation_step,
                                                                  self.coerced_X,
                                                                  self.coerced_Y,
                                                                  self.analyse_and_remove_Rows,
                                                                  self.rows_edges_exploration)
                
                MAS_Simulation.Get_RALs_infos()
                self.Add_Simulation_Results(i, MAS_Simulation)
                if (MAS_Simulation.max_steps_reached):
                    self.log += ["Simulation for image {0}/{1}, named {2} reached max number of allowed steps".format(
                        i+1, self.nb_images, self.names_input_raw[i])]
            
            except:
                print("Failure")
                self.log += ["Simulation for image {0}/{1}, named {2} failed".format(
                        i+1, self.nb_images, self.names_input_raw[i])]
                raise
        
        self.Save_MetaSimulation_Results()
        self.Save_RALs_Infos()
        self.Save_RALs_Nested_Positions()
        self.Save_Log()

    def Get_Simulation_Results(self, _MAS_Simulation):
        
        """
        Gathers the general simulation results
        """
        
        if (self.data_adjusted_position_files != None):
            print("Computing Scores by comparing to the labellisation...", end = " ")
            _MAS_Simulation.Compute_Scores()
            print("Done")
        
        data = {"Time_per_steps": _MAS_Simulation.simu_steps_times,
                "Time_per_steps_details": _MAS_Simulation.simu_steps_time_detailed,
                "Image_Labelled": _MAS_Simulation.labelled,
                "NB_labelled_plants": _MAS_Simulation.nb_real_plants,
                "NB_RALs" : _MAS_Simulation.RALs_recorded_count[-1],
                "TP" : _MAS_Simulation.TP,
                "FN" : _MAS_Simulation.FN,
                "FP" : _MAS_Simulation.FP,
                "InterPlantDistance": _MAS_Simulation.AD.InterPlant_Y,
                "RAL_Fuse_Factor": _MAS_Simulation.RALs_fuse_factor,
                "RALs_fill_factor": _MAS_Simulation.RALs_fill_factor,
                "RALs_recorded_count": _MAS_Simulation.RALs_recorded_count}
        
        print(_MAS_Simulation.simu_steps_times)
        print("NB Rals =", _MAS_Simulation.RALs_recorded_count[-1])
        print("Image Labelled = ", _MAS_Simulation.labelled)
        print("NB_labelled_plants", _MAS_Simulation.nb_real_plants)
        print("TP =", _MAS_Simulation.TP)
        print("FN =", _MAS_Simulation.FN)
        print("FP =", _MAS_Simulation.FP)
        
        return data
    
    def Initialize_Whole_Field_Counted_Plants(self):
        """
        Initialize the keys of the dictionnary self.whole_field_counted_plants
        """
        for i in range (self.nb_images):
            for adj_pos_string in self.data_adjusted_position_files[i]:
                #[_rx, _ry, x, y] = adj_pos_string.split(",")
                self.whole_field_counted_plants[str(adj_pos_string["instance_id"])]=0
    
    def Add_Simulation_Results(self, _image_index, _MAS_Simulation):
        """
        Add the detection results of a MAS simulation to the 
        meta_simulation_results dictionary as well as the RALs information.
        """
        
        data = self.Get_Simulation_Results(_MAS_Simulation)
        self.meta_simulation_results[self.names_input_raw[_image_index]] = data
        
        self.RALs_data[self.names_input_raw[_image_index]] = _MAS_Simulation.RALs_dict_infos
        self.RALs_all_nested_positions.append(_MAS_Simulation.RALs_nested_positions)
    
    def Add_Whole_Field_Results(self, _MAS_Simulation):
        """
        Retrieves the real x_y coordinates of the plants that were detected in the
        simulation and fills the dictionary self.whole_field_counted_plants
        """
        for _key in _MAS_Simulation.real_plant_detected_keys:
            self.whole_field_counted_plants[_key] += 1
    
    def Make_File_Name(self, _base):
        """
        build generic names depending on the options of the simulation
        """
        _name = _base
        if (self.coerced_X):
            _name+= "_cX"
        if (self.coerced_Y):
            _name+= "_cY"
        if (self.analyse_and_remove_Rows):
            _name+="_anrR2"
        if (self.rows_edges_exploration):
            _name+="_REE"
        return _name
    
    def Save_MetaSimulation_Results(self):
        """
        saves the results of the MAS simulations stored in the 
        meta_simulation_results dictionary as a JSON file.
        """
        name = self.Make_File_Name("MetaSimulationResults_"+self.simu_name)
        
        file = open(self.path_output+"/"+name+".json", "w")
        json.dump(self.meta_simulation_results, file, indent = 3)
        file.close()
    
    def Save_RALs_Infos(self):
        """
        saves the results of the MAS simulations stored in the 
        meta_simulation_results dictionary as a JSON file.
        """
        name = self.Make_File_Name("RALs_Infos_"+self.simu_name)
        file = open(self.path_output+"/"+name+".json", "w")
        json.dump(self.RALs_data, file, indent = 2)
        file.close()
    
    def Save_RALs_Nested_Positions(self):
        """
        saves all the RALs position on the image. It makes one json file per
        image. The json file is in the exact same format as The plant predictions
        on
        """
        name = self.Make_File_Name("RALs_NestedPositions_"+self.simu_name)
        _path=self.path_output+"/RALs_NestedPositions"
        gIO.check_make_directory(_path)
        counter = 0
        for _nested_pos in self.RALs_all_nested_positions:
            name = self.names_input_raw[counter].split(".")[0]+"NestedPositions"
            file = open(_path+"/"+name+".json", "w")
            json.dump(_nested_pos, file, indent = 2)
            file.close()
            counter+=1
    
    def Save_Whole_Field_Results(self):
        """
        saves the results of the MAS simulations stored in the 
        whole_field_counted_plants dictionary as a JSON file.
        """
        name = self.Make_File_Name("WholeFieldResults_"+self.simu_name)
        file = open(self.path_output+"/"+name+".json", "w")
        json.dump(self.whole_field_counted_plants, file, indent = 2)
        file.close()
    
    def Save_Log(self):
        name = self.Make_File_Name("LOG_MetaSimulationResults_"+self.simu_name)
        gIO.writer(self.path_output, name+".txt", self.log, True, True)
        
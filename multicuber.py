#!/usr/bin/env python3

from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, SpeedDPS
from pprint import pformat
from subprocess import check_output
from time import sleep
import json
import logging
import os
import signal
import sys
import time
import socket

log = logging.getLogger(__name__)

class Cuber2x(object):
    

    #Elevator Variables
    elevator_speed_up_fast = 300
    elevator_speed_up_slow = 300
    elevator_speed_down_fast = 150
    elevator_speed_down_slow = 150
    
    elevator_final_pos = 0

    elevate_2x2_fully = -570
    elevate_2x2_1_row = -450

    elevate_3x3_fully = -550
    elevate_3x3_1_row = -380
    elevate_3x3_2_rows = -480 

    #Flipper Variables
    flipper_speed_const = 180
    
    flipper_final_pos = 0
    flipper_up = 151

    #Cage Variables
    cage_speed_full_cube = 300
    cage_speed_normal = 300
   
    cw_adj = -35
    ccw_adj = 35
    cw2_adj = -40

    turn_cw_free = 150
    turn_ccw_free = -150

    turn_cw_blocked = 185
    turn_ccw_blocked = -185

    turn_cw2_free = 300
    turn_cw2_blocked = 345

    turn_final_pos = 0


    #Networking
    HOST = "10.13.30.20"
    PORT = 8080

    # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #received_solution = "R2 L' D"
    received_solution = "U' L' U' F' R2"
    #received_solution = "U' L' U' F' R2 B' R F U B2 U B' L U' F U R F' "
    #received_solution = "R2 L' D F2 R' D' R' L U' D R D B2 R' U D2"
    #received_solution = "F B R U D R2 D B' F2 D' B' L U' L2 B2 R B D2 R2 F R2 D2 R' U B' "
    curr_turn = 0
    next_turn = curr_turn + 2
    last_turn = -1 #can only be updated after first turn is made

    def __init__(self):
        self.shutdown = False
        self.elevator = LargeMotor(OUTPUT_A)
        self.flipper = LargeMotor(OUTPUT_B)
        self.cage = LargeMotor(OUTPUT_C)
        
        self.init_motors()
        self.state = ['U','L','F','R','B','D']

        signal.signal(signal.SIGTERM, self.signal_term_handler)
        signal.signal(signal.SIGINT, self.signal_int_handler)

        log.info("Fully initialized")

    def init_motors(self):

        for x in (self.elevator, self.flipper, self.cage):
            x.reset()

        log.info("Initialize rotator %s" % self.elevator)
        #self.rotator.on(SpeedDPS(-50), block=False)
        self.elevator.off()
        self.elevator.reset()

        log.info("Initialize  %s" % self.flipper)
        self.flipper.off()
        self.flipper.reset()

        log.info("Initialize %s" % self.cage)
        self.cage.off()
        self.cage.reset()


    def shutdown_robot(self):
        log.info('Shutting down')
        self.shutdown = True

        #We are shutting down motors. 
        for x in (self.elevator, self.flipper, self.cage):
            x.stop_action = 'brake'
            x.off(False)
    
    def signal_term_handler(self, signal, frame):
        log.error('Caught SIGTERM')

    def signal_int_handler(self, signal, frame):
        log.error('Caught SIGINT')
        self.shutdown_robot()

    def apply_transformation(self, transformation):
        self.state = [self.state[t] for t in transformation]


    def elevate(self, level):
        self.elevator.on_to_position(SpeedDPS(Cuber2x.elevator_speed_up_fast), level)
        sleep(0.05)

        #self.elevator.on_to_position(SpeedDPS(Cuber2x.elevator_speed_down_fast),Cuber2x.elevator_final_pos)
        
    
    def flip(self, direction):
        self.flipper.on_to_position(SpeedDPS(Cuber2x.flipper_speed_const), direction, brake=True)
        sleep(0.05)


    #Cuber2x.cage_cw_blocked
    def turn_cage(self, direction, adj):
        
        self.cage.on_for_degrees(SpeedDPS(Cuber2x.cage_speed_full_cube), direction, brake=True)
        sleep(0.05)

        self.cage.on_for_degrees(SpeedDPS(Cuber2x.cage_speed_full_cube), adj, brake=True)
        sleep(0.05)

    
    def scan(self):
        
        for x in range(3): 
            sleep(1)
            self.elevate(self.elevate_3x3_fully)
            
            self.turn_cage(self.cage_cw_free, 0)

            self.elevate(self.elevator_final_pos)

        sleep(1)
        self.flip(self.flipper_up)
        self.elevate(-200)
        self.flip(self.flipper_final_pos)
        self.elevate(self.elevator_final_pos)
        sleep(1)
        
        self.elevate(self.elevate_3x3_fully)
        self.turn_cage(self.cage_cw2_free, 0)
        self.elevate(self.elevator_final_pos)

        sleep(0.2)
        log.info('waiting for solution....')
        #read from file where solution is written to
        sleep(2)
        self.receive_solution()


        #orient to solve cube
        self.flip(self.flipper_up)
        self.elevate(self.elevate_3x3_fully)
        self.turn_cage(self.cage_ccw_free, 0)
        self.flip(self.flipper_final_pos)
        self.elevate(self.elevator_final_pos)

    
    def connect_to_server(self):

        self.sock.connect((self.HOST, self.PORT))
        self.sock.sendall(b"Connected\n")
        
    def receive_solution(self):

        #self.received_solution = self.sock.recv(1024)
        #self.recieved_solution =
        print("solution is: ", self.received_solution)
        
    
    def decode_solution(self):
        self.received_solution = self.received_solution.replace('\r','').replace('\n','').replace('b','').replace('"','')

        print("cleaned solution: \n", self.received_solution)
    

    def apply_first_two_turns(self):
        
        print('lastturn: ', self.last_turn)
        print('nextturn: ', self.next_turn)


        if self.last_turn[0] == 'U':
            self.elevate(self.elevate_3x3_1_row)
            
            self.turn_direction(self.last_turn)

            print(self.last_turn)
            
            self.u_on_top()
        
        elif self.last_turn[0] == 'L':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)

            self.turn_direction(self.last_turn)
                            
            print(self.last_turn)
            self.l_on_top()

        elif self.last_turn[0] == 'F':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)
            
            self.flip(self.flipper_final_pos)
            self.turn_direction(self.last_turn)
                        
            print(self.last_turn)
            self.f_on_top()
            

        elif self.last_turn[0] == 'R':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_ccw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)

            self.turn_direction(self.last_turn)
            
            print(self.last_turn)
            self.r_on_top()

        elif self.last_turn[0] == 'B':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)
            self.flip(self.flipper_final_pos)


            self.turn_direction(self.last_turn)

            print(self.last_turn)
            self.b_on_top() 

        elif self.last_turn[0] == 'D':

            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)
            
            self.turn_direction(self.last_turn)

            print(self.last_turn)
            self.d_on_top()

    def apply_solution(self):
        
        print(self.received_solution)
        self.received_solution = self.received_solution.split();
        
        self.last_turn = self.received_solution[0] 
        for i in range(1, len(self.received_solution)-1):
            #print(self.received_solution[i], len(self.received_solution[i]))
            
            self.next_turn = self.received_solution[i]# really [i+1]
            if i == 1:
                self.apply_first_two_turns()
            #self.curr_turn = self.received_solution[i]
            #if self.received_solution[i] != self.received_solution[-1]:
            


            if self.last_turn[0] == 'U':
                self.u_on_top()
            
            elif self.last_turn[0] == 'L':
                self.l_on_top()

            elif self.last_turn[0] == 'F':
                self.f_on_top()

            elif self.last_turn[0] == 'R':
                self.r_on_top()

            elif self.last_turn[0] == 'B':
                self.b_on_top() 

            elif self.last_turn[0] == 'D':
                self.d_on_top()

                
    # rename function because it only handles 2 char turns
    def turn_direction(self, this_turn):
        #since broken up by characters if there is no extra len for cw checkf for len and move
        if len(this_turn)  == 1:
            self.turn_cage(self.turn_cw_blocked, self.cw_adj)
            self.elevate(self.elevator_final_pos)


        elif this_turn[-1] == "'":
            self.turn_cage(self.turn_ccw_blocked, self.ccw_adj)
            self.elevate(self.elevator_final_pos)

        elif this_turn[-1] == '2':
            self.turn_cage(self.turn_cw2_blocked, self.cw2_adj)
            self.elevate(self.elevator_final_pos)


    def u_on_top(self):
        if self.next_turn[0] == 'L':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
           
            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'R': #might be broken throughout
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_ccw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)

            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)

            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'F':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)
            
            self.flip(self.flipper_final_pos)        
            self.turn_direction(self.next_turn)

            self.last_turn = self.next_turn
            print(self.next_turn)
           

        elif self.next_turn[0] == 'B':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)
            self.flip(self.flipper_final_pos)

            self.turn_direction(self.next_turn)
            
            self.last_turn = self.next_turn
            print(self.next_turn)



        elif self.next_turn[0] == 'D':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)

            self.turn_direction(self.next_turn)

            self.last_turn = self.next_turn
            print(self.next_turn)

    def l_on_top(self):
        if self.next_turn[0] == 'F':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
           
            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)

            self.last_turn = self.next_turn
            print(self.next_turn)
                
        elif self.next_turn[0] == 'B':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_ccw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)

            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)

            self.last_turn = self.next_turn
            print(self.next_turn)


        elif self.next_turn[0] == 'U':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)
            self.flip(self.flipper_final_pos)
            
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)


        elif self.next_turn[0] == 'D':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)

            self.flip(self.flipper_final_pos)
            
            
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)
            

        elif self.next_turn[0] == 'R':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)

            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

    def f_on_top(self):
        if self.next_turn[0] == 'L':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
           
            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

            
        elif self.next_turn[0] == 'R':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_ccw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)

            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)
             
        elif self.next_turn[0] == 'D':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)
            
            self.flip(self.flipper_final_pos)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)


        elif self.next_turn[0] == 'U':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)

            self.flip(self.flipper_final_pos)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)


        elif self.next_turn[0] == 'B':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)

            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn) 

        
    def r_on_top(self):
        if self.next_turn[0] == 'B':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
           
            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)


        elif self.next_turn[0] == 'F':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_ccw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)


        elif self.next_turn[0] == 'U':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)
            
            self.flip(self.flipper_final_pos)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)


        elif self.next_turn[0] == 'D':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)

            self.flip(self.flipper_final_pos)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)


        elif self.next_turn[0] == 'L':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)

            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

    def b_on_top(self):
        if self.next_turn[0] == 'R':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
           
            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'L':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_ccw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'D':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)
            
            self.flip(self.flipper_final_pos)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'U':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)

            self.flip(self.flipper_final_pos)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'F':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)

            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

    def d_on_top(self):
        if self.next_turn[0] == 'R':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
           
            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'L':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_ccw_free, 0)
            self.flip(self.flipper_up)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'F':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)
            
            self.flip(self.flipper_final_pos)
            self.turn_direction(self.next_turn)        
            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'B':
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_1_row)

            self.flip(self.flipper_final_pos)
            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)

        elif self.next_turn[0] == 'U':
            self.flip(self.flipper_up)
            self.elevate(self.elevate_3x3_fully)
            self.turn_cage(self.turn_cw2_free, 0)
            self.elevate(self.elevator_final_pos)
            self.flip(self.flipper_final_pos)
            self.elevate(self.elevate_3x3_1_row)

            self.turn_direction(self.next_turn)
            self.last_turn = self.next_turn
            print(self.next_turn)
        
if __name__== '__main__':
   
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(filename)12s %(levelname)8s: %(message)s')
    log = logging.getLogger(__name__)

    #Color the errors and warnings in red
    logging.addLevelName(logging.ERROR, "\033[91m   %s\033[0m" % logging.getLevelName(logging.ERROR))
    logging.addLevelName(logging.WARNING, "\033[91m %s\033[0m" % logging.getLevelName(logging.WARNING))
    

    multicuber = Cuber2x()

    try:
        
        #multicuber.connect_to_server()
        #multicuber.scan()
        multicuber.apply_solution()

        multicuber.shutdown_robot()


        #multicuber.flip(multicuber.flipper_up)
        #multicuber.elevate(multicuber.elevate_3x3_fully) 
        #multicuber.flip(multicuber.flipper_final_pos)
        #multicuber.apply_solution()
        #multicuber.shutdown_robot()
        #multicuber.apply_solution()
        #multicuber.shutdown_robot()
        #multicuber.scan()
        #multicuber.shutdown_robot()
        """ 
        multicuber.elevate(multicuber.elevate_3x3_1_row)
        multicuber.turn_cage()

        multicuber.elevate(multicuber.elevator_final_pos)
        multicuber.flip(multicuber.flipper_up)
        
        multicuber.elevate(multicuber.elevate_3x3_1_row)
        multicuber.turn_cage()

        multicuber.flip(multicuber.flipper_final_pos)
        multicuber.elevate(multicuber.elevator_final_pos)
        
        multicuber.shutdown_robot() 
        """


    except Exception as e:
        log.exception(e)
        multicuber.shutdown_robot()
        sys.exit(1)

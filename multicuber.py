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
    elevator_speed_up_fast = 700
    elevator_speed_up_slow = 400
    
    elevator_final_pos = 0

    elevate_2x2_fully = -570
    elevate_2x2_1_row = -450

    elevate_3x3_fully = -540
    elevate_3x3_1_row = -370
    elevate_3x3_2_rows = -470 
    
    elevate_from_2_fully = -70
    elevate_from_1_fully = -170
    #Flipper Variables
    flipper_speed_const = 600
    
    flipper_final_pos = -1
    flipper_up = 151

    #Cage Variables
    cage_speed_full_cube = 700
    cage_speed_normal = 550
   
    cw_adj = -35
    ccw_adj = 35
    cw2_adj = -40

    turn_cw_free = 150
    turn_ccw_free = -150

    turn_cw_blocked = 185
    turn_ccw_blocked = -185

    turn_cw2_free = 300
    turn_cw2_blocked = 340

    turn_final_pos = 0


    #Networking
    HOST = "169.254.17.157"
    PORT = 8080

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #received_solution = "L U B' U' R L' B R' F B' D R D' F'" #anaconda
    #received_solution = "R2 L2 F2 B2"
    #received_solution = "U' R2 L2 F2 B2 U' R L F B' U F2 D2 R2 L2 F2 U2 F2 U' F2" #kilt (scottish skirt)
    #received_solution = "U' L' U' F' R2 B' R F U B2 U B' L U' F U R F'" #cube in a cube in a cube
    #received_solution = "R2 L' D F2 R' D' R' L U' D R D B2 R' U D2"
    #received_solution = "F B R U D R2 D B' F2 D' B' L U' L2 B2 R B D2 R2 F R2 D2 R' U B' "
    received_solution = "U R2 F B R B2 R U2 L B2 R U' D' R2 F R' L B2 U2 F2" #Superflip   
    next_turn = None 
    future_turn = None

    #transformation lists
    cw_trans = [0,2,3,4,1,5]
    ccw_trans = [0,4,1,2,3,5]
    cw2_trans = [0,3,4,1,2,5]
    up_trans = [2,1,5,3,0,4]
    down_trans = [4,1,0,3,5,2]

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

    def apply_trans(self, transformation):
        self.state = [self.state[t] for t in transformation]


    def elevate(self, level):
        self.elevator.on_to_position(SpeedDPS(Cuber2x.elevator_speed_up_fast), level)
        
    
    def flip(self, direction):
        self.flipper.on_to_position(SpeedDPS(Cuber2x.flipper_speed_const), direction)
        #sleep(0.02)


    def turn_cage(self, direction, adj, trans):
        
        #if adj is 0 transformation is happening, because side isn't being turned
        if adj == 0:
            self.apply_trans(trans)

        self.cage.on_for_degrees(SpeedDPS(Cuber2x.cage_speed_full_cube), direction)
        sleep(0.02)

        self.cage.on_for_degrees(SpeedDPS(Cuber2x.cage_speed_full_cube), adj)
        #sleep(0.02)

    
    def scan(self):
        sleep(1) 
        for x in range(3): 
            sleep(1)
            self.elevate(self.elevate_3x3_fully)
            
            self.turn_cage(self.turn_cw_free, 0, self.cw_trans)

            self.elevate(self.elevator_final_pos)

        sleep(1)
        self.flip(self.flipper_up)
        self.elevate(-200)
        self.flip(self.flipper_final_pos)
        self.elevate(self.elevator_final_pos)
        sleep(1)
        
        self.elevate(self.elevate_3x3_fully)
        self.turn_cage(self.turn_cw2_free, 0, self.cw2_trans)
        self.elevate(self.elevator_final_pos)

        sleep(1)
        log.info('waiting for solution....')

        sleep(1) 
        self.receive_solution()
        #read from file where solution is written to

        #orient to solve cube
        self.flip(self.flipper_up)
        self.elevate(self.elevate_3x3_fully)
        self.turn_cage(self.turn_ccw_free, 0, self.ccw_trans)
        self.flip(self.flipper_final_pos)
        self.elevate(self.elevator_final_pos)

        #self.receive_solution()
    
    def connect_to_server(self):

        self.sock.connect((self.HOST, self.PORT))
        self.sock.sendall(b"Connected\n")
        
    def receive_solution(self):

        self.received_solution = self.sock.recv(1024)

        encoding = 'utf-8'
        self.received_solution = self.received_solution.decode(encoding)
        print("solution is: ", self.received_solution)
        
    
    def decode_solution(self):
        
        self.received_solution = self.received_solution.replace('\r','').replace('\n','').replace('b','').replace('"','')
        print("cleaned solution: \n", self.received_solution)
    

    def apply_solution(self):
        
        print(self.received_solution)
        self.received_solution = self.received_solution.split();
        
        for i in range(0, len(self.received_solution)):
            
            self.next_turn = self.received_solution[i]
            if i == len(self.received_solution) -1:
                self.future_turn = self.next_turn
            else:
                self.future_turn = self.received_solution[i+1]


            if self.state[0] == 'U':
                self.u_on_top()
                
            elif self.state[0] == 'L':
                self.l_on_top()
            
            elif self.state[0] == 'F':
                self.f_on_top()

            elif self.state[0] == 'R':
                self.r_on_top()
            
            elif self.state[0] == 'B':
                self.b_on_top()

            elif self.state[0] == 'D':
                self.d_on_top()

    def keep_cube_elevated(self):
                
        for i in range(len(self.state)):
            # i != front or i != back
            if (i == 1 or i == 3) and self.state[i] == self.future_turn[0]:
                #elevate fully for rotation
                if self.next_turn[0] == 'D':
                    self.elevate(self.elevate_3x3_fully)
                    #print("elevated 2")
                    return True
                else:
                    self.elevate(self.elevate_3x3_fully)
                    #print("elevated 1")
                    return True 


    # rename function because it only handles 2 char turns
    def turn_direction(self, this_turn):
        #since broken up by characters if there is no extra len for cw checkf for len and move
        if len(this_turn) == 1:
            self.turn_cage(self.turn_cw_blocked, self.cw_adj, None)

            #before lowering cube check to see if it needs to be lowered...
            if self.keep_cube_elevated():
                return
            else:
                self.elevate(self.elevator_final_pos)

        elif this_turn[-1] == "'":
            self.turn_cage(self.turn_ccw_blocked, self.ccw_adj, None)
            
            if self.keep_cube_elevated():
                return 
            else:
                self.elevate(self.elevator_final_pos)

        elif this_turn[-1] == '2':
            self.turn_cage(self.turn_cw2_blocked, self.cw2_adj, None)
            
            if self.keep_cube_elevated():
                return
            else: 
                self.elevate(self.elevator_final_pos)



    def turn_u(self):
        if self.elevator.position != self.elevate_3x3_fully or self.elevator.position == -539:
            #print("false: ", self.elevator.position, ":", self.elevate_3x3_fully) 
            self.elevate(self.elevate_3x3_1_row)

        #print("true: ", self.elevator.position, ":", self.elevate_3x3_fully) 
        self.turn_direction(self.next_turn)
        print(self.next_turn) 

    def turn_l(self):
        if self.elevator.position != self.elevate_3x3_fully or self.elevator.position == -539:
            #print("false: ", self.elevator.position, ":", self.elevate_3x3_fully) 
            self.elevate(self.elevate_3x3_fully)
        
        
        #print("true: ", self.elevator.position, ":", self.elevate_3x3_fully) 
        self.turn_cage(self.turn_cw_free, 0, self.cw_trans)
        self.flip(self.flipper_up)
        self.elevate(self.elevator_final_pos)
        self.flip(self.flipper_final_pos)
        self.apply_trans(self.down_trans)
        self.elevate(self.elevate_3x3_1_row)
        self.turn_direction(self.next_turn)
        self.last_turn = self.next_turn
        print(self.next_turn)
    
    def turn_f(self):
        
        self.flip(self.flipper_up)
        self.apply_trans(self.up_trans)
        self.elevate(self.elevate_3x3_1_row)
        
        self.flip(self.flipper_final_pos)        
        self.turn_direction(self.next_turn)

        self.last_turn = self.next_turn
        print(self.next_turn)
    
    def turn_r(self):
    
        if self.elevator.position != self.elevate_3x3_fully or self.elevator.position == -539:
            #print("false: ", self.elevator.position, ":", self.elevate_3x3_fully) 
            self.elevate(self.elevate_3x3_fully)
        
        #print("true: ", self.elevator.position, ":", self.elevate_3x3_fully) 
        self.turn_cage(self.turn_ccw_free, 0, self.ccw_trans)
        self.flip(self.flipper_up)
        self.elevate(self.elevator_final_pos)
        self.flip(self.flipper_final_pos)
        self.apply_trans(self.down_trans)
        
        self.elevate(self.elevate_3x3_1_row)
        self.turn_direction(self.next_turn)

        self.last_turn = self.next_turn
        print(self.next_turn)
    
    def turn_b(self):

        self.elevate(-200) #doesn't need to elevate fully as it's just being flipped
         
        #print("true: ", self.elevator.position, ":", self.elevate_3x3_fully) 
        self.flip(self.flipper_up)
        self.elevate(self.elevator_final_pos)
        self.flip(self.flipper_final_pos)
        self.apply_trans(self.down_trans)
        self.elevate(self.elevate_3x3_1_row)

        self.turn_direction(self.next_turn)
        
        self.last_turn = self.next_turn
        print(self.next_turn)

    def turn_d(self):
        if self.elevator.position != self.elevate_3x3_fully or self.elevator.position == -539:
            #print("false: ", self.elevator.position, ":", self.elevate_3x3_fully) 
            self.elevate(self.elevate_3x3_2_rows)
        #we have to check to see what the value is of next turn to perform transformation
        
        if len(self.next_turn) == 1:
            self.apply_trans(self.cw_trans)
        elif self.next_turn[-1] == "'":
            self.apply_trans(self.ccw_trans)
        elif self.next_turn[-1] == "2":
            self.apply_trans(self.ccw_trans)

        #print("true: ", self.elevator.position, ":", self.elevate_3x3_fully) 
        self.turn_direction(self.next_turn)
        self.last_turn = self.next_turn
        print(self.next_turn)

    def determine_next_turn(self):

        for i in self.state:
            if self.next_turn[0] == i:
                
                if self.state.index(i) == 0:
                    self.turn_u()
                elif self.state.index(i) == 1:
                    self.turn_l()
                elif self.state.index(i) == 2:
                    self.turn_f()
                elif self.state.index(i) == 3:
                    self.turn_r()
                elif self.state.index(i) == 4:
                    self.turn_b()
                elif self.state.index(i) == 5:
                    self.turn_d()


    def u_on_top(self):
       self.determine_next_turn() 

    def l_on_top(self):
       self.determine_next_turn() 

    def f_on_top(self):
       self.determine_next_turn() 
        
    def r_on_top(self):
       self.determine_next_turn() 

    def b_on_top(self):
       self.determine_next_turn() 

    def d_on_top(self):
       self.determine_next_turn() 
                    

    def triumph(self):
        self.elevate(self.elevate_3x3_fully)
        self.turn_cage(self.turn_cw2_free*4, 0 ,self.cw2_trans)
        self.state = ['U','L','F','R','B','D']
        self.elevate(self.elevator_final_pos)





if __name__== '__main__':
   
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(filename)12s %(levelname)8s: %(message)s')
    log = logging.getLogger(__name__)

    #Color the errors and warnings in red
    logging.addLevelName(logging.ERROR, "\033[91m   %s\033[0m" % logging.getLevelName(logging.ERROR))
    logging.addLevelName(logging.WARNING, "\033[91m %s\033[0m" % logging.getLevelName(logging.WARNING))
    

    multicuber = Cuber2x()

    try:
        
        multicuber.connect_to_server()
        multicuber.scan()
        multicuber.decode_solution()
        multicuber.apply_solution()
        multicuber.triumph()
        multicuber.shutdown_robot()


    except Exception as e:
        log.exception(e)
        multicuber.shutdown_robot()
        sys.exit(1)

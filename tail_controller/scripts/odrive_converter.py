#!/usr/bin/env python
import rospy
from std_msgs.msg import String
from spirit_msgs.msg import LegCommand, RobotState
import numpy as np
import odrive
from odrive.enums import *
import time

print("finding an odrive...")
od = odrive.find_any()
print("found an odrive")

def feedback_callback(msg):
    position = msg.body.pose.pose.position
    position = np.array([position.x, position.y, position.z])
    print("position:", position)

    orientation = msg.body.pose.pose.orientation
    orientation = np.array([orientation.x, orientation.y, orientation.z, orientation.w])
    print("orientation:", orientation)

    velocity = msg.body.twist.twist.linear
    velocity = np.array([velocity.x, velocity.y, velocity.z])
    print("velocity:", velocity)

    angular_velocity = msg.body.twist.twist.angular
    angular_velocity = np.array([angular_velocity.x, angular_velocity.y, angular_velocity.z])
    print("angular_velocity:", angular_velocity)

def mpc_callback(msg):
    #rospy.loginfo(rospy.get_caller_id() + "I heard %s", msg.motor_commands[1].pos_setpoint)
    
    currentpos0 = od.axis0.encoder.pos_estimate
    currentpos1 = od.axis1.encoder.pos_estimate
    pos0 =  msg.motor_commands[0].pos_setpoint
    pos1 =  msg.motor_commands[1].pos_setpoint

    rospy.loginfo("Motor 0 is at: " + str(currentpos0) + " should be " + str( pos0))

    od.axis0.controller.pos_setpoint = pos0
    od.axis1.controller.pos_setpoint = pos1
    
def listener():
    # Calibrate the motors (needed when running for the first time after being off or having an error)
    calibrate = False

    if(calibrate):
        od.axis0.requested_state = AXIS_STATE_FULL_CALIBRATION_SEQUENCE
        od.axis1.requested_state = AXIS_STATE_FULL_CALIBRATION_SEQUENCE
        while od.axis0.current_state != AXIS_STATE_IDLE or od.axis1.current_state != AXIS_STATE_IDLE:
             time.sleep(0.1)

    # Set up the motors! 
    od.axis0.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
    od.axis1.requested_state = AXIS_STATE_CLOSED_LOOP_CONTROL
    od.axis0.controller.config.control_mode = CTRL_MODE_POSITION_CONTROL
    od.axis0.trap_traj.config.vel_limit = 700000
    od.axis0.trap_traj.config.accel_limit = 800000
    od.axis0.trap_traj.config.decel_limit = 800000
    od.axis0.controller.config.vel_limit  = 720000
    od.axis1.controller.config.control_mode = CTRL_MODE_POSITION_CONTROL
    od.axis1.trap_traj.config.vel_limit = 700000
    od.axis1.trap_traj.config.accel_limit = 800000
    od.axis1.trap_traj.config.decel_limit = 800000
    od.axis1.controller.config.vel_limit  = 720000
    start0 = od.axis0.encoder.pos_estimate
    start1 = od.axis1.encoder.pos_estimate

    use_mpc = rospy.get_param("/tail_controller/use_mpc")
    rospy.init_node('listener', anonymous=True)

    if(use_mpc):
        # Track mpc trajectory
        tail_topic = "/control/tail_command"
        rospy.Subscriber(tail_topic, LegCommand, mpc_callback, queue_size=1)
    else:
        # Feedback control
        state_topic = rospy.get_param("/topics/state/ground_truth")
        rospy.Subscriber(state_topic, RobotState, feedback_callback, queue_size=1)

    # spin() simply keeps python from exiting until this node is stopped
    rospy.spin()

    #put motors into idle when program is killed 
    od.axis0.requested_state = AXIS_STATE_IDLE
    od.axis1.requested_state = AXIS_STATE_IDLE

if __name__ == '__main__':
    listener()

#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################################################################################################

import indigo
import threading
import random
from datetime import datetime, time
import Queue

####################################################################################################
# Plugin
####################################################################################################
class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.threads = {}
        self.q = Queue.Queue()

    def __del__(self):
        for k, v in self.threads.iteritems():
            v.cancel()
        indigo.PluginBase.__del__(self)

    #==============================================================================================#
    # Close threads on shutdown
    #==============================================================================================#
    def shutdown(self):
        for k, v in self.threads.iteritems():
            v.cancel()

    ####################################################################################################
	# Actions here execute every time communication is enabled to a device
	####################################################################################################
    def deviceStartComm(self, device):

        self.lights = {}
        self.p_device = device

        for d in device.pluginProps.get('indigo_dimmable', ''):
            dimmer = indigo.devices[int(d)]
            self.lights[int(d)] = Light(int(d), dimmer.name, True)

        for r in device.pluginProps.get('indigo_relay', ''):
            relay = indigo.devices[int(r)]
            self.lights[int(r)] = Light(int(r), relay.name, False)

    ####################################################################################################
    # Close threads if device is deleted
    ####################################################################################################
    def deviceDeleted(self, device):
        for k, v in self.threads.iteritems():
            v.cancel()

    def runConcurrentThread(self):
        try:
            while True:

                #============================================================================================#
                # Check if random lights should be running at startup
                #============================================================================================#
                quiet_set = self.p_device.pluginProps.get('quiet_checkbox', '')
                daylight = indigo.variables['isDaylight'].value


                #============================================================================================#
                # Check for daylight
                #============================================================================================#
                if daylight == 'true':
                    self.enabled = False

                elif daylight == 'false':
                    self.enabled = True

                    #========================================================================================#
                    # If Quiet Period is set, check if we are within those bounds and enable/disable
                    #========================================================================================#
                    if quiet_set:
                        quiet_start = int(self.p_device.pluginProps.get('quiet_start', ''))
                        quiet_end = int(self.p_device.pluginProps.get('quiet_end', ''))
                        quiet_range = [17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8]
                        quiet_period = quiet_range[quiet_range.index(quiet_start):quiet_range.index(quiet_end)]
                        hour = int(datetime.now().time().hour)

                        if hour in quiet_period:
                            self.enabled = False

                        else:
                            self.enabled = True

                self.sleep(60)

        except self.StopThread:
            # do any cleanup here
            pass

    #==============================================================================================#
    # Start Random Lighting
    #==============================================================================================#
    def start_random_lighting(self, pluginAction):

        #==============================================================================================#
        # Make sure it is dark and we are not within a user-defined quiet period
        #==============================================================================================#
        if self.enabled == True:
            #==============================================================================================#
            # Check if user specified custom start delay min/max, else use default
            #==============================================================================================#
            if self.p_device.pluginProps.get('start_checkbox', '') == True:
                startDelayMin = int(self.p_device.pluginProps.get('start_delay_min', ''))
                startDelayMax = int(self.p_device.pluginProps.get('start_delay_max', ''))
            else:
                startDelayMin = 15
                startDelayMax = 70

            #==============================================================================================#
            # If "Use All Lights" checkbox is un-checked, use only 75% of the lights selected for each run
            #==============================================================================================#
            if self.p_device.pluginProps.get('use_all_lights', '') == False:
                for i in random.sample(self.lights.keys(), int(round(len(self.lights.keys()) * .75))):
                    light = self.lights[i]
                    startDelay = random.randint(startDelayMin,startDelayMax)
                    #========================================================================================#
                    # Turn on light after "random" thread timer
                    #========================================================================================#
                    self.threads['start ' + light.name] = threading.Timer(startDelay, self.turn_on_light, (light,))
                    self.threads['start ' + light.name].start()

            #==============================================================================================#
            # If "Use All Lights" checkbox is checked, use all lights
            #==============================================================================================#
            else:
                for i in self.lights.keys():
                    light = self.lights[i]
                    startDelay = random.randint(startDelayMin,startDelayMax)
                    #========================================================================================#
                    # Turn on light after "random" thread timer
                    #========================================================================================#
                    self.threads['start ' + light.name] = threading.Timer(startDelay, self.turn_on_light, (light,))
                    self.threads['start ' + light.name].start()

    #==============================================================================================#
    # Turn On Light
    #==============================================================================================#
    def turn_on_light(self, light):

        # Close thread that delayed the start of turning light on
        self.threads['start ' + light.name].cancel()

        #==============================================================================================#
        # Check if user specified custom duration min/max, else use default
        #==============================================================================================#
        if self.p_device.pluginProps.get('dur_checkbox', '') == True:
            durMin = int(self.p_device.pluginProps.get('duration_min', ''))
            durMax = int(self.p_device.pluginProps.get('duration_max', ''))
        else:
            durMin = 600
            durMax = 900

        #==============================================================================================#
        # Check if user specified custom brightness min/max, else use default
        #==============================================================================================#
        if self.p_device.pluginProps.get('bri_checkbox', '') == True:
            briMin = int(self.p_device.pluginProps.get('brightness_min', ''))
            briMax = int(self.p_device.pluginProps.get('brightness_max', ''))
        else:
            briMin = 50
            briMax = 85

        #==============================================================================================#
        # Randomize duration and brightness
        #==============================================================================================#
        duration = random.randint(durMin,durMax)
        brightness = random.randint(briMin,briMax)

        if light.dimmable:
            #==============================================================================================#
            # Turn on dimmer
            #==============================================================================================#
            indigo.dimmer.setBrightness(light.indigo_id, value = brightness)

            #==============================================================================================#
            # Turn off light after "random" thread timer
            #==============================================================================================#
            self.threads[light.name] = threading.Timer(duration, self.turn_off_light, (light,))
            self.threads[light.name].start()
            self.q.put(light.indigo_id)

        else:
            #==============================================================================================#
            # Turn on On/Off light
            #==============================================================================================#
            indigo.device.turnOn(light.indigo_id)

            #==============================================================================================#
            # Turn off light after "random" thread timer
            #==============================================================================================#
            self.threads[light.name] = threading.Timer(duration, self.turn_off_light, (light,))
            self.threads[light.name].start()
            self.q.put(light.indigo_id)

    #==============================================================================================#
    # Turn Off Light
    #==============================================================================================#
    def turn_off_light(self, light):

        # Close thread that delayed turning light off
        self.threads[light.name].cancel()

        if self.q.qsize() > 1:
            self.q.get()

            # Turn off light
            indigo.device.turnOff(light.indigo_id)

        #==============================================================================================#
        # Queue ensures that 1 light always stays on each cycle
        #==============================================================================================#
        elif self.q.qsize() == 1:
            self.q.get()
            self.start_random_lighting(None)

    #==============================================================================================#
    # Stop Random Lighting
    #==============================================================================================#
    def stop_random_lighting(self, pluginAction):

        # Clear queue
        with self.q.mutex:
            self.q.queue.clear()

        # Close all active threads
        for k, v in self.threads.iteritems():
            v.cancel()

        # Turn lights off if that is the pluginAction
        if pluginAction.props.get('stop_action', '') == 'stop_and_turn_off':
            for k, v in self.lights.iteritems():
                indigo.device.turnOff(k)

        # If dark, Keep/turn on specific lights, turn off all others
        elif pluginAction.props.get('stop_action', '') == 'stop_and_keep_specific_on':

            daylight = indigo.variables['isDaylight'].value
            if daylight == 'false':

                keepOn = []

                for d in pluginAction.props.get('indigo_dimmable', ''):
                    indigo.device.turnOn(int(d))
                    keepOn.append(int(d))

                for r in pluginAction.props.get('indigo_relay', ''):
                    indigo.device.turnOn(int(r))
                    keepOn.append(int(r))

                for k, v in self.lights.iteritems():
                    if k not in keepOn:
                        indigo.device.turnOff(k)

#==============================================================================================#
# Light Class
#==============================================================================================#
class Light(object):
    def __init__(self, indigo_id, name, dimmable):
        self.indigo_id = indigo_id
        self.name = name
        self.dimmable = dimmable

#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################################################################################################

import indigo
import threading
import random

####################################################################################################
# Plugin
####################################################################################################
class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.lights = {}
        self.threads = {}

    def __del__(self):
        indigo.PluginBase.__del__(self)

    def startup(self):
        indigo.server.log('Randomized Lighting plugin started.')

    def shutdown(self):
        for k, v in self.threads.iteritems():
            v.cancel()
            indigo.server.log(str(k) + ' cancelled.')

    ####################################################################################################
	# Actions here execute every time communication is enabled to a device
	####################################################################################################
    def deviceStartComm(self, device):

        self.p_device = device

        for d in device.pluginProps.get('indigo_dimmable', ''):
            # indigo.server.log(indigo.devices[int(d)].name + ' - ' + str(d))
            dimmer = indigo.devices[int(d)]
            self.lights[int(d)] = Light(int(d), dimmer.name, True)

        for r in device.pluginProps.get('indigo_relay', ''):
            # indigo.server.log(indigo.devices[int(r)].name + ' - ' + str(r))
            relay = indigo.devices[int(r)]
            self.lights[int(r)] = Light(int(r), relay.name, False)

    ####################################################################################################
    # Remove device from our device_dict if it is deleted in Indigo
    ####################################################################################################
    def deviceDeleted(self, device):
        pass

    ####################################################################################################
    # Toggle Debugging
    ####################################################################################################
    def toggle_debugging(self):
        pass

    #==============================================================================================#
    # Start Random Lighting
    #==============================================================================================#
    def start_random_lighting(self, pluginAction):

        #==============================================================================================#
        # Check if user specified custom start delay min/max, else use default
        #==============================================================================================#
        if self.p_device.pluginProps.get('start_checkbox', '') == True:
            startDelayMin = int(self.p_device.pluginProps.get('start_delay_min', ''))
            startDelayMax = int(self.p_device.pluginProps.get('start_delay_max', ''))
        else:
            startDelayMin = 15
            startDelayMax = 70

        if self.p_device.pluginProps.get('use_all_lights', '') == False:
            for i in random.sample(self.lights.keys(), int(round(len(self.lights.keys()) * .75))):
                light = self.lights[i]
                startDelay = random.randint(startDelayMin,startDelayMax)
                #============================================================================================#
                # Turn on light after "random" thread timer
                #============================================================================================#
                self.threads['start ' + light.name] = threading.Timer(startDelay, self.turn_on_light, (light,))
                self.threads['start ' + light.name].start()

        else:
            for i in self.lights.keys():
                light = self.lights[i]
                startDelay = random.randint(startDelayMin,startDelayMax)
                #============================================================================================#
                # Turn on light after "random" thread timer
                #============================================================================================#
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

        briMin = int(self.p_device.pluginProps.get('brightness_min', ''))
        briMax = int(self.p_device.pluginProps.get('brightness_max', ''))

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

    #==============================================================================================#
    # Turn Off Light
    #==============================================================================================#
    def turn_off_light(self, light):

        # Close thread that delayed turning light off
        self.threads[light.name].cancel()

        # Turn off light
        indigo.device.turnOff(light.indigo_id)

#==============================================================================================#
# Light Class
#==============================================================================================#
class Light(object):
    def __init__(self, indigo_id, name, dimmable):
        self.indigo_id = indigo_id
        self.name = name
        self.dimmable = dimmable

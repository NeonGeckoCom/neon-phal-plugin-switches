# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import RPi.GPIO as GPIO

from abc import ABC
from time import sleep
from ovos_plugin_manager.phal import PHALPlugin
from ovos_plugin_manager.hardware.switches import AbstractSwitches
from ovos_utils.log import LOG
from mycroft_bus_client import Message
from sj201_interface.revisions import detect_sj201_revision


class SwitchValidator:
    @staticmethod
    def validate(_=None):
        # TODO: More generic validation
        return detect_sj201_revision() is not None


class SwitchInputs(PHALPlugin):
    validator = SwitchValidator

    def __init__(self, bus=None, config=None):
        super().__init__(bus=bus, name="neon-phal-plugin-switches",
                         config=config)
        # TODO: Read pins from configuration
        self.switches = GPIOSwitches(action_callback=self.on_button_press,
                                     volup_callback=self.on_button_volup_press,
                                     voldown_callback=self.on_button_voldown_press,
                                     mute_callback=self.on_hardware_mute,
                                     unmute_callback=self.on_hardware_unmute)
        self.switches.on_mute = self.on_hardware_mute
        self.switches.on_unmute = self.on_hardware_unmute
        self.switches.on_action = self.on_button_press
        self.switches.on_vol_up = self.on_button_volup_press
        self.switches.on_vol_down = self.on_button_voldown_press

        if GPIO.input(self.switches.mute_pin) == self.switches.muted:
            self.bus.emit(Message('mycroft.mic.mute'))

        self.bus.on('mycroft.mic.status', self.on_mic_status)

    def on_mic_status(self, message):
        if GPIO.input(self.switches.mute_pin) == self.switches.muted:
            msg_type = 'mycroft.mic.mute'
        else:
            msg_type = 'mycroft.mic.unmute'
        self.bus.emit(message.reply(msg_type))

    def on_button_press(self):
        LOG.info("Listen button pressed")
        if GPIO.input(self.switches.mute_pin) != self.switches.muted:
            self.bus.emit(Message("mycroft.mic.listen"))
        else:
            self.bus.emit(Message("mycroft.mic.error",
                                  {"error": "mic_sw_muted"}))

    def on_button_volup_press(self):
        LOG.debug("VolumeUp button pressed")
        self.bus.emit(Message("mycroft.volume.increase"))

    def on_button_voldown_press(self):
        LOG.debug("VolumeDown button pressed")
        self.bus.emit(Message("mycroft.volume.decrease"))

    def on_hardware_mute(self):
        LOG.debug("mic HW muted")
        self.bus.emit(Message("mycroft.mic.mute"))

    def on_hardware_unmute(self):
        LOG.debug("mic HW unmuted")
        self.bus.emit(Message("mycroft.mic.unmute"))


class GPIOSwitches(AbstractSwitches, ABC):
    def __init__(self, action_callback, volup_callback, voldown_callback,
                 mute_callback, unmute_callback, volup_pin: int = 22,
                 voldown_pin: int = 23, action_pin: int = 24,
                 mute_pin: int = 25, sw_active_state: int = 0,
                 sw_muted_state: int = 1):
        self.on_action = action_callback
        self.on_vol_up = volup_callback
        self.on_vol_down = voldown_callback
        self.on_mute = mute_callback
        self.on_unmute = unmute_callback

        self.vol_up_pin = volup_pin
        self.vol_dn_pin = voldown_pin
        self.action_pin = action_pin
        self.mute_pin = mute_pin
        self._active = sw_active_state
        self._muted = sw_muted_state

        self.setup_gpio()

    @property
    def muted(self):
        """
        Returns the state associated with 'mute' (0 for low, 1 for hi)
        """
        return self._muted

    def setup_gpio(self, debounce=100):
        """
        Do GPIO setup.
        """
        # use BCM GPIO pin numbering
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        if self._active == 0:
            pull_up_down = GPIO.PUD_UP
        else:
            pull_up_down = GPIO.PUD_DOWN
        # we need to pull up the 3 buttons and mute switch
        GPIO.setup(self.action_pin, GPIO.IN, pull_up_down=pull_up_down)
        GPIO.setup(self.vol_up_pin, GPIO.IN, pull_up_down=pull_up_down)
        GPIO.setup(self.vol_dn_pin, GPIO.IN, pull_up_down=pull_up_down)
        GPIO.setup(self.mute_pin, GPIO.IN, pull_up_down=pull_up_down)

        # attach callbacks
        GPIO.add_event_detect(self.action_pin,
                              GPIO.BOTH,
                              callback=self.handle_action,
                              bouncetime=debounce)

        GPIO.add_event_detect(self.vol_up_pin,
                              GPIO.BOTH,
                              callback=self.handle_vol_up,
                              bouncetime=debounce)

        GPIO.add_event_detect(self.vol_dn_pin,
                              GPIO.BOTH,
                              callback=self.handle_vol_down,
                              bouncetime=debounce)

        GPIO.add_event_detect(self.mute_pin,
                              GPIO.BOTH,
                              callback=self.handle_mute,
                              bouncetime=debounce)

    def handle_action(self, _):
        if GPIO.input(self.action_pin) == self._active:
            self.on_action()

    def handle_vol_up(self, _):
        if GPIO.input(self.vol_up_pin) == self._active:
            self.on_vol_up()

    def handle_vol_down(self, _):
        if GPIO.input(self.vol_dn_pin) == self._active:
            self.on_vol_down()

    def handle_mute(self, _):
        sleep(0.05)
        if GPIO.input(self.mute_pin) == self._muted:
            self.on_mute()
        else:
            self.on_unmute()

    @property
    def capabilities(self) -> dict:
        return {}

    def shutdown(self):
        pass

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

from abc import ABC
from typing import Optional

from ovos_plugin_manager.phal import PHALPlugin
from ovos_plugin_manager.hardware.switches import AbstractSwitches
from ovos_utils.log import LOG
from ovos_bus_client.message import Message
from gpiozero import Button, pi_info, BadPinFactory


class SwitchValidator:
    @staticmethod
    def validate(_=None):
        try:
            pi_info()
            return True
        except BadPinFactory:
            return False
        except Exception as e:
            LOG.info(e)
        return False


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

        if self.switches.mute_switch.is_active:
            LOG.debug(f"Mute switch active")
            self.bus.emit(Message('mycroft.mic.mute'))

        self.bus.on('mycroft.mic.status', self.on_mic_status)

    def on_mic_status(self, message):
        if self.switches.mute_switch.is_active:
            msg_type = 'mycroft.mic.mute'
        else:
            msg_type = 'mycroft.mic.unmute'
        self.bus.emit(message.reply(msg_type))

    def on_button_press(self, _=None):
        LOG.info("Listen button pressed")
        if not self.switches.mute_switch.is_active:
            self.bus.emit(Message("mycroft.mic.listen"))
        else:
            self.bus.emit(Message("mycroft.mic.error",
                                  {"error": "mic_sw_muted"}))

    def on_button_volup_press(self, _=None):
        LOG.debug("VolumeUp button pressed")
        self.bus.emit(Message("mycroft.volume.increase"))

    def on_button_voldown_press(self, _=None):
        LOG.debug("VolumeDown button pressed")
        self.bus.emit(Message("mycroft.volume.decrease"))

    def on_hardware_mute(self):
        LOG.debug("mic HW muted")
        self.bus.emit(Message("mycroft.mic.mute"))

    def on_hardware_unmute(self):
        LOG.debug("mic HW unmuted")
        self.bus.emit(Message("mycroft.mic.unmute"))


class GPIOSwitches(AbstractSwitches, ABC):
    def __init__(self, action_callback: callable,
                 volup_callback: callable, voldown_callback: callable,
                 mute_callback: callable, unmute_callback: callable,
                 volup_pin: int = 22, voldown_pin: int = 23,
                 action_pin: int = 24, mute_pin: int = 25,
                 sw_muted_state: int = 1, sw_press_state: int = 0):
        """
        Creates an object to manage GPIO switches and callbacks on switch
        activity.
        @param action_callback: Called when the "Action" switch is activated
        @param volup_callback: Called when the volume up switch is activated
        @param voldown_callback: Called when the volume down switch is activated
        @param mute_callback: Called when the mute switch is activated
        @param unmute_callback: Called when the mute switch is de-activated
        @param volup_pin: GPIO pin of the volume up switch
        @param voldown_pin: GPIO pin of the volume down switch
        @param action_pin: GPIO pin of the action switch
        @param mute_pin: GPIO pin of the mute slider
        @param sw_muted_state: mute pin state associated with muted
        @param sw_press_state button pin state associated with a press
        """
        self.on_action = action_callback
        self.on_vol_up = volup_callback
        self.on_vol_down = voldown_callback
        self.on_mute = mute_callback
        self.on_unmute = unmute_callback

        self.mute_switch: Optional[Button] = None
        self._buttons = list()

        self.vol_up_pin = volup_pin
        self.vol_dn_pin = voldown_pin
        self.action_pin = action_pin
        self.mute_pin = mute_pin
        self._muted = sw_muted_state

        self.setup_gpio(active_state=bool(sw_press_state))

    def setup_gpio(self, active_state: bool = True):
        """
        Do GPIO setup.
        @param active_state: If true, switches are active when high
        """

        act = Button(self.action_pin, pull_up=None, active_state=active_state)
        act.when_activated = self.on_action
        vol_up = Button(self.vol_up_pin, pull_up=None,
                        active_state=active_state)
        vol_up.when_activated = self.on_vol_up
        vol_down = Button(self.vol_dn_pin, pull_up=None,
                          active_state=active_state)
        vol_down.when_activated = self.on_vol_down

        self.mute_switch = Button(self.mute_pin, pull_up=None,
                                  active_state=bool(self._muted))

        self.mute_switch.when_deactivated = self.on_unmute
        self.mute_switch.when_activated = self.on_mute

        # Keep references to buttons to keep listeners alive until shutdown
        self._buttons.append(act)
        self._buttons.append(vol_up)
        self._buttons.append(vol_down)

        LOG.info(f"Pin states: vol_up={vol_up.is_active}, "
                 f"vol_down={vol_down.is_active}, act={act.is_active}, "
                 f"mute={self.mute_switch.is_active}")

    @property
    def capabilities(self) -> dict:
        return {}

    def shutdown(self):
        # Release GPIO buttons explicitly
        self._buttons = None
        self.mute_switch = None

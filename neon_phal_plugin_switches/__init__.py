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

from ovos_plugin_manager.phal import PHALPlugin
from ovos_utils.log import LOG
from mycroft_bus_client import Message
from sj201_interface.switches import R6Switches
from sj201_interface.revisions import detect_sj201_revision


class SwitchValidator:
    @staticmethod
    def validate(_=None):
        return detect_sj201_revision() is not None


class SwitchInputs(PHALPlugin):
    validator = SwitchValidator

    def __init__(self, bus=None, config=None):
        super().__init__(bus=bus, name="neon-phal-plugin-switches",
                         config=config)
        # TODO: Make this more generic
        self.switches = R6Switches()
        self.switches.on_mute = self.on_hardware_mute
        self.switches.on_unmute = self.on_hardware_unmute
        self.switches.on_action = self.on_button_press
        self.switches.on_vol_up = self.on_button_volup_press
        self.switches.on_vol_down = self.on_button_voldown_press

        if self.switches.SW_MUTE == 1:
            self.bus.emit(Message('mycroft.mic.mute'))

        self.bus.on('mycroft.mic.status', self.on_mic_status)

    def on_mic_status(self, message):
        if self.switches.SW_MUTE == 1:
            msg_type = 'mycroft.mic.mute'
        else:
            msg_type = 'mycroft.mic.unmute'
        self.bus.emit(message.reply(msg_type))

    def on_button_press(self):
        LOG.info("Listen button pressed")
        self.bus.emit(Message("mycroft.mic.listen"))

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

    def shutdown(self):
        self.switches.shutdown()

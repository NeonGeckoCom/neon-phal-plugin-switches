# PHAL Switches Plugin
Enables switch inputs for volume, mute, and action button. Current implementation
assumes switches match the SJ201 configuration of pull-up momentary switches (GND activated)
and a mute toggle where GND == unmuted.

## Default Pin Configuration
| Pin | Connection    |
|-----|---------------|
| 22  | Volume Up     |
| 23  | Volume Down   |
| 24  | Action Button |
| 25  | Mute Switch   |
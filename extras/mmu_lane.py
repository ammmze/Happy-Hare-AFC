from extras.mmu_toolhead import MmuToolHead, MmuHoming
from extras.mmu_sensors import MmuRunoutHelper
import logging

class MmuLane:
    def __init__(self, config):
        self.mmu = None
        self.printer = config.get_printer()

        # Currently hidden options or testing options...

        # By default HH uses its modified homing extruder. Because this might have unknown consequences on
        # certain set-ups if can be disabled. Homing moves will still work, but the delay in mcu to mcu comms
        # can lead to several mm of error depending on speed. Note that setting to 0 seems to provoke TTC errors!
        self.homing_extruder = config.getint('homing_extruder', 1, minval=0, maxval=1)


        self.mmu_toolhead = MmuToolHead(config, self, self.homing_extruder, has_selector=False, gear_stepper=config.get("stepper", "stepper_mmu_gear"))
        self.mmu_kinematics = self.mmu_toolhead.get_kinematics()
        rails = self.mmu_toolhead.get_kinematics().rails
        self.gear_rail = rails[1]
        self.gear_stepper = self.gear_rail.steppers[0]
        self.mmu_extruder_stepper = self.mmu_toolhead.mmu_extruder_stepper # Is MmuExtruderStepper if 'self.homing_extruder' is True

        # Setup filament homing sensors ------
        for name in [self.ENDSTOP_TOOLHEAD, self.ENDSTOP_GATE, self.ENDSTOP_EXTRUDER_ENTRY]:
            sensor = self.printer.lookup_object("filament_switch_sensor %s_sensor" % name, None)
            if sensor is not None:
                if name == self.ENDSTOP_TOOLHEAD or isinstance(sensor.runout_helper, MmuRunoutHelper):
                    self.sensors[name] = sensor

                    # Add sensor pin as an extra endstop for gear rail
                    sensor_pin = self.config.getsection("filament_switch_sensor %s_sensor" % name).get("switch_pin")
                    ppins = self.printer.lookup_object('pins')
                    pin_params = ppins.parse_pin(sensor_pin, True, True)
                    share_name = "%s:%s" % (pin_params['chip_name'], pin_params['pin'])
                    ppins.allow_multi_use_pin(share_name)
                    mcu_endstop = self.gear_rail.add_extra_endstop(sensor_pin, name)

                    # This ensures rapid stopping of extruder stepper when endstop is hit on synced homing
                    # otherwise the extruder can continue to move a small (speed dependent) distance
                    if self.homing_extruder and name == self.ENDSTOP_TOOLHEAD:
                        mcu_endstop.add_stepper(self.mmu_extruder_stepper.stepper)
                else:
                    logging.warn("Improper setup: Filament sensor %s is not defined in [mmu_sensors]" % name)


    def mmu(self):
        if self.mmu is None:
            self.mmu = self.printer.lookup_object('mmu')
        return self.mmu

    def log_stepper(self, msg):
        self.mmu.log_stepper(msg)

def load_config(config):
    return MmuLane(config)

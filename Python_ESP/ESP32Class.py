import math

class ESPLED:
    def __init__(self, ip, id, pot_value, pot_value_ps_1=None, pot_value_ps_2=None):
        """
        Initialize an ESP device.

        :param id: Unique ID for the ESP device
        :param ip: Unique IP for the ESP device
        :param brightness: Brightness level
        :param led_strips: List of tuples (strip_id, led_count, led_output_id) for each of the 4 LED strips
        """
        self.ip = ip
        self.id = id
        self.pot_value = pot_value
        # Only initialize these variables if self.id == 4
        #if self.id == 3:
        self.pot_value_ps_1 = pot_value_ps_1
        #elif self.id == 4:
        #self.pot_value_ps_1 = None
        self.pot_value_ps_2 = pot_value_ps_2
        
        self.response_data = None
        self.input_brightness_1 = 0
        self.input_brightness_2 = 0
        self.output_brightness_1 = 0
        self.output_brightness_2 = 0
        self.entanglement = 0
        self.entanglement2 = 0
        self.pulse1 = None
        self.pulse2 = None
        """self.pulse1_start = None
        self.pulse2_start = None
        self.pulse1_done = None
        self.pulse2_done = None
        """
        self.strobe1 = None
        self.strobe2 = None
    
    def get_output(self, input_brightness_1, input_brightness_2, previous_entanglement1, previous_entanglement2):#, input_pulse1_done, input_pulse2_done):
        # Initialise output variables
        self.input_brightness_1 = input_brightness_1
        self.input_brightness_2 = input_brightness_2

        """# Pulse logic
        if input_pulse1_done == True and input_pulse2_done == True:
            self.pulse1_start = True
            self.pulse2_start = True"""

        # Calculate brightness
        if self.id == 3:
            T = self.pot_value / 4095
            R = 1 - self.pot_value / 4095
            total_brightness = input_brightness_1 + input_brightness_2
            phaseVal1 = (self.pot_value_ps_1 / 4095) * 2 * math.pi
            self.output_brightness_1 = int(total_brightness* T) if self.output_brightness_1 >= 0 else 0
            self.output_brightness_2 = int(input_brightness_1 + input_brightness_2 * R) if self.output_brightness_2 >= 0 else 0
            # Update output data
            self.input_brightness_1 = input_brightness_1 if input_brightness_1 >= 0 else 0
            self.input_brightness_2 = input_brightness_2 if input_brightness_2 >= 0 else 0
            self.pot_value_ps_2 = round(phaseVal1, 3)

            # Entanglement logic
            if input_brightness_1 != 0 and input_brightness_2 != 0:
                self.entanglement = round((2*T*R*(1+math.cos(phaseVal1)))/(1+2*T*R),3)*20
            else:
                self.entanglement = 0

            # Previous entanglement
            if (previous_entanglement1 != 0 and input_brightness_2 == 0) or (
                    previous_entanglement2 != 0 and input_brightness_1 == 0):
                denominator = (T ** 2 - R ** 2) ** 2 + 4 * T ** 2 * R ** 2
                if denominator != 0:
                    pure_entanglement = (T ** 2 - R ** 2) ** 2 / denominator
                    self.entanglement = 20 * pure_entanglement
                else:
                    self.entanglement = 0

        elif self.id == 4:
            T1, R1 = input_brightness_1/77, (1-(input_brightness_1/77))
            T2, R2 = (self.pot_value / 4095), (1-(self.pot_value / 4095))
            phaseVal1 = (self.pot_value_ps_1 / 4095) * 2 * math.pi
            phaseVal2 = (self.pot_value_ps_2 / 4095) * 2 * math.pi
            self.output_brightness_1 = int((T1 * (T1*T2 + R1*R2 - (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(T1*T2*R1*R2))) + input_brightness_2/77 * (T1*T2 + R1*R2 - (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(T1*T2*R1*R2))))*77) if self.output_brightness_1 >= 0 else 0
            self.output_brightness_2 = int((T1 * (T1*R2 + R1*T2 + (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(T1*T2*R1*R2))) + input_brightness_2/77 * (T1*R2 + R1*T2 + (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(T1*T2*R1*R2))))*77) if self.output_brightness_2 >= 0 else 0
            # Update output data
            self.input_brightness_1 = input_brightness_1 if input_brightness_1 >= 0 else 0
            self.input_brightness_2 = input_brightness_2 if input_brightness_2 >= 0 else 0
            self.pot_value_ps_1 = round(phaseVal1, 3)
            self.pot_value_ps_2 = round(phaseVal2, 3)

            # Entanglement logic
            if input_brightness_1 != 0 and input_brightness_2 != 0:
                self.entanglement = round((2 * T2 * R2 * (1 + math.cos(phaseVal1))) / (1 + 2 * T2 * R2), 3) * 20
            else:
                self.entanglement = 0

            # Previous entanglement
            if (previous_entanglement1 != 0 and input_brightness_2 == 0) or (
                    previous_entanglement2 != 0 and input_brightness_1 == 0):
                denominator = (T2 ** 2 - R2 ** 2) ** 2 + 4 * T2 ** 2 * R2 ** 2
                if denominator != 0:
                    pure_entanglement = (T2 ** 2 - R2 ** 2) ** 2 / denominator
                    self.entanglement = 20 * pure_entanglement
                else:
                    self.entanglement = 0

        else:
            T = self.pot_value / 4095
            R = 1 - self.pot_value / 4095
            total_brightness = input_brightness_1 + input_brightness_2

            self.output_brightness_1 = int(total_brightness * T) if self.output_brightness_1 >= 0 else 0
            self.output_brightness_2 = int(total_brightness * R) if self.output_brightness_2 >= 0 else 0
            # Update output data
            self.input_brightness_1 = input_brightness_1 if input_brightness_1 >= 0 else 0
            self.input_brightness_2 = input_brightness_2 if input_brightness_2 >= 0 else 0

            # Entanglement logic
            if input_brightness_1 != 0 and input_brightness_2 != 0:
                self.entanglement = round((2 * T * R) / (1 + 2 * T * R), 3) * 20
            else:
                self.entanglement = 0

            # Previous entanglement
            if (previous_entanglement1 != 0 and input_brightness_2 == 0) or (
                    previous_entanglement2 != 0 and input_brightness_1 == 0):
                denominator = (T ** 2 - R ** 2) ** 2 + 4 * T ** 2 * R ** 2
                if denominator != 0:
                    pure_entanglement = (T ** 2 - R ** 2) ** 2 / denominator
                    self.entanglement = 20 * pure_entanglement
                else:
                    self.entanglement = 0

        # Pharse output data
        # Create the row in the correct fixed order
        csv_values = [
            self.input_brightness_1,
            self.input_brightness_2,
            self.output_brightness_1,
            self.output_brightness_2,
            self.pot_value_ps_1,
            self.pot_value_ps_2,
            self.entanglement,
            self.entanglement2,
            self.pulse1,
            self.pulse2,
            self.strobe1,
            self.strobe2
        ]

        """csv_values = [
            self.input_brightness_1,
            self.input_brightness_2,
            self.output_brightness_1,
            self.output_brightness_2,
            self.pot_value_ps_1,
            self.pot_value_ps_2,
            self.entanglement,
            self.pulse1_start,
            self.pulse2_start,
            self.pulse1_done,
            self.pulse2_done,
            self.strobe1,
            self.strobe2
        ]"""

        # Format each value: blank if None, otherwise rounded to 3 decimals
        self.response_data = ",".join("" if v is None else f"{v}" for v in csv_values)

    def __repr__(self):
        return f"ESPLED(id={self.id}, ip={self.ip}, pot_value={self.pot_value}, response_data={self.response_data})"

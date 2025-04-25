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
        self.pot_value_ps_1 = pot_value_ps_1
        self.pot_value_ps_2 = pot_value_ps_2

        self.phaseVal1 = 0
        self.phaseVal2 = 0
        
        self.response_data = None
        self.input_brightness_1 = 0
        self.input_brightness_2 = 0
        self.output_brightness_1 = 0
        self.output_brightness_2 = 0
        self.entanglement = 0
        self.entanglement2 = 0
        self.previous_entanglement1 = 0
        self.previous_entanglement2 = 0
        #self.pulse1 = None
        #self.pulse2 = None
        self.pulse_start = None
        self.refresh_rate = None
        self.strobe1 = None
        self.strobe2 = None
    
    def get_output(self, input_brightness_1, input_brightness_2, previous_entanglement1, previous_entanglement2, max_brightness):#, input_pulse1_done, input_pulse2_done):
        # Initialise output variables
        self.input_brightness_1 = input_brightness_1
        self.input_brightness_2 = input_brightness_2
        self.previous_entanglement1 = previous_entanglement1
        self.previous_entanglement2 = previous_entanglement2

        # Update output data
        self.input_brightness_1 = input_brightness_1 if input_brightness_1 >= 0 else 0
        self.input_brightness_2 = input_brightness_2 if input_brightness_2 >= 0 else 0

        # Update transmissivness and reflectivness
        T, R = (self.pot_value / 4095), (1 - (self.pot_value / 4095))

        total_brightness = self.input_brightness_1 + self.input_brightness_2

        # Calculate brightness
        if self.id == 3:
            self.phaseVal2 = round(((self.pot_value_ps_1 / 4095) * 2 * math.pi), 3)
            self.output_brightness_1 = int(total_brightness * T) if self.output_brightness_1 >= 0 else 0
            self.output_brightness_2 = int(total_brightness * R) if self.output_brightness_2 >= 0 else 0

            # Entanglement logic
            if input_brightness_1 != 0 and input_brightness_2 != 0:
                self.entanglement = round((2*T*R*(1+math.cos(self.phaseVal1)))/(1+2*T*R),3)*20
            else:
                self.entanglement = 0

        elif self.id == 4:
            T1, R1 = input_brightness_1/max_brightness, (1-(input_brightness_1/max_brightness))
            self.phaseVal1 = round(((self.pot_value_ps_1 / 4095) * 2 * math.pi), 3)
            self.phaseVal2 = round(((self.pot_value_ps_2 / 4095) * 2 * math.pi), 3)
            self.output_brightness_1 = int((T1 * (T1*T + R1*R - (2 * math.cos(self.phaseVal1-self.phaseVal2) * math.sqrt(T1*T*R1*R))) + input_brightness_2/max_brightness * (T1*T + R1*R - (2 * math.cos(self.phaseVal1-self.phaseVal2) * math.sqrt(T1*T*R1*R))))*max_brightness) if self.output_brightness_1 >= 0 else 0
            self.output_brightness_2 = int((T1 * (T1*R + R1*T + (2 * math.cos(self.phaseVal1-self.phaseVal2) * math.sqrt(T1*T*R1*R))) + input_brightness_2/max_brightness * (T1*R + R1*T + (2 * math.cos(self.phaseVal1-self.phaseVal2) * math.sqrt(T1*T*R1*R))))*max_brightness) if self.output_brightness_2 >= 0 else 0

            # Entanglement logic
            if input_brightness_1 != 0 and input_brightness_2 != 0:
                self.entanglement = round((2 * T * R * (1 + math.cos(self.phaseVal1 - self.phaseVal2))) / (1 + 2 * T * R), 3) * 20
            else:
                self.entanglement = 0

        else:
            self.output_brightness_1 = int(total_brightness * T) if self.output_brightness_1 >= 0 else 0
            self.output_brightness_2 = int(total_brightness * R) if self.output_brightness_2 >= 0 else 0

            # Entanglement logic
            if input_brightness_1 != 0 and input_brightness_2 != 0:
                self.entanglement = round((2 * T * R) / (1 + 2 * T * R), 3) * 20
            else:
                self.entanglement = 0

        # Previous entanglement for all ESPs
        if (self.previous_entanglement1 != 0 and input_brightness_2 == 0) or (self.previous_entanglement2 != 0 and input_brightness_1 == 0):
            denominator = (T ** 2 - R ** 2) ** 2 + 4 * T ** 2 * R ** 2
            #if self.id == 4:
            #    print(denominator)
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
            self.phaseVal1,
            self.phaseVal2,
            self.entanglement,
            self.entanglement2,
            self.pulse_start,
            self.refresh_rate,
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

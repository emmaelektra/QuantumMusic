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
        if self.id == 3:
            self.pot_value_ps_1 = pot_value_ps_1
        elif self.id == 4:
            self.pot_value_ps_1 = pot_value_ps_1
            self.pot_value_ps_2 = pot_value_ps_2
        
        self.response_data = None
        self.output_brightness_1 = 0
        self.output_brightness_2 = 0
        self.entanglement = 0
    
    def get_output(self, input_brightness_1, input_brightness_2):
        # Initialise output variables
        strip_1_bright = input_brightness_1
        strip_2_bright = input_brightness_2
        strip_3_bright = None
        strip_4_bright = None
        strip_1_phaseshift = None
        strip_2_phaseshift = None
        entanglement1 = None
        entanglement2 = None
        pulse1 = None
        pulse2 = None
        strobe1 = None
        strobe2 = None

        # Calculate brightness
        if self.id == 3:
            T = self.pot_value/4095
            R = 1-self.pot_value/4095
            phaseVal1 = (self.pot_value_ps_1 / 4095) * 2 * math.pi
            self.output_brightness_1 = int((input_brightness_1 + input_brightness_2) * T)
            self.output_brightness_2 = int((input_brightness_1 + input_brightness_2) * R)
            # Update output data
            strip_1_bright = input_brightness_1 if input_brightness_1 >= 0 else 0
            strip_2_bright = input_brightness_2 if input_brightness_2 >= 0 else 0
            strip_3_bright = self.output_brightness_1 if self.output_brightness_1 >= 0 else 0
            strip_4_bright = self.output_brightness_2 if self.output_brightness_2 >= 0 else 0
            strip_2_phaseshift = round(phaseVal1, 3)
            #if 0.3 <= (self.pot_value / 4095) <= 0.7 and input_brightness_1 != 0 and input_brightness_2 != 0:
            #    dif = abs(self.pot_value / 4095 - 0.5)
            if input_brightness_1 != 0 and input_brightness_2 != 0:
                self.entanglement = round((2*T*R*(1+math.cos(phaseVal1)))/(1+2*T*R),3)*20
                entanglement1 = int(self.entanglement)
            else:
                self.entanglement = 0
                entanglement1 = int(self.entanglement)
        elif self.id == 4:
            T1, R1 = input_brightness_1/77, (1-(input_brightness_1/77))
            T2, R2 = (self.pot_value / 4095), (1-(self.pot_value / 4095))
            phaseVal1 = (self.pot_value_ps_1 / 4095) * 2 * math.pi
            phaseVal2 = (self.pot_value_ps_2 / 4095) * 2 * math.pi
            self.output_brightness_1 = int((T1 * (T1*T2 + R1*R2 - (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(T1*T2*R1*R2))) + input_brightness_2/77 * (T1*T2 + R1*R2 - (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(T1*T2*R1*R2))))*77)
            self.output_brightness_2 = int((T1 * (T1*R2 + R1*T2 + (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(T1*T2*R1*R2))) + input_brightness_2/77 * (T1*R2 + R1*T2 + (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(T1*T2*R1*R2))))*77)
            # Update output data
            strip_1_bright = input_brightness_1 if input_brightness_1 >= 0 else 0
            strip_2_bright = input_brightness_2 if input_brightness_2 >= 0 else 0
            strip_3_bright = self.output_brightness_1 if self.output_brightness_1 >= 0 else 0
            strip_4_bright = self.output_brightness_2 if self.output_brightness_2 >= 0 else 0
            strip_1_phaseshift = round(phaseVal1, 3)
            strip_2_phaseshift = round(phaseVal2, 3)
            if input_brightness_1 != 0 and input_brightness_2 != 0:
                self.entanglement = round((2 * T2 * R2 * (1 + math.cos(phaseVal1))) / (1 + 2 * T2 * R2), 3) * 20
                entanglement1 = int(self.entanglement)
            else:
                self.entanglement = 0
                entanglement1 = int(self.entanglement)
        else:
            T = self.pot_value / 4095
            R = 1 - self.pot_value / 4095
            total_brightness = input_brightness_1 + input_brightness_2
            alpha = self.pot_value / 4095

            self.output_brightness_1 = int(total_brightness * alpha)
            self.output_brightness_2 = int(total_brightness * (1 - alpha))
            # Update output data
            strip_1_bright = input_brightness_1 if input_brightness_1 >= 0 else 0
            strip_2_bright = input_brightness_2 if input_brightness_2 >= 0 else 0
            strip_3_bright = self.output_brightness_1 if self.output_brightness_1 >= 0 else 0
            strip_4_bright = self.output_brightness_2 if self.output_brightness_2 >= 0 else 0
            if input_brightness_1 != 0 and input_brightness_2 != 0:
                self.entanglement = round((2 * T * R) / (1 + 2 * T * R), 3) * 20
                entanglement1 = int(self.entanglement)
            else:
                self.entanglement = 0
                entanglement1 = int(self.entanglement)

        # Pharse output data
        # Create the row in the correct fixed order
        csv_values = [
            strip_1_bright,
            strip_2_bright,
            strip_3_bright,
            strip_4_bright,
            strip_1_phaseshift,
            strip_2_phaseshift,
            entanglement1,
            entanglement2,
            pulse1,
            pulse2,
            strobe1,
            strobe2
        ]

        # Format each value: blank if None, otherwise rounded to 3 decimals
        self.response_data = ",".join("" if v is None else f"{v}" for v in csv_values)

    def __repr__(self):
        return f"ESPLED(id={self.id}, ip={self.ip}, pot_value={self.pot_value}, response_data={self.response_data})"

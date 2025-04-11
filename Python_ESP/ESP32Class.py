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

        # Check for entaglement
        if 0.3 <= (self.pot_value / 4095) <= 0.7 and input_brightness_1 != 0 and input_brightness_2 != 0:
            dif = abs(self.pot_value / 4095 - 0.5)
            entanglement = 2*(1 + round(dif * 45))
        else:
            entanglement = 0
        # Calculate brightness
        if self.id == 3:
            phaseVal1 = (self.pot_value_ps_1 / 4095) * 2 * math.pi
            self.output_brightness_1 = int((input_brightness_1 / 77 * (
                        self.pot_value / 4095) + input_brightness_2 / 77 * (self.pot_value / 4095)) * 77)
            self.output_brightness_2 = int((input_brightness_1 / 77 * (
                        77 - self.output_brightness_1) / 77 + input_brightness_2 / 77 * (
                                                        77 - self.output_brightness_1) / 77) * 77)
            # Update output data
            strip_1_bright = input_brightness_1
            strip_2_bright = input_brightness_2
            strip_3_bright = self.output_brightness_1
            strip_4_bright = self.output_brightness_2
            strip_2_phaseshift = round(phaseVal1, 3)
            entanglement1 = int(entanglement)
        elif self.id == 4:
            potVal1 = input_brightness_1/77
            potVal2 = (self.pot_value / 4095)
            phaseVal1 = (self.pot_value_ps_1 / 4095) * 2 * math.pi
            phaseVal2 = (self.pot_value_ps_2 / 4095) * 2 * math.pi
            self.output_brightness_1 = int((input_brightness_1/77 * (potVal1*potVal2 + (1-potVal1)* (1-potVal2) - (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(potVal1*potVal2*(1-potVal1)*(1-potVal2)))) + input_brightness_2/77 * (potVal1*potVal2 + (1-potVal1)* (1-potVal2) - (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(potVal1*potVal2*(1-potVal1)*(1-potVal2)))))*77)
            self.output_brightness_2 = int((input_brightness_1/77 * (potVal1*(1-potVal2) + potVal2*(1-potVal1) + (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(potVal1*potVal2*(1-potVal1)*(1-potVal2)))) + input_brightness_2/77 * (potVal1*(1-potVal2) + potVal2*(1-potVal1) + (2 * math.cos(phaseVal1-phaseVal2) * math.sqrt(potVal1*potVal2*(1-potVal1)*(1-potVal2)))))*77)
            # Update output data
            strip_1_bright = input_brightness_1
            strip_2_bright = input_brightness_2
            strip_3_bright = self.output_brightness_1
            strip_4_bright = self.output_brightness_2
            strip_1_phaseshift = round(phaseVal1, 3)
            strip_2_phaseshift = round(phaseVal2, 3)
            entanglement1 = int(entanglement)
        else:
            self.output_brightness_1 = int((input_brightness_1 / 77 * (self.pot_value / 4095) + input_brightness_2 / 77 * (self.pot_value / 4095)) * 77)
            self.output_brightness_2 = int((input_brightness_1 / 77 * (77 - self.output_brightness_1)/77 + input_brightness_2 / 77 * (77 - self.output_brightness_1)/77) * 77)
            # Update output data
            strip_1_bright = input_brightness_1
            strip_2_bright = input_brightness_2
            strip_3_bright = self.output_brightness_1
            strip_4_bright = self.output_brightness_2
            entanglement1 = int(entanglement)

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

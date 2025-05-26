import math
import cmath

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
        self.input_intensity1 = 0
        self.input_intensity2 = 0
        self.output_intensity1 = 0
        self.output_intensity2 = 0
        self.Ein_1 = 0
        self.Ein_2 = 0
        self.Eout_1 = 0
        self.Eout_2 = 0
        self.entanglement = 0
        self.pulse_start1 = None
        self.previous_entanglement1 = 0
        self.previous_entanglement2 = 0
        #self.pulse1 = None
        #self.pulse2 = None
        self.pulse_start2 = None
        self.pulse_start3 = None
        self.max_brightness = 0
        self.strobe1 = None
        self.strobe2 = None

        self.t = 0
        self.r = 0


    def get_output(self, Ein_1, Ein_2, max_brightness):
        # Initialise output variables
        self.t, self.r = self.pot_value / 4095, 1 - (self.pot_value / 4095)
        self.max_brightness = max_brightness

        # Beam splitter transformations
        if self.id == 3:
            self.phaseVal2 = round(((self.pot_value_ps_1 / 4095) * 2 * math.pi), 3)
            Ein2_ps = Ein_2 * cmath.exp(1j * self.phaseVal2)

            self.Eout_1 = math.sqrt(self.r) * Ein_1 + math.sqrt(self.t) * Ein2_ps
            self.Eout_2 = math.sqrt(self.t) * Ein_1 - math.sqrt(self.r) * Ein2_ps

        elif self.id == 4:
            self.phaseVal1 = round(((self.pot_value_ps_1 / 4095) * 2 * math.pi), 3)
            self.phaseVal2 = round(((self.pot_value_ps_2 / 4095) * 2 * math.pi), 3)
            Ein1_ps = Ein_1 * cmath.exp(1j * self.phaseVal1)
            Ein2_ps = Ein_2 * cmath.exp(1j * self.phaseVal2)

            self.Eout_1 = math.sqrt(self.r) * Ein1_ps + math.sqrt(self.t) * Ein2_ps
            self.Eout_2 = math.sqrt(self.t) * Ein1_ps - math.sqrt(self.r) * Ein2_ps

        else:
            self.Eout_1 = math.sqrt(self.r) * Ein_1 + math.sqrt(self.t) * Ein_2
            self.Eout_2 = math.sqrt(self.t) * Ein_1 - math.sqrt(self.r) * Ein_2

        # Calculate intensities for all ESPs
        self.input_intensity1 = int(abs(Ein_1) ** 2)
        self.input_intensity2 = int(abs(Ein_2) ** 2)

        self.output_intensity1 = int(abs(self.Eout_1) ** 2)
        self.output_intensity2 = int(abs(self.Eout_2) ** 2)
 
        # Pharse output data
        # Create the row in the correct fixed order
        csv_values = [
            self.input_intensity1,
            self.input_intensity2,
            self.output_intensity1,
            self.output_intensity2,
            self.phaseVal1,
            self.phaseVal2,
            self.entanglement,
            self.pulse_start1,
            self.pulse_start2,
            self.pulse_start3,
            self.max_brightness,
            self.strobe1,
            self.strobe2
        ]

        # Format each value: blank if None, otherwise rounded to 3 decimals
        self.response_data = ",".join("" if v is None else f"{v}" for v in csv_values)

    def __repr__(self):
        return f"ESPLED(id={self.id}, ip={self.ip}, pot_value={self.pot_value}, response_data={self.response_data})"

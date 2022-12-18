import gdspy
from picwriter import toolkit as tk
#import custom_components as cc
import StaggeredMetalTemplate as cc
import numpy as np

# Based off of the Bondpad class from https://github.com/DerekK88/PICwriter/blob/master/picwriter/components/electrical.py
class StaggeredBondpad(tk.Component):
    """Standard Bondpad Cell class.
    Args:
       * **mt** (MetalTemplate):  WaveguideTemplate object
    Keyword Args:
       * **length** (float): Length of the bondpad.  Defaults to 150
       * **width** (float): Width of the bondpad.  Defaults to 100
       * **port** (tuple): Cartesian coordinate of the input port.  Defaults to (0,0).
       * **direction** (string): Direction that the taper will point *towards*, must be of type `'NORTH'`, `'WEST'`, `'SOUTH'`, `'EAST'`.  Defaults to `'EAST'`.
    Members:
       * **portlist** (dict): Dictionary with the relevant port information
    Portlist format:
       * portlist['output'] = {'port': (x1, y1), 'direction': 'dir'}
    Where in the above (x1,y1) is the same as the 'port' input, and 'dir' is the same as 'direction' input of type `'NORTH'`, `'WEST'`, `'SOUTH'`, `'EAST'`.
    """

    def __init__(
                self, 
                template : cc.StaggeredMetalTemplate, 
                length=150, 
                width=100, 
                potentialRatios = [1, 2 / 3, 1 / 3], 
                lengthRatios = [1 / 3, 1 / 3, 1 / 3], 
                staggaredThickness = True, 
                staggaredCladding = False, 
                staggaredWidth = False, 
                port=(0, 0), 
                direction="EAST", 
                seperation = [0, 0, 0], 
                cladSeperation = [False, False, False]
            ):
        assert len(lengthRatios) == len(potentialRatios)
        assert len(lengthRatios) == len(template.metal_layers)
        tk.Component.__init__(self, "StaggeredBondpad", locals())

        self.portlist = {}

        self.length = length
        self.width = width
        self.port = port
        self.direction = direction
        self.template = template
        self.potentialRatios = potentialRatios 
        self.lengthRatios = lengthRatios 
        self.staggaredThickness = staggaredThickness 
        self.staggaredCladding = staggaredCladding 
        self.staggaredWidth = staggaredWidth 
        self.maxCladdingWidth = self.template.clad_width * np.max(np.array(self.potentialRatios))
        self.seperation = seperation
        self.cladSeperation = cladSeperation
        self.spec = {"layers": template.metal_layers, "datatype": template.metal_datatype}
        self.clad_spec = {"layers": template.clad_layers, "datatype": template.clad_datatype}

        self.__build_cell()
        self.__build_ports()

        """ Translate & rotate the ports corresponding to this specific component object
        """
        self._auto_transform_()

    def __build_cell(self):
        # Sequentially build all the geometric shapes using gdspy path functions
        # for waveguide, then add it to the Cell
        template = self.template
        scanLength = 0
        for ii in range(len(self.lengthRatios)): 
                width = (self.width * self.potentialRatios[ii]) if self.staggaredWidth else self.width
                claddingWidth = self.template.clad_width * self.potentialRatios[ii] if self.staggaredCladding else self.template.clad_width
                seperation = (self.length * self.seperation[ii])
                print("sep: ", seperation)
                nextLength = (self.lengthRatios[ii] * self.length)
                print("l: ", nextLength)
                length = scanLength + nextLength
                self.add(gdspy.Rectangle(
                        (scanLength + (seperation / 2), -width / 2.0), 
                        (length + (seperation / 2), width / 2.0), 
                        self.spec["layers"][ii], 
                        self.spec["datatype"]
                    ))
                seperationCladding = ((seperation / 2) > claddingWidth) and (self.cladSeperation[ii] == True)
                print(seperation / 2, claddingWidth)
                print(((seperation / 2) > claddingWidth), (self.cladSeperation[ii] == True))
                end = 1 if ii == (len(self.lengthRatios) - 1) or seperationCladding == True else 0
                start = 1 if ii == 0 or seperationCladding else 0
                claddingBaseWidth = width if self.staggaredWidth and self.staggaredCladding == True else self.width
                print("SE", seperationCladding, start, end)
                self.add(gdspy.Rectangle(
                       (((seperation / 2) + scanLength - (start * claddingWidth)), -claddingBaseWidth / 2.0 - claddingWidth), 
                       (((seperation / 2) + length + (end * claddingWidth)), claddingBaseWidth / 2.0 + claddingWidth), 
                       self.clad_spec["layers"][ii], 
                       self.clad_spec["datatype"]
                   ))
                scanLength = length + seperation

    def __build_ports(self):
        # Portlist format:
        # example: example:  {'port':(x_position, y_position), 'direction': 'NORTH'}
        self.portlist["output"] = {"port": (0, 0), "direction": "EAST"}

if __name__ == "__main__": 
    import picwriter.components as pc
    waveGuideTemplate = pc.WaveguideTemplate()
    waveguide = pc.Waveguide([(0, 500), (1000, 500)], waveGuideTemplate)
    staggaredMetalTemplate = cc.StaggeredMetalTemplate()
    thicknessStaggardBondPad = StaggeredBondpad(staggaredMetalTemplate)
    widthStaggardBondPad = StaggeredBondpad(
            staggaredMetalTemplate, 
            staggaredThickness = False, 
            staggaredWidth = True, 
            port = (1000, 1000)
        )
    claddingStaggardBondPad = StaggeredBondpad(
            staggaredMetalTemplate, 
            staggaredThickness = False, 
            staggaredCladding = True, 
            port = (0, 1000)
        )
    claddingAndWidthStaggardBondPad = StaggeredBondpad(
            staggaredMetalTemplate, 
            staggaredThickness = False, 
            staggaredWidth = True, 
            staggaredCladding = True, 
            port = (1000, 0)
        )
    smallSeperationBondPad = StaggeredBondpad(
            staggaredMetalTemplate, 
            port = (0, 2000), 
            seperation = [.05, .05, .05]
        )
    largerSeperationBondPad = StaggeredBondpad(
            staggaredMetalTemplate, 
            port = (1000, 2000), 
            seperation = [.30, .30, .30], 
            cladSeperation = [True, True, True]
        )
    largerSeperationNoSeperationCladdingBondPad = StaggeredBondpad(
            staggaredMetalTemplate, 
            port = (2000, 2000), 
            seperation = [.30, .30, .30]
        )
    top = gdspy.Cell("top")
    tk.add(top, thicknessStaggardBondPad)
    tk.add(top, widthStaggardBondPad)
    tk.add(top, claddingStaggardBondPad)
    tk.add(top, claddingAndWidthStaggardBondPad)
    tk.add(top, smallSeperationBondPad)
    tk.add(top, largerSeperationBondPad)
    tk.add(top, largerSeperationNoSeperationCladdingBondPad) 
    tk.add(top, waveguide)
    tk.build_mask(top, waveGuideTemplate, final_layer = 17, final_datatype = 0)
    gdspy.LayoutViewer()


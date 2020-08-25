import numpy as np
import gdspy as gd
import gds_tools as gtools

#================================================
# Define healing function for transmission lines \\
#=========================================================================
# Initialization:   radius      :   radius of healing circle            ||
#                   endpoint    :   (x, y) of circle center             ||
#       (optional)  npoints     :   number of points to use for circum. ||
#       (optional)  layer       :   layer to put healer on              ||
#=========================================================================
def circle(radius, endpoint, npoints = 100, layer = 0, datatype = 0):

    c = gd.Round(endpoint, radius, number_of_points = npoints, layer = layer, datatype = datatype)
    c = gtools.classes.GDStructure(c, {'A': endpoint}, {'A': 2*radius})

    return c

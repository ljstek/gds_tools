import copy
import gdspy
import numpy as np
from operator import add, sub
from recordclass import recordclass

import gds_tools as gtools

class GDStructure:

    def __init__(self, structure, endpoints, endpoint_dims, endpoint_directions = None, method = None, args = {}):
        """Define class to store structures in

        Args:
            structure (gdspy.Path()): gdspy description of object (i.e. ouput of gdspy.PolyPath()).
            endpoints (dict): positions of the endpoints to which you connect other structures.
            endpoint_dims (dict): dimensions of the endpoints (width/height/etc.), to be used for connecting e.g. transmission lines.
            endpoint_directions ([type], optional): [description]. Defaults to None.
            method ([type], optional): [description]. Defaults to None.
            args (dict, optional): [description]. Defaults to {}.
        """

        self.type = 'GDStructure'
        self.structure = structure
        self.endpoints = endpoints
        self.endpoint_dims = endpoint_dims
        self.endpoint_directions = endpoint_directions
        self.compound = []
        self.prev = {}
        self.next = {}
        self.method = method

        self.__args_tuple__ = recordclass('args', args.keys())
        self.args = self.__args_tuple__(**args)

        self.gen = self.generate

    def generate(self):
        if self.method != None:
            return self.method(**self.args.__dict__)
        else:
            raise TypeError('This GDStructure does not support the .generate() method (yet)')

    def copy(self):
        """Makes a new copy of the structure,
        i.e. allocates new memory and copies the data contents to it.

        Returns:
        gds_tools.GDStructure: pointer of copy of original
        """

        # Create deepcopy of self and return the copy
        # Do not copy.deepcopy(self) directly, as this will also copy the connections and screw things up
        # Instead, just fill a new instance of the class with copies of relevant internal structure
        new_obj = gtools.classes.GDStructure(copy.deepcopy(self.structure), copy.deepcopy(self.endpoints), copy.deepcopy(self.endpoint_dims), copy.deepcopy(self.endpoint_directions))

        compound = []
        for i, c in enumerate(self.compound):
            c_copy = c.copy()
            compound.append(c_copy)
            new_obj.next[i] = c_copy

        new_obj.compound = compound

        return new_obj

    #==================
    # Rotate structure \\
    #=========================================================================
    # When rotating, all endpoints need to move wih the rotation,           ||
    # for this reason we need our own rotation function.                    ||
    #                                                                       ||
    # Arguments:    rad         :   amount of radians to rotate             ||
    #               signal_from :   tells linked structure who sent command ||
    #=========================================================================
    def rotate(self, rad, signal_from = None):

        if not isinstance(signal_from, list):
            signal_from = [signal_from]

        # Rotate the structure with standard gdspy .rotation() function
        if self not in signal_from:
            signal_from.append(self)
        self.structure.rotate(rad)

        # Rotate the endpoints
        for i in self.endpoints:
            self.endpoints[i] = tuple(gtools.funcs.VecRot(rad, self.endpoints[i]))
            if self.endpoint_directions:
                self.endpoint_directions[i] += rad

        # Rotate all connected structures
        for i in self.prev:
            if self.prev[i] not in signal_from and self.prev:
                signal_from.append(self.prev[i])
                self.prev[i].rotate(rad, signal_from = signal_from)

        for i in self.next:
            if self.next[i] not in signal_from and self.next:
                signal_from.append(self.next[i])
                self.next[i].rotate(rad, signal_from = signal_from)

        return self

    #=====================
    # Get structure layer \\
    #=========================================================================
    # Gdspy has some inconsistencies in how it stores layers, this getter   ||
    # function should make life easier to obtain the layer of the object    ||
    # stored in self.structure                                              ||
    #=========================================================================
    def getlayer(self):
        return self.structure.layers[0] if hasattr(self.structure, 'layers') else (self.structure.layer if hasattr(self.structure, 'layer') else 0)

    #=====================
    # Translate structure \\
    #=========================================================================
    # Arguments:    delta       :   vector (x, y) how much you want to move ||
    #               signal_from :   tells linked structure who sent command ||
    #=========================================================================
    def translate(self, delta, signal_from = None):

        if not isinstance(signal_from, list):
            signal_from = [signal_from]

        # Translate structure with standard gdspy .translate() function
        if self not in signal_from:
            signal_from.append(self)
        self.structure.translate(delta[0], delta[1])

        # Translate all the endpoints
        for i in self.endpoints:
            self.endpoints[i] = tuple(map(add, self.endpoints[i], delta))

        # Translate all connected structures
        for i in self.prev:
            if self.prev[i] not in signal_from and self.prev:
                signal_from.append(self.prev[i])
                self.prev[i].translate(delta, signal_from = signal_from)

        for i in self.next:
            if self.next[i] not in signal_from and self.next:
                signal_from.append(self.next[i])
                self.next[i].translate(delta, signal_from = signal_from)

        return self

    #=====================
    # Mirror structure \\
    #=========================================================================
    # Arguments:    p1, p2  :   p1 and p2 are (x, y) coords forming         ||
    #                           the mirror line                             ||
    #=========================================================================
    def mirror(self, p1, p2, signal_from = None):

        if not isinstance(signal_from, list):
            signal_from = [signal_from]

        # Mirror the gdspy shape
        if self not in signal_from:
            signal_from.append(self)
        self.structure.mirror(p1, p2 = p2)

        # Process the endpoints
        for k, v in self.endpoints.items():

            p1 = list(p1)
            p2 = list(p2)

            if p1[0] == p2[0]:
                p1[0] += 1E-20

            if p1[1] == p2[1]:
                p1[1] += 1E-20

            # y = ax + c : mirror line
            a = (p2[1] - p1[1]) / (p2[0] - p1[0])
            c = p1[1] - a * p1[0]
            d = (v[0] + (v[1] - c)*a) / (1 + a**2)

            v2x = 2*d - v[0]
            v2y = 2*d*a - v[1] + 2*c

            self.endpoints[k] = (v2x, v2y)

        # Ripple through all connected shapes
        for i in self.prev:
            if self.prev[i] not in signal_from and self.prev:
                signal_from.append(self.prev[i])
                self.prev[i].mirror(p1, p2, signal_from = signal_from)

        for i in self.next:
            if self.next[i] not in signal_from and self.next:
                signal_from.append(self.next[i])
                self.next[i].mirror(p1, p2, signal_from = signal_from)

        return self

    #=================
    # Heal connection \\
    #=========================================================================
    # When connection endpoints, there is always a little space that is not ||
    # overlapped. This function will fill this overlap.                     ||
    #                                                                       ||
    # Arguments:    endpoint    :   (x, y) center of healer                 ||
    #    (optional) npoints     :   number of points to use for boundary    ||
    #=========================================================================
    def heal(self, endpoint, npoints = 100, r = 'auto', layer = None, datatype = None):

        if type(r) == str and r == 'auto':
            r = self.endpoint_dims[endpoint] / 2

        healer = gtools.heal.circle(r, self.endpoints[endpoint], npoints = npoints, layer = layer if layer != None else self.getlayer(), datatype = datatype if datatype != None else self.structure.datatypes[0])

        self.prev['HEAL_' + endpoint] = healer
        self.compound += [healer]

        return self

    #===================
    # Connect structure \\
    #=========================================================================
    # Arguments:    ep_self :   reference to A, B, C, etc.                  ||
    #                           name of endpoint of this structure          ||
    #               to      :   GDStructure class input to which to connect ||
    #               ep_to   :   endpoint to which to connect to             ||
    #               offset  :   (x, y) offset from target endpoints         ||
    #               obj_link:   use Python object reference for linked list ||
    #                           entry rather than endpoint key              ||
    #=========================================================================
    def connect(self, ep_self, to, ep_to, offset = (0, 0), obj_link = False, rotate = True):

        # Rotate to correct orientation
        if self.endpoint_directions != None and to.endpoint_directions != None and self.endpoint_directions and to.endpoint_directions and rotate:
            self.rotate((to.endpoint_directions[ep_to] - self.endpoint_directions[ep_self] - np.pi) % (2 * np.pi))

        # Move to connect endpoints
        delta = tuple(map(sub, to.endpoints[ep_to], self.endpoints[ep_self]))
        delta = tuple(map(add, delta, offset))
        self.mov(delta)

        # Update linked list
        if not obj_link:
            to.next[ep_to] = self
            self.prev[ep_self] = to
        else:
            to.next[self] = self
            self.prev[to] = to

        return self

    #======================
    # Disconnect structure \\
    #=========================================================================
    # Only removes the references in the linked lists                       ||
    #=========================================================================
    def disconnect(self):

        for e in self.endpoints:
            if e in self.next:
                for ne in self.next[e].endpoints:
                    if ne in self.next[e].prev and self.next[e].prev[ne] == self:
                        del self.next[e].prev[ne]
                del self.next[e]
            if e in self.prev:
                for pe in self.prev[e].endpoints:
                    if pe in self.prev[e].next and self.prev[e].next[pe] == self:
                        del self.prev[e].next[pe]
                del self.prev[e]

        return self

    # Aliases
    rot = rotate
    mov = translate
    con = connect
    dis = disconnect

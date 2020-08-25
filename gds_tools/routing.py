import numpy as np
import scipy.spatial as sp
import copy
import gdspy as gd
import gds_tools as gtools

#===========================
# Make a transmission line  \\
#=========================================================================
# Arguments:    dxy         :   (dx, dy), lengths of the line           ||
#               width       :   width of the line                       ||
#    (optional) width_end   :   different width at the end              ||
#    (optional) layer       :   choose layer to put spiral onto         ||
#=========================================================================
def line(dxy, width, width_end = False, layer = 0, datatype = 0):

    width_end = width if (not width_end) else width_end

    p = [(0, 0), dxy]
    w = [width, width_end]

    poly = gd.PolyPath(p, w, layer = layer, datatype = datatype)
    ends = {'A': p[0], 'B': p[-1]}
    epsz = {'A': w[0], 'B': w[-1]}

    return gtools.classes.GDStructure(poly, ends, epsz)

#================================================
# Generate a meander \\ Author: Marta Pita Vidal \\
#=========================================================================
# Arguments:    n               :   number of meanders                  ||
#               width           :   width of the meander path           ||
#               radius          :   radius of the corner circles        ||
#               meander_length  :   length from corner to corner        ||
#               connect_length  :   length of initial transmission line ||
#    (optional) layer           :   layer to put meander on             ||
#=========================================================================
def meander(n, width, radius, meander_length, connect_length, layer = 0):

    # Aliases
    w = width
    d = radius
    N = n
    position = (0, 0)
    xMeander = meander_length / 2
    yBase = connect_length

    # Start path
    meander_path = gd.Path(w, (0, 0))
    meander_path.segment(yBase, np.pi/2, layer = layer).turn(w/2, 'r', layer = layer).segment(xMeander - w/2, layer = layer).turn(d, 'll', layer = layer).segment(xMeander, layer = layer)

    # Generate periodic meanders
    for i in range(N - 1):
        meander_path.segment(xMeander, layer = layer).turn(d, 'rr', layer = layer).segment(2 * xMeander, layer = layer).turn(d, 'll', layer = layer).segment(xMeander, layer = layer)

    # Finalize
    meander_path.segment(xMeander, layer = layer).turn(d, 'rr', layer = layer).segment(xMeander - w/2, layer = layer).turn(w/2, 'l', layer = layer).segment(yBase, '+y', layer = layer)

    # Create object
    struct = gtools.classes.GDStructure(meander_path, {'A': (0, 0), 'B': (meander_path.x, meander_path.y)}, {'A': w, 'B': w})

    return struct

#===================================
# Make a transmission line splitter \\
#=========================================================================
# Arguments:    n       :   number of splits                            ||
#               width   :   width of the paths                          ||
#               length  :   total length from start to end              ||
#               space   :   spacing between splits                      ||
#    (optional) layer   :   choose layer to put split onto              ||
#=========================================================================
def splitter(n, width, length, space, layer = 0):

    p = [(0, 0), (length / 2 - width / 2, 0), (length / 2 - width / 2, (n*width + (n-1)*space)/2 - width / 2)]

    ends = {'A': (0, -width / 2)}
    epsz = {'A': width}

    for i in range(0, n):
        p += [(length, (n*width + (n-1)*space)/2 - i*(space + width) - width / 2)]

        ends[gtools.alphabet[i + 1]] = (length, p[-1][1] - width / 2)
        epsz[gtools.alphabet[i + 1]] = width

        p += [(length, (n*width + (n-1)*space)/2 - i*(space + width) - width - width / 2)]
        p += [(length / 2 + width / 2, (n*width + (n-1)*space)/2 - i*(space + width) - width - width / 2)]
        p += [(length / 2 + width / 2, (n*width + (n-1)*space)/2 - i*(space + width) - width - space - width / 2)]

    p = p[:-1]

    p += [(length / 2 - width / 2, (n*width + (n-1)*space)/2 - (n-1)*(space + width) - width - width / 2)]
    p += [(length / 2 - width / 2, -width)]
    p += [(0, -width)]

    poly = gd.Polygon(p, layer = layer)

    return gtools.classes.GDStructure(poly, ends, epsz)

# Helper function, returns indeces of neighbouring points (u, d, l, r) in a grid
def lookaround(index, row_len, pref = 'y'):

    n = []
    n.append(index - row_len)
    n.append(index + row_len)
    if index % row_len != 0:
        n.append(index - 1)
    n.append(index + 1)

    if pref == 'x':
        n = n[::-1]

    return n

# Autoroute using Lee's routing algorithm
def router(cell, fr_str, fr_ep, to_str, to_ep, width, bmul, grid_s = 1, xr = False, yr = False, uniform_width = False, precision = 0.001, pref = 'y', switch_pref = False, layer = 0, debug = False, nop = 21, dist_multi = 2, pathmethod = 'poly', detect = 'native'):

    fr = fr_str.endpoints[fr_ep]
    to = to_str.endpoints[to_ep]

    border_s = bmul * grid_s
    box = [fr, to]

    # Make sure first box coord is always the top-left corner and add additional border points
    xs = [box[0][0], box[1][0]]
    ys = [box[0][1], box[1][1]]
    box = [[min(xs) - border_s, max(ys) + border_s], [max(xs) + border_s, min(ys) - border_s]]

    # Build list of gridpoints that are outside all structures in cell
    lxr = int((box[1][0] - box[0][0]) / grid_s) + 1
    lyr = int((box[0][1] - box[1][1]) / grid_s) + 1

    if type(xr) not in [list, np.ndarray]:
        xr = np.linspace(box[0][0], box[1][0], lxr)
    else:
        lxr = len(xr)

    if type(yr) not in [list, np.ndarray]:
        yr = np.linspace(box[0][1], box[1][1], lyr)
    else:
        lyr = len(yr)

    p = []
    p_d_to = []
    p_d_fr = []
    for y in yr:
        for x in xr:

            c = (x, y)
            p.append(c)

            # Compute squared Euclidean distance from to and fr coords for each gridpoint
            # For optimization we don't need to sqrt() since minimal in squared is minimal in sqrt
            dist_fr = (x - fr[0])**2 + (y - fr[1])**2
            dist_to = (x - to[0])**2 + (y - to[1])**2

            p_d_fr.append(dist_fr)
            p_d_to.append(dist_to)

    p_i = np.array(p)
    p_d_fr = np.array(p_d_fr)
    p_d_to = np.array(p_d_to)

    # Build list of points that are inside a structure
    cell_ref = gd.CellReference(cell)
    if detect == 'native':
        inside = np.array(gd.inside(p, cell_ref, precision = precision))
    elif detect == 'custom':
        inside = np.array(gtools.funcs.inside(p, cell_ref, dist = dist_multi*grid_s, nop = nop, precision = precision))
    else:
        raise ValueError('Parameter \'detect\' is only allowed to have values [\'native\', \'custom\'], cannot continue')

    p_d_fr_min = np.min(p_d_fr[np.argwhere(inside == False)])
    p_d_to_min = np.min(p_d_to[np.argwhere(inside == False)])

    # Get p_i index of starting values
    start_i = np.argwhere(p_d_fr == p_d_fr_min).tolist()
    end_i = np.argwhere(p_d_to == p_d_to_min).tolist()

    start_i = [item for sublist in start_i for item in sublist]
    end_i = [item for sublist in end_i for item in sublist]

    start = p_i[start_i]
    end = p_i[end_i]

    # Now start stepping from start to end, labelling all gridpoints accordingly by the number of steps required from starting point to reach it
    n = [0] * 4
    lp = len(p)
    p_g = [0] * lp
    path_found = False
    k = 0

    while not path_found and start_i:

        k += 1
        next_start_i = []

        if debug:
            print(start_i)

        for i in start_i:

            # Look up, down, left and right, store the index
            n = lookaround(i, lxr, pref = pref)

            # Check if any of the neighbouring points are not in a structure and not in p_g
            for nb in n:

                if nb in end_i:
                    path_found = True
                    p_g[nb] = k
                    final_index = nb

                    if debug:
                        # Visualize
                        circ = gd.Round(p[nb], 0.1, layer = 10)
                        cell.add(circ)
                        txt = gd.Text(str(k), 0.5, p[nb], layer = 11)
                        cell.add(txt)

                    break

		         # Point is out of bounds, marked as structure (< 0) or already has a step value (> 0)
                if nb < 0 or nb >= lp or p_g[nb] != 0 or (i % lxr == 0 and nb % lxr == 1) or (i % lxr == 1 and nb % lxr == 0):
                    continue # Skip this iteration

                if inside[nb]:
                    p_g[nb] = -1
                else:
                    p_g[nb] = k
                    next_start_i.append(nb)

                    if debug:
                        # Visualize
                        circ = gd.Round(p[nb], 0.1, layer = 1)
                        cell.add(circ)
                        txt = gd.Text(str(k), 0.5, p[nb], layer = 2)
                        cell.add(txt)

        start_i = copy.copy(next_start_i)

    # Routing ended, checking whether we succeeded
    if not path_found:
        print('>> ERROR: No existing route was found.')
        return False

    print('>> Found a route in ' + str(k) + ' steps.')

    # Backtrace path
    this_index = final_index
    backtraced = [to, p[final_index]]
    switched = False
    for this_k in range(k, -1, -1):

        # Change move preference after switch_pref moves
        if switch_pref and not switched and this_k < switch_pref*k:
            pref = 'x' if pref == 'y' else 'y'
            switched = True

        n = lookaround(this_index, lxr, pref = pref)
        for nb in n:
            if nb < lp and p_g[nb] == this_k:
                this_index = nb
                backtraced.append(p[nb])
                break

    backtraced.append(fr)

    if debug:
        print('>> Points of found route:')
        print(backtraced)

    # Generate list of widths for the route
    if not uniform_width:
        to_w = to_str.endpoint_dims[to_ep]
        fr_w = fr_str.endpoint_dims[fr_ep]
        ws = [to_w if to_w != None else width]*2 + [width]*(len(backtraced)-4) + [fr_w if fr_w != None else width]*2
    else:
        ws = width

    # Create backtraced path
    if pathmethod == 'poly':
        r = gd.PolyPath(backtraced, ws, layer = layer)
    elif pathmethod == 'flex':
        r = gd.FlexPath(backtraced, ws, corners = 'smooth', layer = layer)
    else:
        raise ValueError('Parameter \'pathmethod\' only has allowed values [\'poly\', \'flex\']')

    ends = {'A': backtraced[0], 'B': backtraced[-1]}
    epsz = {'A': ws[0] if not uniform_width else width, 'B': ws[-1] if not uniform_width else width}

    structure = gtools.classes.GDStructure(r, ends, epsz)

    # Connect to 'to' and 'from' structures
    fr_str.next['AUTOROUTE_A'] = structure
    to_str.next['AUTOROUTE_B'] = structure
    structure.prev['AUTOROUTE_A'] = fr_str
    structure.prev['AUTOROUTE_B'] = to_str

    return structure

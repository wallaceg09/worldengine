__author__ = 'Federico Tomassetti'

from noise import snoise2
from world import *
import time

import sys
if sys.version_info > (2,):
    xrange = range


def center_land(world):
    """Translate the map horizontally and vertically to put as much ocean as possible at the borders.
       It operates on elevation and plates map"""
    miny = None
    ymin = None
    minx = None
    xmin = None

    for y in xrange(world.height):
        sumy = 0
        for x in xrange(world.width):
            sumy += world.elevation['data'][y][x]
        if miny == None or sumy < miny:
            miny = sumy
            ymin = y
    if world.verbose:
        print("geo.center_land: height complete");

    for x in xrange(world.width):
        sumx = 0
        for y in xrange(world.height):
            sumx += world.elevation['data'][y][x]
        if minx == None or sumx < minx:
            minx = sumx
            xmin = x
    if world.verbose:
        print("geo.center_land: width complete");

    new_elevation_data = []
    new_plates         = []
    for y in xrange(world.height):
        new_elevation_data.append([])
        new_plates.append([])
        srcy = (ymin + y) % world.height
        for x in xrange(world.width):
            srcx = (xmin + x) % world.width
            new_elevation_data[y].append( world.elevation['data'][srcy][srcx] )
            new_plates[y].append( world.plates[srcy][srcx] )
    world.elevation['data'] = new_elevation_data
    world.plates = new_plates
    if world.verbose:
        print("geo.center_land: width complete");


def center_elevation_map(elevation, width, height):
    """Translate the map horizontally and vertically to put as much ocean as possible at the borders."""
    # FIXME this is bad because plates are not translated
    miny = None
    ymin = None
    minx = None
    xmin = None

    for y in xrange(height):
        sumy = 0
        for x in xrange(width):
            sumy += elevation[y * width + x]
        if miny == None or sumy < miny:
            miny = sumy
            ymin = y

    for x in xrange(width):
        sumx = 0
        for y in xrange(height):
            sumx += elevation[y * width + x]
        if minx == None or sumx < minx:
            minx = sumx
            xmin = x

    new_elevation = [0] * (width * height)
    for y in xrange(height):
        srcy = (ymin + y) % height
        for x in xrange(width):
            srcx = (xmin + x) % width
            new_elevation[y * width + x] = elevation[srcy * width + srcx]
    elevation = new_elevation

    return elevation


def get_interleave_value(original_map, x, y):
    """x and y can be float value"""
    weight_next_x, base_x = math.modf(x)
    weight_preceding_x = 1.0 - weight_next_x
    weight_next_y, base_y = math.modf(y)
    weight_preceding_y = 1.0 - weight_next_y

    base_x = int(base_x)
    base_y = int(base_y)

    sum = 0.0

    # In case the point is right on the border, the weight
    # of the next point will be zero and we will not access
    # it
    combined_weight = weight_preceding_x * weight_preceding_y
    if combined_weight > 0.0:
        sum += combined_weight * original_map[base_y][base_x]

    combined_weight = weight_preceding_x * weight_next_y
    if combined_weight > 0.0:
        sum += combined_weight * original_map[base_y + 1][base_x]

    combined_weight = weight_next_x * weight_preceding_y
    if combined_weight > 0.0:
        sum += combined_weight * original_map[base_y][base_x + 1]

    combined_weight = weight_next_x * weight_next_y
    if combined_weight > 0.0:
        sum += combined_weight * original_map[base_y + 1][base_x + 1]

    return sum


def scale(original_map, target_width, target_height):
    original_width = len(original_map[0])
    original_height = len(original_map)

    y_factor = float(original_height - 1) / (target_height - 1)
    x_factor = float(original_width - 1) / (target_width - 1)

    scaled_map = [[0 for x in xrange(target_width)] for y in xrange(target_height)]
    for scaled_y in xrange(target_height):
        original_y = y_factor * scaled_y
        for scaled_x in xrange(target_width):
            original_x = x_factor * scaled_x
            scaled_map[scaled_y][scaled_x] = get_interleave_value(original_map, original_x, original_y)

    return scaled_map


def get_interleave_value_in_array(original_map, width, height, x, y):
    """x and y can be float value"""
    weight_next_x, base_x = math.modf(x)
    weight_preceding_x = 1.0 - weight_next_x
    weight_next_y, base_y = math.modf(y)
    weight_preceding_y = 1.0 - weight_next_y

    base_x = int(base_x)
    base_y = int(base_y)

    sum = 0.0

    # In case the point is right on the border, the weight
    # of the next point will be zero and we will not access
    # it
    combined_weight = weight_preceding_x * weight_preceding_y
    if combined_weight > 0.0:
        sum += combined_weight * original_map[base_y * width + base_x]

    combined_weight = weight_preceding_x * weight_next_y
    if combined_weight > 0.0:
        sum += combined_weight * original_map[(base_y + 1) * width + base_x]

    combined_weight = weight_next_x * weight_preceding_y
    if combined_weight > 0.0:
        sum += combined_weight * original_map[(base_y) * width + base_x + 1]

    combined_weight = weight_next_x * weight_next_y
    if combined_weight > 0.0:
        sum += combined_weight * original_map[(base_y + 1) * width + base_x + 1]

    return sum


def scale_map_in_array(original_map, original_width, original_height, target_width, target_height):
    y_factor = float(original_height - 1) / (target_height - 1)
    x_factor = float(original_width - 1) / (target_width - 1)

    scaled_map = [0 for el in xrange(target_width * target_height)]
    for scaled_y in xrange(target_height):
        original_y = y_factor * scaled_y
        for scaled_x in xrange(target_width):
            original_x = x_factor * scaled_x
            scaled_map[scaled_y * target_width + scaled_x] = get_interleave_value_in_array(original_map, original_width,
                                                                                           original_height, original_x,
                                                                                           original_y)

    return scaled_map


def watermap(world, n):
    def droplet(world, pos, q, _watermap):
        if q < 0:
            return
        x, y = pos
        pos_elev = world.elevation['data'][y][x] + _watermap[y][x]
        lowers = []
        min_higher = None
        min_lower = None
        pos_min_higher = None
        tot_lowers = 0
        for p in world.tiles_around((x, y)):
            px, py = p
            e = world.elevation['data'][py][px] + _watermap[py][px]
            if e < pos_elev:
                dq = int(pos_elev - e) << 2
                if min_lower == None or e < min_lower:
                    min_lower = e
                    if dq == 0:
                        dq = 1
                lowers.append((dq, p))
                tot_lowers += dq

            else:
                if min_higher == None or e > min_higher:
                    min_higher = e
                    pos_min_higher = p
        if lowers:
            f = q / tot_lowers
            for l in lowers:
                s, p = l
                if world.is_land(p):
                    px, py = p
                    ql = f * s
                    # ql = q
                    going = ql > 0.05
                    _watermap[py][px] += ql
                    if going:
                        droplet(world, p, ql, _watermap)
        else:
            _watermap[y][x] += q

    _watermap_data = [[0 for x in xrange(world.width)] for y in xrange(world.height)]
    for i in xrange(n):
        x, y = world.random_land()
        if True and world.precipitation['data'][y][x] > 0:
            droplet(world, (x, y), world.precipitation['data'][y][x], _watermap_data)
    _watermap = {'data': _watermap_data}
    _watermap['thresholds'] = {}
    _watermap['thresholds']['creek'] = find_threshold_f(_watermap_data, 0.05, ocean=world.ocean)
    _watermap['thresholds']['river'] = find_threshold_f(_watermap_data, 0.02, ocean=world.ocean)
    _watermap['thresholds']['main river'] = find_threshold_f(_watermap_data, 0.007, ocean=world.ocean)
    return _watermap


def erode(world, n):
    if world.verbose:
        start_time = time.time()
    EROSION_FACTOR = 250.0

    def droplet(world, pos, q, v):
        # q = precipitation
        if q < 0:
            raise Exception('why?')
        x, y = pos
        pos_elev = world.elevation['data'][y][x]
        lowers = []
        min_higher = None
        min_lower = None
        tot_lowers = 0
        for p in world.tiles_around((x, y)):
            px, py = p
            e = world.elevation['data'][py][px]
            if e < pos_elev:
                dq = int(pos_elev - e) << 2  # diff elev * 4
                if dq == 0:
                    dq = 1
                lowers.append((dq, p))
                tot_lowers += dq
                if min_lower == None or e < min_lower:
                    min_lower = e
            else:
                if min_higher == None or e > min_higher:
                    min_higher = e
        if lowers:
            f = q / tot_lowers # f = precipitation / weighted # of lower surrounding 'tiles'
            for l in lowers:
                s, p = l      # s = dq = proportional to elevation difference, p = position
                if world.is_land(p):
                    px, py = p
                    ql = f * s  # = amount of precipitation that reaches this 'tile'
                    if ql < 0:
                        raise Exception('Why ql<0? f=%f s=%f' % (f, s))
                    # if ql<0.8*q:
                    # ql = q # rafforzativo
                    #ql = q
                    #going = world.elevation['data'][py][px]==min_higher
                    going = ql > 0.05
                    world.elevation['data'][py][px] -= ql / EROSION_FACTOR
                    if going:
                        # RBB: is recursion really necessary? 
                        #      we just made this tile lower than it was. Most of the time,
                        #      won't the surrounding tiles now be higher? Furthermore, isn't
                        #      this "double dipping"? we are lowering other things, before 
                        #      this step is complete. Shouldn't we do more rounds of erode()
                        #      instead?
                        # RBB: another way to look at it, is if there is enough overflow
                        #      precipitation, then go down to the next level
                        droplet(world, p, ql, 0)      
                        #elif random.random()<s:
                        #    droplet(world,p,ql,0)
        else:
            # If there is not a surrounding 'tile' lower than this one,
            # then increase the elevation, but don't go any higher than
            # the highest surrounding 'tile'
            world.elevation['data'][y][x] += 0.3 / EROSION_FACTOR # only grow at 30% the rate of erosion
            if world.elevation['data'][y][x] > min_higher:
                world.elevation['data'][y][x] = min_higher

    for i in xrange(n):
        x, y = world.random_land()
        if True and world.precipitation['data'][y][x] > 0:
            droplet(world, (x, y), world.precipitation['data'][y][x] * 1, 0)
    if world.verbose:
        elapsed_time = time.time() - start_time
        print("...erosion calculated. Elapsed time " +str(elapsed_time) +" seconds.")


def matrix_extremes(matrix):
    min = None
    max = None
    for row in matrix:
        for el in row:
            val = el
            if min == None or val < min:
                min = val
            if max == None or val > max:
                max = val
    return (min, max)


def rescale_value(original, prev_min, prev_max, min, max):
    f = float(original - prev_min) / (prev_max - prev_min)
    return min + ((max - min) * f)


def sea_depth(world, sea_level):
    sea_depth = [[sea_level - world.elevation['data'][y][x] for x in xrange(world.width)] for y in xrange(world.height)]
    for y in xrange(world.height):
        for x in xrange(world.width):
            if world.tiles_around((x, y), radius=1, predicate=world.is_land):
                sea_depth[y][x] = 0
            elif world.tiles_around((x, y), radius=2, predicate=world.is_land):
                sea_depth[y][x] *= 0.3
            elif world.tiles_around((x, y), radius=3, predicate=world.is_land):
                sea_depth[y][x] *= 0.5
            elif world.tiles_around((x, y), radius=4, predicate=world.is_land):
                sea_depth[y][x] *= 0.7
            elif world.tiles_around((x, y), radius=5, predicate=world.is_land):
                sea_depth[y][x] *= 0.9
    antialias(sea_depth, 10)
    min_depth, max_depth = matrix_extremes(sea_depth)
    sea_depth = [[rescale_value(sea_depth[y][x], min_depth, max_depth, 0.0, 1.0) for x in xrange(world.width)] for y in
                 xrange(world.height)]
    return sea_depth


def antialias(elevation, steps):
    width = len(elevation[0])
    height = len(elevation)

    def antialias():
        for y in range(0, height):
            for x in range(0, width):
                antialias_point(x, y)

    def antialias_point(x, y):
        n = 2
        tot = elevation[y][x] * 2
        for dy in range(-1, +2):
            py = y + dy
            if py > 0 and py < height:
                for dx in range(-1, +2):
                    px = x + dx
                    if px > 0 and px < width:
                        n += 1
                        tot += elevation[py][px]
        return tot / n

    for i in range(0, steps):
        antialias()


def find_threshold(elevation, land_perc, ocean=None):    
    width = len(elevation[0])
    height = len(elevation)

    def count(e):
        tot = 0
        for y in range(0, height):
            for x in range(0, width):
                if elevation[y][x] > e and (ocean == None or not ocean[y][x]):
                    tot += 1
        return tot

    def search(a, b, desired):
        if (not type(a) == int) or (not type(b) == int):
            raise "A and B should be int"
        if a == b:
            return a
        if (b - a) == 1:
            ca = count(a)
            cb = count(b)
            dista = abs(desired - ca)
            distb = abs(desired - cb)
            if dista < distb:
                return a
            else:
                return b
        m = int((a + b) / 2)
        cm = count(m)
        if desired < cm:
            return search(m, b, desired)
        else:
            return search(a, m, desired)

    all_land = width * height
    if ocean:
        for y in range(0, height):
            for x in range(0, width):
                if ocean[y][x]:
                    all_land -= 1
    desired_land = all_land * land_perc
    return search(0, 255, desired_land)


def find_threshold_f(elevation, land_perc, ocean=None):
    width = len(elevation[0])
    height = len(elevation)
    if ocean:
        if (width != len(ocean[0])) or (height != len(ocean)):
            raise Exception(
                "Dimension of elevation and ocean do not match. Elevation is %d x %d, while ocean is %d x%d" % (
                    width, height, len(ocean[0]), len(ocean)))

    def count(e):
        tot = 0
        for y in range(0, height):
            for x in range(0, width):
                if elevation[y][x] > e and (ocean == None or not ocean[y][x]):
                    tot += 1
        return tot

    def search(a, b, desired):
        if a == b:
            return a
        if abs(b - a) < 0.005:
            ca = count(a)
            cb = count(b)
            dista = abs(desired - ca)
            distb = abs(desired - cb)
            if dista < distb:
                return a
            else:
                return b
        m = (a + b) / 2.0
        cm = count(m)
        if desired < cm:
            return search(m, b, desired)
        else:
            return search(a, m, desired)

    all_land = width * height
    if ocean:
        for y in range(0, height):
            for x in range(0, width):
                if ocean[y][x]:
                    all_land -= 1
    desired_land = all_land * land_perc
    return search(-1000.0, 1000.0, desired_land)


def around(x, y, width, height):
    ps = []
    for dx in range(-1, 2):
        nx = x + dx
        if nx >= 0 and nx < width:
            for dy in range(-1, 2):
                ny = y + dy
                if ny >= 0 and ny < height and (dx != 0 or dy != 0):
                    ps.append((nx, ny))
    return ps


def fill_ocean(elevation, sea_level):
    width = len(elevation[0])
    height = len(elevation)

    ocean = [[False for x in xrange(width)] for y in xrange(height)]
    to_expand = []
    for x in range(0, width):
        if elevation[0][x] <= sea_level:
            to_expand.append((x, 0))
        if elevation[height -1][x] <= sea_level:
            to_expand.append((x, height - 1))
    for y in range(0, height):
        if elevation[y][0] <= sea_level:
            to_expand.append((0, y))
        if elevation[y][width - 1] <= sea_level:
            to_expand.append((width - 1, y))
    for t in to_expand:
        tx, ty = t
        if not ocean[ty][tx]:
            ocean[ty][tx] = True
            for px, py in around(tx, ty, width, height):
                if not ocean[py][px] and elevation[py][px] <= sea_level:
                    to_expand.append((px, py))

    return ocean


def temperature(seed, elevation, mountain_level):
    width = len(elevation[0])
    height = len(elevation)

    random.seed(seed * 7)
    base = random.randint(0, 4096)
    temp = [[0 for x in xrange(width)] for y in xrange(height)]

    from noise import snoise2

    border = width / 4
    octaves = 6
    freq = 16.0 * octaves

    for y in range(0, height):
        yscaled = float(y) / height
        latitude_factor = 1.0 - (abs(yscaled - 0.5) * 2)
        for x in range(0, width):
            n = snoise2(x / freq, y / freq, octaves, base=base)

            #Added to allow noise pattern to wrap around right and left.
            if x <= border:
                n = (snoise2(x / freq, y / freq, octaves, base=base) * x / border) + (snoise2((x+width) / freq, y / freq, octaves, base=base) * (border-x)/border)

            t = (latitude_factor * 3 + n * 2) / 5.0
            if elevation[y][x] > mountain_level:
                if elevation[y][x] > (mountain_level + 29):
                    altitude_factor = 0.033
                else:
                    altitude_factor = 1.00 - (float(elevation[y][x] - mountain_level) / 30)
                t *= altitude_factor
            temp[y][x] = t

    return temp


def precipitation(seed, width, height):
    """"Precipitation is a value in [-1,1]"""
    border = width / 4 
    random.seed(seed * 13)
    base = random.randint(0, 4096)
    precipitations = [[0 for x in xrange(width)] for y in xrange(height)]

    from noise import snoise2

    octaves = 6
    freq = 64.0 * octaves

    for y in range(0, height):
        yscaled = float(y) / height
        latitude_factor = 1.0 - (abs(yscaled - 0.5) * 2)
        for x in range(0, width):
            n = snoise2(x / freq, y / freq, octaves, base=base)

            # Added to allow noise pattern to wrap around right and left.
            if x < border: 
                n = (snoise2(x / freq, y / freq, octaves, base=base) * x / border) + (snoise2((x+width) / freq, y / freq, octaves, base=base) * (border-x)/border)

            prec = (latitude_factor + n * 4) / 5.0
            precipitations[y][x] = prec

    return precipitations


def irrigation(world):
    width = world.width
    height = world.height

    values = [[0 for x in xrange(width)] for y in xrange(height)]
    radius = 10

    for y in xrange(height):
        for x in xrange(width):
            if world.is_land((x, y)):
                for dy in range(-radius, radius + 1):
                    if (y + dy) >= 0 and (y + dy) < world.height:
                        for dx in range(-radius, radius + 1):
                            if (x + dx) >= 0 and (x + dx) < world.width:
                                dist = math.sqrt(dx ** 2 + dy ** 2)
                                values[y + dy][x + dx] += world.watermap['data'][y][x] / (math.log(dist + 1) + 1)

    return values


def permeability(seed, width, height):
    random.seed(seed * 37)
    base = random.randint(0, 4096)
    temp = [[0 for x in xrange(width)] for y in xrange(height)]

    from noise import snoise2

    octaves = 6
    freq = 64.0 * octaves

    for y in range(0, height):
        yscaled = float(y) / height
        for x in range(0, width):
            n = snoise2(x / freq, y / freq, octaves, base=base)
            t = n
            temp[y][x] = t

    return temp


def classify(data, thresholds, x, y):
    value = data[y][x]
    for name, level in thresholds:
        if (level == None) or (value < level):
            return name


def elevnoise_on_world(world, seed):
    octaves = 6
    freq = 16.0 * octaves
    for y in range(0, world.height):
        for x in range(0, world.width):
            n = snoise2(x / freq * 2, y / freq * 2, octaves, base=seed)
            world.elevation['data'][y][x] += n


def elevnoise(elevation, seed):
    # FIXME use elevnoise_on_world instead
    width = len(elevation[0])
    height = len(elevation)

    octaves = 6
    freq = 16.0 * octaves
    for y in range(0, height):
        for x in range(0, width):
            n = int(snoise2(x / freq * 2, y / freq * 2, octaves, base=seed))
            elevation[y][x] += n


def place_oceans_at_map_borders_on_world(world):
    """
    Lower the elevation near the border of the map
    """

    OCEAN_BORDER = int(min(30, max(world.width / 5, world.height / 5)))

    def place_ocean(x, y, i):
        world.elevation['data'][y][x] = (world.elevation['data'][y][x] * i) / OCEAN_BORDER

    for x in xrange(world.width):
        for i in range(0, OCEAN_BORDER):
            place_ocean(x, i, i)
            place_ocean(x, world.height - i - 1, i)

    for y in xrange(world.height):
        for i in range(0, OCEAN_BORDER):
            place_ocean(i, y, i)
            place_ocean(world.width - i - 1, y, i)


def place_oceans_at_map_borders(elevation):
    """
    Lower the elevation near the border of the map
    :param elevation:
    :return:
    """
    # FIXME remove and use place_ocenas_at_map_borders_on_world instead
    width = len(elevation[0])
    height = len(elevation)

    OCEAN_BORDER = int(min(30, max(width / 5, height / 5)))

    def place_ocean(x, y, i):
        elevation[y][x] = (elevation[y][x] * i) / OCEAN_BORDER
    
    for x in xrange(width):
        for i in range(0, OCEAN_BORDER):
            place_ocean(x, i, i)
            place_ocean(x, height - i - 1, i)


def humidity(world):
    humidity = {}
    humidity['data'] = [[0 for x in xrange(world.width)] for y in xrange(world.height)]

    for y in xrange(world.height):
        for x in xrange(world.width):
            humidity['data'][y][x] = world.precipitation['data'][y][x] + world.irrigation[y][x]

    #These were originally evenly spaced at 12.5% each but changing them to a bell curve produced
    #better results
    humidity['quantiles'] = {}
    humidity['quantiles']['12'] = find_threshold_f(humidity['data'], 0.02, world.ocean)
    humidity['quantiles']['25'] = find_threshold_f(humidity['data'], 0.09, world.ocean)
    humidity['quantiles']['37'] = find_threshold_f(humidity['data'], 0.26, world.ocean)
    humidity['quantiles']['50'] = find_threshold_f(humidity['data'], 0.50, world.ocean)
    humidity['quantiles']['62'] = find_threshold_f(humidity['data'], 0.74, world.ocean)
    humidity['quantiles']['75'] = find_threshold_f(humidity['data'], 0.91, world.ocean)
    humidity['quantiles']['87'] = find_threshold_f(humidity['data'], 0.98, world.ocean)
    return humidity


def initialize_ocean_and_thresholds(world, ocean_level=1.0):
    """
    Calculate the ocean, the sea depth and the elevation thresholds
    :param world: a world having elevation but not thresholds
    :param ocean_level: the elevation representing the ocean level
    :return: nothing, the world will be changed
    """
    e = world.elevation['data']
    ocean = fill_ocean(e, ocean_level)
    hl = find_threshold_f(e, 0.10)
    ml = find_threshold_f(e, 0.03)
    e_th = [('sea', ocean_level), ('plain', hl), ('hill', ml), ('mountain', None)]
    world.set_ocean(ocean)
    world.set_elevation(e, e_th)
    world.sea_depth = sea_depth(world, ocean_level)


def world_gen_precipitation(w):
    start_time = time.time()
    p = precipitation(w.seed, w.width, w.height)
    p_th = [
        ('low', find_threshold_f(p, 0.75, w.ocean)),
        ('med', find_threshold_f(p, 0.3, w.ocean)),
        ('hig', None)
    ]
    w.set_precipitation(p, p_th)
    elapsed_time = time.time() - start_time
    if w.verbose:
        print("...precipitations calculated. Elapsed time " +str(elapsed_time) +" seconds.")
    return [p, p_th]


def world_gen_from_elevation(w, step):
    if isinstance(step, str):
        step = Step.get_by_name(step)
    e = w.elevation['data']
    ocean = w.ocean
    ml = w.start_mountain_th()

    if not step.include_precipitations:
        return w

    # Precipitation with thresholds
    p, p_th = world_gen_precipitation(w)

    if not step.include_erosion:
        return w

    erosion_n = int((w.width*w.height*3000000)/(512*512)) # if the plate size is ever changed, then these 512 values should probably change too
    erode(w, erosion_n)

    # FIXME: create setters
    if w.verbose:
        start_time = time.time()
    w.watermap = watermap(w, 20000)
    w.irrigation = irrigation(w)
    w.humidity = humidity(w)
    hu_th = [
        ('low', find_threshold_f(w.humidity['data'], 0.75, ocean)),
        ('med', find_threshold_f(w.humidity['data'], 0.3, ocean)),
        ('hig', None)
    ]
    if w.verbose:
        elapsed_time = time.time() - start_time
        print("...humidity calculated. Elapsed time " +str(elapsed_time) +" seconds.")

    # Temperature with thresholds
    if w.verbose:
        start_time = time.time()
    t = temperature(w.seed, e, ml)
    t_th = [
	('polar', find_threshold_f(t, 0.90, ocean)),
        ('alpine', find_threshold_f(t, 0.76, ocean)),
        ('boreal', find_threshold_f(t, 0.59, ocean)),
        ('cool', find_threshold_f(t, 0.38, ocean)),
        ('warm', find_threshold_f(t, 0.26, ocean)),
        ('subtropical', find_threshold_f(t, 0.14, ocean)),
        ('tropical', None)
    ]
    w.set_temperature(t, t_th)
    if w.verbose:
        elapsed_time = time.time() - start_time
        print("...set temperature. Elapsed time " +str(elapsed_time) +" seconds.")

    # Permeability with thresholds
    if w.verbose:
        start_time = time.time()
    perm = permeability(w.seed, w.width, w.height)
    perm_th = [
        ('low', find_threshold_f(perm, 0.75, ocean)),
        ('med', find_threshold_f(perm, 0.25, ocean)),
        ('hig', None)
    ]
    w.set_permeability(perm, perm_th)

    if w.verbose:
        elapsed_time = time.time() - start_time
        print("...permeability level calculated. Elapsed time " +str(elapsed_time) +" seconds.")

    if w.verbose:
        start_time = time.time()
    cm = {}
    biome_cm = {}
    biome = [[None for x in xrange(w.width)] for y in xrange(w.height)]
    for y in xrange(w.height):
        for x in xrange(w.width):
            if ocean[y][x]:
                biome[y][x] = 'ocean'
            else:
                if w.is_temperature_polar((x, y)):
                    if w.is_humidity_superarid((x, y)):
                        biome[y][x] = 'polar desert'
                    else:
                        biome[y][x] = 'ice'
                elif w.is_temperature_alpine((x, y)):
                    if w.is_humidity_superarid((x, y)):
                        biome[y][x] = 'subpolar dry tundra'
                    elif w.is_humidity_perarid((x, y)):
                        biome[y][x] = 'subpolar moist tundra'
                    elif w.is_humidity_arid((x, y)):
                        biome[y][x] = 'subpolar wet tundra'
                    else:
                        biome[y][x] = 'subpolar rain tundra'
                elif w.is_temperature_boreal((x, y)):
                    if w.is_humidity_superarid((x, y)):
                        biome[y][x] = 'boreal desert'
                    elif w.is_humidity_perarid((x, y)):
                        biome[y][x] = 'boreal dry scrub'
                    elif w.is_humidity_arid((x, y)):
                        biome[y][x] = 'boreal moist forest'
                    elif w.is_humidity_semiarid((x, y)):
                        biome[y][x] = 'boreal wet forest'
                    else:
                        biome[y][x] = 'boreal rain forest'
                elif w.is_temperature_cool((x, y)):
                    if w.is_humidity_superarid((x, y)):
                        biome[y][x] = 'cool temperate desert'
                    elif w.is_humidity_perarid((x, y)):
                        biome[y][x] = 'cool temperate desert scrub'
                    elif w.is_humidity_arid((x, y)):
                        biome[y][x] = 'cool temperate steppe'
                    elif w.is_humidity_semiarid((x, y)):
                        biome[y][x] = 'cool temperate moist forest'
                    elif w.is_humidity_subhumid((x, y)):
                        biome[y][x] = 'cool temperate wet forest'
                    else:
                        biome[y][x] = 'cool temperate rain forest'
                elif w.is_temperature_warm((x, y)):
                    if w.is_humidity_superarid((x, y)):
                        biome[y][x] = 'warm temperate desert'
                    elif w.is_humidity_perarid((x, y)):
                        biome[y][x] = 'warm temperate desert scrub'
                    elif w.is_humidity_arid((x, y)):
                        biome[y][x] = 'warm temperate thorn scrub'
                    elif w.is_humidity_semiarid((x, y)):
                        biome[y][x] = 'warm temperate dry forest'
                    elif w.is_humidity_subhumid((x, y)):
                        biome[y][x] = 'warm temperate moist forest'
                    elif w.is_humidity_humid((x, y)):
                        biome[y][x] = 'warm temperate wet forest'
                    else:
                        biome[y][x] = 'warm temperate rain forest'
                elif w.is_temperature_subtropical((x, y)):
                    if w.is_humidity_superarid((x, y)):
                        biome[y][x] = 'subtropical desert'
                    elif w.is_humidity_perarid((x, y)):
                        biome[y][x] = 'subtropical desert scrub'
                    elif w.is_humidity_arid((x, y)):
                        biome[y][x] = 'subtropical thorn woodland'
                    elif w.is_humidity_semiarid((x, y)):
                        biome[y][x] = 'subtropical dry forest'
                    elif w.is_humidity_subhumid((x, y)):
                        biome[y][x] = 'subtropical moist forest'
                    elif w.is_humidity_humid((x, y)):
                        biome[y][x] = 'subtropical wet forest'
                    else:
                        biome[y][x] = 'subtropical rain forest'
                elif w.is_temperature_tropical((x, y)):
                    if w.is_humidity_superarid((x, y)):
                        biome[y][x] = 'tropical desert'
                    elif w.is_humidity_perarid((x, y)):
                        biome[y][x] = 'tropical desert scrub'
                    elif w.is_humidity_arid((x, y)):
                        biome[y][x] = 'tropical thorn woodland'
                    elif w.is_humidity_semiarid((x, y)):
                        biome[y][x] = 'tropical very dry forest'
                    elif w.is_humidity_subhumid((x, y)):
                        biome[y][x] = 'tropical dry forest'
                    elif w.is_humidity_humid((x, y)):
                        biome[y][x] = 'tropical moist forest'
                    elif w.is_humidity_perhumid((x, y)):
                        biome[y][x] = 'tropical wet forest'
                    else:
                        biome[y][x] = 'tropical rain forest'
                else:
                    biome[y][x] = 'bare rock'
            if not biome[y][x] in biome_cm:
                biome_cm[biome[y][x]] = 0
            biome_cm[biome[y][x]] += 1

    for cl in cm.keys():
        count = cm[cl]
        if w.verbose:
            print("%s = %i" % (str(cl), count))

    if w.verbose:
        elapsed_time = time.time() - start_time
        print("... biome calculated. Elapsed time " +str(elapsed_time) +" seconds.")
        print('')  # empty line
        print('Biome obtained:')

    for cl in biome_cm.keys():
        count = biome_cm[cl]
        if w.verbose:
            print(" %30s = %7i" % (str(cl), count))

    w.set_biome(biome)
    return w


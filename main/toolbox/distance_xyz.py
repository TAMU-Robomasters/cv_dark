import numpy as np
from subsystems.video_stream import video_stream
from toolbox.globals import runtime
from time import perf_counter

def get_xyz_at_color_coords(point, depth=None):
    # point is [x, y], return tuple (x, y, z)
    try:
        point_3d = video_stream.get_xyz_at_color_point(point, depth=depth)
    except AttributeError:
        print("Your camera is not depth capable.")

    return point_3d

def get_dist_to_bbox(bbox):
    depth_sample_coords = get_depth_sample_coords(bbox, samples_per_dimension=3, width_coverage=0.5, height_coverage=0.5)
    try:
        depth_sample = np.array([video_stream.get_depth_at_point(point) for point in depth_sample_coords])
    except AttributeError:
        print("Your camera is not depth capable.")
        
    if depth_sample.shape[0] == 0:
        return None
    depth_sample = depth_sample[depth_sample != None]
    if depth_sample.shape[0] == 0:
        return None
    depth_sample = depth_sample[depth_sample != 0]
    if depth_sample.shape[0] == 0:
        return None
    aim_start = perf_counter()
    depth_sample = reject_depth_outliers(depth_sample)
    aim_end = perf_counter()
    if depth_sample.shape[0] == 0:
        return None
    # print(f"depth_sample: {depth_sample}")
    print(f"Took: {(aim_end - aim_start)*1000} ms")
    # if np.mean(depth_sample) > 5 or np.mean(depth_sample) < 0:
    #     quit()
    return np.mean(depth_sample)

def reject_depth_outliers(depth_sample):
    ''' Use median absolute deviation to reject outliers in depth sample '''
    median = np.median(depth_sample)
    mad = np.median(np.abs(depth_sample - median))
    return depth_sample[np.abs(depth_sample - median) < 3 * mad]

def get_depth_sample_coords(bbox, samples_per_dimension=3, width_coverage=0.25, height_coverage=0.25):
    #NOTE could maybe simplify this with numpy
    bbox_width_coverage = bbox.width.item() * width_coverage
    bbox_height_coverage = bbox.height.item() * height_coverage

    bbxtl = max(bbox.center[0].item() - (bbox_width_coverage // 2), 0)
    bbytl = max(bbox.center[1].item() - (bbox_height_coverage // 2), 0)

    bbxbr = min(bbxtl + bbox_width_coverage, runtime.color_image.shape[1] - 1)
    bbybr = min(bbytl + bbox_height_coverage, runtime.color_image.shape[0] - 1)


    x_range = (bbxbr - bbxtl) // (samples_per_dimension - 1) if samples_per_dimension > 1 else bbxbr - bbxtl
    y_range = (bbybr - bbytl) // (samples_per_dimension - 1) if samples_per_dimension > 1 else bbybr - bbytl

    coords = []
    for i in range(samples_per_dimension):
        for j in range(samples_per_dimension):
            x = int(bbxtl + x_range * i)
            y = int(bbytl + y_range * j)
            coords.append([x, y])
    return np.array(coords)
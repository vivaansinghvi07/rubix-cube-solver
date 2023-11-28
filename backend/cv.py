from operator import is_
import cv2
import numpy as np
from enum import Enum
from statistics import mode
from typing import TypeAlias
from pycubing.enums import Color, Face
from pycubing.cube import Cube, Cube3x3
from math import sqrt, degrees, atan2, tan, radians, dist, sin, cos

# type aliases for better type annotations
Contour: TypeAlias = np.ndarray
Point: TypeAlias = np.ndarray
AngleRadians: TypeAlias = float
AngleDegrees: TypeAlias = float

# constants, tweakable hyperparams
MAX_IMG_AREA = 2_500_000
ANGLE_DIFF_TOLERANCE = 30   # degrees
VERTICAL_STD_DEV_TOLERANCE = 20
HSV_FILTER_COLORS = {  # each value is as follows: (h_ranges, s_range, v_range)
    Color.RED: (((170, 180), (0, 5)), (100, 255), (100, 255)),
    Color.ORANGE: (((5, 20),), (100, 255), (100, 255)),
    Color.BLUE: (((95, 125),), (100, 255), (100, 255)),
    Color.GREEN: (((40, 75),), (50, 255), (50, 255)),
    Color.WHITE: (((0, 180),), (0, 50), (150, 255)),
    Color.YELLOW: (((20, 35),), (100, 255), (100, 255)),
}
VERTICAL_CHECKING_SHAPE_DIVISOR = 18

class FaceLocation(Enum):
    """ Store information regarding where the faces are on the cube, relative to a picture. """
    TOP = 0
    BOTTOM = 1
    LEFT = 2
    RIGHT = 3

class ComputerVisionException(Exception):
    """ Exceptions for computer vision problems throughout the project. """
    def __init__(self, message: str) -> None:
        self.message = message

def cap_img(img: cv2.Mat) -> cv2.Mat:
    """ Caps a given image to a certain size. """
    scale_factor = min(sqrt(MAX_IMG_AREA / (img.shape[0] * img.shape[1])), 1)
    return cv2.resize(img, (0, 0), fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_AREA)

def imread_capped(filename: str) -> cv2.Mat:
    """ Reads a file and returns a cv2 Image, but resizing it to meet a maximum area. """
    img = cv2.imread(filename)
    return cap_img(img)

def to_hsv(img: cv2.Mat):
    """ Wrapper function for quick conversion to HSV from BGR. """
    return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

def from_hsv(img: cv2.Mat):
    """ Wrapper function for quick conversion from HSV to BGR. """
    return cv2.cvtColor(img, cv2.COLOR_HSV2BGR) 

# https://pyimagesearch.com/2016/02/01/opencv-center-of-contour/
def get_center(cnt: Contour) -> Point:
    """ Gets the center of a contour. """
    moments = cv2.moments(cnt)
    center = (int(moments["m10"] / moments["m00"]), int(moments["m01"] / moments["m00"]))
    return center

# https://stackoverflow.com/a/2259502
def get_rotated_point(pivot: Point, p: Point, angle: AngleRadians) -> Point:
    """ Gets a point rotated around a pivot by a given amount of radians. """

    # setup values
    s = sin(angle)
    c = cos(angle)
    adj_y = pivot[1] - p[1]
    adj_x = p[0] - pivot[0]

    # determine new coordinates
    new_x = adj_x * c - adj_y * s
    new_y = adj_x * s + adj_y * c
    
    # return new coordinates modified to fit opencv
    return (int(new_x + pivot[0]), int(pivot[1] - new_y))

# computes the angle between two corners using c1 as the origin
def compute_incline_angle(c1: Point, c2: Point) -> AngleDegrees:
    """ Computes the angle of the ray going from c1 to c2. """
    x_diff, y_diff = c2[0] - c1[0], c1[1] - c2[1]
    return degrees(atan2(y_diff, x_diff)) % 360 

# this function is only used in the following function
def filter_cubie_contours(img: cv2.Mat, contours: list[Contour], approx: list[Contour]) -> list[Contour]:
    """ 
    Filters contours according to the following metrics:
        - Approximation must be 4 points long
        - Contour area and polynomial approximation area have to be similar
    Arranges contours according to the following rule:
        - Clockwise from the starting point
        - The starting point is chosen to be the left-most point
            - If there are two points closer together in terms of x-axis location, the top-most point is selected
    The latter is done to give contours a consistent ordering
    """

    # filter erradic, non-quadrilateral contours
    proper_contours, proper_approx = [], []
    for cnt, appr in zip(contours, approx):

        # make sure the shape approximation is a quadrilateral 
        D = len(appr) * 2
        if not 8==D:  # lol
            continue

        # make sure the approx isnt crazy different area-wise - consider removing this test
        cnt_area = cv2.contourArea(cnt)
        ratio = cnt_area / cv2.contourArea(appr)
        if min(ratio, 1/ratio) < 0.80:   # artitrary ratio thresold chosen by me
            continue

        # make sure the overlapping area isnt too bad
        overlap_reference = np.zeros(img.shape[:2], dtype=np.uint8)
        cv2.drawContours(overlap_reference, [cnt], -1, (255, 255, 255), cv2.FILLED)
        cv2.drawContours(overlap_reference, [appr], -1, (0, 0, 0), cv2.FILLED)
        if (overlap_reference.sum() // 255) > (cnt_area // 5):
            continue

        proper_contours.append(cnt) 
        proper_approx.append(appr)

    # sweep through it again and cut off the ones that are too small
    avg_area = np.average([*map(cv2.contourArea, proper_approx)])
    largest_approx = [*filter(lambda x: cv2.contourArea(x) > avg_area / 4, proper_approx)]

    # this time, give each contour a consistent ordering, making it start from the leftmost if possible else bottommost
    final_approx = []
    for appr in largest_approx:
        x_axis_vals = [*map(lambda x: x[0], appr)]
        min_indices = np.argsort(x_axis_vals)
        if x_axis_vals[min_indices[1]] - x_axis_vals[min_indices[0]] < img.shape[1] / VERTICAL_CHECKING_SHAPE_DIVISOR:
            y_axis_vals = [*map(lambda x: x[1], appr)]
            min_indices = np.argsort(y_axis_vals)
        final_approx.append(np.concatenate((appr[min_indices[0]:], appr[:min_indices[0]]), axis=0))
    return final_approx 

def get_cubie_contours(img: cv2.Mat) -> list[Contour]:
    """
    Given an image, returns a list of contours that are likely to be the "small squares" part of a Rubik's cube.
    """

    # computes some sizes - doesn't get too crazy because sizes are standardized
    reference_size = max(img.shape)
    blur_size = int(sqrt(reference_size) / 2)
    kernel_size = int(sqrt(reference_size) / 10)

    # image processing to get contours
    blur = cv2.GaussianBlur(img, (blur_size + int(blur_size % 2 == 0),) * 2, kernel_size)
    edges = cv2.Canny(blur, 20, 30)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size * 3,) * 2)
    dilated = cv2.dilate(edges, kernel)
    contours = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
    large_contours = [*filter(lambda x: cv2.contourArea(x, True) > (img.shape[0] * img.shape[1]) // 5000, contours)]
    approx = [*map(lambda x: cv2.approxPolyDP(x, 0.03*cv2.arcLength(x, True), True).reshape(-1, 2), large_contours)]
    
    # filter the contours
    return filter_cubie_contours(img, large_contours, approx)

def get_squares_by_angle(squares: list[Contour]) -> dict[tuple[float], list[Contour]]:
    """ Returns a map of angle-pairs to a list of squares. This is done to seperate them into faces. """

    # determine an angle between specific points on the contour 
    angle_to_squares = {}
    for appr in squares:
        appr = appr.reshape(-1, 2)
        c1, c2, c3 = appr[0], appr[1], appr[-1]  # we can specifically index here because of the ordering done in the prev function
        angle_of_incline1 = compute_incline_angle(c1, c2)
        angle_of_incline2 = compute_incline_angle(c3, c1)
        for (k1, k2), v in angle_to_squares.items():
            if abs(angle_of_incline1 - k1) < ANGLE_DIFF_TOLERANCE and abs(angle_of_incline2 - k2) < ANGLE_DIFF_TOLERANCE:

                # add to list of contours 
                v.append(appr)
                current_total = len(v) - 1

                # replace the key with the new average
                del angle_to_squares[(k1, k2)]
                angle_to_squares[((k1 * current_total + angle_of_incline1) / (current_total + 1), 
                                  (k2 * current_total + angle_of_incline2) / (current_total + 1))] = v
                break
        else:
            angle_to_squares[(angle_of_incline1, angle_of_incline2)] = [appr]

    # raise a red flag if only one side was detected -- assuming the user did everything correctly, this incicates the unique case
    if len(angle_to_squares) == 1:

        # we need to split the cube into two parts, across a diagonal line
        pivot_point = (400, 400)
        average_angle = radians(np.average([compute_incline_angle(c1, c2) for (c1, c2, _, _) in squares]))
        rotated_centers = [get_rotated_point(pivot_point, get_center(appr), -average_angle) for appr in squares]
        if ((max_y := max(map(lambda x: x[1], rotated_centers))) - (min_y := min(map(lambda x: x[1], rotated_centers))) > 
            (max_x := max(map(lambda x: x[0], rotated_centers))) - (min_x := min(map(lambda x: x[0], rotated_centers)))):
            midline = (max_y + min_y) / 2
            comp_function = lambda x: x[1]
        else:
            midline = (max_x + min_x) / 2
            comp_function = lambda x: x[0]
        group_lower = [c for c, rc in zip(squares, rotated_centers) if comp_function(rc) < midline]
        group_upper = [c for c, rc in zip(squares, rotated_centers) if comp_function(rc) > midline]
        angle_to_squares = {  # the angle choice here doesn't really matter
            (0, 0): group_lower,
            (69, 69): group_upper
        }

    return angle_to_squares

# helper function for the next one
def fill_line_through_contour(intersection_map: cv2.Mat, center: Point, mid_corner: Point, ang_ref_corner: Point, thick_ref_corner: Point) -> None:
    """ Draws a thick line through a contour on a given image using given reference points. """

    # determine angles for use later
    line_angle = radians(compute_incline_angle(mid_corner, ang_ref_corner))
    thick_ref_angle = radians(compute_incline_angle(mid_corner, thick_ref_corner))

    # compute locations of bounding points by extrapolating using the angle   -- TODO: consider changing the angle to be the average angle at that spot, eliminate noise
    point1 = (0, tan(line_angle)*center[0] + center[1])
    point2 = (intersection_map.shape[1], center[1] - tan(line_angle)*(intersection_map.shape[1]-center[0]))

    # adjust this to use the x-direction instead
    if abs(point1[1]) > 10000:
        point1 = (center[1] / tan(line_angle) + center[0], 0)
        point2 = (- (intersection_map.shape[0] - center[1]) / tan(line_angle) + center[0], intersection_map.shape[0])

    # determine the thickness using the angle of difference in the parallelogram, and plot to the map
    thickness = int(dist(mid_corner, thick_ref_corner) * abs(sin(thick_ref_angle - line_angle)))
    cv2.line(intersection_map, [*map(int, point1)], [*map(int, point2)], 100, thickness // 2)  # thickness is adjusted to avoid potential overlap of squares

# after this, squares should be fully read
def fill_empty_squares(img: cv2.Mat, face_contours: dict[tuple[float], list[Contour]]):
    """
    Interpolates where squares are, if the squares are not read yet. 
    View the cv_testing.ipynb file to see what this looks like for better understanding.
    """

    new_face_contours = {}
    for key, squares in face_contours.items():

        # fill intersection maps for each deteced piece, showing all possible pieces
        c1_c2_intersection_map = np.zeros(img.shape[:2], dtype=np.uint8)
        c2_c3_intersection_map = np.zeros(img.shape[:2], dtype=np.uint8)
        for cnt in squares:
            center = get_center(cnt)
            c1, c2, c3 = cnt[:-1]
            fill_line_through_contour(c1_c2_intersection_map, center, c2, c3, c1)
            fill_line_through_contour(c2_c3_intersection_map, center, c2, c1, c3)
        
        # determine a final map and new contours that are completely accurate to the cube
        final_map = c1_c2_intersection_map + c2_c3_intersection_map
        thresh = cv2.threshold(final_map, 199, 255, cv2.THRESH_BINARY)[1]
        new_squares = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
        new_approx = [*map(lambda x: cv2.approxPolyDP(x, 0.03*cv2.arcLength(x, True), True).reshape(-1, 2), new_squares)]  # reshape makes it from (-1, 1, 2) to (-1, 2)
        new_face_contours[key] = [*filter(lambda x: len(x) == 4 and cv2.contourArea(x) > np.prod(img.shape[:2]) // 2000, new_approx)]

    return new_face_contours

# this is probably where a lot of things go wrong, ive tried to add a lot of checks tho 
def get_squares_by_face(face_contours: dict[tuple[float], list[Contour]]) -> dict[FaceLocation, list[Contour]]:
    """
    Identifies which locations in the picture contain which faces.
    The input is a dictionary of keys (which are tuples of float) to contours, where each key represents a face.
    Method:
        - Check how many faces are visible:
            - If 2, do the following:
                - Determine the average angle of the line going to the top right in every square of each face.
                    - This should be the same angle on both faces, if the user did everything right.
                - Tilt the contours by negative that angle. 
                    - The faces are either horizontally or vertically aligned now.
                - Find the center of mass of each face.
                - If the center of mass of a face is to the left of every square on the other face, it is horizontal alignment.
                    - Vice versa applies for the center of mass being to the top or bottom.
                - Then, assign each face a location depending on orientation.
            - If 3, do the following:
                - Determine which out of the three faces are on the left and right respectively.
                    - They should always both be present.
                    - To do this, simply find which one contains vertical angles on the left and right sides.
                    - Determine which one is the left and right by simply seeing which center is more left.
                - The remaining face is either bottom or top. Determine this by checking the orientation of the squares in the left and right face.
                    - It is too unreliable to check if it is simply higher or lower than the other pieces.
    """
    
    # remove blank keys
    for key in list(face_contours.keys()):
        if not face_contours[key]:
            del face_contours[key]

    # check if the number if face contours is 0, if so, we only have two options
    if len(face_contours) < 2:
        raise ComputerVisionException("Too few faces detected.")
    elif len(face_contours) > 3:
        raise ComputerVisionException("Too many faces detected.")
    elif len(face_contours) == 2:

        # determine average angle of going top 
        top_right_angle = 0
        for key, squares in face_contours.items():
            left_most_indices = [np.argsort([*map(lambda x: x[0], cnt)])[0] for cnt in squares]
            angle_points = [[cnt[i], cnt[(i-1) % 4]] for cnt, i in zip(squares, left_most_indices)]
            top_right_angle += np.average([compute_incline_angle(left, top) for left, top in angle_points])
        top_right_angle = np.radians(top_right_angle / 2)

        # determine the left_most contour 
        pivot_point = (400, 400)  # arbitrary - relative locations remain the same
        rotated_face_contours = {
            k: [[get_rotated_point(pivot_point, p, -top_right_angle) for p in cnt] for cnt in squares]
            for k, squares in face_contours.items()
        }

        # determine if the contours are significantly above or below each other
        key_1, key_2 = face_contours.keys()
        center_of_mass_1, center_of_mass_2 = map(lambda k: np.average([get_center(np.array(cnt)) for cnt in rotated_face_contours[k]], axis=0), [key_1, key_2])
        if len({center_of_mass_1[0] > get_center(np.array(cnt))[0] for cnt in rotated_face_contours[key_2]}) == 1:  # the key1 is more to the left or right than key

            # here, we make sure key_1 is always the leftmost key for returning
            if center_of_mass_2[0] < center_of_mass_1[0]:
                key_1, key_2 = key_2, key_1

            # some guardrails to make sure we don't get results that make no sense
            bottom_center_of_mass, right_center_of_mass = map(lambda k: np.average([get_center(np.array(cnt)) for cnt in face_contours[k]], axis=0), [key_1, key_2])
            if not (bottom_center_of_mass[1] > right_center_of_mass[1] and right_center_of_mass[0] > bottom_center_of_mass[0]):
                raise ComputerVisionException("Invalid faces detected.")
            return {
                FaceLocation.BOTTOM: face_contours[key_1],
                FaceLocation.RIGHT: face_contours[key_2]
            }
        
        # now we know it's the other scenario -- once again, we make sure key_1 is the top_most key
        else:

            if center_of_mass_2[1] < center_of_mass_1[1]:
                key_1, key_2 = key_2, key_1
            bottom_center_of_mass, left_center_of_mass = map(lambda k: np.average([get_center(np.array(cnt)) for cnt in face_contours[k]], axis=0), [key_2, key_1])
            if not (bottom_center_of_mass[1] > left_center_of_mass[1] and left_center_of_mass[0] < bottom_center_of_mass[0]):
                raise ComputerVisionException("Invalid faces detected.")
            return {
                FaceLocation.LEFT: face_contours[key_1],
                FaceLocation.BOTTOM: face_contours[key_2]
            }
        
    elif len(face_contours) == 3:
        left_right_keys, center_of_masses, left_right_side_points = [], {}, {}
        for key, squares in face_contours.items():

            # storing left-side points and right-side points for each contour
            sorted_left_to_right = [sorted(cnt, key=lambda p: p[0]) for cnt in squares]
            left_side_points = [sorted(points[:2], key=lambda p: p[1]) for points in sorted_left_to_right]    # sorting these two top to bottom for consistency
            right_side_points = [sorted(points[2:], key=lambda p: p[1]) for points in sorted_left_to_right]
            left_right_side_points[key] = (left_side_points, right_side_points)

            # get the average angle figured out, if its pretty much vertical its on the left/right face
            angles = [compute_incline_angle(*points) % 180 for points in left_side_points + right_side_points]
            if 90 - ANGLE_DIFF_TOLERANCE < np.average(angles) < 90 + ANGLE_DIFF_TOLERANCE and np.std(angles) < VERTICAL_STD_DEV_TOLERANCE:  # this means we have detected a mostly vertical angle group
                left_right_keys.append(key)

            # determine the center of mass for the things
            center_of_mass = np.average([get_center(cnt) for cnt in squares], axis=0)
            center_of_masses[key] = center_of_mass

        # determine the left key from looking at where the center is 
        try:
            left_key, right_key = sorted(left_right_keys, key=lambda k: center_of_masses[k][0])
        except ValueError:  # cannot unpack the values, so there were not enough proper faces detected
            raise ComputerVisionException("Something went wrong.")

        # meaning: left_right means the left face, right line. we are checking if the left face right line is higher/lower than the left face left line
        left_left_avg, left_right_avg, right_left_avg, right_right_avg = map(
            lambda points_group: np.array([np.average([*map(lambda x: x[1], points)]) for points in points_group]), [
                left_right_side_points[left_key][0], left_right_side_points[left_key][1], 
                left_right_side_points[right_key][0], left_right_side_points[right_key][1]
            ]
        )
        total_diff = np.average(left_left_avg - left_right_avg) + np.average(right_right_avg - right_left_avg)
        top_or_bottom_face_loc = FaceLocation.BOTTOM if total_diff > 0 else FaceLocation.TOP
        top_or_bottom_key = (set(face_contours.keys()) - {left_key, right_key}).pop()

        # guardrails against stupid cases
        is_below_left, is_below_right = (center_of_masses[top_or_bottom_key][1] > center_of_masses[left_key][1], 
                                         center_of_masses[top_or_bottom_key][1] > center_of_masses[right_key][1])
        if (is_below_left != is_below_right) or (is_below_left ^ (top_or_bottom_face_loc == FaceLocation.BOTTOM)):
            raise ComputerVisionException("Something went wrong.")

        # construct final dict
        return {
            face_loc: face_contours[key]
            for face_loc, key in zip(
                [FaceLocation.LEFT, FaceLocation.RIGHT, top_or_bottom_face_loc],
                [left_key, right_key, top_or_bottom_key]
            )
        }

# helper function for the next function
# https://stackoverflow.com/a/44752405
def get_extreme_diff(channel: np.ndarray) -> np.ndarray:
    """ Finds extreme differences in a given array. """
    dilated = cv2.dilate(channel, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)))
    bg = cv2.medianBlur(dilated, 21)
    diff = 255 - cv2.absdiff(channel, bg) 
    return cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)

# this is only used to make the image less shadowy for the determine_face_colors function
def remove_shadows(img: cv2.Mat) -> cv2.Mat:
    """ Removes the shadows from a given image, returning a new image. """
    hsv_img = to_hsv(img)
    h, s, v = cv2.split(hsv_img)
    new_img = cv2.merge([h, s, get_extreme_diff(v)])
    return new_img

# gets the color at a given point, assuming it is one of the colors in the HSV range
def get_color(hsv_img: cv2.Mat, p: Point) -> Color:
    """ Gets the color at a given point in the `hsv_img`. """
    hsv_pixel = hsv_img[p[1], p[0]]
    for color, (h_ranges, *other_ranges) in HSV_FILTER_COLORS.items():
        for h_range in h_ranges:
            if all([x > x_range[0] and x < x_range[1] for x, x_range in zip(hsv_pixel, [h_range, *other_ranges])]):
                return color
    return None

# basically the last thing done in the pipeline
def determine_face_colors(img: cv2.Mat, squares_by_face: dict[FaceLocation, list[Contour]]) -> dict[FaceLocation, np.ndarray[Color]]:
    """ Determines an array of Colors for each FaceLocation in the given dictionary. """
    
    # determine the size of the cube 
    N = sqrt(max(map(len, squares_by_face.values())))
    if N != (N := int(N)):
        raise ComputerVisionException("Invalid cube detected. Squares per side is not a perfect square.")
    
    # save an hsv version of the image with removed shadows for use within the code
    removed_shadows = remove_shadows(img)

    face_to_colors = {}
    for face, squares in squares_by_face.items():

        # skip if bad square read
        if not sqrt(len(squares)) == N:
            continue
        
        # let the pivot point be the top-most corner of the cube, and find an arbitrary average angle to straighten by 
        pivot_point = min([min(cnt, key=lambda x: x[1]) for cnt in squares], key=lambda x: x[1])
        angles = [compute_incline_angle(*cnt[:2]) for cnt in squares]
        if np.std(angles) > ANGLE_DIFF_TOLERANCE:  # tries again to get more consistent angles, by giving points a better order
            second_try_squares = []
            for cnt in squares:
                x_axis_vals = [*map(lambda x: x[0], cnt)]
                max_index = np.argsort(x_axis_vals)
                if x_axis_vals[max_index[1]] - x_axis_vals[max_index[0]] < img.shape[1] / VERTICAL_CHECKING_SHAPE_DIVISOR:
                    y_axis_vals = [*map(lambda x: x[1], cnt)]
                    max_index = np.argsort(y_axis_vals)
                second_try_squares.append(np.concatenate((cnt[max_index[0]:], cnt[:max_index[0]]), axis=0))
            angles = [compute_incline_angle(*cnt[:2]) for cnt in second_try_squares]
        average_angle = radians(np.average(angles))

        # calculate new, rotated images to use
        new_contours = np.array([[get_rotated_point(pivot_point, p, -average_angle) for p in cnt] for cnt in squares])

        # sort the centers top to bottom, then insert the address of each contour into the thing
        centers_with_index = [(i, get_center(cnt)) for i, cnt in enumerate(new_contours)]
        sorted_centers = sorted(centers_with_index, key=lambda x: x[1][1])
        face_contour_map = [[
            index_point_pair[0] for index_point_pair in
            sorted(sorted_centers[N*i:N*(i+1)], key=lambda x: x[1][0])
        ] for i in range(N)]
        
        # now that we have determined what indeces of the squares list to look at, we can determine the color at each place
        face_to_colors[face] = np.array([[
            get_color(removed_shadows, get_center(squares[face_contour_map[i][j]]))
            for j in range(N)
        ] for i in range(N)])
    return face_to_colors

# this is the class that brings everything together, and what interacts with the outside
class ImageToCube:

    # we must spend at least these frames on a new orientation to consider it individual 
    ROTATION_ORDER: list[tuple[dict[FaceLocation, tuple[Face, int]]]] = [
        {FaceLocation.TOP: (Face.TOP, -1), FaceLocation.RIGHT: (Face.RIGHT, 2), FaceLocation.LEFT: (Face.FRONT, -1)},
        {FaceLocation.BOTTOM: (Face.RIGHT, 2), FaceLocation.RIGHT: (Face.BACK, 2), FaceLocation.LEFT: (Face.TOP, -1)},
        {FaceLocation.TOP: (Face.BACK, 2), FaceLocation.RIGHT: (Face.BOTTOM, 2), FaceLocation.LEFT: (Face.RIGHT, 2)},
        {FaceLocation.BOTTOM: (Face.BOTTOM, 2), FaceLocation.LEFT: (Face.BACK, 2), FaceLocation.RIGHT: (Face.LEFT, -1)},
        {FaceLocation.TOP: (Face.LEFT, -1), FaceLocation.LEFT: (Face.BOTTOM, 2), FaceLocation.RIGHT: (Face.FRONT, -1)},
        {FaceLocation.BOTTOM: (Face.FRONT, -1), FaceLocation.LEFT: (Face.LEFT, -1), FaceLocation.RIGHT: (Face.TOP, -1)}
    ]

    def __init__(self, N: int):

        # store which state of ROTATION_ORDER is being looked at
        self.state = 0

        # information about the cube
        self.cube_guesses = [np.empty((N, N, 1), dtype=object) for _ in range(6)]
        self.N = N
    
    def calculate_score(self, state: int, colors_by_face: dict[FaceLocation, list[list[Color]]]) -> float:
        """ Calculate the score for how well a state matches given colors_by_face. """
        
        scores = []
        for face_loc, (cube_face, rotation) in ImageToCube.ROTATION_ORDER[state % 6].items():

            # get current guess
            if face_loc not in colors_by_face:
                continue
            incoming_face_guess = ImageToCube.interpret_face_guess(cube_face, rotation, colors_by_face[face_loc])
            overall_face_guess = self.get_guess(cube_face)

            # assign scores to different scenarios 
            running_score_total = 0
            for i in range(self.N):
                for j in range(self.N):

                    # either square is none, | operator prevents short circuiting
                    if (inc_none := incoming_face_guess[i, j] is None) | (ove_none := overall_face_guess[i, j] is None):  
                        if ove_none and inc_none:
                            running_score_total += 0.5
                        elif ove_none:
                            running_score_total += 0.7
                        else:
                            running_score_total += 0.45

                    # check equality
                    elif incoming_face_guess[i, j] == overall_face_guess[i, j]:
                        running_score_total += 1.0

            scores.append(running_score_total / (self.N * self.N))

        # determine how many matched faces are there compared to how many faces were read
        score_modifier = (len(scores) / len(colors_by_face)) * 0.2
        return (np.average(scores) if scores else 0) + score_modifier

    @staticmethod
    def interpret_face_guess(cube_face: Face, rotation: int, current_face_guess: np.ndarray[Color]) -> np.ndarray[Color]:
        """ Given a current_face_guess, transform it to how it would be on the cube given values for rotation and cube_face. """
        rotated_guess = np.rot90(current_face_guess, rotation)
        if cube_face == Face.BOTTOM:
            return np.flip(rotated_guess, axis=1)
        return rotated_guess

    def translate(self, img: cv2.Mat):  # assume the image is already in low res

        # run through image processing process
        try:
            cubie_contours = get_cubie_contours(img)
            squares_by_angle = get_squares_by_angle(cubie_contours)
            interpolated_squares = fill_empty_squares(img, squares_by_angle)
            squares_by_face = get_squares_by_face(interpolated_squares)
            colors_by_face = determine_face_colors(img, squares_by_face)  # type hint to help LSP
        except ComputerVisionException:
            return
        
        # don't bother if read N is less than current N
        if len(next(iter(colors_by_face.values()))) != self.N:
            return

        # calculate scores for each state
        prev_state_score = self.calculate_score(self.state - 1, colors_by_face)
        curr_state_score = self.calculate_score(self.state, colors_by_face)
        next_state_score = self.calculate_score(self.state + 1, colors_by_face)

        # determine which state we are going to be on, this can be adjusted later
        if curr_state_score < max(prev_state_score, next_state_score):
            if next_state_score >= prev_state_score:
                self.state += 1
            else:
                self.state -= 1
        
        # go through each thing in the current state
        for face_loc, (cube_face, rotation) in ImageToCube.ROTATION_ORDER[self.state % 6].items():

            # apply needed transformations to be able to add the guess
            if not face_loc in colors_by_face:
                continue
            current_face_guess = ImageToCube.interpret_face_guess(cube_face, rotation, colors_by_face[face_loc])

            # incompatible N value
            try:
                current_face_guess = current_face_guess.reshape(self.N, self.N, 1)
            except ValueError:
                return
            
            # adds guess to array
            if (existing_guesses := self.cube_guesses[cube_face.value]) is not None:
                self.cube_guesses[cube_face.value] = np.concatenate((existing_guesses, current_face_guess), axis=2)
            else:
                self.cube_guesses[cube_face.value] = current_face_guess

    def get_guess(self, face: Face) -> np.ndarray:
        """ Determines the most likely setup of a face given already guessed colors. """
        temp_face_arr = [[None] * self.N for _ in range(self.N)]
        if self.cube_guesses[face.value] is not None:
            for i in range(self.N):
                for j in range(self.N):
                    not_none_colors = [x for x in self.cube_guesses[face.value][i, j] if x is not None]
                    temp_face_arr[i][j] = mode(not_none_colors) if not_none_colors else None
        return np.array(temp_face_arr)

    def create_cube(self) -> Cube:
        """ Uses a voting method to determine the most likely cube read. """
        most_voted_guesses = [None] * 6
        for face in list(Face):
            most_voted_guesses[face.value] = self.get_guess(face)
        if self.N == 3:
            return Cube3x3(scramble=most_voted_guesses)
        return Cube(self.N, scramble=most_voted_guesses)

if __name__ == "__main__":
    translator = ImageToCube(3)
    vidcap = cv2.VideoCapture("./../media/example_video.mov")
    while (image := vidcap.read())[0]:
        translator.translate(image[1])
    cube = translator.create_cube()
    print(cube)

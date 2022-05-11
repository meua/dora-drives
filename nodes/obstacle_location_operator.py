import logging
import time

import numpy as np
import pylot.utils
from pylot.perception.tracking.obstacle_trajectory import ObstacleTrajectory
from pylot.prediction.obstacle_prediction import ObstaclePrediction

from dora_watermark import dump, load

logger = logging.Logger("Obstacle Location")

from dora_tracing import extract_context, tracer


def get_predictions(obstacles, ego_transform):
    """Extracts obstacle predictions out of the message.
    This method is useful to build obstacle predictions when
    the operator directly receives detections instead of predictions.
    The method assumes that the obstacles are static.
    """
    predictions = []
    # Transform the obstacle into a prediction.
    for obstacle in obstacles:
        obstacle_trajectory = ObstacleTrajectory(obstacle, [])
        prediction = ObstaclePrediction(
            obstacle_trajectory,
            obstacle.transform,
            1.0,
            [ego_transform.inverse_transform() * obstacle.transform],
        )
        predictions.append(prediction)

    return predictions


def get_obstacle_locations(
    obstacles,
    depth_frame,
    ego_transform,
):

    depth_frame.camera_setup.set_transform(
        ego_transform * depth_frame.camera_setup.transform
    )

    for obstacle in obstacles:
        center_point = obstacle.bounding_box_2D.get_center_point()
        # Sample several points around the center of the bounding box
        # in case the bounding box is not well centered on the obstacle.
        # In such situations the center point might be in between legs,
        # and thus we might overestimate the distance.
        sample_points = []
        for delta_x in range(-30, 30, 5):
            for delta_y in range(-30, 30, 5):
                sample_point = center_point + pylot.utils.Vector2D(
                    delta_x, delta_y
                )
                if obstacle.bounding_box_2D.is_within(sample_point):
                    sample_points.append(sample_point)
        locations = depth_frame.get_pixel_locations(sample_points)
        # Choose the closest from the locations of the sampled points.
        min_distance = np.infty
        closest_location = None
        for location in locations:
            dist = location.distance(ego_transform.location)
            if dist < min_distance:
                min_distance = dist
                closest_location = location
        obstacle.transform = pylot.utils.Transform(
            closest_location, pylot.utils.Rotation()
        )
    return obstacles


def run(inputs):
    keys = inputs.keys()

    if (
        "depth_frame" not in keys
        or "obstacles_without_location" not in keys
        or "pose" not in keys
    ):
        return {}

    context = extract_context(inputs)
    with tracer.start_span(f"python-{__name__}-pickle-parsing", context=context):
        obstacles, timestamps = load(inputs, "obstacles_without_location")
        depth_frame, _ = load(inputs, "depth_frame")
        pose, _ = load(inputs, "pose")
        timestamps.append(("obstacle_location_operator_recieving", time.time()))

    context = extract_context(inputs)
    with tracer.start_span(f"python-{__name__}-obstacle-location", context=context):
        obstacles_with_location = get_obstacle_locations(
            obstacles,
            depth_frame,
            pose.transform,
        )

    context = extract_context(inputs)
    with tracer.start_span(f"python-{__name__}-location-prediction", context=context):
        obstacles_with_prediction = get_predictions(
            obstacles_with_location, pose.transform
        )


    timestamps.append(("obstacle_location_operator", time.time()))

    context = extract_context(inputs)
    with tracer.start_span(f"python-{__name__}-location-prediction", context=context):
        bytearray = dump(obstacles_with_prediction, timestamps)

    return {"obstacles": bytearray}

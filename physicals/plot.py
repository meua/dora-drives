import time
from typing import Callable

import cv2
import numpy as np
from dora import DoraStatus

font = cv2.FONT_HERSHEY_SIMPLEX
bottomLeftCornerOfText = (10, 500)
fontScale = 1
fontColor = (255, 255, 255)
thickness = 1
lineType = 2

LABELS = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]


class Operator:
    """
    Compute a `control` based on the position and the waypoints of the car.
    """

    def __init__(self):
        self.obstacles_bbox = []
        self.obstacles_id = []
        self.lanes = []
        self.drivable_area = []
        self.last_timestamp = time.time()
        self.camera_frame = []
        self.traffic_sign_bbox = []

    def on_event(
        self,
        dora_event: dict,
        send_output: Callable[[str, bytes], None],
    ) -> DoraStatus:
        if dora_event["type"] == "INPUT":
            return self.on_input(dora_event, send_output)
        return DoraStatus.CONTINUE

    def on_input(
        self,
        dora_input: dict,
        _send_output: Callable[[str, bytes], None],
    ):

        if "obstacles_bbox" == dora_input["id"]:
            self.obstacles_bbox = np.frombuffer(
                dora_input["data"], np.int32
            ).reshape((-1, 6))

        if "traffic_sign_bbox" == dora_input["id"]:
            self.traffic_sign_bbox = np.frombuffer(
                dora_input["data"], np.int32
            ).reshape((-1, 6))

        elif "obstacles_id" == dora_input["id"]:
            self.obstacles_id = np.frombuffer(
                dora_input["data"], np.int32
            ).reshape((-1, 7))

        elif "lanes" == dora_input["id"]:
            lanes = np.frombuffer(dora_input["data"], np.int32).reshape(
                (-1, 30, 2)
            )
            self.lanes = lanes

        elif "drivable_area" == dora_input["id"]:
            drivable_area = np.frombuffer(dora_input["data"], np.int32).reshape(
                (1, -1, 2)
            )
            self.drivable_area = drivable_area

        elif "image" == dora_input["id"]:
            self.camera_frame = cv2.imdecode(
                np.frombuffer(
                    dora_input["data"],
                    np.uint8,
                ),
                -1,
            )

        if "image" != dora_input["id"]:
            return DoraStatus.CONTINUE

        resized_image = self.camera_frame[:, :, :3]
        resized_image = np.ascontiguousarray(resized_image, np.uint8)

        for obstacles_bbox in self.obstacles_bbox:
            [min_x, max_x, min_y, max_y, confidence, label] = obstacles_bbox

            start = (int(min_x), int(min_y))
            end = (int(max_x), int(max_y))
            cv2.rectangle(resized_image, start, end, (0, 255, 0), 2)

            cv2.putText(
                resized_image,
                LABELS[label] + f", {confidence}%",
                (int(max_x), int(max_y)),
                font,
                0.75,
                (0, 255, 0),
                2,
                1,
            )

        for traffic_sign_bbox in self.traffic_sign_bbox:
            [min_x, max_x, min_y, max_y, confidence, label] = traffic_sign_bbox

            start = (int(min_x), int(min_y))
            end = (int(max_x), int(max_y))
            cv2.rectangle(resized_image, start, end, (122, 0, 122), 2)

            cv2.putText(
                resized_image,
                LABELS[label] + f", {confidence}%",
                (int(max_x), int(max_y)),
                font,
                0.75,
                (122, 0, 122),
                2,
                1,
            )

        for obstacle_id in self.obstacles_id:
            [
                min_x,
                max_x,
                min_y,
                max_y,
                track_id,
                confidence,
                label,
            ] = obstacle_id
            start = (int(min_x), int(min_y))
            end = (int(max_x), int(max_y))
            # cv2.rectangle(resized_image, start, end, (0, 255, 0), 2)

            cv2.putText(
                resized_image,
                f"#{track_id}",
                (int(max_x), int(max_y + 20)),
                font,
                0.75,
                (255, 140, 0),
                2,
                1,
            )

        for lane in self.lanes:
            cv2.polylines(resized_image, [lane], False, (0, 0, 255), 3)

        for contour in self.drivable_area:
            back = resized_image.copy()
            if len(contour) != 0:
                cv2.drawContours(back, [contour], 0, (0, 255, 0), -1)

                # blend with original image
                alpha = 0.25
                resized_image = cv2.addWeighted(
                    resized_image, 1 - alpha, back, alpha, 0
                )

        cv2.imshow("image", resized_image)
        cv2.waitKey(1)

        return DoraStatus.CONTINUE

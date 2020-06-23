import os
import time

import cv2
import numpy as np
import tensorflow as tf
from absl import app, flags, logging
from absl.flags import FLAGS

from yolov3_tf2.dataset import transform_images
from yolov3_tf2.models import YoloV3
from yolov3_tf2.utils import draw_outputs

flags.DEFINE_string('classifier', '', 'classifier name')
flags.DEFINE_integer('size', 416, 'resize images to')
flags.DEFINE_string('username', '', 'username')


def main(_argv):
    physical_devices = tf.config.experimental.list_physical_devices('GPU')
    for physical_device in physical_devices:
        tf.config.experimental.set_memory_growth(physical_device, True)

    classifier = FLAGS.classifier
    classifierPath = './classifiers/' + classifier

    class_names = [c.strip() for c in open(classifierPath + '/' + classifier + '.names').readlines()]
    logging.info('Classes loaded')

    yolo = YoloV3(classes=len(class_names))

    checkpointList = os.listdir(classifierPath + "/checkpoints")
    checkpointList.remove('checkpoint')
    lastCheckpoint = checkpointList[-1].split('.')[0] + '.' + checkpointList[-1].split('.')[1]

    yolo.load_weights(classifierPath + "/checkpoints/" + lastCheckpoint).expect_partial()
    logging.info('Weights loaded')

    toScanImagesPath = "./userData/" + FLAGS.username + "/toScan/"
    outputImagesPath = "./userData/" + FLAGS.username + "/output/"
    imagesList = os.listdir(toScanImagesPath)
    for image in imagesList:
        img_raw = tf.image.decode_image(open(toScanImagesPath + image, 'rb').read(), channels=3)

        img = tf.expand_dims(img_raw, 0)
        img = transform_images(img, FLAGS.size)

        t1 = time.time()
        boxes, scores, classes, nums = yolo(img)
        t2 = time.time()
        logging.info('Scan Time: {}'.format(t2 - t1))

        logging.info('Detections:')
        for i in range(nums[0]):
            logging.info('\t{}, {}, {}'.format(class_names[int(classes[0][i])],
                                               np.array(scores[0][i]),
                                               np.array(boxes[0][i])))

        img = cv2.cvtColor(img_raw.numpy(), cv2.COLOR_RGB2BGR)
        img = draw_outputs(img, (boxes, scores, classes, nums), class_names)
        imageOutputPath = outputImagesPath + image
        cv2.imwrite(imageOutputPath, img)
        logging.info('Output saved to: {}'.format(imageOutputPath))


if __name__ == '__main__':
    try:
        app.run(main)
    except SystemExit:
        pass

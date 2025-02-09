import os
from absl import app, flags, logging
from absl.flags import FLAGS
import numpy as np
from yolov3_tf2.models import YoloV3
from yolov3_tf2.utils import load_darknet_weights
import tensorflow as tf

flags.DEFINE_string('weights', './transferTrainingStart/yolov3.weights', 'path to weights file')
flags.DEFINE_string('output', './transferTrainingStart/yolov3.tf', 'path to output')
flags.DEFINE_integer('num_classes', 80, 'number of classes in the model')


def main(_argv):
    physical_devices = tf.config.experimental.list_physical_devices('GPU')
    if len(physical_devices) > 0:
        tf.config.experimental.set_memory_growth(physical_devices[0], True)

    yolo = YoloV3(classes=FLAGS.num_classes)
    yolo.summary()
    logging.info('Model created')

    load_darknet_weights(yolo, FLAGS.weights)
    logging.info('Weights loaded')

    img = np.random.random((1, 320, 320, 3)).astype(np.float32)
    output = yolo(img)
    logging.info('Sanity check passed')

    yolo.save_weights(FLAGS.output)
    logging.info('Model weights saved')

    os.remove(FLAGS.weights)
    logging.info('Old format weights delted')


if __name__ == '__main__':
    try:
        app.run(main)
    except SystemExit:
        pass

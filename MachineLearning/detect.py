import multiprocessing
import sys
import time
from absl import app, flags, logging
from absl.flags import FLAGS
import cv2
import numpy as np
import tensorflow as tf
from yolov3_tf2.models import YoloV3
from yolov3_tf2.dataset import transform_images, load_tfrecord_dataset
from yolov3_tf2.utils import draw_outputs

flags.DEFINE_string('classes', './data/coco.names', 'path to classes file')
flags.DEFINE_integer('num_classes', 80, 'number of classes in the model')
flags.DEFINE_string('weights', './checkpoints/yolov3.tf', 'path to weights file')
flags.DEFINE_integer('size', 416, 'resize images to')
flags.DEFINE_string('image', './data/girl.png', 'path to input image')
flags.DEFINE_string('tfrecord', None, 'tfrecord instead of image')
flags.DEFINE_string('output', './output/output.jpg', 'path to output image')


def main(_argv):
# def main():
    # print("Num GPUs Available: ", len(tf.config.experimental.list_physical_devices('GPU')))
    # physical_devices = tf.config.experimental.list_physical_devices('GPU')
    # if len(physical_devices) > 0:
    #     tf.config.experimental.set_visible_devices(physical_devices[1:], 'GPU')
    #     #tf.config.experimental.set_memory_growth(physical_devices[0], True)

    FLAGS(sys.argv)
    model = YoloV3(classes=FLAGS.num_classes)  # Loading the model with the number of classes

    model.load_weights(FLAGS.weights).expect_partial()
    logging.info('weights loaded')

    class_names = [c.strip() for c in open(FLAGS.classes).readlines()]
    logging.info('classes loaded')

    if FLAGS.tfrecord:
        dataset = load_tfrecord_dataset(
            FLAGS.tfrecord, FLAGS.classes, FLAGS.size)
        dataset = dataset.shuffle(512)
        img_raw, _label = next(iter(dataset.take(1)))
    else:
        img_raw = tf.image.decode_image(
            open(FLAGS.image, 'rb').read(), channels=3)  # 3 is the number of channels of the image

    img = tf.expand_dims(img_raw, 0)
    img = transform_images(img, FLAGS.size)

    t1 = time.time()
    boxes, scores, classes, nums = model(img)
    t2 = time.time()
    logging.info('time: {} seconds'.format(t2 - t1))

    logging.info('detections:')
    for i in range(nums[0]):
        logging.info('\t{}, {}, {}'.format(class_names[int(classes[0][i])],
                                           np.array(scores[0][i]),
                                           np.array(boxes[0][i])))

    img = cv2.cvtColor(img_raw.numpy(), cv2.COLOR_RGB2BGR)
    img = draw_outputs(img, (boxes, scores, classes, nums), class_names)
    cv2.imwrite(FLAGS.output, img)
    logging.info('output saved to: {}'.format(FLAGS.output))

    return 0


if __name__ == '__main__':
    try:
        app.run(main)
        # p = multiprocessing.Process(target=main, name="main")
        # p.start()
        #
        # p.join(10)
        #
        # if p.is_alive():
        #     print('function terminated')
        #     p.terminate()
        #     p.join()
        # else:
        #     print('function ??terminated')
    except SystemExit:
        pass
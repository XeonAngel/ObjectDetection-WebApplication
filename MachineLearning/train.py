import os
import requests

import numpy as np
import tensorflow as tf
from absl import app, flags, logging
from absl.flags import FLAGS
from tensorflow.keras.callbacks import (
    ReduceLROnPlateau,
    EarlyStopping,
    ModelCheckpoint,
    TensorBoard,
    Callback
)

import MachineLearning.yolov3_tf2.dataset as dataset
from MachineLearning.yolov3_tf2.models import (
    YoloV3, YoloLoss,
    yolo_anchors, yolo_anchor_masks
)
from MachineLearning.yolov3_tf2.utils import freeze_all

flags.DEFINE_string('classifier', '', 'classifier name')
flags.DEFINE_string('username', '', 'username')
flags.DEFINE_string('serverPath', '', 'serverPath')
flags.DEFINE_integer('size', 416, 'image size')
flags.DEFINE_integer('epochs', 8, 'number of epochs')
flags.DEFINE_integer('batch_size', 8, 'batch size')
flags.DEFINE_float('learning_rate', 1e-3, 'learning rate')
flags.DEFINE_enum('mode', 'fit', ['fit', 'eager_fit', 'eager_tf'],
                  'fit: model.fit, '
                  'eager_fit: model.fit(run_eagerly=True), '
                  'eager_tf: custom GradientTape')
flags.DEFINE_enum('transfer', 'none',
                  ['none', 'darknet', 'no_output', 'frozen', 'fine_tune'],
                  'none: Training from scratch, '
                  'darknet: Transfer darknet, '
                  'no_output: Transfer all but output, '
                  'frozen: Transfer and freeze all, '
                  'fine_tune: Transfer all and freeze darknet only')
flags.DEFINE_string('weights', './MachineLearning/transferTrainingStart/yolov3.tf', 'path to weights file')
flags.DEFINE_integer('weights_num_classes', 80, 'specify num class for `weights` file if different')


def main(_argv):
    physical_devices = tf.config.experimental.list_physical_devices('GPU')
    for physical_device in physical_devices:
        tf.config.experimental.set_memory_growth(physical_device, True)

    classifierPath = os.path.join('MachineLearning', 'classifiers', FLAGS.classifier)
    datasetPath = os.path.join(classifierPath, FLAGS.classifier + '_train.tfrecord')
    valDatasetPath = os.path.join(classifierPath, FLAGS.classifier + '_val.tfrecord')
    classesPath = os.path.join(classifierPath, FLAGS.classifier + '.names')
    class_names = [c.strip() for c in open(classesPath).readlines()]
    numClasses = len(class_names)

    anchors = yolo_anchors
    anchor_masks = yolo_anchor_masks
    model = YoloV3(FLAGS.size, training=True, classes=numClasses)

    train_dataset = dataset.load_tfrecord_dataset(datasetPath, classesPath, FLAGS.size)
    train_dataset = train_dataset.shuffle(buffer_size=512)
    train_dataset = train_dataset.batch(FLAGS.batch_size)
    train_dataset = train_dataset.map(lambda x, y: (
        dataset.transform_images(x, FLAGS.size),
        dataset.transform_targets(y, anchors, anchor_masks, FLAGS.size)))
    train_dataset = train_dataset.prefetch(
        buffer_size=tf.data.experimental.AUTOTUNE)

    val_dataset = dataset.load_tfrecord_dataset(valDatasetPath, classesPath, FLAGS.size)
    val_dataset = val_dataset.batch(FLAGS.batch_size)
    val_dataset = val_dataset.map(lambda x, y: (
        dataset.transform_images(x, FLAGS.size),
        dataset.transform_targets(y, anchors, anchor_masks, FLAGS.size)))

    # Configure the model for transfer learning
    if FLAGS.transfer == 'none':
        pass  # Nothing to do
    elif FLAGS.transfer in ['darknet', 'no_output']:
        # Darknet transfer is a special case that works
        # with incompatible number of classes

        # reset top layers
        model_pretrained = YoloV3(
            FLAGS.size, training=True, classes=FLAGS.weights_num_classes or numClasses)
        model_pretrained.load_weights(FLAGS.weights)

        if FLAGS.transfer == 'darknet':
            model.get_layer('yolo_darknet').set_weights(
                model_pretrained.get_layer('yolo_darknet').get_weights())
            freeze_all(model.get_layer('yolo_darknet'))

        elif FLAGS.transfer == 'no_output':
            for l in model.layers:
                if not l.name.startswith('yolo_output'):
                    l.set_weights(model_pretrained.get_layer(
                        l.name).get_weights())
                    freeze_all(l)

    else:
        # All other transfer require matching classes
        model.load_weights(FLAGS.weights)
        if FLAGS.transfer == 'fine_tune':
            # freeze darknet and fine tune other layers
            darknet = model.get_layer('yolo_darknet')
            freeze_all(darknet)
        elif FLAGS.transfer == 'frozen':
            # freeze everything
            freeze_all(model)

    optimizer = tf.keras.optimizers.Adam(lr=FLAGS.learning_rate)
    loss = [YoloLoss(anchors[mask], classes=numClasses)
            for mask in anchor_masks]

    if FLAGS.mode == 'eager_tf':
        # Eager mode is great for debugging
        # Non eager graph mode is recommended for real training
        avg_loss = tf.keras.metrics.Mean('loss', dtype=tf.float32)
        avg_val_loss = tf.keras.metrics.Mean('val_loss', dtype=tf.float32)

        for epoch in range(1, FLAGS.epochs + 1):
            for batch, (images, labels) in enumerate(train_dataset):
                with tf.GradientTape() as tape:
                    outputs = model(images, training=True)
                    regularization_loss = tf.reduce_sum(model.losses)
                    pred_loss = []
                    for output, label, loss_fn in zip(outputs, labels, loss):
                        pred_loss.append(loss_fn(label, output))
                    total_loss = tf.reduce_sum(pred_loss) + regularization_loss

                grads = tape.gradient(total_loss, model.trainable_variables)
                optimizer.apply_gradients(
                    zip(grads, model.trainable_variables))

                logging.info("{}_train_{}, {}, {}\n".format(
                    epoch, batch, total_loss.numpy(),
                    list(map(lambda x: np.sum(x.numpy()), pred_loss))))
                avg_loss.update_state(total_loss)

            for batch, (images, labels) in enumerate(val_dataset):
                outputs = model(images)
                regularization_loss = tf.reduce_sum(model.losses)
                pred_loss = []
                for output, label, loss_fn in zip(outputs, labels, loss):
                    pred_loss.append(loss_fn(label, output))
                total_loss = tf.reduce_sum(pred_loss) + regularization_loss

                logging.info("{}_val_{}, {}, {}\n".format(
                    epoch, batch, total_loss.numpy(),
                    list(map(lambda x: np.sum(x.numpy()), pred_loss))))
                avg_val_loss.update_state(total_loss)

            logging.info("{}, train: {}, val: {}\n".format(
                epoch,
                avg_loss.result().numpy(),
                avg_val_loss.result().numpy()))

            avg_loss.reset_states()
            avg_val_loss.reset_states()
            model.save_weights(classifierPath + '/checkpoints/{}_train_{}.tf'.format(FLAGS.classifier, epoch))
    else:
        model.compile(optimizer=optimizer, loss=loss, run_eagerly=(FLAGS.mode == 'eager_fit'))

        callbacks = [
            ReduceLROnPlateau(verbose=1),
            # EarlyStopping(patience=3, verbose=1),
            # ReduceLROnPlateau(monitor='loss', factor=0.1, patience=3, verbose=1),
            EarlyStopping(monitor='loss', min_delta=0, patience=10, verbose=1),
            ModelCheckpoint(classifierPath + '/checkpoints/' + FLAGS.classifier + '_train_{epoch}.tf',
                            verbose=1, save_weights_only=True),
            TensorBoard(log_dir=classifierPath + '/trainingLogs'),
            CustomCallback()
        ]

        history = model.fit(train_dataset, epochs=FLAGS.epochs, callbacks=callbacks, validation_data=val_dataset)

    checkpointList = os.listdir(classifierPath + "/checkpoints")
    checkpointList.remove('checkpoint')
    maxim = -1
    for i in range(2, len(checkpointList), 3):
        maxim = max(maxim, int(checkpointList[i].split('_')[2].split('.')[0]))

    checkpointList.remove(FLAGS.classifier + '_train_' + str(maxim) + '.tf.index')
    checkpointList.remove(FLAGS.classifier + '_train_' + str(maxim) + '.tf.data-00000-of-00002')
    checkpointList.remove(FLAGS.classifier + '_train_' + str(maxim) + '.tf.data-00001-of-00002')
    for checkpoint in checkpointList:
        os.remove(classifierPath + "/checkpoints/" + checkpoint)

    os.remove(datasetPath)
    os.remove(valDatasetPath)
    logging.info('Dataset cleaned\n')

    data = {'trainingStatus': 'Done',
            'classifier': FLAGS.classifier,
            'username': FLAGS.username}
    requests.post(url=FLAGS.serverPath, data=data)


class CustomCallback(Callback):
    def on_epoch_end(self, epoch, logs=None):
        # keys = list(logs.keys())
        data = {'loss': logs['loss'],
                'val_loss': logs['val_loss'],
                'epoch': epoch + 1,
                'total_epoch': FLAGS.epochs,
                'classifier': FLAGS.classifier,
                'username': FLAGS.username}
        requests.post(url=FLAGS.serverPath, data=data)


if __name__ == '__main__':
    try:
        app.run(main)
    except SystemExit:
        pass

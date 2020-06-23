import hashlib
import os
import shutil

import lxml.etree
import tensorflow as tf
import tqdm
from absl import app, flags, logging
from absl.flags import FLAGS

flags.DEFINE_string('classifier', '', 'classifier name')


def build_example(annotation, class_map, dataDirectory):
    img_path = os.path.join(
        dataDirectory, 'JPEGImages', annotation['filename'])
    img_raw = open(img_path, 'rb').read()
    key = hashlib.sha256(img_raw).hexdigest()

    width = int(annotation['size']['width'])
    height = int(annotation['size']['height'])

    xmin = []
    ymin = []
    xmax = []
    ymax = []
    classes = []
    classes_text = []
    truncated = []
    views = []
    difficult_obj = []
    if 'object' in annotation:
        for obj in annotation['object']:
            difficult = bool(int(obj['difficult']))
            difficult_obj.append(int(difficult))

            xmin.append(float(obj['bndbox']['xmin']) / width)
            ymin.append(float(obj['bndbox']['ymin']) / height)
            xmax.append(float(obj['bndbox']['xmax']) / width)
            ymax.append(float(obj['bndbox']['ymax']) / height)
            classes_text.append(obj['name'].encode('utf8'))
            classes.append(class_map[obj['name']])
            truncated.append(int(obj['truncated']))
            views.append(obj['pose'].encode('utf8'))

    example = tf.train.Example(features=tf.train.Features(feature={
        'image/height': tf.train.Feature(int64_list=tf.train.Int64List(value=[height])),
        'image/width': tf.train.Feature(int64_list=tf.train.Int64List(value=[width])),
        'image/filename': tf.train.Feature(bytes_list=tf.train.BytesList(value=[
            annotation['filename'].encode('utf8')])),
        'image/source_id': tf.train.Feature(bytes_list=tf.train.BytesList(value=[
            annotation['filename'].encode('utf8')])),
        'image/key/sha256': tf.train.Feature(bytes_list=tf.train.BytesList(value=[key.encode('utf8')])),
        'image/encoded': tf.train.Feature(bytes_list=tf.train.BytesList(value=[img_raw])),
        'image/format': tf.train.Feature(bytes_list=tf.train.BytesList(value=['jpeg'.encode('utf8')])),
        'image/object/bbox/xmin': tf.train.Feature(float_list=tf.train.FloatList(value=xmin)),
        'image/object/bbox/xmax': tf.train.Feature(float_list=tf.train.FloatList(value=xmax)),
        'image/object/bbox/ymin': tf.train.Feature(float_list=tf.train.FloatList(value=ymin)),
        'image/object/bbox/ymax': tf.train.Feature(float_list=tf.train.FloatList(value=ymax)),
        'image/object/class/text': tf.train.Feature(bytes_list=tf.train.BytesList(value=classes_text)),
        'image/object/class/label': tf.train.Feature(int64_list=tf.train.Int64List(value=classes)),
        'image/object/difficult': tf.train.Feature(int64_list=tf.train.Int64List(value=difficult_obj)),
        'image/object/truncated': tf.train.Feature(int64_list=tf.train.Int64List(value=truncated)),
        'image/object/view': tf.train.Feature(bytes_list=tf.train.BytesList(value=views)),
    }))
    return example


def parse_xml(xml):
    if not len(xml):
        return {xml.tag: xml.text}
    result = {}
    for child in xml:
        child_result = parse_xml(child)
        if child.tag != 'object':
            result[child.tag] = child_result[child.tag]
        else:
            if child.tag not in result:
                result[child.tag] = []
            result[child.tag].append(child_result[child.tag])
    return {xml.tag: result}


def main(_argv):
    dataDirectory = './classifiers/' + FLAGS.classifier + '/' + FLAGS.classifier + '-PascalVOC-export'
    labelMapPath = dataDirectory + '/pascal_label_map.pbtxt'
    classesNamePath = './classifiers/' + FLAGS.classifier + '/' + FLAGS.classifier + '.names'
    classList = ''
    with open(labelMapPath) as f:
        for line in f:
            try:
                result = line.split('\'')[1]
            except:
                continue
            classList = classList + result + '\n'

    f = open(classesNamePath, "w")
    f.write(classList)
    f.close()

    class_map = {name: idx for idx, name in enumerate(
        open(classesNamePath).read().splitlines())}
    logging.info("Class mapping loaded: %s", class_map)

    splitList = ['train', 'val']
    for split in splitList:
        writer = tf.io.TFRecordWriter(
            './classifiers/' + FLAGS.classifier + '/' + FLAGS.classifier + '_' + split + '.tfrecord')
        imagesPath = os.path.join(dataDirectory, 'ImageSets', 'Main', next(iter(class_map)) + '_%s.txt' % split)
        image_list = open(imagesPath).read().splitlines()
        logging.info("Image list loaded: %d", len(image_list))
        for image in tqdm.tqdm(image_list):
            name, _ = image.split('.')
            annotation_xml = os.path.join(
                dataDirectory, 'Annotations', name + '.xml')
            annotation_xml = lxml.etree.fromstring(open(annotation_xml).read())
            annotation = parse_xml(annotation_xml)['annotation']
            tf_example = build_example(annotation, class_map, dataDirectory)
            writer.write(tf_example.SerializeToString())
        writer.close()
        logging.info("Done")

    shutil.rmtree(dataDirectory)
    logging.info("Data directory deleted")


if __name__ == '__main__':
    app.run(main)

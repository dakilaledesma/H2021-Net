#!/usr/bin/python -u

from tensorflow.keras.applications.densenet import preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.densenet import DenseNet201
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model, load_model
from sklearn.utils import shuffle
import tensorflow as tf
import numpy as np
import tensorflow.keras
import tensorflow.keras.backend as K
from tensorflow.keras.optimizers import Optimizer
import pandas as pd
import pickle
import os
import random

os.environ['TF_KERAS'] = '1'

import sys

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)

batch_size = 128
epochs = 20
image_fp = np.load("data/image_fps.npy")
labels = np.load("data/labels.npy")
print(min(labels), max(labels))
labels = np.array(labels)

# def generator():
#     i = 0
#     while i < len(image_fp) * epochs:
#         wrap_index = i
#         while wrap_index >= len(image_fp):
#             wrap_index -= len(image_fp)
#         label = np.zeros(32094)
#         label[labels[wrap_index]] = 1
#         yield image_fp[wrap_index], label
#         i += 1

random_indices = []
for i in range(epochs):
    random_indices += random.sample(range(len(image_fp)), len(image_fp))


def generator():
    i = 0
    while i < len(image_fp) * epochs:
        label = np.zeros(32094)
        label[labels[random_indices[i]]] = 1
        yield image_fp[random_indices[i]], label
        i += 1


# def generator():
#     i = 0
#     while i < len(image_fp):
#         label = np.zeros(32094)
#         label[labels[i]] = 1
#         yield image_fp[i], label
#         i += 1


def parse_function(filename, label):
    image_string = tf.io.read_file(filename)
    image = tf.image.decode_jpeg(image_string, channels=3)
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = tf.image.resize(image, [320, 320])
    return image, label


def train_preprocess(image, label):
    image = preprocess_input(image)
    image = tf.image.random_flip_left_right(image)
    return image, label


tfds = tf.data.Dataset.from_generator(generator, output_types=(tf.string, tf.float32),
                                      output_shapes=(None, [32094]))
tfds = tfds.map(parse_function, num_parallel_calls=20).map(train_preprocess, num_parallel_calls=20)
tfds = tfds.batch(batch_size)
tfds = tfds.prefetch(10)

"""
https://stackoverflow.com/questions/37340129/tensorflow-training-on-my-own-image
"""

model_checkpoint_callback = tensorflow.keras.callbacks.ModelCheckpoint(
    filepath="cp/densenet201-7-tf1-{epoch:02d}",
    save_weights_only=False,
    monitor='loss',
    mode='min',
    save_best_only=False)

strategy = tf.distribute.MirroredStrategy()
print(f'Number of devices: {strategy.num_replicas_in_sync}')
with strategy.scope():
    '''
    Load model
    '''
    # model = load_model("cp/densenet201-5-bottleneck-01", custom_objects={'AdamAccumulate': AdamAccumulate}, compile=False)

    '''
    Without bottleneck
    '''
    model = DenseNet201(weights="imagenet", include_top=False, input_shape=(320, 320, 3), classes=32094)

    '''
    With bottleneck
    '''
    # en_model = DenseNet201(weights='noisy-student', include_top=False, input_shape=(320, 320, 3), pooling='avg')
    # model_output = Dense(512, activation='linear')(en_model.output)
    # model_output = Dense(32094, activation='softmax')(model_output)
    # model = Model(inputs=en_model.input, outputs=model_output)

    # model = Model(inputs=en_model.input, outputs=model_output)
    model.compile(optimizer='adam', loss="categorical_crossentropy", metrics=['acc'])

model.summary()
model.fit(tfds,
          steps_per_epoch=int(image_fp.shape[0] // batch_size),
          epochs=epochs,
          verbose=1,
          callbacks=[model_checkpoint_callback], max_queue_size=100, workers=20, use_multiprocessing=True)

model.save("models/densenet201-7-tf1")
# creating paths to src and data folders in the repo
import sys
import pathlib

# basic imports for data manipulation and visualization
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# silence max image size warning
from PIL import Image
Image.MAX_IMAGE_PIXELS = 1000000000 

# import modeling packages
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# modeling metrics
from sklearn.metrics import classification_report, confusion_matrix

def make_image_generators(split_path):
    train_path = split_path / 'train'
    train_generator = ImageDataGenerator().flow_from_directory(str(train_path),
                                                               target_size=(300, 300),
                                                               batch_size=20,
                                                               class_mode='binary',
                                                               interpolation='bicubic')
    
    test_path = split_path / 'test'
    test_generator = ImageDataGenerator().flow_from_directory(str(test_path),
                                                              target_size=(300, 300),
                                                              batch_size=20,
                                                              class_mode='binary',
                                                              interpolation='bicubic',
                                                              shuffle=False)
    
    val_path = split_path / 'val'
    val_generator = ImageDataGenerator().flow_from_directory(str(val_path),
                                                             target_size=(300, 300),
                                                             batch_size=20,
                                                             class_mode='binary',
                                                             interpolation='bicubic',
                                                             shuffle=False)
    
    return (train_generator, test_generator, val_generator)

def make_model():
    model = models.Sequential()
    model.add(layers.Conv2D(35, (3, 3), activation='tanh', input_shape=(300, 300, 3)))
    model.add(layers.MaxPooling2D((5, 5)))
    model.add(layers.Conv2D(20, (3, 3), activation='relu'))
    model.add(layers.MaxPooling2D((3, 3)))
    model.add(layers.Flatten())
    model.add(layers.Dense(40, activation='relu'))
    model.add(layers.Dropout(.2))
    model.add(layers.Dense(40, activation='relu'))
    model.add(layers.Dropout(.2))
    model.add(layers.Dense(40, activation='relu'))
    model.add(layers.Dense(1, activation='sigmoid'))
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model
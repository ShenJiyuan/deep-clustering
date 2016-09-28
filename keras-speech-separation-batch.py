# -*- coding: utf-8 -*-
"""
Created on Mon Sep 26 15:23:31 2016

@author: jcsilva
"""

import tensorflow as tf
from keras.models import Sequential
from keras.layers import Dropout, Activation, Input, Reshape, BatchNormalization
from keras.layers import Dense, LSTM, Bidirectional
from keras.layers.wrappers import TimeDistributed
from keras.layers.noise import GaussianNoise
from keras.optimizers import SGD, RMSprop, Adadelta
from keras.models import model_from_json
from feats import get_egs

import numpy as np
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

EMBEDDINGS_DIMENSION = 20
NUM_CLASSES = 3


def get_dims(generator, embedding_size):
    inp, out = next(generator)
    inp_shape = (None, inp.shape[-1])
    out_shape = (None, out.shape[-1]//NUM_CLASSES * embedding_size)
    return inp_shape, out_shape


def save_model(model, filename):
    # serialize model to JSON
    model_json = model.to_json()
    with open(filename + ".json", "w") as json_file:
        json_file.write(model_json)
    #serialize weights to HDF5
    model.save_weights(filename + ".h5")
    print("Saved model to disk")


def load_model(filename):
    # load json and create model
    json_file = open(filename + '.json', 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    loaded_model = model_from_json(loaded_model_json)
    # load weights into new model
    loaded_model.load_weights(filename + ".h5")
    print("Loaded model from disk")
    return loaded_model
 
 
def affinitykmeans(Y, V):
    def norm(tensor):
        square_tensor = tf.square(tensor)
        tensor_sum = tf.reduce_sum(square_tensor)
        frobenius_norm = tf.sqrt(tensor_sum)
        return frobenius_norm
    
    # V e Y estao vetorizados
    # Antes de mais nada, volto ao formato de matrizes
    V = tf.reshape(V, [-1, EMBEDDINGS_DIMENSION])
    Y = tf.reshape(Y, [-1, NUM_CLASSES])
   
    T = tf.transpose
    dot = tf.matmul
    return norm(dot(T(V), V)) - 2 * norm(dot(T(V), Y)) + norm(dot(T(Y), Y))


def train_nnet():
    inp_shape, out_shape = get_dims(get_egs('wavlist_short', 50),
                                    EMBEDDINGS_DIMENSION)
#    model = Sequential()
#    model.add(Dense(64, input_dim=INPUT_SAMPLE_SIZE, init='uniform'))
#    model.add(Activation('tanh'))
#    model.add(Dropout(0.5))
#    model.add(Dense(64, init='uniform'))
#    model.add(Activation('tanh'))
#    model.add(Dropout(0.5))
#    model.add(Dense(INPUT_SAMPLE_SIZE * EMBEDDINGS_DIMENSION, init='uniform'))
#    model.add(Activation('softmax'))

    model = Sequential()
    model.add(Bidirectional(LSTM(30, return_sequences=True),
                            input_shape=inp_shape))
    model.add(TimeDistributed(BatchNormalization(mode=2)))
#    model.add(GaussianNoise(0.77))
#    model.add(Dropout(0.5))
    model.add(Bidirectional(LSTM(30, return_sequences=True)))
    model.add(TimeDistributed(BatchNormalization(mode=2)))
#    model.add(GaussianNoise(0.77))
#    model.add(Dropout(0.5))
    model.add(TimeDistributed(Dense(out_shape[-1],
                                    init='uniform',
                                    activation='tanh')))
#    model.add(Reshape((12900,EMBEDDINGS_DIMENSION)))


    #model.add(TimeDistributed(Dense(EMBEDDINGS_DIMENSION)))
    #model.add(Activation('softmax'))

#    sgd = SGD(lr=1e-5, momentum=0.9, decay=0.0, nesterov=True)
    sgd = Adadelta()
    model.compile(loss=affinitykmeans, optimizer=sgd)

    model.fit_generator(get_egs('wavlist_short', 50),
                        samples_per_epoch=20, nb_epoch=10, max_q_size=10)
    # score = model.evaluate(X_test, y_test, batch_size=16)
    save_model(model, "model")


def main():
    train_nnet()
    loaded_model = load_model("model")

    x, y = next(get_egs('wavlist_short', 50))
    v = loaded_model.predict(x)
    x = x[0][::2]
    y = y[0][::2]
    v = v[0][::2]
    x = x.reshape((-1, 129))
    y = y.reshape((-1, 129, 3))
    v = v.reshape((-1, 129, EMBEDDINGS_DIMENSION))

    k = NUM_CLASSES
    model = KMeans(k)
    eg = model.fit_predict(v.reshape(-1, EMBEDDINGS_DIMENSION))
    imshape = y.shape
    img = np.zeros(eg.shape + (3,))
    img[eg == 0] = [1, 0, 0]
    img[eg == 1] = [0, 1, 0]
    if(k > 2):
        img[eg == 2] = [0, 0, 1]
        img[eg == 3] = [0, 0, 0]
    img = img.reshape(imshape)

    img2 = y
    img3 = x

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1)
    ax1.imshow(img.swapaxes(0, 1), origin='lower')
    ax2.imshow(img2.swapaxes(0, 1), origin='lower')
    ax3.imshow(img3.swapaxes(0, 1), origin='lower')


if __name__ == "__main__":
    main()
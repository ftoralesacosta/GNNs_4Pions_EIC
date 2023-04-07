import tensorflow as tf
from energyflow.archs import PFN
import h5py as h5
import numpy as np
import os
import shutil
import pickle

import sys
print(tf.config.experimental.list_physical_devices('GPU'))
sys.path.insert(0, '../functions')
from training_functions import *

import yaml

#Using YAML configuration File
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

h5_filename = config["h5_filename"]
print(h5_filename)
learning_rate = config["learning_rate"]
num_epochs = config["n_epochs"]
batch_size = config["batch_size"]

# h5_filename = "../generate_data/to_hdf5/Uniform_pi+_0-100GeV_standalone_TVT_Split.hdf5"
h5_file = h5.File(h5_filename,'r')

label = "Gen_Data_Fixed"  #Replace with your own variation!      
path = "./"+label
shutil.rmtree(path, ignore_errors=True)
os.makedirs(path)


do_normalization = True
input_dim = h5_file['train_hcal'].shape[-2] #should be 4: Cell E,X,Y,Z, the number of features per particle
learning_rate = 1e-3
dropout_rate = 0.1
batch_size = 1_000
N_Epochs = 50
patience = 10
N_Latent = 128
shuffle_split = True #Turn FALSE for images!
train_shuffle = True #Turn TRUE for images!
loss = 'mae' #'mae'

Phi_sizes, F_sizes = (100, 100, N_Latent), (100, 100, 100)
output_act, output_dim = 'linear', 1 #Train to predict error


pfn = PFN(input_dim=input_dim, 
          Phi_sizes=Phi_sizes, 
          F_sizes=F_sizes, 
          output_act=output_act, 
          output_dim=output_dim, 
          loss=loss, 
          latent_dropout=dropout_rate,
          F_dropouts=dropout_rate,
          optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate))


# Tensorflow CallBacks
lr_scheduler = tf.keras.callbacks.LearningRateScheduler(lr_decay,verbose=0)
early_stopping = tf.keras.callbacks.EarlyStopping(patience=patience)
history_logger=tf.keras.callbacks.CSVLogger(path+"/log.csv", separator=",", append=True)
model_checkpoint = tf.keras.callbacks.ModelCheckpoint(filepath=path, save_best_only=True)
callbacks=[lr_scheduler, early_stopping,history_logger,batch_history(),model_checkpoint]


train_generator = tf.data.Dataset.from_generator(
    training_generator(h5_filename,'train_hcal','train_mc',batch_size,do_normalization,path),
    output_shapes=(tf.TensorShape([None,None,None]),[None]),
    output_types=(tf.float64, tf.float64))

# train_generator = tf.data.Dataset.from_generator(
#     training_generator(h5_filename,'train_hcal','train_mc',batch_size,do_normalization,path),
#     tf.TensorSpec(shape=((None,None,None),(None)), dtype=tf.float64),
#     output_types=(tf.float64, tf.float64))

val_generator = tf.data.Dataset.from_generator(
    training_generator(h5_filename,'val_hcal','val_mc',batch_size,do_normalization,path),
    output_shapes=(tf.TensorShape([None,None,None]),[None]),
    output_types=(tf.float64, tf.float64))

test_generator = tf.data.Dataset.from_generator(
    test_generator(h5_filename,'test_hcal','test_mc',batch_size,do_normalization,path),
    output_shapes=(tf.TensorShape([None,None,None])),
    output_types=(tf.float64))


N_QA_Batches = 5 #number of batches for just plotting input data
pre_training_QA(h5_filename,path,N_QA_Batches,batch_size,do_normalization)

history = pfn.fit(
    train_generator,
    epochs=N_Epochs,
    batch_size=batch_size,
    callbacks=callbacks,
    validation_data=val_generator,
    verbose=1
)


#save batch loss
np.save("%s/batch_loss.npy"%(path),batch_history.batch_loss)

#save epoch loss
with open(path+'/history_file', 'wb') as hist_file:
    pickle.dump(history.history, hist_file)

pfn.layers
pfn.save("%s/energy_regression.h5"%(path))
mypreds = pfn.predict(test_generator, batch_size=1000)
np.save("%s/predictions.npy"%(path),mypreds)
#FIXME: un-norm the predictions





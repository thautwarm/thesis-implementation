# -*- coding: utf-8 -*-
"""
Created on Sun Jan 14 16:47:22 2018

@author: misakawa
"""

import matplotlib
import platform
if 'windows' in platform.architecture()[1].lower():
    pass
else:
    matplotlib.use("Agg")
from definition import *
import os
from linq import Flow
from linq.standard.general import Map
from skimage import data, img_as_float
from pipe_fn import infix, and_then
from matplotlib import pyplot as plt
from math import exp
from itertools import cycle
import dill
from noise_maker import poisson_noise, gaussian_noise

try:    
    model = torch.load('model_denoise', pickle_module=dill)
    print('load model')
except:    
    print('new_model')
    model = RainRemoval(8)

model.cuda()

train_dir = './rainy_image_dataset/ground truth'
raw_sources = Flow(os.listdir(train_dir))
train_data_size = 500
test_data_size = 100
epochs = 100
lr = 0.01
batch_group_num = 3
loss_fn = torch.nn.MSELoss(size_average=False)


def to_batch(image):
    target, *samples = image
    return (np.stack(samples),  # X
            np.stack([target] * len(samples)))

def mixed_noise(imgs_flow: np.ndarray):
    return and_then(
                gaussian_noise,  # 加高斯噪声
                poisson_noise)(imgs_flow)  # 浮点数张量 [0, 255]->[0, 1]

def DataIOStream(raw_src: Flow):
    return (raw_src
            .Filter(lambda x: x.endswith('.jpg'))  # select jpg files/选取jpg格式文件
            .Map(lambda x: os.path.join(train_dir, x))  # 拿到ground truth数据
            .Map(data.imread)
            .Map(lambda im:[im, 
                            mixed_noise(im), 
                            gaussian_noise(im), 
                            poisson_noise(im)] | infix/Map@img_as_float)
            .Map(to_batch))

train_batches = DataIOStream(raw_sources.Take(train_data_size).Then(cycle))
print('data_loaded')

loss = None
opt = torch.optim.Adam(model.parameters(), lr=lr)
try:
    for epoch in range(epochs):
        Loss: list = []
        train_loss = None
        
        for inner_idx, train in enumerate(train_batches.Take(train_data_size).Unboxed()):
            
            opt.zero_grad()
        
            train_samples, train_targets = train
            
            # 内存不足，只能取少一点的数据
    
            details, train_samples, train_targets = data_preprocessing(train_samples, train_targets)
            
            
            prediction = model(details.cuda(), train_samples.cuda())
    
            loss = loss_fn(prediction, train_targets.cuda())
            if train_loss is not None:
                train_loss += loss
            else:
                train_loss = loss
            
            if inner_idx is not 0 and inner_idx % batch_group_num == 0:
                train_loss.backward()
                opt.step()
                print('current-minibatch-loss:', train_loss.cpu().data.numpy()[0])
                train_loss = None
            
            loss = loss.cpu().data.numpy()[0]
            Loss.append(loss)
        
        if inner_idx % batch_group_num is not 0:
            train_loss.backward()
            opt.step()
            print('current-minibatch-loss:', train_loss.cpu().data.numpy()[0])
            train_loss = None
            
        Loss: float = np.mean(Loss)
        print('epoch {}. lr {}. loss: {}'.format(epoch, lr, Loss))
finally:
    print('saving model')
    torch.save(model.cpu(), 'model_denoise', pickle_module=dill)
    






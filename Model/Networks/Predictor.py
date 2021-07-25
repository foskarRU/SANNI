from Model.Networks.Base import BaseModel
from Model.Dataset import DataSet

import os
import json

import numpy as np
import matplotlib.pyplot as plt
from sklearn import metrics

from keras.layers import Conv2D
from keras.models import Model, Input, load_model
from keras.layers import Dense
from tensorflow.keras.layers import GRU, Dropout
from keras.regularizers import l1, l2, l1_l2


class Predictor(BaseModel):
    def __init__(self, size_subsequent: int, dataset: str, load=None) -> None:
        super().__init__(size_subsequent, dataset, load)
        self.dataset_dir = dataset
        self.bath_size = 25
        self.epochs = 40
        self.loss = "mse"
        self.optimizer = "adam"
        try:
            with open(dataset + "/networks.json", "r") as read_file:
                self.layers = json.load(read_file)["predict"]
        except Exception as e:
            print(e)
            self.layers = [128]
        self.model = self.__init_networks()
        print("Инициализации сверточной сети")

    def __init_networks(self):
        input_layer = Input((self.size_subsequent, 2),
                            name="img_input",
                            dtype='float32')
        output = input_layer
        for i in self.layers[:-1]:
            output = GRU(i,
                         return_sequences=True,
                         kernel_initializer='he_normal',
                         #          kernel_regularizer=l1_l2(l1=1e-5, l2=1e-4),
                         #           bias_regularizer=l2(1e-4),
                         #           activity_regularizer=l2(1e-5),

                         activation='relu')(output)
            output = Dropout(0.05)(output)
        output = GRU(self.layers[-1],
                     kernel_initializer='he_normal',
                     #    kernel_regularizer=l1_l2(l1=1e-5, l2=1e-4),
                     #    bias_regularizer=l2(1e-4),
                     #    activity_regularizer=l2(1e-5),
                     activation='relu')(output)
        output = Dropout(0.05)(output)
        output = Dense(1)(output)
        model = Model(inputs=input_layer, outputs=output)
        model.compile(loss=self.loss, optimizer=self.optimizer)
        model.summary()
        return model

    def init_dataset(self):
        self.dataset = DataSet(self.dataset_dir, self.bath_size, name="Predict", shuffle=False)

    def del_dataset(self):
        del self.dataset

    def train_model(self):
        print("Запуск обучения Предсказателя")

        history = self.model.fit(self.dataset.X_train.
                                 reshape(self.dataset.X_train.shape[0],
                                         self.dataset.X_train.shape[2],
                                         self.dataset.X_train.shape[1]),
                                 self.dataset.y_train,
                                 validation_data=(self.dataset.X_valid.
                                                  reshape(self.dataset.X_valid.shape[0],
                                                          self.dataset.X_valid.shape[2],
                                                          self.dataset.X_valid.shape[1]),
                                                  self.dataset.y_valid),
                                 batch_size=self.bath_size, epochs=self.epochs)

        plt.plot(history.history["loss"], label="train_dataset")
        plt.plot(history.history["val_loss"], label="valid_dataset")
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.savefig(self.dir_dataset + '/result/Predictor.png')
        print("Провел обучение")
        self.save_model()

    def load_model(self):
        self.model = load_model(self.dir_dataset + "/networks/predict.h5")
        print("Загрузка предсказателя сети из файла")

    def save_model(self) -> None:

        if not os.path.exists(self.dir_dataset + "/networks"):
            os.mkdir(self.dir_dataset + "/networks")

        self.model.save(self.dir_dataset + "/networks/predict.h5")

        with open(self.dir_dataset + "/current_params.json") as f:
            current = json.load(f)
        current["predict"] = True
        with open(self.dir_dataset + '/current_params.json', 'w') as outfile:
            json.dump(current, outfile)
        print("Сохранил модель")

    def test(self):
        y_predict = self.predict(self.dataset.X_test.reshape(self.dataset.X_test.shape[0],
                                                             self.dataset.X_test.shape[2],
                                                             self.dataset.X_test.shape[1]))

        print("mse предсказателя - {0};".
              format(metrics.mean_squared_error(y_true=self.dataset.y_test,
                                                y_pred=y_predict)))
        print("rmse предсказателя- {0};".
              format(metrics.mean_squared_error(y_true=self.dataset.y_test,
                                                y_pred=y_predict) * 0.5))
        result = {
            "mse": metrics.mean_squared_error(y_true=self.dataset.y_test, y_pred=y_predict),
            "rmse": metrics.mean_squared_error(y_true=self.dataset.y_test, y_pred=y_predict) * 0.5
        }
        with open(self.dir_dataset + "/result/predictor_result.txt", 'w') as outfile:
            json.dump(result, outfile)

        print("Провел внутренние тестирование предсказателя на основе сниппетов")

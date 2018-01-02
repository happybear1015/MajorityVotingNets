import tensorflow as tf
from data_pipeline import get_train_batch
import random
import numpy as np


class Hps:
    batch_size = 128
    x_size = 2
    y_size = 2
    learning_rate = 1e-3
    regularization = 1e-3
    hidden_layers = [7, ]


VARIABLES = 'variables'

random.seed(0)


class BaseModel:
    dtype = tf.float32

    def __init__(self, hps: Hps, iterator=None, is_train=True):
        self.hps = hps
        self.__build_layer()

        if is_train and iterator:
            self.loss, self.op, self.summary, self.global_steps = \
                self.get_loss_with_x_y(iterator.x, iterator.y)

    def __build_layer(self):
        with tf.variable_scope('hidden', reuse=tf.AUTO_REUSE):
            self.w = tf.get_variable(
                'w', [self.hps.x_size, self.hps.hidden_layers[0]],
                dtype=BaseModel.dtype, initializer=tf.truncated_normal_initializer(stddev=0.05)
            )
        tf.add_to_collection(VARIABLES, self.w)

        with tf.variable_scope('bias', reuse=tf.AUTO_REUSE):
            self.b = tf.get_variable(
                'b', [],
                dtype=BaseModel.dtype, initializer=tf.zeros_initializer
            )

        with tf.variable_scope('w2', reuse=tf.AUTO_REUSE):
            self.w2 = tf.get_variable(
                'w2', [self.hps.hidden_layers[0], self.hps.y_size],
                dtype=BaseModel.dtype, initializer=tf.truncated_normal_initializer(stddev=0.05)
            )

        tf.add_to_collection(VARIABLES, self.w2)

        with tf.variable_scope('b2', reuse=tf.AUTO_REUSE):
            self.b2 = tf.get_variable(
                'b2', [],
                dtype=BaseModel.dtype, initializer=tf.zeros_initializer
            )

    def get_loss(self, logits, y):
        loss = tf.losses.softmax_cross_entropy(y, logits)

        tf.summary.scalar('loss', loss)

        l2_loss = tf.nn.l2_loss
        loss += self.hps.regularization * tf.reduce_sum([l2_loss(self.w),
                                                         l2_loss(self.w2),
                                                         l2_loss(self.b),
                                                         l2_loss(self.b2)])

        return loss

    def eval(self, x):
        x = tf.cast(x, self.dtype)
        output_1 = tf.matmul(x, self.w) + self.b
        output_1 = tf.nn.leaky_relu(output_1)
        # predicate = tf.nn.sigmoid(predicate)

        output_2 = tf.matmul(output_1, self.w2) + self.b2
        # output_2 = tf.nn.relu(output_2)
        return output_2

    def get_loss_with_x_y(self, x, y):
        output = self.eval(x)
        loss = self.get_loss(output, y)
        op, global_steps = self.optimize(loss)
        summary = tf.summary.merge_all()

        return loss, op, summary, global_steps

    def optimize(self, loss):
        global_step = tf.Variable(0, trainable=False)
        learning_rate = tf.train.exponential_decay(self.hps.learning_rate, global_step,
                                                   1000, 0.90, staircase=False)
        op = (tf.train.AdamOptimizer(learning_rate=learning_rate)
                .minimize(loss, global_step=global_step))
        return op, global_step


hps1 = Hps(); hps1.hidden_layers = [7]
hps2 = Hps(); hps2.hidden_layers = [10]
hps3 = Hps(); hps3.hidden_layers = [15]
HPS = [hps1, hps2, hps3]


def train(hps):
    tf.reset_default_graph()

    epoch = 20
    mark = "2_dimensional_total_50_hidden_layer_{}_epoch_{}".format(hps.hidden_layers[0], epoch)

    iterator = get_train_batch('dataset/mini_corpus_train.txt', batch_size=hps.batch_size)
    model = BaseModel(hps, iterator=iterator)

    saver = tf.train.Saver()

    def save_model(_loss, global_step, _sess):
        model_file_name = './models/step-{}-loss-{}-mark-{}'.format(global_step, _loss, mark)
        saver.save(_sess, model_file_name, global_step=global_step)
        return model_file_name + '-' + str(global_step)

    total_steps = 0

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        for i in range(epoch):
            print('epoch: {}'.format(i))
            sess.run(iterator.initializer)
            while True:
                try:
                    loss, _, summary = sess.run([model.loss, model.op, model.summary])
                    if total_steps % 10 == 0: print("epoch: {} loss: {}".format(i, loss))
                    total_steps += 1

                except tf.errors.OutOfRangeError:
                    break # break while, into another for loop

        global_steps = sess.run(model.global_steps)
        print(global_steps)
        print('final loss {} precision is {}'.format(loss, np.e ** (-loss)))
        model_path = save_model(loss, global_steps, sess)
        return model_path


if __name__ == '__main__':
    # train(HPS[2])
    with open('model_paths.txt', 'w') as f:
        models = [train(hps) for hps in HPS]
        f.writelines('\n'.join(models))
from design_bench.oracles.tensorflow.tensorflow_oracle import TensorflowOracle
from design_bench.datasets.discrete_dataset import DiscreteDataset
from scipy import stats
import tensorflow as tf
import tensorflow.keras as keras
import tensorflow.keras.layers as layers
import tempfile
import math
import numpy as np


class ResNetOracle(TensorflowOracle):
    """An abstract class for managing the ground truth score functions f(x)
    for model-based optimization problems, where the
    goal is to find a design 'x' that maximizes a prediction 'y':

    max_x { y = f(x) }

    Public Attributes:

    dataset: DatasetBuilder
        an instance of a subclass of the DatasetBuilder class which has
        a set of design values 'x' and prediction values 'y', and defines
        batching and sampling methods for those attributes

    is_batched: bool
        a boolean variable that indicates whether the evaluation function
        implemented for a particular oracle is batched, which effects
        the scaling coefficient of its computational cost

    internal_batch_size: int
        an integer representing the number of design values to process
        internally at the same time, if None defaults to the entire
        tensor given to the self.score method
    internal_measurements: int
        an integer representing the number of independent measurements of
        the prediction made by the oracle, which are subsequently
        averaged, and is useful when the oracle is stochastic

    noise_std: float
        the standard deviation of gaussian noise added to the prediction
        values 'y' coming out of the ground truth score function f(x)
        in order to make the optimization problem difficult

    expect_normalized_y: bool
        a boolean indicator that specifies whether the inputs to the oracle
        score function are expected to be normalized
    expect_normalized_x: bool
        a boolean indicator that specifies whether the outputs of the oracle
        score function are expected to be normalized
    expect_logits: bool
        a boolean that specifies whether the oracle score function is
        expecting logits when the dataset is discrete

    Public Methods:

    predict(np.ndarray) -> np.ndarray:
        a function that accepts a batch of design values 'x' as input and for
        each design computes a prediction value 'y' which corresponds
        to the score in a model-based optimization problem

    check_input_format(DatasetBuilder) -> bool:
        a function that accepts a list of integers as input and returns true
        when design values 'x' with the shape specified by that list are
        compatible with this class of approximate oracle

    fit(np.ndarray, np.ndarray):
        a function that accepts a data set of design values 'x' and prediction
        values 'y' and fits an approximate oracle to serve as the ground
        truth function f(x) in a model-based optimization problem

    """

    name = "tensorflow_resnet"

    def __init__(self, dataset, noise_std=0.0, batch_size=32, **kwargs):
        """Initialize the ground truth score function f(x) for a model-based
        optimization problem, which involves loading the parameters of an
        oracle model and estimating its computational cost

        Arguments:

        dataset: DiscreteDataset
            an instance of a subclass of the DatasetBuilder class which has
            a set of design values 'x' and prediction values 'y', and defines
            batching and sampling methods for those attributes
        noise_std: float
            the standard deviation of gaussian noise added to the prediction
            values 'y' coming out of the ground truth score function f(x)
            in order to make the optimization problem difficult

        """

        # initialize the oracle using the super class
        super(ResNetOracle, self).__init__(
            dataset, noise_std=noise_std, is_batched=True,
            internal_batch_size=batch_size, internal_measurements=1,
            expect_normalized_y=True,
            expect_normalized_x=not isinstance(dataset, DiscreteDataset),
            expect_logits=False if isinstance(
                dataset, DiscreteDataset) else None, **kwargs)

    @classmethod
    def check_input_format(cls, dataset):
        """a function that accepts a model-based optimization dataset as input
        and determines whether the provided dataset is compatible with this
        oracle score function (is this oracle a correct one)

        Arguments:

        dataset: DatasetBuilder
            an instance of a subclass of the DatasetBuilder class which has
            a set of design values 'x' and prediction values 'y', and defines
            batching and sampling methods for those attributes

        Returns:

        is_compatible: bool
            a boolean indicator that is true when the specified dataset is
            compatible with this ground truth score function

        """

        # ensure that the data has exactly one sequence dimension
        if isinstance(dataset, DiscreteDataset) and not dataset.is_logits:
            return len(dataset.input_shape) == 1
        return len(dataset.input_shape) == 2

    def save_model_to_zip(self, model, zip_archive):
        """a function that serializes a machine learning model and stores
        that model in a compressed zip file using the python ZipFile interface
        for sharing and future loading by an ApproximateOracle

        Arguments:

        model: Any
            any format of of machine learning model that will be stored
            in the self.model attribute for later use

        zip_archive: ZipFile
            an instance of the python ZipFile interface that has loaded
            the file path specified by self.resource.disk_target

        """

        # extract the bytes of an h5 serialized model
        with tempfile.NamedTemporaryFile() as file:
            model["model"].save(file.name, save_format='h5')
            model_bytes = file.read()

        # write the h5 bytes ot the zip file
        with zip_archive.open('resnet.h5', "w") as file:
            file.write(model_bytes)  # save model bytes in the h5 format

        # write the validation rank correlation to the zip file
        with zip_archive.open('rank_correlation.npy', "w") as file:
            file.write(model["rank_correlation"].dumps())

    def load_model_from_zip(self, zip_archive):
        """a function that loads components of a serialized model from a zip
        given zip file using the python ZipFile interface and returns an
        instance of the model

        Arguments:

        zip_archive: ZipFile
            an instance of the python ZipFile interface that has loaded
            the file path specified by self.resource.disk_target

        Returns:

        model: Any
            any format of of machine learning model that will be stored
            in the self.model attribute for later use

        """

        # read the validation rank correlation from the zip file
        with zip_archive.open('rank_correlation.npy', "r") as file:
            rank_correlation = np.loads(file.read())

        # read the h5 bytes from the zip file
        with zip_archive.open('resnet.h5', "r") as file:
            model_bytes = file.read()  # read model bytes in the h5 format

        # load the model using a temporary file as a buffer
        with tempfile.NamedTemporaryFile() as file:
            file.write(model_bytes)
            return dict(model=keras.models.load_model(file.name),
                        rank_correlation=rank_correlation)

    def fit(self, dataset, hidden_size=512, activation='relu',
            kernel_size=3, num_blocks=4, epochs=25,
            shuffle_buffer=5000, learning_rate=0.001, **kwargs):
        """a function that accepts a set of design values 'x' and prediction
        values 'y' and fits an approximate oracle to serve as the ground
        truth function f(x) in a model-based optimization problem

        Arguments:

        dataset: DatasetBuilder
            an instance of a subclass of the DatasetBuilder class which has
            a set of design values 'x' and prediction values 'y', and defines
            batching and sampling methods for those attributes

        Returns:

        model: Any
            any format of of machine learning model that will be stored
            in the self.model attribute for later use

        """

        # prepare the dataset for training and validation
        training, validation = dataset.split(**kwargs)
        validation_x = self.dataset_to_oracle_x(validation.x)
        validation_y = self.dataset_to_oracle_y(validation.y)

        # obtain the expected shape of inputs to the model
        input_shape = training.input_shape
        if isinstance(training, DiscreteDataset) and training.is_logits:
            input_shape = input_shape[:-1]

        # the input layer of a keras model
        x = input_layer = keras.Input(shape=input_shape)

        # build a model with an input layer and optional embedding
        if isinstance(training, DiscreteDataset):
            x = layers.Embedding(training.num_classes, hidden_size)(x)
        else:
            x = layers.Dense(hidden_size,
                             activation=None, use_bias=False)(x)

        # the exponent of a positional embedding
        inverse_frequency = 1.0 / (10000.0 ** (tf.range(
            0.0, hidden_size, 2.0) / hidden_size))[tf.newaxis]

        # calculate a positional embedding to break symmetry
        pos = tf.range(0.0, tf.shape(x)[1], 1.0)[:, tf.newaxis]
        positional_embedding = tf.concat([
            tf.math.sin(pos * inverse_frequency),
            tf.math.cos(pos * inverse_frequency)], axis=1)[tf.newaxis]

        # add the positional encoding
        x = layers.Add()([x, positional_embedding])
        x = layers.LayerNormalization()(x)

        # add several residual blocks to the model
        for i in range(num_blocks):

            # first convolution layer in a residual block
            h = layers.Conv1D(hidden_size, kernel_size,
                              padding='same', activation=None)(x)
            h = layers.LayerNormalization()(h)
            h = layers.Activation(activation)(h)

            # second convolution layer in a residual block
            h = layers.Conv1D(hidden_size, kernel_size,
                              padding='same', activation=None)(h)
            h = layers.LayerNormalization()(h)
            h = layers.Activation(activation)(h)

            # add a residual connection to the model
            x = layers.Add()([x, h])

        # pool the final activations using an attention mechanism
        s = layers.Softmax(axis=1)(layers.Dense(1)(x))
        x = layers.Dot(axes=1)([x, s])
        x = layers.Reshape((hidden_size,))(x)

        # fully connected layer to regress to y values
        output_layer = layers.Dense(1)(x)
        model = keras.Model(inputs=input_layer,
                            outputs=output_layer)

        # estimate the number of training steps per epoch
        steps = int(math.ceil(training.dataset_size
                              / self.internal_batch_size))

        # build an optimizer to train the model
        lr = keras.experimental.CosineDecay(
            learning_rate, steps * epochs, alpha=0.0)
        optimizer = keras.optimizers.Adam(learning_rate=lr)
        model.compile(optimizer=optimizer, loss='mse')

        # fit the model to a tensorflow dataset
        model.fit(self.create_tensorflow_dataset(
            training, batch_size=self.internal_batch_size,
            shuffle_buffer=shuffle_buffer, repeat=epochs),
            steps_per_epoch=steps, epochs=epochs,
            validation_data=(validation_x, validation_y))

        # evaluate the validation rank correlation of the model
        rank_correlation = stats.spearmanr(
            model.predict(validation_x)[:, 0], validation_y[:, 0])[0]

        # return the trained model and rank correlation
        return dict(model=model,
                    rank_correlation=rank_correlation)

    def protected_predict(self, x):
        """Score function to be implemented by oracle subclasses, where x is
        either a batch of designs if self.is_batched is True or is a
        single design when self._is_batched is False

        Arguments:

        x_batch: np.ndarray
            a batch or single design 'x' that will be given as input to the
            oracle model in order to obtain a prediction value 'y' for
            each 'x' which is then returned

        Returns:

        y_batch: np.ndarray
            a batch or single prediction 'y' made by the oracle model,
            corresponding to the ground truth score for each design
            value 'x' in a model-based optimization problem

        """

        # call the model's predict function to generate predictions
        return self.model["model"].predict(x).numpy().astype(np.float32)
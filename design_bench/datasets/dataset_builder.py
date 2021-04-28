from design_bench.disk_resource import DiskResource
from collections.abc import Iterable
import numpy as np
import abc


class DatasetBuilder(abc.ABC):
    """An abstract base class that defines a common set of functions
    and attributes for a model-based optimization dataset, where the
    goal is to find a design 'x' that maximizes a prediction 'y':

    max_x { y = f(x) }

    Public Attributes:

    x: np.ndarray
        the design values 'x' for a model-based optimization problem
        represented as a numpy array of arbitrary type

    input_shape: Tuple[int]
        the shape of a single design values 'x', represented as a list of
        integers similar to calling np.ndarray.shape

    input_size: int
        the total number of components in the design values 'x', represented
        as a single integer, the product of its shape entries

    input_dtype: np.dtype
        the data type of the design values 'x', which is typically either
        floating point or integer (np.float32 or np.int32)

    y: np.ndarray
        the prediction values 'y' for a model-based optimization problem
        represented by a scalar floating point value per 'x'

    output_shape: Tuple[int]
        the shape of a single prediction value 'y', represented as a list of
        integers similar to calling np.ndarray.shape

    output_size: int
        the total number of components in the prediction values 'y',
        represented as a single integer, the product of its shape entries

    output_dtype: np.dtype
        the data type of the prediction values 'y', which is typically a
        type of floating point (np.float32 or np.float16)

    dataset_size: int
        the total number of paired design values 'x' and prediction values
        'y' in the dataset, represented as a single integer

    dataset_max_percentile: float
        the percentile between 0 and 100 of prediction values 'y' above
        which are hidden from access by members outside the class

    dataset_min_percentile: float
        the percentile between 0 and 100 of prediction values 'y' below
        which are hidden from access by members outside the class

    Public Methods:

    subsample(max_percentile: float,
              min_percentile: float):
        a function that exposes a subsampled version of a much larger
        model-based optimization dataset containing design values 'x'
        whose prediction values 'y' are skewed

    relabel(relabel_function:
            Callable[[np.ndarray, np.ndarray], np.ndarray]):
        a function that accepts a function that maps from a dataset of
        design values 'x' and prediction values y to a new set of
        prediction values 'y' and relabels the model-based optimization dataset

    normalize_x(new_x: np.ndarray) -> np.ndarray:
        a helper function that accepts floating point design values 'x'
        as input and standardizes them so that they have zero
        empirical mean and unit empirical variance

    denormalize_x(new_x: np.ndarray) -> np.ndarray:
        a helper function that accepts floating point design values 'x'
        as input and undoes standardization so that they have their
        original empirical mean and variance

    normalize_y(new_x: np.ndarray) -> np.ndarray:
        a helper function that accepts floating point prediction values 'y'
        as input and standardizes them so that they have zero
        empirical mean and unit empirical variance

    denormalize_y(new_x: np.ndarray) -> np.ndarray:
        a helper function that accepts floating point prediction values 'y'
        as input and undoes standardization so that they have their
        original empirical mean and variance

    map_normalize_x():
        a destructive function that standardizes the design values 'x'
        in the class dataset in-place so that they have zero empirical
        mean and unit variance

    map_denormalize_x():
        a destructive function that undoes standardization of the
        design values 'x' in the class dataset in-place which are expected
        to have zero  empirical mean and unit variance

    map_normalize_y():
        a destructive function that standardizes the prediction values 'y'
        in the class dataset in-place so that they have zero empirical
        mean and unit variance

    map_denormalize_y():
        a destructive function that undoes standardization of the
        prediction values 'y' in the class dataset in-place which are
        expected to have zero empirical mean and unit variance

    """

    @abc.abstractmethod
    def rebuild_dataset(self, x_shards, y_shards, **kwargs):
        """Initialize a model-based optimization dataset and prepare
        that dataset by loading that dataset from disk and modifying
        its distribution of designs and predictions

        Arguments:

        x_shards: Union[         np.ndarray,           RemoteResource,
                        Iterable[np.ndarray], Iterable[RemoteResource]]
            a single shard or a list of shards representing the design values
            in a model-based optimization dataset; shards are loaded lazily
            if RemoteResource otherwise loaded in memory immediately
        y_shards: Union[         np.ndarray,           RemoteResource,
                        Iterable[np.ndarray], Iterable[RemoteResource]]
            a single shard or a list of shards representing prediction values
            in a model-based optimization dataset; shards are loaded lazily
            if RemoteResource otherwise loaded in memory immediately
        **kwargs: dict
            additional keyword arguments used by sub classes that determine
            functionality or apply transformations to a model-based
            optimization dataset such as an internal batch size

        """

        raise NotImplementedError

    @abc.abstractmethod
    def batch_transform(self, x_batch, y_batch,
                        return_x=True, return_y=True):
        """Apply a transformation to batches of samples from a model-based
        optimization data set, including sub sampling and normalization
        and potentially other used defined transformations

        Arguments:

        x_batch: np.ndarray
            a numpy array representing a batch of design values sampled
            from a model-based optimization data set
        y_batch: np.ndarray
            a numpy array representing a batch of prediction values sampled
            from a model-based optimization data set
        return_x: bool
            a boolean indicator that specifies whether the generator yields
            design values at every iteration; note that at least one of
            return_x and return_y must be set to True
        return_y: bool
            a boolean indicator that specifies whether the generator yields
            prediction values at every iteration; note that at least one
            of return_x and return_y must be set to True

        Returns:

        x_batch: np.ndarray
            a numpy array representing a batch of design values sampled
            from a model-based optimization data set
        y_batch: np.ndarray
            a numpy array representing a batch of prediction values sampled
            from a model-based optimization data set

        """

        raise NotImplementedError

    def __init__(self, x_shards, y_shards, internal_batch_size=32):
        """Initialize a model-based optimization dataset and prepare
        that dataset by loading that dataset from disk and modifying
        its distribution of designs and predictions

        Arguments:

        x_shards: Union[         np.ndarray,           RemoteResource,
                        Iterable[np.ndarray], Iterable[RemoteResource]]
            a single shard or a list of shards representing the design values
            in a model-based optimization dataset; shards are loaded lazily
            if RemoteResource otherwise loaded in memory immediately
        y_shards: Union[         np.ndarray,           RemoteResource,
                        Iterable[np.ndarray], Iterable[RemoteResource]]
            a single shard or a list of shards representing prediction values
            in a model-based optimization dataset; shards are loaded lazily
            if RemoteResource otherwise loaded in memory immediately
        internal_batch_size: int
            the number of samples per batch to use when computing
            normalization statistics of the data set and while relabeling
            the prediction values of the data set

        """

        # save the provided dataset shards to be loaded into batches
        self.x_shards = (x_shards,) if \
            not isinstance(x_shards, Iterable) else x_shards
        self.y_shards = (y_shards,) if \
            not isinstance(y_shards, Iterable) else y_shards

        # download the remote resources if they are given
        self.num_shards = 0
        for x_shard, y_shard in zip(self.x_shards, self.y_shards):
            self.num_shards += 1
            if isinstance(x_shard, DiskResource) \
                    and not x_shard.is_downloaded:
                x_shard.download()
            if isinstance(y_shard, DiskResource) \
                    and not y_shard.is_downloaded:
                y_shard.download()

        # update variables that describe the data set
        self.dataset_min_percentile = 0.0
        self.dataset_max_percentile = 100.0
        self.dataset_min_output = np.NINF
        self.dataset_max_output = np.PINF

        # initialize the normalization state to False
        self.internal_batch_size = internal_batch_size
        self.is_normalized_x = False
        self.is_normalized_y = False

        # special flags that control when the dataset is mutable
        self.disable_transform = False
        self.freeze_statistics = False

        # initialize statistics for data set normalization
        self.x_mean = None
        self.y_mean = None
        self.x_standard_dev = None
        self.y_standard_dev = None

        # assign variables that describe the design values 'x'
        for x in self.iterate_samples(return_y=False):
            self.input_shape = x.shape
            self.input_size = int(np.prod(x.shape))
            self.input_dtype = x.dtype
            break  # only sample a single design from the data set

        # assign variables that describe the prediction values 'y'
        self.output_shape = [1]
        self.output_size = 1
        self.output_dtype = np.float32

        # check the output format and count the number of samples
        self.dataset_size = 0
        for i, y in enumerate(self.iterate_samples(return_x=False)):
            self.dataset_size += 1  # assume the data set is large
            if i == 0 and len(y.shape) != 1 or y.shape[0] != 1:
                raise ValueError(f"predictions must have shape [N, 1]")

    def get_num_shards(self):
        """A helper function that returns the number of shards in a
        model-based optimization data set, which is useful when the data set
        is too large to be loaded inot memory all at once

        Returns:

        num_shards: int
            an integer representing the number of shards in a model-based
            optimization data set that can be loaded

        """

        return self.num_shards

    def get_shard_x(self, shard_id):
        """A helper function used for retrieving the data associated with a
        particular shard specified by shard_id containing design values
        in a model-based optimization data set

        Arguments:

        shard_id: int
            an integer representing the particular identifier of the shard
            to be loaded from a model-based optimization data set

        Returns:

        shard_data: np.ndarray
            a numpy array that represents the data encoded in the shard
            specified by the integer identifier shard_id

        """

        # check the shard id is in bounds
        if 0 < shard_id >= self.get_num_shards():
            raise ValueError(f"shard id={shard_id} out of bounds")

        # if that shard entry is a numpy array
        if isinstance(self.x_shards[shard_id], np.ndarray):
            return self.x_shards[shard_id]

        # if that shard entry is stored on the disk
        elif isinstance(self.x_shards[shard_id], DiskResource):
            return np.load(self.x_shards[shard_id].disk_target)

    def get_shard_y(self, shard_id):
        """A helper function used for retrieving the data associated with a
        particular shard specified by shard_id containing prediction values
        in a model-based optimization data set

        Arguments:

        shard_id: int
            an integer representing the particular identifier of the shard
            to be loaded from a model-based optimization data set

        Returns:

        shard_data: np.ndarray
            a numpy array that represents the data encoded in the shard
            specified by the integer identifier shard_id

        """

        # check the shard id is in bounds
        if 0 < shard_id >= self.get_num_shards():
            raise ValueError(f"shard id={shard_id} out of bounds")

        # if that shard entry is a numpy array
        if isinstance(self.y_shards[shard_id], np.ndarray):
            return self.y_shards[shard_id]

        # if that shard entry is stored on the disk
        elif isinstance(self.y_shards[shard_id], DiskResource):
            return np.load(self.y_shards[shard_id].disk_target)

    def set_shard_x(self, shard_id, shard_data):
        """A helper function used for assigning the data associated with a
        particular shard specified by shard_id containing design values
        in a model-based optimization data set

        Arguments:

        shard_id: int
            an integer representing the particular identifier of the shard
            to be loaded from a model-based optimization data set

        shard_data: np.ndarray
            a numpy array that represents the data to be encoded in the
            shard specified by the integer identifier shard_id

        """

        # check the shard id is in bounds
        if 0 < shard_id >= self.get_num_shards():
            raise ValueError(f"shard id={shard_id} out of bounds")

        # if that shard entry is a numpy array
        if isinstance(self.x_shards[shard_id], np.ndarray):
            self.x_shards[shard_id] = shard_data

        # if that shard entry is stored on the disk
        elif isinstance(self.x_shards[shard_id], DiskResource):
            np.save(self.x_shards[shard_id].disk_target, shard_data)

    def set_shard_y(self, shard_id, shard_data):
        """A helper function used for assigning the data associated with a
        particular shard specified by shard_id containing prediction values
        in a model-based optimization data set

        Arguments:

        shard_id: int
            an integer representing the particular identifier of the shard
            to be loaded from a model-based optimization data set

        shard_data: np.ndarray
            a numpy array that represents the data to be encoded in the
            shard specified by the integer identifier shard_id

        """

        # check the shard id is in bounds
        if 0 < shard_id >= self.get_num_shards():
            raise ValueError(f"shard id={shard_id} out of bounds")

        # if that shard entry is a numpy array
        if isinstance(self.y_shards[shard_id], np.ndarray):
            self.y_shards[shard_id] = shard_data

        # if that shard entry is stored on the disk
        elif isinstance(self.y_shards[shard_id], DiskResource):
            np.save(self.y_shards[shard_id].disk_target, shard_data)

    def iterate_batches(self, batch_size, return_x=True,
                        return_y=True, drop_remainder=False):
        """Returns an object that supports iterations, which yields tuples of
        design values 'x' and prediction values 'y' from a model-based
        optimization data set for training a model

        Arguments:

        batch_size: int
            a positive integer that specifies the batch size of samples
            taken from a model-based optimization data set; batches
            with batch_size elements are yielded
        return_x: bool
            a boolean indicator that specifies whether the generator yields
            design values at every iteration; note that at least one of
            return_x and return_y must be set to True
        return_y: bool
            a boolean indicator that specifies whether the generator yields
            prediction values at every iteration; note that at least one
            of return_x and return_y must be set to True
        drop_remainder: bool
            a boolean indicator representing whether the last batch
            should be dropped in the case it has fewer than batch_size
            elements; the default behavior is not to drop the smaller batch.

        Returns:

        generator: Iterator
            a python iterable that yields samples from a model-based
            optimization data set and returns once finished

        """

        # check whether the generator arguments are valid
        if batch_size < 1 or (not return_x and not return_y):
            raise ValueError("invalid arguments passed to batch generator")

        # track a list of incomplete batches between shards
        y_batch_size = 0
        x_batch = [] if return_x else None
        y_batch = [] if return_y else None

        # iterate through every registered shard
        for shard_id in range(self.get_num_shards()):
            x_shard_data = self.get_shard_x(shard_id) if return_x else None
            y_shard_data = self.get_shard_y(shard_id)

            # loop once per batch contained in the shard
            shard_position = 0
            while shard_position < y_shard_data.shape[0]:

                # how many samples will be attempted to read
                target_size = batch_size - y_batch_size

                # slice out a component of the current shard
                x_sliced = x_shard_data[shard_position:(
                    shard_position + target_size)] if return_x else None
                y_sliced = y_shard_data[shard_position:(
                    shard_position + target_size)]

                # take a subset of the sliced arrays using a pre-defined
                # transformation that sub-samples and normalizes
                if not self.disable_transform:
                    x_sliced, y_sliced = self.batch_transform(
                        x_sliced, y_sliced,
                        return_x=return_x, return_y=return_y)

                # update the read position in the shard tensor
                shard_position += target_size
                samples_read = (y_sliced if
                                return_y else x_sliced).shape[0]

                # update the current batch to be yielded
                y_batch_size += samples_read
                x_batch.append(x_sliced) if return_x else None
                y_batch.append(y_sliced) if return_y else None

                # yield the current batch when enough samples are loaded
                if y_batch_size >= batch_size \
                        or (shard_position >= y_shard_data.shape[0]
                            and shard_id + 1 == self.get_num_shards()
                            and not drop_remainder):

                    try:

                        # determine which tensors to yield
                        if return_x and return_y:
                            yield np.concatenate(x_batch, axis=0), \
                                  np.concatenate(y_batch, axis=0)
                        elif return_x:
                            yield np.concatenate(x_batch, axis=0)
                        elif return_y:
                            yield np.concatenate(y_batch, axis=0)

                    except GeneratorExit:

                        # handle cleanup when break is called
                        return

                    # reset the buffer for incomplete batches
                    y_batch_size = 0
                    x_batch = [] if return_x else None
                    y_batch = [] if return_y else None

    def iterate_samples(self, return_x=True, return_y=True):
        """Returns an object that supports iterations, which yields tuples of
        design values 'x' and prediction values 'y' from a model-based
        optimization data set for training a model

        Arguments:

        return_x: bool
            a boolean indicator that specifies whether the generator yields
            design values at every iteration; note that at least one of
            return_x and return_y must be set to True
        return_y: bool
            a boolean indicator that specifies whether the generator yields
            prediction values at every iteration; note that at least one
            of return_x and return_y must be set to True

        Returns:

        generator: Iterator
            a python iterable that yields samples from a model-based
            optimization data set and returns once finished

        """

        # generator that only returns single samples
        for batch in self.iterate_batches(
                self.internal_batch_size,
                return_x=return_x, return_y=return_y):
            if return_x and return_y:
                for i in range(batch[0].shape[0]):
                    yield batch[0][i], batch[1][i]
            elif return_x or return_y:
                for i in range(batch.shape[0]):
                    yield batch[i]

    def __iter__(self):
        """Returns an object that supports iterations, which yields tuples of
        design values 'x' and prediction values 'y' from a model-based
        optimization data set for training a model

        Returns:

        generator: Iterator
            a python iterable that yields samples from a model-based
            optimization data set and returns once finished

        """

        # generator that returns batches of designs and predictions
        for x_batch, y_batch in \
                self.iterate_batches(self.internal_batch_size):
            yield x_batch, y_batch

    def update_x_statistics(self):
        """A helpful function that calculates the mean and standard deviation
        of the designs and predictions in a model-based optimization dataset
        either iteratively or all at once using numpy

        """

        # check that statistics are not frozen for this dataset
        if self.freeze_statistics:
            raise ValueError("cannot update dataset when it is frozen")

        # make sure the statistics are calculated from original samples
        original_is_normalized_x = self.is_normalized_x
        self.is_normalized_x = False

        # iterate through the entire dataset a first time
        samples = x_mean = 0
        for x_batch in self.iterate_batches(
                self.internal_batch_size, return_y=False):

            # calculate how many samples are actually in the current batch
            batch_size = np.array(x_batch.shape[0], dtype=np.float32)

            # update the running mean using dynamic programming
            x_mean = x_mean * (samples / (samples + batch_size)) + \
                np.sum(x_batch,
                       axis=0, keepdims=True) / (samples + batch_size)

            # update the number of samples used in the calculation
            samples += batch_size

        # iterate through the entire dataset a second time
        samples = x_variance = 0
        for x_batch in self.iterate_batches(
                self.internal_batch_size, return_y=False):

            # calculate how many samples are actually in the current batch
            batch_size = np.array(x_batch.shape[0], dtype=np.float32)

            # update the running variance using dynamic programming
            x_variance = x_variance * (samples / (samples + batch_size)) + \
                np.sum(np.square(x_batch - x_mean),
                       axis=0, keepdims=True) / (samples + batch_size)

            # update the number of samples used in the calculation
            samples += batch_size

        # expose the calculated mean and standard deviation
        self.x_mean = x_mean
        self.x_standard_dev = np.sqrt(x_variance)

        # remove zero standard deviations to prevent singularities
        self.x_standard_dev = np.where(
            self.x_standard_dev == 0.0, 1.0, self.x_standard_dev)

        # reset the normalized state to what it originally was
        self.is_normalized_x = original_is_normalized_x

    def update_y_statistics(self):
        """A helpful function that calculates the mean and standard deviation
        of the designs and predictions in a model-based optimization dataset
        either iteratively or all at once using numpy

        """

        # check that statistics are not frozen for this dataset
        if self.freeze_statistics:
            raise ValueError("cannot update dataset when it is frozen")

        # make sure the statistics are calculated from original samples
        original_is_normalized_y = self.is_normalized_y
        self.is_normalized_y = False

        # iterate through the entire dataset a first time
        samples = y_mean = 0
        for y_batch in self.iterate_batches(
                self.internal_batch_size, return_x=False):

            # calculate how many samples are actually in the current batch
            batch_size = np.array(y_batch.shape[0], dtype=np.float32)

            # update the running mean using dynamic programming
            y_mean = y_mean * (samples / (samples + batch_size)) + \
                np.sum(y_batch,
                       axis=0, keepdims=True) / (samples + batch_size)

            # update the number of samples used in the calculation
            samples += batch_size

        # iterate through the entire dataset a second time
        samples = y_variance = 0
        for y_batch in self.iterate_batches(
                self.internal_batch_size, return_x=False):

            # calculate how many samples are actually in the current batch
            batch_size = np.array(y_batch.shape[0], dtype=np.float32)

            # update the running variance using dynamic programming
            y_variance = y_variance * (samples / (samples + batch_size)) + \
                np.sum(np.square(y_batch - y_mean),
                       axis=0, keepdims=True) / (samples + batch_size)

            # update the number of samples used in the calculation
            samples += batch_size

        # expose the calculated mean and standard deviation
        self.y_mean = y_mean
        self.y_standard_dev = np.sqrt(y_variance)

        # remove zero standard deviations to prevent singularities
        self.y_standard_dev = np.where(
            self.y_standard_dev == 0.0, 1.0, self.y_standard_dev)

        # reset the normalized state to what it originally was
        self.is_normalized_y = original_is_normalized_y

    def subsample(self, max_percentile=100.0, min_percentile=0.0):
        """a function that exposes a subsampled version of a much larger
        model-based optimization dataset containing design values 'x'
        whose prediction values 'y' are skewed

        Arguments:

        max_percentile: float
            the percentile between 0 and 100 of prediction values 'y' above
            which are hidden from access by members outside the class
        min_percentile: float
            the percentile between 0 and 100 of prediction values 'y' below
            which are hidden from access by members outside the class

        """

        # check that statistics are not frozen for this dataset
        if self.freeze_statistics:
            raise ValueError("cannot update dataset when it is frozen")

        # return an error is the arguments are invalid
        if min_percentile > max_percentile:
            raise ValueError("invalid arguments provided")

        # convert the original prediction generator to a numpy tensor
        self.disable_transform = True
        y = np.concatenate(list(self.iterate_batches(
            self.internal_batch_size, return_x=False)), axis=0)
        self.disable_transform = False

        # calculate the min threshold for predictions in the dataset
        min_output = np.percentile(y[:, 0], min_percentile) \
            if min_percentile > 0.0 else np.NINF
        self.dataset_min_percentile = min_percentile
        self.dataset_min_output = min_output

        # calculate the max threshold for predictions in the dataset
        max_output = np.percentile(y[:, 0], max_percentile) \
            if max_percentile < 100.0 else np.PINF
        self.dataset_max_percentile = max_percentile
        self.dataset_max_output = max_output

        # create a mask for which predictions
        # in the dataset satisfy the range [min_threshold, max_threshold]
        # and update the size of the dataset based on the thresholds
        self.dataset_size = np.where(np.logical_and(
            y <= max_output, y >= min_output))[0].size

        # update normalization statistics for design values
        if self.is_normalized_x:
            self.update_x_statistics()

        # update normalization statistics for prediction values
        if self.is_normalized_y:
            self.update_y_statistics()

    @property
    def x(self) -> np.ndarray:
        """A helpful function for loading the design values from disk in case
        the dataset is set to load all at once rather than lazily and is
        overridden with a numpy array once loaded

        Returns:

        x: np.ndarray
            processed design values 'x' for a model-based optimization problem
            represented as a numpy array of arbitrary type

        """

        return np.concatenate([x for x in self.iterate_batches(
            self.internal_batch_size, return_y=False)], axis=0)

    @property
    def y(self) -> np.ndarray:
        """A helpful function for loading prediction values from disk in case
        the dataset is set to load all at once rather than lazily and is
        overridden with a numpy array once loaded

        Returns:

        y: np.ndarray
            processed prediction values 'y' for a model-based optimization
            problem represented as a numpy array of arbitrary type

        """

        return np.concatenate([y for y in self.iterate_batches(
            self.internal_batch_size, return_x=False)], axis=0)

    def relabel(self, relabel_function):
        """a function that accepts a function that maps from a dataset of
        design values 'x' and prediction values y to a new set of
        prediction values 'y' and relabels a model-based optimization dataset

        Arguments:

        relabel_function: Callable[[np.ndarray, np.ndarray], np.ndarray]
            a function capable of mapping from a numpy array of design
            values 'x' and prediction values 'y' to new predictions 'y' 
            using batching to prevent memory overflow

        """

        # check that statistics are not frozen for this dataset
        if self.freeze_statistics:
            raise ValueError("cannot update dataset when it is frozen")

        # prevent the data set for being sub-sampled or normalized
        self.disable_transform = True
        examples = self.y.shape[0]
        examples_processed = 0

        # track a list of incomplete batches between shards
        y_shard = []
        y_shard_size = 0

        # calculate the appropriate size of the first shard
        shard_id = 0
        shard = self.get_shard_y(shard_id)
        shard_size = shard.shape[0]

        # relabel the prediction values of the internal data set
        for x_batch, y_batch in \
                self.iterate_batches(self.internal_batch_size):

            # calculate the new prediction values to be stored as shards
            y_batch = relabel_function(x_batch, y_batch)
            read_position = 0

            # loop once per batch contained in the shard
            while read_position < y_batch.shape[0]:

                # calculate the intended number of samples to serialize
                target_size = shard_size - y_shard_size

                # slice out a component of the current shard
                y_slice = y_batch[read_position:read_position + target_size]
                samples_read = y_slice.shape[0]

                # increment the read position in the prediction tensor
                # and update the number of shards and examples processed
                read_position += target_size
                examples_processed += samples_read

                # update the current shard to be serialized
                y_shard.append(y_slice)
                y_shard_size += samples_read

                # yield the current batch when enough samples are loaded
                if y_shard_size >= shard_size \
                        or examples_processed >= examples:

                    # serialize the value of the new shard data
                    self.set_shard_y(shard_id,
                                     np.concatenate(y_shard, axis=0))

                    # reset the buffer for incomplete batches
                    y_shard = []
                    y_shard_size = 0

                    # calculate the appropriate size for the next shard
                    if not examples_processed >= examples:
                        shard_id += 1
                        shard = self.get_shard_y(shard_id)
                        shard_size = shard.shape[0]

        # re-sample the data set and recalculate statistics
        self.disable_transform = False
        self.subsample(max_percentile=self.dataset_max_percentile,
                       min_percentile=self.dataset_min_percentile)

    def clone(self, shard_size=5000, to_disk=False,
              disk_target="dataset", is_absolute=False):
        """Generate a cloned copy of a model-based optimization dataset
        using the provided name and shard generation settings; useful
        when relabelling a dataset buffer from the disk

        Arguments:

        shard_size: int
            an integer representing the number of samples from a model-based
            optimization data set to save per shard
        to_disk: boolean
            a boolean that indicates whether to store the split data set
            in memory as numpy arrays or to the disk
        disk_target: str
            a string that determines the name and sub folder of the saved
            data set if to_disk is set to be true
        is_absolute: boolean
            a boolean that indicates whether the disk_target path is taken
            relative to the benchmark data folder

        Returns:

        dataset: DatasetBuilder
            an instance of a data set builder subclass containing a copy
            of all data originally associated with this dataset

        """

        # disable transformations and check the size of the data set
        self.disable_transform = True
        original_y = self.y[:, 0]

        # create lists to store shards and numpy arrays
        partial_shard_x, partial_shard_y = [], []
        x_shards, y_shards = [], []

        # iterate once through the entire data set
        for sample_id, (x, y) in enumerate(self.iterate_samples()):

            # add the sampled x and y to the dataset
            partial_shard_x.append(x)
            partial_shard_y.append(y)

            # if the validation shard is large enough then write it
            if (sample_id + 1 == original_y.size and len(
                    partial_shard_x) > 0) or len(
                    partial_shard_x) >= shard_size:

                # stack the sampled x and y values into a shard
                shard_x = np.stack(partial_shard_x, axis=0)
                shard_y = np.stack(partial_shard_y, axis=0)

                if to_disk:

                    # write the design values shard first to a new file
                    x_resource = DiskResource(
                        f"{disk_target}-x-{len(x_shards)}.npy",
                        is_absolute=is_absolute,
                        download_method=None, download_target=None)
                    np.save(x_resource.disk_target, shard_x)
                    shard_x = x_resource

                    # write the prediction values shard second to a new file
                    y_resource = DiskResource(
                        f"{disk_target}-y-{len(y_shards)}.npy",
                        is_absolute=is_absolute,
                        download_method=None, download_target=None)
                    np.save(y_resource.disk_target, shard_y)
                    shard_y = y_resource

                # empty the partial shards and record the saved shard
                x_shards.append(shard_x)
                y_shards.append(shard_y)
                partial_shard_x.clear()
                partial_shard_y.clear()

            # at the last sample return two split data sets
            if sample_id + 1 == original_y.size:

                # remember to re-enable original transformations
                self.disable_transform = False

                # return a new version of the dataset
                return self.rebuild_dataset(x_shards, y_shards)

    def split(self, fraction, shard_size=5000,
              to_disk=False, disk_target="dataset", is_absolute=False):
        """Split a model-based optimization data set into a training set and
        a validation set allocating 'fraction' of the data set to the
        validation set and the rest to the training set

        Arguments:

        fraction: float
            a floating point number specifying the fraction of the original
            dataset to split into a validation set
        shard_size: int
            an integer representing the number of samples from a model-based
            optimization data set to save per shard
        to_disk: boolean
            a boolean that indicates whether to store the split data set
            in memory as numpy arrays or to the disk
        disk_target: str
            a string that determines the name and sub folder of the saved
            data set if to_disk is set to be true
        is_absolute: boolean
            a boolean that indicates whether the disk_target path is taken
            relative to the benchmark data folder

        Returns:

        training_dataset: DatasetBuilder
            an instance of a data set builder subclass containing all data
            points associated with the training set
        validation_dataset: DatasetBuilder
            an instance of a data set builder subclass containing all data
            points associated with the validation set

        """

        # disable transformations and check the size of the data set
        self.disable_transform = True
        original_y = self.y[:, 0]

        # select examples from the active set according to sub sampling
        active_ids = np.where(np.logical_and(
            self.dataset_min_output <= original_y,
            self.dataset_max_output >= original_y))[0]
        active_ids = active_ids[np.random.choice(
            active_ids.size, size=int(fraction * float(
                active_ids.size)), replace=False).tolist()]

        # select examples from the hidden set according to sub sampling
        hidden_ids = np.where(np.logical_and(
            self.dataset_min_output > original_y,
            self.dataset_max_output < original_y))[0]
        hidden_ids = hidden_ids[np.random.choice(
            hidden_ids.size, size=int(fraction * float(
                hidden_ids.size)), replace=False).tolist()]

        # generate a set of ids for the validation set
        validation_ids = set(np.append(active_ids,
                                       hidden_ids).tolist())

        # create lists to store shards and numpy arrays
        training_partial_shard_x, training_partial_shard_y = [], []
        training_x_shards, training_y_shards = [], []
        validation_partial_shard_x, validation_partial_shard_y = [], []
        validation_x_shards, validation_y_shards = [], []

        # iterate once through the entire data set
        for sample_id, (x, y) in enumerate(self.iterate_samples()):

            # add the sampled x and y to the training or validation set
            (validation_partial_shard_x if sample_id in
             validation_ids else training_partial_shard_x).append(x)
            (validation_partial_shard_y if sample_id in
             validation_ids else training_partial_shard_y).append(y)

            # if the validation shard is large enough then write it
            if (sample_id + 1 == original_y.size and len(
                    validation_partial_shard_x) > 0) or len(
                    validation_partial_shard_x) >= shard_size:

                # stack the sampled x and y values into a shard
                shard_x = np.stack(validation_partial_shard_x, axis=0)
                shard_y = np.stack(validation_partial_shard_y, axis=0)

                if to_disk:

                    # write the design values shard first to a new file
                    x_resource = DiskResource(
                        f"{disk_target}-val-x-"
                        f"{len(validation_x_shards)}.npy",
                        is_absolute=is_absolute,
                        download_method=None, download_target=None)
                    np.save(x_resource.disk_target, shard_x)
                    shard_x = x_resource

                    # write the prediction values shard second to a new file
                    y_resource = DiskResource(
                        f"{disk_target}-val-y-"
                        f"{len(validation_y_shards)}.npy",
                        is_absolute=is_absolute,
                        download_method=None, download_target=None)
                    np.save(y_resource.disk_target, shard_y)
                    shard_y = y_resource

                # empty the partial shards and record the saved shard
                validation_x_shards.append(shard_x)
                validation_y_shards.append(shard_y)
                validation_partial_shard_x.clear()
                validation_partial_shard_y.clear()

            # if the training shard is large enough then write it
            if (sample_id + 1 == original_y.size and len(
                    training_partial_shard_x) > 0) or len(
                    training_partial_shard_x) >= shard_size:

                # stack the sampled x and y values into a shard
                shard_x = np.stack(training_partial_shard_x, axis=0)
                shard_y = np.stack(training_partial_shard_y, axis=0)

                if to_disk:

                    # write the design values shard first to a new file
                    x_resource = DiskResource(
                        f"{disk_target}-train-x-"
                        f"{len(training_x_shards)}.npy",
                        is_absolute=is_absolute,
                        download_method=None, download_target=None)
                    np.save(x_resource.disk_target, shard_x)
                    shard_x = x_resource

                    # write the prediction values shard second to a new file
                    y_resource = DiskResource(
                        f"{disk_target}-train-y-"
                        f"{len(training_y_shards)}.npy",
                        is_absolute=is_absolute,
                        download_method=None, download_target=None)
                    np.save(y_resource.disk_target, shard_y)
                    shard_y = y_resource

                # empty the partial shards and record the saved shard
                training_x_shards.append(shard_x)
                training_y_shards.append(shard_y)
                training_partial_shard_x.clear()
                training_partial_shard_y.clear()

            # at the last sample return two split data sets
            if sample_id + 1 == original_y.size:

                # remember to re-enable original transformations
                self.disable_transform = False

                # check if the validation set is empty
                if (len(validation_x_shards) == 0 or
                        len(validation_y_shards) == 0):
                    raise ValueError("split produces empty training set")

                # check if the training set is empty
                if (len(training_x_shards) == 0 or
                        len(training_y_shards) == 0):
                    raise ValueError("split produces empty validation set")

                # build two new datasets
                dtraining = self.rebuild_dataset(
                    training_x_shards, training_y_shards)
                dvalidation = self.rebuild_dataset(
                    validation_x_shards, validation_y_shards)

                # intentionally freeze the dataset statistics in order
                # to prevent bugs once a data set is split
                dtraining.freeze_statistics = True
                dvalidation.freeze_statistics = True
                return dtraining, dvalidation

    def map_normalize_x(self):
        """a function that standardizes the design values 'x' to have zero
        empirical mean and unit empirical variance in the dataset

        """

        # check that statistics are not frozen for this dataset
        if self.freeze_statistics:
            raise ValueError("cannot update dataset when it is frozen")

        # check design values and prediction values are not normalized
        if not self.is_normalized_x:
            self.is_normalized_x = True

        # calculate the normalization statistics in advance
        self.update_x_statistics()

    def map_normalize_y(self):
        """a function that standardizes the prediction values 'y' to have
        zero empirical mean and unit empirical variance in the dataset

        """

        # check that statistics are not frozen for this dataset
        if self.freeze_statistics:
            raise ValueError("cannot update dataset when it is frozen")

        # check design values and prediction values are not normalized
        if not self.is_normalized_y:
            self.is_normalized_y = True

        # calculate the normalization statistics in advance
        self.update_y_statistics()

    def normalize_x(self, x):
        """a function that standardizes the design values 'x' to have
        zero empirical mean and unit empirical variance

        Arguments:

        x: np.ndarray
            a design value represented as a numpy array potentially
            given as a batch of designs which
            shall be normalized according to dataset statistics

        Returns:

        x: np.ndarray
            a design value represented as a numpy array potentially
            given as a batch of designs which
            has been normalized using dataset statistics

        """

        # calculate the mean and standard deviation of the prediction values
        if self.x_mean is None or self.x_standard_dev is None:
            self.update_x_statistics()

        # normalize the prediction values
        return (x - self.x_mean) / self.x_standard_dev

    def normalize_y(self, y):
        """a function that standardizes the prediction values 'y' to have
        zero empirical mean and unit empirical variance

        Arguments:

        y: np.ndarray
            a prediction value represented as a numpy array potentially
            given as a batch of predictions which
            shall be normalized according to dataset statistics

        Returns:

        y: np.ndarray
            a prediction value represented as a numpy array potentially
            given as a batch of predictions which
            has been normalized using dataset statistics

        """

        # calculate the mean and standard deviation of the prediction values
        if self.y_mean is None or self.y_standard_dev is None:
            self.update_y_statistics()

        # normalize the prediction values
        return (y - self.y_mean) / self.y_standard_dev

    def map_denormalize_x(self):
        """a function that un-standardizes the design values 'x' which have
        zero empirical mean and unit empirical variance in the dataset

        """

        # check that statistics are not frozen for this dataset
        if self.freeze_statistics:
            raise ValueError("cannot update dataset when it is frozen")

        # check design values and prediction values are normalized
        if self.is_normalized_x:
            self.is_normalized_x = False

    def map_denormalize_y(self):
        """a function that un-standardizes the prediction values 'y' which
        have zero empirical mean and unit empirical variance in the dataset

        """

        # check that statistics are not frozen for this dataset
        if self.freeze_statistics:
            raise ValueError("cannot update dataset when it is frozen")

        # check design values and prediction values are normalized
        if self.is_normalized_y:
            self.is_normalized_y = False

    def denormalize_x(self, x):
        """a function that un-standardizes the design values 'x' which have
        zero empirical mean and unit empirical variance

        Arguments:

        x: np.ndarray
            a design value represented as a numpy array potentially
            given as a batch of designs which
            shall be denormalized according to dataset statistics

        Returns:

        x: np.ndarray
            a design value represented as a numpy array potentially
            given as a batch of designs which
            has been denormalized using dataset statistics

        """

        # calculate the mean and standard deviation
        if self.x_mean is None or self.x_standard_dev is None:
            self.update_x_statistics()

        # denormalize the prediction values
        return x * self.x_standard_dev + self.x_mean

    def denormalize_y(self, y):
        """a function that un-standardizes the prediction values 'y' which
        have zero empirical mean and unit empirical variance

        Arguments:

        y: np.ndarray
            a prediction value represented as a numpy array potentially
            given as a batch of predictions which
            shall be denormalized according to dataset statistics

        Returns:

        y: np.ndarray
            a prediction value represented as a numpy array potentially
            given as a batch of predictions which
            has been denormalized using dataset statistics

        """

        # calculate the mean and standard deviation
        if self.y_mean is None or self.y_standard_dev is None:
            self.update_y_statistics()

        # denormalize the prediction values
        return y * self.y_standard_dev + self.y_mean
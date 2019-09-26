#!/usr/bin/env python
__author__ = 'solivr'
__license__ = "GPL"

import os
import json
from .alphabet_helpers import load_lookup_from_json, map_lookup
from glob import glob
import string
import csv
from functools import reduce
import pandas as pd
from typing import List


class CONST:
    DIMENSION_REDUCTION_W_POOLING = 2*2  # 2x2 pooling in dimension W on layer 1 and 2


class Alphabet:
    """
    Object for alphabet / symbols units.

    :ivar _blank_symbol: Blank symbol used for CTC
    :vartype _blank_symbol: str
    :ivar _alphabet_units: list of elements composing the alphabet. The units may be a single character or multiple characters.
    :vartype _alphabet_units: List[str]
    :ivar _codes: Each alphabet unit has a unique corresponding code.
    :vartype _codes: List[int]
    :ivar _nclasses: number of alphabet units.
    :vartype _nclasses: int
    """
    def __init__(self, lookup_alphabet_file: str=None, blank_symbol: str='$'):

        self._blank_symbol = blank_symbol

        if lookup_alphabet_file:
            lookup_alphabet = load_lookup_from_json(lookup_alphabet_file)
            # Blank symbol must have the largest value
            if self._blank_symbol in lookup_alphabet.keys():

                # TODO : check if blank symbol is the last one
                assert lookup_alphabet[self._blank_symbol] == max(lookup_alphabet.values()), \
                    "Blank symbol should have the largest code integer"
                lookup_alphabet[self._blank_symbol] = max(lookup_alphabet.values()) + 1
            else:
                lookup_alphabet.update({self._blank_symbol: max(lookup_alphabet.values()) + 1})

            self._alphabet_units = list(lookup_alphabet.keys())
            self._codes = list(lookup_alphabet.values())
            self._nclasses = len(self.codes) + 1  # n_classes should be + 1 of labels codes

            if 0 in self._codes:
                raise ValueError('0 code is in the lookup table, you should''nt use it.')

            self.lookup_int2str = dict(zip(self.codes, self.alphabet_units))

    def check_input_file_alphabet(self, csv_filenames: List[str],
                                  discarded_chars: str=';|{}'.format(string.whitespace[1:]),
                                  csv_delimiter: str=";") -> None:
        """
        Checks if labels of input files contains only characters that are in the Alphabet.

        :param csv_filenames: list of the csv filename
        :param discarded_chars: discarded characters
        :param csv_delimiter: character delimiting field in the csv file
        :return:
        """
        assert isinstance(csv_filenames, list), 'csv_filenames argument is not a list'

        alphabet_set = set(self.alphabet_units)

        for filename in csv_filenames:
            input_chars_set = set()

            with open(filename, 'r', encoding='utf8') as f:
                csvreader = csv.reader(f, delimiter=csv_delimiter, escapechar='\\', quoting=0)
                for line in csvreader:
                    input_chars_set.update(line[1])

            # Discard all whitespaces except space ' '
            for whitespace in discarded_chars:
                input_chars_set.discard(whitespace)

            extra_chars = input_chars_set - alphabet_set
            assert len(extra_chars) == 0, 'There are {} unknown chars in {} : {}'.format(len(extra_chars),
                                                                                         filename, extra_chars)

    @classmethod
    def create_lookup_from_labels(cls, csv_files: List[str], export_lookup_filename: str,
                                  original_lookup_filename: str=None):
        """
        Create a lookup dictionary for csv files containing labels. Exports a json file with the Alphabet.

        :param csv_files: list of files to get the labels from (should be of format path;label)
        :param export_lookup_filename: filename to export alphabet lookup dictionary
        :param original_lookup_filename: original lookup filename to update (optional)
        :return:
        """
        if original_lookup_filename:
            with open(original_lookup_filename, 'r') as f:
                lookup = json.load(f)
            set_chars = set(list(lookup.keys()))
        else:
            set_chars = set(list(string.ascii_letters) + list(string.digits))
            lookup = dict()

        for filename in csv_files:
            data = pd.read_csv(filename, sep=';', encoding='utf8', error_bad_lines=False, header=None,
                               names=['path', 'transcription'], escapechar='\\')
            for index, row in data.iterrows():
                set_chars.update(row.transcription.split('|'))

        # Update (key, values) of lookup table
        for el in set_chars:
            if el not in lookup.keys():
                lookup[el] = max(lookup.values()) + 1 if lookup.values() else 0

        lookup = map_lookup(lookup)

        # Save new lookup
        with open(export_lookup_filename, 'w', encoding='utf8') as f:
            json.dump(lookup, f)

    @property
    def n_classes(self):
        return self._nclasses

    @property
    def blank_symbol(self):
        return self._blank_symbol

    @property
    def codes(self):
        return self._codes

    @property
    def alphabet_units(self):
        return self._alphabet_units


class Params:
    """
    Object for general parameters

    :ivar input_shape: input shape of the image to batch (this is the shape after data augmentation).
        The original will either be resized or pad depending on its original size
    :vartype input_shape: Tuple[int, int]
    :ivar input_channels: number of color channels for input image
    :vartype input_channels: int
    :ivar csv_delimiter: character to delimit csv input files
    :vartype csv_delimiter: str
    :ivar string_split_delimiter: character that delimits each alphabet unit in the labels
    :vartype string_split_delimiter: str
    :ivar lookup_alphabet_file: json file that contains the mapping alphabet units <-> codes
    :vartype lookup_alphabet_file: str
    :ivar csv_files_train: csv filename which contains the (path;label) of each training sample
    :vartype csv_files_train: str
    :ivar csv_files_eval: csv filename which contains the (path;label) of each eval sample
    :vartype csv_files_eval: str
    :ivar output_model_dir: output directory where the model will be saved and exported
    :vartype output_model_dir: str
    :ivar keep_prob_dropout: keep probability
    :vartype keep_prob_dropout: float
    :ivar num_beam_paths: number of paths (transcriptions) to return for ctc beam search (only used when predicting)
    :vartype num_beam_paths: int
    :ivar data_augmentation: if True augments data on the fly
    :vartype data_augmentation: bool
    :ivar data_augmentation_max_rotation: max permitted roation to apply to image during training (radians)
    :vartype data_augmentation_max_rotation: float
    :ivar input_data_n_parallel_calls: number of parallel calls to make when using Dataset.map()
    :vartype input_data_n_parallel_calls: int
    :ivar n_epochs: numbers of epochs to run the training (default: 50)
    :vartype n_epochs: int
    :ivar train_batch_size: batch size during training (default: 64)
    :vartype train_batch_size: int
    :ivar eval_batch_size: batch size during evaluation (default: 128)
    :vartype eval_batch_size: int
    :ivar learning_rate: initial learning rate (default: 1e-4)
    :vartype learning_rate: float
    :ivar evaluate_every_epoch: evaluate every 'evaluate_every_epoch' epoch (default: 5)
    :vartype evaluate_every_epoch: int
    :ivar save_interval: save the model every 'save_interval' epoch (default: 10)
    :vartype save_interval: int
    :ivar optimizer: which optimizer to use ('adam', 'rms', 'ada') (default: 'adam)
    :vartype optimizer: str
    :ivar restore_model: boolean to continue training with saved weights
    :vartype restore_model: bool
    """
    def __init__(self, **kwargs):
        # model params
        self.input_shape = kwargs.get('input_shape', (96, 1400))
        self.input_channels = kwargs.get('input_channels', 1)
        self.cnn_features_list = kwargs.get('cnn_features_list', [16, 32, 64, 96, 128])
        self.cnn_kernel_size = kwargs.get('cnn_kernel_size', [3, 3, 3, 3, 3])
        self.cnn_stride_size = kwargs.get('cnn_stride_size', [(1, 1), (1, 1), (1, 1), (1, 1), (1, 1)])
        self.cnn_pool_size = kwargs.get('cnn_pool_size', [(2, 2), (2, 2), (2, 2), (2, 2), (1, 1)])
        self.cnn_pool_strides = kwargs.get('cnn_pool_strides', [(2, 2), (2, 2), (2, 2), (2, 2), (1, 1)])
        self.cnn_batch_norm = kwargs.get('cnn_batch_norm', [False, False, False, False, False])
        self.rnn_units = kwargs.get('rnn_units', [256, 256])
        self._keep_prob_dropout = kwargs.get('keep_prob', 0.5)
        self.num_beam_paths = kwargs.get('num_beam_paths', 3)
        # csv params
        self.csv_delimiter = kwargs.get('csv_delimiter', ';')
        self.string_split_delimiter = kwargs.get('string_split_delimiter', '|')
        self.csv_files_train = kwargs.get('csv_files_train')
        self.csv_files_eval = kwargs.get('csv_files_eval')
        # alphabet params
        self.blank_symbol = kwargs.get('blank_symbol', '$')
        self.max_chars_per_string = kwargs.get('max_chars_per_string', 75)
        self.lookup_alphabet_file = kwargs.get('lookup_alphabet_file')
        # data augmentation params
        self.data_augmentation = kwargs.get('data_augmentation', True),
        self.data_augmentation_max_rotation = kwargs.get('data_augmentation_max_rotation', 0.005)
        self.data_augmentation_max_slant = kwargs.get('data_augmentation_max_slant', 0.7)
        # training params
        self.n_epochs = kwargs.get('n_epochs', 50)
        self.train_batch_size = kwargs.get('train_batch_size', 64)
        self.eval_batch_size = kwargs.get('eval_batch_size', 128)
        self.learning_rate = kwargs.get('learning_rate', 1e-4)
        self.optimizer = kwargs.get('optimizer', 'adam')
        self.output_model_dir = kwargs.get('output_model_dir', '')
        self.evaluate_every_epoch = kwargs.get('evaluate_every_epoch', 5)
        self.save_interval = kwargs.get('save_interval', 20)
        self.restore_model = kwargs.get('restore_model', False)

        self._assign_alphabet()

        # TODO compute n_pool correctly, this is missing cnn_pool_stride
        cnn_params = zip(self.cnn_pool_size, self.cnn_stride_size)
        self.n_pool = reduce(lambda i, j: i*j, map(lambda k: k[0][1] * k[1][1], cnn_params))

        # TODO add additional checks for the architecture
        assert len(self.cnn_features_list) == len(self.cnn_kernel_size) == len(self.cnn_stride_size) \
               == len(self.cnn_pool_size) == len(self.cnn_pool_strides) == len(self.cnn_batch_norm), \
            "Length of parameters of model are not the same, check that all the layers parameters have the same length."

        max_input_width = (self.max_chars_per_string + 1) * self.n_pool
        assert max_input_width <= self.input_shape[1], "Maximum length of labels is {}, input width should be greater or " \
                                                       "equal to {} but is {}".format(self.max_chars_per_string,
                                                                                      max_input_width,
                                                                                      self.input_shape[1])

        assert self.optimizer in ['adam', 'rms', 'ada'], 'Unknown optimizer {}'.format(self.optimizer)

        if os.path.isdir(self.output_model_dir):
            print('WARNING : The output directory {} already exists.'.format(self.output_model_dir))

    def show_experiment_params(self) -> dict:
        """
        Returns a dictionary with the variables of the class.
        :return:
        """
        return vars(self)

    def _assign_alphabet(self):
        self.alphabet = Alphabet(lookup_alphabet_file=self.lookup_alphabet_file, blank_symbol=self.blank_symbol)

    @property
    def keep_prob_dropout(self):
        return self._keep_prob_dropout

    @keep_prob_dropout.setter
    def keep_prob_dropout(self, value):
        assert (0.0 < value <= 1.0), 'Must be 0.0 < value <= 1.0'
        self._keep_prob_dropout = value

    def to_dict(self) -> dict:
        new_dict = self.__dict__.copy()
        del new_dict['alphabet']
        del new_dict['n_pool']
        return new_dict

    @classmethod
    def from_json_file(cls, json_file: str):
        with open(json_file, 'r') as file:
            config = json.load(file)

        return cls(**config)


def import_params_from_json(model_directory: str=None, json_filename: str=None) -> dict:
    """
    Read the exported json file with parameters of the experiment.

    :param model_directory: Direcoty where the odel was exported
    :param json_filename: filename of the file
    :return: a dictionary containing the parameters of the experiment
    """

    assert not all(p is None for p in [model_directory, json_filename]), 'One argument at least should not be None'

    if model_directory:
        # Import parameters from the json file
        try:
            json_filename = glob(os.path.join(model_directory, 'model_params*.json'))[-1]
        except IndexError:
            print('No json found in dir {}'.format(model_directory))
            raise FileNotFoundError
    else:
        if not os.path.isfile(json_filename):
            print('No json found with filename {}'.format(json_filename))
            raise FileNotFoundError

    with open(json_filename, 'r') as data_json:
        params_json = json.load(data_json)

    # Remove 'private' keys
    keys = list(params_json.keys())
    for key in keys:
        if key[0] == '_':
            params_json.pop(key)

    return params_json

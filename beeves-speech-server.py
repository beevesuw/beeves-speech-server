#! /usr/bin/env python3

# Parts copied from Picovoice demo 
#
# Copyright 2018 Picovoice Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
import os
import platform
import struct
import sys
import json
import glob
from datetime import datetime
from threading import Thread
import time
import numpy as np
import pyaudio
import soundfile

sys.path.append(os.path.join(os.path.dirname(__file__), 'Porcupine/binding/python'))

from porcupine import Porcupine
import logging

import pathlib

logging.basicConfig(level=logging.DEBUG)

def encodeMessage(messageContent):
    encodedContent = json.dumps(messageContent).encode('utf-8')
    encodedLength = struct.pack('@I', len(encodedContent))
    return {'length': encodedLength, 'content': encodedContent}

# Send an encoded message to stdout
def sendMessage(encodedMessage):
    sys.stdout.buffer.write(encodedMessage['length'])
    sys.stdout.buffer.write(encodedMessage['content'])
    sys.stdout.buffer.flush()


def get_keywords_directory(base_dir = './Porcupine/resources/keyword_files'):
    system = platform.system()


    dir_mappings = {
        'Darwin' : 'mac',
        'Linux' :  'linux',
        'Windows' : 'windows'
    }

    return os.path.join(base_dir, dir_mappings[system])

class HotwordServer(Thread):
    """
    Demo class for wake word detection (aka Porcupine) library. It creates an input audio stream from a microphone,
    monitors it, and upon detecting the specified wake word(s) prints the detection time and index of wake word on
    console. It optionally saves the recorded audio into a file for further review.
    """

    def __init__(
            self,
            library_path,
            model_file_path,
            keyword_dir,
            sensitivity=0.5,
            input_device_index=None):

        """
        Constructor.

        :param library_path: Absolute path to Porcupine's dynamic library.
        :param model_file_path: Absolute path to the model parameter file.
        :param keyword_file_paths: List of absolute paths to keyword files.
        :param sensitivities: Sensitivity parameter for each wake word. For more information refer to
        'include/pv_porcupine.h'. It uses the
        same sensitivity value for all keywords.
        :param input_device_index: Optional argument. If provided, audio is recorded from this input device. Otherwise,
        the default audio input device is used.
        :param output_path: If provided recorded audio will be stored in this location at the end of the run.
        """

        super(HotwordServer, self).__init__()

        self._library_path = library_path
        self._model_file_path = model_file_path
        self.keyword_dir = keyword_dir
        self._input_device_index = input_device_index

        logging.info(f'{self._library_path}, {self._model_file_path}, {self.keyword_dir}, {self._input_device_index}')

    @property
    def keywords(self):
        paths = set(glob.glob(os.path.join(self.keyword_dir, '*.ppn'), recursive=True)) - set(glob.glob(os.path.join(self.keyword_dir, '*_compressed.ppn'), recursive=True) )

        result = dict(zip([os.path.basename(x).replace('.ppn', '').split('_')[0] for x in paths], paths))
        logging.info('Keys: %r' % (repr([x for x in result.keys()])))
        return result


    def run(self, keyword_name='bumblebee', sensitivity=0.5):
        """
         Creates an input audio stream, initializes wake word detection (Porcupine) object, and monitors the audio
         stream for occurrences of the wake word(s). It prints the time of detection for each occurrence and index of
         wake word.
         """

        print('- %s (sensitivity: %f)' % (keyword_name, sensitivity))

        porcupine = None
        pa = None
        audio_stream = None
        try:
            porcupine = Porcupine(
                library_path=self._library_path,
                model_file_path=self._model_file_path,
                keyword_file_path = self.keywords[keyword_name],
                sensitivity=sensitivity)

            pa = pyaudio.PyAudio()
            audio_stream = pa.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=porcupine.frame_length,
                input_device_index=self._input_device_index)

            while True:
                pcm = audio_stream.read(porcupine.frame_length)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

                result = porcupine.process(pcm)
                if result:
                    encoded_message = encodeMessage({'hotword' : keyword_name, 'message' : 'detected', 'timestamp' : str(datetime.now().isoformat())})
                    sendMessage(encoded_message)
                    print('[%s] detected keyword' % str(datetime.now()))


        except KeyboardInterrupt:
            print('stopping ...')
        finally:
            if porcupine is not None:
                porcupine.delete()

            if audio_stream is not None:
                audio_stream.close()

            if pa is not None:
                pa.terminate()


    _AUDIO_DEVICE_INFO_KEYS = ['index', 'name', 'defaultSampleRate', 'maxInputChannels']

    @classmethod
    def show_audio_devices_info(cls):
        """ Provides information regarding different audio devices available. """

        pa = pyaudio.PyAudio()

        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            print(', '.join("'%s': '%s'" % (k, str(info[k])) for k in cls._AUDIO_DEVICE_INFO_KEYS))

        pa.terminate()


def _default_library_path():
    system = platform.system()
    machine = platform.machine()

    if system == 'Darwin':
        return os.path.join(os.path.dirname(__file__), 'Porcupine/lib/mac/%s/libpv_porcupine.dylib' % machine)
    elif system == 'Linux':
        if machine == 'x86_64' or machine == 'i386':
            return os.path.join(os.path.dirname(__file__), 'Porcupine/lib/linux/%s/libpv_porcupine.so' % machine)
        else:
            raise Exception('cannot autodetect the binary type. Please enter the path to the shared object using --library_path command line argument.')
    elif system == 'Windows':
        if platform.architecture()[0] == '32bit':
            return os.path.join(os.path.dirname(__file__), 'Porcupine\\lib\\windows\\i686\\libpv_porcupine.dll')
        else:
            return os.path.join(os.path.dirname(__file__), 'Porcupine\\lib\\windows\\amd64\\libpv_porcupine.dll')
    raise NotImplementedError('Porcupine is not supported on %s/%s yet!' % (system, machine))




if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--keyword_dir', help='directory in which to find keyword files', type=str)

    parser.add_argument(
        '--library_path',
        help="absolute path to Porcupine's dynamic library",
        type=str)

    parser.add_argument(
        '--model_file_path',
        help='absolute path to model parameter file',
        type=str,
        default=os.path.join(os.path.dirname(__file__), 'Porcupine/lib/common/porcupine_params.pv'))

    parser.add_argument('--sensitivity', help='detection sensitivity [0, 1]', default=0.5)
    parser.add_argument('--input_audio_device_index', help='index of input audio device', type=int, default=None)

    parser.add_argument('--show_audio_devices_info', action='store_true')

    args = parser.parse_args()
    args.keyword_dir = './Porcupine/resources/keyword_files/linux'

    if args.show_audio_devices_info:
        HotwordServer.show_audio_devices_info()
    else:
        if not args.keyword_dir:
            raise ValueError('keyword file dir is missing')



        HotwordServer(
            library_path=args.library_path if args.library_path is not None else _default_library_path(),
            model_file_path=args.model_file_path,
            keyword_dir=args.keyword_dir,
            sensitivity=args.sensitivity,
            input_device_index=args.input_audio_device_index).run()

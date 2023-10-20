import pydub

from discord.sinks.core import Filters, Sink, default_filters
from queue import Queue
import sys


class StreamSink(Sink):
    def __init__(self, *, filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)
        self.vc = None
        self.audio_data = {}

        # user id for parsing their specific audio data
        self.user_id = None
        self.buffer = StreamBuffer()

    def write(self, data, user):

        # if the data comes from the inviting user, we append it to buffer
        if user == self.user_id:
            self.buffer.write(data=data, user=user)

    def cleanup(self):
        self.finished = True

    def get_all_audio(self):
        # not applicable for streaming but may cause errors if not overloaded
        pass

    def get_user_audio(self, user):
        # not applicable for streaming but will def cause errors if not overloaded called
        pass

    def set_user(self, user_id: int):
        self.user_id = user_id
        print(f"Set user ID: {user_id}")


class StreamBuffer:
    def __init__(self) -> None:
        # holds byte-form audio data as it builds
        self.byte_buffer = bytearray()  # bytes
        self.segment_buffer = Queue()  # pydub.AudioSegments

        # audio data specifications
        self.sample_width = 2
        self.channels = 2
        self.sample_rate = 48000
        self.bytes_ps = 192000  # bytes added to buffer per second
        self.block_len = 1  # how long you want each audio block to be in seconds
        # min len to pull bytes from buffer
        self.buff_lim = self.bytes_ps * self.block_len

        # temp var for outputting audio
        self.ct = 1

    def write(self, data, user):
        self.byte_buffer += data  # data is a bytearray object
        audio_segment = None
        while len(self.byte_buffer) >= self.buff_lim:
            byte_slice = self.byte_buffer[:self.buff_lim]
            self.byte_buffer = self.byte_buffer[self.buff_lim:]

            audio_segment = pydub.AudioSegment(
                data=byte_slice,
                sample_width=self.sample_width,
                frame_rate=self.sample_rate,
                channels=self.channels
            )

            self.segment_buffer.put(audio_segment)
            self.ct += 1

        # Если после цикла данных все равно не хватает, заполняем тишиной
        if len(self.byte_buffer) < self.buff_lim:
            silence_data = bytearray(b'\x00' * (self.buff_lim - len(self.byte_buffer)))
            self.byte_buffer += silence_data

        # temporary for validating process
        if not audio_segment is None:
            audio_segment.export(f"output{self.ct}.wav", format="wav")
            self.ct += 1

from typing import Optional

from binaryninja import Architecture, Endianness, BinaryView, Settings, SegmentFlag
from binaryninja.log import log_info, log_error, log_to_stdout, LogLevel

from . import ihex

import os.path
import importlib


class MPC5674FihexView(BinaryView):
    blocks: dict[bytes]
    entrypoints: list[int]

    name = 'MPC5674FihexView'
    long_name = 'MPC5674F PowerPC IHEX Firmware'

    def __init__(self, data: BinaryView):
        blocks, entrypoints = ihex.parse(data.read(0, data.length).decode('utf-8'))

        log_info('Loading PPC IHEX from %s' % data.file.filename)

        # merge the blocks into a single memory space, Because the MPC5674F 
        # starts at address 0 the binary data will cover the range 0x0000_0000 
        # to 0x0040_0000
        parsed = bytearray(0x00400000)
        for addr, block in blocks.items():
            parsed[addr:addr+len(block)] = block

        # We need to make a new binary view parent with the raw data
        parent = BinaryView.new(data=parsed)
        BinaryView.__init__(self, file_metadata=data.file, parent_view=parent)

        self.platform = Architecture['ppc'].standalone_platform

        # Add the default segment
        self.add_auto_segment(0, len(parsed), 0, len(parsed),
                              SegmentFlag.SegmentReadable | SegmentFlag.SegmentExecutable)

        # Now add the SVD information
        try:
            svd_plugin = importlib.import_module('binaryninja-svd')
        except ModuleNotFoundError:
            try:
                svd_plugin = importlib.import_module('ehntoo_binaryninjasvd')
            except ModuleNotFoundError:
                log_error('Unable to load memory map for target processor, please install the binaryninja-svd plugin')
                svd_plugin = None

        if svd_plugin:
            path = os.path.dirname(os.path.abspath(__file__))
            svd_plugin.load_svd(self, os.path.join(path, 'svd/MPC5674F.xml'))

        # Add the entry points read from the ihex file
        for addr in entrypoints:
            self.add_entry_point(addr)

    def perform_get_default_endianness(self):
        return Endianness.BigEndian

    def perform_get_address_size(self):
        return 4

    @classmethod
    def get_load_settings_for_data(cls, _data: BinaryView) -> Optional[Settings]:
        s = Settings()
        return s

    @classmethod
    def is_valid_for_data(cls, data: BinaryView) -> bool:
        return data.file.filename.endswith('.ihex') or \
                data.file.filename.endswith('.hex') or \
                data.file.filename.endswith('.xcal')


MPC5674FihexView.register()

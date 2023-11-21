import io
import enum
import struct


class CODE(enum.IntEnum):
    DATA = 0
    EOF = 1
    EXT_SEG_ADDR = 2
    START_SEG_ADDR = 3
    EXT_LINEAR_ADDR = 4
    START_LINEAR_ADDR = 5


def checksum(data, init=0):
    """
    Performs a simple 1-byte checksum as used by the ihex file format
    """
    val = init
    for i in range(len(data)):
        val = (val + data[i]) & 0xFF
    return val


def parse_ihex(filename):
    """
    Utility wrapper around the parse function
    """
    with open(filename, 'r') as f:
        blocks, _ = parse(f.read())
        return blocks


def parse(data):
    """
    Parses ihex files and ignores any invalid data
    """
    blocks = {}
    entrypoints = []
    cur_block = None
    cur_offset = None
    offset = 0

    # readlines is really useful for this and ihex files only use ascii 
    # characters so treat the incoming bytes as string data
    with io.StringIO(data) as f:
        lines = f.readlines()

    for line in lines:
        # Check
        if line[0] != ':':
            continue

        # convert the line to bytes (drop the ':' and newline)
        line_data = bytes.fromhex(line.strip(':\r\n'))

        # Validate the checksum
        assert checksum(line_data) == 0

        size, addr, code = struct.unpack_from('>BHB', line_data)

        # 4 bytes of header + 1 byte of checksum
        assert len(line_data) == size + 5

        # Determine if the data should be treated as bytes or an integer
        if code == CODE.DATA:
            if cur_block is not None and \
                    cur_offset + len(cur_block) != offset + addr:
                blocks[cur_offset] = cur_block
                cur_block = bytearray()
                cur_offset = offset + addr

            elif cur_block is None:
                cur_block = bytearray()
                cur_offset = offset + addr

            cur_block += line_data[4:-1]

        elif code == CODE.EOF:
            break

        elif code == CODE.EXT_SEG_ADDR:
            assert size == 2
            base = struct.unpack_from('>H', line_data, 4)[0]
            offset = base * 16

        elif code == CODE.START_SEG_ADDR:
            cs, ip = struct.unpack_from('>HH', line_data, 4)[0]
            offset = (cs << 4) + ip
            entrypoints.append(offset)

        elif code == CODE.EXT_LINEAR_ADDR:
            assert size == 2
            base = struct.unpack_from('>H', line_data, 4)[0]
            offset = base << 16

        elif code == CODE.START_LINEAR_ADDR:
            offset = struct.unpack_from('>I', line_data, 4)[0]
            entrypoints.append(offset)

    # Save the last block
    if cur_block is not None:
        blocks[cur_offset] = cur_block

    return (blocks, entrypoints)

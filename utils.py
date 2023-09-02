from __future__ import print_function

from os.path import exists
import sys, os, errno, tempfile
import common, blockimgdiff, sparse_img
from threading import Thread
import zipfile
# -----
# ====================================================
#          FUNCTION: sdat2img img2sdat
#       AUTHORS: xpirt - luxi78 - howellzhu
#          DATE: 2018-10-27 10:33:21 CEST | 2018-05-25 12:19:12 CEST
# ====================================================
# -----
# ----VALUES


# ----DEFS
def sdat2img(TRANSFER_LIST_FILE, NEW_DATA_FILE, OUTPUT_IMAGE_FILE):
    __version__ = '1.2'

    print('sdat2img binary - version: {}\n'.format(__version__))

    def rangeset(src):
        src_set = src.split(',')
        num_set = [int(item) for item in src_set]
        if len(num_set) != num_set[0] + 1:
            print('Error on parsing following data to rangeset:\n{}'.format(src))
            return

        return tuple([(num_set[i], num_set[i + 1]) for i in range(1, len(num_set), 2)])

    def parse_transfer_list_file(path):
        with open(TRANSFER_LIST_FILE, 'r') as trans_list:
            # First line in transfer list is the version number
            # Second line in transfer list is the total number of blocks we expect to write
            new_blocks = int(trans_list.readline())
            if version := int(trans_list.readline()) >= 2:
                # Third line is how many stash entries are needed simultaneously
                trans_list.readline()
                # Fourth line is the maximum number of blocks that will be stashed simultaneously
                trans_list.readline()
            # Subsequent lines are all individual transfer commands
            commands = []
            for line in trans_list:
                line = line.split(' ')
                cmd = line[0]
                if cmd in ['erase', 'new', 'zero']:
                    commands.append([cmd, rangeset(line[1])])
                else:
                    # Skip lines starting with numbers, they are not commands anyway
                    if not cmd[0].isdigit():
                        print('Command "{}" is not valid.'.format(cmd))
                        return
        return version, new_blocks, commands

    version, new_blocks, commands = parse_transfer_list_file(TRANSFER_LIST_FILE)

    show = "Android {} detected!\n"
    if version == 1:
        print(show.format("Lollipop 5.0"))
    elif version == 2:
        print(show.format("Lollipop 5.1"))
    elif version == 3:
        print(show.format("Marshmallow 6.x"))
    elif version == 4:
        print(show.format("Nougat 7.x / Oreo 8.x / Pie 9.x"))
    else:
        print(f'Unknown Android version:{version}!\n')

    # Don't clobber existing files to avoid accidental data loss
    try:
        output_img = open(OUTPUT_IMAGE_FILE, 'wb')
    except IOError as e:
        if e.errno == errno.EEXIST:
            print('Error: the output file "{}" already exists'.format(e.filename))
            print('Remove it, rename it, or choose a different file name.')
            return e.errno
        else:
            raise

    new_data_file = open(NEW_DATA_FILE, 'rb')
    all_block_sets = [i for command in commands for i in command[1]]
    max_file_size = max(pair[1] for pair in all_block_sets) * (BLOCK_SIZE := 4096)

    for command in commands:
        if command[0] == 'new':
            for block in command[1]:
                begin = block[0]
                end = block[1]
                block_count = end - begin
                print('Copying {} blocks into position {}...'.format(block_count, begin))

                # Position output file
                output_img.seek(begin * BLOCK_SIZE)

                # Copy one block at a time
                while block_count > 0:
                    output_img.write(new_data_file.read(BLOCK_SIZE))
                    block_count -= 1
        else:
            print('Skipping command {}...'.format(command[0]))

    # Make file larger if necessary
    if output_img.tell() < max_file_size:
        output_img.truncate(max_file_size)

    output_img.close()
    new_data_file.close()
    print('Done! Output image: {}'.format(os.path.realpath(output_img.name)))


def qc(file_) -> None:
    if not exists(file_):
        return
    with open(file_, 'r+', encoding='utf-8', newline='\n') as f:
        data = f.readlines()
        new_data = sorted(set(data), key=data.index)
        if len(new_data) == len(data):
            print("No need to handle")
            return
        f.seek(0)
        f.truncate()
        f.writelines(new_data)
    del data, new_data


def cz(func, *args):
    Thread(target=func, args=args, daemon=True).start()


def img2sdat(input_image, out_dir='.', version=None, prefix='system'):
    print('img2sdat binary - version: %s\n' % 1.7)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
        '''            
        1. Android Lollipop 5.0
        2. Android Lollipop 5.1
        3. Android Marshmallow 6.0
        4. Android Nougat 7.0/7.1/8.0/8.1
        '''

    blockimgdiff.BlockImageDiff(sparse_img.SparseImage(input_image, tempfile.mkstemp()[1], '0'), None, version).Compute(
        out_dir + '/' + prefix)
    print('Done! Output files: %s' % os.path.dirname(prefix))


def findfile(file, dir_) -> str:
    for root, dirs, files in os.walk(dir_, topdown=True):
        if file in files:
            if os.name == 'nt':
                return (root + os.sep + file).replace("\\", '/')
            else:
                return root + os.sep + file
        else:
            pass


def findfolder(dir__, folder_name):
    for root, dirnames, filenames in os.walk(dir__):
        for dirname in dirnames:
            if dirname == folder_name:
                return os.path.join(root, dirname).replace("\\", '/')
    return None


# ----CLASSES


class vbpatch:
    def __init__(self, file_):
        self.file = file_

    def checkmagic(self):
        if os.access(self.file, os.F_OK):
            magic = b'AVB0'
            with open(self.file, "rb") as f:
                buf = f.read(4)
                return magic == buf
        else:
            print("File dose not exist!")

    def readflag(self):
        if not self.checkmagic():
            return False
        if os.access(self.file, os.F_OK):
            with open(self.file, "rb") as f:
                f.seek(123, 0)
                flag = f.read(1)
                if flag == b'\x00':
                    return 0  # Verify boot and dm-verity is on
                elif flag == b'\x01':
                    return 1  # Verify boot but dm-verity is off
                elif flag == b'\x02':
                    return 2  # All verity is off
                else:
                    return flag
        else:
            print("File does not exist!")

    def patchvb(self, flag):
        if not self.checkmagic():
            return False
        if os.access(self.file, os.F_OK):
            with open(self.file, 'rb+') as f:
                f.seek(123, 0)
                f.write(flag)
            print("Done!")
        else:
            print("File not Found")

    def restore(self):
        self.patchvb(b'\x00')

    def disdm(self):
        self.patchvb(b'\x01')

    def disavb(self):
        self.patchvb(b'\x02')

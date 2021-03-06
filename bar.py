import argparse
import blocks
import subprocess
import sys
import time
from yaml import load


class Bar:
    def __init__(self, update_interval=1, offset={'x':0, 'y':0},
                 dimensions={'w':'all', 'h':20}, fonts=None,
                 xresources=True, colors=None, underline_thickness=1, args=None):
        self.args = args
        self.update_interval = update_interval

        if args.geometry:
            # Force geometry
            tmp = args.geometry.split('+')
            offset = tmp[1:]
            dimensions = tmp[0].split('x')
            if offset:
                self.offset = {'x': offset[0], 'y': offset[1]}
            else:
                self.offset = {'x': 0, 'y': 0}
            self.dimensions = {'w': dimensions[0], 'h': dimensions[1]}
        else:
            # Geometry from config
            self.offset = offset
            self.dimensions = dimensions

        self.fonts = fonts
        self.underline_thickness = underline_thickness
        #TODO:
        self.colors = self._load_xresources() if xresources else colors

        self.command = 'lemonbar -p'.split()
        for font in self.fonts:
            self.command += ['-f', font['str'],
                             '-o', str(font['offset'])]
        self.command += ['-g',
                         '{w}x{h}+{x}+{y}'.format(**self.dimensions,
                                                  **self.offset)]
        self.command += ['-u', str(self.underline_thickness)]
        self.command += ['-F', self.colors['foreground'],
                         '-B', self.colors['background']]

        self.callback_blocks = []
        self.blocks = []

        self.__prev_time = 0
        self.refresh = False

    def _load_xresources(self):
        # TODO
        pass

    def add_block(self, block):
        # if hasattr(block, 'foreground') and not block.foreground:
        #     block.foreground = self.__foreground
        # if hasattr(block, 'background') and not block.background:
        #     block.background = self.__background

        # if block.is_callback_block:
        #     self.callback_blocks.append(block)
        # else:
        self.blocks.append(block)

    def add_blocks(self, blocks):
        for block in blocks:
            self.add_block(block)

    def add_blocks_from_config(self, config):
        align = ['left', 'center', 'right']

        for a in align:
            if config.get(a):
                self.add_block(blocks.Align(a[0]))
                for block, bc in config[a].items():
                    try:
                        block = getattr(blocks, block)
                        self.add_block(block(**bc))
                    except AttributeError:
                        print('Block {} not found.'.format(block))
                        pass
                    except TypeError as e:
                        print('Block {} configured incorrectly:\n'\
                              .format(block) + str(e))
                        pass

    def feed(self):
        return ''.join([b() for b in self.blocks]) + '\n'

    def start(self, feed_only=False):
        for b in self.blocks:
            if b.is_callback_block:
                b.set_callbacks()

        if not feed_only:
            self.lemonbar = subprocess.Popen(self.command, stdin=subprocess.PIPE)

        while True:
            if (self.__prev_time + self.update_interval <= time.time()) or self.refresh:
                if feed_only:
                    print(self.feed(), end='')
                    sys.stdout.flush()
                    self.lemonbar = None
                else:
                    self.lemonbar.stdin.write(self.feed().encode())
                    self.lemonbar.stdin.flush()
                self.refresh = False
            time.sleep(0.1)

    def kill(self):
        if self.lemonbar:
            self.lemonbar.kill()


def main():
    from pprint import pprint
    parser = argparse.ArgumentParser(description='Feed script for LemonBar')
    parser.add_argument('-c', '--config', default='config.yaml',
                        help='YAML Config file')
    parser.add_argument('-f', '--feed', action='store_true',
                        help='Only print feed data \
                              (don\'t start lemonbar')
    parser.add_argument('-g', '--geometry', default=None,
                        help='Geometry of lemonbar, example: (w)x(h)+(x)+(y). None for config')
    args = parser.parse_args()

    try:
        config = load(open(args.config))
    except FileNotFoundError:
        print('Config file not found!')
        sys.exit(1)

    bar = Bar(**config.get('lemonbar'), args=args)
    bar.add_blocks_from_config(config.get('blocks'))

    try:
        bar.start(feed_only=args.feed)
    except KeyboardInterrupt:
        print('Closing')
    finally:
        bar.kill()


if __name__ == '__main__':
    main()

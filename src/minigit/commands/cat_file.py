"""minigit cat-file: look inside an object.

This is the best command for exploring how Git stores things. Try:

    minigit cat-file -p HEAD                 # the commit
    minigit cat-file -p <tree sha from it>   # its top-level directory
"""

import sys

from minigit.objects import parse_tree, read_object
from minigit.refs import resolve

NAME = "cat-file"
HELP = "Show the type, size or content of an object"


def configure(parser):
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("-t", dest="show", action="store_const", const="type", help="show type")
    mode.add_argument("-s", dest="show", action="store_const", const="size", help="show size")
    mode.add_argument("-p", dest="show", action="store_const", const="pretty", help="pretty-print")
    parser.add_argument("object", help="a SHA, branch, tag or HEAD")


def run(args, repo):
    obj_type, data = read_object(repo, resolve(repo, args.object))
    if args.show == "type":
        print(obj_type)
    elif args.show == "size":
        print(len(data))
    elif obj_type == "tree":
        for entry in parse_tree(data):
            print(f"{entry.mode.rjust(6, '0')} {entry.type} {entry.sha}\t{entry.name}")
    else:
        # Write raw bytes: blobs can be binary files, not just text.
        sys.stdout.flush()
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    return 0

import math


def chunkify(ls, size):
    return [ls[(n * size):(min(len(ls), (n + 1) * size))] for n in
            range(0, math.ceil(len(ls) / size))]

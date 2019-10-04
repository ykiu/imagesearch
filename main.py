from argparse import ArgumentParser
import json
from statistics import mean
from glob import glob
from typing import Sequence, Any, Iterator, List, Mapping, Tuple

from PIL import Image
from PIL.ImageChops import difference
from PIL.ImageStat import Stat


def meandiff(image1: Any, image2: Any) -> float:
    return float(mean(Stat(difference(image1, image2)).mean))


class ImageGroup:

    def __init__(self, paths: Sequence[str], size: Tuple[int, int]) -> None:
        self.size = size
        self.images = [(path, Image.open(path).resize(size)) for path in paths]

    def __iter__(self) -> Iterator[Any]:
        return iter(self.images)

    def meandiff(self, image: Any) -> List[Tuple[str, float]]:
        return [(path, meandiff(image, im)) for path, im in self]

    def filter_similar(self, image: Any, threshold: float) -> List[str]:
        return [path for path, diff in self.meandiff(image) if diff < threshold]

    def lookup(self, other: 'ImageGroup', threshold: float) -> Mapping[str, List[str]]:
        diffs = {path: other.filter_similar(image, threshold) for path, image in self}
        return diffs


def main(pattern1: str, pattern2: str, outpath: str, width: int, height: int, threshold: int) -> None:
    paths1 = glob(pattern1)
    paths2 = glob(pattern2)
    size = (width, height)
    grp1 = ImageGroup(paths1, size)
    grp2 = ImageGroup(paths2, size)
    similar_images = grp1.lookup(grp2, threshold)
    with open(outpath, 'w', encoding='utf8') as fp:
        json.dump(similar_images, fp)


parser = ArgumentParser(description='Relate similar-looking images')
parser.add_argument('pattern1', type=str)
parser.add_argument('pattern2', type=str)
parser.add_argument('outpath', type=str)
parser.add_argument('--width', type=int)
parser.add_argument('--height', type=int)
parser.add_argument('--threshold', type=int)


if __name__ == '__main__':
    kwargs = vars(parser.parse_args())
    main(**kwargs)

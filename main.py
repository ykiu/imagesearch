from argparse import ArgumentParser
import json
from statistics import mean
from glob import glob
from typing import Sequence, Iterator, List, Mapping, Tuple

from PIL import Image
from PIL.ImageChops import difference
from PIL.ImageFile import ImageFile
from PIL.ImageStat import Stat
from tqdm import tqdm


ANGLES = [90, 180, 270]


def meandiff(image1: ImageFile, image2: ImageFile) -> float:
    return float(mean(Stat(difference(image1, image2)).mean))


def resize_to_fit(image: ImageFile, size: int) -> ImageFile:
    rate = size / max(image.width, image.height)
    new_image = image.resize((int(image.width * rate), int(image.height * rate)))
    return new_image


def rotate_to_multiple_angles(image: ImageFile) -> List[ImageFile]:
    return [image] + [image.rotate(angle, expand=True) for angle in ANGLES]


class ImageGroup:
    def __init__(self, paths: Sequence[str], size: int, verbose: bool, rotate) -> None:
        self.size = size
        self.verbose = verbose
        if self.verbose:
            print("Loading images...")
            it = tqdm(paths)
        else:
            it = paths
        resized_images = [(path, resize_to_fit(Image.open(path), size)) for path in it]
        if rotate:
            rotated_images = [
                (path, rotated_image)
                for path, image in resized_images
                for rotated_image in rotate_to_multiple_angles(image)
            ]
            self.images = rotated_images
        else:
            self.images = resized_images

    def __iter__(self) -> Iterator[ImageFile]:
        return iter(self.images)

    def __len__(self) -> int:
        return len(self.images)

    def meandiff(self, image: ImageFile) -> List[Tuple[str, float]]:
        return [(path, meandiff(image, im)) for path, im in self]

    def filter_similar(self, image: ImageFile, threshold: float) -> List[str]:
        return [path for path, diff in self.meandiff(image) if diff < threshold]

    def lookup(self, other: "ImageGroup", threshold: float) -> Mapping[str, List[str]]:
        if self.verbose:
            print("Comparing images...")
            it = tqdm(self)
        else:
            it = self
        diffs = {path: other.filter_similar(image, threshold) for path, image in it}
        return diffs


def main(
    pattern1: str,
    pattern2: str,
    outpath: str,
    size: int,
    rotate: bool,
    threshold: int,
    verbose: bool,
) -> None:
    paths1 = glob(pattern1)
    paths2 = glob(pattern2)
    grp1 = ImageGroup(paths1, size, verbose, False)
    grp2 = ImageGroup(paths2, size, verbose, rotate)
    similar_images = grp1.lookup(grp2, threshold)
    with open(outpath, "w", encoding="utf8") as fp:
        json.dump(similar_images, fp)


parser = ArgumentParser(
    description="A utility to link thumbnails to the original images (or vice versa)."
)
parser.add_argument(
    "pattern1",
    type=str,
    help=(
        "Filename pattern of the images to analyze. "
        "Wildcard supported. Ex: ~/thumbnails/*.jpg"
    ),
)
parser.add_argument(
    "pattern2",
    type=str,
    help=(
        "Filename pattern of the images that the <pattern1> images should be linked to. "
        "Wildcard supported. Ex: ~/original_images/*.jpg"
    ),
)
parser.add_argument(
    "outpath", type=str, help="The name of the json file to write the result to."
)
parser.add_argument(
    "--size",
    type=int,
    default=100,
    help="The images would be normalized to this size (px). Defaults to 100px.",
)
parser.add_argument(
    "--rotate",
    action="store_true",
    help=(
        "Rotate images by 90°, 180° and 270° before comparison. "
        "Usefull when thumbnails are rotated whereas the original images are not."
    ),
)
parser.add_argument(
    "--threshold",
    type=int,
    default=30,
    help=(
        "The images would be considered 'the same' "
        "if the mean difference of the pixel values is below this threshold. "
        "Defaults to 30."
    ),
)
parser.add_argument("--verbose", action="store_true", help="Display progress bars.")


if __name__ == "__main__":
    kwargs = vars(parser.parse_args())
    main(**kwargs)

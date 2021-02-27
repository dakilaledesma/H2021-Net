import os
import shutil
from glob import glob
from tqdm import tqdm

restructure_path = "restructured/test/images"

test_path = "data/nybg2020/test"

image_filepaths = glob(f"{test_path}/**/*.jpg", recursive=True)
for filepath in tqdm(image_filepaths, desc="Moving images"):
    image_fn = os.path.basename(filepath)

    shutil.move(filepath, f"{restructure_path}/{image_fn}")
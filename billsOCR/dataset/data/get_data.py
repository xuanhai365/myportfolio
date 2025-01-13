import os
import json
import argparse
from PIL import Image
import pandas as pd
import numpy as np
from datasets import load_dataset
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', type=str, help = 'huggingface data name', required=True)
    parser.add_argument('--split', type=str, help = 'split name', default=[], nargs='+', required=True)
    parser.add_argument('--det_dir', type=str, help = 'detection dataset directory', default='./det_dataset')
    parser.add_argument('--recog_dir', type=str, help = 'recognition dataset directory', default='./recog_dataset')
    args = parser.parse_args()

    dataset = load_dataset(args.name)
    for split_name in args.split:
        img_path = os.path.join(Path(args.det_dir), split_name, 'images')
        gt_path = os.path.join(Path(args.det_dir), split_name, 'gts')
        recog_path = os.path.join(Path(args.recog_dir), split_name)
        os.makedirs(img_path, exist_ok=True)
        os.makedirs(gt_path, exist_ok=True)
        os.makedirs(recog_path, exist_ok=True)

        save_id = 0
        labels = []
        for idx in range(len(dataset[split_name])):
            img = dataset[split_name][idx]['image']
            lbl = json.loads(dataset[split_name][idx]['ground_truth'])

            img_name = f'{split_name}_{idx}.jpg'
            lbl_name = f'gt_{split_name}_{idx}.txt'

            img.save(os.path.join(img_path, img_name))
            img = np.array(img)

            with open(os.path.join(gt_path, lbl_name), 'w') as f:
                for line in lbl['valid_line']:
                    for word in line['words']:
                        cor = word['quad']
                        text = word['text']
                        cordinate = [cor['x1'], cor['y1'], cor['x2'], cor['y2'], cor['x3'], cor['y3'], cor['x4'], cor['y4']]
                        cordinate = np.maximum(cordinate, 0)
                        for cor in cordinate:
                            f.write(f'{cor},')
                            f.write(f'{text}\n')

                            crop_cor = [min(cordinate[0], cordinate[6]), min(cordinate[1], cordinate[3]),
                                        max(cordinate[2], cordinate[4]), max(cordinate[5], cordinate[7])]
                            save_img = img[crop_cor[1]:crop_cor[3], crop_cor[0]:crop_cor[2], :]
                            save_img = Image.fromarray(save_img)
                            save_img.save(os.path.join(recog_path, f'{save_id}.jpg'))
                            labels.append([f'{save_id}.jpg', text])
                            save_id += 1
        df = pd.DataFrame(labels, columns = ['filename', 'words'])
        df.to_csv(os.path.join(recog_path, 'labels.csv'), index = False)

if __name__ == '__main__':
    main()
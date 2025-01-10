import shutil
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', type=str, default='all')
    args = parser.parse_args()
    if args.dir == 'all':
        shutil.rmtree('data/det_dataset')
        shutil.rmtree('data/recog_dataset')
    else:
        shutil.rmtree(f'data/{dir}')

if __name__ == '__main__':
    main()
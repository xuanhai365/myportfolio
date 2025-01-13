import argparse
from s3_db import ModelData

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--s3_bucket', type=str, required=True)
    args = parser.parse_args()
    model_data = ModelData(args.s3_bucket)
    model_data.retrieve()
    
if __name__ == '__main__':
    main()
import argparse
from s3_connect import ModelData

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--s3_bucket', type=str, required=True)
    parser.add_argument('--access_key', type=str, required=True)
    parser.add_argument('--secret_key', type=str, required=True)
    args = parser.parse_args()
    model_data = ModelData(args.s3_bucket, args.access_key, args.secret_key)
    model_data.retrieve()
    
if __name__ == '__main__':
    main()
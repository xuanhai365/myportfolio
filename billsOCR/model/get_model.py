from s3_materials import ModelMaterials
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--s3_bucket', type=str, required=True)
    args = argparse.parse_args()

    model_materials = ModelMaterials(args.s3_bucket)
    model_materials.pull_model_repo()

if __name__ == '__main__':
    main()
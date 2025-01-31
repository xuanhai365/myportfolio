from s3_materials import ModelMaterials
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--s3_bucket', type=str, required=True)
    args = parser.parse_args()

    model_materials = ModelMaterials(args.s3_bucket)
    model_materials.push_model_repo()

if __name__ == '__main__':
    main()
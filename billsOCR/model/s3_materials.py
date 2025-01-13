import os
import boto3
import zipfile
import shutil
from dotenv import load_dotenv
import os

load_dotenv('/sources/.env')
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
REGION = os.getenv('REGION')

class ModelMaterials:
    def __init__(self, s3_bucket):
        self.s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION)
        self.s3_bucket = s3_bucket
        self.model_repo = 'FAST.zip'
    def push_model_repo(self):
        shutil.make_archive(self.model_repo.split('.')[0], 'zip', self.model_repo.split('.')[0])
        self.s3.upload_file(self.model_repo, self.s3_bucket, self.model_repo)
        os.remove(self.model_repo)
    def pull_model_repo(self):
        self.s3.download_file(self.s3_bucket, self.model_repo, self.model_repo)
        with zipfile.ZipFile('model_repo.zip', 'r') as zip_ref:
            zip_ref.extractall('model_repo')
        os.remove('model_repo.zip')
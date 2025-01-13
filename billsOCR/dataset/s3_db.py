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

class ModelData:
    def __init__(self, s3_bucket):
        self.s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION)
        self.s3_bucket = s3_bucket
    def update(self):
        data_name = 'dataset.zip'
        try:
            self.s3.download_file(self.s3_bucket, data_name, data_name)
        except:
            print('Detection dataset not found, creating new dataset')
        
        if os.path.exists(data_name):
            with zipfile.ZipFile(data_name, 'r') as zip_ref:
                zip_ref.extractall('data')
            os.remove(data_name)
        shutil.make_archive(data_name.split('.')[0], 'zip', 'data')
        self.s3.upload_file(data_name, self.s3_bucket, data_name)
        os.remove(data_name)
    def retrieve(self):
        data_name = 'dataset.zip'
        self.s3.download_file(self.s3_bucket, data_name, data_name)
        with zipfile.ZipFile(data_name, 'r') as zip_ref:
            zip_ref.extractall('data')
        os.remove(data_name)
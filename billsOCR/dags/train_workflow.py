from airflow import DAG
from airflow.operators.python import BranchPythonOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.providers.ssh.hooks.ssh import SSHHook
#from airflow.utils.db import provide_session
from airflow import settings
from airflow.models import Connection
from datetime import datetime
import boto3
from dotenv import load_dotenv
import os

load_dotenv()
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
MLFLOW_URI = os.getenv('MLFLOW_URI')
REGION = os.getenv('REGION')
S3_BUCKET = os.getenv('S3_BUCKET')

key_dir = 'train_ec2_key.pem'
conn_id = 'ec2_ssh'
    
def create_ec2(**kwargs):
    ec2_client = boto3.client('ec2', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION)
    
    # Create key pair and save it to file
    train_ec2_key = ec2_client.create_key_pair(KeyName='train_key', KeyType='rsa')
    with open(key_dir, 'w') as file:
        file.write(train_ec2_key['KeyMaterial'])
    os.chmod(key_dir, 400)

    # Create new instance
    ec2 = boto3.resource('ec2', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION)
    instances = ec2.create_instances(
        BlockDeviceMappings=[
            {
                'DeviceName':'/dev/xvda',
                'Ebs': {
                    'VolumeSize': 32,
                    'VolumeType': 'gp3',
                    'Throughput': 512
                }
            }
        ],
        ImageId='ami-0bd55ebedabddc3c0',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='train_key')
    instance = instances[0]
    instance.wait_until_running()
    instance.load()
    instance.create_tags(Tags=[{"Key": "Name", "Value": "train_instance"}])
    ti = kwargs['ti']
    ti.xcom_push(key='public_dns', value=instance.public_dns_name)
    
def create_ssh_conn():
    session = settings.Session()
    conn = session.query(Connection).filter(Connection.conn_id == conn_id).first()
    if conn is not None:
        session.delete(conn)
        session.commit()
    conn = Connection(
        conn_id=conn_id,
        conn_type='ssh',
        host='no_host',
        login='ec2-user',
        port=22,
        extra={'key_file':f'{key_dir}'}
    )
    session.add(conn)
    session.commit()

def clean_everything():
    ec2_client = boto3.client('ec2', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY, region_name=REGION)
    key_pairs = ec2_client.describe_key_pairs()
    for key in key_pairs['KeyPairs']:
        if key['KeyName'] == 'train_key':
            ec2_client.delete_key_pair(KeyName='train_key')
            break
    filters = [{  
        'Name': 'tag:Name',
        'Values': ['train_instance']
        }]
    reservations = ec2_client.describe_instances(Filters=filters)
    instance_ids = []
    if len(reservations['Reservations']) > 0:
        for reservation in reservations['Reservations']:
            for instance in reservation['Instances']:
                instance_ids.append(instance['InstanceId'])
        ec2_client.terminate_instances(InstanceIds=instance_ids)
    os.remove(key_dir)

with DAG('train_pipeline',
         start_date=datetime.now(),
         schedule='@daily',
         catchup=False) as dag:
    create_ec2_boto3 = PythonOperator(
        task_id='create_ec2_boto3',
        python_callable=create_ec2
    )
    create_ssh = PythonOperator(
        task_id='create_ssh_conn',
        python_callable=create_ssh_conn
    )
    setup_env = SSHOperator(
        task_id = "setup_env",
        command = f"""sudo yum -y install unzip && \
        sudo yum -y install git-all && \
        sudo yum -y install python-pip && \
        git clone https://github.com/xuanhai365/myportfolio.git && cd ./myportfolio/billsOCR/model && \
        pip install mmcv==2.2.0 -f https://download.openmmlab.com/mmcv/dist/cu121/torch2.3/index.html && \
        pip install -r requirements.txt && \
        sh compile.sh && \
        aws configure set aws_access_key_id {ACCESS_KEY} && \
        aws configure set aws_secret_access_key {SECRET_KEY} && \
        aws configure set region {REGION}""",
        ssh_conn_id=conn_id,
        remote_host="{{ ti.xcom_pull(task_ids='create_ec2_boto3', key='public_dns') }}",
        cmd_timeout=None
    )
    get_train_materials = SSHOperator(
        task_id="get_train_materials",
        command=f"""aws s3 cp s3://{S3_BUCKET} . --recursive && \
        unzip ./dataset.zip && \
        mv -r ./FAST/pretrained ./myportfolio/billsOCR/model/FAST && \
        mv -r ./CRNN/pretrained ./myportfolio/billsOCR/model/EasyOCR && \
        mv -r ./weights ./myportfolio/billsOCR/model""",
        ssh_conn_id=conn_id,
        remote_host="{{ ti.xcom_pull(task_ids='create_ec2_boto3', key='public_dns') }}",
        cmd_timeout=None
    )
    train_model = SSHOperator(
        task_id="train_model",
        command=f"""export MLFLOW_URI={MLFLOW_URI} && \
        export S3_BUCKET={S3_BUCKET} && \
        cd ./myportfolio/billsOCR/model && python fast_train.py FAST/config/fast/ic15/fast_tiny_ic15_736_finetune_ic17mlt.py --worker=0""",
        ssh_conn_id=conn_id,
        remote_host="{{ ti.xcom_pull(task_ids='create_ec2_boto3', key='public_dns') }}",
        cmd_timeout=None
    )
    clean_up = PythonOperator(
        task_id='clean_up',
        python_callable=clean_everything,
        trigger_rule='all_done'
    )
    create_ec2_boto3 >> create_ssh >> setup_env >> get_train_materials >> train_model >> clean_up

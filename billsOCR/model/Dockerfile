FROM python:3.11-slim
WORKDIR /model
COPY ./FAST ./EasyOCR crnn_train.py fast_train.py requirements.txt compile.sh ./
RUN apt update && apt install build-essential -y
RUN pip install -r requirements.txt
RUN pip install mmcv==2.2.0 -f https://download.openmmlab.com/mmcv/dist/cu121/torch2.3/index.html
RUN sh compile.sh
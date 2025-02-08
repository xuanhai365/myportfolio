import os
from mmengine.config import Config
from .FAST import build_model, fuse_module, rep_model_convert, scale_aligned_short
from .EasyOCR import Reader, reformat_input
import torch
from torchvision import transforms
import logging
import sys
import numpy as np
import cv2
from PIL import Image
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
class billsOCR():
    def __init__(self):
        # Load EasyOCR recognitor
        self.reader = Reader(['en'], recog_network='my_model', model_storage_directory='./weights', detector=False)

        # Load FAST detector
        self.fast_cfg = Config.fromfile('./model/FAST/config/fast/ic15/fast_tiny_ic15_736_finetune_ic17mlt.py')
        fast_cp_dir = './weights/checkpoint.pth.tar'
        # Build model
        self.fast_model = build_model(self.fast_cfg.model)
        self.fast_model = self.fast_model.to(device)
        #Load checkpoint
        if fast_cp_dir is not None:
            if os.path.isfile(fast_cp_dir):
                print("Loading model and optimizer from checkpoint '{}'".format(fast_cp_dir))
                logging.info("Loading model and optimizer from checkpoint '{}'".format(fast_cp_dir))
                sys.stdout.flush()
                #checkpoint = torch.load(fast_cp_dir)
                checkpoint = torch.load(fast_cp_dir, map_location=torch.device('cpu'))
                state_dict = checkpoint['state_dict']
                d = dict()
                for key, value in state_dict.items():
                    tmp = key.replace("module.", "")
                    d[tmp] = value
                self.fast_model.load_state_dict(d)
            else:
                print("No checkpoint found at '{}'".format(fast_cp_dir))
                raise
        self.fast_model = rep_model_convert(self.fast_model)
        # fuse conv and bn
        self.fast_model = fuse_module(self.fast_model)

    def FAST_detect(self, data):
        data['imgs'] = data['imgs'].to(device, non_blocking=True)
        data.update(dict(cfg=self.fast_cfg))
        # forward
        self.fast_model.eval()
        with torch.no_grad():
            outputs = self.fast_model(**data)
        return outputs

    def prepare_input(self, img, name_idx=0):
        short_size = self.fast_cfg.data.test.short_size
        if isinstance(img, str):
            filename = img.split('/')[-1][:-4]
            img = cv2.imread(img)
        else:
            filename = 'img'

        img_rgb, img_cv_grey = reformat_input(img)
        img_meta = dict(org_img_size=np.array([img_rgb.shape[:2]]))

        img = scale_aligned_short(img_rgb, short_size)
        img_meta.update(dict(img_size=np.array([img.shape[:2]]), filename=filename))

        img = Image.fromarray(img)
        img = img.convert('RGB')
        img = transforms.ToTensor()(img)
        img = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])(img)
        data = dict(
                imgs=img.unsqueeze(0),
                img_metas=img_meta
            )
        return data, img_rgb, img_cv_grey

    def inference_method(func):
        def wrapper(self, source, output):
            if os.path.isdir(source):
                for idx, file in enumerate(os.listdir(source)):
                    print('Testing %d/%d\r' % (idx, len(os.listdir(source))), flush=True, end='')
                    logging.info('Testing %d/%d\r' % (idx, len(os.listdir(source))))
                    img_path = os.path.join(source, file)
                    func(self, img_path, output)
            elif os.path.isfile(source):
                func(self, source, output)
            else:
                preds = func(self, source, output)
                return preds
        return wrapper

    @inference_method
    def inference(self, source, output):
        img_output = os.path.join(output, 'images')
        lbl_output = os.path.join(output, 'labels')
        os.makedirs(img_output, exist_ok=True)
        os.makedirs(lbl_output, exist_ok=True)
        # Prepare data
        data, img_rgb, img_cv_grey = self.prepare_input(source)
        # FAST detection
        fast_res = self.FAST_detect(data)
        # Result transform
        horizontal_list = []
        free_list = []
        for res in fast_res['results'][0]['bboxes']:
            horizontal_list.append([int(min(res[0], res[6])), int(max(res[2], res[4])), int(min(res[1], res[3])), int(max(res[5], res[7]))])
        # CRNN recognition
        results = self.reader.recognize(img_cv_grey, horizontal_list, free_list)
        idx = 0
        img_name = f"{data['img_metas']['filename']}.jpg"
        lbl_name = f"{data['img_metas']['filename']}.txt"
        while True:
            if img_name in os.listdir(img_output):
                img_name = f"{data['img_metas']['filename']}_{idx}.jpg"
                lbl_name = f"{data['img_metas']['filename']}_{idx}.txt"
                idx+=1
            else:
                break
        
        img_path = os.path.join(img_output, img_name)
        lbl_path = os.path.join(lbl_output, lbl_name)
        cv2.imwrite(img_path, cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
        with open(lbl_path, 'w') as f:
            for text in results:
                formated_text = []
                for cor in text[0]:
                    formated_text.append(str(cor[0]))
                    formated_text.append(str(cor[1]))
                formated_text.append(str(text[1]))
                #formated_text.append(str(text[2]))
                f.write(f"{','.join(formated_text)}\n")
        return results
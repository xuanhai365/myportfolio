import torch
import numpy as np
import random
import argparse
import os
import os.path as osp
import json
from mmengine.config import Config
import logging
import mlflow
from dotenv import load_dotenv
from datetime import datetime

from FAST.train import train, save_checkpoint
from FAST.dataset import build_data_loader
from FAST.models import build_model
from FAST.utils import setup_logger, EMA
from FAST.dataset.dataloader import DataLoaderX

try:
    import apex
except:
    pass
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

load_dotenv()
MLFLOW_URI = os.getenv('MLFLOW_URI')
S3_BUCKET = os.getenv('S3_BUCKET')

experiment_name = 'FAST'

def main(args):
    cfg = Config.fromfile(args.config)
    logging.info(json.dumps(cfg._cfg_dict, indent=4))
    mlflow.log_dict(cfg._cfg_dict, 'config.json')
    config_name = args.config.split('/')[-1]
    mlflow.log_params({'config_name': config_name,
                      'data_repeat': cfg.repeat_times,
                      'train_batch': cfg.data.batch_size,
                      'input_size': cfg.data.train.img_size,
                      'init_lr': cfg.train_cfg.lr,
                      'scheduler': cfg.train_cfg.schedule,
                      'epochs': cfg.train_cfg.epoch,
                      'optimizer': cfg.train_cfg.optimizer})

    cfg_name, _ = osp.splitext(osp.basename(args.config))
    checkpoint_path = osp.join('checkpoints', cfg_name)
    if not osp.isdir(checkpoint_path):
        os.makedirs(checkpoint_path)
    logging.info('Checkpoint path: %s.' % checkpoint_path)

    # data loader
    data_loader = build_data_loader(cfg.data.train)
    train_loader = DataLoaderX(
        data_loader,
        batch_size=cfg.data.batch_size,
        shuffle=True,
        num_workers=args.worker,
        drop_last=True,
        pin_memory=True
    )

    # model
    model = build_model(cfg.model)
    
    # logging.info(model)

    if cfg.train_cfg.optimizer == 'SGD':
        momentum = 0.9
        weight_decay=1e-4
        optimizer = torch.optim.SGD(model.parameters(), lr=cfg.train_cfg.lr, momentum=momentum, weight_decay=weight_decay)
        mlflow.log_params({'momentum': momentum,
                           'weight_decay': weight_decay})
    elif cfg.train_cfg.optimizer == 'Adam':
        optimizer = torch.optim.Adam(model.parameters(), lr=cfg.train_cfg.lr)
    elif cfg.train_cfg.optimizer == 'AdamW':
        optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.train_cfg.lr)

    if args.apex == True:
        model, optimizer = apex.amp.initialize(model.to(device), optimizer, opt_level="O1")
        logging.info("Initializing mixed precision done.")

    model = torch.nn.DataParallel(model).to(device)
    
    start_epoch = 0
    start_iter = 0
    if hasattr(cfg.train_cfg, 'pretrain'):
        assert osp.isfile(cfg.train_cfg.pretrain), 'Error: no pretrained weights found!'
        logging.info('Finetuning from pretrained model %s.' % cfg.train_cfg.pretrain)
        checkpoint = torch.load(cfg.train_cfg.pretrain)
        try:
            logging.info("loading ema pretrained weights!")
            state_dict = checkpoint['ema']
        except:
            state_dict = checkpoint['model']
            new_state_dict = {}
            for k, v in state_dict.items():
                new_state_dict["module.backbone."+k] = v
            state_dict = new_state_dict
        logging.info(model.load_state_dict(state_dict, strict=False))
    if args.resume:
        assert osp.isfile(args.resume), 'Error: no checkpoint directory found!'
        logging.info('Resuming from checkpoint %s.' % args.resume)
        checkpoint = torch.load(args.resume)
        start_epoch = checkpoint['epoch']
        start_iter = checkpoint['iter']
        logging.info(model.load_state_dict(checkpoint['state_dict']))
        optimizer.load_state_dict(checkpoint['optimizer'])
    
    ema = EMA(model, 0.999)
    ema.register()
    
    for epoch in range(start_epoch, cfg.train_cfg.epoch):
        logging.info(cfg_name)
        logging.info('\nEpoch: [%d | %d]' % (epoch + 1, cfg.train_cfg.epoch))

        l_text, l_kernel, l_emb, l_rec, loss, iou_text, iou_kernel, acc = train(train_loader, model, optimizer, ema, epoch, start_iter, cfg, args)
        mlflow.log_metrics({'text loss': l_text,
                            'kernel loss': l_kernel,
                            'emb loss': l_emb,
                            'rec loss': l_rec,
                            'loss': loss,
                            'text iou': iou_text,
                            'kernel iou': iou_kernel,
                            'accuracy': acc},
                            step = epoch)

        ema.apply_shadow()
        ema_state_dict = model.state_dict()
        ema.restore()
        
        state = dict(
            epoch=epoch + 1,
            iter=0,
            state_dict=model.state_dict(),
            optimizer=optimizer.state_dict(),
            ema=ema_state_dict
        )
        file_path = save_checkpoint(state, checkpoint_path, cfg)
        mlflow.log_artifact(file_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Hyperparams')
    parser.add_argument('config', help='config file path')
    parser.add_argument('--resume', nargs='?', type=str, default=None)
    parser.add_argument('--worker', type=int, default=16)
    parser.add_argument('--apex', action='store_true', help='use apex')
    parser.add_argument('--seed', type=int, default=666)

    args = parser.parse_args()

    torch.manual_seed(args.seed)
    torch.cuda.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    
    torch.backends.cudnn.benchmark = True

    setup_logger(name=os.path.basename(args.config),
                 save_dir=os.path.join("checkpoints", os.path.basename(args.config).replace(".py", "")),
                 distributed_rank=0, mode='a+')

    mlflow.set_tracking_uri(MLFLOW_URI)
    print(f"MLflow Backend URI: {mlflow.get_tracking_uri()}")
    try:
        mlflow.create_experiment(experiment_name, f"s3://{S3_BUCKET}")
    except:
        pass
    mlflow.set_experiment(experiment_name)
    run_name = f'{experiment_name}: {str(datetime.now())}'
    with mlflow.start_run(run_name=run_name, log_system_metrics=True) as run:
        print(f"MLflow Artifact URI: {mlflow.get_artifact_uri()}")
        main(args)
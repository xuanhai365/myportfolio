from .. import dataset


def build_data_loader(cfg):
    param = dict()
    for key in cfg:
        if key == 'type':
            continue
        param[key] = cfg[key]
    print(cfg.type)
    data_loader = dataset.__dict__[cfg.type](**param)

    return data_loader

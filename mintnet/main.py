import argparse
import traceback
import time
import shutil
import logging
import yaml
import sys
import os
import torch
import numpy as np
from runners import *

import wandb
import getpass

WANDB = {
    'kechoi': 'kristychoi',
    'chenlin': 'chenlin9',
}


def parse_args_and_config():
    parser = argparse.ArgumentParser(description=globals()['__doc__'])
    parser.add_argument('--runner', type=str, default='DensityEstimationRunner', help='The runner to execute')
    parser.add_argument('--config', type=str, default='mnist_mintnet.yml', help='Path to the config file')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--run', type=str, default='run', help='Path for saving running related data.')
    parser.add_argument('--doc', type=str, default='0', help='A string for documentation purpose')
    parser.add_argument('--verbose', type=str, default='info', help='Verbose level: info | debug | warning | critical')
    parser.add_argument('--test', action='store_true', help='Whether to test the model')
    parser.add_argument('--resume_training', action='store_true', help='Whether to resume training')
    args = parser.parse_args()
    run_id = str(os.getpid())
    run_time = time.strftime('%Y-%b-%d-%H-%M-%S')
    # args.doc = '_'.join([args.doc, run_id, run_time])
    args.log = os.path.join(args.run, 'logs', args.doc)

    # parse config file
    with open(os.path.join('configs', args.config), 'r') as f:
        config = yaml.load(f)
    new_config = dict2namespace(config)

    # make sample dir
    sample_dir = os.path.join('./samples', args.doc)
    if not os.path.exists(sample_dir):
        os.makedirs(sample_dir)
    new_config.sample_dir = sample_dir

    # set up wandb
    mode = None
    wandb.init(
        project='iclr-time-score-dre',
        entity=WANDB[getpass.getuser()],
        name=args.doc,
        # mode='disabled'
        mode=mode
    )

    if not args.test:
        if not args.resume_training:
            if os.path.exists(args.log):
                shutil.rmtree(args.log)
            os.makedirs(args.log)

        with open(os.path.join(args.log, 'config.yml'), 'w') as f:
            yaml.dump(new_config, f, default_flow_style=False)

        # setup logger
        level = getattr(logging, args.verbose.upper(), None)
        if not isinstance(level, int):
            raise ValueError('level {} not supported'.format(args.verbose))

        handler1 = logging.StreamHandler()
        handler2 = logging.FileHandler(os.path.join(args.log, 'stdout.txt'))
        formatter = logging.Formatter('%(levelname)s - %(filename)s - %(asctime)s - %(message)s')
        handler1.setFormatter(formatter)
        handler2.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(handler1)
        logger.addHandler(handler2)
        logger.setLevel(level)

    else:
        level = getattr(logging, args.verbose.upper(), None)
        if not isinstance(level, int):
            raise ValueError('level {} not supported'.format(args.verbose))

        handler1 = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(filename)s - %(asctime)s - %(message)s')
        handler1.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(handler1)
        logger.setLevel(level)

    # add device
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    logging.info("Using device: {}".format(device))
    new_config.device = device

    # set random seed
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    return args, new_config


def dict2namespace(config):
    namespace = argparse.Namespace()
    for key, value in config.items():
        if isinstance(value, dict):
            new_value = dict2namespace(value)
        else:
            new_value = value
        setattr(namespace, key, new_value)
    return namespace


def main():
    args, config = parse_args_and_config()
    logging.info("Writing log file to {}".format(args.log))
    logging.info("Exp instance id = {}".format(os.getpid()))
    logging.info("Config =")
    print(">" * 80)
    print(config)
    print("<" * 80)

    try:
        runner = eval(args.runner)(args, config)
        if not args.test:
            runner.train()

        else:
            runner.test()
    except:
        logging.error(traceback.format_exc())

    return 0


if __name__ == '__main__':
    sys.exit(main())

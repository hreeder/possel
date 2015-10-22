import yaml


class PosselConfig:
    def __init__(self, settings={}):
        self.config = settings

    def read_config(self, config):
        with open(config, 'r') as configfile:
            self.config.update(yaml.load(configfile))

    def update_from_argparse(self, args):
        self.config.update(args.__dict__)

    def __getattr__(self, item):
        return self.config[item]

    def __getitem__(self, item):
        return self.config[item]

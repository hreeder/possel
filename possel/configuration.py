import yaml


class Configuration:
    def __init__(self, default=None):
        self.config = default or {}

    def read_configuration(self, config):
        with open(config, 'r') as configfile:
            self.config.update(yaml.load(configfile))

    def update_from_argparse(self, args):
        for key in args.__dict__:
            if args.__dict__[key]:
                self.config[key] = args.__dict__[key]
            # If there's a key in argparse, but it doesn't have a corresponding key in the config
            # Create the key in the config, as it is still a configuration value
            elif key not in self.config:
                self.config[key] = None

    def __getattr__(self, item):
        return self.config[item]

    def __getitem__(self, item):
        return self.config[item]

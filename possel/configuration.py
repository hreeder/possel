import yaml


class Configuration:
    def __init__(self, default={}):
        self.config = default

    def read_configuration(self, config):
        with open(config, 'r') as configfile:
            self.config.update(yaml.load(configfile))

    def update_from_argparse(self, args):
        for key in args.__dict__:
            if args.__dict__[key]:
                self.config[key] = args.__dict__[key]

    # Trying and excepting on KeyError allows us to do things like
    # "if config.value" and have it return False if the value has not been set
    # In this case, if a default should be true, pass the key/value pair in the default config
    def __getattr__(self, item):
        try:
            return self.config[item]
        except KeyError:
            return False

    def __getitem__(self, item):
        try:
            return self.config[item]
        except KeyError:
            return False

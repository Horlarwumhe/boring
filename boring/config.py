import os


class BadConfigFile(Exception):
    pass


class Config:
    ''' Configurations class for the server '''
    def __init__(self, args, config_file='boring.config'):
        self.args = args
        self.file = config_file  # self.load(config_file)
        self._options = {}

    def load(self):
        path = os.path.abspath(self.file)
        if not os.path.exists(path):
            raise BadConfigFile('path to config file not found %s' % path)
        try:
            config = open(self.file)
        except PermissionError as e:
            raise OSError('Failed to open config file [%s]' % e)
        while 1:
            line = config.readline()
            if not line:
                break
            if line.strip().startswith('#') or line.isspace():
                continue
            try:
                key, value = line.split('=')
            except ValueError as e:
                raise BadConfigFile("Bad config file %s [%s]" % (line, e))
            key = key.strip().rstrip()
            value = value.strip().rstrip('\n')
            self._options[key] = value

    def __getitem__(self, name):
        value = self._options.get(name)
        if not value:
            if not self.args:
                # the server is not started from command line
                return ''
            return getattr(self.args, name, '')
        return value

    def __setitem__(self, key, value):
        self._options[key] = value

    __getattr__ = __getitem__

    def __bool__(self):
        return True


class DummyConfig:
    # pylint: disable=unused-argument
    def __init__(self, *args):
        pass

    def __getitem__(self, name):
        return ''

    def __setitem__(self, *args):
        pass

    __getattr__ = __getitem__

    def __bool__(self):
        return False

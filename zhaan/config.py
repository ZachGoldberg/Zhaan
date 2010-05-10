import ConfigParser, os

class ZhaanConfig(object):


    file = os.path.expanduser('~/.config/zhaan.cfg')

    def __init__(self):
        self.config = self.__load_config()

    def write(self):
        self.config.write(open(self.file, 'w'))

    def get(self, section, option):
        return self.config.get(section, option)

    def set(self, section, option, value):
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, option, value)
        self.write()

    def __load_config(self):
        config = ConfigParser.ConfigParser()
        files = config.read([ZhaanConfig.file])

        if not files:
            return ZhaanConfig.write_default_config()

        return config

    @classmethod
    def write_default_config(clazz):
        config = ConfigParser.ConfigParser()
        config.add_section("Playback")
        config.set("Playback", "Randomized", "false")
        config.write(open(ZhaanConfig.file, 'w'))
        return config


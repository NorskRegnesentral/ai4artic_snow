import attr
import json
import pickle
import copy
import logging

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

from pathlib import Path, PosixPath


JSON_SUFFIXES = (".json", ".jsn")
YAML_SUFFIXES = (".yaml", ".yml")
PICKLE_SUFFIXES = (".pickle", ".pkl", ".pcl")


logger = logging.getLogger(__name__)


class Config(dict):
    """Mapping object allowing attribute access to contents"""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        del self[key]


class ConfigJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, Config):
            return dict(o)
        return super().default(o)


@attr.s
class AttrsConverter:
    allow_none = attr.ib(default=True, converter=bool)
    deepcopy = attr.ib(default=True, converter=bool)

    def __call__(self, arg=None):
        if arg is None:
            return Config()
        arg = cfg_from_dict(arg)
        if deepcopy:
            arg = deepcopy(arg)
        return arg


# Define encoders for YAML
if yaml is not None:

    def _yaml_config_representer(dumper, data):
        dumper.sort_keys = False
        return dumper.represent_dict(data)

    def _yaml_path_representer(dumper, data):
        return dumper.represent_str(str(data))

    yaml.add_representer(Config, _yaml_config_representer)
    yaml.add_representer(Path, _yaml_path_representer)
    yaml.add_representer(PosixPath, _yaml_path_representer)


def assert_yaml():
    assert yaml is not None, \
        "'yaml' is not available. Please install with 'pip install pyyaml'"


def cfg_from_dict(d=None):
    """Recursively construct Config object from dictionary

    Parameters
    ----------
    d : dict
        The dictionary to convert to Config()

    Returns
    -------
    Config
        The resulting Config() object
    """
    if d is None:
        return Config()
    c = Config()
    for k, v in d.items():
        if isinstance(v, dict):
            v = cfg_from_dict(v)
        c[k] = v
    return c


def deepcopy(cfg):
    """Recursively copy the config

    Parameters
    ----------
    cfg : Config
        The config to copy

    Returns
    -------
    Config
        The copy of the input config
    """
    return copy.deepcopy(cfg)


def keypath_update(cfg, keypath, value):
    """Update config value using keypath (list of keys)

    Parameters
    ----------
    cfg : Config
        The config to update.
    keypath : list
        list of keys
    value :
        New/updated value.

    Returns
    -------
    None
        None

    """
    d = cfg
    for k in keypath[:-1]:
        d = d.setdefault(k, Config())
    recursive_update(d, {keypath[-1]: value})


def apply_variables(cfg, variables, recursive=True, missing_variable_action=""):
    """Recursively update string values with variables

    Values in config are updated using ``value.format(**variables)``. Thus, the
    config string values are assumed to be formatted using named references
    to the variable names. I.e "This string contains {variable_name}". Whereas the
    variables dictionary contains the variable name as key:
    ``dict(variable_name="garbage")``

    If ``recursive`` is True (default) the variables are applied recursively
    to the config.

    Parameters
    ----------
    cfg : Config
        The config to apply variables to
    variables : dict
        A dictionary containing the variables
    missing_variable_action : str ("warning", "exception" or "")
        Action to perform if a config string value contains reference to variable
        not in the variables dictionary. Nothing (""), log a warning ("warning")
        or raise an exception ("exception"). Default is nothing.

    Returns
    -------
    None

    """
    for k, v in cfg.items():
        if recursive and isinstance(v, dict):
            apply_variables(
                v, variables, missing_variable_action=missing_variable_action
            )
            continue
        try:
            cfg[k] = v.format(**variables)
        except KeyError as ke:
            if missing_variable_action.lower() in ("warning", "warn"):
                logger.warning("Variable '%s' missing. Failed to apply to '%s'",
                               ke, k)
            elif missing_variable_action.lower() in ("exception", "except"):
                raise ke
        except AttributeError:
            # Not a string value
            pass


def recursive_update(cfg, update):
    """Recursively update and overwrite config.

    Keys not in the update config are left untouched.

    Parameters
    ----------
    cfg : :py:class:`Config`
        The config to insert fields from update into
    update : :py:class:`Config` or dict
        Config or dictionary object to copy into cfg

    Returns
    -------
    :py:class:`Config`
        The updated config.
    """
    for k, v in update.items():
        if isinstance(v, dict):
            assert isinstance(
                cfg.setdefault(k, Config()), dict
            ), "Cannot update non Config with dict"
            recursive_update(cfg[k], v)
        else:
            assert k not in cfg or not isinstance(
                cfg[k], dict
            ), "Cannot update dict with non dict"
            cfg[k] = v
    return cfg


def combine(cfgs):
    """Combine configs into one by recursive_update

    Parameters:
    -----------
    cfgs : list
        List of configs to combine

    Returns:
    --------
    :py:class:`Config`
        The combination of all configs
    """
    ocfg = Config()
    for c in cfgs:
        ocfg = recursive_update(ocfg, c)
    return ocfg


def load_directory(path, keysep=".", recursive=False, exclude=None):
    """Read a directory of config files

    A structure like:

        config/
            __init__.py
            foobar.yml
            foo.yml
            bar.yml
            abc.def.yml
            logging.json

    Then

        load_directory("config/")

    will result in a config like:

        config.foobar: <contents of foobar.yml>
        config.foo: <contents of foo.yml>
        config.bar: <contents of bar.yml>
        config.abc.def: <contents of abc.def.yml>
        config.logging: <contents of logging.json>

    Parameters
    ----------
    path : str or Path
        Path to directory to read
    keysep : str
        String to use for splitting filename into config keys
    recursive : bool
        Read directory recursively
    exclude : iterable
        List with files to exclude

    Returns
    -------
    Config
        The config with contents from all (not excluded) files

    """
    config = Config()
    for f in path.iterdir():
        if exclude is not None and f.name in exclude:
            continue
        if f.is_dir():
            if not recursive:
                continue
            c = load_directory(f, keysep, recursive, exclude)
        else:
            try:
                c = load(f)
            except IOError:
                continue
        keys = f.stem.split(keysep)
        cfg = config
        for k in keys:
            cfg = cfg.setdefault(k, Config())
        recursive_update(cfg, c)
    return config


def load(path, format=""):
    """Read config from filename

    Read config from a JSON, YAML or Pickle file.

    Parameters
    ----------
    path : str or Path
        File to read.
    format : str
        Set format of the file. Default is derived from suffix. One of 'json',
        'yaml' or 'pickle'

    Returns
    -------
    Config
        Config object read from file

    Raises
    ------
    IOError : If suffix is unknown
    """
    path = Path(path)
    if path.suffix in JSON_SUFFIXES or format.lower() == "json":
        with path.open() as fid:
            d = json.load(fid)
            return cfg_from_dict(d)
    elif path.suffix in YAML_SUFFIXES or format.lower() == "yaml":
        assert_yaml()
        with path.open() as fid:
            d = yaml.load(fid, yaml.Loader)
        return cfg_from_dict(d)
    elif path.suffix in PICKLE_SUFFIXES or format.lower() == "pickle":
        with path.open("rb") as fid:
            return pickle.load(fid)
    else:
        raise IOError("Config file suffix {} not supported".format(path.suffix))


def loads(s, format="yaml"):
    """Load from string or bytes

    Parameters
    ----------
    s : str or byte
        String or byte (if binary format as pickle) to load Config from
    format : str
        Which format the Config is written in. ('pickle', 'yaml' or 'json')

    Returns
    -------
    Config
        Loaded Config object

    Raises
    -------
    Exception
        If unknown format

    """
    if format.lower() in ("pickle", ):
        return pickle.loads(s)
    if format.lower() in ("yaml"):
        return yaml.load(s, yaml.Loader)
    if format.lower() in ("json"):
        return json.loads(s)
    raise Exception("Unkown dump format '{}'".format(format))


def dump(cfg, path):
    """Write config to file

    Write config to a JSON, YAML or Pickle file. Suffix of file determines the
    file format.

    Parameters
    ----------
    cfg : Config
        Config object to write to file
    path : str or Path
        Full path of file to write.

    Returns
    -------
    None

    Raises
    ------
    IOError : Raised if unknown suffix is given
    """
    path = Path(path)
    if path.suffix in JSON_SUFFIXES:
        with path.open("w") as fid:
            json.dump(cfg, fid, indent=4, cls=ConfigJSONEncoder)
    elif path.suffix in YAML_SUFFIXES:
        assert_yaml()
        with path.open("w") as fid:
            yaml.dump(cfg, stream=fid, indent=4, default_flow_style=False)
    elif path.suffix in PICKLE_SUFFIXES:
        with path.open("wb") as fid:
            pickle.dump(cfg, fid)
    else:
        raise IOError("Config file suffix {} not supported".format(path.suffix))


def dumps(cfg, format="yaml"):
    """Dump to string

    Parameters
    ----------
    cfg : Config
        Config object to dump
    format : str
        Which format to use. ('pickle', 'yaml' or 'json')

    Returns
    -------
    str or bytes
        The string representation of the Config.

    Raises
    -------
    Exception
        If an unsupported format is requested

    """
    if format.lower() in ("pickle", ):
        return pickle.dumps(cfg)
    if format.lower() in ("yaml"):
        return yaml.dump(cfg, indent=4, default_flow_style=False)
    if format.lower() in ("json"):
        return json.dumps(cfg, indent=4, cls=ConfigJSONEncoder)
    raise Exception("Unkown dump format '{}'".format(format))


def yaml_dumps(cfg):
    """YAML dump to string.

    Parameters
    ----------
    cfg : config
        config to dump.

    Returns
    -------
    str
        YAML formatted string of config
    """
    assert_yaml()
    return yaml.dump(cfg, indent=4, default_flow_style=False)

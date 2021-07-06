import itertools
import os
from copy import deepcopy
from typing import List

from cw2 import util
from cw2.cw_config import conf_path
from cw2.cw_config import cw_conf_keys as KEY
from cw2.cw_data import cw_logging


def unfold_exps(exp_configs: List[dict]) -> List[dict]:
    """unfolds a list of experiment configurations into the different
    hyperparameter runs and repetitions

    Args:
        exp_configs (List[dict]): list of experiment configurations

    Returns:
        List[dict]: list of unfolded experiment configurations
    """
    param_expansion = expand_experiments(exp_configs)
    unrolled = unroll_exp_reps(param_expansion)
    return unrolled


def expand_experiments(_experiment_configs: List[dict]) -> List[dict]:
    """Expand the experiment configuration with concrete parameter instantiations

    Arguments:
        experiment_configs {List[dict]} -- List with experiment configs

    Returns:
        List[dict] -- List of experiment configs, with set parameters
    """

    # get all options that are iteratable and build all combinations (grid) or tuples (list)
    experiment_configs = deepcopy(_experiment_configs)
    expanded_config_list = []
    for config in experiment_configs:
        iter_func = None
        key = None

        # Set Default Values
        # save path argument from YML for grid modification
        if KEY.i_BASIC_PATH not in config:
            config[KEY.i_BASIC_PATH] = config[KEY.PATH]
        # save name argument from YML for grid modification
        if KEY.i_EXP_NAME not in config:
            config[KEY.i_EXP_NAME] = config[KEY.NAME]
        # add empty string for parent DIR in case of grid
        if KEY.i_NEST_DIR not in config:
            config[KEY.i_NEST_DIR] = ''

        # In-Between Step to solve grid AND list combinations
        if all(k in config for k in (KEY.GRID, KEY.LIST)):
            iter_func = zip
            key = KEY.LIST

            experiment_configs += params_combine(
                config, key, iter_func)
            continue

        if KEY.GRID in config:
            iter_func = itertools.product
            key = KEY.GRID

        if KEY.LIST in config:
            iter_func = zip
            key = KEY.LIST

        expansion = params_combine(config, key, iter_func)

        if KEY.ABLATIVE in config:
            expansion += ablative_expand(expansion)

        expanded_config_list += expansion
    return conf_path.normalize_expanded_paths(expanded_config_list)


def params_combine(config: dict, key: str, iter_func) -> List[dict]:
    """combines experiment parameter with its list/grid combinations

    Args:
        config (dict): an single experiment configuration
        key (str): the combination key, e.g. 'list' or 'grid'
        iter_func: itertool-like function for creating the combinations

    Returns:
        List[dict]: list of parameter-combined experiments
    """
    if iter_func is None:
        return [config]

    combined_configs = []
    # convert list/grid dictionary into flat dictionary, where the key is a tuple of the keys and the
    # value is the list of values
    tuple_dict = util.flatten_dict_to_tuple_keys(config[key])
    _param_names = ['.'.join(t) for t in tuple_dict]

    param_lengths = map(len, tuple_dict.values())
    if key == KEY.LIST and len(set(param_lengths)) != 1:
        cw_logging.getLogger().warning(
            "list params of experiment \"{}\" are not of equal length.".format(config[KEY.NAME]))

    # create a new config for each parameter setting
    for values in iter_func(*tuple_dict.values()):
        _config = deepcopy(config)

        # Remove Grid/List Argument
        del _config[key]

        if KEY.PARAMS not in _config:
            _config[KEY.PARAMS] = {}

        # Expand Grid/List Parameters
        for i, t in enumerate(tuple_dict.keys()):
            util.insert_deep_dictionary(
                _config[KEY.PARAMS], t, values[i])

        _config = extend_config_name(_config, _param_names, values)
        combined_configs.append(_config)
    return combined_configs


def ablative_expand(conf_list: List[dict]) -> List[dict]:
    """expand experiment configurations according to the "ablative" design

    Args:
        conf_list (List[dict]): a list of experiment configurations

    Returns:
        List[dict]: list of experiment configurations with ablative expansion
    """
    combined_configs = []
    for config in conf_list:
        tuple_dict = util.flatten_dict_to_tuple_keys(config[KEY.ABLATIVE])
        _param_names = ['.'.join(t) for t in tuple_dict]

        for i, key in enumerate(tuple_dict):
            for val in tuple_dict[key]:
                _config = deepcopy(config)

                if KEY.PARAMS not in _config:
                    _config[KEY.PARAMS] = {}

                util.insert_deep_dictionary(
                    _config[KEY.PARAMS], key, val
                )

                _config = extend_config_name(_config, _param_names[i], [val])
                combined_configs.append(_config)
    return combined_configs


def extend_config_name(config: dict, param_names: list, values: list) -> dict:
    """extend an experiment name with a shorthand derived from the parameters and their values

    Args:
        config (dict): experiment config
        param_names (list): list of parameter names
        values (list): list of parameter values

    Returns:
        dict: experiment config with extended name
    """
    # Rename and append
    _converted_name = util.convert_param_names(param_names, values)

    # Use __ only once as a seperator
    sep = '__'
    if KEY.i_EXP_NAME in config and sep in config[KEY.i_EXP_NAME]:
        sep = '_'

    config[KEY.i_EXP_NAME] = config[KEY.i_EXP_NAME] + sep + _converted_name
    config[KEY.i_NEST_DIR] = config[KEY.NAME]
    return config


def unroll_exp_reps(exp_configs: List[dict]) -> List[dict]:
    """unrolls experiment repetitions into their own configuration object

    Args:
        exp_configs (List[dict]): List of experiment configurations

    Returns:
        List[dict]: List of unrolled experiment configurations
    """
    unrolled_exps = []

    for config in exp_configs:
        if KEY.i_REP_IDX in config:
            unrolled_exps.append(config)
            continue

        for r in range(config[KEY.REPS]):
            c = deepcopy(config)
            c[KEY.i_REP_IDX] = r
            c[KEY.i_REP_LOG_PATH] = os.path.join(
                c[KEY.LOG_PATH], 'rep_{:02d}'.format(r))
            unrolled_exps.append(c)
    return unrolled_exps

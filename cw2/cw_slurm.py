import os
import sys

import attrdict

import __main__
from cw2 import cli_parser, config

def _finalize_slurm_config(conf: config.Config, num_jobs: int) -> attrdict:
    """enrich slurm configuration with dynamicallyy computed values

    Args:
        conf (config.Config): configuration object.
        num_jobs (int): total number of defined jobs

    Returns:
        attrdict: complete slurm configuration dictionary
    """
    sc = conf.slurm_config

    # numjobs is last job index, counting starts at 0
    sc['num_jobs'] = num_jobs - 1

    if "experiment_cwd" not in sc:
        sc["experiment_cwd"] = os.getcwd()

    if "experiment_log" not in sc:
        sc["experiment_log"] = os.path.join(conf.exp_configs[0]['_experiment_path'], 'log')

    if "slurm_ouput" not in sc:
        sc["slurm_out"] = os.path.join(conf.exp_configs[0]['_experiment_path'], 'sbatch.sh')

    os.makedirs(sc["experiment_log"], exist_ok=True)

    cw_options = cli_parser.Arguments().get()
    sc["experiment_selectors"] = ""

    if cw_options.experiments is not None:
        sc["experiment_selectors"] = "-e " + " ".join(cw_options.experiments)

    # TODO: Automatically fill in python path?
    print(sys.path)

    return sc


def create_slurm_script(conf: config.Config, num_jobs: int) -> str:
    """creates an sbatch.sh script for slurm

    Args:
        conf (config.Config): Configuration object 

    Returns:
        str: path to slurm file
    """
    sc = _finalize_slurm_config(conf, num_jobs)
    template_path = conf.slurm_config.path_to_template
    output_path = sc["slurm_out"]

    experiment_code = __main__.__file__

    fid_in = open(template_path, 'r')
    fid_out = open(output_path, 'w')

    tline = fid_in.readline()

    while tline:
        tline = tline.replace('%%project_name%%', sc['project_name'])
        tline = tline.replace('%%experiment_name%%',
                              sc['experiment_name'])
        tline = tline.replace('%%time_limit%%', '{:d}:{:d}:00'.format(sc['time_limit'] // 60,
                                                                      sc['time_limit'] % 60))

        #tline = tline.replace('%%experiment_root%%', sc['experiment_root'])
        tline = tline.replace('%%experiment_cwd%%', sc['experiment_cwd'])
        tline = tline.replace('%%experiment_log%%', sc['experiment_log'])
        tline = tline.replace('%%python_script%%', experiment_code)
        tline = tline.replace('%%exp_name%%', sc["experiment_selectors"])
        tline = tline.replace('%%path_to_yaml_config%%', conf.config_path)
        tline = tline.replace('%%num_jobs%%', '{:d}'.format(sc['num_jobs']))
        tline = tline.replace('%%num_parallel_jobs%%',
                              '{:d}'.format(sc['num_parallel_jobs']))
        tline = tline.replace('%%mem%%', '{:d}'.format(sc['mem']))
        tline = tline.replace('%%number_of_jobs%%',
                              '{:d}'.format(sc['number_of_jobs']))
        tline = tline.replace('%%number_of_cpu_per_job%%',
                              '{:d}'.format(sc['number_of_cpu_per_job']))

        fid_out.write(tline)

        tline = fid_in.readline()
    fid_in.close()
    fid_out.close()
    return output_path

import os
import subprocess
import tempfile

CUR_DIR = os.path.dirname(__file__)

babel_cfg = os.path.join(CUR_DIR, 'babel.cfg')


def _run(cmd):
    print(f'--Running {cmd}')
    return subprocess.call(cmd, shell=True)


def _rm_tmp(tmp):
    if tmp and len(tmp) > 2:  # weak protect
        _run(f'rm -f {tmp}')


def _check_exists(path):
    return os.path.exists(path)


def _extract_messages(scan_dir, pot_file, config_file=None):
    config_file = config_file or babel_cfg
    cmd = f'pybabel extract -F {config_file} -k _l -o {pot_file} {scan_dir}'
    return _run(cmd)


def create_translations(scan_dir, translations_dir, language, config_file=None):
    tmp = tempfile.mktemp(suffix='.pot')
    try:
        _extract_messages(scan_dir, tmp, config_file=config_file)
        _run(f'pybabel init -i {tmp} -d {translations_dir} -l {language}')
    finally:
        _rm_tmp(tmp)


def update_translations(scan_dir, translations_dir, config_file=None):
    if not _check_exists(translations_dir):
        print(f'Translations dir ({translations_dir}) does not exists. Skip updating.')
        return
    tmp = tempfile.mktemp(suffix='.pot')
    try:
        _extract_messages(scan_dir, tmp, config_file=config_file)
        _run(f'pybabel update -i {tmp} -d {translations_dir}')
        _run(f'pybabel compile -d {translations_dir}')
    finally:
        _rm_tmp(tmp)


def compile_translations(translations_dir):
    if not _check_exists(translations_dir):
        print(f'Translations dir ({translations_dir}) does not exists. Skip compiling.')
        return
    _run(f'pybabel compile -d {translations_dir}')

import inspect
import subprocess
import os


def run_subprocess(call, env=None):
    """
    Args:
        call (list): List of strings repr. the command to run (ex. ["git", "diff", "--name-only"])
    Returns:
        str: The stdout from the command that was run
    """
    branch_out = subprocess.Popen(
        call,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env
    )
    stdout, stderr = branch_out.communicate()
    if stderr:
        stderr = stderr.decode('utf-8')
        raise Exception(stderr)
    stdout = stdout.decode('utf-8')
    return stdout


def up():
    # 0. get ip
    import platform
    os_type = platform.platform()
    env = os.environ.copy()

    user = os.getenv("USER")
    if "Linux" in os_type:
        ip = run_subprocess(["hostname", "-I"])
        ip = ip.split(" ")[0]
        env["DOCKER_USER"] = f"{user}-ubuntu"
    else:
        ip = run_subprocess(["ipconfig", "getifaddr", "en0"])
        env["DOCKER_USER"] = f"{user}-mac"
    env["EXTERNAL_IP"] = ip

    # 1. check whether have micro-net
    res = run_subprocess(["docker", "network", "inspect", "micro-net"])
    if res.find("No such network") != -1:
        run_subprocess(
            ["docker", "network", "create", "--subnet=192.168.100.0/24",
             "micro-net"])

    cwd = os.path.abspath(inspect.getfile(up))
    cwd = os.path.dirname(cwd)
    file_loc = os.path.join(cwd, 'docker-compose.yml')
    res = run_subprocess(["docker-compose", "-f", file_loc, "pull"])
    print(res)
    res = run_subprocess(
        ["docker-compose", "-f", file_loc, "up", "-d", "--remove-orphans"], env=env)
    print(res)

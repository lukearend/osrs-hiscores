""" VPN driver code. """

import logging
import shlex
import textwrap
from getpass import getpass
from pathlib import Path
from subprocess import Popen, PIPE, DEVNULL


def reset_vpn(password):
    """ Reset VPN, acquiring a new IP address. Requires root permissions. """

    vpn_script = Path(__file__).resolve().parents[2] / "bin" / "reset_vpn"
    logging.info(f"resetting VPN...")
    checksudo(password)
    proc = Popen(vpn_script, stderr=PIPE)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"resetting VPN failed.\n{proc.stderr.read().decode()}")
    logging.info(f"successfully reset VPN")


def checksudo(password):
    """ Attempt to acquire sudo permissions using the given password. """

    proc = Popen(shlex.split(f"sudo -Svp ''"), stdin=PIPE, stderr=DEVNULL)
    proc.communicate(password.encode())
    if proc.returncode != 0:
        raise ValueError("sudo failed to authenticate")


def askpass():
    print(textwrap.dedent("""
        Root permissions are required by the OpenVPN client which is used
        during scraping to periodically acquire a new IP address. Privileges
        granted here are only used to start and stop the VPN connection.
        """))
    pwd = getpass("Enter root password: ")
    print()
    checksudo(pwd)
    return pwd

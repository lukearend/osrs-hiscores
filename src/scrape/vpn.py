import shlex
import subprocess
import textwrap
from getpass import getpass
from pathlib import Path
from subprocess import Popen, PIPE, DEVNULL


def reset_vpn():
    """ Reset VPN, acquiring a new IP address. Requires root permissions. """
    vpn_script = Path(__file__).resolve().parents[2] / "bin" / "reset_vpn"
    p = subprocess.run(vpn_script)
    p.check_returncode()


def getsudo(password):
    """ Attempt to acquire sudo permissions using the given password. """
    proc = Popen(shlex.split(f"sudo -Svp ''"), stdin=PIPE, stderr=DEVNULL)
    proc.communicate(password.encode())
    return True if proc.returncode == 0 else False


def askpass():
    """ Request root password for VPN usage. """
    msg1 = textwrap.dedent("""
        Root permissions are required by the OpenVPN client which is used during
        scraping to periodically acquire a new IP address. Privileges granted here
        will only be used to manage the VPN connection and the password will only
        persist in RAM as long as the program is running.
        """)

    msg2 = textwrap.dedent("""
        Proceeding without VPN. It is likely your IP address will get blocked or
        throttled after a few minutes of scraping due to the volume of requests.
        """)

    print(msg1)
    pwd = getpass("Enter root password (leave empty to continue without VPN): ")
    if not pwd:
        print(msg2)
        return None
    print()
    return pwd

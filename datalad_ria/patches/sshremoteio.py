"""

This patch fixes the __init__ function of SSHRemoteIO, i.e.
it adds error handling and a proper SSHRI-to-string function.
"""

import logging
import subprocess

from datalad import ssh_manager
from datalad.support.exceptions import CommandError
from datalad_next.patches import apply_patch

# use same logger as -core
lgr = logging.getLogger('datalad.customremotes.ria_remote')


# This method is taken from
# datalad@8a145bf432ae8931be7039c97ff602e53813d238
# datalad/distributed/ore-remote.py:SSHRemoteIO.__init___


DEFAULT_BUFFER_SIZE = 65536


def _sshri_as_url(sshri):
    fields = sshri.fields
    url_format = 'ssh://'
    if fields['username']:
        url_format += '{username}@'
    url_format += '{hostname}'
    if fields['port']:
        url_format += ':{port}'
    if fields['path']:
        if not fields.path.startswith('/'):
            url_format += '/'
        url_format += {'path'}
    return url_format.format(**fields)


def __init__(self, host, buffer_size=DEFAULT_BUFFER_SIZE):
    """
    Parameters
    ----------
    host : str
      SSH-accessible host(name) to perform remote IO operations
      on.
    """

    # the connection to the remote
    # we don't open it yet, not yet clear if needed
    self.ssh = ssh_manager.get_connection(
        host,
        use_remote_annex_bundle=False,
    )
    self.ssh.open()
    # open a remote shell
    cmd = ['ssh'] + self.ssh._ssh_args + [_sshri_as_url(self.ssh.sshri)]
    self.shell = subprocess.Popen(cmd,
                                  stderr=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE,
                                  stdin=subprocess.PIPE)
    # swallow login message(s):
    self.shell.stdin.write(b"echo RIA-REMOTE-LOGIN-END\n")
    self.shell.stdin.flush()
    while True:
        status = self.shell.poll()
        if status not in (0, None):
            raise CommandError(f'ssh shell process exited with {status}')
        line = self.shell.stdout.readline()
        if line == '':
            raise RuntimeError(f'ssh shell process close stdout unexpectedly')
        if line == b"RIA-REMOTE-LOGIN-END\n":
            break
    # TODO: Same for stderr?

    # make sure default is used when None was passed, too.
    self.buffer_size = buffer_size if buffer_size else DEFAULT_BUFFER_SIZE


apply_patch(
    'datalad.distributed.ora_remote', 'SSHRemoteIO', '__init__',
    __init__,
)

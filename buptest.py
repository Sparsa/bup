
from __future__ import absolute_import, print_function
from collections import namedtuple
from contextlib import contextmanager
from os.path import abspath, basename, dirname, realpath
from pipes import quote
from subprocess import PIPE, Popen
from traceback import extract_stack
import errno, os, subprocess, sys, tempfile

from wvtest import WVPASSEQ, wvfailure_count

from bup import helpers


@contextmanager
def no_lingering_errors():
    def fail_if_errors():
        if helpers.saved_errors:
            bt = extract_stack()
            src_file, src_line, src_func, src_txt = bt[-4]
            msg = 'saved_errors ' + repr(helpers.saved_errors)
            print('! %-70s %s' % ('%s:%-4d %s' % (basename(src_file),
                                                  src_line,
                                                  msg),
                                  'FAILED'))
            sys.stdout.flush()
    fail_if_errors()
    helpers.clear_errors()
    yield
    fail_if_errors()
    helpers.clear_errors()


# Assumes (of course) this file is at the top-level of the source tree
_bup_tmp = realpath(dirname(__file__) + '/t/tmp')
try:
    os.makedirs(_bup_tmp)
except OSError as e:
    if e.errno != errno.EEXIST:
        raise


@contextmanager
def test_tempdir(prefix):
    initial_failures = wvfailure_count()
    tmpdir = tempfile.mkdtemp(dir=_bup_tmp, prefix=prefix)
    yield tmpdir
    if wvfailure_count() == initial_failures:
        subprocess.call(['chmod', '-R', 'u+rwX', tmpdir])
        subprocess.call(['rm', '-rf', tmpdir])


ex_res = namedtuple('SubprocResult', ['out', 'err', 'proc', 'rc'])

def run(cmd, check=True, input=None, **kwargs):
    """Run a subprocess as per subprocess.Popen(cmd, **kwargs) followed by
    communicate(input=input).  If check is true, then throw an
    exception if the subprocess exits with non-zero status.  Return a
    SubprocResult tuple.

    """
    if input:
        assert 'stdin' not in kwargs
        kwargs['stdin'] = PIPE
    p = Popen(cmd, **kwargs)
    out, err = p.communicate(input=input)
    if check and p.returncode != 0:
        raise Exception('subprocess %r failed with status %d%s'
                        % (' '.join(map(quote, cmd)), p.returncode,
                           (', stderr: %r' % err) if err else ''))
    return ex_res(out=out, err=err, proc=p, rc=p.returncode)

def logcmd(cmd):
    if isinstance(cmd, basestring):
        print(cmd, file=sys.stderr)
    else:
        print(' '.join(map(quote, cmd)), file=sys.stderr)

def ex(cmd, **kwargs):
    """Print cmd to stderr and then run it as per ex(...).
    Print the subprocess stderr to stderr if stderr=PIPE and there's
    any data.
    """
    logcmd(cmd)
    result = run(cmd, **kwargs)
    if result.err:
        sys.stderr.write(result.err)
    return result

def exo(cmd, **kwargs):
    """Print cmd to stderr and then run it as per ex(..., stdout=PIPE).
    Print the subprocess stderr to stderr if stderr=PIPE and there's
    any data.

    """
    assert 'stdout' not in kwargs
    kwargs['stdout'] = PIPE
    return ex(cmd, **kwargs)
'''Utilities to help manage the various environments required in the LHCb software.'''

import subprocess, select, timeit, exceptions, pprint, tempfile, os

strippingDVVersions = {'stripping21' : ('v36r2', 'x86_64-slc6-gcc48-opt'), # Should be 'v36r1p3' but it crashes when importing anything Stripping related.
                       'stripping20' : ('v32r2p1', 'x86_64-slc5-gcc46-opt'),
                       'stripping20r1' : ('v32r2p3', 'x86_64-slc5-gcc46-opt')}

def get_stripping_dv_version(version) :
    version = version.lower()
    if version in strippingDVVersions :
        return strippingDVVersions[version]
    version = 'stripping' + version.replace('stripping', '').split('p')[0]
    if version in strippingDVVersions :
        return strippingDVVersions[version]
    version = 'stripping' + version.replace('stripping', '').split('r')[0]
    if version in strippingDVVersions :
        return strippingDVVersions[version]
    return None, None

class Shell(object) :
    __slots__ = ('args', 'process', 'stdoutpoller', 'stderrpoller', 'exitcodeline', 
                 'exittest', 'getexitcode', 'initoutput', 'stdout', 'stderr')
    
    def __init__(self, args, exitcodeline, exittest, getexitcode, inittimeout = None, 
                 env = None) :
        if isinstance(args, str) :
            args = [args]
        self.args = args
        self.exitcodeline = exitcodeline
        if isinstance(exittest, str) :
            self.exittest = lambda line : exittest in line
        else :
            self.exittest = exittest
        self.getexitcode = getexitcode
        self.process = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.PIPE, 
                                        stdin = subprocess.PIPE, env = env, bufsize = -1)
        self.stdout = self.process.stdout
        self.stderr = self.process.stderr
        self.stdoutpoller = select.poll()
        self.stdoutpoller.register(self.stdout.fileno(), select.POLLIN)
        self.stderrpoller = select.poll()
        self.stderrpoller.register(self.stderr.fileno(), select.POLLIN)

        # Ensure that any initial configuration of the environment is done before proceeding.
        self.initoutput = None
        self.initoutput = self.eval('', timeout = inittimeout, raiseerror = True)

    def is_alive(self, raiseError = False) :
        if self.process.poll() :
            if raiseError :
                raise RuntimeError('The shell with args ' + repr(self.args) + 
                                   ', pid ' + str(self.process.pid) 
                                   + ', has died!') 
            return False
        return True

    def _read(self, polltime = 100, timeout = None) :

        if not self.is_alive() :
            stdout = ''
            exitcode = None
            for line in self.stdout :
                stdout += line
                if self.exittest(line) :
                    exitcode = self.getexitcode(line)
            stderr = self.stderr.read()
            self.stdout.close()
            self.stderr.close()
            return {'stdout' : stdout, 'stderr' : stderr, 'exitcode' : exitcode}
        
        stdout = stderr = ''
        exitcode = None
        if timeout :
            now = timeit.default_timer()
            testtimeout = lambda : ((timeit.default_timer() - now) < timeout)
        else :
            testtimeout = lambda : True 
        # Read stdout at a frequency of polltime til the exit signature is found or 
        # the timeout is reached. 
        while testtimeout() :
            if not self.stdoutpoller.poll(polltime) :
                continue
            line = self.stdout.readline()
            if self.exittest(line) :
                exitcode = self.getexitcode(line)
                break
            stdout += line
        # Read stderr til there's nothing left to read. 
        while self.stderrpoller.poll(0) and testtimeout() :
            stderr += self.stderr.readline()
        return {'stdout' : stdout, 'stderr' : stderr, 'exitcode' : exitcode}

    def eval(self, cmd, polltime = 100, timeout = None, raiseerror = False) :

        self.is_alive(True)

        if cmd[-1:] != '\n' :
            cmd += '\n'
        cmd += self.exitcodeline
        self.process.stdin.write(cmd)
        self.process.stdin.flush()
        returnvals = self._read(polltime, timeout)
        if raiseerror and returnvals['exitcode'] != 0 :
            msg = '''{module}.{cls} environment with args:
{args}
init output:
{initoutput}
failed to execute command:
{cmd}
giving output:
{output}'''.format(module = self.__module__,
                   cls = self.__class__.__name__,
                   args = pprint.pformat(self.args),
                   initoutput = pprint.pformat(self.initoutput),
                   cmd = cmd,
                   output = pprint.pformat(returnvals))
            raise Exception(msg)
        return returnvals 

    def eval_python(self, cmd, objnames = None, evalobjects = True, 
                    polltime = 10, timeout = None, raiseerror = False) :
        if objnames :
            if cmd[-1:] != '\n' :
                cmd += '\n'
            cmd += 'print "__PYOBJECTS__", repr(dict('
            if evalobjects :
                cmd += ', '.join([name + ' = ' + name for name in objnames])
            else :
                cmd += ', '.join([name + ' = repr(' + name + ')' for name in objnames])
            cmd += '))\n'
        # Writing the cmd to a tempfile seems to be the safest way to retain the correct
        # quotation marks, rather than using python -c.
        flag, fname = tempfile.mkstemp()
        with open(fname, 'w') as tmpfile :
            tmpfile.write(cmd)
        try :
            returnvals = self.eval('python ' + fname, polltime, timeout, raiseerror)
        except Exception as excpt :
            msg = excpt.message
            msg += '\nCommand written to file ' + fname + ':\n' + cmd
            os.remove(fname)
            raise Exception(msg)
        os.remove(fname)
        if objnames :
            if returnvals['exitcode'] == 0 :
                lastline = filter(lambda line : '__PYOBJECTS__' in line, 
                                  returnvals['stdout'].split('\n'))[-1]
                returnvals['objects'] = eval(lastline[len('__PYOBJECTS__'):])
            else :
                returnvals['objects'] = None
        return returnvals

class LHCbEnv(Shell) :

    def __init__(self, env, version = 'latest', platform = None, shell = 'bash',
                 exitcodeline = 'echo "*_*_*_* EXITCODE: $?"\n',
                 exittest = '*_*_*_* EXITCODE: ',
                 getexitcode = lambda line : int(line.rstrip('\n').split()[-1]),
                 inittimeout = 600) :
        # Probably more options could be considered here. 
        args = ['lb-run']
        if platform :
            args += ['-c', platform]
        args += [env + '/' + version]
        args += [shell]
        Shell.__init__(self, args, exitcodeline, exittest, getexitcode, inittimeout)

lhcbenvs = {}
def get_lhcb_env(env, version = 'latest', platform = None, **kwargs) :
    global lhcbenvs
    key = env
    if version :
        key += '_' + version
    if platform :
        key += '_' + platform

    if not key in lhcbenvs :
        lhcbenvs[key] = LHCbEnv(env, version, platform, **kwargs)
    return lhcbenvs[key]

def get_stripping_env(version, **kwargs) :
    ver, platform = get_stripping_dv_version(version)
    return get_lhcb_env('DaVinci', version = ver, platform = platform, **kwargs)

if __name__ == '__main__' :
    
    diracEnv = get_lhcb_env('LHCbDirac')
    stdout, stderr = diracEnv.eval('dirac-version', 2e3)
    print 'stdout'
    print stdout
    print 'stderr'
    print stderr

    # For some reason python shells don't work. 
    # diracPythonEnv = LHCbEnv('LHCbDirac', 'python')
    # stdoutpy, stderrpy = diracPythonEnv.eval('print "spam"')
    # print 'stdoutpy'
    # print stdoutpy
    # print 'stderrpy'
    # print stderrpy

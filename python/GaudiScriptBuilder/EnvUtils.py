'''Utilities to help manage the various environments required in the LHCb software.'''

import subprocess, select, timeit, exceptions, pprint

strippingDVVersions = {'stripping21' : 'v36r1p3',
                       'stripping20' : 'v32r2p1',
                       'stripping20r1' : 'v32r2p3'}

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
    return None

class Shell(object) :
    __slots__ = ('args', 'process', 'stdoutpoller', 'stderrpoller', 'exitcodeline', 
                 'exittest', 'getexitcode', 'initoutput')
    
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
        self.process = subprocess.Popen(args, stdout = subprocess.PIPE, 
                                        stderr = subprocess.PIPE, stdin = subprocess.PIPE, env = env)
        self.stdoutpoller = select.poll()
        self.stdoutpoller.register(self.process.stdout.fileno(), select.POLLIN)
        self.stderrpoller = select.poll()
        self.stderrpoller.register(self.process.stderr.fileno(), select.POLLIN)

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
            for line in self.process.stdout :
                stdout += line
                if self.exittest(line) :
                    exitcode = self.getexitcode(line)
            stderr = self.process.stderr.read()
            self.process.stdout.close()
            self.process.stderr.close()
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
            line = self.process.stdout.readline()
            if self.exittest(line) :
                exitcode = self.getexitcode(line)
                break
            stdout += line
        # Read stderr til there's nothing left to read. 
        while self.stderrpoller.poll(0) and testtimeout() :
            stderr += self.process.stderr.readline()
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
            cmd += 'print repr(dict(' \
                + ', '.join([name + ' = ' + name for name in objnames])\
                + '))\n'
        cmd = 'python -c \'' + cmd + '\''
        returnvals = self.eval(cmd, polltime, timeout, raiseerror)
        if objnames :
            if returnvals['exitcode'] == 0 :
                lastline = filter(None, returnvals['stdout'].split('\n'))[-1]
                if evalobjects :
                    returnvals['objects'] = eval(lastline)
                else :
                    returnvals['objects'] = lastline
            else :
                returnvals['objects'] = None
        return returnvals

class LHCbEnv(Shell) :
    lbloginscript = '/afs/cern.ch/lhcb/software/releases/LBSCRIPTS/prod/InstallArea/scripts/LbLogin.sh'

    def __init__(self, env, version = None, platform = None, shell = 'bash',
                 exitcodeline = 'echo "*_*_*_* EXITCODE: $?"\n',
                 exittest = '*_*_*_* EXITCODE: ',
                 getexitcode = lambda line : int(line.rstrip('\n').split()[-1]),
                 inittimeout = None) :
        # Probably more options could be considered here. 
        args = ['lb-run']
        if platform :
            args += ['-c', platform]
        args += [env]
        if version :
            args += [version]
        args += [shell]
        Shell.__init__(self, args, exitcodeline, exittest, getexitcode, inittimeout)

lhcbenvs = {}
def get_lhcb_env(env, version = None, platform = None, **kwargs) :
    global lhcbenvs
    key = env
    if version :
        key += '_' + version
    if platform :
        key += '_' + platform

    if not key in lhcbenvs :
        lhcbenvs[key] = LHCbEnv(env, version, platform, **kwargs)
    return lhcbenvs[key]

def get_stripping_env(version, platform = None, **kwargs) :
    return get_lhcb_env('DaVinci', get_stripping_dv_version(version), platform, **kwargs)

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

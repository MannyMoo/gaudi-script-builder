'''Utilities to help manage the various environments required in the LHCb software.'''

import subprocess, select

class Shell(object) :
    __slots__ = ('args', 'process', 'stdoutpoller', 'stderrpoller')
    
    def __init__(self, args, env = None) :
        if isinstance(args, str) :
            args = [args]
        self.args = args
        self.process = subprocess.Popen(args, stdout = subprocess.PIPE, 
                                        stderr = subprocess.PIPE, stdin = subprocess.PIPE, env = env)
        self.stdoutpoller = select.poll()
        self.stdoutpoller.register(self.process.stdout.fileno(), select.POLLIN)
        self.stderrpoller = select.poll()
        self.stderrpoller.register(self.process.stderr.fileno(), select.POLLIN)

    def is_alive(self, raiseError = False) :
        if self.process.poll() :
            if raiseError :
                raise RuntimeError('The shell with args ' + repr(self.args) + 
                                   ', pid ' + str(self.process.pid) 
                                   + ', has died!') 
            return False
        return True

    def read(self, pollTime = 500, maxTries = 1, lineTime = 0) :

        if not self.is_alive() :
            stdout = self.process.stdout.read()
            stderr = self.process.stderr.read()
            self.process.stdout.close()
            self.process.stderr.close()
            return stdout, stderr
        
        stdout = stderr = ''
        iTry = 0 
        while iTry < maxTries :
            iTry += 1
            if self.stdoutpoller.poll(pollTime) or self.stderrpoller.poll(pollTime) :
                break
        while self.stdoutpoller.poll(lineTime) :
            stdout += self.process.stdout.readline()
        while self.stderrpoller.poll(lineTime) :
            stderr += self.process.stderr.readline()
        return stdout, stderr

    def eval(self, cmd, pollTime = 500, maxTries = 1) :

        self.is_alive(True)

        if not cmd :
            return None, None
        if cmd[-1:] != '\n' :
            cmd += '\n'
        self.process.stdin.write(cmd)
        self.process.stdin.flush()
        return self.read(pollTime, maxTries)

class LHCbEnv(Shell) :
    lbloginscript = '/afs/cern.ch/lhcb/software/releases/LBSCRIPTS/prod/InstallArea/scripts/LbLogin.sh'

    def __init__(self, env, shell = 'bash') :
        Shell.__init__(self, ['lb-run', env, shell])
        # Poll at 10s intervals up to 1 min.
        self.read(10e3, 6)

lhcbenvs = {}
def get_lhcb_env(env) :
    global lhcbenvs
    if not lhcbenvs.has_key(env) :
        lhcbenvs[env] = LHCbEnv(env)
    return lhcbenvs[env]


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

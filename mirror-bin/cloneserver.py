#!/usr/bin/env python

import sys
import select
import socket
import os
import re

ALLOW_UPDATE = ALLOW_WRITE = False
for arg in sys.argv[1:]:
    if arg=='--allow-write':
        ALLOW_WRITE = True
    elif arg=='--allow-update':
        ALLOW_UPDATE = True
    else:
        print "Unexpected argument",arg
        print "syntax: cloneserver.py [--allow-write] [--allow-update]"
        raise SystemExit(1)

if os.umask(022)!=022:
    print "Warning: umask was something other than 022.  Changed, so the cloned files will be readable."

MIRROR_ROOT='/home/sudomirror/public_html/mirror/'

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
sock.bind(("127.0.0.1",8082))
sock.listen(2)

def read_line(sock):
    ret = ''
    while 1:
        c = sock.recv(1)
        ret += c
        if c=='\n':
            return ret
        elif not c:
            return ret

def clean_path(url):
    segs = url.split('/')
    ret = []
    for seg in segs:
        if '..' in seg:
           return None
        if seg.startswith('.'):
           return None
        if not seg:
           return None
        if '\012' in seg:
           return None
        if re.match('^([-A-Z_a-z0-9.]+)$',seg):
           if seg.startswith('-'):
               return None
           ret.append(seg)
        else:
           return None
    if ret:
        return '/'.join(ret)

def log(proto, result, data):
    """
    Each log line consists of (protocol) (result) (data), separated by spaces.
    There may be spaces in the log data.
    
    Allowed results:
    cloned - successfully created the initial clone of (url in data)
    in-cache - We already have a clone, using it.
    ok - clone successful or already existed.
    trying - Client requested clone of (url in data).
    updated - Updated a repository (git or svn)

    Error:(details) - An error occurred.
    """
    if '\012' in data:
        raise Exception("Newlines in log data not allowed.")
    f = open(os.path.join(MIRROR_ROOT,'mirror.log'),'ab')
    f.write(' '.join((proto,result,data))+"\n")
    f.close()

def logged(proto, func, url):
    log(proto,'trying',url)
    ret = func(url)
    if ret:
        log(proto,'sent',url)
    else:
        log(proto,'Error:Fail',url)
    return ret

def wget_clone(url):
    if url.startswith('http://'):
        path = clean_path(url[7:])
        if not path:
            raise Exception("Could not sanitize URL")
        dest_path = os.path.join(MIRROR_ROOT,'http',path)
        try:
            file(dest_path,'rb').close()
            log('wget','in-cache',url)
            return True
        except:
            pass
        if not ALLOW_WRITE:
            print "Error: Cannot mirror."
            return False
        spath = dest_path.rsplit('/',1)
        try:
            os.makedirs(spath[0])
        except:
            os.listdir(spath[0])
    else:
        log('wget','Error:Protocol',url)
        raise Exception("Unexpected URL protocol")
    try:
        os.makedirs(os.path.join(MIRROR_ROOT,'tmp'))
    except:
        pass
    tmpfilename = os.path.join(MIRROR_ROOT,'tmp/wget.'+str(os.getpid())+'.tmp')
    if os.spawnvp(os.P_WAIT,'wget',['wget',url,'-O',tmpfilename]):
        print "An error occurred downloading",url
        try:
            os.unlink(tmpfilename)
        except Exception,e:
            print "Delete of",tmpfilename,"failed:",e
            pass
        log('wget','Error:download-failed',url)
        return False
    os.rename(tmpfilename,dest_path)
    return True

def svn_clone(url):
    proto, path = url.split('://',1)
    if proto not in ('http','svn'):
        print "Bad protocol in",url
        raise Exception("Unexpected protocol.\n")
    if proto == 'svn':
        protodir = 'svn'
    else:
        protodir = 'svn-'+proto
    path = clean_path(path)
    if not path:
        print "Could not clean path in",url
        raise Exception("Path cleaning error.")
    dest_path = os.path.join(MIRROR_ROOT,protodir,path)
    try:
        os.listdir(dest_path)
        exists = True
    except Exception,e:
        print "cloneserver.py: can't read",dest_path,'-',e
        exists = False
    if not exists:
        if ALLOW_WRITE:
            print "About to clone"
            retv = os.spawnvp(os.P_WAIT,'svn-clonerepo.pl',['svn-clonerepo.pl',url])
            if retv:
                print "FAIL",url,retv
                return False
            log('svn','cloned',url)
            return True
        print "Write disallowed, not mirroring."
        return False
    elif ALLOW_UPDATE:
        print "[cloneserver.py:] Subversion sync."
        retv = os.spawn(os.P_WAIT, 'svnsync', ['svnsync','sync','file://'+MIRROR_ROOT+protodir+'/'+path])
        if retv:
            print "[cloneserver.py:] svnsync of",url,'failed with return value',retv
            return False
        log('svn','updated',url)
        return True
    else:
        print "Cached."
        log('svn','in-cache',url)
        return True

def git_clone(url):
    proto, path = url.split('://',1)
    if proto not in ('git','http','https'):
        print "[cloneserver.py:] Bad protocol in",url
        raise Exception("Unexpected protocol for git clone.")
    path = clean_path(path)
    if not path:
        print "Could not clean path in",url
        raise Exception("Could not clean path.")
    if proto != 'git':
        proto_dir = 'git-'+proto
    else:
        proto_dir = proto
    dest_path = os.path.join(MIRROR_ROOT,proto_dir,path)
    try:
        os.listdir(dest_path)
        exists = True
    except:
        exists = False
    if not exists:
        if ALLOW_WRITE:
            print "About to create initial mirror of git repo."
            retv = os.spawnvp(os.P_WAIT,'git-clonerepo.pl',['git-clonerepo.pl',url])
            if retv:
                print "FAIL",url,retv
                return False
            log('git','cloned',url)
            return True
        print "Write disallowed, not mirroring."
        return False
    elif ALLOW_UPDATE:
        retv = os.spawnvp(os.P_WAIT,'git-syncrepo.sh',['git-syncrepo.sh',dest_path])
        if retv:
            log('git','Error:update-failed',url)
            print "Failed to sync remote:",dest_path,retv
            return False
        log('git','updated',url)
        return True
    else:
        log('git','in-cache',url)
        print "[cloneserver.py:] Using cached git repo."
    return True

def handle_req(sock):
    while 1:
        line = read_line(sock)
        if line.endswith("\012"):
            line = line[:-1]
        if line.endswith("\015"):
            line = line[:-1]
        if line.startswith('wget '):
            if logged('wget',wget_clone,line[5:]):
                sock.send("ok "+line[5:]+'\015')
            else:
                sock.send('fail\012')
            sock.close()
            return
        elif line.startswith('git '):
            if logged('git',git_clone,line[4:]):
                sock.send("ok "+line[4:]+'\015')
            else:
                sock.send('fail\012')
            sock.close()
            return
        elif line.startswith('svn '):
            if logged('svn',svn_clone,line[4:]):
                sock.send("ok "+line[4:]+'\015')
            else:
                sock.send('fail\012')
            sock.close()
            return
        else:
            sock.send('fail\012')
            sock.close()
            return

peer = sock.accept()
while peer:
    print "Connected",peer[1]
    URL = 'nil'
    HOST = 'nil'
    handle_req(peer[0])
    peer = sock.accept()

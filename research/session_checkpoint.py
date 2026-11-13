"""Private atomic checkpoint for a negotiated isolated-boot transport session."""
import json,os,tempfile
from pathlib import Path

def save(path,session,boot_id):
    path=Path(path)
    if path.is_symlink() or (path.exists() and path.stat().st_mode&0o077):
        raise ValueError('Private regular session checkpoint required')
    key=session['shared_key']
    if type(key) is not bytes or len(key)!=32:raise ValueError('Invalid transport key')
    if not 0<=session['sequence']<=65535:raise ValueError('Invalid sequence')
    payload=json.dumps(dict(boot_id=boot_id,shared_key=key.hex(),sequence=session['sequence'],expires=session['expires'])).encode()
    fd,temp=tempfile.mkstemp(prefix='.session-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(temp):os.unlink(temp)

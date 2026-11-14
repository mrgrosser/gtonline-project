"""Python2-compatible selection of the stable /tmp/go process, not fork helpers.

pidof returns newest matching processes first; the game forks short-lived go
children before exec. Only a unique top-level matching executable is accepted.
No attach, signal or writes. Ambiguity/missing process returns None.
"""
import os

def _stat(root,pid):
    with open(os.path.join(root,str(pid),'stat')) as f:text=f.read()
    start=text.find('(');end=text.rfind(')')
    if start<0 or end<=start:raise ValueError('Malformed proc stat')
    fields=text[end+2:].split()
    if len(fields)<20:raise ValueError('Short proc stat')
    return dict(pid=int(text[:start].strip()),comm=text[start+1:end],state=fields[0],ppid=int(fields[1]),start_ticks=int(fields[19]))

def game_process(proc_root='/proc',expected_executable='/tmp/go'):
    candidates={};parents={}
    try:entries=os.listdir(proc_root)
    except OSError:return None
    for entry in entries:
        if not entry.isdigit():continue
        try:
            row=_stat(proc_root,int(entry));parents[row['pid']]=row['ppid']
            if row['comm']!='go' or row['state'] in ('Z','X'):continue
            executable=os.readlink(os.path.join(proc_root,entry,'exe'))
            if executable.endswith(' (deleted)'):executable=executable[:-10]
            if executable!=expected_executable:continue
            candidates[row['pid']]=row
        except (IOError,OSError,ValueError):continue
    roots=[]
    for pid,row in candidates.items():
        parent=row['ppid'];seen=set([pid]);child=False
        while parent>0 and parent not in seen:
            if parent in candidates:child=True;break
            seen.add(parent);parent=parents.get(parent,0)
        if not child:roots.append(row)
    if len(roots)!=1:return None
    chosen=roots[0]
    # Recheck identity after the scan, refusing exit/PID-reuse races.
    try:
        now=_stat(proc_root,chosen['pid'])
        if now['state'] in ('Z','X') or any(now[k]!=chosen[k] for k in ('pid','ppid','comm','start_ticks')):return None
        executable=os.readlink(os.path.join(proc_root,str(chosen['pid']),'exe'))
        if executable.endswith(' (deleted)'):executable=executable[:-10]
        if executable!=expected_executable:return None
    except (IOError,OSError,ValueError):return None
    return chosen

def game_pid(proc_root='/proc'):
    selected=game_process(proc_root)
    return None if selected is None else selected['pid']

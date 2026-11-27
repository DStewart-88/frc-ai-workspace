"""Shot detector with the level-relative fix (Nov 10, 2026).

Same as detect() in shot_counter.py, except the overspeed and below-setpoint rules are measured
against the flywheel's own running level (median tracking error over the last 1 s while armed,
floored at 0) instead of the setpoint. Needed because since April the flywheel runs ~1.4 rps above
its setpoint while feeding, so the October rule rejected most real dips (BOB Q7: 72 -> 271 shots;
Newton Q23: 253 -> 258). See the Pitwall scoring-module framing doc.
"""
from collections import deque
import statistics as st
DIP, REARM, LOCK, VMIN, OVER, BELOW, HANG, WIN, BASE = 1.5, 0.75, 0.10, 10.0, 2.0, 0.75, 0.30, 0.20, 1.0
def detect2(t, v, sp, on, gate, base_win=BASE, over=OVER, below=BELOW):
    """October detector, but the overspeed and below-setpoint rules use the flywheel's own running
    level (median tracking error over the last base_win s while armed) instead of the setpoint."""
    ev=[]; buf=deque(); hist=deque(); in_dip=False; trough=0; last=-1e9; lastg=-1e9
    for i in range(len(t)):
        if gate[i]: lastg=t[i]
        armed = on[i] and (t[i]-lastg)<=HANG and v[i]>VMIN
        if not armed: buf.clear(); in_dip=False; hist.clear(); continue
        e=v[i]-sp[i]
        while hist and hist[0][0]<t[i]-base_win: hist.popleft()
        lvl = st.median([x[1] for x in hist]) if len(hist)>=5 else 0.0
        lvl = max(0.0, lvl)   # never looser than the October rule when the flywheel runs low
        hist.append((t[i],e))
        if in_dip:
            trough=min(trough,e)
            if e-trough>=REARM: in_dip=False; buf.clear()
            else: continue
        while buf and buf[0][0]<t[i]-WIN: buf.popleft()
        peak=max([x[1] for x in buf]+[e]); buf.append((t[i],e))
        if peak-e>=DIP and peak<=lvl+over and e<=lvl-below and t[i]-last>=LOCK:
            ev.append(i); last=t[i]; in_dip=True; trough=e
    return ev

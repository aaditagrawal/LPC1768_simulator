import time
import pytest
from pathlib import Path

from simulator.runtime import Runtime, CATALOG, ROOT
from simulator.server import create_app
from simulator.compiler import CompileError, Compiler


@pytest.fixture
def rt():
    r=Runtime(start_worker=False)
    yield r
    r.close()


@pytest.fixture
def client(rt):
    return create_app(rt).test_client()


def test_failed_compile_or_hex_preserves_machine(rt):
    old = rt.machine
    with pytest.raises(CompileError):
        rt.compile('#include <LPC17xx.h>\nint main( {')
    assert rt.machine is old
    with pytest.raises(ValueError):
        rt.load('bad')
    assert rt.machine is old


def test_connections_are_not_automatically_fixed(rt):
    before=rt.snapshot()
    check=rt.check('lab9_keypad')
    assert not check['ok']
    assert rt.snapshot()['cables']==before['cables']==[]
    assert rt.snapshot()['jumpers']==before['jumpers']


def test_reset_retains_physical_configuration(rt):
    rt.physical(dict(action='connect',a='CNA',b='CNA1'))
    rt.physical(dict(action='jumper',name='JP4',value='1-2'))
    rt.physical(dict(action='pot',channel=5,voltage=2.4))
    rt.control('reset')
    s=rt.snapshot()
    assert s['cables']==[['CNA','CNA1']]
    assert s['jumpers']['JP4']=='1-2'
    assert s['pots'][5]==2.4


def test_only_one_cable_per_header_and_wrong_wiring_is_real(rt):
    rt.physical(dict(action='connect',a='CNC',b='CNA1'))
    with pytest.raises(ValueError):
        rt.physical(dict(action='connect',a='CNA',b='CNA1'))
    result=Compiler().compile('''#include <LPC17xx.h>
      int main(void) {LPC_GPIO0->FIODIR=0xFF0;LPC_GPIO0->FIOPIN=0xFF0;while(1) {}}''')
    rt.load(result.hex)
    rt.machine.run(10000)
    assert not any(rt.snapshot()['leds'])
    rt.physical(dict(action='disconnect',header='CNC'))
    rt.physical(dict(action='connect',a='CNA',b='CNA1'))
    assert all(rt.snapshot()['leds'])


@pytest.mark.parametrize('path,data',[
    ('/api/firmware',{'hex':'corrupt'}),
    ('/api/compile',{'source':123}),
    ('/api/control',{'action':'run'}),
    ('/api/physical',{'action':'key','key':16,'pressed':True}),
    ('/api/physical',{'action':'pot','channel':4,'voltage':4}),
    ('/api/physical',{'action':'jumper','name':'JP4','value':'closed'}),
    ('/api/physical',{'action':'connect','a':[],'b':'CNA1'}),
])
def test_api_validation(client,path,data):
    r=client.post(path,json=data)
    assert r.status_code==400
    assert r.json['error']


def test_api_source_and_same_origin(client):
    assert len(client.get('/api/info').json['exercises'])==18
    assert '#include <LPC17xx.h>' in client.get('/api/examples/lab7_sequence').json['source']
    assert client.get('/api/state',headers={'Origin':'https://example.com'}).status_code==403
    assert client.get('/api/state',headers={'Host':'example.com'}).status_code==403


def test_worker_pause_resume_and_reset():
    rt=Runtime()
    try:
        rt.load((ROOT/'examples/idle.hex').read_text())
        rt.control('run')
        deadline=time.monotonic()+3
        while rt.snapshot()['ticks']==0 and time.monotonic()<deadline:
            time.sleep(.01)
        assert rt.snapshot()['ticks']>0
        rt.control('pause')
        tick=rt.snapshot()['ticks']
        time.sleep(.05)
        assert rt.snapshot()['ticks']==tick
        rt.control('resume')
        deadline=time.monotonic()+3
        while rt.snapshot()['ticks']==tick and time.monotonic()<deadline:
            time.sleep(.01)
        assert rt.snapshot()['ticks']>tick
        rt.control('stop')
        assert rt.snapshot()['ticks']==0
    finally:
        rt.close()

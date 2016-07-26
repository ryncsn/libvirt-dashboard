#!/bin/env python
import requests

DASHBOARD = 'http://127.0.0.1:5000/api/'


def debug_post(url, json={}):
    res = requests.post(url, json=json)
    print "REQ:" + str(url)
    print "DATA:" + str(json)
    print "GOT:" + str(res)
    print "IN JSON:" + str(res.json())
    return res

res = debug_post(DASHBOARD + 'run/', json={
    "arch": "x86",
    "build": "2.0.1",
    "component": "libvirt",
    "date": "2016-07-18T17:02:28.798848",
    "description": "debuging",
    "framework": "libvirt-autotest",
    "name": "libvirt-RHEL-7.3-runtest-x86_64-function-migration",
    "polarion_id": "Libvirt-Auto-Record-1",
    "project": "VIRTTP",
    "type": "function",
    "version": "7.3"
})

run_id = res.json()['id']

for case in [
        "a.b.c.d",
        "a.b.c.4.e",
        "a.b.c.3.e",
        "a.b.c.2.e",
        "a.b.c.1.e",
        "a.b.c.4.f",
        "a.b.c.3.f",
        "a.b.c.2.f",
        "a.b.c.1.f"]:

    debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
        "output": "WOW",
        "time": "123.456",
        "case": case,
    })


debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "failure": "Failure 1",
    "case": "1.1.1"
})

debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "failure": "Failure 2",
    "case": "1.2.1"
})

debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "failure": "Failure 2",
    "case": "1.2.2"
})

debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "failure": "Failure 2",
    "case": "1.2.3"
})

debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "failure": "Failure 2",
    "case": "1.2.4"
})

debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "failure": "Failure 3",
    "case": "1.3.1"
})

debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "failure": "Failure 3",
    "case": "1.3.2"
})

debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "failure": "Failure 3",
    "case": "1.3.3"
})

debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "case": "1.3.4"
})

debug_post(DASHBOARD + 'run/' + str(run_id) + "/", json={
    "output": "WOW",
    "time": "123.456",
    "failure": "Failure UnKnown",
    "case": "1.4.1"
})

#!/usr/bin/python3

import json
import socket
import threading
import requests


from wakeonlan import send_magic_packet


class Kodi_API:
    def __init__(self, host, port=8080, user="", password=""):
        self.host = host

        self.ip = socket.gethostbyname(host)
        self.mac = get_mac_address(ip=self.ip)

        print("IP", self.mac)
        self.url = "http://%s:%s@%s:%s/jsonrpc" % (user, password, self.ip, port)
        self.session = requests.Session()

    def _send_command(self, *args, as_thread=True, **kwargs):
        print("_send_command", kwargs, as_thread)
        if as_thread:
            t = threading.Thread(target=self._send, args=args, kwargs=kwargs)
            t.start()
        else:
            try:
                ret = self._send(*args, **kwargs)
                print("_send_command_ret", kwargs, ret)
                return ret
            except Exception as e:
                print(e)
                return None

    def _send(self, params={}, method="Input.ExecuteAction"):
        data = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        try:
            ret = self.session.post(
                self.url,
                data=json.dumps(data),
                headers={"Content-type": "application/json"},
                timeout=0.2,
            )
        except Exception as e:
            print(e)
            return None
        print(repr(ret.text))
        return ret.json()["result"]

    def up(self):
        self._send_command(params={"action": "up"})

    def down(self):
        self._send_command(params={"action": "down"})

    def left(self):
        # ~ self._send_command(params={"action":"left"})
        self._send_command(
            method="Input.ButtonEvent",
            params={"button": "left", "keymap": "KB", "holdtime": 0},
        )

    def right(self):
        # ~ self._send_command(params={"action":"right"})
        self._send_command(
            method="Input.ButtonEvent",
            params={"button": "right", "keymap": "KB", "holdtime": 0},
        )

    def back(self):
        self._send_command(params={"action": "back"})

    def info(self):
        self._send_command(params={"action": "info"})

    def volup(self):
        self._send_command(
            method="Application.SetVolume", params={"volume": "increment"}
        )

    def voldown(self):
        self._send_command(
            method="Application.SetVolume", params={"volume": "decrement"}
        )

    def get_vol(self):
        ret = self._send_command(
            method="Application.GetProperties",
            params={"properties": ["volume"]},
            as_thread=False,
        )
        return ret["volume"]

    def ping(self):
        data = self._send_command(method="JSONRPC.Ping", params={}, as_thread=False)
        if data == None:
            return False
        if data == "pong":
            return True
        else:
            return False

    def home(self):
        self._send_command(method="Input.Home", params={})

    def osd(self):
        self._send_command(method="Input.showOSD", params={})

    def select(self):
        # ~ if self.get_top_window()["id"] == 12005:
        # ~ self.osd()
        # ~ else:
        # ~ self._send_command(params={"action":"select"})

        self._send_command(
            method="Input.ButtonEvent",
            params={"button": "enter", "keymap": "KB", "holdtime": 0},
        )

    def get_active(self):

        ret = self._send_command(
            method="Player.GetActivePlayers", params={}, as_thread=False
        )
        print(ret)
        if len(ret) == 0:
            return None

        pid = ret[0]["playerid"]
        ptype = ret[0]["type"]

        params = {"properties": ["title", "thumbnail"], "playerid": pid}
        ret = self._send_command(
            method="Player.GetItem", params=params, as_thread=False
        )
        ret["item"]["type"] = ptype
        return ret["item"]

    def get_top_window(self):
        ret = self._send_command(
            method="GUI.GetProperties",
            params={"properties": ["currentwindow"]},
            as_thread=False,
        )
        return ret["currentwindow"]

    def get_players(self):

        ret = self._send_command(
            method="Player.GetActivePlayers", params={}, as_thread=False
        )
        outlist = []
        if ret:
            for e in ret:
                outlist.append(e["playerid"])

        return outlist

    def reboot(self):
        self._send_command(method="System.Reboot")

    def shutdown(self):
        self._send_command(method="System.Shutdown")

    def suspend(self):
        self._send_command(method="System.Suspend")

    def hibernate(self):
        self._send_command(method="System.Hibernate")

    def eject(self):
        self._send_command(method="System.EjectOpticalDrive")

    def wol(self):
        send_magic_packet(self.mac)

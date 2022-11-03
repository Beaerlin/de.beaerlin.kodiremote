#!/usr/bin/python3

import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
# ~ gi.require_version('Polkit', '1.0')
from gi.repository import Gtk, GLib, Adw, GObject, Gio  # Polkit


from pydbus import SessionBus

BUS_NAME = "org.sigxcpu.Feedback"
try:
    bus = SessionBus()
    feedbackd = bus.get(BUS_NAME)
except:
    feedbackd = None

#
# class Stack(Gtk.Stack):
#     """Wrapper for Gtk.Stack with  with a StackSwitcher"""
#
#     def __init__(self):
#         super(Stack, self).__init__()
#         self.switcher = Gtk.StackSwitcher()
#         self.switcher.set_stack(self)
#         self._pages = {}
#
#     def add_page(self, name, title, widget):
#         page = self.add_child(widget)
#         page.set_name(name)
#         page.set_title(title)
#         self._pages[name] = page
#         return page


import threading
import os
import time
import requests
import tempfile
from settings import Settings
from kodi_api import Kodi_API
from functools import partial
import urllib
from urllib import parse
import scan

VERSION = "0.0.1"

if os.path.isdir("images"):
    imagepath = "images"
else:
    imagepath = "/app/images"
configpath = os.path.join(
    os.path.expanduser("~"), ".var/app/", "de.beaerlin.kodiremote", "config"
)
if not os.path.isdir(configpath):
    os.makedirs(configpath)
configfile = os.path.join(configpath, "remote.cfg")


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        app = kwargs["application"]
        super().__init__(*args, **kwargs)
        self.closed = False
        self.set_default_size(720 / 2, 1440 / 2)
        self.connect("close-request", self._on_close)
        self.timeouts = {}
        self._build_header()
        self.mainbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.mainbox.append(Gtk.Label(label=" "))
        # ~ self.mainbox.modify_bg(Gtk.StateType.NORMAL, Gdk.RGBA(0.5,0.0,0.0,0.5));

        self.kodi_list = []
        self.kodi_selected = 0
        # ~ self.set_decorated(False)

        topgrid = Gtk.Grid(column_spacing=1, row_spacing=1)
        topgrid.set_hexpand(True)
        topgrid.set_vexpand(True)

        self.kodi_store = Gtk.ListStore(str)

        self.kcombo = Gtk.ComboBox.new_with_model(self.kodi_store)

        renderer_text = Gtk.CellRendererText()
        self.kcombo.pack_start(renderer_text, True)
        self.kcombo.add_attribute(renderer_text, "markup", 0)
        self.kcombo.set_hexpand(True)

        # ~ gesture = Gtk.GestureClick.new()
        # ~ gesture.connect("pressed", partial(self.remove_server))
        # ~ btnminus = Gtk.Image.new_from_file(os.path.join(imagepath,"png/server-remove.png"))
        # ~ btnminus.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", partial(self.manage_server))
        btnplus = Gtk.Image.new_from_file(os.path.join(imagepath, "png/servers.png"))
        btnplus.add_controller(gesture)

        topgrid.attach(self.kcombo, 0, 0, 100, 50)
        # ~ topgrid.attach_next_to(btnminus, self.kcombo, Gtk.PositionType.LEFT, 40, 50)
        topgrid.attach_next_to(btnplus, self.kcombo, Gtk.PositionType.LEFT, 80, 50)

        status = Gtk.Label()
        status.set_markup("<span font='10' face='Georgia'>Offline</span>")
        status.set_wrap(True)
        status.set_property("height-request", 60)

        topgrid.attach(status, -50, 100, 180, 60)
        self.status = status

        self.mainbox.append(topgrid)

        self.mainbox.append(self._build_control())

        downgrid = Gtk.Grid(column_homogeneous=True, row_spacing=8)

        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", partial(self._button_press, "volup", True))
        gesture.connect("released", partial(self._button_press, "volup", False))
        btnplus = Gtk.Image.new_from_file(
            os.path.join(imagepath, "png/volume-plus.png")
        )
        btnplus.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", partial(self._button_press, "voldown", True))
        gesture.connect("released", partial(self._button_press, "voldown", False))
        btnminus = Gtk.Image.new_from_file(
            os.path.join(imagepath, "png/volume-minus.png")
        )
        btnminus.add_controller(gesture)

        downgrid.attach(btnplus, 0, 0, 10, 10)
        downgrid.attach_next_to(btnminus, btnplus, Gtk.PositionType.BOTTOM, 10, 10)

        self.mainbox.append(downgrid)

        self.stack = Stack()
        setupbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        setupbox.set_vexpand(True)

        setupbox.append(Gtk.Label(label=""))
        h1 = Gtk.Label(label="Delete Media Player")
        h1.set_markup(f"<span font='15' face='Georgia'>Delete Media Player</span>")
        setupbox.append(h1)

        self.del_box = Gtk.ListBox()
        self.del_box.set_vexpand("True")
        setupbox.append(self.del_box)

        setupbox.append(Gtk.Label(label=""))
        h1 = Gtk.Label(label="Add Media Player")
        h1.set_markup(f"<span font='15' face='Georgia'>Add Media Player</span>")
        setupbox.append(h1)

        setupbox.append(Gtk.Label(label=""))

        setupbox.append(Gtk.Label(label="Name:"))
        self.add_name = Gtk.Entry()
        setupbox.append(self.add_name)

        setupbox.append(Gtk.Label(label="Host:"))
        self.add_host = Gtk.Entry()
        setupbox.append(self.add_host)

        setupbox.append(Gtk.Label(label="Port:"))
        self.add_port = Gtk.Entry()
        self.add_port.set_text("8080")
        setupbox.append(self.add_port)

        setupbox.append(Gtk.Label(label="User:"))
        self.add_user = Gtk.Entry()
        setupbox.append(self.add_user)

        setupbox.append(Gtk.Label(label="Password:"))
        self.add_pass = Gtk.Entry()
        setupbox.append(self.add_pass)

        setupbox.append(Gtk.Label(label=""))

        setupbox.append(Gtk.Label(label="Found on Network:"))
        self.kodi_box = Gtk.ListBox()
        self.kodi_box.set_vexpand("True")
        setupbox.append(self.kodi_box)

        self.add_error = Gtk.Label(label="")
        setupbox.append(self.add_error)

        savebox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        savebox.set_valign(3)
        save = Gtk.Button(label="Save")
        save.set_size_request(-1, 60)
        save.connect("clicked", self.add_save)
        save.set_hexpand(True)
        self.add_cancel = Gtk.Button(label="Cancel")
        self.add_cancel.connect("clicked", self.back)
        savebox.append(self.add_cancel)
        savebox.append(save)
        setupbox.append(savebox)

        rembox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.dellabel = Gtk.Label(label="Delete: ")
        self.dellabel.set_vexpand(True)
        rembox.append(self.dellabel)

        delbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        delbox.set_valign(3)
        delete = Gtk.Button(label="Delete")
        delete.connect("clicked", self.del_server)
        delete.set_hexpand(True)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", self.back)
        cancel.set_size_request(-1, 60)
        delbox.append(cancel)
        delbox.append(delete)
        rembox.append(delbox)

        self.stack.add_page("Main", "Mainbox", self.mainbox)
        self.stack.add_page("Add", "Add Kodi", setupbox)
        self.stack.add_page("Del", "Del Kodi", rembox)

        self.set_child(self.stack)
        self.load()

        t = threading.Thread(target=self.update)
        t.start()

    def back(self, *args):

        self.stack.set_visible_child_name("Main")
        self.popover.set_sensitive(True)

    def add_save(self, *args):
        print("Save")
        name = self.add_name.get_text()
        host = self.add_host.get_text()
        port = self.add_port.get_text()
        user = self.add_user.get_text()
        password = self.add_pass.get_text()
        c = Kodi_API(host, port, user, password)

        if name == "":
            self.add_error.set_text("Please enter a name")
            return

        if host == "":
            self.add_error.set_text("Please enter a host")
            return

        try:
            port = int(port)
        except:
            self.add_error.set_text("Port is no Integer")
            return

        if not c.ping():
            self.add_error.set_text("Connection Error")
            return

        s = Settings(configfile)
        sect = s.get_sections()
        if name in sect:
            self.add_error.set_text("Name exists already")
            return

        s.set(name, "host", host)
        s.set(name, "port", port)
        s.set(name, "user", user)
        s.set(name, "password", password)
        s.set(name, "mac", c.mac)

        self.load()
        self.back()

    def manage_server(self, *args):
        print("manage_server")

        s = Settings(configfile)
        sect = s.get_sections()

        for ch in list(self.del_box):
            self.del_box.remove(ch)

        for kodi in sect:
            listboxrow = Gtk.ListBoxRow()
            button = Gtk.Button(label=kodi)
            button.connect("clicked", partial(self.remove_server, kodi))
            listboxrow.set_child(button)
            self.del_box.append(listboxrow)

        self.popover.set_sensitive(False)
        self.add_error.set_text("")
        self.stack.set_visible_child_name("Add")

        s = Settings(configfile)
        sect = s.get_sections()
        if len(sect) < 1:
            self.add_cancel.set_sensitive(False)
        else:
            self.add_cancel.set_sensitive(True)

        # ~ help(self.kodi_box)

        t = threading.Thread(target=self._search_thread)
        t.start()

    def _search_thread(self):

        print("scan")

        for ch in list(self.kodi_box):
            self.kodi_box.remove(ch)

        kodis = zconf.scan_for_kodi()
        for kodi in kodis:
            listboxrow = Gtk.ListBoxRow()

            button = Gtk.Button(label=kodi["name"])
            button.connect("clicked", partial(self.set_preset, kodi))
            listboxrow.set_child(button)

            self.kodi_box.append(listboxrow)

    def set_preset(self, kodi, *args):
        self.add_name.set_text(kodi["name"])
        self.add_host.set_text(kodi["host"])
        self.add_port.set_text(str(kodi["port"]))

    def del_server(self, *args):

        s = Settings(configfile)
        s.del_section(self.to_del)
        self.back()
        self.load()

    def remove_server(self, kodi, *args):
        self.to_del = kodi
        self.popover.set_sensitive(False)
        self.dellabel.set_markup(
            f"<span font='15' face='Georgia'>Delete:\n{kodi}</span>"
        )
        self.stack.set_visible_child_name("Del")

    def update(self):

        while not self.closed:

            time.sleep(1)
            try:
                c = self.get_connection()
            except Exception as e:
                self.status.set_markup(
                    f"<span font='10' face='Georgia'>Error Loading Config {e}</span>"
                )
                continue

            if not c.ping():
                self.status.set_markup("<span font='10' face='Georgia'>Offline</span>")
                continue

            try:
                act = c.get_active()
            except:
                self.status.set_markup("<span font='10' face='Georgia'>Offline</span>")
                continue
            if act == None:
                self.status.set_markup("<span font='10' face='Georgia'>Stopped</span>")
                continue
            else:
                # ~ self.status.set_text('Playing: %s'%act['label'])
                self.status.set_markup(
                    f"<span font='10' face='Georgia'>Playing: {act['label']}</span>"
                )

            if act["thumbnail"].startswith("http"):
                uri = act["thumbnail"]
            else:
                uri = " http://htpcw.mgm:8080/image/%s" % urllib.parse.quote(
                    act["thumbnail"], safe=""
                )

            thumb = requests.get(uri)
            tmp = tempfile.NamedTemporaryFile(suffix=".jpg").name
            with open(tmp, "wb") as f:
                f.write(thumb.content)
            image = Gtk.Image.new_from_file("/path/to/my_file.png")
            os.remove(tmp)

    def _build_header(self):
        self.header_bar = Gtk.HeaderBar()
        self.header_bar.set_show_title_buttons(True)

        self.popover = Gtk.Popover()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        button = Gtk.Button(label="Suspend")
        button.connect("clicked", partial(self._send, "suspend"))
        vbox.append(button)
        button = Gtk.Button(label="WakeUp")
        button.connect("clicked", partial(self._send, "wol"))
        vbox.append(button)
        button = Gtk.Button(label="Shutdown")
        button.connect("clicked", partial(self._send, "shutdown"))
        vbox.append(button)
        button = Gtk.Button(label="Reboot")
        button.connect("clicked", partial(self._send, "reboot"))
        vbox.append(button)
        button = Gtk.Button(label="Eject Disc")
        button.connect("clicked", partial(self._send, "eject"))
        vbox.append(button)

        self.popover.set_child(vbox)

        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_icon_name("view-more-symbolic")
        self.menu_button.set_popover(self.popover)
        self.header_bar.pack_end(self.menu_button)

        self.set_titlebar(self.header_bar)

    def _build_control(self):

        presspeed = 10

        gesture = Gtk.GestureClick.new()
        gesture.connect(
            "pressed", partial(self._button_press, "up", True, speed=presspeed)
        )
        gesture.connect("released", partial(self._button_press, "up", False))
        btnup = Gtk.Image.new_from_file(
            os.path.join(imagepath, "png/arrow-up-bold-box.png")
        )
        btnup.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect(
            "pressed", partial(self._button_press, "down", True, speed=presspeed)
        )
        gesture.connect("released", partial(self._button_press, "down", False))
        btndown = Gtk.Image.new_from_file(
            os.path.join(imagepath, "png/arrow-down-bold-box.png")
        )
        btndown.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect(
            "pressed", partial(self._button_press, "left", True, speed=presspeed)
        )
        gesture.connect("released", partial(self._button_press, "left", False))
        btnleft = Gtk.Image.new_from_file(
            os.path.join(imagepath, "png/arrow-left-bold-box.png")
        )
        btnleft.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect(
            "pressed", partial(self._button_press, "right", True, speed=presspeed)
        )
        gesture.connect("released", partial(self._button_press, "right", False))
        btnright = Gtk.Image.new_from_file(
            os.path.join(imagepath, "png/arrow-right-bold-box.png")
        )
        btnright.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", partial(self._send, "select"))
        btnselect = Gtk.Image.new_from_file(os.path.join(imagepath, "png/select.png"))
        btnselect.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", partial(self._send, "back"))
        btnback = Gtk.Image.new_from_file(os.path.join(imagepath, "png/back.png"))
        btnback.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", partial(self._send, "home"))
        btnhome = Gtk.Image.new_from_file(os.path.join(imagepath, "png/home.png"))
        btnhome.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", partial(self._send, "info"))
        btninfo = Gtk.Image.new_from_file(os.path.join(imagepath, "png/info.png"))
        btninfo.add_controller(gesture)

        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", partial(self._send, "osd"))
        btnosd = Gtk.Image.new_from_file(os.path.join(imagepath, "png/osd.png"))
        btnosd.add_controller(gesture)

        # ~ self.grid = Gtk.Grid(column_spacing=1,row_spacing=3)
        grid = Gtk.Grid(column_homogeneous=True, row_spacing=12)
        grid.set_row_homogeneous(True)

        grid.set_hexpand(True)
        # ~ self.grid.override_background_color(Gtk.StateFlags.NORMAL,Gdk.RGBA(0.0,0.0,0.0,0.5))

        grid.attach(btnselect, 0, 0, 10, 10)
        # ~ grid.attach(Gtk.Label(label=' '),31, 1, 1, 1)
        grid.attach_next_to(btndown, btnselect, Gtk.PositionType.BOTTOM, 10, 10)
        grid.attach_next_to(btnup, btnselect, Gtk.PositionType.TOP, 10, 10)
        grid.attach_next_to(btnright, btnselect, Gtk.PositionType.RIGHT, 10, 10)
        grid.attach_next_to(btnleft, btnselect, Gtk.PositionType.LEFT, 10, 10)
        grid.attach_next_to(btnhome, btnup, Gtk.PositionType.LEFT, 10, 10)
        grid.attach_next_to(btnosd, btnup, Gtk.PositionType.RIGHT, 10, 10)
        grid.attach_next_to(btnback, btndown, Gtk.PositionType.LEFT, 10, 10)
        grid.attach_next_to(btninfo, btndown, Gtk.PositionType.RIGHT, 10, 10)
        # ~ grid.attach_next_to(Gtk.Label(label=' '), btnright, Gtk.PositionType.RIGHT, 10, 1)

        return grid

    def _button_press(self, button, press, *args, speed=80, startonpress=True):
        if press:
            if feedbackd:
                # /usr/share/feedbackd/themes/pin64,pinephone.json
                feedbackd.TriggerFeedback("source", "button-pressed", [], -1)
            if startonpress:
                p = partial(self._send, button)
                p()
            time.sleep(0.3)
            timeout = speed
            self.timeouts[button] = GLib.timeout_add(timeout, p)
            if feedbackd:
                feedbackd.TriggerFeedback("source", "button-released", [], -1)
        else:
            GLib.source_remove(self.timeouts[button])
            self.timeouts[button] = 0

    def _send(self, command, *args):

        # ~ print('Send',command)
        try:
            c = self.get_connection()
            cmd = getattr(c, command)
            cmd()
        except Exception as e:
            print(e)
            pass

        return True

    def _on_close(self, app):
        self.closed = True

    def get_connection(self):
        num = self.kcombo.get_active()
        # ~ print(name)
        # ~ data = self.kodi_store[num]

        data = self.kodi_list[num]
        # ~ print('##########',data)
        c = Kodi_API(data["host"], data["port"], data["user"], data["password"])
        return c

    def load(self):

        self.kodi_store.clear()
        self.kodi_list = []

        s = Settings(configfile)
        sect = s.get_sections()

        if len(sect) < 1:
            print("addserver")
            self.manage_server()
            return

        for sec in sect:
            print(sec)
            k = {}
            k["name"] = sec
            k["host"] = s.get(sec, "host")
            k["port"] = int(s.get(sec, "port"))
            k["user"] = s.get(sec, "user")
            k["password"] = s.get(sec, "password")

            self.kodi_list.append(k)

        counter = 0

        for k in self.kodi_list:
            self.kodi_store.append(
                [f"<span font='13' face='Georgia'>{k['name']}</span>"]
            )

        self.kcombo.set_active(0)


class RemoteApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(
            application=app, title="Kodi Remote Control (%s)" % VERSION
        )
        self.win.set_icon_name("de.beaerlin.kodiremote")
        app.inhibit(self.win, Gtk.ApplicationInhibitFlags.SUSPEND, "Remote")
        app.inhibit(self.win, Gtk.ApplicationInhibitFlags.IDLE, "Remote")
        self.win.present()
        print("loaded")


if __name__ == "__main__":
    app = RemoteApp(application_id="de.beaerlin.kodiremote")
    app.run(sys.argv)
    print("exit")

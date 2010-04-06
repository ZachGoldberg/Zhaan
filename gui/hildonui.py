#!/usr/bin/env python
import gtk, hildon, gobject
from gi.repository import GUPnP, GUPnPAV, GObject

from gui.hildonplaylist import Playlist
from gui.zhaanui import ZhaanUI

class HildonZhaanUI(ZhaanUI):        

    def begin_progress_indicator(self):
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)

    def end_progress_indicator(self):
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
                           
    def update_renderer_status(self, device, state):
        if device.get_udn() == self.renderer_device.get_udn():
            device_state = ""
            if "pause" in state.lower():
                device_state = "Paused"
            elif "play" in state.lower():
                device_state = "Playing"
            elif "stop" in state.lower():
                device_state = "Stoppted"

            if device_state:
                self.device_state = device_state
                self.window.set_title("Zhaan - %s (%s)" % (device.get_model_name(),
                                                           device_state))

    def renderer_changed(self, box, index=None):
        super(HildonZhaanUI, self).renderer_changed(box, index)
        self.window.set_title("Zhaan Control Point")
        
    def remove_source(self, device):
        super(HildonZhaanUI, self).remove_source(device)
        
        if len(self.sources) == 0:
            self.setup_default_source()
            self.source_browser.get_model().clear()

    def remove_renderer(self, device):
        super(HildonZhaanUI, self).remove_renderer(device)
        
        if len(self.renderers) == 0:
            self.setup_default_renderer()

    def setup_default_source(self):
        self.source_list.get_model(0).append(
            ["No Available Media Sources", None, None])
        self.select_source.set_active(0)
        
    def setup_default_renderer(self):        
        self.renderer_list.get_model(0).append(
            ["No Available Media Players", None, None])
        self.select_renderer.set_active(0)
        
    def add_renderer(self, device, icon_file):
        self.renderers.append(device)

        if len(self.renderers) == 1:
            model = self.renderer_list.get_model(0)
            iter = model.get_iter(0)
            while iter and model.iter_is_valid(iter):
                model.remove(iter)
                break

        self.icons[device.get_udn()] = icon_file
        self.renderer_list.get_model(0).append(
            [device.get_friendly_name(), gtk.STOCK_OPEN, device])

        if len(self.renderers) == 1:
            self.select_renderer.set_active(0)
        
    def add_source(self, device, icon_file):
        self.sources.append(device)
        if len(self.sources) == 1:
            model =  self.source_list.get_model(0)
            iter = model.get_iter(0)
            while iter and model.iter_is_valid(iter):            
                model.remove(iter)
                break

        self.icons[device.get_udn()] = icon_file
        self.source_list.get_model(0).append([device.get_friendly_name(), gtk.STOCK_OPEN, device])
        

        if len(self.sources) == 1:
            self.select_source.set_active(0)

    def init_top_bar(self):
        self.top_bar = gtk.HBox(True)
        
        liststore = gtk.ListStore(str, str, object)
        self.source_list = hildon.TouchSelector()
        
        cellpb = gtk.CellRendererPixbuf()
        cell = gtk.CellRendererText()

        self.source_list.append_text_column(liststore, False)
        col1 = self.source_list.get_column(0)
        col1.pack_start(cellpb)
        col1.set_property("text-column", False)
        col1.set_cell_data_func(cellpb, self.make_pb)        

        self.source_list.set_active(0, 0)
        self.source_list.connect("changed", self.source_changed)

        
        liststore = gtk.ListStore(str, str, object)
        self.renderer_list = hildon.TouchSelector()
        
        cellpb = gtk.CellRendererPixbuf()
        cell = gtk.CellRendererText()
        self.renderer_list.append_text_column(liststore, False)
        col1 = self.renderer_list.get_column(0)
        col1.set_property("text-column", False)
        col1.pack_start(cellpb)

        col1.set_cell_data_func(cellpb, self.make_pb)

        self.renderer_list.set_active(0, 0)
        self.renderer_list.connect("changed", self.renderer_changed)

        self.select_source = hildon.PickerButton(0, 0)
        self.select_source.set_selector(self.source_list)               
        self.select_source.show()
        
        self.select_renderer = hildon.PickerButton(0, 0)
        self.select_renderer.set_selector(self.renderer_list)
        self.select_renderer.show()
        
        self.setup_default_source()
        self.setup_default_renderer()
        
        self.top_bar.pack_start(self.select_source)
        self.top_bar.pack_start(self.select_renderer)
        self.source_list.show()
        self.renderer_list.show()
        self.top_bar.show()

        return self.top_bar

    def init_main_bar(self):
        self.main_bar = gtk.HBox(homogeneous=True)

        self.source_browser_win = hildon.PannableArea()
        self.source_browser_win.set_property("mov-mode",
                                         hildon.MOVEMENT_MODE_BOTH)
        
        tree_model = gtk.ListStore(str)
        self.source_browser = gtk.TreeView(tree_model)
        self.source_browser.set_reorderable(True)
        
        col = gtk.TreeViewColumn("Media Items in this Source")
        col.cell = gtk.CellRendererText()
        col.pack_start(col.cell)
        col.set_attributes(col.cell, text=0)
        self.source_browser.append_column(col)
        self.source_browser.connect("row-activated", self.enqueue_or_dive)
        self.source_browser_win.add(self.source_browser)
        self.source_browser_win.show()
        
        # -------
        # Main bar packing / cleanup
        # -------
        self.playlist = Playlist()
        self.playlist.build_signals()
        self.playlist.connect("play", self.play)
        self.playlist.connect("pause", self.pause)
        self.playlist.connect("stop", self.stop)

        self.main_bar.pack_start(self.source_browser_win, padding=3)
        self.main_bar.pack_start(self.playlist.build_ui(), padding=3)

        self.main_bar.show()
        self.source_browser.show()

        return self.main_bar


    def pull_renderer_status(self):
        if self.stop_controller:
            return False
        
        try:
            progress_data = self.upnp.get_renderer_status(self.renderer_device)
            volume_data   = self.upnp.get_volume(self.renderer_device)
        except:
            return

        trackdata = {}
        if "TrackMetaData" in progress_data and progress_data["TrackMetaData"]:
            metadata = progress_data["TrackMetaData"].props
            trackdata = {
                "title": metadata.title,
                "album": metadata.album,
                "artist": metadata.artist,
                "track_number": metadata.track_number,
                "genre": metadata.genre,
                "description": metadata.description,
                }
        
        self.track.set_text("(%s) %s " % (
                self.device_state, 
                trackdata.get("title", "Unknown Title")))

        self.album.set_text("%s From %s" % (trackdata.get("artist", "Unknown Artist"),
                                            trackdata.get("album", "Unknown Album")))
        
        maxv = float(self.time_to_int(progress_data["TrackDuration"]))
        self.progress.set_range(0, maxv)
        self.progress.ignore_seek = True
        self.progress.set_value(
            float(self.time_to_int(progress_data["RelTime"])))
        self.volume_control.set_value(float(volume_data) * -1)
        self.progress.ignore_seek = False

        return True

    def delete_controller(self, window):
        self.stop_controller = True

    def seek_media(self, scale):
        if not self.progress.ignore_seek:
            self.seek("00:" + self.int_to_time(None, scale.get_value()))
    
    def change_volume(self, scale):
        if not self.progress.ignore_seek:
            volume = int(scale.get_value() * -1)
            print "Volume: ", volume
            self.set_volume(volume)

    def leave_control_window(self):
        self.controller_win.destroy()
        self.in_control_window = False

    def change_to_controller(self, button):
        self.stop_controller = False
        self.controller_win = hildon.StackableWindow()
        self.in_control_window = True

        self.controller_win.set_title("Control - %s" %
                                      self.renderer_device.get_friendly_name())

        self.controller_win.connect("destroy", self.delete_controller)

        self.track = gtk.Label("Loading...")        
        self.track.show()

        self.album = gtk.Label()
        self.album.show()        
                         

        self.volume_control = gtk.VScale()
        self.volume_control.set_range(-100, 0)
        self.volume_control.set_update_policy(gtk.UPDATE_DELAYED)
        self.volume_control.show()
        self.volume_control.connect("value-changed", self.change_volume)
        self.volume_control.connect("format-value", lambda x,y: abs(int(y)))

        self.progress = gtk.HScale()
        self.progress.set_update_policy(gtk.UPDATE_DELAYED)
        self.progress.show()
        self.progress.connect("format-value", self.int_to_time)
        self.progress.connect("value-changed", self.seek_media)
        
        playlist = Playlist()
        try:
            playlist.build_signals()
        except:
            pass
        playlist.connect("play", self.play)
        playlist.connect("pause", self.pause)
        playlist.connect("stop", self.stop)
        playlist.connect("prev", self.prev)
        playlist.connect("next", self.next)
        

        controlbox = gtk.HBox()

        main = gtk.VBox()
        
        main.add(self.track)
        main.add(self.album)
        main.add(self.progress)
        main.add(playlist.build_control_box())
        main.show()
        
        controlbox.add(self.volume_control)
        controlbox.add(main)
        controlbox.show()

        self.controller_win.add(controlbox)
        self.controller_win.show()                

        GObject.timeout_add(1000, self.pull_renderer_status)
        self.pull_renderer_status()

    def __init__(self, upnp_backend):
        super(HildonZhaanUI, self).__init__(upnp_backend)
        
        self.window = hildon.StackableWindow()
        self.window.set_title("Zhaan Control Point")

        self.window.set_border_width(10)
        self.window.set_default_size(800,480)

        self.vbox = gtk.VBox(homogeneous=False)

        self.vbox.pack_start(self.init_top_bar(), False)
        self.vbox.pack_start(self.init_main_bar(), True)
        self.window.add(self.vbox)
        self.window.show()
        self.vbox.show()

        clear_button = hildon.Button(0, 0, "Clear Playlist")
        clear_button.connect("clicked", self.playlist.clear)

        controller_button = hildon.Button(0, 0, "Play Control")
        controller_button.connect("clicked", self.change_to_controller)

        menu = hildon.AppMenu()
        menu.append(clear_button)
        menu.append(controller_button)
        menu.show_all()

        self.window.set_app_menu(menu)

    def main(self):
        gtk.main()

if __name__ == "__main__":
    hello = HelloWorld()
    hello.main()

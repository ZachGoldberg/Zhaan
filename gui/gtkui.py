#!/usr/bin/env python
from gi.repository import GUPnP, GUPnPAV
import pygtk
pygtk.require('2.0')
import gtk, gobject

from gui.zhaanui import ZhaanUI
from gui.gtkplaylist import Playlist

class GTKZhaanUI(ZhaanUI):
                
    def add_renderer(self, device, icon_file):
        self.icons[device.get_udn()] = icon_file
        self.renderer_list.get_model().append([device.get_model_name(), gtk.STOCK_OPEN, device])
        self.renderers.append(device)
        if len(self.renderers) == 1:
            self.renderer_list.set_active(1)

    def add_source(self, device, icon_file):
        self.icons[device.get_udn()] = icon_file
        self.source_list.get_model().append([device.get_friendly_name(), gtk.STOCK_OPEN, device])
        
        self.sources.append(device)
        if len(self.sources) == 1:
            self.source_list.set_active(1)
    
    
    def init_top_bar(self):
        self.top_bar = gtk.HBox()
        
        liststore = gtk.ListStore(str, str, object)
        self.source_list = gtk.ComboBox(liststore)
        cellpb = gtk.CellRendererPixbuf()
        cell = gtk.CellRendererText()
        self.source_list.pack_start(cellpb, False)
        self.source_list.pack_start(cell, True)

        self.source_list.set_cell_data_func(cellpb, self.make_pb)
        self.source_list.add_attribute(cell, 'text', 0)
        self.source_list.get_model().append(["Media Sources", gtk.STOCK_OPEN, None])
        self.source_list.set_active(0)
        self.source_list.connect("changed", self.source_changed)

        liststore = gtk.ListStore(str, str, object)
        self.renderer_list = gtk.ComboBox(liststore)
        cellpb = gtk.CellRendererPixbuf()
        cell = gtk.CellRendererText()
        self.renderer_list.pack_start(cellpb, False)
        self.renderer_list.pack_start(cell, True)
        self.renderer_list.set_cell_data_func(cellpb, self.make_pb)
        self.renderer_list.add_attribute(cell, 'text', 0)
        self.renderer_list.get_model().append(["Media Players", gtk.STOCK_OPEN, None])
        self.renderer_list.set_active(0)        
        self.renderer_list.connect("changed", self.renderer_changed)

        self.top_bar.pack_start(self.source_list)
        self.top_bar.pack_start(self.renderer_list)
        self.source_list.show()
        self.renderer_list.show()
        self.top_bar.show()

        return self.top_bar

    def init_main_bar(self):
        self.main_bar = gtk.HBox(homogeneous=True)

        self.source_browser_win = gtk.ScrolledWindow()

        tree_model = gtk.ListStore(str)
        self.source_browser = gtk.TreeView(tree_model)
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

        self.playlist.connect("play", self.play)
        self.playlist.connect("pause", self.pause)
        self.playlist.connect("stop", self.stop)

        self.main_bar.pack_start(self.source_browser_win, padding=3)
        self.main_bar.pack_start(self.playlist.build_ui(), padding=3)

        self.main_bar.show()
        self.source_browser.show()

        return self.main_bar


    def __init__(self, upnp_backend):
        
        super(GTKZhaanUI, self).__init__(upnp_backend)

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_border_width(10)
        self.window.set_default_size(800,480)

        self.vbox = gtk.VBox(homogeneous=False)

        self.vbox.pack_start(self.init_top_bar(), False)
        self.vbox.pack_start(self.init_main_bar(), True)
        self.window.add(self.vbox)
        self.window.show()
        self.vbox.show()

    def main(self):
        gtk.main()

if __name__ == "__main__":
    hello = HelloWorld()
    hello.main()

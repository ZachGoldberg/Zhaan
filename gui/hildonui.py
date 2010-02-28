#!/usr/bin/env python
import gtk, hildon, gobject
from gi.repository import GUPnP, GUPnPAV

from gui.hildonplaylist import Playlist
from gui.zhaanui import ZhaanUI

class HildonZhaanUI(ZhaanUI):        

    def begin_progress_indicator(self):
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 1)

    def end_progress_indicator(self):
        hildon.hildon_gtk_window_set_progress_indicator(self.window, 0)
                           
    def add_renderer(self, device, icon_file):
        self.renderers.append(device)

        if len(self.renderers) == 1:
            model = self.renderer_list.get_model(0)
            iter = model.get_iter(0)
            while iter and model.iter_is_valid(iter):
                model.remove(iter)
                break
asd
        self.icons[device.get_udn()] = icon_file
        self.renderer_list.get_model(0).append(
            [device.get_friendly_name(), gtk.STOCK_OPEN, device])

        if len(self.renderers) == 1:
            self.renderer_list.set_active(0, 1)

        
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
            self.source_list.set_active(0, 1)    


    def init_top_bar(self):
        self.top_bar = gtk.HBox(True)
        
        liststore = gtk.ListStore(str, str, object)
        self.source_list = hildon.TouchSelector()
        
        cellpb = gtk.CellRendererPixbuf()
        cell = gtk.CellRendererText()

        self.source_list.append_text_column(liststore, False)
        col1 = self.source_list.get_column(0)
        col1.pack_start(cellpb)

        col1.set_cell_data_func(cellpb, self.make_pb)        

        self.source_list.set_active(0, 0)
        self.source_list.connect("changed", self.source_changed)

        
        liststore = gtk.ListStore(str, str, object)
        self.renderer_list = hildon.TouchSelector()
        
        cellpb = gtk.CellRendererPixbuf()
        cell = gtk.CellRendererText()

        self.renderer_list.append_text_column(liststore, False)
        col1 = self.renderer_list.get_column(0)
        col1.pack_start(cellpb)

        col1.set_cell_data_func(cellpb, self.make_pb)

        self.renderer_list.set_active(0, 0)
        self.renderer_list.connect("changed", self.renderer_changed)
        
        self.source_list.get_model(0).append(
            ["No Available Media Sources", None, None])

        self.renderer_list.get_model(0).append(
            ["No Available Media Players", None, None])


        self.select_source = hildon.PickerButton(0, 0)
        self.select_source.set_title("Select Source")
        self.select_source.set_selector(self.source_list)
        self.select_source.show()

        self.select_renderer = hildon.PickerButton(0, 0)
        self.select_renderer.set_title("Select Player")
        self.select_renderer.set_selector(self.renderer_list)
        self.select_renderer.show()
        
        
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

        self.playlist.connect("play", self.play)
        self.playlist.connect("pause", self.pause)
        self.playlist.connect("stop", self.stop)

        self.main_bar.pack_start(self.source_browser_win, padding=3)
        self.main_bar.pack_start(self.playlist.build_ui(), padding=3)

        self.main_bar.show()
        self.source_browser.show()

        return self.main_bar

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
        
        menu = hildon.AppMenu()
        menu.append(clear_button)
        menu.show_all()

        self.window.set_app_menu(menu)

    def main(self):
        gtk.main()

if __name__ == "__main__":
    hello = HelloWorld()
    hello.main()

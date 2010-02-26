#!/usr/bin/env python
import gtk, hildon, gobject
from gi.repository import GUPnP, GUPnPAV

from gui.hildonplaylist import Playlist

class ZhaanUI(object):
    def hello(self, widget, data=None):
        print "Hello World"

    def delete_event(self, widget, event, data=None):
        print "delete event occurred"
        return False

    def destroy(self, widget, data=None):
        print "destroy signal occurred"
        gtk.main_quit()

    def source_changed(self, box, index):
        active = self.source_list.get_active(0)

        if active < 0: # Selected nothing
            return
        
        self.stack = []
        self.source_device = self.sources[active]
        self.select_source.set_title(self.source_device.get_friendly_name())
        self.upnp.load_children(self.source_device)

    def renderer_changed(self, box, index):
        active = self.renderer_list.get_active()

        if active < 0: # Selected nothing
            return
        
        self.renderer_device = self.renderers[active]

    def enqueue_or_dive(self, tree, col_loc, col):
        item = self.items[col_loc[0]]
        if isinstance(item, GUPnPAV.GUPnPDIDLLiteContainer):
            self.stack.append(item.get_parent_id())
            self.upnp.load_children(self.source_device, item.get_id())
        elif isinstance(item, GUPnPAV.GUPnPDIDLLiteItem):
            self.playlist.add(item, item.get_title())
        else:
            if len(self.stack) > 0:
                self.upnp.load_children(self.source_device, 
                                        self.stack.pop())
            
    def add_source_item(self, item, txt):
        self.items.append(item)
        self.source_browser.get_model().append([txt])

    def clear_source_browser(self):
        self.source_browser.get_model().clear()
        self.items = []
        self.add_source_item(None, "..")
        
    def add_container(self, container):
        self.add_source_item(container, "(+) %s" % container.get_title())

    def add_object(self, object):
        self.add_source_item(object, object.get_title())
        
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
    
    def remove_renderer(self, device):
        self.remove_device(device, self.renderers, self.renderer_device, self.renderer_list)
        
    def remove_source(self, device):
        self.remove_device(device, self.sources, self.source_device, self.source_list)
      

    def remove_device(self, device, cache_list, cache_item, ui_list):
        for d in cache_list:
            if d.get_udn() == device.get_udn():
                cache_list.remove(d)
                if d.get_udn() == cache_item.get_udn():
                    if len(cache_list) > 1:
                        ui_list.set_active(1)
                    else:
                        ui_list.set_active(0)

        model = ui_list.get_model()
        iter =  model.get_iter(0)
        while iter and model.iter_is_valid(iter):
            iter = model.iter_next(iter)
            if iter and model.get_value(iter, 2).get_udn() == device.get_udn():
                model.remove(iter)

    def make_pb(self, col, cell, model, iter):
        stock = model.get_value(iter, 1)
	if not stock:
	    return

        device = model.get_value(iter, 2)

        if device and self.icons[device.get_udn()]:
            pb = gtk.gdk.pixbuf_new_from_file(self.icons[device.get_udn()])
            pb = pb.scale_simple(22, 22, gtk.gdk.INTERP_HYPER)
        else:
            pb = self.source_list.render_icon(stock, gtk.ICON_SIZE_MENU, None)

        cell.set_property('pixbuf', pb)
        return

    def play(self, playlist, item):
        if not self.source_device or not self.renderer_device:
            print "Missing either source or destination device"
            return

	if item:
          print "Begin playing %s" % item.get_title()

        self.playing_item = item
        self.upnp.play_object(self.source_device,
                              self.renderer_device,
                              item)
        
    def stop(self, playlist, item):
        if not self.source_device or not self.renderer_device:
            print "Missing either source or destination device"
            return

        self.upnp.stop_object(self.source_device,
                              self.renderer_device,
                              self.playing_item)

    def pause(self, playlist, item):
        if not self.source_device or not self.renderer_device:
            print "Missing either source or destination device"
            return

        self.upnp.pause_object(self.source_device,
                              self.renderer_device,
                              self.playing_item)

    def init_top_bar(self):
        self.top_bar = gtk.HBox()
	
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
        self.upnp = upnp_backend

        self.playing_item = None
        self.sources = []
        self.icons = {}
        self.renderers = []
        self.items = []
        self.source_device = None
        self.renderer_device = None
        self.stack = []

        program = hildon.Program.get_instance()
        
        self.window = hildon.StackableWindow()
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
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

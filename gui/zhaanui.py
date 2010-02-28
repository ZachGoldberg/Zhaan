import gtk
from gi.repository import GUPnPAV

class ZhaanUI(object):

    def __init__(self, upnp_backend):
        self.upnp = upnp_backend
        
        self.playing_item = None
        self.sources = []
        self.icons = {}
        self.renderers = []
        self.items = []
        self.renderer_device = None
        self.source_device = None
        self.stack = []
        
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
    def begin_progress_indicator(self):
        pass

    def end_progress_indicator(self):
        pass

    def add_container(self, container):
        self.add_source_item(container, "(+) %s" % container.get_title())

    def add_object(self, object):
        self.add_source_item(object, object.get_title())

    def add_source_item(self, item, txt):          
        self.items.append(item)
        self.source_browser.get_model().append([txt])

    def clear_source_browser(self):
        self.source_browser.get_model().clear()
        self.items = []
        if len(self.stack) != 0:
            self.add_source_item(None, "..")

    def source_changed(self, box, index=None):
        if not self.sources: # Selected nothing
            return

        # Prevent a Critical Glib warning by not calling get_active
        # when the tree is technically empty
        if len(self.sources) == 1:
            active = 0
        else:        
            active = self.source_list.get_active(0)
        
        self.stack = []
        self.source_device = self.sources[active]
        self.upnp.load_children(self.source_device)

        if hasattr(self, "select_source"):
            self.select_source.set_title(self.source_device.get_friendly_name())

    def renderer_changed(self, box, index):
        if not self.renderers: # Selected nothing
            return

        if len(self.renderers) == 1:
            active = 0
        else:
            active = self.renderer_list.get_active(0)
        
        self.renderer_device = self.renderers[active]
        if hasattr(self, "select_renderer"):
            self.select_renderer.set_title(
                self.renderer_device.get_friendly_name())

    def remove_renderer(self, device):
        self.remove_device(device, self.renderers,
                           self.renderer_device, self.renderer_list)
        
    def remove_source(self, device):
        self.remove_device(device, self.sources,
                           self.source_device, self.source_list)

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
            pb = pb.scale_simple(44, 44, gtk.gdk.INTERP_HYPER)
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

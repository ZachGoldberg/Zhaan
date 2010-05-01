import gtk, time
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
        self.current_id = 0

    def destroy(self, widget, data=None):
	print "Exiting"
	gtk.main_quit()

    def enqueue_or_dive(self, tree, col_loc, col):
        item = self.items[col_loc[0]][0]
        if isinstance(item, GUPnPAV.GUPnPDIDLLiteContainer):
            self.stack.append(item.get_parent_id())
            self.current_id = item.get_id()
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

    def update_renderer_status(self, device, state):
        pass

    def add_container(self, container):
        self.add_source_item(container, "(+) %s" % container.get_title())

    def add_object(self, object):
        self.add_source_item(object, object.get_title())

    def add_source_item(self, item, txt):          
        self.items.append((item, txt))
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
	    try:
               active = self.source_list.get_active()
               if active > 0: # Account for the title entry
		 active -= 1
	    except:
               active = self.source_list.get_active(0)
        
        self.stack = []
        self.source_device = self.sources[active]
        self.upnp.load_children(self.source_device)

    def renderer_changed(self, box, index=None):
        if not self.renderers: # Selected nothing
            return

        if len(self.renderers) == 1:
            active = 0
        else:
	    try:
               active = self.renderer_list.get_active()
               if active > 0: # Account for the title entry
		 active -= 1
	    except:
               active = self.renderer_list.get_active(0)
        
        self.renderer_device = self.renderers[active]

    def remove_renderer(self, device):
        if device.get_udn() == self.renderer_device.get_udn():
          if getattr(self, "in_control_window", False):
            self.leave_control_window()

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
                        try:
                            ui_list.set_active(1)
                        except:
                            ui_list.set_active(0, 1)
                    else:
                        try:
                            ui_list.set_active(0)
                        except:
                            ui_list.set_active(0, 0)

        try:
            model = ui_list.get_model()
        except:
            model = ui_list.get_model(0)
            
        iter =  model.get_iter(0)
        while iter and model.iter_is_valid(iter):
            dev = model.get_value(iter, 2)
            if dev and dev.get_udn() == device.get_udn():
                model.remove(iter)
                break
            iter = model.iter_next(iter)
            

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

    def search_directory(self, button, entry):
        query = entry.get_text()
        if not query:
            return

        query = query.lower()
        # Ideally we would now actually query the remote source
        # with a search.  However we already have the contents
        # of the current directory in a local cache, might
        # as well just do the search ourselves.
        matching_items = []
        for (item, text) in self.items:
            if query in text.lower():
                matching_items.append((item, text))

        if self.stack and (self.stack[-1] != self.current_id):
            # If we search within a search we dont want to add
            # to the stack twice
            self.stack.append(self.current_id)
            
        self.clear_source_browser()
        for (item, text) in matching_items:
            self.add_source_item(item, text)

    def time_to_int(self, time):
        try:
          (hour, min, sec) = time.split(":")
          return (int(hour) * 3600) + (int(min) * 60) + int(sec)
        except:
          return 0

    def int_to_time(self, range, timevalue):
        return "%.2d:%.2d" % (int(timevalue / 60), timevalue % 60)

    def play_no_item(self, playlist, item):
        if not self.renderer_device:
            print "Missing Renderer"
            return

        self.upnp.play(self.source_device,
                       self.renderer_device,
                       item)

    
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
        if not self.renderer_device:
            print "Missing Renderer"
            return

        self.upnp.stop_object(self.source_device,
                              self.renderer_device,
                              self.playing_item)

    def pause(self, playlist, item):
        if  not self.renderer_device:
            print "Missing Renderer"
            return

        self.upnp.pause_object(self.source_device,
                              self.renderer_device,
                              self.playing_item)

    def prev(self, playlist, item):
        if not self.renderer_device:
            print "Missing Renderer"
            return

        self.upnp.prev_object(self.source_device,
                              self.renderer_device,
                              self.playing_item)

    def next(self, playlist, item):
        if not self.renderer_device:
            print "Missing Renderer"
            return

        self.upnp.next_object(self.source_device,
                              self.renderer_device,
                              self.playing_item)

    def seek(self, abs_time):
        self.upnp.seek_object(self.source_device,
                              self.renderer_device,
                              self.playing_item,
                              abs_time)

    def set_volume(self, volume):
        self.upnp.set_volume(self.renderer_device,
                             volume)

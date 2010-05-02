import gtk, hildon, gobject


class Playlist(gobject.GObject):
    def __init__(self):
        self.playlist = None
        self.items = []
        self.history = []
        super(Playlist, self).__init__()
        
    def build_signals(self):
        gobject.signal_new("play", Playlist, gobject.SIGNAL_RUN_LAST, 
                           gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

        gobject.signal_new("pause", Playlist, gobject.SIGNAL_RUN_LAST, 
                          gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

        gobject.signal_new("stop", Playlist, gobject.SIGNAL_RUN_LAST, 
                          gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

        gobject.signal_new("next", Playlist, gobject.SIGNAL_RUN_LAST, 
                          gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

        gobject.signal_new("prev", Playlist, gobject.SIGNAL_RUN_LAST, 
                          gobject.TYPE_BOOLEAN, (gobject.TYPE_PYOBJECT,))

    def get_selected_item(self):
        if not hasattr(self, "playlist_box"):
            return [None]
        
        selection = self.playlist_box.get_selection().get_selected_rows()        
        model = self.playlist_box.get_model()
        iter = model.get_iter_first()
        if not iter:
            return None, None

        first = model.get_value(iter, 0)
        item = self.items[0]

        # this should one day return the actual
        # selected item and its display text
        return item, ""

    def clear(self, button=None):
        self.items = []
        self.history = []
        self.playlist_box.get_model().clear()
        
        
    def play(self, button):
        self.emit("play", self.get_selected_item()[0])
    
    def pause(self, button):
        self.emit("pause", self.get_selected_item()[0])
    
    def stop(self, button):
        self.emit("stop", self.get_selected_item()[0])

    def prev(self, button):
        self.emit("prev", self.get_selected_item()[0])

    def next(self, button):
        self.emit("next", self.get_selected_item()[0])

    def up(self, button):
        store, selection = self.playlist_box.get_selection().get_selected_rows()
        model, selected_row_iter = self.playlist_box.get_selection().get_selected()
        
        prev = model.get_iter_from_string(str(selection[0][0] - 1))
        if not prev:
            return
        
        model.move_before(selected_row_iter, prev)
        temp = self.items[selection[0][0]]
        self.items[selection[0][0]] = self.items[selection[0][0] - 1]
        self.items[selection[0][0] - 1] = temp
        
        
    def down(self, button):
        store, selection = self.playlist_box.get_selection().get_selected_rows()
        model, selected_row_iter = self.playlist_box.get_selection().get_selected()
        
        next = model.iter_next(selected_row_iter)
        if not next:
            return
        
        model.move_after(selected_row_iter, next)

        temp = self.items[selection[0][0]]
        self.items[selection[0][0]] = self.items[selection[0][0] + 1]
        self.items[selection[0][0] + 1] = temp
        
    def rm(self, index):
        try:
            model_iter = self.playlist_box.get_model().get_iter_from_string(str(index))
        except:
            # The playlist could be empty, or other bad index input
            return
        
        self.playlist_box.get_model().remove(model_iter)
        self.items.remove(self.items[0])

    def prepend(self, item, title):
        self.items.insert(0, item)
        self.playlist_box.get_model().insert(0, [title])    

    def add(self, item, title):
        self.items.append(item)
        self.playlist_box.get_model().append([title])


    def new_button(self, title):
        return hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH |
                                         gtk.HILDON_SIZE_FINGER_HEIGHT,
                                         hildon.BUTTON_ARRANGEMENT_VERTICAL,
                                         title)

    def build_control_box(self):
        if self.playlist:
            return self.playlist

        self.playlist = gtk.VBox()

        # -------
        # Play Control
        # -------

        self.control_box = gtk.HBox()
        self.play_button = self.new_button("Play")
        self.control_box.pack_start(self.play_button, True)
        self.play_button.connect("clicked", self.play)
        self.play_button.show()

        self.pause_button = self.new_button("Pause")
        self.control_box.pack_start(self.pause_button, True)
        self.pause_button.connect("clicked", self.pause)
        self.pause_button.show()

        self.stop_button = self.new_button("Stop")
        self.control_box.pack_start(self.stop_button, True)
        self.stop_button.connect("clicked", self.stop)
        self.stop_button.show()

        self.prev_button = self.new_button("Previous")
        self.control_box.pack_start(self.prev_button, True)
        self.prev_button.connect("clicked", self.prev)
        self.prev_button.show()

        self.next_button = self.new_button("Next")
        self.control_box.pack_start(self.next_button, True)
        self.next_button.connect("clicked", self.next)
        self.next_button.show()

        self.playlist.pack_start(self.control_box, False)
        self.control_box.show()

        self.playlist.show()        
        return self.playlist

    def build_ui(self):
        if self.playlist:
            return self.playlist

        self.playlist = gtk.VBox()

        # -------
        # Play Control
        # -------

        self.control_box = gtk.HBox()
        self.play_button = self.new_button("Play")
        self.control_box.pack_start(self.play_button, True)
        self.play_button.connect("clicked", self.play)
        self.play_button.show()

        self.pause_button = self.new_button("Pause")
        self.control_box.pack_start(self.pause_button, True)
        self.pause_button.connect("clicked", self.pause)
        self.pause_button.show()

        self.stop_button = self.new_button("Stop")
        self.control_box.pack_start(self.stop_button, True)
        self.stop_button.connect("clicked", self.stop)
        self.stop_button.show()

        self.playlist.pack_start(self.control_box, False)
        self.control_box.show()

        # -------
        # Playlist itself
        # -------

        self.playlist_win = hildon.PannableArea()
        self.playlist_win.set_property("mov-mode", hildon.MOVEMENT_MODE_BOTH)
        
        tree_model2 = gtk.ListStore(str)
        self.playlist_box = gtk.TreeView(tree_model2)
        
        self.playlist_box.set_reorderable(True)
        
        col2 = gtk.TreeViewColumn("Playlist")
        col2.cell = gtk.CellRendererText()
        col2.pack_start(col2.cell)
        col2.set_attributes(col2.cell, text=0)
        self.playlist_box.append_column(col2)
        self.playlist_box.show()
        self.playlist_win.add(self.playlist_box)
        self.playlist_win.show()
        self.playlist.pack_start(self.playlist_win, True, padding=3)
        # -------
        # Playlist Control Box
        # -------

        self.playlist_control = gtk.HBox()

        self.pl_up_button = self.new_button("Up")
        self.playlist_control.pack_start(self.pl_up_button, True)
        self.pl_up_button.connect("clicked", self.up)
        self.pl_up_button.show()

        self.pl_down_button = self.new_button("Down")
        self.playlist_control.pack_start(self.pl_down_button, True)
        self.pl_down_button.connect("clicked", self.down)
        self.pl_down_button.show()

        self.pl_rm_button = self.new_button("Remove")
        self.playlist_control.pack_start(self.pl_rm_button, True)
        self.pl_rm_button.connect("clicked", self.rm)
        self.pl_rm_button.show()

        #self.playlist.pack_start(self.playlist_control, False, padding=3)
        self.playlist_control.show()
                                   
        self.playlist.show()        
        return self.playlist

import pygtk
pygtk.require('2.0')
from gi.repository import GLib, GUPnP, GUPnPAV, GSSDP, GObject
import os, urllib2, tempfile, atexit
import pygtk, gtk, sys, time

from action import UPnPAction

from DIDLParser import DIDLParser
from UPnPDeviceManager import UPnPDeviceManager

class Zhaan(object):
  def __init__(self):
    self.devices = []
    self.introspections = {}
    self.device_services = {}
    
    self.ui = None
    self.cps = []
    self.contexts = []  
    self.created_files = []


  def main(self):
    self.device_mgr = UPnPDeviceManager()

    self.device_mgr.connect("device_available", self.device_available)
    self.device_mgr.connect("device_unavailable", self.device_unavailable)

    # Determine which kind of UI to use based on whats available
    try:
      import hildon
      from gui.hildonui import HildonZhaanUI as ZhaanUI
    except:      
      pass

    if not "ZhaanUI" in dir():
      try:
        import gtk
        from gui.gtkui import GTKZhaanUI as ZhaanUI
      except:
        sys.stderr.write("Could not find hildon or gtk.")
        sys.exit(1)


    GObject.timeout_add(1000, self.update_renderer_status)
      
    self.ui = ZhaanUI(self)
    self.ui.main()


  def update_renderer_status(self):
    for device in self.ui.renderers:
      serv = self.device_mgr.is_renderer(device)

      def loaded(service, action, data):
	keys = ["CurrentTransportState",
		"CurrentTransportStatus",
		"CurrentSpeed"]
        
        try:
          success, return_data = service.end_action_list(action, keys,
                                                         [GObject.TYPE_STRING,
                                                          GObject.TYPE_STRING,
                                                          GObject.TYPE_STRING]
                                                         )
        except:
          return
							

	if return_data:
		return_data = dict(zip(keys, return_data))

                self.ui.update_renderer_status(
                  data,
                  return_data["CurrentTransportState"])
                
      return_data = serv.begin_action_list("GetTransportInfo",
                                           ["InstanceID"],
                                           ["0"],
                                           loaded, device)

           
    return True

  def device_available(self, manager, device):
    if device.is_source:
      self.ui.add_source(device, device.icon_file)
    if device.is_renderer:
      self.ui.add_renderer(device, device.icon_file)

  def device_unavailable(self, manager, device):
    if not device:
	return

    if device.is_source:
      self.ui.remove_source(device)
    if device.is_renderer:
      self.ui.remove_renderer(device)


  def set_volume(self, renderer, volume):
    control = self.device_mgr.get_service_on_device(renderer, 
                                                    "RenderingControl")

    if not control:
      return
    
    try:
      result, data = control.send_action_list("SetVolume", ["InstanceID",
                                                            "Channel",
                                                            "DesiredVolume"],
                                                           ["0", "Master", str(volume)],
                                                           [], [])
    except:
      pass # Maybe show something in the UI?

  def get_volume(self, renderer):
    control = self.device_mgr.get_service_on_device(renderer, 
                                                    "RenderingControl")

    if not control:
      return
    
    result, data = control.send_action_list("GetVolume", ["InstanceID",
                                                          "Channel"],
                                            ["0", "Master"],
                                            ["CurrentVolume"],
                                            [GObject.TYPE_STRING]
                                            )
    if result and data:
      return data[0]

    return 0
    

  def get_renderer_status(self, renderer):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    if not av_serv:
      return {}
    
    out_keys = ["Track",
                "TrackDuration",
                "TrackMetaData",
                "TrackURI",
                "RelTime",               
                "AbsTime"]
    
    out_types = [GObject.TYPE_STRING for i in range(6)]
    in_keys = ["InstanceID"]

    result, data = av_serv.send_action_list("GetPositionInfo", in_keys,
                                            ["0"],
                                            out_keys,
                                            out_types)
    if not result or not data:
      return {}

    data = dict(zip(out_keys, data))

    if data.get("TrackMetaData"):
      parser = None
      try:
        parser = DIDLParser(data["TrackMetaData"])
      except:
        pass
        
      if parser and parser.objects:
        data["TrackMetaData"] = parser.objects[0]
      else:
        del data["TrackMetaData"]

    return data

  def set_next_uri(self, source, renderer, item):
    resources = None

    if item:
      resources = item.get_resources()

    if not resources:
      return

    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")

    if not av_serv:
      return

    try:
      av_serv.send_action_list("SetNextAVTransportURI", ["InstanceID", "NextURI"],
                               ["0", resources[0]], [], [])
    except:
      pass
    
      
  def stop_object(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Stop", ["InstanceID"],
                             ["0"], [], [])


  def pause_object(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Pause", ["InstanceID"],
                             ["0"], [], [])

  def prev_object(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Previous", ["InstanceID"],
                             ["0"], [], [])

  def next_object(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Next", ["InstanceID"],
                             ["0"], [], [])


  def seek_object(self, source, renderer, item, abs_time):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Seek", ["InstanceID", "Unit", "Target"],
                             ["0", "ABS_TIME", abs_time], [], [])

    
  def play_object(self, source, renderer, item):
    resources = None
    if item:
       resources = item.get_resources()
 
    uri = ""
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")

    if not av_serv:
      print "Renderer is invalid?"
      self.ui.remove_renderer(renderer)
      return

    if resources:
      uri = resources[0].get_uri()
      data = {"InstanceID": "0", "CurrentURI": uri, "CurrentURIMetaData": uri} 
    
      act = UPnPAction(renderer,
                     av_serv,
                     "SetAVTransportURI",
                     data)
      act.register_device_manager(self.device_mgr)
      act.execute()
    else:
      print "No Resources for item?"

    data = {"InstanceID": "0", "CurrentURI": uri, "CurrentURIMetaData": uri, "Speed": 1} 
    act = UPnPAction(renderer,
                     av_serv,
                     "Play",
                     data)

    act.register_device_manager(self.device_mgr)
    act.execute()

  def play(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")

    if not av_serv:
      print "Renderer is invalid?"
      self.ui.remove_renderer(renderer)
      return

    data = {"InstanceID": "0", "Speed": 1} 
    act = UPnPAction(renderer,
                     av_serv,
                     "Play",
                     data)

    act.register_device_manager(self.device_mgr)
    act.execute()

  def children_loaded(self, service, action, data):
    """
    Ends the action and loads the data
    """
    self.ui.end_progress_indicator()
    keys = ["Result", "NumberReturned", "TotalMatches", "UpdateID"]

    success, return_data = service.end_action_list(action, keys,
                                                   [GObject.TYPE_STRING,
                                                    GObject.TYPE_STRING,
                                                    GObject.TYPE_STRING,
                                                    GObject.TYPE_STRING])

    return_data = dict(zip(keys, return_data))

    if not success:
      print "Browse Node Action Failed"
      return

    parser = DIDLParser(return_data["Result"])

    if not data:
      self.ui.clear_source_browser()
      
      for c in parser.containers:
        self.ui.add_container(c)

      for o in parser.objects:
        self.ui.add_object(o)

    else:
      for c in parser.containers:
        data(c)

      for o in parser.objects:
        data(o)


  def load_children(self, device, object_id=0, callback=None):
    """
    Make an asynchronous call to download the children of this node
    The UI will call this and then continue.  The calback for the
    async browse function will populate the UI
    """
    self.ui.begin_progress_indicator()

    serv = self.device_mgr.is_source(device)

    # It's possible this is a stale device or other problems
    if not serv:
      return
    
    return_data = serv.begin_action_list("Browse",
                                         ["ObjectID",
                                          "BrowseFlag",
                                          "Filter",
                                          "StartingIndex",
                                          "RequestedCount",
                                          "SortCriteria"],
                                         [str(object_id),
                                          "BrowseDirectChildren",
                                          "*",
                                          "0",
                                          "0",
                                          ""],
                                         self.children_loaded, callback)
  
if __name__ == "__main__":
  prog = Zhaan()
  prog.main()

from gi.repository import GLib, GUPnP, GUPnPAV, GSSDP, GObject
import os, urllib2, tempfile, atexit
import pygtk, gtk, sys, time

from action import UPnPAction

from DIDLParser import DIDLParser
from UPnPDeviceManager import UPnPDeviceManager

class DIDLParser(object):
  def __init__(self,  xml_data):
    self.containers = []
    self.objects = []

    parser = GUPnPAV.GUPnPDIDLLiteParser()
    parser.connect("container_available", self.new_container)
    parser.connect("item_available", self.new_item)
    try:
      parser.parse_didl(xml_data)
    except:
      pass
        
  def new_item(self, node, object):
    self.objects.append(object)

  def new_container(self, node, object):
    self.containers.append(object)


class PyGUPnPCP(object):
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
        out_data = {"CurrentTransportState": "", "CurrentTransportStatus": "",
                    "CurrentSpeed": ""}
	keys = ["CurrentTransportState",
		"CurrentTransportStatus",
		"CurrentSpeed"]
        success, return_data = service.end_action_list(action, keys,
								[GObject.TYPE_STRING,
								 GObject.TYPE_STRING,
								 GObject.TYPE_STRING]
								)
							

	if return_data:
		return_data = dict(zip(keys, return_data))
        self.ui.update_renderer_status(data, return_data["CurrentTransportState"])
                    
      return_data = serv.begin_action_list("GetTransportInfo",
                                           ["InstanceID"],
                                           [GObject.TYPE_STRING],
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
                                            [GObject.TYPE_STRING],
                                            ["0"],
                                            out_keys,
                                            out_types)
    if not result or not data:
      return {}

    print data
    
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
      
  def stop_object(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Stop", ["InstanceID"], [GObject.TYPE_STRING],
                             ["0"], [], [])


  def pause_object(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Pause", ["InstanceID"], [GObject.TYPE_STRING],
                             ["0"], [], [])

  def prev_object(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Previous", ["InstanceID"], [GObject.TYPE_STRING],
                             ["0"], [], [])

  def next_object(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Next", ["InstanceID"], [GObject.TYPE_STRING],
                             ["0"], [], [])


  def seek_object(self, source, renderer, item, abs_time):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    av_serv.send_action_list("Seek", ["InstanceID", "Unit", "Target"],
                             [GObject.TYPE_STRING for i in range(3)],
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

  def children_loaded(self, service, action, data):
    """
    Ends the action and loads the data
    """
    self.ui.end_progress_indicator()
    print "loaded"
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

    self.ui.clear_source_browser()
    for c in parser.containers:
      self.ui.add_container(c)

    for o in parser.objects:
      self.ui.add_object(o)

  def load_children(self, device, object_id=0):
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
                                         [GObject.TYPE_STRING,
                                          GObject.TYPE_STRING,
                                          GObject.TYPE_STRING,
                                          GObject.TYPE_STRING,
                                          GObject.TYPE_STRING,
                                          GObject.TYPE_STRING],
                                         [str(object_id),
                                          "BrowseDirectChildren",
                                          "*",
                                          "0",
                                          "0",
                                          ""],
                                         self.children_loaded, None)
  
if __name__ == "__main__":
  prog = PyGUPnPCP()
  prog.main()

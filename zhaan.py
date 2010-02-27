from gi.repository import GLib, GUPnP, GUPnPAV, GSSDP, GObject, libsoup
import os, urllib2, tempfile, atexit
import pygtk, gtk

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
    parser.parse_didl(xml_data)
        
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
      from gui.hildonui import ZhaanUI
    except:      
      pass

    if not "ZhaanUI" in dir():
      try:
        import gtk
        from gui.gtkui import ZhaanUI
      except:
        sys.stderr.write("Could not find hildon or gtk.")
        sys.exit(1)
      
    self.ui = ZhaanUI(self)
    self.ui.main()

  def device_available(self, manager, device):
    if device.is_source:
      self.ui.add_source(device, device.icon_file)
    elif device.is_renderer:
      self.ui.add_renderer(device, device.icon_file)

  def device_unavailable(self, manager, device):
    if device.is_source:
      self.ui.remove_source(device)
    elif device.is_renderer:
      self.ui.remove_renderer(device)


  def stop_object(self, source, renderer, item):
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    data = {"InstanceID": 0}
    av_serv.send_action_hash("Stop", data, {})

  def pause_object(self, source, renderer, item):
    print "Sending Pause"
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")
    data = {"InstanceID": 0}
    print "Pre action"
    av_serv.send_action_hash("Pause", data, {})
    print "post action"
    
  def play_object(self, source, renderer, item):
    resources = None
    if item:
       resources = item.get_resources()
 
    uri = ""
    av_serv = self.device_mgr.get_service_on_device(renderer, "AVTransport")

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

    print "Sending action..."
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

    out_data = {"Result": "", "NumberReturned": "", "TotalMatches": "", "UpdateID": ""}

    success, return_data = service.end_action_hash(action, out_data)
    if not success:
      print "Browse Node Action Failed"

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
    serv = self.device_mgr.is_source(device)
  
    assert serv

    in_data = {"ObjectID": object_id, "BrowseFlag": "BrowseDirectChildren",
               "Filter": "*", "StartingIndex": "0", "RequestCount": "0",
               "SortCriteria": ""}

    return_data = serv.begin_action_list("Browse",
                                         ["ObjectID",
                                          "BrowseFlag",
                                          "Filter",
                                          "StartingIndex",
                                          "RequestCount"],
                                         [GObject.TYPE_STRING,
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

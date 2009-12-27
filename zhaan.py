from gi.repository import GLib, GUPnP, GUPnPAV, GSSDP, GObject, libsoup
import os, urllib2, tempfile, atexit
import pygtk, gtk

from gui import PyGUPnPCPUI
from action import UPnPAction
from DIDLParser import DIDLParser
from UPnPDeviceManager import UPnPDeviceManager


class PyGUPnPCP(object):
  def __init__(self):
    self.devices = []
    self.introspections = {}
    self.device_services = {}
    
    self.sources = []
    self.renderers = []
    self.ui = None
    self.cps = []
    self.contexts = []  
    self.created_files = []

    atexit.register(self.cleanup_files)

  def cleanup_files(self):
    for i in self.created_files:
      os.unlink(i)
    

  def main(self):
    GObject.threads_init()

    self.device_mgr = UPnPDeviceManager()
    self.device_mgr.connect("device-available", self.device_available)
    self.device_mgr.connect("device-unavailable", self.device_unavailable)

    self.ui = PyGUPnPCPUI(self)
    self.ui.main()

  def stop_object(self, source, renderer, item):
    av_serv = self.get_av_for_renderer(renderer)
    data = {"InstanceID": 0}
    av_serv.send_action_hash("Stop", data, {})

  def pause_object(self, source, renderer, item):
    print "Sending Pause"
    av_serv = self.get_av_for_renderer(renderer)
    data = {"InstanceID": 0}
    print "Pre action"
    av_serv.send_action_hash("Pause", data, {})
    print "post action"

  def get_av_for_renderer(self, renderer):
    services = self.device_mgr.device_services[renderer.get_udn()]
    av_serv = None
    for s in services:
      if "AVTransport" in s.get_service_type():
        av_serv = s
        break
    return av_serv
    
  def play_object(self, source, renderer, item):
    resources = None
    if item:
       resources = item.get_resources()
 
    uri = ""
    av_serv = self.get_av_for_renderer(renderer) 

    if resources:
      uri = resources[0].get_uri()
      data = {"InstanceID": "0", "CurrentURI": uri, "CurrentURIMetaData": uri} 
    
      act = UPnPAction(renderer,
                     av_serv,
                     "SetAVTransportURI",
                     data)

      self.execute_action(act)

    print "Sending action..."
    data = {"InstanceID": "0", "CurrentURI": uri, "CurrentURIMetaData": uri, "Speed": 1} 
    act = UPnPAction(renderer,
                     av_serv,
                     "Play",
                     data)

    self.execute_action(act)


  def execute_action(self, action):
    if not action.is_executable():
      device = action.device_udn
      services = self.device_services[device]
      for s in services:
        if s.get_udn() == action.service_udn:
          action.service = s

    action.execute()

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
    serv = self.device_mgr.is_source(device.get_udn())
    assert serv

    in_data = {"ObjectID": object_id, "BrowseFlag": "BrowseDirectChildren",
               "Filter": "*", "StartingIndex": "0", "RequestCount": "0",
               "SortCriteria": ""}

    return_data = serv.begin_action_hash("Browse", self.children_loaded, None, in_data)
    if not return_data:
      print "Error initiating the Browse action"
  
  def device_available(self, mgr, device):
    print "%s (%s) is now available" % (device.get_model_name(), device.get_friendly_name())

    if device.is_source:
      self.ui.add_source(device, device.icon_file)

    if device.is_renderer:
      self.ui.add_renderer(device, device.icon_file)

  def device_unavailable(self, mgr, device):
    print "%s has disappeared!" % device.get_model_name()

    if device.is_source:
      self.ui.remove_source(device)
        
    if device.is_renderer:
      self.ui.remove_renderer(device)

if __name__ == "__main__":
  prog = PyGUPnPCP()
  prog.main()


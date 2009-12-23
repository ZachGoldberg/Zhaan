from gi.repository import GLib, GUPnP, GUPnPAV, GSSDP, GObject, libsoup
import os, urllib2, tempfile, atexit
import pygtk, gtk

from gui import PyGUPnPCPUI
from action import UPnPAction

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

    # Get a default maincontext
    self.main_ctx = GLib.main_context_default() 

    self.ctx_mgr = GUPnP.ContextManager.new(self.main_ctx, 0)
    self.ctx_mgr.connect("context_available", self.new_ctx)

#    GObject.timeout_add(3000, self.list_cur_devices)

    self.ui = PyGUPnPCPUI(self)
    self.ui.main()

  def new_ctx(self, ctx_mgr, ctx):

    self.contexts.append(ctx)

    # Bind to the context in the maincontext on any port
    cp  = GUPnP.ControlPoint().new(ctx, "upnp:rootdevice")

    # Use glib style .connect() as a callback on the controlpoint to listen for new devices
    cp.connect("device-proxy-available", self.device_available)
    cp.connect("device-proxy-unavailable", self.device_unavailable)

    # "Tell the Control Point to Start Searching"
    GSSDP.ResourceBrowser.set_active(cp, True)
    
    self.cps.append(cp)

  def list_cur_devices(self):
    for d in self.devices:
      print "Device: %s (%s)" % (d.get_model_name(), d.get_udn())
      for s in self.device_services[d.get_udn()]:
        print "\tService: %s" % s.get_service_type()
        if not s.get_udn() in self.introspections:
          continue
        for a in self.introspections[s.get_udn()].list_actions():
          print "\t\tAction: %s" % a.name
          
    print "Current Sources:"
    for i in self.sources:
      print "\t%s (%s)" % (i.get_model_name(), i.get_udn())

    print "Current Renderers:"
    for i in self.renderers:
      print "\t%s (%s)" % (i.get_model_name(), i.get_udn())

    print "-" * 30

    return True

  def is_source(self, device):
    if not isinstance(device, basestring):
      device = device.get_udn()
  
    if not device in self.device_services:
      return False
  
    for s in self.device_services[device]:
      if "ContentDirectory" in s.get_service_type():
        return s
  
    return False

  def is_renderer(self, device):
    if not isinstance(device, basestring):
      print device.get_friendly_name()
      device = device.get_udn()
  
    if not device in self.device_services:
      return False


    for s in self.device_services[device]:
      print s.get_service_type()
      if "AVTransport" in s.get_service_type():
        return s
  
    return False


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
    services = self.device_services[renderer.get_udn()]
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
    serv = self.is_source(device.get_udn())
  
    assert serv

    in_data = {"ObjectID": object_id, "BrowseFlag": "BrowseDirectChildren",
               "Filter": "*", "StartingIndex": "0", "RequestCount": "0",
               "SortCriteria": ""}

    return_data = serv.begin_action_hash("Browse", self.children_loaded, None, in_data)
    if not return_data:
      print "Error initiating the Browse action"
  
  def server_introspection(self, service, introspection, error, userdata):
    self.introspections[service.get_udn()] = introspection

  def device_available(self, cp, device):
    print "%s (%s) is now available" % (device.get_model_name(), device.get_friendly_name())

    for d in self.devices:
	if d.get_udn() == device.get_udn():
          # We can only assume that the old one dropped off the network
          # and didn't tell us about it.  So manually remove it then proceed
          # to readd.
          print "Duplicate device online?  Removing old entry"
	  self.device_unavailable(cp, d)

    self.devices.append(device)
  
    (icon_url, _, _, _, _) = device.get_icon_url(None, 32, 22, 22, False)
    icon_file = None
    if icon_url:
      try:
        data = urllib2.urlopen(icon_url)
        f, icon_file = tempfile.mkstemp()
        os.write(f, ''.join(data.readlines()))
        os.close(f)
      except urllib2.URLError:
        pass
     
    self.device_services[device.get_udn()] = device.list_services()
    
    for s in self.device_services[device.get_udn()]:
      s.get_introspection_async(self.server_introspection, None)

    if self.is_source(device):
      self.sources.append(device)
      self.ui.add_source(device, icon_file)

    if self.is_renderer(device):
      self.renderers.append(device)
      self.ui.add_renderer(device, icon_file)

    if icon_file:
      self.created_files.append(icon_file)

  def device_unavailable(self, cp, device):
    print "%s has disappeared!" % device.get_model_name()
    for d in self.devices:
      if d.get_udn() == device.get_udn():
        self.devices.remove(d)


    for d in self.sources:
      if d.get_udn() == device.get_udn():
        self.sources.remove(d)
        self.ui.remove_source(d)
        
    for d in self.renderers:
      if d.get_udn() == device.get_udn():
        self.renderers.remove(d)
        self.ui.remove_renderer(d)

if __name__ == "__main__":
  prog = PyGUPnPCP()
  prog.main()







#  for service in device_services[device.get_udn()]:
#      introspections.remove(service.get_udn())

#  if device.get_model_name() == "MediaTomb":
#      for service in device.list_services():
#          print service.get_service_type()
#          if "ContentDirectory" in service.get_service_type():
#              service.get_introspection_async(server_introspection, None)



#  actions = intro.list_actions()
#  print len(actions)
#  for i in actions:
#      print service.get_service_type(), i.name      
#      if i.name == "SetAVTransportURI":
#          dict = {"Speed": "1", "InstanceID": "0"}
#          muri = "http://192.168.1.55:49152/content/media/object_id=6327&res_id=0&ext=.mp3"
#          curi = "http://192.168.1.55:49152/content/media/object_id=6327&res_id=0&ext=.mp3"
#          data = {"InstanceID": "0", "CurrentURI": curi, "CurrentURIMetaData": muri} 
#          service.send_action_hash(i.name, data, {})
#	  print "Done setting URI"
#          data2 = {"Speed": "1", "InstanceID": "0"}
#          service.send_action_hash("Stop", {"InstanceID": 0}, {})
#          print "Done Stopping"
#          service.send_action_hash("Play", data2, {})


  

#def server_introspection(service, introspection, error, userdata):
#  print "Got server introspection"
#  for i in introspection.list_actions():
#      if i.name == "Browse":
#         in_data = {"ObjectID": "0", "BrowseFlag": "BrowseDirectChildren",
#		    "Filter": "", "StartingIndex": "0", "RequestCount": "0",
#		    "SortCriteria": ""}
#         out_data = {"Result": "", "NumberReturned": "", "TotalMatches": "", "UpdateID": ""}#
#	 print "SEND ACTION"
#         return_data = service.send_action_hash("Browse", in_data, out_data)
#	 global serv
#	 serv=service
#	 print "Good news!"
#	 print return_data[1]["Result"]
#	 parser = GUPnPAV.GUPnPDIDLLiteParser()
#	 parser.connect("container_available", new_container)
#	 parser.connect("item_available", new_item)
#	 parser.parse_didl(return_data[1]["Result"])
#	 print len(objects)


from gi.repository import GObject, GUPnP, GLib, GSSDP
import urllib2, tempfile, os, atexit

class UPnPDeviceManager(GObject.GObject):

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
      device = device.get_udn()
  
    if not device in self.device_services:
      return False
  
    for s in self.device_services[device]:
      if "AVTransport" in s.get_service_type():
        return s
  
    return False

  def activate_action(self, action):
    if not action:
      return

    if action.is_activated():
      if action.device.valid:
        return

    device = None
    for d in self.devices:
      if d.get_udn() == action.device_udn:
        device = d

    service = None  
    for s in self.device_services.get(action.device_udn, []):
      if s.get_service_type() == action.service_type:
        service = s

    action.activate(device, service)

  def __init__(self):
      
      super(UPnPDeviceManager, self).__init__()
      GObject.threads_init()
      GObject.signal_new("device-available", UPnPDeviceManager, 
                         GObject.SIGNAL_RUN_LAST, 
                         GObject.TYPE_BOOLEAN, (GObject.TYPE_PYOBJECT,))

      GObject.signal_new("device-unavailable", UPnPDeviceManager, 
                         GObject.SIGNAL_RUN_LAST, 
                         GObject.TYPE_BOOLEAN, (GObject.TYPE_PYOBJECT,))

      atexit.register(self.cleanup_files)

      self.contexts = []
      self.cps = []
      self.devices = []
      self.sources = []
      self.renderers = []
      self.device_services = {}
      self.introspections = {}
      self.created_files = []

      # Get a default maincontext
      self.main_ctx = GLib.main_context_default() 
        
      # Use the built in GUPnP Network Manager to listen on 
      # all interfaces      
      self.ctx_mgr = GUPnP.ContextManager.new(self.main_ctx, 0)
      self.ctx_mgr.connect("context_available", self.new_ctx)

      self.new_ctx(self.ctx_mgr, GUPnP.Context(interface="eth0"))

  def cleanup_files(self):
    for i in self.created_files:
      os.unlink(i)

  def new_ctx(self, ctx_mgr, ctx):
      self.contexts.append(ctx)

      # Bind to the context in the maincontext on any port
      cp  = GUPnP.ControlPoint().new(ctx, "upnp:rootdevice")
      

      cp.connect("device-proxy-available", self.device_available)
      cp.connect("device-proxy-unavailable", self.device_unavailable)
        
      # "Tell the Control Point to Start Searching"
      GSSDP.ResourceBrowser.set_active(cp, True)
    
      self.cps.append(cp)

  def get_service_on_device(self, device, service_type):
    services = []
    try:
      if isinstance(device, basestring):      
        services = self.device_services[device]
      else:
        services = self.device_services[device.get_udn()]
    except:
      return None

    for service in services:
      if service_type in service.get_service_type():
        return service

    return None


  def device_available(self, cp, device):
    for d in self.devices:
	if d.get_udn() == device.get_udn():
          print "Duplicate device online?  Ignoring new entity."
          return
         
    self.devices.append(device)

    
    (icon_url, _, _, _, _) = device.get_icon_url(None, 32, 22, 22, False)
    device.icon_file = None
    if icon_url:
      try:
        data = urllib2.urlopen(icon_url)
        f, device.icon_file = tempfile.mkstemp()
        os.write(f, ''.join(data.readlines()))
        os.close(f)
        self.created_files.append(device.icon_file)

      except urllib2.URLError:
        pass
     
    self.device_services[device.get_udn()] = device.list_services()
    
    for s in self.device_services[device.get_udn()]:
      s.get_introspection_async(self.server_introspection, None)

    device.is_source = False
    device.is_renderer = False
    device.valid = True
    
    if self.is_source(device):
      self.sources.append(device)
      device.is_source = True

    if self.is_renderer(device):
      self.renderers.append(device)
      device.is_renderer = True

    self.emit("device-available", device)

  def device_unavailable(self, cp, device):
    original = None
    for d in self.devices:
      if d.get_udn() == device.get_udn():
        self.devices.remove(d)
        original = d
        # Ensure that nobody uses the old reference
        d.valid = False

    for d in self.sources:
      if d.get_udn() == device.get_udn():
        self.sources.remove(d)
        
    for d in self.renderers:
      if d.get_udn() == device.get_udn():
        self.renderers.remove(d)

    self.device_services[d.get_udn()] = []
    self.emit("device-unavailable", original)

  def server_introspection(self, service, introspection, error, userdata):
    self.introspections[service.get_udn()] = introspection

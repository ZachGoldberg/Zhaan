import simplejson

class UPnPAction(object):
    def __init__(self, device, service, action, data, next_action=False):
        
        if isinstance(device, basestring):
            self.device_udn = device
            self.device = None
        else:
            self.device = device
            self.device_udn = device.get_udn()

        if isinstance(service,  basestring):
            self.service_type = service
            self.service = None
        else:
            self.service = service
            self.service_type = service.get_service_type()

        self.action = action
        self.data = data

        self.next_action = next_action

    
    def register_device_manager(self, device_mgr):
        self.device_mgr = device_mgr
        
    def activate(self, device, service):
        self.device = device
        self.service = service
        if self.is_activated():
            print "ACTIVATED", self.device, self.service
        else:
            print "INACTIVATED", self.device, self.service

    def execute(self):
        if self.is_executable():
            try:
                self.service.send_action_hash(str(self.action), self.data, {})
            except:
                print "Error sending action"
        else:
            print "Error -- Tried to execute an action that hasn't been activated"


    def is_activated(self):
        return bool(self.service)
    
    def is_executable(self):
        if not hasattr(self, "device_mgr") or not self.device_mgr:
            print "Error - You must register a device manager with this action before you can execute it"
            
        self.device_mgr.activate_action(self)
        if self.next_action:        
            return self.is_activated() and self.next_action.is_executable()
        else:
            return self.is_activated()
    
    def dumps(self):
        next_action = None
        if self.next_action:
            next_action = self.next_action.dumps()
            
        return simplejson.dumps({
            "device": self.device_udn,
            "service": self.service_type,
            "action": self.action,
            "data": simplejson.dumps(self.data),
            "next_action": next_action,
                })

    @classmethod
    def loads(claz, datas):
        data = simplejson.loads(datas)
        next_action = None
        if "next_action" in data and data["next_action"]:
            next_action = UPnPAction.loads(data["next_action"])
            
        return UPnPAction(
            data["device"],
            data["service"],
            data["action"],
            simplejson.loads(data["data"])          
            )

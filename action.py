import simplejson

class UPnPAction(object):
    def __init__(self, device, service, action, data):
        
        if isinstance(device, basestring):
            self.device_udn = device
            self.device = None
        else:
            self.device = device
            self.device_udn = device.get_udn()

        if isinstance(service,  basestring):
            self.service_udn = service
            self.service = None
        else:
            self.service = service
            self.service_udn = service.get_udn()

        self.action = action
        self.data = data

    def execute(self):
        if self.is_executable():
            print "Send action"
            self.service.send_action_hash(self.action, self.data, {})
            print "Send action done"

    def is_executable(self):
        return bool(self.service)

    def dumps(self):
        return simplejson.dumps({
                "device": self.device_udn,
                "service": self.service_udn,
                "action": self.action,
                "data": simplejson.dumps(self.data)
                })

    @classmethod
    def loads(datas):
        data = simplejson.loads(datas)
        return UPnPAction(
            data["device"],
            data["service"],
            data["action"],
            simplejson.loads(data["data"])
            )

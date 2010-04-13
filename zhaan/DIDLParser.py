from gi.repository import GUPnPAV

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


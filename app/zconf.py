import time
import socket
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf



class MyListener(ServiceListener):

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} updated")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        if not hasattr(self,'kodis'):
            self.kodis = []

        info = zc.get_service_info(type_, name)
        
        if 'Kodi' in name:
            ip = socket.inet_ntoa(info.addresses[0])
            port = info.port
            self.kodis.append({'name':name.split('._')[0],'host':ip,'port':port})

def scan_for_kodi():
    zeroconf = Zeroconf()
    listener = MyListener()
    browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)

    time.sleep(2)

    zeroconf.close()
    if hasattr(listener,'kodis'):
        return listener.kodis
    else:
        return []
        
if __name__ == '__main__':
    print(scan_for_kodi())

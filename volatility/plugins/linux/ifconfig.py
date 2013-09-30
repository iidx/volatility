# Volatility
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details. 
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA 

"""
@author:       Andrew Case
@license:      GNU General Public License 2.0 or later
@contact:      atcuno@gmail.com
@organization: Digital Forensics Solutions
"""

import volatility.plugins.linux.common as linux_common
import volatility.debug as debug
import volatility.obj as obj

class linux_ifconfig(linux_common.AbstractLinuxCommand):
    """Gathers active interfaces"""

    def _get_devs_base(self):
        net_device_ptr = obj.Object("Pointer", offset = self.addr_space.profile.get_symbol("dev_base"), vm = self.addr_space)
        net_device = net_device_ptr.dereference_as("net_device")

        for net_dev in linux_common.walk_internal_list("net_device", "next", net_device):
            yield net_dev

    def _get_devs_namespace(self):
        nslist_addr = self.addr_space.profile.get_symbol("net_namespace_list")
        nethead = obj.Object("list_head", offset = nslist_addr, vm = self.addr_space)

        # walk each network namespace
        # http://www.linuxquestions.org/questions/linux-kernel-70/accessing-ip-address-from-kernel-ver-2-6-31-13-module-815578/
        for net in nethead.list_of_type("net", "list"):

            # walk each device in the current namespace
            for net_dev in net.dev_base_head.list_of_type("net_device", "dev_list"):
                yield net_dev

    def _gather_net_dev_info(self, net_dev):
        mac_addr = net_dev.mac_addr
        promisc  = str(net_dev.promisc)

        in_dev = obj.Object("in_device", offset = net_dev.ip_ptr, vm = self.addr_space)
        
        for dev in in_dev.devices():
            ip_addr = dev.ifa_address.cast('IpAddress')
            name    = dev.ifa_label
            yield (name, ip_addr, mac_addr, promisc)

    def calculate(self):
        linux_common.set_plugin_members(self)

        # newer kernels
        if self.addr_space.profile.get_symbol("net_namespace_list"):
            for net_dev in self._get_devs_namespace():
                for ip_addr_info in self._gather_net_dev_info(net_dev):
                    yield ip_addr_info

        elif self.addr_space.profile.get_symbol("dev_base"):
            for net_dev in self._get_devs_base():
                for ip_addr_info in self._gather_net_dev_info(net_dev):
                    yield ip_addr_info
        
        else:
            debug.error("Unable to determine ifconfig information")
        
    def render_text(self, outfd, data):

        self.table_header(outfd, [("Interface", "16"),
                                  ("IP Address", "20"),
                                  ("MAC Address", "18"),
                                  ("Promiscous Mode", "5")])

        for (name, ip_addr, mac_addr, promisc) in data:
            self.table_row(outfd, name, ip_addr, mac_addr, promisc)


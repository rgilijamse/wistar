import libvirt
from lxml import etree

conn = None
is_init = False

# FIXME - improve error handling here... lots of catching and smothering exceptions...


def connect():
    global is_init
    global conn
    if is_init is True:
        return True
    else:
        conn = libvirt.open(None)
        if conn is None:
            raise Exception("Could not connect to hypervisor")
        else:
            is_init = True
            return True


def close():
    global is_init
    if is_init is True:
        conn.close()
        is_init = False


def get_network_by_name(network_name):
    connect()

    try:
        return conn.networkLookupByName(network_name)

    except Exception as e:
        print str(e)
        raise Exception("Could not get network by name")


def get_domain_by_uuid(domain_id):
    connect()

    try:
        return conn.lookupByUUIDString(domain_id)

    except Exception as e:
        print str(e)
        raise Exception("Could not get domain by uuid")


def domain_exists(domain_name):
    connect()

    try:
        domains = conn.listAllDomains(0)
        for d in domains:
            if d.name() == domain_name:
                return True

        return False

    except Exception as ee:
        print repr(ee)
        return False


def promote_instance_to_image(domain_name):
    """
    Takes a domains instance file and performs a
    blockPull operation. This results in the instance file
    being a fully self sustained file that can be used as a
    standalone image

    :param domain_name: domain name string
    :return: None Block already completed
    :return: False Error condition
    :return True Block pull started
    """
    connect()

    try:
        domain = get_domain_by_name(domain_name)
        image_path = get_image_for_domain(domain.UUIDString())

        if domain.blockJobInfo(image_path, 0) != {}:
                print "block job already in progress"
                return None 

        print "Performing blockPull on " + image_path
        domain.blockPull(image_path, 0, 0)
        return True

    except Exception as e:
        print str(e)
        return False


def is_image_in_block_pull(domain, image_path):
    if domain.blockJobInfo(image_path) != {}:
        print "block job already in progress"
        return True
    else:
        return False


def get_domain_by_name(domain_name):
    """ Get single domain by name """
    connect()

    domains = conn.listAllDomains(0)
    for d in domains:
        if d.name() == domain_name:
            return d

    raise Exception("Could not get domain by name")


# convenience function to check if a domain is currently started
def is_domain_running(domain_name):
    try:
        domain = get_domain_by_name(domain_name)

        if domain.info()[0] == 1:
            return True

        return False

    except Exception as e:
        print str(e)
        return False


def list_domains():
    """ Get all domains """
    connect()

    domain_list = []
    try:
        domains = conn.listAllDomains(0)
        for d in domains:
            domain = dict()
            domain["name"] = d.name()
            domain["id"] = d.ID()
            domain["uuid"] = d.UUIDString()
            if d.info()[0] == 1:
                domain["state"] = "running"
            else:
                domain["state"] = "shut off"
            domain_list.append(domain)

        domain_list.sort(key=lambda k: k["name"])
        return domain_list
    except Exception as e:
        print str(e)
        raise Exception("Could not list domains")


def get_domains_for_topology(topology_id):
    """ Get all domains for a given topology Id """
    connect()

    domain_list = []
    try:
        domains = list_domains()
        for d in domains:
            if d["name"].startswith(topology_id):
                domain_list.append(d)

        return domain_list
    except Exception as e:
        print str(e)
        raise Exception("Could not list domains")


def undefine_all_in_topology(topology_id):

    network_list = get_networks_for_topology(topology_id)
    for network in network_list:
        print "Undefining network: " + network["name"]
        undefine_network(network["name"])

    domain_list = get_domains_for_topology(topology_id)
    for domain in domain_list:
        print "undefining domain: " + domain["name"]
        undefine_domain(domain["uuid"])


def network_exists(network_name):
    connect()

    try:
        networks = conn.listAllNetworks(0)
        for n in networks:
            if n.name() == network_name:
                return True

        return False

    except Exception as e:
        print repr(e)
        return False


def list_networks():
    connect()

    network_list = []
    try:
        networks = conn.listAllNetworks(0)
        for n in networks:
            network = dict()
            network["name"] = n.name()
            network["uuid"] = n.UUID()
            if n.isActive() == 1:
                network["state"] = "running"
            else:
                network["state"] = "shut off"
            network_list.append(network)

        network_list.sort(key=lambda k: k["name"])
        return network_list
    except Exception as e:
        print str(e)
        raise Exception("Could not list networks")


def get_networks_for_topology(topology_id):
    """ Get Networks for a given topology Id """
    connect()

    network_list = []

    networks = list_networks()
    for n in networks:
        if n["name"].startswith(topology_id):
            network_list.append(n)

    return network_list


# blow away everything and start from scratch!
def reset_kvm():
    domains = list_domains()
    networks = list_networks()
    for n in networks:
        if n["name"] != "default":
            network = get_network_by_name(n["name"])
            if network.isActive() == 1:
                network.destroy()

            network.undefine()

    for d in domains:
        domain = get_domain_by_uuid(d["uuid"])
        if domain.info()[0] == 1:
            domain.destroy()
        domain.undefine()


# defines domain from supplied xml file. use wistarUtils to create said XML
def define_domain_from_xml(xml):
    connect()

    try:
        domain = conn.defineXML(xml)
        print "Defined Domain: " + domain.name()

        return domain
    except Exception as e:
        print str(e)
        raise Exception("Could not define domain")


def define_network_from_xml(xml):
    connect()

    try:
        network = conn.networkDefineXML(xml)
        print "Defined Network: " + network.name()

        return network
    except Exception as e:
        print str(e)
        raise Exception("Could not define network")


def undefine_domain(domain_id):
    connect()

    try:
        domain = get_domain_by_uuid(domain_id)

        if domain.hasManagedSaveImage(0):
            print "Removing saved state for domain " + domain.name()
            domain.managedSaveRemove(0)

        if domain.info()[0] == 1:
            domain.destroy()

        domain.undefine()
        return True

    except Exception as e:
        print str(e)
        return False


def stop_domain(domain_id):
    connect()

    try:
        domain = get_domain_by_uuid(domain_id)
        domain.destroy()
        return True

    except Exception as e:
        print str(e)
        return False


def suspend_domain(domain_id):
    connect()

    try:
        domain = get_domain_by_uuid(domain_id)
        domain.managedSave(0)
        return True

    except Exception as e:
        print str(e)
        return False


def start_domain(domain_id):
    connect()

    try:
        domain = get_domain_by_uuid(domain_id)
        if domain.info()[0] != 1:
            domain.create()
        return True

    except Exception as e:
        print str(e)
        return False


def start_domain_by_name(domain_name):
    try:
        d = get_domain_by_name(domain_name)
        if d.info()[0] != 1:
            d.create()

        return True

    except Exception as e:
        print str(e)
        return False


def undefine_network(network_name):
    connect()

    # cannot delete default domain!
    if network_name == "default":
        return False

    try:
        network = get_network_by_name(network_name)
        if network.isActive() == 1:
            print "Stopping network before destroy"
            network.destroy()

        network.undefine()
        return True

    except Exception as e:
        print str(e)
        return False


def stop_network(network_name):
    connect()

    # cannot delete default domain!
    if network_name == "default":
        return False

    try:
        network = get_network_by_name(network_name)
        network.destroy()
        return True

    except Exception as e:
        print str(e)
        return False


def start_network(network_name):
    print "Starting network " + str(network_name)
    connect()

    # cannot delete default domain!
    if network_name == "default":
        return False

    try:
        network = get_network_by_name(network_name)
        if network.isActive() != 1:
            network.create()
        return True

    except Exception as e:
        print str(e)
        return False


def get_domain_vnc_port(domain):
    xml = domain.XMLDesc(0)
    doc = etree.fromstring(xml)
    graphics_el = doc.find(".//graphics")
    if graphics_el is not None:
        graphics_type = graphics_el.get("type")
        if graphics_type == "vnc":
            vnc_port = graphics_el.get("port")
            return vnc_port
        else:
            return 0
    else:
        return 0


# simple func to ensure we always use a valid vnc_port
def get_next_domain_vnc_port(offset=0):
    print "Getting next vnc port with offset: " + str(offset)
    current_iteration = 0
    connect()

    used_ports = []
    domains = conn.listAllDomains(0)
    for d in domains:
        vnc_port = get_domain_vnc_port(d)
        try:
            port = int(vnc_port)
            if port != 0 and port != -1:
                used_ports.append(port)
        except Exception as e:
            # in some cases,port can be something other than int like None
            # just catch all the here and continue on
            print "found unhandled error for vnc_port! " + str(vnc_port)
            print str(e)
            continue

    if len(used_ports) > 1:
        used_ports.sort()
        print str(used_ports)
        last = used_ports[0]
        maximum = used_ports[-1]
        for p in used_ports:

            if (int(p) - int(last)) > 1:
                next_port = int(last) + 1
                if current_iteration == offset:
                    print "retuning " + str(next_port)
                    return str(next_port)
                else:
                    print "keep going:" + str(next_port)
                    current_iteration += 1
                    last = p
            else:
                last = p

        # we ran through all the ports and didn't find a gap we can re-use
        next_port = int(maximum) + 1 + int(offset)
        print "returning max+1+offset: " + str(next_port)
        return next_port
    else:
        print "No vnc ports currently in use"
        return int(5900) + offset


def get_image_for_domain(domain_id):
    """
    :param domain_id: uuid of the domain
    :return: the path to the image file
    """
    domain = get_domain_by_uuid(domain_id)
    xml = domain.XMLDesc(0)
    doc = etree.fromstring(xml)
    source_el = doc.find(".//source")
    if source_el is not None:
        source_file = source_el.get("file")
        return source_file
    else:
        return None


def attach_iso_to_domain(domain_name, file_path):
    try:
        xml = """<disk type='file' device='cdrom'>
          <driver name='qemu' type='raw'/>
          <source file='{0:s}'/>
          <target dev='hdc' bus='ide'/>
          <readonly/>
          <address type='drive' controller='0' bus='0' target='0' unit='1'/>
        </disk>""".format(file_path)

        print xml

        domain = get_domain_by_name(domain_name)
        domain.updateDeviceFlags(xml, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        return True
    except Exception as e:
        print str(e)
        return False


def detach_iso_from_domain(domain_name):
    try:
        xml = """<disk type='file' device='cdrom'>
          <driver name='qemu' type='raw'/>
          <source file=''/>
          <target dev='hdc' bus='ide'/>
          <readonly/>
          <address type='drive' controller='0' bus='0' target='0' unit='1'/>
        </disk>"""

        print xml

        domain = get_domain_by_name(domain_name)
        domain.updateDeviceFlags(xml, libvirt.VIR_DOMAIN_AFFECT_CONFIG)
        return True
    except Exception as e:
        print str(e)
        return False


def get_iso_for_domain(domain_name):
    """
    :param domain_name: name of the domain
    :return: the path to the iso file
    """
    domain = get_domain_by_name(domain_name)
    xml = domain.XMLDesc(0)
    doc = etree.fromstring(xml)
    source_el = doc.find(".//disk[@device='cdrom']/source")
    if source_el is not None:
        source_file = source_el.get("file")
        return source_file
    else:
        return None


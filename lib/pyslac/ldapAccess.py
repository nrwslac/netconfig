#!/usr/bin/python
# LDAP access routines specific to SLAC network

import ldap
import ldapurl
import sys
import re

class ldapObject:
    """This class is an object oriented representation of an LDAP directory
    each node in the directory is an object and you can access children and 
    parent, but you cannot search"""

    def __init__(self, ldapAccess, dn):
        "Constructor"
        self.dn = dn
        self.ldapAccess = ldapAccess
        self.attr = ldapAccess.get_attributes(dn)
    
    def get_attr(self, attr = None):
        """If attr is None return a dictionary containing all the attributes
        of this LDAP node, otherwise return a list that contain all values for
        the attribute in argument"""
        if attr == None:
            return self.attr
        if not self.attr.has_key(attr):
            return []
        return self.attr[attr]
    
    def add_attr(self, attr, val):
        """Add an attribute to this LDAP object and set its value to val
        if the attribute already exist, a new attribute will still be created"""
        if attr == None:
            raise ValueError, "add_attr require a valid attribute"
        modlist = [ (ldap.MOD_ADD, attr, val) ]
        self.ldapAccess.get_ldap_handle().modify_s(self.dn, modlist)
        return
    
    def del_attr(self, attr, val = None):
        """If val is None delete all values of attr, otherwise delete only
        a specific value"""
        if attr == None:
            raise ValueError, "add_attr require a valid attribute"
        modlist = [ (ldap.MOD_DELETE, attr, val) ]
        self.ldapAccess.get_ldap_handle().modify_s(self.dn, modlist)
        return
    
    def set_attr(self, attr, val):
        """Replace the value of attribute to this LDAP object with val"""
        if attr == None:
            raise ValueError, "set_attr require a valid attribute"
        modlist = [ (ldap.MOD_REPLACE, attr, val) ]
        self.ldapAccess.get_ldap_handle().modify_s(self.dn, modlist)
        return
    
    def get_children(self, lstTupplesSearch = None):
        """Look for children that match lstTupplesSearch criteria (logical
        AND of all the (attribute, value) pairs in the list
        This API returns a list of ldapObject"""
        if lstTupplesSearch == None:
            lstTupplesSearch = [("objectClass", "*")]
        lst = []
        for dn in self.ldapAccess.get_dn_by_attribute(lstTupplesSearch, self.dn):
            lst.append(ldapObject(self.ldapAccess, dn))
        return lst
    
    def get_parent(self):
        "Return an ldapObject representing the parent of this object"
        return ldapObject(self.ldapAccess, self.ldapAccess.get_parent(self.dn))

    def get_dn(self):
        "Return the Dinstinguished Name of the LDAP Object"
        return self.dn

    def del_modify_add( self, attr, value ):
        """If the specified value is not among the existing
        values for the specified attribute, then add the
        attribute to the attribute list, delete the LDAP dn
        and re-add this object to LDAP with the modified
        attribute: this is needed when the LDAP syntax doesn't
        allow comparions between attribute values (eg for
        nisNetgroupTriple)"""
        if attr is None or value is None:
            raise RuntimeError, "Neither argument may be null"
        if attr not in self.attr:
            self.attr[attr] = []
        if value not in self.attr[attr]:
            self.attr[attr].append(value)
            addlist = []
            for key in self.attr:
                addlist.append((key, self.attr[key]))
            self.ldapAccess.get_ldap_handle().delete_s(self.dn)
            self.ldapAccess.get_ldap_handle().add_s(self.dn, addlist)
            return True
        else:
            return False

    def del_modify_del( self, attr, value ):
        if attr is None or value is None:
            raise RuntimeError, "Neither argument may be null"
        if value in self.attr[attr]:
            self.attr[attr].remove(value)
            addlist = []
            for key in self.attr:
                addlist.append((key, self.attr[key]))
            self.ldapAccess.get_ldap_handle().delete_s(self.dn)
            self.ldapAccess.get_ldap_handle().add_s(self.dn, addlist)
            return True
        else:
            return False

class ldapAccess:
    """This class is a wrapper around the python LDAP access library
    that makes some assumptions about the configuration in order to
    simplify access to the database. It also contains some helper
    methods to access SLAC specific LDAP objects and attributes"""
    
    def __init__(self, who = None, cred = "", method = "", auth = None):
        # Parse the openldap config file
        try:
            configfile=open("/etc/openldap/ldap.conf")
            regexBase = re.compile("^BASE\s+(.*)$")
            regexHost = re.compile("^URI\s+(.*)$")
            for line in configfile.xreadlines():
                find = regexBase.search(line)
                if find != None:
                    self.dnBase=find.expand(r"\1").strip()
                else:
                    find = regexHost.search(line)
                    if find != None:
                        self.strLDAPServer=find.expand(r"\1").strip()
#                       if self.strLDAPServer.startswith('ldap://'):
#                           self.strLDAPServer = self.strLDAPServer[7:]
#                           self.strLDAPServer = self.strLDAPServer.rstrip('/')
            if self.dnBase == None:
                raise RuntimeError, "No BASE statement in config file"
            if self.strLDAPServer == None:
                raise RuntimeError, "No HOST statement in config file"
            servers=self.strLDAPServer.split()

        except:
            raise RuntimeError, "could not read LDAP configuration: %s (line %d)" % (sys.exc_value, sys.exc_traceback.tb_lineno)
        # Open the LDAP database
        connected = "N"
        for strLDAPServer in servers:
            try:
                # print "Connecting to %s" %strLDAPServer
                #ldapdb_url=ldapurl.LDAPUrl(hostport=strLDAPServer, dn=self.dnBase)
                ldapdb_url=ldapurl.LDAPUrl(strLDAPServer + "/" + self.dnBase)
                self.ldapHandle=ldap.initialize(ldapdb_url.unparse())
                if who == None:
                    # Bind as user anonymous
                    self.ldapHandle.simple_bind_s()
                elif auth == None:
                    # Bind using the simple authentication
                    self.ldapHandle.bind_s(who, cred, method)
                else:
                    self.ldapHandle.sasl_interactive_bind_s(who, auth)
                connected = "Y"
                break
            except:
                print "Unable to connect to server. Will try the next one."
            if (connected == "N"):  
                raise RuntimeError, "could not connect to LDAP: %s (line %d)" % (sys.exc_value, sys.exc_traceback.tb_lineno)
    
    def get_ldap_handle(self):
        "Return a handle to the python LDAP library object"
        return self.ldapHandle
    
    def get_dnbase(self):
        "Return the base DN being used"
        return self.dnBase

    def get_hostdn_by_alias(self, strAlias, strSubnet = None):
        "Get a node DN by looking for its alias"
        dnSearch = "ou=Subnets," + self.dnBase
        if strSubnet != None:
            dnSearch = "dc=" + strSubnet + "," + dnSearch
        try:
            dn = self.ldapHandle.search_s(dnSearch, ldap.SCOPE_SUBTREE, \
                "(&(objectClass=hostObject)(|(cn=" + strAlias + ")(alias=" + strAlias + ")))")[0][0]
            return dn
        except:
            raise NameError, "%s not found" % (strAlias)
    
    def get_hostdn_by_cname(self, strCname, strSubnet = None):
        "Get a node DN by looking for its cname"
        dnSearch = "ou=Subnets," + self.dnBase
        if strSubnet != None:
            dnSearch = "dc=" + strSubnet + "," + dnSearch
        try:
            dn = self.ldapHandle.search_s(dnSearch, ldap.SCOPE_SUBTREE, \
                "(&(objectClass=hostObject)(|(cn=" + strCname + ")(cname=" + strCname + ")))")[0][0]
            return dn
        except:
            raise NameError, "%s not found" % (strCname)
    def get_attributes(self, dnNode, attr = None):
        """Return all or a list of attributes of a node, the return value is
        of type DictType with each element being a list of values"""
        try:
            node = self.ldapHandle.search_s(dnNode, ldap.SCOPE_BASE, "(objectClass=*)", attr)[0]
            return node[1]
        except:
            try:
                self.ldapHandle.search_s(dnNode, ldap.SCOPE_BASE, "(objectClass=*)")
            except:
                raise NameError, "%s not found" % (dnNode)
            raise AttributeError, "one of those attributes does not exist in %s: %s" % (dnNode, ", ".join(attr))

    def get_cn( self, dnNode ):
        """Return the cn (common name) for this dn (distinguised name)"""
        try:
            return self.get_attributes( dnNode, ["cn"] )["cn"][0]
        except:
            raise NameError, "Invalid dn %s" % (dnNode)

    def get_dn_by_attribute(self, lstTupplesSearch, dnBase = None, scope = ldap.SCOPE_SUBTREE):
        """Search for a list of nodes whose attributes match the description in a subtree dnBase,
        if dnBase is not specified this API will look in the whole tree.
        The description lstTupplesSearch is a list of tupples (attribute, value) and all
        of those attributes must match"""
        try:
            if dnBase == None:
                dnBase = self.dnBase
            strSearch = "(&" + "".join(["(" + attr + "=" + val + ")" for (attr, val) in lstTupplesSearch]) + ")"
            #result = self.ldapHandle.search_s(dnBase, ldap.SCOPE_SUBTREE, strSearch)
            result = self.ldapHandle.search_s(dnBase, scope, strSearch)
            return [ node[0] for node in result ]
        except:
            raise NameError, "%s not found in %s" % (strSearch, dnBase)
    
    def search_s(self, lstTupplesSearch, dnBase = None, scope = ldap.SCOPE_SUBTREE):
        """Search for a list of nodes whose attributes match the description in a subtree dnBase,
        if dnBase is not specified this API will look in the whole tree.
        The description lstTupplesSearch is a list of tupples (attribute, value) and all
        of those attributes must match"""
        try:
            if dnBase == None:
                dnBase = self.dnBase
            strSearch = "(&" + "".join(["(" + attr + "=" + val + ")" for (attr, val) in lstTupplesSearch]) + ")"
            #result = self.ldapHandle.search_s(dnBase, ldap.SCOPE_SUBTREE, strSearch)
            result = self.ldapHandle.search_s(dnBase, scope, strSearch)
            return [ node for node in result ]
        except:
            return None

    def search_any_host(self, lstTupplesSearch, dnBase = None, scope = ldap.SCOPE_SUBTREE):
        """Search for a list of nodes whose attributes match the description in a subtree dnBase,
        if dnBase is not specified this API will look in the whole tree.
        The description lstTupplesSearch is a list of tupples (attribute, value) and any
        of those attributes must match"""
        try:
            if dnBase == None:
                dnBase = self.dnBase
            strSearch = "(&(objectClass=hostObject)(|" + "".join(["(" + attr + "=" + val + ")" for (attr, val) in lstTupplesSearch]) + "))"
            result = self.ldapHandle.search_s(dnBase, scope, strSearch)
            return [ node for node in result ]
        except:
            return None

    def get_parent(self, dnChild):
        """Return the dn of the parent, to do it eliminate the first part of the dn up to the comma"""
        try:
            regex=re.compile("^[^,]+,(.*)$")
            find = regex.match(dnChild)
            return find.expand(r"\1")
        except:
            raise SyntaxError, "invalid DN %s" % (dnChild)

    def create_ldapObject(self, dn, attr=None):
        """Create a new LDAP entry and return an ldapObject pointing to it"""
        try:
            addlist=[(dn.split(",")[0].split("=")[0], dn.split(",")[0].split("=")[1])]
            if attr != None:
                addlist.extend(attr)
            self.ldapHandle.add_s(dn, addlist)
        except:
            print "4-16 Unexpected error:", sys.exc_info()[0]
            raise SyntaxError, "Failed to create LDAP object %s" % (dn)
        #return ldapObject(self, dn)
    
    def delete_ldapObject(self, dn):
        try:
            self.ldapHandle.delete_s(dn)
        except:
            raise SyntaxError, "Failed to delete LDAP object %s" % (dn)

    def rename_dn(self, dn, newrdn, newsuperior=None):
        """Rename a dn"""
        print "newsuperior: %s" %newsuperior
        print "newrdn: %s" %newrdn
        print "dn; %s" %dn
        try:
            if newsuperior != None:
                self.ldapHandle.rename_s(dn, newrdn, newsuperior)
            else:
                print "calling rename_s"
                self.ldapHandle.rename_s(dn, newrdn)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            raise SyntaxError, "Failed to rename LDAP object %s" % (dn)

    def modify_dn(self, dn, modlist):
        """Modify attributes in a dn"""
        try:
            self.ldapHandle.modify_s( dn, modlist)
        except:
            raise SyntaxError, "Failed to modify LDAP object %s" % (dn)

###
# Copyright (c) 2011, Dave Riches
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import yum
import yum.misc as misc
import yum.config
import yum.Errors
import yum.packages
import os, time
from fedora.client.bodhi import BodhiClient


class Repoquery(callbacks.Plugin):
    """Add the help for "@plugin help Repoquery" here
    This should describe *how* to use this plugin."""
    repoCommands = ('info')
    threaded = True

    def rversion(self, irc, msg, args, fedver, arch, package):
        """<fedora version> <package name>

        returns the repository info for a given package name

        <fedora version> must be a number, <arch> must be either x32 or x64 <package name>
        specific name of package eg. kernel
        """
        channel = None
        if (not package):
            irc.reply("This plugin requires 3 arguments. <fedora version> <arch> <package>") 
        if irc.isChannel(msg.args[0]):
            channel = msg.args[0]
        if arch=="x32":
            arch="i686"
        else:
            arch="x86_64"
        try:
            stripped = str(int(fedver))
            target = fedver
            yb = yum.YumBase()
            yb.preconf.releasever=target
            yb.preconf.arch=arch
            yb.setCacheDir()
            yb.repos.enableRepo('updates-testing')
            res = yb.pkgSack.searchNames([package])
            if len(res)==0:
                irc.reply("sorry, I was unable to locate that package. To use this plugin, you must be specific with package names")
            for i in res:
                irc.reply(i.ui_envra+" "+i.repo.name+"|size "+str((i.size/1024)/1024)+"MB|Date "+time.ctime(i.committime))
            yb.close()
        except:
            irc.reply("Fedora release versions must be a number")
    rversion = wrap(rversion, ['something', additional('something'), additional('something')])

    def rprovides(self, irc, msg, args, fedver, package):
        """<fedora version> <text>

           returns a list of providing packages for <text>. If the resultant number of packages
           is greater than 5, the reply will be sent in a /PRIVMSG
        """
        channel = None
        msgargs = ""
        if irc.isChannel(msg.args[0]):
            channel = msg.args[0]
        stripped = str(int(fedver))
        target = fedver
        yb = yum.YumBase()
        yb.preconf.releasever=target
        yb.setCacheDir()
        res = yb.returnPackagesByDep(package)
        if len(res)==0:
            irc.reply("sorry, I was unable to locate a package.")
        elif 3 < len(res) < 20:
            irc.reply("the number of packages was greater than 3 (%s in total), I will send the result in a /PRIVMSG" % len(res))
            thisreply=""
            for i in res:
                irc.reply(i.ui_envra+" "+i.repo.name+"|size "+str((i.size/1024)/1024)+"MB|Date "+time.ctime(i.committime), prefixNick=msg.nick,private=msg.nick)
        elif len(res)>20:
            irc.reply("the number of results was greater than 20 (%s in total), I would suggest using yum locally" % len(res))
        else:
            thisreply=""
            for i in res:
                thisreply+=(i.ui_envra+" "+i.repo.name+"|size "+str((i.size/1024)/1024)+"MB|Date "+time.ctime(i.committime))
            irc.reply(thisreply)
        yb.close()
    rprovides = wrap(rprovides, ['something', additional('something')])

    def bodhi(self, irc, msg, args, package):
        """<package>

           returns a list of latest builds for <package>. If the resultant number of packages
           is greater than 5, the reply will be sent in a /PRIVMSG
        """
        channel = None
        msgargs = ""
        if irc.isChannel(msg.args[0]):
            channel = msg.args[0]
        try:
            yb = BodhiClient()
            res = yb.latest_builds(package)
            res = res.items()
            if len(res)==0:
                irc.reply("sorry, I was unable to locate a package.")
            elif 3 < len(res) < 20:
                irc.reply("the number of packages was greater than 3 (%s in total), I will send the result in a /PRIVMSG" % len(res))
                thisreply=""
                for dist,build in res:
#                    thisreply=thisreply+i.ui_envra+" "+i.repo.name+"|size "+str((i.size/1024)/1024)+"MB|Date "+time.ctime(i.committime)
                    irc.reply(str(dist)+" : "+str(build), prefixNick=msg.nick,private=msg.nick)
            elif len(res)>20:
                irc.reply("the number of results was greater than 20 (%s in total), I would suggest using yum locally" % len(res))
            else:
                for i in res:
                    irc.reply(i.keys+" : "+i.values)
        except:
            irc.reply("Something went wrong")
    bodhi = wrap(bodhi, ['something'])


Class = Repoquery


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

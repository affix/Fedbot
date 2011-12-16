###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009, Kevin Fenzi
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


#class RootWarner(callbacks.Plugin):
#    """Add the help for "@plugin help RootWarner" here
#    This should describe *how* to use this plugin."""
#    pass

__revision__ = "$Id: RootWarner.py,v 1.14 2004/09/20 03:05:30 jamessan Exp $"

import supybot.plugins as plugins

import supybot.conf as conf
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.registry as registry
import supybot.callbacks as callbacks

class RootWarner(callbacks.Plugin):
    """Warns or kicks people who appear to be using IRC as root.  Check out the
    configuration variables supybot.plugins.RootWarner.warn,
    supybot.plugins.RootWarner.kick, and supybot.plugins.RootWarner.warning to
    configure this plugin's behavior.
    """
    def doJoin(self, irc, msg):
        user = ircutils.userFromHostmask(msg.prefix)
        if user == 'root' or user == '~root' or user == 'n=root':
            channel = msg.args[0]
            s = self.registryValue('warning', channel)
            if self.registryValue('warn', channel):
                irc.queueMsg(ircmsgs.notice(msg.nick, s))
            if self.registryValue('kick', channel):
                irc.queueMsg(ircmsgs.kick(channel, msg.nick, s))

Class = RootWarner
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:


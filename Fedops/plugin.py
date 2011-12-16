###
# Copyright (c) 2010, Dave Riches
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
import supybot.ircmsgs as ircmsgs                                            


class Fedops(callbacks.Plugin):
    """This pugin is simply called by @ops and will message #fedora-ops with the details of the sender and the channel
in question. This plugin is designed to be used _only_ for #fedora-ops"""
    threaded = True
    text = []                                                                         
    def ops(self, irc, msg, args, channel, text):
        """[<text>]

        This plugin will notify Fedora operators of any potential problems in any of the channels. No argument is
        needed, but you can provide a brief description of the problem you are having. This it not for general support
        """
        if text==None:
            orig_string="" 
        else:
            orig_string=", (orig message : '%s')" % text                                      
        irc.queueMsg(ircmsgs.privmsg("#fedora-ops", 'Hello, %s says could someone take a look at issues in %s%s' % (msg.nick,msg.args[0],orig_string)))                         
        irc.noReply()                                                       
    ops = wrap(ops, ['inChannel',optional('text')]) 
#    ops = ('inChannel','text')
Class = Fedops

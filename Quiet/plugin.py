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

import sys

import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.schedule as schedule
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import time

class Quiet(callbacks.Plugin):
    """Add the help for "@plugin help Quiet" here
    This should describe *how* to use this plugin."""
    def _sendMsg(self, irc, msg):
        irc.queueMsg(msg)
        irc.noReply()
    def quiet(self, irc, msg, args, channel, nick, expiry):
        """[<channel>] <nick> [<expiry>]

        Quietens <nick> from <channel> for <expiry>.  If <expiry> isn't given,
        the duration is permanent.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        if ircutils.strEqual(nick, irc.nick):
            irc.error('I cowardly refuse to quiet myself.', Raise=True)
        thismsg=self.registryValue('message')
        self._sendMsg(irc, ircmsgs.mode(channel, ("+q", nick)))
        if self.registryValue('SendMsgPvt'):
            self._sendMsg(irc, ircmsgs.privmsg(nick,nick+", "+thismsg ))
        else:
            self._sendMsg(irc, ircmsgs.privmsg(channel,nick+", "+thismsg ))
        def f():
            irc.queueMsg(ircmsgs.mode(channel, ("-q", nick)))
        schedule.addEvent(f, expiry)
    quiet = wrap(quiet, ['op', ('haveOp', 'quieten someone'),
                       'nickInChannel',
                        optional('expiry', 0)])
    pass


Class = Quiet

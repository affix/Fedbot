###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2009, James Vega
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

import re
import math
import time

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
import supybot.ircmsgs as ircmsgs
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.schedule as schedule

class BadWords(callbacks.Privmsg):
    def __init__(self, irc):
        self.__parent = super(BadWords, self)
        self.__parent.__init__(irc)
        # This is so we can not filter certain outgoing messages (like list,
        # which would be kinda useless if it were filtered).
        self.filtering = True
        self.lastModified = 0
        self.words = conf.supybot.plugins.BadWords.words

    def callCommand(self, name, irc, msg, *args, **kwargs):
        if ircdb.checkCapability(msg.prefix, 'admin'):
            self.__parent.callCommand(name, irc, msg, *args, **kwargs)
        else:
            irc.errorNoCapability('admin')

    def sub(self, m):
        replaceMethod = self.registryValue('replaceMethod')
        if replaceMethod == 'simple':
            return self.registryValue('simpleReplacement')
        elif replaceMethod == 'nastyCharacters':
            return self.registryValue('nastyChars')[:len(m.group(1))]

    def inFilter(self, irc, msg):
        self.filtering = True
        # We need to check for bad words here rather than in doPrivmsg because
        # messages don't get to doPrivmsg is the user is ignored.
        if msg.command == 'PRIVMSG':
            self.updateRegexp()
            s = ircutils.stripFormatting(msg.args[1])
            channel = msg.args[0]
            if ircutils.isChannel(channel) and self.registryValue('kickban', channel):
                if self.regexp.search(s):
                    if irc.nick in irc.state.channels[channel].ops:
                        message = self.registryValue('kickban.message', channel)
                        bannedHostmask = irc.state.nickToHostmask(msg.nick)
                        banmaskstyle = conf.supybot.protocols.irc.banmask
                        banmask = banmaskstyle.makeBanmask(bannedHostmask)
                        irc.queueMsg(ircmsgs.ban(channel, banmask))
                        irc.queueMsg(ircmsgs.kick(channel, msg.nick, message))
                        expiry = self.registryValue('kickban.banexpire', channel)
                        if expiry > 0:
                         def f():
                          if channel in irc.state.channels and \
                             banmask in irc.state.channels[channel].bans:
                             irc.queueMsg(ircmsgs.unban(channel, banmask))
                         schedule.addEvent(f,time.time()+expiry)
                    else:
                        self.log.warning('Should kickban %s from %s, but not opped.',
                                         msg.nick, channel)

            else: 
                if ircutils.isChannel(channel) and self.registryValue('kick', channel):
                 if self.regexp.search(s):
                    if irc.nick in irc.state.channels[channel].ops:
                        message = self.registryValue('kick.message', channel)
                        irc.queueMsg(ircmsgs.kick(channel, msg.nick, message))
                    else:
                        self.log.warning('Should kick %s from %s, but not opped.',
                                         msg.nick, channel)
        return msg

    def updateRegexp(self):
        if self.lastModified < self.words.lastModified:
            self.makeRegexp(self.words())
            self.lastModified = time.time()

    def outFilter(self, irc, msg):
        if self.filtering and msg.command == 'PRIVMSG':
            self.updateRegexp()
            s = msg.args[1]
            if self.registryValue('stripFormatting'):
                s = ircutils.stripFormatting(s)
            t = self.regexp.sub(self.sub, s)
            if t != s:
                msg = ircmsgs.privmsg(msg.args[0], t, msg=msg)
        return msg

    def makeRegexp(self, iterable):
        s = '(%s)' % '|'.join(map(re.escape, iterable))
        if self.registryValue('requireWordBoundaries'):
            s = r'\b%s\b' % s
        self.regexp = re.compile(s, re.I)

    def list(self, irc, msg, args):
        """takes no arguments

        Returns the list of words being censored.
        """
        L = list(self.words())
        if L:
            self.filtering = False
            utils.sortBy(str.lower, L)
            irc.reply(format('%L', L))
        else:
            irc.reply('I\'m not currently censoring any bad words.')
    list = wrap(list, ['admin'])

    def add(self, irc, msg, args, words):
        """<word> [<word> ...]

        Adds all <word>s to the list of words the bot isn't to say.
        """
        set = self.words()
        set.update(words)
        self.words.setValue(set)
        irc.replySuccess()
    add = wrap(add, ['admin', many('something')])

    def remove(self, irc, msg, args, words):
        """<word> [<word> ...]

        Removes a <word>s from the list of words the bot isn't to say.
        """
        set = self.words()
        for word in words:
            set.discard(word)
        self.words.setValue(set)
        irc.replySuccess()
    remove = wrap(remove, ['admin', many('something')])


Class = BadWords


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

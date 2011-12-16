# -*- Encoding: utf-8 -*-
###
# Copyright (c) 2005-2007 Dennis Kaarsemaker
# Copyright (c) 2008-2010 Terence Simpson
# Copyright (c) 2010 Elián Hanisch
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
###
###
# Based on the standard supybot logging plugin, which has the following
# copyright:
#
# Copyright (c) 2002-2004, Jeremiah Fincher
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

from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import supybot.ircmsgs as ircmsgs
import supybot.conf as conf
import supybot.ircdb as ircdb
import supybot.schedule as schedule
from fnmatch import fnmatch
import sqlite3
import pytz
import cPickle
import datetime
import time
import random
import hashlib
import threading

isUserHostmask = ircutils.isUserHostmask

tz = 'UTC'

def now():
    return cPickle.dumps(datetime.datetime.now(pytz.timezone(tz)))

def fromTime(x):
    return cPickle.dumps(datetime.datetime(*time.gmtime(x)[:6], **{'tzinfo': pytz.timezone("UTC")}))

def capab(user, capability):
    capability = capability.lower()
    capabilities = list(user.capabilities)
    # Capability hierarchy #
    if capability == "bantracker":
        if capab(user, "admin"):
            return True
    if capability == "admin":
        if capab(user, "owner"):
            return True
    # End #
    if capability in capabilities:
        return True
    else:
        return False

def hostmaskPatternEqual(pattern, hostmask):
    if pattern.count('!') != 1 or pattern.count('@') != 1:
        return False
    if pattern.count('$') == 1:
        pattern = pattern.split('$',1)[0]
    if pattern.startswith('%'):
        pattern = pattern[1:]
    return ircutils.hostmaskPatternEqual(pattern, hostmask)

def nickMatch(nick, pattern):
    """Checks if a given nick matches a pattern or in a list of patterns."""
    if isinstance(pattern, str):
        pattern = [pattern]
    nick = nick.lower()
    for s in pattern:
        if fnmatch(nick, s.lower()):
            return True
    return False

def dequeue(parent, irc):
    global queue
    queue.dequeue(parent, irc)

class MsgQueue(object):
    def __init__(self):
        self.msgcache = []
    def queue(self, msg):
        if msg not in self.msgcache:
            self.msgcache.append(msg)
    def clear(self):
        self.msgcache = []
    def dequeue(self, parent, irc):
        parent.thread_timer.cancel()
        parent.thread_timer = threading.Timer(10.0, dequeue, args=(parent, irc))
        if len(self.msgcache):
            msg = self.msgcache.pop(0)
            irc.queueMsg(msg)
        parent.thread_timer.start()

queue = MsgQueue()

class Ban(object):
    """Hold my bans"""
    def __init__(self, args=None, **kwargs):
        self.id = None
        if args:
            # in most ircd: args = (nick, channel, mask, who, when)
            self.mask = args[2]
            self.who = args[3]
            self.when = float(args[4])
        else:
            self.mask = kwargs['mask']
            self.who = kwargs['who']
            self.when = float(kwargs['when'])
            if 'id' in kwargs:
                self.id = kwargs['id']
        self.ascwhen = time.asctime(time.gmtime(self.when))

    def __tuple__(self):
        return (self.mask, self.who, self.ascwhen)

    def __iter__(self):
        return self.__tuple__().__iter__()

    def __str__(self):
        return "%s by %s on %s" % tuple(self)

    def __repr__(self):
        return '<%s object "%s" at 0x%x>' % (self.__class__.__name__, self, id(self))

    def op(self):
        return self.mask.split('!')[0]

    def time(self):
        return datetime.datetime.fromtimestamp(self.when)

def guessBanType(mask):
    if mask[0] == '%':
        return 'quiet'
    elif ircutils.isUserHostmask(mask) or mask.endswith('(realname)'):
        return 'ban'
    return 'removal'

class PersistentCache(dict):
    def __init__(self, filename):
        self.filename = conf.supybot.directories.data.dirize(filename)
        self.time = 0

    def open(self):
        import csv
        try:
            reader = csv.reader(open(self.filename, 'rb'))
        except IOError:
            return
        self.time = int(reader.next()[1])
        for row in reader:
            host, value = self.deserialize(*row)
            try:
                L = self[host]
                if value not in L:
                    L.append(value)
            except KeyError:
                self[host] = [value]

    def close(self):
        import csv
        try:
            writer = csv.writer(open(self.filename, 'wb'))
        except IOError:
            return
        writer.writerow(('time', str(int(self.time))))
        for host, values in self.iteritems():
            for v in values:
                writer.writerow(self.serialize(host, v))

    def deserialize(self, host, nick, command, channel, text):
        if command == 'PRIVMSG':
            msg = ircmsgs.privmsg(channel, text)
        elif command == 'NOTICE':
            msg = ircmsgs.notice(channel, text)
        else:
            return
        return (host, (nick, msg))

    def serialize(self, host, value):
        nick, msg = value
        command, channel, text = msg.command, msg.args[0], msg.args[1]
        return (host, nick, command, channel, text)



class Bantracker(callbacks.Plugin):
    """Plugin to manage bans.
       See '@list Bantracker' and '@help <command>' for commands"""
    noIgnore = True
    threaded = True
    
    def __init__(self, irc):
        self.__parent = super(Bantracker, self)
        self.__parent.__init__(irc)
        self.default_irc = irc
        self.lastMsgs = {}
        self.lastStates = {}
        self.replies = {}
        self.logs = ircutils.IrcDict()
        self.nicks = {}
        self.hosts = {}
        self.bans = ircutils.IrcDict()

        self.thread_timer = threading.Timer(10.0, dequeue, args=(self,irc))
        self.thread_timer.start()

        db = self.registryValue('database')
        if db:
            self.db = sqlite3.connect(db)
        else:
            self.db = None
        self.get_bans(irc)
        self.get_nicks(irc)
        self.pendingReviews = PersistentCache('bt.reviews.db')
        self.pendingReviews.open()
        self._banreviewfix()
        # add scheduled event for check bans that need review, check every hour
        try:
            schedule.removeEvent(self.name())
        except:
            pass
        schedule.addPeriodicEvent(lambda : self.reviewBans(irc), 60*60,
                name=self.name())

    def get_nicks(self, irc):
        self.hosts.clear()
        for (channel, c) in irc.state.channels.iteritems():
            if not self.registryValue('enabled', channel):
                continue
            for nick in list(c.users):
                nick = nick.lower()
                if not nick in self.nicks:
                    host = self.nick_to_host(irc, nick, False).lower()
                    self.nicks[nick] = host
                    host = host.split('@', 1)[1]
                    if '*' not in host:
                        if host not in self.hosts:
                            self.hosts[host] = []
                        self.hosts[host].append(nick)

    def get_bans(self, irc):
        global queue
        for channel in irc.state.channels.keys():
            if not self.registryValue('enabled', channel):
                continue
            if channel not in self.bans:
                self.bans[channel] = []
            queue.queue(ircmsgs.mode(channel, 'b'))

    def sendWhois(self, irc, nick, do_reply=False, *args):
        nick = nick.lower()
        irc.queueMsg(ircmsgs.whois(nick, nick))
        if do_reply:
            self.replies[nick] = [args[0], args[1:]]

    def do311(self, irc, msg):
        """/whois"""
        nick = msg.args[1].lower()
        mask = "%s!%s@%s" % (nick, msg.args[2].lower(), msg.args[3].lower())
        self.nicks[nick] = mask
        if nick in self.replies:
            f = getattr(self, "%s_real" % self.replies[nick][0])
            args = self.replies[nick][1]
            del self.replies[nick]
            kwargs={'from_reply': True, 'reply': "%s!%s@%s" % (msg.args[1], msg.args[2], msg.args[3])}
            f(*args, **kwargs)

    def do314(self, irc, msg):
        """/whowas"""
        nick = msg.args[1].lower()
        mask = "%s!%s@%s" % (nick, msg.args[2].lower(), msg.args[3].lower())
        if not nick in self.nicks:
            self.nicks[nick] = mask
        if nick in self.replies:
            f = getattr(self, "%s_real" % self.replies[nick][0])
            args = self.replies[nick][1]
            del self.replies[nick]
            kwargs={'from_reply': True, 'reply': "%s!%s@%s" % (msg.args[1], msg.args[2], msg.args[3])}
            f(*args, **kwargs)

    def do401(self, irc, msg):
        """/whois faild"""
        irc.queueMsg(ircmsgs.IrcMsg(prefix="", command='WHOWAS', args=(msg.args[1],), msg=msg))

    def do406(self, irc, msg):
        """/whowas faild"""
        nick = msg.args[1].lower()
        if nick in self.replies:
            f = getattr(self, "%s_real" % self.replies[nick][0])
            args = self.replies[nick][1]
            del self.replies[nick]
            kwargs = {'from_reply': True, 'reply': None}
            f(*args, **kwargs)

    def do367(self, irc, msg):
        """Got ban"""
        if msg.args[1] not in self.bans.keys():
            self.bans[msg.args[1]] = []
        bans = self.bans[msg.args[1]]
        bans.append(Ban(msg.args))
        bans.sort(key=lambda x: x.when) # needed for self.reviewBans

    def nick_to_host(self, irc=None, target='', with_nick=True, reply_now=True):
        target = target.lower()
        if ircutils.isUserHostmask(target):
            return target
        elif target in self.nicks:
            return self.nicks[target]
        elif irc:
            try:
                return irc.state.nickToHostmask(target)
            except:
                if reply_now:
                    if with_nick:
                        return "%s!*@*" % target
                    return "*@*"
        return

        if target in self.nicks:
            return self.nicks[target]
        else:
            return "%s!*@*" % target

    def die(self):
        global queue
        if self.db:
            try:
                self.db.close()
            except:
                pass
        try:
            self.thread_timer.cancel()
        except:
            pass
        queue.clear()
        schedule.removeEvent(self.name())
        self.pendingReviews.close()

    def reset(self):
        global queue
        if self.db:
            try:
                self.db.close()
            except:
                pass
        queue.clear()
#        self.logs.clear()
        self.lastMsgs.clear()
        self.lastStates.clear()
#        self.nicks.clear()

    def __call__(self, irc, msg):
        try:
            super(self.__class__, self).__call__(irc, msg)
            if irc in self.lastMsgs:
                if irc not in self.lastStates:
                    self.lastStates[irc] = irc.state.copy()
                self.lastStates[irc].addMsg(irc, self.lastMsgs[irc])
        finally:
            self.lastMsgs[irc] = msg

    def db_run(self, query, parms, expect_result = False, expect_id = False):
        if not self.db:
            db = self.registryValue('database')
            if db:
                try:
                    self.db = sqlite3.connect(db)
                except:
                    self.log.error("Bantracker: failed to connect to database")
                    return
            else:
                self.log.error("Bantracker: no database")
                return
        try:
            cur = self.db.cursor()
            cur.execute(query, parms)
            self.db.commit()
            self.db.close()
        except:
            self.log.error("Bantracker: Error while trying to access the Bantracker database.")
            return None
        data = None
        if expect_result and cur: data = cur.fetchall()
        if expect_id: data = self.db.insert_id()
        self.db.commit()
        return data

    def requestComment(self, irc, channel, ban):
        if not ban or not self.registryValue('request', channel):
            return
        # check the type of the action taken
        mask = ban.mask
        type = guessBanType(mask)
        if type == 'quiet':
            mask = mask[1:]
        # check if type is enabled
        if type not in self.registryValue('request.type', channel):
            return
        prefix = conf.supybot.reply.whenAddressedBy.chars()[0] # prefix char for commands
        # check to who send the request
        try:
            nick = ircutils.nickFromHostmask(ban.who)
        except:
            nick = ban.who
        if nickMatch(nick, self.registryValue('request.ignore', channel)):
            return
        if nickMatch(nick, self.registryValue('request.forward', channel)):
            s = "Please somebody comment on the %s of %s in %s done by %s, use:"\
                " %scomment %s <comment>" %(type, mask, channel, nick, prefix, ban.id)
            self._sendForward(irc, s, channel)
        else:
            # send to op
            s = "Please comment on the %s of %s in %s, use: %scomment %s <comment>" \
                    %(type, mask, channel, prefix, ban.id)
            irc.reply(s, to=nick, private=True)

    def reviewBans(self, irc=None):
        reviewTime = int(self.registryValue('request.review') * 86400)
        if not reviewTime:
            # time is zero, do nothing
            return
        now = time.mktime(time.gmtime())
        lastreview = self.pendingReviews.time
        self.pendingReviews.time = now # update last time reviewed
        if not lastreview:
            # initialize last time reviewed timestamp
            lastreview = now - reviewTime

        for channel, bans in self.bans.iteritems():
            if not self.registryValue('enabled', channel) \
                    or not self.registryValue('request', channel):
                continue

            for ban in bans:
                if guessBanType(ban.mask) in ('quiet', 'removal'):
                    # skip mutes and kicks
                    continue
                banAge = now - ban.when
                reviewWindow = lastreview - ban.when
                #self.log.debug('review ban: %s ban %s by %s (%s/%s/%s %s)', channel, ban.mask,
                #        ban.who, reviewWindow, reviewTime, banAge, reviewTime - reviewWindow)
                if reviewWindow <= reviewTime < banAge:
                    # ban is old enough, and inside the "review window"
                    try:
                        # ban.who should be a user hostmask
                        nick = ircutils.nickFromHostmask(ban.who)
                        host = ircutils.hostFromHostmask(ban.who)
                    except:
                        if ircutils.isNick(ban.who, strictRfc=True):
                            # ok, op's nick, use it
                            nick = ban.who
                            host = None
                        else:
                            # probably a ban restored by IRC server in a netsplit
                            # XXX see if something can be done about this
                            continue
                    if nickMatch(nick, self.registryValue('request.ignore', channel)):
                        # in the ignore list
                        continue
                    if not ban.id:
                        ban.id = self.get_banId(ban.mask, channel)
                    if nickMatch(nick, self.registryValue('request.forward', channel)):
                        s = "Hi, please somebody review the ban '%s' set by %s on %s in"\
                        " %s, link: %s/bans.cgi?log=%s" %(ban.mask, nick, ban.ascwhen, channel,
                                self.registryValue('bansite'), ban.id)
                        self._sendForward(irc, s, channel)
                    else:
                        s = "Hi, please review the ban '%s' that you set on %s in %s, link:"\
                        " %s/bans.cgi?log=%s" %(ban.mask, ban.ascwhen, channel,
                                self.registryValue('bansite'), ban.id)
                        msg = ircmsgs.privmsg(nick, s)
                        if host in self.pendingReviews \
                            and (nick, msg) not in self.pendingReviews[host]:
                            self.pendingReviews[host].append((nick, msg))
                        else:
                            self.pendingReviews[host] = [(nick, msg)]
                elif banAge < reviewTime:
                    # since we made sure bans are sorted by time, the bans left are more recent
                    break

    def _sendForward(self, irc, s, channel=None):
        if not irc:
            return
        for chan in self.registryValue('request.forward.channels', channel=channel):
            msg = ircmsgs.notice(chan, s)
            irc.queueMsg(msg)

    def _banreviewfix(self):
        # FIXME workaround until proper fix is done.
        bag = set()
        nodups = set()
        for host, reviews in self.pendingReviews.iteritems():
            for nick, msg in reviews:
                if nick == 'Automated-Addition':
                    continue
                chan, m = msg.args[0], msg.args[1]
                s = m.rpartition(' ')[0] #remove the url
                if (nick, chan, s) not in bag:
                    bag.add((nick, chan, s))
                    nodups.add((host, nick, msg)) 

        self.pendingReviews.clear()

        for host, nick, msg in nodups:
            if host in self.pendingReviews:
                self.pendingReviews[host].append((nick, msg))
            else:
                self.pendingReviews[host] = [(nick, msg)]

    def _sendReviews(self, irc, msg):
        host = ircutils.hostFromHostmask(msg.prefix)
        if host in self.pendingReviews:
            self._banreviewfix()
            for nick, m in self.pendingReviews[host]:
                if msg.nick != nick and not irc.isChannel(nick): # I'm a bit extra careful here
                    # correct nick in msg
                    m = ircmsgs.privmsg(msg.nick, m.args[1])
                irc.queueMsg(m)
            del self.pendingReviews[host]
        # check if we have any reviews by nick to send
        if None in self.pendingReviews:
            L = self.pendingReviews[None]
            for i, v in enumerate(L):
                nick, m = v
                if ircutils.strEqual(msg.nick, nick):
                    irc.queueMsg(m)
                    del L[i]
            if not L:
                del self.pendingReviews[None]

    def doLog(self, irc, channel, s):
        if not self.registryValue('enabled', channel):
            return
        channel = ircutils.toLower(channel) 
        if channel not in self.logs.keys():
            self.logs[channel] = []
        format = conf.supybot.log.timestampFormat()
        if format:
            s = time.strftime(format, time.gmtime()) + " " + ircutils.stripFormatting(s)
        self.logs[channel] = self.logs[channel][-199:] + [s.strip()]

    def doKickban(self, irc, channel, *args, **kwargs):
        ban = self._doKickban(irc, channel, *args, **kwargs)
        self.requestComment(irc, channel, ban)
        return ban

    def _doKickban(self, irc, channel, operator, target, kickmsg = None, use_time = None, extra_comment = None):
        if not self.registryValue('enabled', channel):
            return
        n = now()
        if use_time:
            n = fromTime(use_time)
        try:
            nick = ircutils.nickFromHostmask(operator)
        except:
            nick = operator
        id = self.db_run("INSERT INTO bans (channel, mask, operator, time, log) values(%s, %s, %s, %s, %s)", 
                          (channel, target, nick, n, '\n'.join(self.logs[channel])), expect_id=True)
        if kickmsg and id and not (kickmsg == nick):
            self.db_run("INSERT INTO comments (ban_id, who, comment, time) values(%s,%s,%s,%s)", (id, nick, kickmsg, n))
        if extra_comment:
            self.db_run("INSERT INTO comments (ban_id, who, comment, time) values(%s,%s,%s,%s)", (id, nick, extra_comment, n))
        if channel not in self.bans:
            self.bans[channel] = []
        ban = Ban(mask=target, who=operator, when=time.mktime(time.gmtime()), id=id)
        self.bans[channel].append(ban)
        return ban

    def doUnban(self, irc, channel, nick, mask):
        if not self.registryValue('enabled', channel):
            return
        data = self.db_run("SELECT MAX(id) FROM bans where channel=%s and mask=%s", (channel, mask), expect_result=True)
        if len(data) and not (data[0][0] == None):
            self.db_run("UPDATE bans SET removal=%s , removal_op=%s WHERE id=%s", (now(), nick, int(data[0][0])))
        if not channel in self.bans:
            self.bans[channel] = []
        idx = None
        for ban in self.bans[channel]:
            if ban.mask == mask:
                idx = self.bans[channel].index(ban)
                break
        if idx != None:
            del self.bans[channel][idx]

    def doPrivmsg(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if irc.isChannel(channel):
                nick = msg.nick or irc.nick
                if ircmsgs.isAction(msg):
                    self.doLog(irc, channel,
                               '* %s %s\n' % (nick, ircmsgs.unAction(msg)))
                else:
                    self.doLog(irc, channel, '<%s> %s\n' % (nick, text))
        self._sendReviews(irc, msg)

    def doNotice(self, irc, msg):
        (recipients, text) = msg.args
        for channel in recipients.split(','):
            if irc.isChannel(channel):
                self.doLog(irc, channel, '-%s- %s\n' % (msg.nick, text))

    def doNick(self, irc, msg):
        oldNick = msg.nick
        newNick = msg.args[0]
        for (channel, c) in irc.state.channels.iteritems():
            if newNick in c.users:
                self.doLog(irc, channel,
                           '*** %s is now known as %s\n' % (oldNick, newNick))
        if oldNick.lower() in self.nicks:
            del self.nicks[oldNick.lower()]
        nick = newNick.lower()
        hostmask = nick + "!".join(msg.prefix.lower().split('!')[1:])
        self.nicks[nick] = hostmask

    def doJoin(self, irc, msg):
        global queue
        for channel in msg.args[0].split(','):
            if msg.nick:
                self.doLog(irc, channel,
                       '*** %s (%s) has joined %s\n' % (msg.nick, msg.prefix.split('!', 1)[1], channel))
            else:
                self.doLog(irc, channel,
                       '*** %s has joined %s\n' % (msg.prefix, channel))
            if not channel in self.bans.keys():
                self.bans[channel] = []
            if msg.prefix.split('!', 1)[0] == irc.nick:
                queue.queue(ircmsgs.mode(channel, 'b'))
        nick = msg.nick.lower() or msg.prefix.lower().split('!', 1)[0]
        self.nicks[nick] = msg.prefix.lower()

    def doKick(self, irc, msg):
        if len(msg.args) == 3:
            (channel, target, kickmsg) = msg.args
        else:
            (channel, target) = msg.args
            kickmsg = ''
        host = self.nick_to_host(irc, target, True)
        if host == "%s!*@*" % host:
            host = None
        if kickmsg:
            self.doLog(irc, channel,
                       '*** %s was kicked by %s (%s)\n' % (target, msg.nick, kickmsg))
        else:
            self.doLog(irc, channel,
                       '*** %s was kicked by %s\n' % (target, msg.nick))
        self.doKickban(irc, channel, msg.prefix, target, kickmsg, extra_comment=host)

    def doPart(self, irc, msg):
        for channel in msg.args[0].split(','):
            self.doLog(irc, channel, '*** %s (%s) has left %s (%s)\n' % (msg.nick, msg.prefix, channel, len(msg.args) > 1 and msg.args[1] or ''))
            if len(msg.args) > 1 and msg.args[1].startswith('requested by'):
                args = msg.args[1].split()
                self.doKickban(irc, channel, args[2], msg.nick, ' '.join(args[3:]).strip(), extra_comment=msg.prefix)

    def doMode(self, irc, msg):
        channel = msg.args[0]
        if irc.isChannel(channel) and msg.args[1:]:
            self.doLog(irc, channel,
                       '*** %s sets mode: %s %s\n' %
                       (msg.nick or msg.prefix, msg.args[1],
                        ' '.join(msg.args[2:])))
            modes = ircutils.separateModes(msg.args[1:])
            for param in modes:
                realname = ''
                mode = param[0]
                mask = ''
                comment=None
                if param[0] not in ("+b", "-b", "+q", "-q"):
                    continue
                mask = param[1]
                if mask.startswith("$r:"):
                    mask = mask[3:]
                    realname = ' (realname)'

                if param[0][1] == 'q':
                    mask = '%' + mask

                if param[0] in ('+b', '+q'):
                    comment = self.getHostFromBan(irc, msg, mask)
                    self.doKickban(irc, channel, msg.prefix, mask + realname, extra_comment=comment)
                elif param[0] in ('-b', '-q'):
                    self.doUnban(irc,channel, msg.nick, mask + realname)

    def getHostFromBan(self, irc, msg, mask):
        if irc not in self.lastStates:
            self.lastStates[irc] = irc.state.copy()
        if mask[0] == '%':
            mask = mask[1:]
        try:
            (nick, ident, host) = ircutils.splitHostmask(mask)
        except AssertionError:
            # not a hostmask
            return None
        channel = None
        chan = None
        if mask[0] not in ('*', '?'): # Nick ban
            if nick in self.nicks:
                return self.nicks[nick]
        else: # Host/ident ban
            for (inick, ihost) in self.nicks.iteritems():
                if ircutils.hostmaskPatternEqual(mask, ihost):
                    return ihost
        return None

    def doTopic(self, irc, msg):
        if len(msg.args) == 1:
            return # It's an empty TOPIC just to get the current topic.
        channel = msg.args[0]
        self.doLog(irc, channel,
                   '*** %s changes topic to "%s"\n' % (msg.nick, msg.args[1]))

    def doQuit(self, irc, msg):
        if irc not in self.lastStates:
            self.lastStates[irc] = irc.state.copy()
        for (channel, chan) in self.lastStates[irc].channels.iteritems():
            if msg.nick in chan.users:
                self.doLog(irc, channel, '*** %s (%s) has quit IRC (%s)\n' % (msg.nick, msg.prefix, msg.args[0]))
#            if msg.nick in self.user:
#                del self.user[msg.nick]

    def outFilter(self, irc, msg):
        # Gotta catch my own messages *somehow* :)
        # Let's try this little trick...
        if msg.command in ('PRIVMSG', 'NOTICE'):
            # Other messages should be sent back to us.
            m = ircmsgs.IrcMsg(msg=msg, prefix=irc.prefix)
            self(irc, m)
        return msg
        
#    def callPrecedence(self, irc):
#        before = []
#        for cb in irc.callbacks:
#            if cb.name() == 'IRCLogin':
#                return (['IRCLogin'], [])
#        return ([], [])

    def check_auth(self, irc, msg, args, cap='bantracker'):
        hasIRCLogin = False
        for cb in self.callPrecedence(irc)[0]:
            if cb.name() == "IRCLogin":
                hasIRCLogin = True
        if hasIRCLogin and not msg.tagged('identified'):
            irc.error(conf.supybot.replies.incorrectAuthentication())
            return False
        try:
            user = ircdb.users.getUser(msg.prefix)
        except:
            irc.error(conf.supybot.replies.incorrectAuthentication())
            return False

        if not capab(user, cap):
            irc.error(conf.supybot.replies.noCapability() % cap)
            return False
        return user

    def btlogin(self, irc, msg, args):
        """Takes no arguments

        Sends you a message with a link to login to the bantracker.
        """
        user = self.check_auth(irc, msg, args)
        if not user:
            return
        user.addAuth(msg.prefix)
        try:
            ircdb.users.setUser(user, flush=False)
        except:
            pass

        if not capab(user, 'bantracker'):
            irc.error(conf.supybot.replies.noCapability() % 'bantracker')
            return
        if not self.registryValue('bansite'):
            irc.error("No bansite set, please set supybot.plugins.Bantracker.bansite")
            return
        sessid = hashlib.md5('%s%s%d' % (msg.prefix, time.time(), random.randint(1,100000))).hexdigest()
        self.db_run("INSERT INTO sessions (session_id, user, time) VALUES (%s, %s, %d);",
            ( sessid, msg.nick, int(time.mktime(time.gmtime())) ) )
        irc.reply('Log in at %s/bans.cgi?sess=%s' % (self.registryValue('bansite'), sessid), private=True)

    btlogin = wrap(btlogin)

    def mark(self, irc, msg, args, channel, target, kickmsg):
        """[<channel>] <nick|hostmask> [<comment>]

        Creates an entry in the Bantracker as if <nick|hostmask> was kicked from <channel> with the comment <comment>,
        if <comment> is given it will be uses as the comment on the Bantracker, <channel> is only needed when send in /msg
        """
        user = self.check_auth(irc, msg, args)
        if not user:
            return

        if target == '*' or target[0] == '*':
            irc.error("Can not create a mark for '%s'" % target)
            return

        if not channel:
            irc.error('<channel> must be given if not in a channel')
            return
        channel = channel.lower()
        channels = []
        for chan in irc.state.channels.keys():
            channels.append(chan.lower())

        if not channel in channels:
            irc.error('Not in that channel')
            return

        if not kickmsg:
            kickmsg = '**MARK**'
        else:
            kickmsg = "**MARK** - %s" % kickmsg
        hostmask = self.nick_to_host(irc, target)

        self.doLog(irc, channel.lower(), '*** %s requested a mark for %s\n' % (msg.nick, target))
        self._doKickban(irc, channel.lower(), msg.prefix, hostmask, kickmsg)
        irc.replySuccess()

    mark = wrap(mark, [optional('channel'), 'something', additional('text')])

    def sort_bans(self, channel=None):
        data = self.db_run("SELECT mask, removal, channel, id FROM bans", (), expect_result=True)
        if channel:
            data = [i for i in data if i[2] == channel]
        bans  = [(i[0], i[3]) for i in data if i[1] == None and '%' not in i[0]]
        mutes = [(i[0], i[3]) for i in data if i[1] == None and '%' in i[0]]
        return mutes + bans

    def get_banId(self, mask, channel):
        data = self.db_run("SELECT MAX(id) FROM bans WHERE mask=%s AND channel=%s", (mask, channel), True)
        if data:
            data = data[0]
        if not data or not data[0]:
            return
        return int(data[0])

    def getBans(self, hostmask, channel):
        match = []
        if channel:
            if channel in self.bans and self.bans[channel]:
                for b in self.bans[channel]:
                    if hostmaskPatternEqual(b.mask, hostmask):
                        match.append((b.mask, self.get_banId(b.mask,channel)))
                data = self.sort_bans(channel)
                for e in data:
                    if hostmaskPatternEqual(e[0], hostmask):
                        if (e[0], e[1]) not in match:
                            match.append((e[0], e[1]))
        else:
            for c in self.bans:
                for b in self.bans[c]:
                    if hostmaskPatternEqual(b.mask, hostmask):
                        match.append((b.mask, self.get_banId(b.mask,c)))
            data = self.sort_bans()
            for e in data:
                    if hostmaskPatternEqual(e[0], hostmask):
                        if (e[0], e[1]) not in match:
                            match.append((e[0], e[1]))
        return match

    def bansearch_real(self, irc, msg, args, target, channel, from_reply=False, reply=None):
        """<nick|hostmask> [<channel>]

        Search bans database for a ban on <nick|hostmask>,
        if <channel> is not given search all channel bans.
        """
        def format_entry(entry):
            ret = list(entry[:-1])
            t = cPickle.loads(entry[-1]).astimezone(pytz.timezone('UTC')).strftime("%b %d %Y %H:%M:%S")
            ret.append(t)
            return tuple(ret)

        user = self.check_auth(irc, msg, args)
        if not user:
            return

        if from_reply:
            if not reply:
                if capab(user, 'admin'):
                    if len(queue.msgcache) > 0:
                            irc.reply("Warning: still syncing (%i)" % len(queue.msgcache))
                irc.reply("No matches found for %s in %s" % (hostmask, True and channel or "any channel"))
            hostmask = reply
        else:
            hostmask = self.nick_to_host(irc, target, reply_now=False)
        if not hostmask:
            self.sendWhois(irc, target, True, 'bansearch', irc, msg, args, target, channel)
            return
        match = self.getBans(hostmask, channel)

        if capab(user, 'owner'):
            if len(queue.msgcache) > 0:
                irc.reply("Warning: still syncing (%i)" % len(queue.msgcache))

        if channel:
            if not ircutils.isChannel(channel):
                channel = None

        if '*' in target or '?' in target:
            irc.error("Can only search for a complete hostmask")
            return
        hostmask = target
        if '!' not in target or '@' not in target:
            hostmask = self.nick_to_host(irc, target)
        if '!' not in hostmask:
            if "n=" in hostmask:
                hostmask = hostmask.replace("n=", "!n=", 1)
            elif "i=" in hostmask:
                hostmask = hostmask.replace("i=", "!i=", 1)
        match = self.getBans(hostmask, channel)

        if not match:
            irc.reply("No matches found for %s in %s" % (hostmask, True and channel or "any channel"))
            return
        ret = []
        replies = []
        for m in match:
            if m[1]:
                ret.append((format_entry(self.db_run("SELECT mask, operator, channel, time FROM bans WHERE id=%d", m[1], expect_result=True)[0]), m[1]))
        if not ret:
            done = []
            for c in self.bans:
                for b in self.bans[c]:
                    for m in match:
                        if m[0] == b.mask:
                            if not c in done:
                                irc.reply("Match %s in %s" % (b, c))
                                done.append(c)
            return
        for i in ret:
            if '*' in i[0][0] or '?' in i[0][0]:
                banstr = "Match: %s by %s in %s on %s (ID: %s)" % (i[0] + (i[1],))
            else:
                banstr = "Mark: by %s in %s on %s (ID: %s)" % (i[0][1:] + (i[1],))
            if (banstr, False) not in replies:
                replies.append((banstr, False))

        if replies:
            for r in replies:
                irc.reply(r[0], private=r[1])
            return
        irc.error("Something not so good happened, please tell stdin about it")

    bansearch = wrap(bansearch_real, ['something', optional('something', default=None)])

    def banlog(self, irc, msg, args, target, channel):
        """<nick|hostmask> [<channel>]

        Prints the last 5 messages from the nick/host logged before a ban/mute,
        the nick/host has to have an active ban/mute against it.
        If channel is not given search all channel bans.
        """
        user = self.check_auth(irc, msg, args)
        if not user:
            return

        if capab(user, 'owner') and len(queue.msgcache) > 0:
            irc.reply("Warning: still syncing (%i)" % len(queue.msgcache))

        hostmask = self.nick_to_host(irc, target)
        target = target.split('!', 1)[0]
        match = self.getBans(hostmask, channel)

        if not match:
            irc.reply("No matches found for %s (%s) in %s" % (target, hostmask, True and channel or "any channel"))
            return

        ret = []
        for m in match:
            if m[1]:
                ret.append((self.db_run("SELECT log, channel FROM bans WHERE id=%d", m[1], expect_result=True), m[1]))

        sent = []
        if not ret:
            irc.reply("No matches in tracker")
        for logs in ret:
            log = logs[0]
            id = logs[1]
            lines = ["%s: %s" % (log[0][1], i) for i in log[0][0].split('\n') if "<%s>" % target.lower() in i.lower() and i[21:21+len(target)].lower() == target.lower()]
            show_sep = False
            if not lines:
                show_sep = False
                irc.error("No log for ID %s available" % id)
            else:
                for l in lines[:5]:
                    if l not in sent:
                        show_sep = True
                        irc.reply(l)
                        sent.append(l)
            if show_sep:
                irc.reply('--')

    banlog = wrap(banlog, ['something', optional('anything', default=None)])

    def updatebt(self, irc, msg, args, channel):
        """[<channel>]

        Update bans in the tracker from the channel ban list,
        if channel is not given then run in all channels
        """

        def getBans(chan):
            data = self.db_run("SELECT mask, removal FROM bans WHERE channel=%s", chan, expect_result=True)
            L = []
            for mask, removal in data:
                if removal is not None:
                    continue
                elif not isUserHostmask(mask) and mask[0] != '$':
                    continue
                L.append(mask)
            return L

        def remBans(chan):
            bans = getBans(chan)
            old_bans = bans[:]
            new_bans = [i.mask for i in self.bans[chan]]
            remove_bans = []
            for ban in old_bans:
                if ban not in new_bans:
                    remove_bans.append(ban)
                    bans.remove(ban)

            for ban in remove_bans:
                self.log.info("Bantracker: Removing ban %s from %s" % (ban.replace('%', '%%'), chan))
                self.doUnban(irc, channel, "Automated-Removal", ban)

            return len(remove_bans)

        def addBans(chan):
            bans = self.bans[chan]
            old_bans = getBans(chan)
            add_bans = []
            for ban in bans:
                if ban.mask not in old_bans and ban not in add_bans:
                    add_bans.append(ban)

            for ban in add_bans:
                nick = ban.who
                if nick.endswith('.freenode.net'):
                    nick = "Automated-Addition"
                self.log.info("Bantracker: Adding ban %s to %s (%s)" % (str(ban).replace('%', '%%'), chan, nick))
                self.doLog(irc, channel.lower(), '*** Ban sync from channel: %s\n' % str(ban).replace('%', '%%'))
                self._doKickban(irc, chan, nick, ban.mask, use_time = ban.when)
            return len(add_bans)

        if not self.check_auth(irc, msg, args, 'owner'):
            return

        add_res = 0
        rem_res = 0

        if len(queue.msgcache) > 0:
            irc.reply("Error: still syncing (%i)" % len(queue.msgcache))
            return

        try:
            if channel:
                rem_res += remBans(channel)
                add_res += addBans(channel)
            else:
                for channel in irc.state.channels.keys():
                    if channel not in  self.bans:
                        self.bans[channel] = []
                    rem_res += remBans(channel)
                    add_res += addBans(channel)
        except KeyError, e:
            irc.error("%s, Please wait longer" % e)
            return

        irc.reply("Cleared %i obsolete bans, Added %i new bans" % (rem_res, add_res))

    updatebt = wrap(updatebt, [optional('anything', default=None)])

    def comment(self, irc, msg, args, id, kickmsg):
        """<id> [<comment>]

        Reads or adds the <comment> for the ban with <id>,
        use @bansearch to find the id of a ban
        """
        def addComment(id, nick, msg):
            n = now()
            self.db_run("INSERT INTO comments (ban_id, who, comment, time) values(%s,%s,%s,%s)", (id, nick, msg, n))
        def readComment(id):
            return self.db_run("SELECT who, comment, time FROM comments WHERE ban_id=%i", (id,), True)

        nick = msg.nick
        if kickmsg:
            addComment(id, nick, kickmsg)
            irc.replySuccess()
        else:
            data = readComment(id)
            if data:
                for c in data:
                    irc.reply("%s %s: %s" % (cPickle.loads(c[2]).astimezone(pytz.timezone('UTC')).strftime("%b %d %Y %H:%M:%S"), c[0], c[1].strip()) )
            else:
                irc.error("No comments recorded for ban %i" % id)
    comment = wrap(comment, ['id', optional('text')])

    def banlink(self, irc, msg, args, id, highlight):
        """<id> [<highlight>]

        Returns a link to the log of the ban/kick with id <id>.
        If <highlight> is given, lines containing that term will be highlighted
        """
        if not self.check_auth(irc, msg, args):
            return
        if not highlight:
            irc.reply("%s/bans.cgi?log=%s" % (self.registryValue('bansite'), id), private=True)
        else:
            irc.reply("%s/bans.cgi?log=%s&mark=%s" % (self.registryValue('bansite'), id, highlight), private=True)
    banlink = wrap(banlink, ['id', optional('somethingWithoutSpaces')])

    def banreview(self, irc, msg, args):
        """
        Lists pending ban reviews."""
        if not self.check_auth(irc, msg, args):
            return
        count = {}
        for reviews in self.pendingReviews.itervalues():
            for nick, msg in reviews:
                try:
                    count[nick] += 1
                except KeyError:
                    count[nick] = 1
        total = sum(count.itervalues())
        s = ' '.join([ '%s:%s' %pair for pair in count.iteritems() ])
        s = 'Pending ban reviews (%s): %s' %(total, s)
        irc.reply(s)

    banreview = wrap(banreview)

Class = Bantracker

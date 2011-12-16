# -*- Encoding: utf-8 -*-
###
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

from supybot.test import *

import supybot.conf as conf
import supybot.ircmsgs as ircmsgs
import supybot.world as world

import time


pluginConf = conf.supybot.plugins.Bantracker
pluginConf.enabled.setValue(True)
pluginConf.bansite.setValue('http://foo.bar.com')
pluginConf.database.setValue('bantracker-test.db')

def quiet(channel, hostmask, prefix='', msg=None):
    """Returns a MODE to quiet nick on channel."""
    return ircmsgs.mode(channel, ('+q', hostmask), prefix, msg)

class BantrackerTestCase(ChannelPluginTestCase):
    plugins = ('Bantracker',)

    def setUp(self):
        self.setDb()
        super(BantrackerTestCase, self).setUp()
        pluginConf.request.setValue(False) # disable comments
        pluginConf.request.ignore.set('')
        pluginConf.request.forward.set('')
        pluginConf.request.review.setValue(1.0/86400) # one second
        # Bantracker for some reason doesn't use Supybot's own methods for check capabilities,
        # so it doesn't have a clue about testing and screws my tests by default.
        # This would fix it until I bring myself to take a look
        cb = self.getCallback()
        f = cb.check_auth
        def test_check_auth(*args, **kwargs):
            if world.testing:
                return True
            else:
                return f(*args, **kwargs)
        cb.check_auth = test_check_auth

    def setDb(self):
        import sqlite, os
        dbfile = os.path.join(os.curdir, pluginConf.database())
        try:
            os.remove(dbfile)
        except:
            pass
        db = sqlite.connect(dbfile)
        cursor = db.cursor()
        cursor.execute('CREATE TABLE bans ('
                'id INTEGER PRIMARY KEY,'
                'channel VARCHAR(30) NOT NULL,'
                'mask VARCHAR(100) NOT NULL,'
                'operator VARCHAR(30) NOT NULL,'
                'time VARCHAR(300) NOT NULL,'
                'removal DATETIME,'
                'removal_op VARCHAR(30),'
                'log TEXT)')
        cursor.execute('CREATE TABLE comments ('
                'ban_id INTEGER,'
                'who VARCHAR(100) NOT NULL,'
                'comment MEDIUMTEXT NOT NULL,'
                'time VARCHAR(300) NOT NULL)')
        cursor.execute('CREATE TABLE sessions ('
                'session_id VARCHAR(50) PRIMARY KEY,'
                'user MEDIUMTEXT NOT NULL,'
                'time INT NOT NULL)')
        cursor.execute('CREATE TABLE users ('
                'username VARCHAR(50) PRIMARY KEY,'
                'salt VARCHAR(8),'
                'password VARCHAR(50))')
        db.commit()
        cursor.close()
        db.close()

    def getCallback(self):
        for cb in self.irc.callbacks:
            if cb.name() == 'Bantracker':
                break
        return cb

    def getDb(self):
        return self.getCallback().db

    def query(self, query, parms=()):
        cursor = self.getDb().cursor()
        cursor.execute(query, parms)
        return cursor.fetchall()

    def feedBan(self, hostmask, prefix='', channel=None, mode='b'):
        if not channel:
            channel = self.channel
        if not prefix:
            prefix = 'op!user@host.net'
        if mode == 'b':
            ban = ircmsgs.ban(channel, hostmask, prefix=prefix)
        elif mode == 'q':
            ban = quiet(channel, hostmask, prefix=prefix)
        elif mode == 'k':
            ban = ircmsgs.kick(channel, hostmask, s='kthxbye!', prefix=prefix)
        elif mode == 'p':
            ban = ircmsgs.part(channel, prefix=hostmask,
                    s='requested by %s (kthxbye!)' %prefix[:prefix.find('!')])
        self.irc.feedMsg(ban)
        return ban

    def testComment(self):
        pluginConf.request.setValue(True)
        # test bans
        self.feedBan('asd!*@*')
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(), 
            "PRIVMSG op :Please comment on the ban of asd!*@* in #test, use: @comment 1"
            " <comment>")
        # test quiets
        self.feedBan('dude!*@*', mode='q')
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(), 
            "PRIVMSG op :Please comment on the quiet of dude!*@* in #test, use: @comment 2"
            " <comment>")
        # test kick/part
        self.feedBan('dude', mode='k')
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(), 
            "PRIVMSG op :Please comment on the removal of dude in #test, use: @comment 3"
            " <comment>")
        self.feedBan('dude!dude@trollpit.com', mode='p')
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(), 
            "PRIVMSG op :Please comment on the removal of dude in #test, use: @comment 4"
            " <comment>")

    def testCommentIgnore(self):
        pluginConf.request.setValue(True)
        pluginConf.request.ignore.set('FloodBot? FloodBotK?')
        self.feedBan('asd!*@*', prefix='floodbotk1!bot@botpit.com')
        msg = self.irc.takeMsg()
        self.assertEqual(msg, None)
        self.feedBan('dude!*@*', mode='q', prefix='FloodBot1!bot@botpit.com')
        msg = self.irc.takeMsg()
        self.assertEqual(msg, None)
        self.feedBan('dude', mode='k', prefix='FloodBot2!bot@botbag.com')
        msg = self.irc.takeMsg()
        self.assertEqual(msg, None)
        self.feedBan('dude!dude@trollpit.com', mode='p', prefix='FloodBotK2!bot@botbag.com')
        msg = self.irc.takeMsg()
        self.assertEqual(msg, None)
        self.feedBan('asd!*@*')
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(), 
            "PRIVMSG op :Please comment on the ban of asd!*@* in #test, use: @comment 5"
            " <comment>")

    def testCommentForward(self):
        pluginConf.request.setValue(True)
        pluginConf.request.forward.set('bot')
        pluginConf.request.forward.channels.set('#channel')
        self.feedBan('qwe!*@*')
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(), 
            "PRIVMSG op :Please comment on the ban of qwe!*@* in #test, use: @comment 1"
            " <comment>")
        self.feedBan('zxc!*@*', prefix='bot!user@host.com')
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(), 
            "NOTICE #channel :Please somebody comment on the ban of zxc!*@* in #test done by bot,"
            " use: @comment 2 <comment>")

    def testReview(self):
        pluginConf.request.setValue(True)
        cb = self.getCallback()
        self.feedBan('asd!*@*')
        self.irc.takeMsg() # ignore comment request comment
        cb.reviewBans()
        self.assertFalse(cb.pendingReviews)
        print 'waiting 4 secs..'
        time.sleep(2)
        cb.reviewBans()
        # check is pending
        self.assertTrue(cb.pendingReviews)
        # send msg if a user with a matching host says something
        self.feedMsg('Hi!', frm='op!user@fakehost.net') 
        msg = self.irc.takeMsg()
        self.assertEqual(msg, None)
        self.feedMsg('Hi!', frm='op_!user@host.net') 
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(),
            "PRIVMSG op_ :Hi, please review the ban 'asd!*@*' that you set on %s in #test, link: "\
            "%s/bans.cgi?log=1" %(cb.bans['#test'][0].ascwhen, pluginConf.bansite()))
        # don't ask again
        cb.reviewBans()
        self.assertFalse(cb.pendingReviews)
        # test again with two ops
        self.feedBan('asd2!*@*')
        self.irc.takeMsg()
        self.feedBan('qwe!*@*', prefix='otherop!user@home.net')
        self.irc.takeMsg()
        time.sleep(2)
        cb.reviewBans()
        self.assertTrue(len(cb.pendingReviews) == 2)
        self.feedMsg('Hi!', frm='op!user@fakehost.net') 
        msg = self.irc.takeMsg()
        self.assertEqual(msg, None)
        self.assertResponse('banreview', 'Pending ban reviews (2): otherop:1 op:1')
        self.feedMsg('Hi!', frm='mynickissocreative!user@home.net') 
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(),
            "PRIVMSG mynickissocreative :Hi, please review the ban 'qwe!*@*' that you set on %s in #test, link: "\
            "%s/bans.cgi?log=3" %(cb.bans['#test'][2].ascwhen, pluginConf.bansite()))
        self.feedMsg('ping', to='test', frm='op!user@host.net') # in a query
        self.irc.takeMsg() # drop pong reply
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(),
            "PRIVMSG op :Hi, please review the ban 'asd2!*@*' that you set on %s in #test, link: "\
            "%s/bans.cgi?log=2" %(cb.bans['#test'][1].ascwhen, pluginConf.bansite()))

    def testReviewForward(self):
        pluginConf.request.setValue(True)
        pluginConf.request.forward.set('bot')
        pluginConf.request.forward.channels.set('#channel')
        cb = self.getCallback()
        self.feedBan('asd!*@*', prefix='bot!user@host.net')
        self.irc.takeMsg() # ignore comment request comment
        cb.reviewBans(self.irc)
        self.assertFalse(cb.pendingReviews)
        print 'waiting 2 secs..'
        time.sleep(2)
        cb.reviewBans(self.irc)
        # since it's a forward, it was sent already
        self.assertFalse(cb.pendingReviews)
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(),
            "NOTICE #channel :Hi, please somebody review the ban 'asd!*@*' set by bot on %s in #test, link: "\
            "%s/bans.cgi?log=1" %(cb.bans['#test'][0].ascwhen, pluginConf.bansite()))

    def testReviewIgnore(self):
        pluginConf.request.setValue(True)
        pluginConf.request.ignore.set('FloodBot? FloodBotK?')
        cb = self.getCallback()
        self.feedBan('asd!*@*', prefix='floodbotk1!bot@botpit.com')
        cb.reviewBans(self.irc)
        self.assertFalse(cb.pendingReviews)
        print 'waiting 2 secs..'
        time.sleep(2)
        cb.reviewBans(self.irc)
        # since it's was ignored, it should not be queued
        self.assertFalse(cb.pendingReviews)

    def testReviewNickFallback(self):
        """If for some reason we don't have ops full hostmask, revert to nick match. This may be
        needed in the future as hostmasks aren't stored in the db."""
        pluginConf.request.setValue(True)
        cb = self.getCallback()
        self.feedBan('asd!*@*')
        self.irc.takeMsg() # ignore comment request comment
        cb.bans['#test'][0].who = 'op' # replace hostmask by nick
        print 'waiting 2 secs..'
        time.sleep(2)
        cb.reviewBans()
        # check is pending
        self.assertTrue(cb.pendingReviews)
        self.assertResponse('banreview', 'Pending ban reviews (1): op:1')
        # send msg if a user with a matching nick says something
        self.feedMsg('Hi!', frm='op_!user@host.net') 
        msg = self.irc.takeMsg()
        self.assertEqual(msg, None)
        self.feedMsg('Hi!', frm='op!user@host.net') 
        msg = self.irc.takeMsg()
        self.assertEqual(str(msg).strip(),
            "PRIVMSG op :Hi, please review the ban 'asd!*@*' that you set on %s in #test, link: "\
            "%s/bans.cgi?log=1" %(cb.bans['#test'][0].ascwhen, pluginConf.bansite()))
        # check not pending anymore
        self.assertFalse(cb.pendingReviews)

    def testPersistentCache(self):
        """Save pending reviews and when bans were last checked. This is needed for plugin
        reloads"""
        msg1 = ircmsgs.privmsg('nick', 'Hello World')
        msg2 = ircmsgs.privmsg('nick', 'Hello World') # duplicate msg, should be ignored
        msg2 = ircmsgs.privmsg('nick', 'Hello World2')
        msg3 = ircmsgs.notice('#chan', 'Hello World')
        msg4 = ircmsgs.privmsg('nick_', 'Hello World')
        pr = self.getCallback().pendingReviews
        pr['host.net'] = [('op', msg1), ('op', msg2), ('op_', msg3)]
        pr['home.net'] = [('dude', msg4)]
        self.assertResponse('banreview', 'Pending ban reviews (4): op_:1 dude:1 op:2')
        pr.close()
        pr.clear()
        pr.open()
        self.assertResponse('banreview', 'Pending ban reviews (4): op_:1 dude:1 op:2')
        items = pr['host.net']
        self.assertTrue(items[0][0] == 'op' and items[0][1] == msg1)
        self.assertTrue(items[1][0] == 'op' and items[1][1] == msg2)
        self.assertTrue(items[2][0] == 'op_' and items[2][1] == msg3)
        items = pr['home.net']
        self.assertTrue(items[0][0] == 'dude' and items[0][1] == msg4)

    def testReviewBanreview(self):
        pr = self.getCallback().pendingReviews
        m = ircmsgs.privmsg('#test', 'asd')
        pr['host.net'] = [('op', m), ('op_', m), ('op', m)]
        pr['home.net'] = [('dude', m)]
        self.assertResponse('banreview', 'Pending ban reviews (4): op_:1 dude:1 op:2')

    def testBan(self):
        self.feedBan('asd!*@*')
        fetch = self.query("SELECT id,channel,mask,operator FROM bans")
        self.assertEqual((1, '#test', 'asd!*@*', 'op'), fetch[0])

    def testQuiet(self):
        self.feedBan('asd!*@*', mode='q')
        fetch = self.query("SELECT id,channel,mask,operator FROM bans")
        self.assertEqual((1, '#test', '%asd!*@*', 'op'), fetch[0])

    def testKick(self):
        self.feedBan('troll', mode='k')
        fetch = self.query("SELECT id,channel,mask,operator FROM bans")
        self.assertEqual((1, '#test', 'troll', 'op'), fetch[0])

    def testPart(self):
        self.feedBan('troll!user@trollpit.net', mode='p')
        fetch = self.query("SELECT id,channel,mask,operator FROM bans")
        self.assertEqual((1, '#test', 'troll', 'op'), fetch[0])




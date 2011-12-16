#!/usr/bin/env python
###
# Copyright (c) 2005-2007 Dennis Kaarsemaker
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

import sys
# This needs to be set to the location of the commoncgi.py file
sys.path.append('/var/www/bot')
from commoncgi import *

### Variables
db       = '/home/bot/data/bans.db'
num_per_page = 100

con = sqlite.connect(db)
cur = con.cursor()

# Login check
error    = ''
user = None

# Delete old sessions
try:
    cur.execute("""DELETE FROM sessions WHERE time < %d""", int(time.time()) - 2592000 * 3)
except:
    pass

# Session handling
if form.has_key('sess'):
    cookie['sess'] = form['sess'].value
if cookie.has_key('sess'):
    try:
        sess = cookie['sess'].value
        cur.execute("""SELECT user FROM sessions WHERE session_id=%s""",sess)
        user = cur.fetchall()[0][0]
    except:
        con.commit()
        pass

if not user:
    print "Sorry, bantracker has been shut down for anonymous users due to server load<br>"
    print "Join <a href=irc://irc.freenode.net/ubuntu-ops>#ubuntu-ops</a> on irc.freenode.net to discuss bans"
    send_page('bans.tmpl')

# Log
if form.has_key('log'):
   cur.execute("""SELECT log FROM bans WHERE id=%s""", form['log'].value)
   log = cur.fetchall()
   con.commit()
   if form.has_key('mark'):
      marked = form['mark'].value
      lines = log[0][0].splitlines()
      for line in lines:
         if marked.lower() in line.lower():
            print '<font style="BACKGROUND-COLOR: yellow">%s</font><br>' % q(line)
         else:
            print "%s<br>" % q(line)
   else:
      print q(log[0][0]).replace('\n', '<br />')
   send_page('empty.tmpl')

# Main page
# Process comments
if form.has_key('comment') and form.has_key('comment_id') and user:
    cur.execute("""SELECT ban_id FROM comments WHERE ban_id=%s and comment=%s""", (form['comment_id'].value, form['comment'].value))
    comm = cur.fetchall()
    if not len(comm):
        cur.execute("""INSERT INTO comments (ban_id, who, comment, time) VALUES (%s, %s, %s, %s)""",
                    (form['comment_id'].value,user,form['comment'].value,pickle.dumps(datetime.datetime.now(pytz.UTC))))
    con.commit()

# Write the page
print '<form action="bans.cgi" method="POST">'

# Personal data
print '<div class="pdata">'
if user:
    print 'Logged in as: %s <br /> ' % user

print 'Timezone: '
if form.has_key('tz') and form['tz'].value in pytz.common_timezones:
    tz = form['tz'].value
elif cookie.has_key('tz') and cookie['tz'].value in pytz.common_timezones:
    tz = cookie['tz'].value
else:
    tz = 'UTC'
cookie['tz'] = tz
print '<select class="input" name="tz">'
for zone in pytz.common_timezones:
    print '<option value="%s"' % zone
    if zone == tz:
        print ' selected="selected"'
    print ">%s</option>" % zone
print '</select><input class="submit" type="submit" value="change" /></form><br />'
print '</div>'

tz = pytz.timezone(tz)

# Search form
print '<div class="search">'
print '<form action="bans.cgi" method="GET">'
print '<input class="input" type="text" name="query"'
if form.has_key('query'):
   print 'value="%s" ' % form['query'].value
print '/> Search string (% is wildcard)<br />'

# Search fields
print '<div style="float:left">'
print '<input class="input" type="checkbox" name="kicks" '
if form.has_key('kicks') or not form.has_key('query'):
    print 'checked="checked" '
print '/> Search in kicks<br />'
print '<input class="input" type="checkbox" name="oldbans" '
if form.has_key('oldbans') or not form.has_key('query'):
    print 'checked="checked" '
print '/> Search in removed bans<br />'
print '<input class="input" type="checkbox" name="bans" '
if form.has_key('bans') or not form.has_key('query'):
    print 'checked="checked"  '
print '/> Search in existing bans<br />'
print '</div>'
    
print '<div style="float:left">'
print '<input class="input" type="checkbox" name="oldmutes" '
if form.has_key('oldmutes') or not form.has_key('query'):
    print 'checked="checked" '
print '/> Search in removed mutes<br />'
print '<input class="input" type="checkbox" name="mutes" '
if form.has_key('mutes') or not form.has_key('query'):
    print 'checked="checked"  '
print '/> Search in existing mutes<br />'
print '<input class="input" type="checkbox" name="floods" '
if form.has_key('floods') or not form.has_key('query'):
    print 'checked="checked"  '
print '/> Include FloodBots<br />'
print '</div>'
    
print '<div style="clear:both"><input  class="submit" type="submit" value="search" /></div>'
print '</form></div>'

# Pagination, only when not processing a search
if not form.has_key('query'):
    sort = ''
    if form.has_key('sort'):
        sort='&sort=' + form['sort'].value
    print '<div style="clear: both">&middot;'
    cur.execute('SELECT COUNT(id) FROM bans')
    nump = int(math.ceil(int(cur.fetchall()[0][0]) / float(num_per_page)))
    for i in range(nump):
        print '<a href="bans.cgi?page=%d%s">%d</a> &middot;' % (i, sort, i+1)
    print '</div>'

# Empty log div, will be filled with AJAX
print '<div id="log" class="log">&nbsp;</div>'

# Main bans table
# Table heading
print '<table cellspacing="0" ><tr>'
for h in [['Channel',0], ['Nick/Mask',1], ['Operator',2], ['Time',6]]:
    # Negative integers for backwards searching
    try:
        v = int(form['sort'].value)
        if v < 10: h[1] += 10
    except:
        pass
    print '<th><a href="bans.cgi?sort=%s">%s</a></th>' % (h[1],h[0])
print '<th>Log</th></tr>'

# Select and filter bans
def getBans(id=None):
    if id == None:
        cur.execute("SELECT channel,mask,operator,time,removal,removal_op,id FROM bans ORDER BY id DESC")
    else:
        cur.execute("SELECT channel,mask,operator,time,removal,removal_op,id FROM bans ORDER BY id DESC WHERE id = %d", id)
    return cur.fetchall()

def myfilter(item, regex, kick, ban, oldban, mute, oldmute, floods, operator, channel):
    if operator:
        if not operator.lower() in item[2].lower(): return False
    if channel:
        if not channel.lower() in item[0].lower(): return False
    if '!' not in item[1]: 
        if not kick: return False
    if not floods:
        if 'floodbot' in item[2].lower(): return False
    if item[1][0] == '%':
        if item[4]:
            if not oldmute: return False
        else:
            if not mute: return False
    else:
        if item[4]:
            if not oldban: return False
        else:
            if not ban: return False
    if operator:
        return regex.search(item[1]) or regex.search(item[0]) or (item[5] and regex.search(item[5]))
    return regex.search(item[1]) or regex.search(item[2]) or regex.search(item[0]) or (item[5] and regex.search(item[5]))

def getQueryTerm(query, term):
    if term[-1] != ':':
        term += ':'
    if term in query:
        idx = query.index(term) + len(term)
        ret = query[idx:].split(None, 1)[0]
        query = query.replace(term + ret, '', 1).strip()
        return (query, ret)
    return (query, None)

bans = []

if form.has_key('query'):
    try:
        bans = getBans(int(form['query'].value))
        start = 0; end = 1
    except:
        bans = getBans()
        k = b = ob = m = om = fb = False
        oper = chan = False
        if form.has_key('kicks'):    k  = True
        if form.has_key('oldbans'):  ob = True
        if form.has_key('bans'):     b  = True
        if form.has_key('oldmutes'): om = True
        if form.has_key('mutes'):    m  = True
        if form.has_key('floods'):   fb = True
        if "chan:" in form['query'].value:
            (form['query'].value, chan) = getQueryTerm(form['query'].value, "chan:")
        if "oper:" in form['query'].value:
            (form['query'].value, oper) = getQueryTerm(form['query'].value, "oper:")
        regex = re.compile(re.escape(form['query'].value).replace('\%','.*'), re.DOTALL | re.I)
        bans = filter(lambda x: myfilter(x, regex, k, b, ob, m, om, fb, oper, chan), bans)
        start = 0; end = len(bans)
else:
    page = 0
    try:
        page = int(form['page'].value)
    except:
        pass
    start = page * num_per_page
    end = (page+1) * num_per_page

# Sort the bans
def _sortf(x1,x2,field):
   if x1[field] < x2[field]: return -1
   if x1[field] > x2[field]: return 1
   return 0
        
if form.has_key('sort'):
    try:
        field = int(form['sort'].value)
    except:
        pass
    else:
        if field in (0,1,2,6,10,11,12,16):
            bans.sort(lambda x1,x2: _sortf(x1,x2,field%10))
            if field >= 10:
                bans.reverse()

# And finally, display them!
i = 0
for b in bans[start:end]:
    print '<tr'
    if i % 2:
        print ' class="bg2"'
    i += 1
    print '>'
    # Channel
    print '<td> %s</td>' % b[0]
    # Mask
    print '<td>%s' % b[1]
    # Ban removal
    if b[4]:
        print '<br /><span class="removal">(Removed)</span>'
    print'</td>'
    # Operator
    print '<td>%s' % b[2]
    if b[4]:                  # Ban removal
        print u'<br /><span class="removal">%s</span>' % b[5]
    print '</td>'
    # Time
    print '<td>%s'      % pickle.loads(b[3]).astimezone(tz).strftime("%b %d %Y %H:%M:%S")
    if b[4]:                  # Ban removal
        print '<br /><span class="removal">%s</span>' % pickle.loads(b[4]).astimezone(tz).strftime("%b %d %Y %H:%M:%S")
    print '</td>'
    # Log link
    print '<td><span class="pseudolink" onclick="showlog(\'%s\')">Show/Hide log</span></td>' % b[6]
    print '</tr>'
    
    # Comments
    print '<tr'
    if not i % 2:
        print ' class="bg2"'
    print '>'
    print '<td colspan="5" class="comment">'
    cur.execute("""SELECT who, comment, time FROM comments WHERE ban_id = %s""" % b[6])
    comments = cur.fetchall()
    if len(comments) == 0:
        print '<span class="removal">(No comments) </span>'
    else:
        for c in comments:
            print q(c[1])
            print u' <span class="removal"><br />%s, %s</span><br />' % \
                (c[0],pickle.loads(c[2]).astimezone(tz).strftime("%b %d %Y %H:%M:%S"))
    if user:
        print """<span class="pseudolink" onclick="toggle('%s','comment')">Add comment</span>""" % b[6]
        print """<div class="invisible" id="comment_%s"><br />""" % b[6]
        print """<form action="bans.cgi" method="POST"><textarea cols="50" rows="5" class="input" name="comment"></textarea><br />"""
        print """<input type="hidden" name="comment_id" value="%s" />""" % b[6]
        print """<input class="submit" type="submit" value="Send" /></form>"""
    print '</td></tr>'

print '</table>'

if not bans and form.has_key('query'):
    if chan and oper:
        print "<center><u>No matches for:</u> &quot;%s&quot in %s by %s;</center>" % (form['query'].value, chan, oper)
    elif chan:
        print "<center><u>No matches for:</u> &quot;%s&quot; in %s</center>" % (form['query'].value, chan)
    elif oper:
        print "<center><u>No matches for:</u> &quot;%s&quot; by %s</center>" % (form['query'].value, oper)
    else:
        print "<center><u>No matches for:</u> &quot;%s&quot;</center>" % form['query'].value

# Aaaaaaaaaaaaaaaaand send!
send_page('bans.tmpl')

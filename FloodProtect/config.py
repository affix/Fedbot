###
# Copyright (c) 2008, Nicolas Coevoet
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

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('FloodProtect', True)

FloodProtect = conf.registerPlugin('FloodProtect')
conf.registerGlobalValue(FloodProtect, 'lifeQueueKick',registry.PositiveInteger(7, """Queue life for flood kick detection ( in seconds : default 7)"""))
conf.registerGlobalValue(FloodProtect, 'lifeQueueBan',registry.PositiveInteger(600, """Queue life for flood ban detection ( in seconds : default 600)"""))
conf.registerGlobalValue(FloodProtect, 'lifeQueueLongBan',registry.PositiveInteger(3600, """Queue life for flood long ban detection ( in seconds : default 3600)"""))

conf.registerChannelValue(FloodProtect, 'enable',registry.Boolean(False, """Enable channel flood protection"""))
conf.registerChannelValue(FloodProtect, 'reasonKick',registry.String("don't flood : use pastebin to copy/paste, please.", """kick reason"""))
conf.registerChannelValue(FloodProtect, 'reasonBan',registry.String("flood : banned during %s", """Kick reason when ban is put"""))
conf.registerChannelValue(FloodProtect,	'maxKick',registry.PositiveInteger(4, """max message of an user during 'lifeQueueKick' before kick"""))
conf.registerChannelValue(FloodProtect,	'maxKickToBan',registry.PositiveInteger(1, """max kick before ban during 'lifeQueueBan'"""))
conf.registerChannelValue(FloodProtect,	'maxBanToLongBan',registry.PositiveInteger(1, """max short ban before long ban during 'lifeQueueLongBan'"""))
conf.registerChannelValue(FloodProtect,	'durationBan',registry.PositiveInteger(900, """ban duration in seconds"""))
conf.registerChannelValue(FloodProtect,	'durationLongBan',registry.PositiveInteger(86400, """long ban duration in seconds"""))

# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=79:




###
# Copyright (c) 2005, Jeremiah Fincher
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

import time

import supybot.conf as conf
import supybot.registry as registry

def configure(advanced):
    from supybot.questions import output, expect, anything, something, yn
    conf.registerPlugin('BadWords', True)
    if yn('Would you like to add some bad words?'):
        words = anything('What words? (separate individual words by spaces)')
        conf.supybot.plugins.BadWords.words.set(words)

class LastModifiedSetOfStrings(registry.SpaceSeparatedSetOfStrings):
    lastModified = 0
    def setValue(self, v):
        self.lastModified = time.time()
        registry.SpaceSeparatedListOfStrings.setValue(self, v)

BadWords = conf.registerPlugin('BadWords')
conf.registerGlobalValue(BadWords, 'words',
    LastModifiedSetOfStrings([], """Determines what words are
    considered to be 'bad' so the bot won't say them."""))
conf.registerGlobalValue(BadWords,'requireWordBoundaries',
    registry.Boolean(False, """Determines whether the bot will require bad
    words to be independent words, or whether it will censor them within other
    words.  For instance, if 'darn' is a bad word, then if this is true, 'darn'
    will be censored, but 'darnit' will not.  You probably want this to be
    false."""))

class String256(registry.String):
    def __call__(self):
        s = registry.String.__call__(self)
        return s * (1024/len(s))

    def __str__(self):
        return self.value

conf.registerGlobalValue(BadWords, 'nastyChars',
    String256('!@#&', """Determines what characters will replace bad words; a
    chunk of these characters matching the size of the replaced bad word will
    be used to replace the bad words you've configured."""))

class ReplacementMethods(registry.OnlySomeStrings):
    validStrings = ('simple', 'nastyCharacters')

conf.registerGlobalValue(BadWords, 'replaceMethod',
    ReplacementMethods('nastyCharacters', """Determines the manner in which
    bad words will be replaced.  'nastyCharacters' (the default) will replace a
    bad word with the same number of 'nasty characters' (like those used in
    comic books; configurable by supybot.plugins.BadWords.nastyChars).
    'simple' will replace a bad word with a simple strings (regardless of the
    length of the bad word); this string is configurable via
    supybot.plugins.BadWords.simpleReplacement."""))
conf.registerGlobalValue(BadWords,'simpleReplacement',
    registry.String('[CENSORED]', """Determines what word will replace bad
    words if the replacement method is 'simple'."""))
conf.registerGlobalValue(BadWords, 'stripFormatting',
    registry.Boolean(True, """Determines whether the bot will strip
    formatting characters from messages before it checks them for bad words.
    If this is False, it will be relatively trivial to circumvent this plugin's
    filtering.  If it's True, however, it will interact poorly with other
    plugins that do coloring or bolding of text."""))

conf.registerChannelValue(BadWords, 'kick',
    registry.Boolean(False, """Determines whether the bot will kick people with
    a warning when they use bad words."""))
conf.registerChannelValue(BadWords.kick, 'message',
    registry.NormalizedString("""You have been kicked for using a word
    prohibited in the presence of this bot.  Please use more appropriate
    language in the future.""", """Determines the kick message used by the bot
    when kicking users for saying bad words."""))

conf.registerChannelValue(BadWords, 'kickban',
    registry.Boolean(False, """Determines whether the bot will kickban people with
    a warning when they use bad words."""))
conf.registerChannelValue(BadWords.kickban, 'message',
    registry.NormalizedString("""You have been kicked for using a word
    prohibited in the presence of this bot.  Please use more appropriate
    language in the future.""", """Determines the kick message used by the bot
    when kicking users for saying bad words."""))
 
conf.registerChannelValue(BadWords.kickban, 'banexpire',
    registry.Integer(0, """How long a ban should last for BadWords
    kickban."""))

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

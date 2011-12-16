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
"""
This plugin can store all kick/ban/remove/mute actions
"""

import supybot
import supybot.world as world

__version__ = "0.3.1"
__author__ = supybot.Author("Terence Simpson", "tsimpson", "tsimpson@ubuntu.com")
__contributors__ = {
    supybot.Author("Elián Hanisch", "m4v", "lambdae2@gmail.com"): ['Author', 'Maintainer'],
    supybot.Author("Dennis Kaarsemaker","Seveas","dennis@kaarsemaker.net"): ['Original Author']
}
__url__ = 'https://launchpad.net/ubuntu-bots/'

import config
reload(config)
import plugin
reload(plugin)

if world.testing:
    import test

Class = plugin.Class
configure = config.configure


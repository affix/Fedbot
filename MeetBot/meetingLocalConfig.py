class Config(object):
   #
   # Throw any overrides into meetingLocalConfig.py in this directory:
   #
   # Where to store files on disk
   logFileDir = '/home/brand1/kevin/.public_html/fedora/'
   # The links to the logfiles are given this prefix
   logUrlPrefix = 'http://www.scrye.com/~kevin/fedora/'
   # Give the pattern to save files into here.  Use %(channel)s for
   # channel.  This will be sent through strftime for substituting it
   # times, howover, for strftime codes you must use doubled percent
   # signs (%%).  This will be joined with the directories above.
   filenamePattern = '%(channel)s/%%Y/%(meetingname)s.%%F-%%H.%%M'
   # Where to say to go for more information about MeetBot
   MeetBotInfoURL = 'http://wiki.debian.org/MeetBot'
   # This is used with the #restrict command to remove permissions from files.
   #RestrictPerm = stat.S_IRWXO|stat.S_IRWXG  # g,o perm zeroed
   # RestrictPerm = stat.S_IRWXU|stat.S_IRWXO|stat.S_IRWXG  # u,g,o perm zeroed.
   # used to detect #link :
   UrlProtocols = ('http:', 'https:', 'irc:', 'ftp:', 'mailto:', 'ssh:')
   # regular expression for parsing commands.  First group is the command name,
   # second group is the rest of the line.
   #command_RE = re.compile(r'#([\w]+)[ \t]*(.*)')
   # This is the help printed when a meeting starts
   #usefulCommands = "#action #agreed #halp #info #idea #link #topic"
   # The channels which won't have date/time appended to the filename.
   #specialChannels = ("#meetbot-test", "#meetbot-test2")
   #specialChannelFilenamePattern = '%(channel)s/%(channel)s'
   # HTML irc log highlighting style.  `pygmentize -L styles` to list.
   pygmentizeStyle = 'colorful'
   # Timezone setting.  You can use friendly names like 'US/Eastern', etc.
   # Check /usr/share/zoneinfo/ .  Or `man timezone`: this is the contents
   # of the TZ environment variable.
   timeZone = 'UTC'

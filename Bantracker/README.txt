This plugin can store all bans/kicks etc in an sqlite database. It includes a
cgi script to view bans/kicks and comment on them. To view/user the bantracker
web interface a user must use the @btlogin command from the bot. They must also
have the 'bantracker' capability.
You can use the @mark <nick|hostmask> [<channel>] [<comment>]
command to manually add an entry to the bantracker without having to actially
kick/ban someone.

It also uses commoncgi.py which should be on your sys.path (or as you can see in
the script, sys.path is modified to include the dir of commoncgi.py)

The schema of the sqlite database:

CREATE TABLE bans (
                        id INTEGER PRIMARY KEY,
                        channel VARCHAR(30) NOT NULL,
                        mask VARCHAR(100) NOT NULL,
                        operator VARCHAR(30) NOT NULL,
                        time VARCHAR(300) NOT NULL,
                        removal DATETIME,
                        removal_op VARCHAR(30),
                        log TEXT
                   );
CREATE TABLE comments (
                        ban_id INTEGER,
                        who VARCHAR(100) NOT NULL,
                        comment MEDIUMTEXT NOT NULL,
                        time VARCHAR(300) NOT NULL
                   );
CREATE TABLE sessions (
                        session_id VARCHAR(50) PRIMARY KEY,
                        user MEDIUMTEXT NOT NULL,
                        time INT NOT NULL
);
CREATE TABLE users (
                        username VARCHAR(50) PRIMARY KEY,
                        salt VARCHAR(8),
                        password VARCHAR(50)
);

To configure the plugin, create the sqlite database with above structure and set
supybot.plugins.bantracker.database to its filename. Then enable it per channel
by setting the channel variable supybot.plugins.bantracker.enabled

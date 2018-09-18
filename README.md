# scribe

Scribe is a Discord bot that transcribes messages on command.

## Basic Usage

Use `!pin <first few words of message>` to pin a single message.

```
!quote
<first few words of start message>
<first few words of end message>
```

pins a message block.

The bot also accepts message IDs. You can copy any message's ID by turning on Developer Mode in the Appearance menu of Discord settings. This seems to be the only thing Developer Mode does.

Use `!pinfile` to grab the current channel's pin file, or `!pinfile #channel` to obtain another channel's pin file.

Use `!invite` to obtain an invite for Scribe, or use this link: https://discordapp.com/api/oauth2/authorize?client_id=413082884912578560&permissions=0&scope=bot

## Support
Go to https://discord.gg/Tk6G9Gr for Scribe support.

## Setup
Requirements:
* Python 3.5 (I recommend using `python3 -m venv` or `virtualenv`)
* Working PostgreSQL repository
* The following Python modules (`pip install -U modulename`):
  * discord.py rewrite (use pip to install from git: `pip install -U git+https://github.com/Rapptz/discord.py@rewrite`)
  * asyncpg
* Discord developer account with a bot user created - have its token ready
To setup:
* Clone this repository
* Make a postgres database called `scribe`:
  * `create user scribe with password 'PWD';`
  * `create database scribe;`
  * `grant all privileges on database scribe to scribe;`
  * copy `demo_scribe_config.py` to `config.py` and fill in your database credentials and bot token
* in a tmux or screen, activate your virtualenv if needed, then run `python scribe.py`
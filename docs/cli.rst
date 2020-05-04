.. _cli:

CWS Command Line Interface
==========================

cws
---

``cws`` is a command-line shell program that provides convenience and productivity
features to help user to :

 * Export information from microservice definition
 * Update deployed services

Usage
-----

::

	$ cws --help
	Usage: cws [OPTIONS] COMMAND [ARGS]...

	Options:
	  --version               Show the version and exit.
	  -p, --project-dir TEXT  The project directory path (absolute or relative).
				  Defaults to CWD

	  --help                  Show this message and exit.

	Commands:
	  export  Exports microservice description in other descrioption languages.
	  info    Information on a microservice.
	  init    Init chalice configuration file.
	  run     Runs local server.
	  update

init
^^^^

The ``init`` command allows to create the chalice environment project, usefull to run your code locally::

	$ cws init --help
	Usage: cws init [OPTIONS]

	  Init chalice configuration file.

	Options:
	  --force / --no-force  Forces project reinitialization.
	  --help                Show this message and exit.


Then to create the new initialized folder ``src``::

	$ cws --project-dir src init
	Project src initialized

info
^^^^

The ``info`` command returns information on a microservice as a JSON string::

	$ cws info --help
	Usage: cws info [OPTIONS]

	  Information on a microservice.

	Options:
	  -m, --module TEXT  Filename of your microservice python source file.
	  -a, --app TEXT     Coworks application in the source file.
	  --help             Show this message and exit.


Then to get info on the example::

	$ cws -p src info
	{"name": "SimpleMicroService", "type": "tech"}

run
^^^

The ``run`` command runs your service locally as a simple HTTP server::

	$ cws run --help
	Usage: cws run [OPTIONS]

	  Runs local server.

	Options:
	  -m, --module TEXT     Filename of your microservice python source file.
	  -a, --app TEXT        Coworks application in the source file.
	  -h, --host TEXT
	  -p, --port INTEGER
 	  --debug / --no-debug  Print debug logs to stderr.
	  --help                Show this message and exit.




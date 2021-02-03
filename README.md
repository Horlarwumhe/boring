
### Boring

A simple [HTTP](https://en.m.wikipedia.org/wiki/Hypertext_Transfer_Protocol) webserver for [WSGI]( https://en.m.wikipedia.org/wiki/Web_Server_Gateway_Interface) compatible web app, 
support any wsgi web framework , django,flask, bottle and others. it is fairly fast .........


### installation

boring has no dependency except python standard library, so it can be installed by cloning this repository , then run python setup.py install , or install from `pypi` with `pip install boring`

## Starting the server

`boring myapp:app` or `python -m boring myapp:app`

assuming there is myapp.py in the current directory and and a callable object `app` in myapp.py

using boring with django
`boring yourproject.wsgi` or `python -m boring yourproject.wsgi`

## command line options
	usage: boring [-h] [-p PORT] [--reload] [-b BIND] [--use-config] [-v] app

	positional arguments:
	  app                   wsgi app to load

	optional arguments:
	  -h, --help            show this help message and exit

	  -p PORT, --port PORT  port number to use, default 8000

	  --reload              enable auto reload

	  -b BIND, --bind BIND  bind to this address

	   --use-config          use configuration for boring

	  -v, --version         show program's version number and exit


## Serving Static Files

boring can be configured to serve static files (js,css,images and others). to serve static files ,create a file `boring.config` and add the following to the config file
` STATIC_URL=url # url for serving files eg /static/ for django and others`
` STATIC_ROOT=path  # folder where to find static files`
then add `--use-config` to the command line argument when starting the server

### Boring in action

[test-boring.herokuapp.com](http://test-boring.herokuapp.com) , is flask webapp copied from [miguelgrinberg blog](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) running boring as http server

[firdawss.herokuapp.com](http://firdawss.herokuapp.com) a django powered site running boring as the webserver


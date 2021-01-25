
#### Boring

A simple [HTTP](https://en.m.wikipedia.org/wiki/Hypertext_Transfer_Protocol) webserver for [WSGI]( https://en.m.wikipedia.org/wiki/Web_Server_Gateway_Interface) compatible web app, 
support any wsgi web framework , django,flask, bottle and others


#### installation

boring has no dependency except python standard library, so it can be installed by cloning this repository, then run python setup.py install

#### Starting the server

`python -m boring myapp:app`

assuming there is myapp.py in the current directory and and a callable object app in myapp.py

#### command line options
   -b  <addr>   bind to the addr , default 0.0.0.0

   -p <port>   port number to use , default 8000

  --reload      to enable auto reload when any files change, default to false


#### example 

  just-a-tests.herokuapp.com , is flask webapp copied from [miguelgrinberg blog](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) running boring as http server

 
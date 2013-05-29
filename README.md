Flask-WebTest
=============

Flask-WebTest provides a set of utilities to ease testing Flask applications with WebTest.

`flask.ext.webtest.TestApp` extends `webtest.TestApp` by adding few useful fields to response:

* `response.templates` ― dictionary containing information about what templates were used to build the response and what their contexts were. The keys are template names and the values are template contexts.  
  If only one template was used, it's name and context can be accessed through `response.template` and `response.context`.

* `response.flashes` ― list of tuples (category, message) containing flashed messages.  
*Note*:  
This is fully supported only starting with Flask 0.10 (which is not released at the time of writing).  
If you use previous version, `response.flashes` will contain only those messages that was consumed by `get_flashed_messages()` _template_ call.

* `response.session` ― dictionary containing session data.

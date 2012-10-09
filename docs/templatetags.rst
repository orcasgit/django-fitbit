Template tags
==============

.. _is_integrated_with_fitbit:

is_integrated_with_fitbit
--------------------------

This filter takes a user and returns True if the user has granted us access to their fitbit data.

For example::

    {% if {{ request.user|is_integrated_with_fitbit }} %}
        do something
    {% else %}
        do something else
    {% endif %}

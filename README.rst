========================
sqlalchemy-csv-normalise
========================


.. image:: https://img.shields.io/pypi/v/sqlalchemy-csv-normalise.svg
        :target: https://pypi.python.org/pypi/sqlalchemy-csv-normalise

.. image:: https://travis-ci.com/mohawk2/sqlalchemy-csv-normalise.svg?branch=master
        :target: https://travis-ci.com/mohawk2/sqlalchemy-csv-normalise

.. image:: https://readthedocs.org/projects/sqlalchemy-csv-normalise/badge/?version=latest
        :target: https://sqlalchemy-csv-normalise.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


.. image:: https://pyup.io/repos/github/mohawk2/sqlalchemy-csv-normalise/shield.svg
     :target: https://pyup.io/repos/github/mohawk2/sqlalchemy-csv-normalise/
     :alt: Updates



SQLAlchemy utilities for normalising / denormalising table data, useful for CSV


Where a table is normalised to have "lookup tables" of values
referred to by e.g. a numeric foreign-key ID, these functions will
enable extraction of the data (or conversely, loading from such)
with the looked-up values substituted in. Among other things, this
allows more human-friendly data editing in e.g. a spreadsheet.

Example::

    from sqlalchemy_csv_normalise import denormalise_prepare
    q, col_names = denormalise_prepare(db.session, table)
    filename = table_to_filename(table)
    with open(filename, 'w', newline='') as csv_file:
        csv_file_writer = csv.writer(csv_file)
        csv_file_writer.writerow(col_names)
        csv_file_writer.writerows(q.all())

    from sqlalchemy_csv_normalise import renormalise_prepare, empty_deleter,\
        type_coercer
    row_maker = renormalise_prepare(db.session, table)
    row_cleaner = empty_deleter(table)
    row_coercer = type_coercer(table)
    filename = table_to_filename(table)
    with open(filename, newline='') as csv_file:
        for d in csv.DictReader(csv_file):
            row = row_coercer(row_cleaner(row_maker(d)))
            db.session.add(table(**row))
    db.session.commit()


* Free software: MIT license
* Documentation: https://sqlalchemy-csv-normalise.readthedocs.io.


Features
--------

* denormalise_prepare(session, table, colname_tidier)

Returns SQLAlchemy query, and the column-names it will return.
The query will denormalise any foreign keys (FKs) if they refer to a
table with a unique column that is not its primary key.

The names of any FK columns will have `_id` taken off the end
as a simple heuristic. Override this by providing a `colname_tidier`.


* empty_deleter(table)

Returns function that returns given dict minus empty strings for nullable
columns.
Useful because CSV has no way to record NULL.

* type_coercer(table)

Returns function that given a row dict will coerce values.
Works on dates and booleans.

* renormalise_prepare(session, table, colname_tidier)

Returns function that will renormalise given dictionary
Does the inverse of denormalise_prepare.

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

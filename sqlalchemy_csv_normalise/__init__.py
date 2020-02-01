"""Functions to denormalise and renormalise SQLAlchemy tables

These are useful for writing the contents of tables out e.g. to CSV
files, and reading them back in.

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
"""

__author__ = """Ed J"""
__email__ = 'mohawk2@users.noreply.github.com'
__version__ = '0.1.2'

from sqlalchemy import inspect
import datetime
import dateutil.parser

_COERCE = {
    datetime.datetime: dateutil.parser.parse,
    datetime.date: dateutil.parser.parse,
    bool: lambda v: v == "True",
}

def find_natural_key(table):
    """
    Find the natural key from unique columns in table, or return the primary keys.
    """
    primary_keys, foreign_keys, other = columns_partition(table)
    natural_keys = [ c for c in other if c.unique ]
    if len(natural_keys) == 1:
        # if >1, can't function as primary key because not unique as composite
        return natural_keys
    return primary_keys

def columns_partition(table):
    """Partitions columns into primary keys, foreign keys, other.
    Columns will only be considered primary keys if not also foreign keys.
    This is the most useful way to treat them for these purposes.
    """
    primary_keys, foreign_keys, other = [], [], []
    for name, c in inspect(table).columns.items():
        if c.foreign_keys:
            foreign_keys.append(c)
        elif c.primary_key:
            primary_keys.append(c)
        else:
            other.append(c)
    return (primary_keys, foreign_keys, other)

def _tidy_colname(n):
    # simple heuristic
    import re
    return re.sub('_id$', '', n)

def denormalise_prepare(session, table, colname_tidier=_tidy_colname):
    """Returns SQLAlchemy query, and the column-names it will return.
    The query will denormalise any foreign keys (FKs) if they refer to a
    table with a unique column that is not its primary key.

    The names of any FK columns will have `_id` taken off the end
    as a simple heuristic. Override this by providing a `colname_tidier`.
    """
    simple_cols, denormalised_cols, to_tables, to_columns, from_columns = \
        _normalisation_info(table)
    q = _denormalise_query(
        session,
        simple_cols + denormalised_cols,
        to_tables, to_columns, from_columns,
    )
    col_names = [ c.name for c in simple_cols ] + \
        [ colname_tidier(c.name) for c in denormalised_cols ]
    return q, col_names

def _denormalise_query(session, columns, to_tables, to_columns, from_columns):
    q = session.query(*columns)
    for to_table, to_column, fk in zip(to_tables, to_columns, from_columns):
        q = q.join(to_table, to_column == fk)
    return q

def _normalisation_info(table):
    primary_keys, foreign_keys, other = columns_partition(table)
    natural_keys = find_natural_key(table)
    if [ c for c in natural_keys if c.primary_key ]:
        # not unique columns, real numerical primary keys
        maybe_primary_keys = primary_keys
    else:
        maybe_primary_keys = []
    simple_cols = maybe_primary_keys + other
    denormalised_cols, to_tables, to_columns, from_columns = [], [], [], []
    for fk in foreign_keys:
        to_column = list(fk.foreign_keys)[0].column
        to_table = to_column.table
        remote_natural_keys = find_natural_key(to_table)
        if [ c for c in remote_natural_keys if c.primary_key ]:
            # no natural remote key, just use fk
            simple_cols.append(fk)
            continue
        denormalised_cols.append(remote_natural_keys[0].label(fk.name))
        to_tables.append(to_table)
        to_columns.append(to_column)
        from_columns.append(fk)
    return simple_cols, denormalised_cols, to_tables, to_columns, from_columns

def empty_deleter(table):
    """Returns function that returns given dict minus empty strings for nullable columns.
    Useful because CSV has no way to record NULL.
    """
    nullables = [ c.name for c in inspect(table).columns if c.nullable ]
    def _row_cleaner(d):
        c = dict(d)
        for col in nullables:
            if c[col] == '': c.pop(col)
        return c
    return _row_cleaner

def type_coercer(table):
    """Returns function that given a row dict will coerce values.
    Works on dates and booleans.
    Will only operate on strings, so if you have pass in a row that has already
    got non-string values, they will not be affected.
    """
    coerceables = {}
    for c in inspect(table).columns:
        coerceables[c.name] = _COERCE.get(c.type.python_type, lambda x: x)
    def _row_coercer(d):
        c = dict(d)
        for col in c:
            if isinstance(c[col], str):
                c[col] = coerceables[col](c[col])
        return c
    return _row_coercer

def renormalise_prepare(session, table, colname_tidier=_tidy_colname):
    """Returns function that will renormalise given dictionary
    Does the inverse of denormalise_prepare.
    """
    simple_cols, denormalised_cols, to_tables, to_columns, _ = \
        _normalisation_info(table)
    lookups = []
    for natural_key, surrogate_key in zip(denormalised_cols, to_columns):
        lookup_query = session.query(natural_key, surrogate_key)
        # coerce key to string as that's what CSV gives
        lookup = { str(nat): surr for nat, surr in lookup_query.all() }
        csv_name = colname_tidier(natural_key.name)
        lookups.append((csv_name, natural_key.name, lookup))
    def _row_maker(d):
        c = dict(d)
        for csv_name, sql_name, lookup in lookups:
            c[sql_name] = lookup[c.pop(csv_name)]
        return c
    return _row_maker

import pydoni
import pydoni.db
import pydoni.vb
from pydoni.scripts.__script_resources__.movie import clean_omdb_response
from pydoni.scripts.__script_resources__.movie import parse_omdb_ratings
from pydoni.scripts.__script_resources__.movie import query_omdb


def refresh_movie_imdb_table(schema, table, omdbapikey, verbose=False):
    """
    Query Postgres table containing IMDB metadata and refresh any values that need updating.
    """
    args, result = pydoni.pydonicli_declare_args_and_result(locals())
    result = {'Updated': [], 'No change': [], 'Not found': [], 'Error': []}

    import click
    import numpy as np
    from datetime import datetime, date
    from tqdm import tqdm

    def replace_null(val):
        """
        Replace given value with 'NULL' if it's an equivalent of NULL.

        :param val: value to check
        :type val: any
        :return: 'NULL' or `val`
        :rtype: str
        """

        if isinstance(val, float):
            if np.isnan(val):
                return 'NULL'

        if val is None:
            return 'NULL'

        if isinstance(val, str):
            if val in ['nan', 'None']:
                return 'NULL'

        return val

    def filter_updated_values(omdbresp, row):
        """
        Check each value queried from OMDB and that already in the database, and only add
        to a new dictionary, `upd` if it has changed. Therefore we only updated changed values.
        """
        import re

        upd = dict()
        for k, v in omdbresp.items():
            dbval = row[k]
            if v != dbval:
                if isinstance(dbval, date):
                    dbval = str(dbval)
                else:
                    # Attempt to compare integers/floats, may be
                    # stored as int/float/str
                    try:
                        v = re.sub(r'\..*', '', str(v))
                        dbval = re.sub(r'\..*', '', str(dbval))
                    except:
                        pass

                if v != replace_null(dbval):
                    upd[k] = v

        return upd

    pg = pydoni.db.Postgres()
    pkey_name = 'movie_id'
    df = pg.read_table(schema, table).sort_values(pkey_name)
    cols = pg.colnames(schema=schema, table=table)

    if verbose:
        pbar = tqdm(total=len(df), unit='movie')

    for i, row in df.iterrows():
        movie_name = '{} ({})'.format(row['title'], str(row['release_year']))

        try:
            omdbresp = query_omdb(title=row['title'], release_year=row['release_year'], omdbapikey=omdbapikey)
        except Exception as e:
            tqdm.write("{} in '{}': {}".format(click.style('ERROR', fg='red'), movie_name, str(e)))
            result['Error'].append(movie_name)
            if verbose:
                pbar.update(1)
            continue

        omdbresp = {k: v for k, v in omdbresp.items() if k in cols}
        omdbresp = {k: replace_null(v) for k, v in omdbresp.items()}

        color_map = {'No change': 'yellow', 'Updated': 'green', 'Not found': 'red'}
        change = 'Not found' if not len(omdbresp) else 'No change'

        # Filter out columns and values that do not require an update
        if change != 'Not found':
            upd = filter_updated_values(omdbresp, row)
            change = 'Updated' if len(upd) else change
            upd['imdb_update_ts'] = datetime.now()

            stmt = pg.build_update(schema,
                                   table,
                                   pkey_name=pkey_name,
                                   pkey_value=row[pkey_name],
                                   columns=[k for k, v in upd.items()],
                                   values=[v for k, v in upd.items()],
                                   validate=True)
            pg.execute(stmt)

        result[change].append(movie_name)

        if verbose:
            pbar.update(1)
            tqdm.write(click.style(change + ': ', fg=color_map[change]) + movie_name)

    if verbose:
        pbar.close()
        pydoni.vb.program_complete('Movie refresh complete!')

    pydoni.pydonicli_register_backend_vars(pydoni.what_is_my_name(with_modname=True), args, result)

import pydoni
import pydoni.db


def parse_omdb_ratings(ratings_object):
    """
    Extract IMDB, Rotten Tomatoes and Metacritic rating out of a ratings list of dictionaries
    queried directly from OMDB.

    :param ratings_object: list of dictionaries containing retrieved OMDB rating values
    :type ratings_object: list
    :return: cleaned ratings dictionary
    :rtype: dict
    """
    import re

    movie_source_map = {
        'internet movie database': 'rating_imdb',
        'rotten tomatoes': 'rating_rt',
        'metacritic': 'rating_mc',
    }

    res = {
        'rating_imdb': None,
        'rating_rt': None,
        'rating_mc': None
    }

    valid_sources = ['internet movie database', 'rotten tomatoes', 'metacritic']
    for rating in ratings_object:
        value = int(rating['value'].split('/')[0].replace('.', '').replace('%', '').replace(',', ''))
        res[movie_source_map[rating['source'].lower()]] = value

    return res


def clean_omdb_response(omdb_response_object):
    """
    Clean OMDB API response.

    :param omdb_response_object: raw response from OMDB API
    :type omdb_response_object: dict
    :return: dictionary of cleaned OMDB reponse
    :rtype: dict
    """
    from datetime import datetime, date

    data = omdb_response_object
    ratings = parse_omdb_ratings(data['ratings'])
    
    keep_cols = ['imdb_votes', 'runtime', 'director', 'awards', 'imdb_id', 'country',
        'omdb_populated', 'genre', 'production', 'writer', 'type', 'box_office', 'dvd',
        'language', 'actors', 'response', 'rated', 'poster', 'website', 'plot']
    addtl_cols = ['rating_imdb', 'rating_rt', 'rating_mc']

    res = {col: None for col in keep_cols + addtl_cols}
    res['omdb_populated'] = True if len(data) else False

    for k, v in data.items():
        if k in res.keys():
            res[k] = v

    for k, v in ratings.items():
        if k in res.keys():
            res[k] = v
    
    none_values = ['N/A']
    for k, v in res.items():
        if v in none_values:
            res[k] = None

    date_items = ['dvd']
    for item in date_items:
        if res[item] is not None:
            res[item] = datetime.strptime(res[item], '%d %b %Y').date()

    bool_items = ['response']
    for item in bool_items:
        if res[item] is not None:
            res[item] = True if res[item].lower() in ['t', 'true'] else False

    num_items = ['imdb_votes', 'runtime', 'box_office']
    for item in num_items:
        if res[item] is not None:
            rm_str = [',', '.', 'min', ' ', '$']
            for string in rm_str:
                res[item] = res[item].replace(string, '')
            res[item] = int(res[item].strip())

    return res


def query_omdb(title, release_year, omdbapikey):
    """
    Query OMDB and return a dictionary. Will return empty if not found.

    :param title: movie title to query for
    :type title: str
    :param release_year: release year of movie
    :type release_year: int
    :param omdbapikey: OMDB API key
    :type omdbapikey: str
    :return: dictionary of cleaned OMDB API response
    :rtype: dict
    """
    import omdb
    from datetime import datetime

    omdb.set_default('apikey', omdbapikey)

    data = omdb.get(title=title, year=release_year, fullplot=False, tomatoes=False)
    data = clean_omdb_response(data) if len(data) else {}
    
    return data
    


        
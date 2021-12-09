import csv
import collections
import os
import random

from requests import Session
from . import DataProvider

from ..constants import US_STATE_NAME_DICT
from ...campaign.constants import (TARGET_CHAMBER_BOTH, TARGET_CHAMBER_UPPER, TARGET_CHAMBER_LOWER,
        ORDER_IN_ORDER, ORDER_SHUFFLE, ORDER_UPPER_FIRST, ORDER_LOWER_FIRST)


class USStateData(DataProvider):
    KEY_OPENSTATES = 'us_state:openstates:{id}'
    KEY_GOVERNOR = 'us_state:governor:{state}'

    def __init__(self, cache, api_cache=None):
        self.cache = cache

    def _load_governors(self):
        """
        Load US state governor data from saved file
        Returns a dictionary keyed by state to cache for fast lookup

        eg us:governor:CA = {'title':'Governor', 'name':'Jerry Brown Jr.', 'phone': '18008076755'}
        """
        governors = collections.defaultdict(dict)

        with open('call_server/political_data/data/us_states.csv') as f:
            reader = csv.DictReader(f)

            for l in reader:
                direct_key = self.KEY_GOVERNOR.format(**{'state': l['state']})
                d = {
                    'title': 'Governor',
                    'name': ' '.join([l.get('first_name'), l.get('last_name')]),
                    'phone': l.get('phone'),
                    'state': l.get('state')
                }
                governors[direct_key] = d
        return governors

    def load_data(self):
        governors = self._load_governors()

        if hasattr(self.cache, 'set_many'):
            self.cache.set_many(governors)
        elif hasattr(self.cache, 'update'):
            self.cache.update(governors)
        else:
            raise AttributeError('cache does not appear to be dict-like')

        return len(governors)

    def cache_set(self, key, val):
        if hasattr(self.cache, 'set'):
            self.cache.set(key, val)
        elif hasattr(self.cache, 'update'):
            self.cache.update({key: val})
        else:
            raise AttributeError('cache does not appear to be dict-like')

    def get_legid(self, legid):
        cache_key = self.KEY_OPENSTATES.format(id=legid)
        return self.get_key(cache_key) or {}

    def get_uid(self, key):
        return self.cache.get(key) or {}

    def get_governor(self, state):
        cache_key = self.KEY_GOVERNOR.format(state=state)
        return self.cache.get(cache_key) or {}

    def locate_governor(self, state):
        return [self.KEY_GOVERNOR.format(state=state)]

    def locate_targets(self, latlon, chambers=TARGET_CHAMBER_BOTH, order=ORDER_IN_ORDER, state=None):
        """ Find all state legislators for a location, as comma delimited (lat,lon)
            Returns a list of cached openstate keys in specified order.
        """
        if type(latlon) == tuple:
            lat = latlon[0]
            lon = latlon[1]
        else:
            try:
                (lat, lon) = latlon.split(',')
            except ValueError:
                raise ValueError('USStateData requires location as lat,lon')

        params = dict(lat=float(lat), lng=float(lon), include='offices')
        s = Session()
        s.headers.update({'X-Api-Key': os.environ.get('OPENSTATES_API_KEY')})
        response = s.get("https://v3.openstates.org/people.geo", params=params)
        s.close()
        if response.status_code != 200:
            if response.status_code == 404:
                raise NotFound("Not found: {0}".format(response.url))
            else:
                raise Exception(response.text)

        legislators = response.json()['results']
        targets = []
        senators = []
        house_reps = []

        for l in legislators:
            parts = l['jurisdiction']['id'].partition('state:')
            state_abbr = parts[2].partition("/")[0]
            if state and (state.upper() != state_abbr.upper()):
                # limit to one state
                continue

            cache_key = self.KEY_OPENSTATES.format(**l)
            self.cache_set(cache_key, l)

            # limit to state legislators only
            if l['current_role']['org_classification'] == 'upper' and l['jurisdiction']['classification'] == 'state':
                senators.append(cache_key)
            if l['current_role']['org_classification'] == 'lower' and l['jurisdiction']['classification'] == 'state':
                house_reps.append(cache_key)

        if chambers == TARGET_CHAMBER_UPPER:
            targets = senators
        elif chambers == TARGET_CHAMBER_LOWER:
            targets = house_reps
        else:
            # default to TARGET_CHAMBER_BOTH
            if order == ORDER_UPPER_FIRST:
                targets.extend(senators)
                targets.extend(house_reps)
            elif order == ORDER_LOWER_FIRST:
                targets.extend(house_reps)
                targets.extend(senators)
            else:
                # default to name
                targets.extend(senators)
                targets.extend(house_reps)
                targets.sort()

        if order == ORDER_SHUFFLE:
            random.shuffle(targets)

        return targets

import csv
import collections
import random

from datetime import datetime
import yaml

from . import DataProvider

from ...campaign.constants import (TARGET_CHAMBER_BOTH, TARGET_CHAMBER_UPPER, TARGET_CHAMBER_LOWER,
        ORDER_IN_ORDER, ORDER_SHUFFLE, ORDER_UPPER_FIRST, ORDER_LOWER_FIRST)


class USData(DataProvider):
    KEY_BIOGUIDE = 'us:bioguide:{bioguide_id}'
    KEY_HOUSE = 'us:house:{state}:{district}'
    KEY_SENATE = 'us:senate:{state}'
    KEY_ZIPCODE = 'us:zipcode:{zipcode}'

    def __init__(self, cache):
        self.cache = cache

    def _load_legislators(self):
        """
        Load US legislator data from saved file
        Returns a dictionary keyed by state to cache for fast lookup

        eg us:senate:CA = [{'title':'Sen', 'first_name':'Dianne',  'last_name': 'Feinstein', ...},
                           {'title':'Sen', 'first_name':'Barbara', 'last_name': 'Boxer', ...}]
        or us:house:CA:13 = [{'title':'Rep', 'first_name':'Barbara',  'last_name': 'Lee', ...}]
        """
        legislators = collections.defaultdict(list)

        with open('call_server/political_data/data/legislators-current.yaml') as f:
            for info in yaml.load(f):
                term = info["terms"][-1]
                if term["start"] < "2011-01-01":
                    continue # don't get too historical

                record = {
                    "first_name":  info["name"]["first"],
                    "last_name":   info["name"]["last"],
                    "bioguide_id": info["id"]["bioguide"],
                    "title":       "Senator" if term["type"] == "sen" else "Representative",
                    "phone":       term["phone"],
                    "current":     datetime.now().strftime("%Y-%m-%d") <= term["end"],
                    "chamber":     "senate" if term["type"] == "sen" else "house",
                    "state":       term["state"],
                    "district":    term.get("district", None),
                    "bioguide_id": info["id"]["bioguide"]
                }

                direct_key = self.KEY_BIOGUIDE.format(**record)
                if record["chamber"] == "senate":
                    chamber_key = self.KEY_SENATE.format(**record)
                else:
                    chamber_key = self.KEY_HOUSE.format(**record)

                legislators[direct_key].append(record)
                legislators[chamber_key].append(record)

        return legislators

    def load_data(self):
        legislators = self._load_legislators()

        if hasattr(self.cache, 'set_many'):
            self.cache.set_many(legislators)
        elif hasattr(self.cache, 'update'):
            self.cache.update(legislators)
        else:
            raise AttributeError('cache does not appear to be dict-like')

        return len(legislators)

    # convenience methods for easy house, senate, district access
    def get_house_member(self, state, district):
        key = self.KEY_HOUSE.format(state=state, district=district)
        return self.cache.get(key)

    def get_senators(self, state):
        key = self.KEY_SENATE.format(state=state)
        return self.cache.get(key) or []

    def get_bioguide(self, uid):
        return self.cache.get(self.KEY_BIOGUIDE.format(bioguide_id=uid)) or {}

    def get_executive(self):
        # return Whitehouse comment line
        return [{'office': 'Whitehouse Comment Line',
                'number': '12024561111'}]

    def get_uid(self, key):
        return self.cache.get(key) or {}

    def locate_targets(self, state, district, chambers=TARGET_CHAMBER_BOTH, order=ORDER_IN_ORDER):
        """ Find all congressional targets for a state/district.
        Returns a list of cached bioguide keys in specified order.
        """

        senators = []
        house_reps = []
        for senator in self.get_senators(state):
            senators.append(self.KEY_BIOGUIDE.format(**senator))

        rep = self.get_house_member(state, district)[0]
        house_reps.append(self.KEY_BIOGUIDE.format(**rep))

        targets = []
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

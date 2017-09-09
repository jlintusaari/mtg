#!/usr/bin/env python

"""Python 3 class for scraping scryfall card info and images

Usage
-----
python3 suomi24scraper.py -h
python3 suomi24scraper.py [num_pages] -v

"""

import os
import logging
import argparse
import datetime
import json
import time
import pickle

from bs4 import BeautifulSoup as BS
import requests
import re


logger = logging.getLogger('mtg')


def fetch_url(url, decode=True):
    resp = requests.get(url)
    if resp.status_code != 200:
        raise ValueError('Request failed, status code {}'.format(resp.status_code))

    content = resp.content
    if decode:
        content = content.decode()
    return content


class ScryfallScraper:

    def __init__(self):
        self.data_path = 'data'
        self.image_path = 'data/images'
        os.makedirs(self.image_path, exist_ok=True)

        self.last_fetch_time = None
        self.fetch_delay = .1

        # TODO: open the cards file
        # Saved by their id
        self.cards = {}

    def scrape_cards(self):
        next_url = 'https://api.scryfall.com/cards'

        while True:
            if next_url is None:
                break

            logger.info('Parsing url %s' % next_url)

            data = self.fetch_url(next_url)
            data = json.loads(data)

            cards = data['data']
            self.parse_cards(cards)

            next_url = data['next_page'] if data['has_more'] else None

        pickle.dump(self.cards, open(os.path.join(self.data_path, "cards.pkl"), "wb"))

    def parse_cards(self, cards):
        for card in cards:
            logger.info('Parsing card %s' % card['name'])

            id = card['id']
            self.cards[id] = card
            image_uri = card['image_uri']

            if not image_uri:
                logger.info('No image for %d' % id)
                continue

            image_fn = os.path.join(self.image_path, id + '.' + self._get_image_extension(image_uri))
            img_content = self.fetch_url(image_uri, False)

            with open(image_fn, 'wb') as handler:
                handler.write(img_content)

    def _get_image_extension(self, image_uri):
        ext = image_uri.split('/')[-1]
        ext = ext.split('?')[0]
        return ext.split('.')[1]

    def fetch_url(self, url, decode=True):
        t = time.time()
        t0 = self.last_fetch_time or 0
        sleep = t0 + self.fetch_delay - t
        if sleep > 0:
            time.sleep(sleep)

        resp = requests.get(url)
        self.last_fetch_time = time.time()

        if resp.status_code != 200:
            raise ValueError('Request failed, status code {}'.format(resp.status_code))

        content = resp.content
        if decode:
            content = content.decode()

        return content


def parse_args():
    parser = argparse.ArgumentParser(
        description='Suomi 24 scraper'
    )

    parser.add_argument("-d", "--to_date", nargs=1, default=None, type=str, help="To which date to scrape.")
    parser.add_argument("-o", "--operator", nargs=1, default=['elisan-liittymat'], type=str,
                        help="Operator name in Suomi24. Possible values include: "
                             "dna-, "
                             "elisan-liittymat, "
                             "muut-liittymat, "
                             "saunalahti, "
                             "sonera-, "
                             "tele-finland.")
    parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    #parser = parse_args()

    #args = parse_args()
    #if args.verbose:
    #    logging.basicConfig(level=logging.INFO)

    #to_date = datetime.date.today() - datetime.timedelta(days=7) if args.to_date is None \
    #    else parse_finnish_date(args.to_date[0])
    #operator = args.operator

    #scraper = Suomi24Scraper(operator=operator[0])
    #scraper.scrape(to_date=to_date)

    scraper = ScryfallScraper()
    scraper.scrape_cards()

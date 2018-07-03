#!/usr/bin/env python

"""Python 3 class for scraping scryfall card info and images

Usage
-----
python3 scraper.py

"""

import os
import logging
import argparse
import datetime
import json
import time
import pickle

import requests
import re
import glob


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
        self.cards_base_name = 'cards_dict.json'

        os.makedirs(self.image_path, exist_ok=True)

        self.last_fetch_time = None
        self.fetch_delay = .1

        # Saved by their id
        self.cards = {}

    @property
    def cards_path(self):
        return os.path.join(self.data_path, self.cards_base_name)

    def load_cards(self):
        """Load card dictionary from data_path"""
        path = self.cards_path
        logger.info("Opening file {}".format(path))

        if not os.path.isfile(path):
            raise FileNotFoundError('No cards dictionary file {} found'.format(path))

        with open(path, 'r') as cards_file:
            self.cards = json.load(cards_file)

    def save_cards(self):
        path = self.cards_path
        logger.info("Saving to file {}".format(path))

        with open(path, 'w') as cards_file:
            json.dump(self.cards, cards_file)

    def fetch_cards(self, start_page=None):
        """Fetch the card dictionary from the server and save it"""
        next_url = 'https://api.scryfall.com/cards'
        if start_page is not None:
            next_url += '?page={}'.format(start_page)

        while True:
            if next_url is None:
                break

            logger.info('Parsing cards from url %s' % next_url)

            json_data = self.fetch_url(next_url)
            # Read the cards list
            data = json.loads(json_data)
            cards = data['data']

            self._parse_cards_list(cards)

            next_url = data['next_page'] if data['has_more'] else None

        logger.info('Found {}/{} cards'.format(len(self.cards), data['total_cards']))

        self.save_cards()

    def _parse_cards_list(self, cards):
        """Parse the card list from the server into self.cards"""
        for card in cards:
            logger.info('Parsing card %s' % card['name'])

            id = card['id']
            self.cards[id] = card

    def _get_image_paths(self):
        return glob.glob(os.path.join(self.image_path, '*.*'))

    def _get_image_ids(self):
        image_paths = self._get_image_paths()
        id_set = set()
        for path in image_paths:
            id = path.split('/')[-1].split('.')[0]
            id_set.add(id)
        return id_set

    def fetch_images(self):
        """Fetch images from the server.

        Checks if the image exists in disk, and if not, fetches it from the server.
        """
        if self.cards is None:
            raise ValueError('Please first either load the cards or fetch them from the server')

        existing_images = self._get_image_ids()

        logger.info('{} images found from disk'.format(len(existing_images)))

        for card in self.cards.values():
            id = card['id']
            if id in existing_images:
                continue

            self._fetch_card(card)

    def _fetch_card(self, card):
        id = card['id']
        image_uri = card['image_uri']
        name = card['name']

        logger.info('Fetching card {}'.format(name))

        if not image_uri:
            logger.info('No image for {} {}'.format(name, id))
            return

        image_fn = os.path.join(self.image_path, id + '.' + self._get_image_extension(image_uri))
        img_content = self.fetch_url(image_uri, False)

        with open(image_fn, 'wb') as handler:
            handler.write(img_content)

    def _get_image_extension(self, image_uri):
        ext = image_uri.split('/')[-1]
        ext = ext.split('?')[0]
        return ext.split('.')[-1]

    def fetch_url(self, url, decode=True):
        t = time.time()
        t0 = self.last_fetch_time or 0
        sleep = t0 + self.fetch_delay - t
        if sleep > 0:
            time.sleep(sleep)

        self.last_fetch_time = time.time()
        resp = requests.get(url)

        if resp.status_code != 200:
            raise ValueError('Request failed, status code {}'.format(resp.status_code))

        content = resp.content
        if decode:
            content = content.decode()

        return content


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    # Fetch images for all cards
    scraper = ScryfallScraper()
    scraper.load_cards()
    scraper.fetch_images()


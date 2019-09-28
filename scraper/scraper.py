import asyncio
import hashlib
import logging
import os
import random
from datetime import datetime
from typing import List

import aiohttp
import requests
from bs4 import BeautifulSoup

from line import Line
from utils import chunkify
from utils.bitly_utils import shorten

BITLY_ACCESS_TOKEN_ENV = "BITLY_ACCESS_TOKEN"

FIRESTORE_BATCH_MAXIMUM_SIZE = 500

logger = logging.getLogger(__name__)

if BITLY_ACCESS_TOKEN_ENV not in os.environ:
    raise ValueError(
        "Environment variable '{}' required".format(BITLY_ACCESS_TOKEN_ENV))
bitly_token = os.getenv(BITLY_ACCESS_TOKEN_ENV)


def get_soup_and_hash(url):
    """
    Download content of the timetable page from GrandaBus website.
    :param url: url to be scraped
    :return: BeautifulSoup of the html response obtained
    """
    response = requests.get(url)
    if not response.status_code == 200:
        raise Exception(f'Something went wrong while requesting {url}')

    text = response.text
    response_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
    return BeautifulSoup(text, "html.parser"), response_hash


class GrandaBusScraper:
    """
    Scraper that extracts bus lines from the bus company website.
    Bus lines are then stored in Firestore.
    """

    # url of the timetable page from GrandaBus website
    _URL = "http://grandabus.it/orari-per-localita/"

    def __init__(self, firestore_client,
                 do_not_overwrite_if_unchanged=True):
        """
        Constructor
        Instantiate a new GrandaBusScraper
        """
        self.do_not_overwrite_if_unchanged = do_not_overwrite_if_unchanged

        self._firestore = firestore_client

        # callbacks
        self._on_line_deleted = None
        self._on_lines_file_changed = None

    @property
    def on_lines_deleted(self):
        return self._on_line_deleted

    @on_lines_deleted.setter
    def on_lines_deleted(self, callback):
        if not callback:
            raise ValueError("on_line_deleted callback should not be None")
        self._on_line_deleted = callback

    @property
    def on_lines_file_changed(self):
        return self._on_lines_file_changed

    @on_lines_file_changed.setter
    def on_lines_file_changed(self, callback):
        if not callback:
            raise ValueError("on_line_file_changed callback should not be None")
        self._on_lines_file_changed = callback

    async def run(self):
        """
        Scrape the timetables page
        """
        logger.info("Scraping started")
        lines = list()

        soup, response_hash = get_soup_and_hash(self._URL)

        if self.do_not_overwrite_if_unchanged:
            if response_hash == self._get_last_session_hash():
                # no need to go further
                return

        timetable = soup.find(id="tablepress-99")

        # verify that all the table fields are where they are expected to be
        if not self._verify_headers(timetable):
            logger.fatal("Table schema changed. Cannot scrape data.")
            raise IOError("Damn! Timetable schema changed.")

        for row in timetable.find("tbody").find_all("tr"):
            # for each row extract all the fields needed
            td = row.find("td")  # province (unused)

            td = td.find_next_sibling("td")
            name = td.get_text()

            td = td.find_next_sibling("td")
            line_code = td.get_text()

            # check if a line with the same code already exists
            line = next(filter(lambda x: x.code == line_code, lines), None)
            if line is None:
                # if the line does not exists, create one
                td = td.find_next_sibling("td")
                line_name = td.get_text()

                a = td.find_next_sibling("td").find("a")
                url = a['href']

                line = Line(line_code, line_name, url)
                lines.append(line)

            line.cities.append(name)

        await self._complete(lines)
        self._set_last_session_hash(response_hash, datetime.now())

    async def _complete(self, lines: List[Line]):
        """
        Last step of the scraper execution.
        Delete outdated lines and save new ones. Also notify the outer world about
        what happened.

        :param lines: lines scraped
        """
        await self._shorten_urls(lines)
        await self._compute_file_hashes(lines)

        old_lines = self._get_all_lines()

        # delete lines that are currently inside the database
        # but not into the ones just scraped
        should_delete = set(old_lines) - set(lines)  # set difference
        should_delete_ids = list(map(lambda x: x.code, should_delete))
        self._delete_old_lines(should_delete_ids)

        should_notify_file_change = list()
        for line in lines:
            try:
                old_line = next(filter(lambda x: x.code == line.code, old_lines))
                if line.file_hash is not None and not old_line.file_hash == line.file_hash:
                    should_notify_file_change.append(old_line)  # old_line contains the list of users to be notified
            except StopIteration:
                pass

        # notify the outer world
        self.on_lines_deleted(should_delete)
        self.on_lines_file_changed(should_notify_file_change)

        # push the lines to the database
        self._save(lines)

    def _get_last_session_hash(self):
        """
        Get the hash of the last scraped page
        :return: hash of the last scraped page if it exists, None otherwise
        """
        d = self._firestore.collection('scraper').document('last_session').get()
        return d.to_dict()['response_hash'] if d.exists else None

    def _set_last_session_hash(self, response_hash, date):
        """
        Set last session information
        :param response_hash: hash of the page scraped
        :param date: when the page was scraped
        """
        self._firestore.collection('scraper').document('last_session').set({
            u'response_hash': response_hash,
            u'date': date
        })

    def _save(self, lines):
        """
        Save lines scraped from the website.
        :param lines: lines to be saved
        """
        lines_ref = self._firestore.collection(u'lines')
        # split the lines in chunks and batch update them in the database
        for chunk in chunkify(lines, FIRESTORE_BATCH_MAXIMUM_SIZE):
            batch = self._firestore.batch()
            for line in chunk:
                batch.set(lines_ref.document(line.code), {
                    u'code': line.code,
                    u'name': line.name,
                    u'timetable_url': line.url,
                    u'cities': list(line.cities),
                    u'file_hash': line.file_hash
                }, merge=True)
                logging.info(f'saving line with code {line.code}')
            batch.commit()

    def _get_all_lines(self) -> List[Line]:
        """
        Read currently stored lines.
        :return: a list of lines
        """
        lines_ref = self._firestore.collection(u'lines')
        return list([Line.from_dict(line.to_dict()) for line in lines_ref.stream()])

    def _delete_old_lines(self, should_delete):
        """
        Remove outdated lines from the database.
        :param should_delete: lines to be deleted
        """
        lines_ref = self._firestore.collection(u'lines')

        # split the should_delete into chunks of size 500
        # and then batch delete them
        for chunk in chunkify(should_delete, FIRESTORE_BATCH_MAXIMUM_SIZE):
            batch = self._firestore.batch()

            for line in chunk:
                batch.delete(lines_ref.document(line))
                logger.info(f'deleting outdated line {line}.')
            batch.commit()

    @staticmethod
    def _verify_headers(table):
        """
        Check if table schema of the page is still the same.
        :param table: html table from GrandaBus page
        :return: true if all the headers are the ones expected
        """
        ths = table.find("thead").find_all("th")
        headers = list(map(lambda th: th.get_text().lower(), ths))

        return headers[0] == "provincia" \
               and headers[1] == "comune" \
               and headers[2] == "codice" \
               and headers[3] == "linea" \
               and headers[4] == "url"

    @staticmethod
    async def _shorten_urls(lines: List[Line]):
        """
        Shorten timetables's URLs.
        Since shortening is not mandatory, if one process fails a log written and that url ignored.
        :param lines: lines to be processed
        """
        # try to shorten the urls
        async with aiohttp.ClientSession() as session:
            for line in lines:
                try:
                    old_url = line.url
                    line.url = await shorten(line.url, bitly_token, session) or line.url
                    logger.info(f'Shortened url {old_url} -> {line.url}')
                except Exception as e:
                    logger.error(f'Cannot shorten {line.url}. Message: {e}')
                await asyncio.sleep(random.randint(1, 2))

    @staticmethod
    async def _compute_file_hashes(lines: List[Line]):
        """
        Download timetables and compute sha256 hashes
        :param lines: lines to be processed
        """
        async with aiohttp.ClientSession() as session:
            for i, line in enumerate(lines):
                try:
                    line.file_hash = await GrandaBusScraper._compute_file_hash(line, session)
                    logging.debug(f'Computed hash {i + 1}/{len(lines)} (line {line.code}): {line.file_hash}')
                    await asyncio.sleep(random.randint(5, 10))
                except Exception as e:
                    logging.error(f'Error computing hash {i}/{len(lines)}: {e}')

    @staticmethod
    async def _compute_file_hash(line: Line, session: aiohttp.ClientSession):
        """
        Compute the sha256 hash of the line's timetable pdf.
        :param line: line to be processed
        :param session: aiohttp session
        :return: the sha256 hash of the timetable
        """
        if not line.url:
            return None

        async with session.get(line.url) as response:
            if not response.status == 200:
                raise IOError(f'Cannot fetch {line.url}')

            payload = await response.read()
            h = hashlib.sha256(payload)
            return h.hexdigest()
